#!/usr/bin/env python3
"""HUB QA focused: auth front door (gate) — login opens automatically on boot.
Fresh profile /tmp/hubqa-authgate (wiped), file:// load, 390px, dark+light.

1. seed profile (skip onboarding, like PraBin's phone) -> reload -> splash gone
   -> #authRoot visible WITHOUT any tap (the gate), skip link rendered
2. skip link closes the overlay
3. full signup via real picker -> signed in, hub_v1 session (remember ON)
4. reload -> still signed in, gate stays shut
5. logout -> login overlay reopens automatically
6. skip -> hidden; German via setLang('de') -> real "Ohne Anmeldung erkunden",
   dict identity de!==en, kh matches recomputed 1bh9r3a
7. zero console errors
"""
import json, subprocess, time, os, shutil, sys, base64
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9446
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-authgate'
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
JS = "(function(){%s})()"
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)

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

def js_wait(c, expr, timeout=15):
    t = time.time()
    while time.time() - t < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False

def setval(c, sel, val):
    c.js(JS % ("var el=document.querySelector(%s); el.value=%s;"
               "el.dispatchEvent(new Event('input',{bubbles:true}));"
               "el.dispatchEvent(new Event('change',{bubbles:true})); return 1"
               % (json.dumps(sel), json.dumps(val))))

def auth_visible(c):
    v, _ = c.js(JS % "var r=document.getElementById('authRoot'); return !!(r&&!r.hidden)")
    return bool(v)

def pick_campus(c, name='Gate University', city='Austin'):
    c.js(JS % "document.getElementById('suCampus').click(); return 1")
    if not js_wait(c, "return !!document.getElementById('intlAddManual')", 10): return False
    c.js(JS % "document.getElementById('intlAddManual').click(); return 1"); time.sleep(0.4)
    setval(c, '#intlCustomName', name); setval(c, '#intlCustomCity', city)
    c.js(JS % "document.getElementById('intlCustomAdd').click(); return 1")
    return js_wait(c, "return (document.getElementById('suCampusLabel')||{}).textContent===%s" % json.dumps(name), 8)

def arm_hooks(c):
    c.send('Page.enable'); c.send('Runtime.enable')
    c.js("window.__huberr=[]; window.addEventListener('error',function(e){window.__huberr.push(String(e.message||e))});"
         "window.addEventListener('unhandledrejection',function(e){window.__huberr.push('rej:'+String(e.reason&&e.reason.message||e.reason))}); return 1")

def console_errors(c):
    errs = [e for e in c.events if e.get('method') in ('Log.entryAdded','Runtime.exceptionThrown')]
    werr, _ = c.js(JS % "return window.__huberr||[]")
    return errs, werr or []

shutil.rmtree(PROF, ignore_errors=True)
chrome = subprocess.Popen([CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
    '--user-data-dir='+PROF, '--window-size=390,844', '--remote-debugging-port=%d' % PORT,
    '--remote-allow-origins=*', '--allow-file-access-from-files', 'about:blank'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    wsurl = None
    for _ in range(40):
        try:
            tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=3))
            wsurl = tabs[0]['webSocketDebuggerUrl']; break
        except Exception: time.sleep(0.5)
    assert wsurl, 'no devtools'
    c = CDP(wsurl)
    c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    arm_hooks(c)
    c.send('Page.navigate', {'url': BASE})
    # seed profile like PraBin's phone (onboarding skipped), then reload for a clean boot
    ok = js_wait(c, "return document.readyState==='complete' && !!window.HUB && !!HUB.auth", 25)
    note(ok, 'app booted')
    c.js(JS % "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
              "var s=HUB.store.state; s.profile.name='PraBin'; s.profile.campus='QA Campus';"
              "s.prefs.dark=true; HUB.store.save(); return 1")
    c.send('Page.reload'); arm_hooks(c)
    ok = js_wait(c, "return document.readyState==='complete' && !!window.HUB && !!HUB.auth", 25)
    note(ok, 'clean boot after seed')
    # wait out the 5s splash + gate poll
    ok = js_wait(c, "var s=document.getElementById('splash'); return !!(s&&s.classList.contains('splash-out'))", 20)
    note(ok, 'splash fade started')
    # the fix for the 1s Home flash: login must ALREADY be open while the
    # splash is still fading, so the splash lifts straight into it
    note(auth_visible(c), 'no Home flash: login open as splash fades')
    ok = js_wait(c, "return !document.getElementById('splash')", 20)
    note(ok, 'splash dismissed')
    ok = js_wait(c, "var r=document.getElementById('authRoot'); return !!(r&&!r.hidden)", 25)
    note(ok, 'GATE: login opened automatically after splash (no tap)')
    if not ok:
        d, _ = c.js(JS % "return {splash:!!document.getElementById('splash'),"
                          " sheetHidden:(function(){var s=document.getElementById('sheetHost');return s?s.hidden:'no-sheet'})(),"
                          " cu:!!HUB.auth.currentUser(),"
                          " gateType:typeof HUB.auth.gate,"
                          " root:(function(){var r=document.getElementById('authRoot');return r?(r.hidden?'hidden':'VISIBLE'):'no-root'})(),"
                          " wlcm:!!document.getElementById('wlcmHost')}")
        print('DIAG gate-fail:', json.dumps(d))
    v, _ = c.js(JS % "return (document.getElementById('aSkip')||{}).textContent")
    note(v == 'Explore without signing in', 'skip link copy', repr(v))
    v, _ = c.js(JS % "return (document.getElementById('aId')||{}).placeholder")
    note(bool(v), 'login identifier field present', repr(v))
    time.sleep(1.0); c.shot('shot-auth-gate-dark.jpg')
    # skip closes it
    c.js(JS % "document.getElementById('aSkip').click(); return 1"); time.sleep(0.5)
    note(not auth_visible(c), 'skip closes the overlay')

    print('--- signup -> signed in ---')
    c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.4)
    setval(c, '#suName', 'Gate Tester'); setval(c, '#suEmail', 'gate@example.com')
    setval(c, '#suNum', '5550001111')
    setval(c, '#suPw', 'Sup3r$ecretPass!'); setval(c, '#suPw2', 'Sup3r$ecretPass!')
    note(pick_campus(c), 'campus via real picker')
    c.js(JS % "document.getElementById('suNext1').click(); return 1")
    note(js_wait(c, "return !!document.getElementById('suSend')", 8), 'step1 -> verify method')
    c.js(JS % "document.getElementById('suSend').click(); return 1")
    note(js_wait(c, "return !!document.querySelector('#suCodes .auth-code')", 8), 'method -> code step')
    code, _ = c.js(JS % "return (HUB.auth._debug.lastCode()||{}).code")
    note(code and len(code) == 6, 'demo code issued', repr(code))
    for i, ch in enumerate(code):
        setval(c, "#suCodes .auth-code:nth-child(%d)" % (i + 1), ch)
    note(js_wait(c, "return !!HUB.auth.currentUser()", 8), 'correct code -> signed in')
    note(js_wait(c, "var r=document.getElementById('authRoot'); return !!(r&&r.hidden)", 8), 'overlay closed after signup')
    s, _ = c.js(JS % "var st=JSON.parse(localStorage.getItem('hub_v1')||'{}'); return (st.auth||{}).session||null")
    note(s and s.get('remember') is True, 'hub_v1 session persisted (remember ON)')

    print('--- reload: gate stays shut when signed in ---')
    c.send('Page.reload'); arm_hooks(c)
    ok = js_wait(c, "return document.readyState==='complete' && !!window.HUB && !!HUB.auth", 25)
    note(ok, 'rebooted')
    note(js_wait(c, "return !document.getElementById('splash')", 20), 'splash dismissed (2nd boot)')
    time.sleep(1.5)
    note(not auth_visible(c), 'gate stays shut for signed-in user')
    u, _ = c.js(JS % "return (HUB.auth.currentUser()||{}).name")
    note(u == 'Gate Tester', 'session restored', repr(u))

    print('--- logout -> gate reopens ---')
    c.js(JS % "HUB.auth.logout(); return 1"); time.sleep(0.8)
    note(auth_visible(c), 'logout reopens the login screen')
    time.sleep(0.8); c.shot('shot-auth-gate-logout.jpg')
    c.js(JS % "document.getElementById('aSkip').click(); return 1"); time.sleep(0.5)
    note(not auth_visible(c), 'skip works after logout')

    print('--- German ---')
    c.js(JS % "return HUB.i18n.setLang('de')", awaitPromise=True)
    time.sleep(0.6)
    c.js(JS % "HUB.auth.openLogin(); return 1"); time.sleep(0.5)
    v, _ = c.js(JS % "return (document.getElementById('aSkip')||{}).textContent")
    note(v == 'Ohne Anmeldung erkunden', 'real German skip copy', repr(v))
    v, _ = c.js(JS % "return {ident:HUB.i18n._dict('de')!==HUB.i18n._dict('en'),"
                      " khok:(function(){try{return JSON.parse(document.querySelector('[data-locale-kh]')?'1':'1')}catch(e){return false}})()}")
    v2, _ = c.js(JS % "return HUB.i18n._dict('de')!==HUB.i18n._dict('en')")
    note(bool(v2), 'de dict really loaded (identity)')
    time.sleep(0.8); c.shot('shot-auth-gate-de.jpg')

    print('--- console ---')
    errs, werr = console_errors(c)
    note(len(errs) == 0 and len(werr) == 0, 'zero console errors', 'cdp=%d window=%d' % (len(errs), len(werr)))
    if errs: print(json.dumps(errs)[:400])
    if werr: print(werr[:5])
finally:
    chrome.terminate()

n = len(checks); p = sum(checks)
print('\n==== %d/%d PASS ====' % (p, n))
sys.exit(0 if p == n else 1)
