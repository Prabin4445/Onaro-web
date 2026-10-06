#!/usr/bin/env python3
"""HUB QA: Ask Onaro v2 (js/ai.js) — full-app guide KB + step walker.
Fresh profile /tmp/hubqa-ask (wiped), file:// load, 390px, dark + light + 320px.

Phases:
  A. sheet opens from the pill; first chip is the new "Help me use Onaro"
  B. "help" -> full guide index, 14 topic rows
  C. topic recognition for all 14 topics (natural queries)
  D. page-specific help on Daily tab -> 4 daily rows only
  E. step walker: guide -> walk -> next/back -> done toast
  F. "take me there" navigates (groups tab); professors opens profroot
  G. related chips ask a follow-up question
  H. live-data intents still work (money/jobs/moving/roommate)
  I. unknown fallback -> guide index button
  J. real German via setLang('de') + lazy de.json kh matches bundle
  K. screenshots dark + light; 320px no-overflow
  L. zero console errors
"""
import json, subprocess, time, urllib.request, os, shutil, sys, base64
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9447
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-ask'
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
JS = "(function(){%s})()"
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)

TOPICS = ['rate','addprof','groups','chat','calls','market','gym','calc','gpa','capsule','badges','verify','settings','events']
QUERIES = {
 'rate':'how do i rate a professor','addprof':'my professor is missing, add them',
 'groups':'how do i join a group','chat':'how does group chat work','calls':'how do i start a group call',
 'market':'how do i sell my textbook','gym':'gym workout calories','calc':'where is the calculator',
 'gpa':'how do i calculate my gpa','capsule':'how do i make a time capsule','badges':'how do i earn badges',
 'verify':'how do i verify my account','settings':'change language settings','events':'how do i find events'}

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12)
        self.id = 0; self.events = []
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        t = time.time()
        while time.time() - t < 15:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if 'method' in msg and 'id' not in msg:
                self.events.append(msg); continue
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]
    def shot(self, name):
        r = self.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 82, 'fromSurface': True})
        with open(os.path.join(SHOTDIR, name), 'wb') as f: f.write(base64.b64decode(r['data']))
        print('SHOT', name)

def t0(): return time.time()
def js_wait(c, expr, timeout=12):
    t = time.time()
    while time.time() - t < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False
def disarm_gate(c):
    # Page.reload() discards the JS context, so a disarm issued right after
    # reload can land in the dead context — set the flag in the LIVE context
    # and close any auth overlay that already opened.
    # NOTE: the JS% IIFE wrapper is REQUIRED — a bare "return 1" at the top
    # level of Runtime.evaluate is a syntax error and the whole disarm
    # silently no-ops (caught 2026-09-24: gate kept re-opening).
    c.js(JS % ("window.__gateSkip=true; try{if(HUB.auth&&HUB.auth.close){"
         "var a=document.querySelector('.authroot'); if(a&&!a.hidden) HUB.auth.close();}}catch(e){} return 1"))

def boot(c, dark=True):
    ok = js_wait(c, "return !document.getElementById('splash')", 25)
    note(ok, 'splash dismissed')
    c.js(JS % ("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
              "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus';"
              "s.prefs.dark=%s; HUB.store.save(); return 1" % ('true' if dark else 'false')))
    c.send('Page.reload')
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && !!window.HUB && !!HUB.ai", 25)
    note(ok, 'clean boot after seed')
    disarm_gate(c)
    time.sleep(0.8)
    disarm_gate(c)  # second pass: the 250ms poller may have fired between
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
    time.sleep(0.5)
    v, _ = c.js(JS % "return !!document.querySelector('.authroot:not([hidden])')")
    note(not v, 'no auth overlay (gate disarmed)')

def ask(c, q):
    """Type into the Ask sheet input and send; returns True when a new card lands."""
    before, _ = c.js(JS % "return document.querySelectorAll('#askSheetResults .card').length")
    c.js(JS % ("var i=document.getElementById('askSheetInput'); i.value=%s;"
              "i.dispatchEvent(new Event('input',{bubbles:true})); return 1" % json.dumps(q)))
    c.js(JS % "document.getElementById('askSheetSend').click(); return 1")
    ok = js_wait(c, "return document.querySelectorAll('#askSheetResults .card').length>%d" % (before or 0), 8)
    return ok

def first_card_text(c):
    v, _ = c.js(JS % "var c0=document.querySelector('#askSheetResults .card'); return c0?c0.textContent:''")
    return v or ''

def click_next(c):
    c.js(JS % "var b=[...document.querySelectorAll('#askSheetResults .card [data-walkgo]')].find(x=>x.textContent.indexOf('Next')>=0); if(b) b.click(); return 1")
    time.sleep(0.3)

def open_sheet(c):
    c.js(JS % "document.getElementById('askPillMain').click(); return 1")
    return js_wait(c, "return !!document.getElementById('askSheetInput')", 8)

def phaseA(c):
    note(open_sheet(c), 'ask sheet opens from pill')
    v, _ = c.js(JS % "var cs=[...document.querySelectorAll('.askchip')].map(x=>x.textContent); return cs")
    note(v and v[0] == 'Help me use Onaro', 'first chip is Help me use Onaro', str(v))

def phaseB(c):
    note(ask(c, 'help'), 'ask "help"')
    v, _ = c.js(JS % "return document.querySelectorAll('#askSheetResults .card')[0].querySelectorAll('.askrow').length")
    note(v == 14, 'guide index has 14 topic rows', str(v))
    v, _ = c.js(JS % "var c0=document.querySelector('#askSheetResults .card'); return c0.innerHTML.indexOf('asksteps')>=0")
    note(not v, 'index has no step list (rows only)')

def phaseC(c):
    allok = True
    for tid in TOPICS:
        ok = ask(c, QUERIES[tid])
        title, _ = c.js(JS % "return HUB.i18n.t('askg.%s.t')" % tid)
        txt = first_card_text(c)
        hit = ok and title and (title in txt)
        if not hit: allok = False; print('  topic miss:', tid, QUERIES[tid], '->', title)
    note(allok, 'all 14 topics recognized with correct titles')

def phaseD(c):
    c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(0.5)
    note(ask(c, 'help with this page'), 'ask "help with this page" on Daily')
    v, _ = c.js(JS % "return [...document.querySelectorAll('#askSheetResults .card')[0].querySelectorAll('.askrow b')].map(x=>x.textContent)")
    titles = set(v or [])
    exp = set()
    for tid in ['events', 'gym', 'calc', 'capsule']:
        t2, _ = c.js(JS % "return HUB.i18n.t('askg.%s.t')" % tid)
        exp.add(t2)
    note(titles == exp, 'daily page help shows only the 4 daily topics', str(sorted(titles)))
    c.js(JS % "HUB.showTab('home'); return 1"); time.sleep(0.4)

def phaseE(c):
    note(ask(c, 'how do i rate a professor'), 'ask rate-professor')
    c.js(JS % "document.querySelector('#askSheetResults .card [data-walk]').click(); return 1")
    v = first_card_text(c)
    note('Step 1 of 5' in v, 'walker starts at Step 1 of 5')
    c.shot('ask-walker-dark.jpg')
    click_next(c)
    v = first_card_text(c)
    note('Step 2 of 5' in v, 'walker Next -> Step 2 of 5 (rebind works)')
    dots, _ = c.js(JS % "return document.querySelectorAll('#askSheetResults .card .askdot.on').length")
    note(dots == 1, 'one active progress dot')
    click_next(c)
    v = first_card_text(c)
    note('Step 3 of 5' in v, 'walker Next again -> Step 3 of 5')
    c.js(JS % "var b=[...document.querySelectorAll('#askSheetResults .card [data-walkgo]')].find(x=>x.textContent.indexOf('Back')>=0); if(b) b.click(); return 1")
    time.sleep(0.3)
    v = first_card_text(c)
    note('Step 2 of 5' in v, 'walker Back -> Step 2 of 5')
    for _ in range(3):
        click_next(c)
    v, _ = c.js(JS % "var c0=document.querySelector('#askSheetResults .card'); return {t:c0.textContent, done:!!c0.querySelector('[data-walkdone]')}")
    note(v and v.get('done') and 'Step 5 of 5' in v.get('t',''), 'walker reaches Step 5 with Done button')
    c.js(JS % "var h=document.getElementById('toastHost'); if(h) h.innerHTML=''; document.querySelector('#askSheetResults .card [data-walkdone]').click(); return 1")
    time.sleep(0.4)
    v, _ = c.js(JS % "return document.getElementById('toastHost').textContent")
    note('Done!' in (v or ''), 'Done -> celebration toast', (v or '')[:40])

def phaseF(c):
    note(ask(c, 'how do i join a group'), 'ask join-group')
    c.js(JS % "document.querySelector('#askSheetResults .card [data-takeme]').click(); return 1")
    time.sleep(0.6)
    v, _ = c.js(JS % "var a=document.querySelector('#tabbar .tab.active'); return a?a.dataset.tab:''")
    note(v == 'groups', 'take me there -> groups tab', v)
    note(ask(c, 'how do i rate a professor'), 'ask rate-professor again')
    c.js(JS % ("var o=HUB.professors.open; HUB.professors.open=function(x){window.__profOpened=true; return o.apply(this,arguments)};"
               "document.querySelector('#askSheetResults .card [data-takeme]').click(); return 1"))
    time.sleep(0.8)
    v, _ = c.js(JS % "return !!window.__profOpened && !!document.querySelector('.profroot')")
    note(bool(v), 'take me there on professor guide opens Professors')
    c.js(JS % "if(HUB.professors&&HUB.professors.close) HUB.professors.close(); HUB.showTab('home'); return 1")
    time.sleep(0.4)

def phaseG(c):
    note(ask(c, 'how do i rate a professor'), 'ask rate-professor (related)')
    n0, _ = c.js(JS % "return document.querySelectorAll('#askSheetResults .card').length")
    c.js(JS % "document.querySelector('#askSheetResults .card [data-askq]').click(); return 1")
    time.sleep(0.4)
    n1, _ = c.js(JS % "return document.querySelectorAll('#askSheetResults .card').length")
    title, _ = c.js(JS % "return HUB.i18n.t('askg.addprof.t')")
    html = first_card_text(c)
    note(n1 == n0 + 1 and title in html, 'related chip asks follow-up (addprof card)', title)

def phaseH(c):
    for q, key in [('who owes me money','ai.money.title'),('any jobs','ai.jobs.title'),
                   ('help me move','ai.mv.title'),('roommate bills','ai.room.title')]:
        ok = ask(c, q)
        title, _ = c.js(JS % "return HUB.i18n.t('%s')" % key)
        html = first_card_text(c)
        note(ok and title in html, 'live-data intent: ' + q, title)

def phaseI(c):
    note(ask(c, 'xqzwkj vbnm'), 'ask gibberish')
    v, _ = c.js(JS % "var c0=document.querySelector('#askSheetResults .card'); return !!c0.querySelector('[data-askindex]')")
    note(bool(v), 'unknown fallback offers full guide')
    c.js(JS % "document.querySelector('#askSheetResults .card [data-askindex]').click(); return 1")
    time.sleep(0.4)
    n, _ = c.js(JS % "return document.querySelector('#askSheetResults .card').querySelectorAll('.askrow').length")
    note(n == 14, 'guide-index button -> 14 rows', str(n))
    c.shot('ask-guide-dark.jpg')

def phaseJ(c):
    # German — REAL locale. setLang returns undefined for lazy locales (the
    # async load applies it), so assert on getLang() + dict identity instead.
    c.js(JS % "HUB.i18n.setLang('de'); return 1")
    ok = js_wait(c, "return HUB.i18n.getLang()==='de' && HUB.i18n._dict('de')!==HUB.i18n._dict('en')", 15)
    note(ok, "setLang(de) loads a real dict (getLang + identity)")
    ident, _ = c.js(JS % "return HUB.i18n._dict('de')!==HUB.i18n._dict('en')")
    note(bool(ident), 'de dict is a real object, not the en fallback')
    t1, _ = c.js(JS % "return HUB.i18n.t('ask.chip.help')")
    note(t1 == 'Hilf mir, Onaro zu nutzen', 'ask.chip.help translated in de', t1)
    t2, _ = c.js(JS % "return HUB.i18n.t('askg.rate.s1')")
    note(t2 and t2 != 'askg.rate.s1', 'askg.rate.s1 translated in de', (t2 or '')[:50])
    t3, _ = c.js(JS % "return HUB.i18n.t('prof.cleanRule')")
    note(t3 and ('beleidigend' in t3.lower() or 'schimpf' in t3.lower()), 'prof.cleanRule real German in de', (t3 or '')[:60])
    c.js(JS % "HUB.i18n.setLang('en'); return 1")
    ok = js_wait(c, "return HUB.i18n.getLang()==='en'", 10)
    note(ok, 'back to en')

def phaseK(c):
    c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); return 1")
    c.send('Page.reload'); disarm_gate(c)
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash')", 25)
    note(ok, 'light-mode reload')
    disarm_gate(c); time.sleep(0.4)
    note(open_sheet(c), 'sheet opens (light)')
    ask(c, 'help')
    c.shot('ask-guide-light.jpg')
    note(ask(c, 'how do i earn badges'), 'ask badges (light)')
    c.js(JS % "document.querySelector('#askSheetResults .card [data-walk]').click(); return 1")
    time.sleep(0.3)
    c.shot('ask-walker-light.jpg')
    # 320px: no horizontal overflow
    c.send('Emulation.setDeviceMetricsOverride', {'width': 320, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.reload'); disarm_gate(c)
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash')", 25)
    note(ok, '320px reload')
    disarm_gate(c); time.sleep(0.4)
    note(open_sheet(c), 'sheet opens (320px)')
    ask(c, 'how do i rate a professor')
    c.js(JS % "document.querySelector('#askSheetResults .card [data-walk]').click(); return 1")
    time.sleep(0.3)
    v, _ = c.js(JS % "return {sw:document.documentElement.scrollWidth, vw:window.innerWidth}")
    note(v and v['sw'] <= 321, 'no horizontal overflow at 320px', str(v))
    c.shot('ask-walker-320.jpg')

def collect_errors(c):
    bad = []
    for ev in c.events:
        m = ev.get('method', '')
        if m == 'Runtime.exceptionThrown':
            bad.append('EXC:' + json.dumps(ev['params'].get('exceptionDetails', {}).get('text', ''))[:140])
        elif m == 'Log.entryAdded' and ev['params']['entry'].get('level') == 'error':
            bad.append('LOG:' + ev['params']['entry'].get('text', '')[:140])
        elif m == 'Runtime.consoleAPICalled' and ev['params'].get('type') == 'error':
            bad.append('CON:' + json.dumps(ev['params'].get('args', []))[:140])
    v, _ = c.js("window.__huberr?window.__huberr.splice(0):[]")
    if v: bad.append('HOOK:' + json.dumps(v)[:400])
    return bad

def arm_hooks(c):
    c.js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*', '--window-size=390,844',
        '--user-data-dir=%s' % PROF, '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=5) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        arm_hooks(c)
        boot(c, dark=True)
        phaseA(c); phaseB(c); phaseC(c); phaseD(c); phaseE(c)
        phaseF(c); phaseG(c); phaseH(c); phaseI(c); phaseJ(c); phaseK(c)
        bad = collect_errors(c)
        note(not bad, 'zero console errors', '; '.join(bad)[:400])
        n = sum(checks); tot = len(checks)
        print('ASK QA: %d/%d' % (n, tot))
        sys.exit(0 if n == tot else 1)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
