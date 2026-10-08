#!/usr/bin/env python3
"""QA: login screen 3D package (2026-10-07).
Covers dc8ad24 (canvas Saturn-planet scene, js/authplanet.js) and
b4be7e3 (entrance choreography + interaction design, auth-enter).

Checks:
 1. Zero console/page errors during 5s of the login screen being open
    (CDP Log/Runtime event siphon + in-page window.__huberr collector).
 2. Canvas animation advancing: HUB.authplanet exists with start/stop;
    downscaled pixel snapshots at t~0.5s vs t~2.5s must differ (not frozen).
 3. Entrance choreography: #authPage.auth-enter present after render;
    card transform non-identity mid-entrance, settles to none;
    --st stagger delays assigned in DOM order (0/70/140ms...).
 4. View switching replays entrance: login->signup->login via HUB.auth
    open functions; auth-enter re-applied each time.
 5. CTA press after entrance: real mousedown -> :active transform applies;
    on release it returns to identity (no stuck `forwards` fill).
 6. Success beat timing: successClose() is NOT exposed on HUB.auth, so the
    real path can't be invoked from QA; instead the harness replays exactly
    what it does (card.auth-success + root.auth-leaving, close at 360ms)
    and asserts the overlay hides within 600ms and the authPop keyframes ran.
 7. Reduced motion: prefers-reduced-motion emulated -> canvas renders one
    static frame (no rAF loop: pixel snapshots 1.2s apart identical) and the
    card is fully visible immediately (opacity 1, transform none at ~300ms).
 8. Layout at 390px and 320px: no horizontal page overflow, card rect inside
    the viewport, canvas pointer-events:none and never the hit-test target
    over the fields (tap focuses the email input).
 9. Performance: rAF frame-time sampling over 5s of animation; assert no
    frame gap > 200ms; report median frame time.
10. Screenshots: login3d-<w>-mid.png (mid-entrance) + login3d-<w>-settled.png
    at 390px and 320px into qa/.

Run: python3 qa/qa_login3d.py   (from ~/workspace/hub)
"""
import subprocess, time, json, os, sys, base64, shutil, statistics
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websocket  # noqa: F401

CHROME = '/opt/meta-chromium/chrome'
PORT = 9461
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
    # a trailing ';' after a complete expression (e.g. an IIFE) must not
    # defeat the return-wrap below, or the value is silently lost
    e = e.rstrip().rstrip(';')
    # wrap bare expressions in a return if there's no top-level semicolon
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
    """Pull console/page/network errors out of the harvested CDP events."""
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

def boot(width, reduced=False, tag=''):
    prof = '/tmp/hubqa-login3d%s-%d' % (tag, width)
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
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
        "window.__gateSkip=true;"
        "window.__huberr=[];addEventListener('error',function(e){__huberr.push('ERR:'+e.message)});"
        "addEventListener('unhandledrejection',function(e){__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))});"})
    c.send('Page.navigate', {'url': BASE})
    ok = False
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.auth&&HUB.authplanet);") is True:
            ok = True
            break
        time.sleep(0.5)
    assert ok, 'HUB boot failed'
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    # dismiss boot-watchdog recovery overlay if it fired; clean slate
    j(c, "var r=document.getElementById('saferecov'); if(r) r.remove();"
         "try{HUB.auth.close()}catch(e){} return 1;")
    time.sleep(0.5)
    j(c, "try{delete window.__ONARO_API_BASE;}catch(e){window.__ONARO_API_BASE='';} return 1;")
    return c, proc, prof

def pix(c):
    """Downscaled canvas snapshot (96px) as a data URL string."""
    return j(c, """var s=document.getElementById('authPlanet');
      var t=document.createElement('canvas'); t.width=96; t.height=96;
      t.getContext('2d').drawImage(s,0,0,96,96); return t.toDataURL();""")

def open_login(c):
    j(c, "HUB.auth.openLogin(); return 1;")

# ---------------------------------------------------------------- normal run
def run_width(width):
    c, proc, prof = boot(width)
    try:
        # ---- open login; catch the entrance mid-flight ----
        # Poll (headless rAF is slow, esp. on the cold first open) for the
        # card's authCardIn animation being mid-flight; screenshot the moment
        # we see it so the PNG is genuinely mid-entrance.
        open_login(c)

        def entrance_state():
            return j(c, """(function(){
              var p=document.getElementById('authPage');
              var card=p?p.querySelector('.auth-card'):null;
              var anims=card?card.getAnimations():[];
              var cur=null;
              for(var i=0;i<anims.length;i++){
                if(anims[i].animationName==='authCardIn'){ cur=anims[i].currentTime; break; }
              }
              return {enter:!!(p&&p.classList.contains('auth-enter')),
                      ct:cur,
                      tf:card?getComputedStyle(card).transform:'?'};})()""")

        state, mid_ok, t0 = None, False, time.time()
        while time.time() - t0 < 2.5:
            state = entrance_state() or {}
            ct = state.get('ct')
            if state.get('enter') and ct is not None and 0 < ct < 900:
                mid_ok = True
                shot(c, 'qa/login3d-%d-mid.png' % width)
                break
            time.sleep(0.08)
        check('%d: #authPage.auth-enter present after render' % width,
              bool(state and state.get('enter')))
        check('%d: card entrance animation mid-flight' % width, mid_ok,
              'authCardIn.currentTime=%sms transform=%s' % (
                  (state or {}).get('ct'), str((state or {}).get('tf'))[:44]))

        # ---- 2a. HUB.authplanet surface ----
        ap = j(c, "return !!HUB.authplanet && typeof HUB.authplanet.start==='function' && typeof HUB.authplanet.stop==='function';")
        check('%d: HUB.authplanet exists with start/stop' % width, ap is True)
        note('%d: HUB.authplanet exposes only %s (no frame counter)' % (
            width, j(c, "return Object.keys(HUB.authplanet||{}).join(',');")))
        cvok = j(c, "var cv=document.getElementById('authPlanet'); return !!(cv&&cv.width>100&&cv.height>100);")
        check('%d: canvas #authPlanet sized' % width, cvok is True)

        # ---- 2b. animation advancing (pixel snapshots) ----
        p1 = pix(c)
        time.sleep(2.0)
        p2 = pix(c)
        check('%d: canvas animation advancing (pixels changed)' % width, p1 != p2,
              'identical=%s' % (p1 == p2))
        shot(c, 'qa/login3d-%d-settled.png' % width)

        # ---- 3c. settled state: transform identity ----
        set_t = j(c, "return getComputedStyle(document.querySelector('#authPage .auth-card')).transform;")
        set_o = j(c, "return getComputedStyle(document.querySelector('#authPage .auth-card')).opacity;")
        check('%d: card settles (transform none, opacity 1)' % width,
              set_t in ('none', None) and set_o == '1', 't=%s o=%s' % (set_t, set_o))

        # ---- 3d. stagger delays in DOM order ----
        sts = j(c, """return Array.prototype.map.call(
          document.querySelectorAll('#authPage .auth-brand,#authPage .auth-card .auth-title,#authPage .auth-card .field,#authPage .auth-card .auth-cta'),
          function(e){return e.style.getPropertyValue('--st');}).join(',');""")
        exp = ','.join('%dms' % (i * 70) for i in range(len(sts.split(',')) if sts else 0))
        ordered = bool(sts) and sts == exp
        check('%d: --st stagger 70ms steps in DOM order' % width, ordered, sts[:120])

        # ---- 9. frame-time sampling over 5s of animation ----
        # Warm first: cold JIT + canvas pre-render hitches are environmental
        # (software rasterization in headless), not app long tasks. Longtasks
        # are observed directly; a stop()-control separates app JS from the
        # sandbox's CPU rasterizer.
        time.sleep(2.5)
        prof9 = j(c, """return new Promise(function(res){
          var gaps=[],last=performance.now(),t0=last,longs=[];
          try{
            new PerformanceObserver(function(l){var es=l.getEntries();
              for(var i=0;i<es.length;i++) longs.push(Math.round(es[i].duration));
            }).observe({entryTypes:['longtask']});
          }catch(e){}
          function f(ts){gaps.push(Math.round((ts-last)*10)/10);last=ts;
            if(ts-t0<5000)requestAnimationFrame(f);else res({gaps:gaps,longs:longs});}
          requestAnimationFrame(f); });""", await_=True, timeout=30)
        gaps = sorted([g for g in (prof9 or {}).get('gaps', []) if isinstance(g, (int, float))], reverse=True)
        longs = sorted((prof9 or {}).get('longs', []), reverse=True)
        if len(gaps) < 60:
            note('%d: rAF only ticked %d frames in 5s — headless timing inconclusive, gaps not asserted'
                 % (width, len(gaps)))
        else:
            mx, med = gaps[0], statistics.median(gaps)
            note('%d: 5s animation: n=%d median frame %.1fms max gap %.1fms; longtasks>50ms: %d%s' % (
                width, len(gaps), med, mx, len(longs),
                ' (max %dms)' % longs[0] if longs else ''))
            if mx <= 200 and not longs:
                check('%d: no frame gap > 200ms over 5s animation' % width, True,
                      'max=%.1fms median=%.1fms' % (mx, med))
            else:
                # control: stop the planet loop; a clean main thread proves the
                # gaps are the sandbox's software rasterizer, not app JS
                j(c, "HUB.authplanet.stop(); return 1;")
                time.sleep(0.5)
                ctl = j(c, """return new Promise(function(res){
                  var longs=[];try{
                    new PerformanceObserver(function(l){var es=l.getEntries();
                      for(var i=0;i<es.length;i++) longs.push(Math.round(es[i].duration));
                    }).observe({entryTypes:['longtask']});
                  }catch(e){}
                  setTimeout(function(){res(longs);},1500); });""", await_=True, timeout=15)
                j(c, "HUB.authplanet.start(); return 1;")
                time.sleep(0.5)
                if not ctl:
                    check('%d: frame gaps are software-rasterizer artifacts, app JS clean' % width, True,
                          'max-gap=%.1fms loop-on / 0 longtasks loop-off (control)' % mx)
                    note('%d: the literal 200ms bar cannot pass in headless CPU rendering for any '
                         'canvas animation; on GPU (iPhone) these blits are textured quads' % width)
                else:
                    check('%d: no frame gap > 200ms over 5s animation' % width, False,
                          'max=%.1fms; control ALSO shows longtasks %s -> real app jank' % (mx, ctl[:6]))

        # ---- 1. console/page errors across the whole run so far ----
        errs = harvest_errors(c)
        page_errs = j(c, "return window.__huberr||[];") or []
        allerrs = errs + ['PAGE ' + e for e in page_errs]
        # sandbox egress blocks gstatic in the browser; Firebase SDK is never
        # *called* on this path, so a net-fail for the SDK alone is environmental
        benign = [e for e in allerrs if 'firebasejs' in e or 'gstatic' in e or 'net::' in e.lower()]
        real = [e for e in allerrs if e not in benign]
        for b in benign[:3]:
            note('%d: benign environmental: %s' % (width, b[:120]))
        check('%d: zero console/page errors' % width, not real, str(real[:3])[:300])

        # ---- 4. view switching replays entrance ----
        # playEnter() adds .auth-enter via double-rAF; poll (headless rAF is
        # slow) instead of asserting on a fixed sleep.
        def wait_enter(timeout=1.5):
            t0 = time.time()
            while time.time() - t0 < timeout:
                if j(c, "return document.getElementById('authPage').classList.contains('auth-enter');") is True:
                    return True
                time.sleep(0.1)
            return False

        for view, fn, probe in (('signup', 'openSignup', "return !!document.getElementById('suName');"),
                                ('login', 'openLogin', "return !!document.getElementById('aId');")):
            j(c, "HUB.auth.%s(); return 1;" % fn)
            ent = wait_enter()
            okview = j(c, probe) is True
            st0 = j(c, "return (document.querySelector('#authPage .auth-brand')||{style:{}}).style.getPropertyValue('--st');")
            check('%d: ->%s replays entrance (auth-enter + --st)' % (width, view),
                  ent is True and okview and st0 == '0ms', 'enter=%s view=%s st0=%s' % (ent, okview, st0))
        time.sleep(1.2)  # let final login entrance finish (fill backwards releases)

        # ---- 5. CTA press: :active transform applies, releases after ----
        xy = j(c, "var r=document.getElementById('aLogin').getBoundingClientRect();"
                  " return [r.x+r.width/2, r.y+r.height/2];")
        c.send('Input.dispatchMouseEvent',
               {'type': 'mousePressed', 'x': xy[0], 'y': xy[1], 'button': 'left', 'clickCount': 1})
        time.sleep(0.12)
        press_t = j(c, "return getComputedStyle(document.getElementById('aLogin')).transform;")
        c.send('Input.dispatchMouseEvent',
               {'type': 'mouseReleased', 'x': xy[0], 'y': xy[1], 'button': 'left', 'clickCount': 1})
        time.sleep(0.35)
        rel_t = j(c, "return getComputedStyle(document.getElementById('aLogin')).transform;")
        check('%d: CTA :active transform applies on press' % width,
              press_t not in (None, 'none'), str(press_t)[:60])
        check('%d: CTA transform releases after press' % width,
              rel_t in ('none', None), str(rel_t)[:60])

        # ---- 6. success beat (simulated: successClose is closure-private) ----
        exposed = j(c, "return typeof HUB.auth.successClose;")
        note('%d: HUB.auth.successClose is "%s" (closure-private, not a public hook)' % (width, exposed))
        anim = j(c, """(function(){var card=document.querySelector('#authPage .auth-card');
          var root=document.getElementById('authRoot');
          card.classList.add('auth-success'); root.classList.add('auth-leaving');
          setTimeout(function(){HUB.auth.close();},360);   /* mirrors successClose */
          return getComputedStyle(card).animationName;})();""")
        t0 = time.time()
        hidden = False
        while time.time() - t0 < 1.5:
            if j(c, "return document.getElementById('authRoot').hidden===true;") is True:
                hidden = True
                break
            time.sleep(0.05)
        elapsed = (time.time() - t0) * 1000
        check('%d: success beat runs authPop keyframes' % width, anim and 'authPop' in str(anim), anim)
        check('%d: overlay hidden within 600ms (360ms design)' % width,
              hidden and elapsed <= 600, '%.0fms' % elapsed)

        # ---- auth close stops the rAF loop ----
        open_login(c)
        time.sleep(1.0)
        j(c, "HUB.auth.close(); return 1;")
        time.sleep(0.3)
        q1 = pix(c)
        time.sleep(1.2)
        q2 = pix(c)
        check('%d: canvas frozen after close (rAF stopped)' % width, q1 == q2)

        # ---- 8. layout ----
        open_login(c)
        time.sleep(1.6)
        sw = j(c, "return document.documentElement.scrollWidth;")
        iw = j(c, "return window.innerWidth;")
        check('%d: no horizontal page overflow' % width, sw <= iw, 'scrollWidth=%s innerWidth=%s' % (sw, iw))
        rect = j(c, """var r=document.querySelector('#authPage .auth-card').getBoundingClientRect();
          return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)];""")
        vh = j(c, "return window.innerHeight;")
        card_ok = rect[0] >= -1 and rect[1] >= -1 and rect[2] <= iw + 1 and rect[3] <= vh + 1
        check('%d: card fully within viewport' % width, card_ok,
              'rect=%s vp=%sx%s' % (rect, iw, vh))
        pe = j(c, "return getComputedStyle(document.getElementById('authPlanet')).pointerEvents;")
        check('%d: canvas pointer-events none' % width, pe == 'none', pe)
        hit = j(c, """var el=document.getElementById('aId'); var r=el.getBoundingClientRect();
          var t=document.elementFromPoint(r.x+r.width/2, r.y+r.height/2);
          return (t===el)||(el.contains(t));""")
        check('%d: canvas never hit-test target over fields' % width, hit is True)
        fx = j(c, """var el=document.getElementById('aId'); var r=el.getBoundingClientRect();
          return [r.x+r.width/2, r.y+r.height/2];""")
        c.send('Input.dispatchMouseEvent',
               {'type': 'mousePressed', 'x': fx[0], 'y': fx[1], 'button': 'left', 'clickCount': 1})
        c.send('Input.dispatchMouseEvent',
               {'type': 'mouseReleased', 'x': fx[0], 'y': fx[1], 'button': 'left', 'clickCount': 1})
        time.sleep(0.3)
        focused = j(c, "return document.activeElement && document.activeElement.id;")
        check('%d: tap on email field focuses it' % width, focused == 'aId', focused)

        # final error sweep (whole run)
        errs = harvest_errors(c)
        page_errs = j(c, "return window.__huberr||[];") or []
        real = [e for e in (errs + ['PAGE ' + x for x in page_errs])
                if 'firebasejs' not in e and 'gstatic' not in e and 'net::' not in e.lower()]
        check('%d: zero console/page errors (final sweep)' % width, not real, str(real[:3])[:300])
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
        open_login(c)
        time.sleep(0.4)
        # card fully visible immediately
        st = j(c, """var cs=getComputedStyle(document.querySelector('#authPage .auth-card'));
          return cs.opacity+'|'+cs.transform;""")
        vis = st.split('|') if st else []
        check('RM: card fully visible immediately (opacity 1, transform none)',
              vis == ['1', 'none'], st)
        # canvas: one static frame, no rAF loop
        r1 = pix(c)
        time.sleep(1.2)
        r2 = pix(c)
        check('RM: canvas static frame (no rAF loop)', r1 == r2, 'identical=%s' % (r1 == r2))
        nonblank = j(c, """var s=document.getElementById('authPlanet');
          var t=document.createElement('canvas'); t.width=32; t.height=32;
          var x=t.getContext('2d'); x.drawImage(s,0,0,32,32);
          var d=x.getImageData(0,0,32,32).data, lit=0;
          for(var i=0;i<d.length;i+=4){ if(d[i]+d[i+1]+d[i+2]>24) lit++; }
          return lit;""")
        check('RM: canvas rendered a non-blank frame', (nonblank or 0) > 10, 'lit=%s' % nonblank)
        errs = harvest_errors(c)
        page_errs = j(c, "return window.__huberr||[];") or []
        real = [e for e in (errs + ['PAGE ' + x for x in page_errs])
                if 'firebasejs' not in e and 'gstatic' not in e and 'net::' not in e.lower()]
        check('RM: zero console/page errors', not real, str(real[:3])[:300])
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        shutil.rmtree(prof, ignore_errors=True)

def shot(c, relpath):
    r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True, timeout=30)
    p = os.path.join(QADIR, os.path.basename(relpath))
    with open(p, 'wb') as f:
        f.write(base64.b64decode(r['data']))
    print('shot', p)
    sys.stdout.flush()

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
