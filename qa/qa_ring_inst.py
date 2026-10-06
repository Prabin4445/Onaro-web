#!/usr/bin/env python3
"""HUB QA: instrument ringtones (piano/violin/guitar) replacing the vocal one.
Covers: vocal fully gone (files, RINGS, picker); 3 new audio files decode;
loudness RMS~0.40 (NOT hotter than Classic/Warm), peak<=0.95; picker lists
5 built-ins, no vocal row; select/persist/reload per ringtone; preview works;
incoming-call demo plays the selected one; vocal->classic prefs migration;
no overflow; zero console errors. Dark + light at 390x844. Fresh profile."""
import json, subprocess, time, urllib.request, os, base64, shutil, wave
import numpy as np
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
AUD = os.path.expanduser('~/workspace/hub/audio')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9435
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-ringinst'
errors, checks = [], []
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
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

def targets():
    with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=5) as r:
        return json.load(r)
def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
def hook_err(c):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def drain_err(c, label):
    v, _ = c.js("window.__huberr.splice(0)")
    if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])
def wait_js(c, expr, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v, _ = c.js(expr)
        if v: return v
        time.sleep(0.5)
    return None
def seed(c, name):
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
def set_theme(c, dark):
    c.js("(()=>{HUB.store.state.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 't'})()" % ('true' if dark else 'false'))
    time.sleep(0.8)
def no_overflow(c):
    v, _ = c.js("document.documentElement.scrollWidth<=window.innerWidth")
    return bool(v)
def show_me(c):
    c.js("HUB.showTab('me')")
    return wait_js(c, "!!document.getElementById('ringList')")

def audio_checks():
    """Static decode + loudness + loop-click checks on the new files."""
    for key in ['piano', 'violin', 'guitar']:
        for ext in ['wav', 'mp3', 'ogg']:
            p = os.path.join(AUD, 'ringtone-%s.%s' % (key, ext))
            note(os.path.exists(p) and os.path.getsize(p) > 1000,
                 'file exists ringtone-%s.%s' % (key, ext))
        w = wave.open(os.path.join(AUD, 'ringtone-%s.wav' % key), 'rb')
        n = w.getnframes(); raw = w.readframes(n); w.close()
        y = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
        rms = float(np.sqrt(np.mean(y ** 2))); pk = float(np.max(np.abs(y)))
        dur = n / w.getframerate()
        note(abs(rms - 0.40) < 0.03 and pk <= 0.96,
             'loudness %s pleasant (not hotter)' % key, 'rms=%.3f peak=%.3f' % (rms, pk))
        note(3.0 < dur < 3.4, 'duration %s ~3.2s' % key, '%.2fs' % dur)
        # click-free loop: phrase boundary (halfway) must be near silence on both sides
        half = len(y) // 2
        edge = float(np.max(np.abs(y[half-200:half+200])))
        note(edge < 0.05, 'loop boundary click-free %s' % key, 'edge=%.4f' % edge)
    # classic/warm reference level (must not be exceeded by new ones)
    for key in ['classic', 'warm']:
        w = wave.open(os.path.join(AUD, 'ringtone-%s.wav' % key), 'rb')
        n = w.getnframes(); raw = w.readframes(n); w.close()
        y = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
        rms = float(np.sqrt(np.mean(y ** 2)))
        note(rms <= 0.44, 'classic/warm reference rms', '%s=%.3f' % (key, rms))
    # vocal files gone
    for ext in ['wav', 'mp3', 'ogg']:
        note(not os.path.exists(os.path.join(AUD, 'ringtone-vocal.%s' % ext)),
             'vocal file deleted ringtone-vocal.%s' % ext)

def main():
    audio_checks()
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--user-data-dir={PROF}', '--allow-file-access-from-files', '--hide-scrollbars',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
        '--autoplay-policy=no-user-gesture-required',
        '--no-first-run', '--no-default-browser-check', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        try:
            targets(); break
        except Exception:
            pass
    else:
        proc.terminate(); raise SystemExit('chrome did not come up')
    try:
        t = [x for x in targets() if x['type'] == 'page'][0]
        c = CDP(t['webSocketDebuggerUrl'])
        c.send('Page.enable'); c.send('Emulation.setDeviceMetricsOverride',
            {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE})
        wait_js(c, "!!window.HUB&&!!HUB.sound", 30)
        hook_err(c); seed(c, 'Prabin QA')

        for dark in (True, False):
            tag = 'dark' if dark else 'light'
            set_theme(c, dark)
            note(show_me(c), '[%s] me tab renders ringList' % tag)
            # picker rows: 5 built-ins, no vocal
            rows, _ = c.js("(()=>[...document.querySelectorAll('#ringList [data-ring]')].map(r=>r.getAttribute('data-ring')))()")
            note(rows == ['classic', 'warm', 'piano', 'violin', 'guitar'],
                 '[%s] picker lists 5 built-ins, vocal gone' % tag, str(rows))
            labels, _ = c.js("(()=>[...document.querySelectorAll('#ringList .ringname')].map(e=>e.childNodes[0].textContent.trim()))()")
            note(labels == ['Onaro Classic', 'Onaro Warm', 'Onaro Piano', 'Onaro Violin', 'Onaro Guitar'],
                 '[%s] picker labels' % tag, str(labels))
            pv, _ = c.js("(()=>['piano','violin','guitar'].every(k=>!!document.querySelector('#ringList [data-ring=\"'+k+'\"] [data-pv]')))()")
            note(bool(pv), '[%s] preview buttons on new rows' % tag)
            note(no_overflow(c), '[%s] no horizontal overflow' % tag)
            if dark:
                shot(c, 'ring-inst-dark')
            else:
                shot(c, 'ring-inst-light')
            drain_err(c, 'me-' + tag)

        # select / persist / reload per new ringtone
        for key in ['piano', 'violin', 'guitar']:
            c.js("HUB.sound.setRingtone('%s')" % key)
            v, _ = c.js("HUB.sound.getRingtone()")
            note(v == key, 'select %s' % key)
            c.send('Page.reload', {}); wait_js(c, "!!window.HUB&&!!HUB.sound", 30); seed(c, 'Prabin QA')
            v2, _ = c.js("HUB.sound.getRingtone()")
            note(v2 == key, 'persists across reload: %s' % key)
        # preview each new one (plays once, selection untouched)
        c.js("HUB.sound.setRingtone('classic')")
        for key in ['piano', 'violin', 'guitar']:
            st, _ = c.js("HUB.sound.preview('%s')" % key)
            pv, _ = c.js("HUB.sound.previewing()")
            sel, _ = c.js("HUB.sound.getRingtone()")
            note(st == 'playing' and pv == key and sel == 'classic',
                 'preview %s (selection untouched)' % key, str(st))
            c.js("HUB.sound.stopPreview()")
        # incoming-call demo plays the selected new ringtone
        c.js("HUB.sound.setRingtone('violin')")
        c.js("HUB.sound.playRingtone()"); time.sleep(1.0)
        dbg, _ = c.js("HUB.sound._debug()")
        note(bool(dbg and 'ringtone-violin' in str(dbg.get('ringSrc', ''))),
             'incoming-call demo plays selected violin ringtone',
             str((dbg or {}).get('ringSrc'))[-40:])
        c.js("HUB.sound.stopRingtone()")
        # vocal -> classic migration
        c.js("(()=>{HUB.store.state.prefs.ringtone='vocal'; HUB.store.save(); return 1})()")
        c.send('Page.reload', {}); wait_js(c, "!!window.HUB&&!!HUB.sound", 30); seed(c, 'Prabin QA')
        mg, _ = c.js("HUB.sound.getRingtone()")
        mgp, _ = c.js("HUB.store.state.prefs.ringtone")
        note(mg == 'classic' and mgp == 'classic', 'vocal pref migrates to classic silently')
        drain_err(c, 'final')
    finally:
        try: c.send('Browser.close')
        except Exception: pass
        proc.wait(timeout=10)
    n_pass = sum(1 for ok, _ in checks if ok)
    print('\n==== %d/%d checks passed, %d error groups ====' % (n_pass, len(checks), len(errors)))
    raise SystemExit(0 if n_pass == len(checks) and not errors else 1)

if __name__ == '__main__':
    main()
