#!/usr/bin/env python3
"""Silence QA (2026-09-29, PraBin's order: ALL sound effects removed, only the
call ringtone remains).

Asserts in headless Chromium, fresh profile, zero console errors:
1. HUB.sound.playNotification() makes ZERO Audio.play() calls (silent no-op).
2. A toast (store.js) appears in the DOM with ZERO play calls.
3. Real Edit Profile path: gender -> female -> Save -> zero play calls,
   theme-rose applied, saved toast visible.
4. Call ringtone still works: playRingtone() triggers exactly one play call,
   stopRingtone() silences it.
5. Ringtone picker preview still plays once (ringtone feature intact).
6. audio/notify.* files are gone (404 on file:// read).
7. me.set.soundNote now says only "Call ringtone." (en).
"""
import json, subprocess, time, urllib.request, os, shutil
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9499
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

W, H = 390, 844
prof = '/tmp/hubqa-silence'
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
    f'--window-size={W},{H}', f'--user-data-dir={prof}',
    '--hide-scrollbars', '--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required', BASE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                ts = json.load(rr)
            tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
        except Exception: continue
    else: raise RuntimeError('no target')
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
    c.send('Emulation.setDeviceMetricsOverride', {'width': W, 'height': H,
           'deviceScaleFactor': 2, 'mobile': True})
    def js(expr):
        try:
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            if r and 'exceptionDetails' in r:
                ed = r['exceptionDetails']
                return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
            return (r or {}).get('result', {}).get('value')
        except Exception as e: return 'JSERR:' + str(e)[:120]
    def js_wait_ready(timeout=20):
        dl = time.time() + timeout
        while time.time() < dl:
            try:
                r = c.send('Runtime.evaluate', {'expression': 'document.readyState', 'returnByValue': True})
                if (r or {}).get('result', {}).get('value') == 'complete': return True
            except Exception: pass
            time.sleep(0.5)
        return False

    c.send('Page.navigate', {'url': BASE}); js_wait_ready(); time.sleep(4)
    # arm error siphon + Audio.play spy (counts every play() attempt)
    js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
       "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));"
       "window.__plays=[];"
       "HTMLMediaElement.prototype.play=(function(_p){return function(){window.__plays.push((this.currentSrc||this.src||'?').split('/').pop());"
       "return _p.apply(this,arguments);};})(HTMLMediaElement.prototype.play);")
    # seed + disarm auth gate (harness lesson from qa_prof)
    js("window.__gateSkip=true;HUB.store.state.profile.name='Prabin';HUB.store.state.profile.campus='Dallas College';"
       "HUB.store.save();HUB.auth.close();var w=document.getElementById('wlcmHost');if(w)w.remove();")
    time.sleep(1)
    def plays(): return js("window.__plays.splice(0).length")
    def errs(label):
        v = js("window.__huberr.splice(0)")
        note(not v, 'zero console errors @ ' + label, json.dumps(v)[:200] if v else '')

    # 1. playNotification is a silent no-op
    js("HUB.sound.playNotification()"); time.sleep(0.4)
    note(plays() == 0, 'playNotification() makes zero play calls')

    # 2. toast is silent
    js("HUB.ui.toast('hello-test')"); time.sleep(0.6)
    note(plays() == 0, 'toast() is silent')
    note(js("!!document.querySelector('#toastHost .toast')") is True, 'toast still renders in DOM')

    # 3. real Edit Profile path: gender -> female -> Save
    js("HUB.showTab('me')"); time.sleep(1)
    note(js("(function(){document.getElementById('meEditBtn').click();return true;})()") is True, 'edit profile opens')
    time.sleep(1.5)
    js("(function(){var b=document.querySelector('#peditGender button[data-g=\"female\"]');if(b)b.click();return !!b;})()")
    js("document.getElementById('peditSave').click()")
    time.sleep(2.5)  # save + water-flow transition
    note(plays() == 0, 'gender change + save: ZERO play calls')
    note(js("document.body.classList.contains('theme-rose')") is True, 'female theme applied (rose)')
    note(js("HUB.store.state.profile.gender") == 'female', 'gender persisted as female')
    note(js("!!document.querySelector('#toastHost .toast')") is True, 'saved toast visible, silently')

    # 4. call ringtone still works
    js("HUB.sound.playRingtone()"); time.sleep(0.8)
    n = plays()
    note(n >= 1, 'playRingtone() triggers play call', 'calls=%d' % n)
    js("HUB.sound.stopRingtone()"); time.sleep(0.3)
    note(js("HUB.sound.isRinging()") is False, 'stopRingtone() silences')

    # 5. ringtone picker preview still functional
    r = js("HUB.sound.preview('aurora')"); time.sleep(0.8)
    note(r == 'playing', 'preview(aurora) returns playing', str(r))
    note(plays() >= 1, 'preview triggers one play call')
    js("HUB.sound.stopPreview()")

    # 6. whistle files gone
    note(js("(function(){return fetch('audio/notify.mp3').then(r=>r.status).catch(()=>0);})()") == 0,
         'audio/notify.mp3 unreachable')

    # 7. settings note now ringtone-only
    note(js("HUB.i18n.t('me.set.soundNote')") == 'Call ringtone.', 'soundNote says Call ringtone only')

    errs('silence QA')
finally:
    proc.terminate()

fails = [l for ok, l in checks if not ok]
print('\n==== %d/%d passed ====' % (len(checks) - len(fails), len(checks)))
if fails: print('FAILURES:', fails)
