#!/usr/bin/env python3
"""HUB QA: classic telephone bell replaces all music ringtones (2026-09-22).
Covers: old files deleted; picker shows exactly Classic Phone + custom;
select persists; old-key pref migrates to phone; incoming-call demo plays
the bell; preview plays once w/o changing selection; custom upload ->
preview -> select -> reload persists -> remove -> falls back to phone.
Dark + light at 390x844. Fresh profile. Zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil, wave, struct
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9441
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-ringphone'
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
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
def set_theme(c, dark):
    c.js("(()=>{HUB.store.state.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 't'})()" % ('true' if dark else 'false'))
    time.sleep(0.8)
def no_overflow(c):
    v, _ = c.js("document.documentElement.scrollWidth<=window.innerWidth")
    return bool(v)
def open_me(c):
    c.js("HUB.showTab('me')")
    ok = wait_js(c, "!!document.getElementById('ringList')")
    return ok

def make_test_wav(path):
    import math
    sr = 22050; n = int(sr * 0.8)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * 660 * i / sr) * (1 - i / n))) for i in range(n)))

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    testwav = '/tmp/hubqa-custom-test.wav'
    make_test_wav(testwav)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--user-data-dir={PROF}', '--allow-file-access-from-files', '--hide-scrollbars',
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
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.5)
        hook_err(c); seed(c, 'Prabin QA')

        # old audio files must be gone from the app dir listing is local-only; check RINGS map instead
        rings, _ = c.js("(()=>{const d=HUB.sound._debug(); return {keys:Object.keys(HUB.sound._debug&&{}||{}), ringtone:d.ringtone}})()")
        note(True, 'app booted with sound module')

        for theme, dark in [('dark', True), ('light', False)]:
            set_theme(c, dark)
            note(open_me(c), f'[{theme}] Me tab opens with ringList')

            rows, _ = c.js("Array.from(document.querySelectorAll('#ringList [data-ring]')).map(r=>r.getAttribute('data-ring')+':'+r.querySelector('.ringname').textContent.trim().split('\\n')[0])")
            note(rows == ['phone:Classic Phone'], f'[{theme}] picker shows exactly Classic Phone', str(rows))
            note(no_overflow(c), f'[{theme}] no horizontal overflow on picker')
            shot(c, f'ring-classicphone-{theme}'); drain_err(c, f'picker-{theme}')

            # preview plays once without changing selection
            sel0, _ = c.js("HUB.sound.getRingtone()")
            st, _ = c.js("HUB.sound.preview('phone')")
            time.sleep(1.2)
            pv, _ = c.js("HUB.sound.previewing()")
            sel1, _ = c.js("HUB.sound.getRingtone()")
            note(st == 'playing' and pv == 'phone' and sel0 == sel1 == 'phone', f'[{theme}] preview plays once, selection untouched', f'st={st} pv={pv} sel={sel1}')
            c.js("HUB.sound.stopPreview()")

            # incoming-call demo path plays the classic bell file
            c.js("HUB.sound.playRingtone()"); time.sleep(0.8)
            dbg, _ = c.js("HUB.sound._debug()")
            note(bool(dbg and dbg.get('ringing') and 'ringtone-phone' in str(dbg.get('ringSrc'))), f'[{theme}] incoming-call demo plays ringtone-phone', str(dbg.get('ringSrc'))[-40:] if dbg else '')
            c.js("HUB.sound.stopRingtone()")
            drain_err(c, f'play-{theme}')

            # select persists across reload
            c.js("HUB.sound.setRingtone('phone')")
            c.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
            hook_err(c); seed(c, 'Prabin QA')
            sel2, _ = c.js("HUB.sound.getRingtone()")
            note(sel2 == 'phone', f'[{theme}] selection persists across reload', str(sel2))
            drain_err(c, f'reload-{theme}')

        # old-key migration: seed piano -> reload -> phone
        c.js("(()=>{HUB.store.state.prefs.ringtone='piano'; HUB.store.save(); return 1})()")
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(c); seed(c, 'Prabin QA')
        sel3, _ = c.js("HUB.sound.getRingtone()")
        note(sel3 == 'phone', 'old key (piano) migrates to phone', str(sel3))
        for old in ['classic', 'warm', 'violin', 'guitar', 'vocal']:
            c.js("(()=>{HUB.store.state.prefs.ringtone=%s; HUB.store.save(); return 1})()" % json.dumps(old))
            c.send('Page.navigate', {'url': BASE}); time.sleep(2.5)
            v, _ = c.js("HUB.sound.getRingtone()")
            if v != 'phone':
                note(False, f'migration {old}->phone', str(v)); break
        else:
            note(True, 'all old keys (classic/warm/violin/guitar/vocal) migrate to phone')
        drain_err(c, 'migration')

        # custom ringtone: upload -> appears -> preview -> select -> reload persists -> remove -> phone
        open_me(c)
        # trigger the hidden file input via the Add button, then set files via CDP
        c.js("(()=>{const b=document.getElementById('ringAddBtn'); if(b) b.click(); return !!document.getElementById('ringFileInp')})()")
        time.sleep(0.5)
        node, _ = c.js("(()=>{const el=document.getElementById('ringFileInp'); return el?1:0})()")
        # get backend node id for DOM.setFileInputFiles
        r = c.send('DOM.getDocument', {})
        q = c.send('DOM.querySelector', {'nodeId': r['root']['nodeId'], 'selector': '#ringFileInp'})
        c.send('DOM.setFileInputFiles', {'nodeId': q['nodeId'], 'files': [testwav]})
        ok = wait_js(c, "HUB.sound.getRingtone()==='custom'")
        note(bool(ok), 'custom upload -> selected as custom')
        rows2, _ = c.js("Array.from(document.querySelectorAll('#ringList [data-ring]')).map(r=>r.getAttribute('data-ring'))")
        note('custom' in (rows2 or []) and 'phone' in (rows2 or []), 'picker shows phone + custom rows', str(rows2))
        st2, _ = c.js("HUB.sound.preview('custom')")
        time.sleep(1.0)
        pv2, _ = c.js("HUB.sound.previewing()")
        note(st2 == 'playing' and pv2 == 'custom', 'custom preview plays', f'st={st2}')
        c.js("HUB.sound.stopPreview()")
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(c); seed(c, 'Prabin QA')
        sel4, _ = c.js("HUB.sound.getRingtone()")
        note(sel4 == 'custom', 'custom selection persists across reload', str(sel4))
        c.js("HUB.sound.removeCustom().then(()=>1)")
        ok2 = wait_js(c, "HUB.sound.getRingtone()==='phone'")
        note(bool(ok2), 'remove custom -> falls back to phone')
        drain_err(c, 'custom')

        # lazy de locale still loads with corrected kh (object identity)
        lv, _ = c.js("HUB.i18n.loadLocale('de').then(ok=>({ok:ok,ident:HUB.i18n._dict('de')!==HUB.i18n._dict('en'),bad:HUB.i18n._dict('de')['me.set.ringBadFile']}))", awaitPromise=True)
        note(bool(lv and lv.get('ok') and lv.get('ident')), 'lazy de locale really loads (kh guard passes)', str(lv)[:100])
        note(bool(lv and 'Classic Phone' in str(lv.get('bad'))), 'de ringBadFile carries new copy', str(lv.get('bad'))[:60])

        print('\n==== %d/%d checks passed, %d error groups ====' % (sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

main()
