#!/usr/bin/env python3
"""Capture the two transient delight moments: the verification sparkle burst
(shot mid-flight) and the login wake-up glow. Fresh profile /tmp/hubqa-authm."""
import json, subprocess, time, urllib.request, os, shutil, sys, base64
try:
    import websocket
except ImportError:
    sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9443
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-authm'
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
JS = "(function(){%s})()"

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12)
        self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if 'method' in msg and 'id' not in msg: continue
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
        res = (r or {}).get('result', {})
        return res.get('value'), res.get('exceptionDetails')
    def shot(self, name):
        r = self.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 82, 'fromSurface': True})
        with open(os.path.join(SHOTDIR, name), 'wb') as f: f.write(base64.b64decode(r['data']))
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
        c.send('Runtime.enable'); c.send('Page.enable')
        js_wait(c, "return !document.getElementById('splash')", 25)
        c.js(JS % "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
                  "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus'; s.prefs.dark=true; HUB.store.save(); return 1")
        c.send('Page.reload')
        js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash')", 25)
        c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
        time.sleep(0.6)

        # drive signup fast
        c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.4)
        setval(c, '#suName', 'Moment Tester'); setval(c, '#suEmail', 'moment@example.com')
        setval(c, '#suNum', '5559990001'); setval(c, '#suPw', 'Sup3r$ecretPass!'); setval(c, '#suPw2', 'Sup3r$ecretPass!')
        c.js(JS % "document.getElementById('suCampus').click(); return 1")
        js_wait(c, "return !!document.getElementById('intlAddManual')", 10)
        c.js(JS % "document.getElementById('intlAddManual').click(); return 1"); time.sleep(0.3)
        setval(c, '#intlCustomName', 'QA University'); setval(c, '#intlCustomCity', 'Austin')
        c.js(JS % "document.getElementById('intlCustomAdd').click(); return 1")
        js_wait(c, "return (document.getElementById('suCampusLabel')||{}).textContent==='QA University'", 8)
        c.js(JS % "document.getElementById('suNext1').click(); return 1")
        js_wait(c, "return !!document.getElementById('suSend')", 8)
        c.js(JS % "document.getElementById('suSend').click(); return 1")
        js_wait(c, "return !!document.querySelector('#suCodes .auth-code')", 8)
        c.js(JS % "HUB.auth._debug.setCredApi({isUserVerifyingPlatformAuthenticatorAvailable:function(){return Promise.resolve(true)},"
                  "create:function(){return Promise.resolve({rawId:new Uint8Array([1,2,3,4]).buffer})},"
                  "get:function(){return Promise.resolve({})}}); return 1")
        v, _ = c.js(JS % "return (HUB.auth._debug.lastCode()||{}).code")
        for i, ch in enumerate(v):
            setval(c, "#suCodes .auth-code:nth-child(%d)" % (i + 1), ch)
        c.js(JS % "document.getElementById('suVerify').click(); return 1")
        js_wait(c, "return !!document.getElementById('enRoll')", 10)
        time.sleep(0.45)
        n, _ = c.js(JS % "return document.querySelectorAll('.auth-bmote').length")
        print('burst motes alive at 0.45s:', n)
        c.shot('shot-auth-burst.jpg')
        time.sleep(1.6)
        n2, _ = c.js(JS % "return document.querySelectorAll('.auth-bmote').length")
        print('burst motes after 2s (should be 0):', n2)

        # logout, then login to catch the wake glow
        c.js(JS % "document.getElementById('enSkip').click(); return 1"); time.sleep(0.5)
        c.js(JS % "HUB.showTab('me'); return 1"); time.sleep(0.8)
        c.js(JS % "var b=document.getElementById('acLogout'); if(b) b.click(); return 1"); time.sleep(0.6)
        c.js(JS % "HUB.auth.openLogin(); return 1"); time.sleep(0.5)
        v, _ = c.js(JS % "return document.activeElement && document.activeElement.id")
        print('login autofocus element:', v)
        setval(c, '#aId', '5559990001')
        setval(c, '#aPw', 'Sup3r$ecretPass!')
        c.js(JS % "document.getElementById('aLogin').click(); return 1")
        time.sleep(0.8)  # spinner 0.55s done, wake glow mid-flight
        w, _ = c.js(JS % "return !!document.querySelector('.auth-wake')")
        print('wake div present at 0.8s:', w)
        c.shot('shot-auth-wake.jpg')
        time.sleep(0.8)
        v, _ = c.js(JS % "return {hidden:document.getElementById('authRoot').hidden, user:(HUB.auth.currentUser()||{}).name}")
        print('after login:', v)
        print('DONE')
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
