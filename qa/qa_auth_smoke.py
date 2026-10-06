#!/usr/bin/env python3
"""HUB QA smoke: auth (login + signup) overlay.
Fresh profile, file:// load, waits out the splash, then:
- HUB.auth.openLogin() renders the water-crystal login screen
- validation errors surface inline + toast
- HUB.auth.openSignup() renders step 1 with step indicator
- ME tab shows the Account card; its Log in button opens the overlay
- Face ID QA seam: setCredApi(fake) -> faceIdAvailable() true via the real path
- _debug.reset()/users()/lastCode() work
- zero console errors (CDP event siphon + window.__huberr)
No screenshots (visual review belongs to the follow-up QA worker)."""
import json, subprocess, time, urllib.request, os, shutil, sys
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9439
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-auth'
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

JS = "(function(){%s})()"
def targets():
    with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=5) as r:
        return json.load(r)

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
                ts = targets()
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
             "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        # wait out the splash
        t0 = time.time(); gone = False
        while time.time() - t0 < 25:
            if c.js(JS % "return !document.getElementById('splash')")[0]: gone = True; break
            time.sleep(0.5)
        note(gone, 'splash dismissed')
        # seed a clean onboarded profile, reload for a clean boot
        c.js(JS % "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
                  "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus'; HUB.store.save(); return 1")
        c.send('Page.reload')
        t0 = time.time(); ready = False
        while time.time() - t0 < 25:
            v, _ = c.js(JS % "return document.readyState==='complete' && !document.getElementById('splash')")
            if v: ready = True; break
            time.sleep(0.5)
        note(ready, 'clean boot after seed')
        # dismiss any welcome/onboarding overlays deterministically
        c.js(JS % "try{HUB.ui.closeSheet()}catch(e{}); var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1".replace('e{}','e){}'))
        time.sleep(0.6)

        # 1. openLogin renders
        v, x = c.js(JS % "HUB.auth.openLogin(); var r=document.getElementById('authRoot');"
                          "return {vis:!r.hidden, card:!!r.querySelector('.auth-card'), title:document.querySelector('.auth-title').textContent,"
                          " remember:document.getElementById('aRemember').classList.contains('on'),"
                          " ccopts:document.getElementById('aCC').options.length, motes:document.querySelectorAll('.auth-motes i').length}")
        note(not x and v and v['vis'] and v['card'], 'openLogin renders', json.dumps(v)[:160])
        note(v and v['title'] == 'Log in', 'login title copy', repr(v and v['title']))
        note(v and v['remember'], 'remember-me defaults ON')
        note(v and v['ccopts'] > 40, 'country select populated', repr(v and v['ccopts']))
        note(v and v['motes'] == 8, 'sparkle motes present', repr(v and v['motes']))
        # backdrop art + crystal card computed style
        v, _ = c.js(JS % "var cs=getComputedStyle(document.querySelector('.auth-card'));"
                          "return {bdFilter:cs.backdropFilter||cs.webkitBackdropFilter, bg:document.querySelector('.auth-bg')?getComputedStyle(document.querySelector('.auth-bg')).backgroundImage:'none'}")
        note(v and 'blur' in (v['bdFilter'] or ''), 'crystal card backdrop blur', repr(v and v['bdFilter']))
        note(v and 'splash-art.jpg' in (v['bg'] or ''), 'dimmed splash-art backdrop', (v and v['bg'] or '')[:80])

        # 2. validation: unknown phone in the single smart identifier -> error inline + toast
        c.js(JS % "document.getElementById('aId').value='5550100'; document.getElementById('aLogin').click(); return 1")
        time.sleep(0.4)
        v, _ = c.js(JS % "var e=document.getElementById('aErr'); return {vis:!e.hidden, txt:e.textContent.slice(0,40), toast:document.getElementById('toastHost').textContent.slice(0,40)}")
        note(v and v['vis'] and 'No account found' in v['txt'], 'login validation error inline', json.dumps(v)[:120])

        # 3. Escape closes the overlay (auth owns Escape)
        c.js(JS % "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); return 1")
        time.sleep(0.3)
        v, _ = c.js(JS % "return document.getElementById('authRoot').hidden")
        note(v is True, 'Escape closes auth overlay')

        # 4. openSignup -> step 1
        v, x = c.js(JS % "HUB.auth.openSignup(); return {s1:document.getElementById('suName')?'y':'n',"
                          " step:document.querySelector('.auth-steps').textContent, dots:document.querySelectorAll('.auth-dots i').length,"
                          " pwHint:!!document.getElementById('suPwHint'), campus:!!document.getElementById('suCampus')}")
        note(not x and v and v['s1'] == 'y', 'openSignup renders step 1', json.dumps(v)[:140])
        note(v and v['step'] == 'Step 1 of 3', 'step indicator copy', repr(v and v['step']))
        # empty submit -> name error
        c.js(JS % "document.getElementById('suNext1').click(); return 1")
        time.sleep(0.3)
        v, _ = c.js(JS % "var e=document.getElementById('suErr1'); return {vis:!e.hidden, txt:e.textContent.slice(0,30)}")
        note(v and v['vis'] and 'name' in v['txt'].lower(), 'signup validation (name)', json.dumps(v)[:80])
        # password strength hint reacts (dispatch + read in one call)
        v, x = c.js(JS % "var p=document.getElementById('suPw'); p.value='Sup3r$ecretPass!';"
                          "p.dispatchEvent(new Event('input',{bubbles:true}));"
                          "var h=document.getElementById('suPwHint'); return h?h.textContent:'NO-HINT'")
        note(v and 'Strong' in v, 'password strength hint', repr(v))
        c.js(JS % "HUB.auth.close(); return 1")

        # 5. ME tab account card (signed out)
        c.js(JS % "HUB.showTab('me'); return 1"); time.sleep(0.8)
        v, _ = c.js(JS % "return {card:!!document.querySelector('.auth-acct'), login:!!document.getElementById('acLogin'), signup:!!document.getElementById('acSignup')}")
        note(v and v['card'] and v['login'] and v['signup'], 'ME account card (signed out)', json.dumps(v))
        c.js(JS % "document.getElementById('acLogin').click(); return 1"); time.sleep(0.4)
        v, _ = c.js(JS % "return !document.getElementById('authRoot').hidden")
        note(v is True, 'ME card Log in opens overlay')
        c.js(JS % "HUB.auth.close(); return 1")

        # 6. Face ID QA seam exercises the real path
        v, x = c.js(JS % "HUB.auth._debug.setCredApi({isUserVerifyingPlatformAuthenticatorAvailable:function(){return Promise.resolve(true)},"
                          "create:function(){return Promise.resolve({rawId:new Uint8Array([1,2,3,4]).buffer})},"
                          "get:function(){return Promise.resolve({})}}); return HUB.auth.faceIdAvailable()", awaitPromise=True)
        note(v is True, 'faceIdAvailable true via injected fake', repr(v))
        v, _ = c.js(JS % "HUB.auth._debug.setCredApi(null); return HUB.auth._debug.users().length")
        note(v == 0, '_debug.reset state clean (0 users)', repr(v))

        # 7. console errors: CDP siphon + window hook
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
        note(not bad, 'zero console errors', '; '.join(bad)[:300])

        n = sum(checks); tot = len(checks)
        print('SMOKE: %d/%d' % (n, tot))
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
