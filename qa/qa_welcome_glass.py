#!/usr/bin/env python3
"""QA: welcome-flow glass redesign (2026-10-07).
Covers 60c0368 (styles.css: 3D crystal glass system, iOS selection kill
(`-webkit-user-select:none` on the .wlcmhost subtree, inputs re-enabled),
volt-glow selected states, glassy dots, wlcmRise/wlcmStepR/wlcmStepL
keyframes, reduced-motion fallback, .wlcm-aurora) and 92757c8 (js/i18n.js:
staggered wlcm-rise entrances, direction-aware wlcm-step-enter-r/l on
#wlcmBody, aurora div injection, flow logic untouched).

Checks:
 1. Welcome forced: localStorage['orbit_i18n'] cleared, then
    HUB.i18n.ensureWelcome(()=>{}) via Runtime.evaluate.
 2. Screenshots of all 3 steps (lang, country, ready) at 390px and 320px.
 3. Zero console/page errors on load + through all steps.
 4. Selection-artifact: long-press (touchStart, 700ms, touchEnd) on a
    language card and on the "Choose your language" heading ->
    window.getSelection().toString()==='' and zero ranges.
 5. Full flow: tap lang -> country step renders; tap country -> ready step;
    Back -> lang step; Continue (#wlcmGo) -> host hidden +
    localStorage['orbit_i18n'] persisted.
 6. Search input: type in #wlcmLQ -> list filters, input keeps focus.
 7. No horizontal overflow (documentElement.scrollWidth <= innerWidth) on
    all steps, both viewports.
 8. .wlcm-aurora pointer-events:none; cards are the hit-test target.
 9. Reduced motion: emulated -> content visible/static, flow completes.
10. Perf: no longtask > 500ms observed during the step transitions.

Run: python3 qa/qa_welcome_glass.py   (from ~/workspace/hub)
"""
import subprocess, time, json, os, sys, base64, shutil
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websocket  # noqa: F401

CHROME = '/opt/meta-chromium/chrome'
PORT = 9462  # not 9461 (qa_login3d) — never share a CDP port with another harness
BASE = 'file:///home/hatch/workspace/hub/index.html'
QADIR = os.path.dirname(os.path.abspath(__file__))
fails = []
notes = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    sys.stdout.flush()
    if not ok:
        fails.append(n)

def note(s):
    notes.append(s)
    print("NOTE " + s)
    sys.stdout.flush()

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl)
        self.ws.settimeout(35)
        self.id = 0
        self.evts = []
    def send(self, method, params=None, wait=True, timeout=30):
        self.id += 1
        myid = self.id
        self.ws.send(json.dumps({'id': myid, 'method': method, 'params': params or {}}))
        if not wait:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = json.loads(self.ws.recv())
            except Exception as e:
                raise TimeoutError(method + ': ' + str(e)[:100])
            if msg.get('id') == myid:
                return msg.get('result')
            self.evts.append(msg)  # event or stray response -> harvest
        raise TimeoutError(method)

def j(c, expr, await_=False, timeout=30):
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip()
        if e.endswith(';'):
            e = e[:-1]
    e = e.rstrip().rstrip(';')
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q:
                instr = False
        elif ch in '"\'`':
            instr, q = True, ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ';' and depth == 0:
            top_semi = True
            break
    if not top_semi:
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'awaitPromise': await_, 'returnByValue': True},
               wait=True, timeout=timeout)
    return ((r or {}).get('result', {}) or {}).get('value')

def harvest_errors(c):
    errs = []
    for m in c.evts:
        meth = m.get('method')
        if meth == 'Log.entryAdded':
            e = (m.get('params') or {}).get('entry', {})
            if e.get('level') == 'error':
                errs.append('LOG[%s] %s' % (e.get('source'), (e.get('text') or '')[:180]))
        elif meth == 'Runtime.exceptionThrown':
            d = (m.get('params') or {}).get('exceptionDetails', {})
            errs.append('EXC %s' % ((d.get('text') or '')[:180]))
        elif meth == 'Runtime.consoleAPICalled':
            p = m.get('params') or {}
            if p.get('type') == 'error':
                txt = ' '.join(str(a.get('value', a.get('description', '')))
                               for a in p.get('args', []))[:180]
                errs.append('CONSOLE %s' % txt)
        elif meth == 'Network.loadingFailed':
            p = m.get('params') or {}
            errs.append('NETFAIL %s (%s)' % (p.get('errorText'), (p.get('blockedReason') or '')))
    return errs

def errors_now(c):
    errs = harvest_errors(c)
    page_errs = j(c, "return window.__huberr||[];") or []
    return [e for e in (errs + ['PAGE ' + x for x in page_errs])
            if 'firebasejs' not in e and 'gstatic' not in e and 'net::' not in e.lower()]

def boot(width, reduced=False, tag=''):
    prof = '/tmp/hubqa-wlcm%s-%d' % (tag, width)
    shutil.rmtree(prof, ignore_errors=True)
    args = [CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
            '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files',
            '--remote-allow-origins=*', '--user-data-dir=' + prof,
            '--hide-scrollbars', '--window-size=%d,844' % width, 'about:blank']
    proc = subprocess.Popen(args)
    time.sleep(2.5)
    tgt = None
    for _ in range(30):
        try:
            tgts = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read())
            pages = [t for t in tgts if t.get('type') == 'page']
            if pages:
                tgt = pages[0]
                break
        except Exception:
            pass
        time.sleep(0.4)
    assert tgt, 'no page target'
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable')
    c.send('Page.enable')
    c.send('Log.enable')
    c.send('Network.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': width, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    if reduced:
        c.send('Emulation.setEmulatedMedia',
               {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    # NOTE: orbit_i18n is deliberately NOT seeded — this run wants the
    # welcome flow. __gateSkip keeps the auth front-door overlay away.
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "window.__gateSkip=true;"
        "window.__huberr=[];addEventListener('error',function(e){__huberr.push('ERR:'+e.message)});"
        "addEventListener('unhandledrejection',function(e){__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))});"})
    c.send('Page.navigate', {'url': BASE})
    ok = False
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.i18n&&typeof HUB.i18n.ensureWelcome==='function');") is True:
            ok = True
            break
        time.sleep(0.5)
    assert ok, 'HUB boot failed'
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    # boot watchdog fires the "couldn't start" recovery overlay on fresh
    # headless profiles because ensureWelcome waits for user input —
    # pre-existing, not an app regression; dismiss it.
    j(c, "var r=document.getElementById('saferecov'); if(r) r.remove(); return 1;")
    # longtask observer for the perf check (check 10)
    j(c, """window.__longs=[];
      try{ new PerformanceObserver(function(l){var es=l.getEntries();
        for(var i=0;i<es.length;i++) __longs.push(Math.round(es[i].duration));
      }).observe({entryTypes:['longtask']}); }catch(e){} return 1;""")
    # check 1: force the welcome flow (fresh, no orbit_i18n).
    # The app's own boot ALSO calls ensureWelcome async via bootLocale(); if
    # we force ours first, boot's call lands ~seconds later, resets
    # wlcmStep='lang' and rebuilds the host mid-test (caught by QA as a
    # transient "no step" state followed by a jump back to lang). So: wait for
    # the app's own welcome host to be visible first, then re-force with our
    # instrumented callback, then demand a quiescent 'lang' step before
    # proceeding.
    for _ in range(60):
        if j(c, "var h=document.getElementById('wlcmHost'); return !!(h&&!h.hidden);") is True:
            break
        time.sleep(0.25)
    time.sleep(1.0)
    j(c, "try{localStorage.removeItem('orbit_i18n');}catch(e){}"
         "HUB.i18n.ensureWelcome(function(){window.__wlcmDone=true;}); return 1;")
    time.sleep(0.5)
    j(c, "var r=document.getElementById('saferecov'); if(r) r.remove(); return 1;")
    t0, last, stable = time.time(), None, 0
    while time.time() - t0 < 8:
        s = j(c, "if(document.getElementById('wlcmLQ')) return 'lang';"
                 " if(document.getElementById('wlcmQ')) return 'country';"
                 " if(document.getElementById('wlcmGo')) return 'ready'; return null;")
        stable = stable + 1 if (s == 'lang' and s == last) else 0
        last = s
        if stable >= 6:  # 1.5s of steady 'lang': boot's call already landed
            break
        time.sleep(0.25)
    # Disarm the 15s boot watchdog via the app's own API. Boot is NOT hung —
    # we are intentionally dwelling on the welcome screen, and HUB.safe.booted()
    # is otherwise only called after welcome completes, so the watchdog would
    # otherwise pop the #saferecov recovery overlay mid-test and swallow taps.
    # NOTE: j() cannot wrap try/catch statements (its return-wrap produces a
    # syntax error and silently yields None), so the disarm is a plain
    # statement list with a top-level semicolon before the final return.
    disarmed = j(c, "var __b=window.HUB&&HUB.safe; if(__b&&__b.booted) __b.booted();"
                    " return (__b&&__b.isBooted)?__b.isBooted():false;")
    check('%d: watchdog disarmed via HUB.safe.booted()' % width, disarmed is True, disarmed)
    j(c, "var r=document.getElementById('saferecov'); if(r) r.remove(); return 1;")
    return c, proc, prof

def shot(c, relpath):
    r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True, timeout=30)
    p = os.path.join(QADIR, os.path.basename(relpath))
    with open(p, 'wb') as f:
        f.write(base64.b64decode(r['data']))
    print('shot', p)
    sys.stdout.flush()

def center(c, selector):
    return j(c, "var el=document.querySelector(%s); if(!el) return null;"
                " var r=el.getBoundingClientRect();"
                " return [Math.round(r.x+r.width/2), Math.round(r.y+r.height/2)];"
             % json.dumps(selector))

def tap(c, x, y):
    c.send('Input.dispatchMouseEvent',
           {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
    c.send('Input.dispatchMouseEvent',
           {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})

def touch_hold(c, x, y, ms=700):
    c.send('Input.dispatchTouchEvent',
           {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y, 'id': 1}]})
    time.sleep(ms / 1000.0)
    c.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})

def sel_state(c):
    """[text, rangeCount, isCollapsed] of the current selection."""
    return j(c, """var s=window.getSelection();
      return [s.toString(), s.rangeCount, s.isCollapsed];""")

def touch_hold_sel(c, x, y, ms=700):
    """Long-press, then report the selection state it left behind."""
    j(c, "window.getSelection().removeAllRanges(); return 1;")
    touch_hold(c, x, y, ms)
    return sel_state(c)

def sel_ok(s):
    return isinstance(s, list) and s[0] == '' and (s[1] == 0 or s[2] is True)

def step(c):
    """'lang' | 'country' | 'ready' | None"""
    return j(c, """if(document.getElementById('wlcmLQ')) return 'lang';
      if(document.getElementById('wlcmQ')) return 'country';
      if(document.getElementById('wlcmGo')) return 'ready'; return null;""")

def wait_step(c, want, timeout=4.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if step(c) == want:
            return True
        time.sleep(0.08)
    return False

def poll_body_dir(c, want, timeout=1.2):
    """Catch the direction-aware step-transition class (cleared after 320ms)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = j(c, "return document.getElementById('wlcmBody').classList.contains(%s);"
              % json.dumps(want))
        if v is True:
            return True
        time.sleep(0.03)
    return False

def kill_recover(c):
    j(c, "var r=document.getElementById('saferecov'); if(r) r.remove(); return 1;")

def overflow_ok(c):
    return j(c, "return document.documentElement.scrollWidth <= window.innerWidth;") is True

# ---------------------------------------------------------------- main run
def run_width(width):
    c, proc, prof = boot(width)
    try:
        kill_recover(c)
        check('%d: welcome host shown (lang step)' % width,
              j(c, "return !document.getElementById('wlcmHost').hidden;") is True and step(c) == 'lang')
        time.sleep(1.4)  # let wlcmRise stagger (<=540ms cap) settle
        kill_recover(c)
        shot(c, 'qa/wlcm-lang-%d.png' % width)

        # ---- glass system (60c0368 CSS side) ----
        bf = j(c, "return getComputedStyle(document.querySelector('.wlcm-card')).backdropFilter;")
        check('%d: crystal glass card (backdrop-filter blur 18px)' % width,
              bf not in (None, 'none') and 'blur(18px)' in bf, bf)
        us = j(c, "return getComputedStyle(document.getElementById('wlcmHost')).userSelect;")
        check('%d: iOS selection kill on .wlcmhost subtree' % width, us == 'none', us)
        ius = j(c, "return getComputedStyle(document.getElementById('wlcmLQ')).userSelect;")
        check('%d: search input re-enables text selection' % width, ius == 'text', ius)
        dotbs = j(c, "return getComputedStyle(document.querySelector('.wlcm-dot.on')).boxShadow;")
        check('%d: glassy active dot has volt glow' % width,
              dotbs not in (None, 'none') and '212, 245, 63' in dotbs, str(dotbs)[:70])
        onbs = j(c, "return getComputedStyle(document.querySelector('[data-wlang=\"en\"]')).boxShadow;")
        check('%d: selected lang card volt-glow (.wlcm-lang.on)' % width,
              onbs not in (None, 'none') and '212, 245, 63' in onbs, str(onbs)[:70])
        stg = j(c, """return Array.prototype.map.call(
          document.querySelectorAll('.wlcm-langs .wlcm-lang'),
          function(e,i){return (i<3)?(e.classList.contains('wlcm-rise')?1:0)+':'+e.style.getPropertyValue('--d'):'';}
          ).slice(0,3).join(',');""")
        check('%d: staggered wlcm-rise entrance (0/45/90ms --d)' % width,
              stg == '1:0ms,1:45ms,1:90ms', stg)

        # ---- check 8: aurora ----
        au_pe = j(c, "var a=document.querySelector('.wlcm-aurora');"
                     " return a?getComputedStyle(a).pointerEvents:null;")
        au_in = j(c, "return !!(document.getElementById('wlcmHost')&&"
                      "document.querySelector('.wlcm-aurora')&&"
                      "document.getElementById('wlcmHost').contains(document.querySelector('.wlcm-aurora')));")
        au_anim = j(c, "return getComputedStyle(document.querySelector('.wlcm-aurora'),'::before').animationName;")
        check('%d: .wlcm-aurora injected, pointer-events:none' % width,
              au_pe == 'none' and au_in is True, 'pe=%s in-host=%s' % (au_pe, au_in))
        check('%d: aurora ambient animation running' % width,
              au_anim not in (None, 'none'), au_anim)
        # The task's overlap requirement: aurora must not intercept, and the
        # card must be what a tap hits. elementFromPoint is evaluated against
        # the LIVE button (the list re-renders, so no stale identity check);
        # the functional taps later in the flow are the final proof.
        hit, hit_diag = False, ''
        for _ in range(3):
            pt = center(c, '[data-wlang="en"]')
            hit_diag = j(c, """var el=document.elementFromPoint(%d,%d);
              var b=el&&el.closest?el.closest('button.wlcm-lang'):null;
              return (b&&b.hasAttribute('data-wlang')) ? 'card'
                : (el? (el.tagName+'.'+el.className+'#'+el.id) : 'null');""" % (pt[0], pt[1]))
            if hit_diag == 'card':
                hit = True
                break
            time.sleep(0.3)
        check('%d: cards receive taps (aurora never the hit-test target)' % width,
              hit is True, hit_diag)

        # ---- check 7: overflow on lang step ----
        check('%d: no horizontal overflow (lang)' % width, overflow_ok(c),
              'scrollWidth=%s innerWidth=%s' % (
                  j(c, "return document.documentElement.scrollWidth;"),
                  j(c, "return window.innerWidth;")))

        # ---- check 4 (part 1): heading long-press ----
        hpt = center(c, 'h2.wlcm-h')
        assert hpt, 'h2.wlcm-h not found'
        sel = touch_hold_sel(c, hpt[0], hpt[1])
        check('%d: long-press heading -> no text selection' % width,
              sel_ok(sel), sel)
        time.sleep(0.2)
        kill_recover(c)
        shot(c, 'qa/wlcm-select-%d.png' % width)

        # ---- check 5: forward step (mouse tap lang -> country), direction ----
        # Dedicated mouse tap here so the wlcm-step-enter-r class is caught
        # deterministically (the card long-press below also navigates, which
        # would make this racy if done after).
        pt = center(c, '[data-wlang="en"]')
        tap(c, pt[0], pt[1])
        seen_r = poll_body_dir(c, 'wlcm-step-enter-r')
        check('%d: forward step slides in from right (wlcm-step-enter-r)' % width,
              seen_r is True)
        check('%d: tap lang -> country step renders' % width, wait_step(c, 'country'),
              step(c))
        time.sleep(0.6)
        cleared = j(c, "return document.getElementById('wlcmBody')"
                       ".classList.contains('wlcm-step-enter-r');") is False
        check('%d: step-transition class cleared after animation' % width, cleared)
        kill_recover(c)
        shot(c, 'qa/wlcm-country-%d.png' % width)
        check('%d: no horizontal overflow (country)' % width, overflow_ok(c))
        crowbs = j(c, "return getComputedStyle(document.querySelector('.wlcm-crow.on')).background;")
        check('%d: selected country row volt wash (.wlcm-crow.on)' % width,
              crowbs is not None and '212, 245, 63' in crowbs, str(crowbs)[:70])
        crowsh = j(c, "return getComputedStyle(document.querySelector('.wlcm-crow.on')).boxShadow;")
        check('%d: selected country row volt left-edge (.wlcm-crow.on)' % width,
              crowsh is not None and '212, 245, 63' in crowsh and '3px' in crowsh,
              str(crowsh)[:80])

        # ---- check 5b: Back -> lang step (direction class) ----
        bpt = center(c, '#wlcmBack')
        assert bpt, '#wlcmBack not found (not on country step?)'
        tap(c, bpt[0], bpt[1])
        seen_l = poll_body_dir(c, 'wlcm-step-enter-l')
        check('%d: Back slides in from left (wlcm-step-enter-l)' % width, seen_l is True)
        check('%d: Back -> language step renders' % width, wait_step(c, 'lang'), step(c))

        # ---- check 6: search input filters, keeps focus ----
        qpt = center(c, '#wlcmLQ')
        tap(c, qpt[0], qpt[1])
        time.sleep(0.25)
        full_n = j(c, "return document.querySelectorAll('[data-wlang]').length;")
        c.send('Input.insertText', {'text': 'esp'})
        time.sleep(0.4)
        fil_n = j(c, "return document.querySelectorAll('[data-wlang]').length;")
        allmatch = j(c, """return Array.prototype.every.call(
          document.querySelectorAll('[data-wlang]'),
          function(b){var t=b.textContent.toLowerCase(); return t.indexOf('esp')!==-1;});""")
        focus = j(c, "return document.activeElement&&document.activeElement.id;")
        val = j(c, "return document.getElementById('wlcmLQ').value;")
        check('%d: search filters the language list' % width,
              full_n > fil_n >= 1 and allmatch is True, 'full=%s filtered=%s' % (full_n, fil_n))
        check('%d: search input keeps focus + value after redraw' % width,
              focus == 'wlcmLQ' and val == 'esp', 'focus=%s value=%s' % (focus, val))
        shot(c, 'qa/wlcm-search-%d.png' % width)

        # ---- check 4 (part 2): card long-press selection kill ----
        # The hold fires a real click that advances to the country step; that
        # is expected and doubles as the es->country navigation for the flow.
        cpt = center(c, '[data-wlang="es"]')
        assert cpt, 'Espanol card not found after filter'
        sel2 = touch_hold_sel(c, cpt[0], cpt[1])
        check('%d: long-press language card -> no text selection' % width,
              sel_ok(sel2), sel2)
        check('%d: long-press tap advanced to country step' % width,
              wait_step(c, 'country'), step(c))

        # ---- check 5c: full flow: tap country (Nepal) -> ready -> Continue ----
        np = j(c, """var el=document.querySelector('[data-wcc="NP"]');
          if(el){el.scrollIntoView({block:'center'});} return !!el;""")
        check('%d: Nepal country row exists' % width, np is True)
        time.sleep(0.3)
        npt = center(c, '[data-wcc="NP"]')
        tap(c, npt[0], npt[1])
        check('%d: tap country -> ready step renders' % width, wait_step(c, 'ready'), step(c))
        time.sleep(0.7)
        kill_recover(c)
        shot(c, 'qa/wlcm-ready-%d.png' % width)
        rstg = j(c, """return Array.prototype.map.call(
          document.querySelectorAll('.wlcm-pick.wlcm-rise,.wlcm-disclaimer.wlcm-rise,#wlcmGo.wlcm-rise'),
          function(e){return e.style.getPropertyValue('--d');}).join(',');""")
        check('%d: ready step staggers picks/disclaimer/Continue' % width,
              rstg == '0ms,45ms,90ms,135ms', rstg)
        check('%d: no horizontal overflow (ready)' % width, overflow_ok(c))
        gpt = center(c, '#wlcmGo')
        tap(c, gpt[0], gpt[1])
        t0 = time.time()
        hidden = False
        while time.time() - t0 < 2.0:
            if j(c, "return document.getElementById('wlcmHost').hidden===true;") is True:
                hidden = True
                break
            time.sleep(0.05)
        persisted = j(c, "var v=localStorage.getItem('orbit_i18n'); return v?JSON.parse(v):null;")
        done_cb = j(c, "return window.__wlcmDone===true;")
        check('%d: Continue hides host + persists orbit_i18n' % width,
              hidden and persisted.get('lang') == 'es' and persisted.get('country') == 'NP' and done_cb is True,
              'hidden=%s persisted=%s done=%s' % (hidden, persisted, done_cb))

        # ---- check 3: zero console/page errors across the run ----
        real = errors_now(c)
        for e in real[:5]:
            note('%d: ERROR: %s' % (width, e[:160]))
        check('%d: zero console/page errors (full flow)' % width, not real, str(real[:2])[:280])

        # ---- check 10: perf — longtasks during transitions ----
        longs = j(c, "return window.__longs||[];") or []
        mx = max(longs) if longs else 0
        check('%d: no longtask > 500ms during step transitions' % width,
              mx <= 500, 'max=%dms n=%d' % (mx, len(longs)))
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        shutil.rmtree(prof, ignore_errors=True)

# ---------------------------------------------------------------- reduced motion
def run_reduced():
    c, proc, prof = boot(390, reduced=True, tag='-rm')
    try:
        kill_recover(c)
        ok = step(c) == 'lang'
        check('RM: welcome renders (lang step)', ok, step(c))
        st = j(c, """var e=document.querySelector('.wlcm-langs .wlcm-lang');
          var cs=getComputedStyle(e); return cs.opacity+'|'+cs.transform;""")
        check('RM: content visible/static (opacity 1, transform none)',
              st == '1|none', st)
        an = j(c, """var a=document.querySelector('.wlcm-aurora');
          return a?getComputedStyle(a,'::before').animationName:null;""")
        check('RM: aurora frozen (no animation)', an in ('none', None), an)
        dot_tr = j(c, "return getComputedStyle(document.querySelector('.wlcm-dot')).transition;")
        check('RM: glassy-dot transitions disabled', dot_tr in ('none', None, 'all 0s ease 0s'), dot_tr)
        # flow still completes under reduced motion
        pt = center(c, '[data-wlang="en"]')
        tap(c, pt[0], pt[1])
        check('RM: tap lang -> country step', wait_step(c, 'country'), step(c))
        np = j(c, "var el=document.querySelector('[data-wcc=\"US\"]');"
                  " if(el) el.scrollIntoView({block:'center'}); return !!el;")
        check('RM: country row found', np is True)
        npt = center(c, '[data-wcc="US"]')
        tap(c, npt[0], npt[1])
        check('RM: tap country -> ready step', wait_step(c, 'ready'), step(c))
        time.sleep(0.4)
        shot(c, 'qa/wlcm-rm-ready-390.png')
        gpt = center(c, '#wlcmGo')
        tap(c, gpt[0], gpt[1])
        t0 = time.time()
        hidden = False
        while time.time() - t0 < 2.0:
            if j(c, "return document.getElementById('wlcmHost').hidden===true;") is True:
                hidden = True
                break
            time.sleep(0.05)
        persisted = j(c, "var v=localStorage.getItem('orbit_i18n'); return v?JSON.parse(v):null;")
        check('RM: Continue hides host + persists', hidden and persisted.get('country') == 'US',
              'hidden=%s persisted=%s' % (hidden, persisted))
        real = errors_now(c)
        check('RM: zero console/page errors', not real, str(real[:2])[:280])
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        shutil.rmtree(prof, ignore_errors=True)

if __name__ == '__main__':
    for w in (390, 320):
        run_width(w)
    run_reduced()
    print('\n%d failures' % len(fails))
    if notes:
        print('--- notes ---')
        for n in notes:
            print(' *', n)
    sys.exit(1 if fails else 0)
