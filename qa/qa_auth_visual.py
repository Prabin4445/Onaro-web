#!/usr/bin/env python3
"""HUB QA visual: auth showcase screenshots + full signup flow drive.
Fresh profile /tmp/hubqa-authv. Captures dark+light shots of every auth step
for designer review. Also pinpoints the pw-hint smoke failure."""
import json, subprocess, time, urllib.request, os, shutil, sys, base64
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9441
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-authv'
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
JS = "(function(){%s})()"

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12)
        self.id = 0; self.events = []
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
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
        p = os.path.join(SHOTDIR, name)
        with open(p, 'wb') as f: f.write(base64.b64decode(r['data']))
        print('SHOT', name)

def js_wait(c, expr, timeout=12):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False

def setval(c, sel, val):
    c.js(JS % "var el=document.querySelector(%s); el.value=%s; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); return 1" % (json.dumps(sel), json.dumps(val)))

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
        c.js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
             "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        ok = js_wait(c, "return !document.getElementById('splash')", 25)
        print('splash gone:', ok)
        # seed clean onboarded profile, reload for clean boot
        c.js(JS % "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
                  "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus'; s.prefs.dark=true; HUB.store.save(); return 1")
        c.send('Page.reload')
        ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash')", 25)
        print('clean boot:', ok)
        c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
        time.sleep(0.6)

        # ---- debug the pw-hint failure with exception details ----
        c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.5)
        v, x = c.js(JS % "var p=document.getElementById('suPw'); if(!p) return 'NO suPw';"
                          "p.value='Sup3r$ecretPass!'; p.dispatchEvent(new Event('input',{bubbles:true}));"
                          "var h=document.getElementById('suPwHint'); return h?('hint='+h.textContent):'NO suPwHint'")
        print('pw-hint debug:', repr(v), 'exc:', json.dumps(x)[:200] if x else None)

        # ---- shot 1: login (dark) ----
        c.js(JS % "HUB.auth.openLogin(); return 1"); time.sleep(0.9)
        c.shot('shot-auth-login-dark.jpg')

        # ---- shot 2: signup step 1 (dark) ----
        c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.9)
        c.shot('shot-auth-su1-dark.jpg')

        # ---- drive the real flow: fill step 1 ----
        setval(c, '#suName', 'PraBin Shrestha')
        setval(c, '#suEmail', 'prabin@example.com')
        setval(c, '#suNum', '5551234567')
        setval(c, '#suPw', 'Sup3r$ecretPass!')
        setval(c, '#suPw2', 'Sup3r$ecretPass!')
        time.sleep(0.3)
        c.shot('shot-auth-su1-filled-dark.jpg')
        # campus via the real picker: manual add
        c.js(JS % "document.getElementById('suCampus').click(); return 1")
        got = js_wait(c, "return !!document.getElementById('intlAddManual')", 10)
        print('picker manual btn:', got)
        if got:
            c.js(JS % "document.getElementById('intlAddManual').click(); return 1"); time.sleep(0.4)
            setval(c, '#intlCustomName', 'QA University')
            setval(c, '#intlCustomCity', 'Austin')
            c.js(JS % "document.getElementById('intlCustomAdd').click(); return 1")
            got2 = js_wait(c, "return (document.getElementById('suCampusLabel')||{}).textContent==='QA University'", 8)
            print('campus picked:', got2)
        c.js(JS % "document.getElementById('suNext1').click(); return 1")
        got3 = js_wait(c, "return !!document.getElementById('suSend')", 8)
        print('reached step 2:', got3)
        time.sleep(0.9)
        # ---- shot 3: step 2 verify-method (dark) ----
        c.shot('shot-auth-su2-dark.jpg')
        c.js(JS % "document.getElementById('suSend').click(); return 1")
        got4 = js_wait(c, "return !!document.querySelector('#suCodes .auth-code')", 8)
        print('reached step 3:', got4)
        time.sleep(0.9)
        # ---- shot 4: step 3 code entry (dark) ----
        c.shot('shot-auth-su3-dark.jpg')
        # inject fake Face ID so the enroll screen appears after verify
        c.js(JS % "HUB.auth._debug.setCredApi({isUserVerifyingPlatformAuthenticatorAvailable:function(){return Promise.resolve(true)},"
                  "create:function(){return Promise.resolve({rawId:new Uint8Array([1,2,3,4]).buffer})},"
                  "get:function(){return Promise.resolve({})}}); return 1")
        v, _ = c.js(JS % "return (HUB.auth._debug.lastCode()||{}).code")
        print('demo code:', v)
        if v:
            for i, ch in enumerate(v):
                setval(c, "#suCodes .auth-code:nth-child(%d)" % (i + 1), ch)
            time.sleep(0.4)
            c.js(JS % "document.getElementById('suVerify').click(); return 1")
        got5 = js_wait(c, "return !!document.getElementById('enRoll')", 10)
        print('reached enroll:', got5)
        time.sleep(1.0)
        # ---- shot 5: welcome/enroll (dark) ----
        c.shot('shot-auth-enroll-dark.jpg')
        c.js(JS % "document.getElementById('enSkip').click(); return 1"); time.sleep(0.6)
        # ---- shot 6: ME signed in ----
        c.js(JS % "HUB.showTab('me'); return 1"); time.sleep(1.0)
        c.shot('shot-auth-me-in-dark.jpg')
        # ---- shot 7: ME signed out card ----
        c.js(JS % "var b=document.getElementById('acLogout'); if(b) b.click(); return 1"); time.sleep(0.8)
        c.shot('shot-auth-me-out-dark.jpg')

        # ---- light mode ----
        c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme(); HUB.auth.openLogin(); return 1")
        time.sleep(1.0)
        c.shot('shot-auth-login-light.jpg')
        c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(1.0)
        c.shot('shot-auth-su1-light.jpg')
        c.js(JS % "HUB.auth.close(); HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme(); return 1")

        # ---- console errors ----
        bad = []
        for ev in c.events:
            m = ev.get('method', '')
            if m == 'Runtime.exceptionThrown':
                bad.append('EXC:' + json.dumps(ev['params'].get('exceptionDetails', {}).get('text', ''))[:120])
            elif m == 'Log.entryAdded' and ev['params']['entry'].get('level') == 'error':
                bad.append('LOG:' + ev['params']['entry'].get('text', '')[:120])
            elif m == 'Runtime.consoleAPICalled' and ev['params'].get('type') == 'error':
                bad.append('CON:' + json.dumps(ev['params'].get('args', []))[:120])
        v, _ = c.js("window.__huberr.splice(0)")
        if v: bad.append('HOOK:' + json.dumps(v)[:300])
        print('console errors:', bad if bad else 'ZERO')
        print('DONE')
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
