#!/usr/bin/env python3
"""HUB QA: Aurora ringtones (2026-09-23, PraBin's modern-2026 soft call tones).
Part A (no browser): 6 audio files exist; 16s stereo 44.1k; peak < -1 dBFS;
  mp3 < 500KB; loop junction click-free.
Part B (headless Chromium, fresh profile): fresh default is Aurora Soft;
  existing 'phone' choice preserved; retired keys migrate to aurora; picker
  lists Aurora Soft / Aurora Breeze / Classic Phone with translated labels;
  preview plays once w/o changing selection; incoming-call demo plays the
  aurora mp3; notification source still audio/notify (unchanged); custom
  upload -> select -> reload persists -> remove -> falls back to aurora;
  real German lazy locale (object identity, kh=nyjuql) with translated
  labels, rendered in the picker. Dark + light at 390x844. Zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil, wave, struct, math
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
AUD = os.path.expanduser('~/workspace/hub/audio')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9447
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-ringaurora'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)

# ---------------- Part A: audio files ----------------
def ffprobe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration,size', '-show_entries', 'stream=codec_name,sample_rate,channels',
        '-of', 'json', path], capture_output=True, text=True)
    d = json.loads(r.stdout)
    return d['streams'][0], d['format']

def max_volume(path):
    # exact peak via numpy on decoded PCM (volumedetect rounds to 1 decimal)
    import numpy as np
    if path.endswith('.wav'):
        w = wave.open(path, 'rb'); n, ch = w.getnframes(), w.getnchannels()
        pcm = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(n, ch).astype(np.float64) / 32768
    else:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', '44100', '-'],
                           capture_output=True)
        pcm = np.frombuffer(r.stdout, dtype=np.float32)
    peak = float(np.abs(pcm).max())
    return 20 * math.log10(peak) if peak > 0 else None

def partA():
    print('== Part A: audio files ==')
    for base in ['ringtone-aurora', 'ringtone-breeze']:
        for ext in ['wav', 'mp3', 'ogg']:
            p = os.path.join(AUD, base + '.' + ext)
            note(os.path.exists(p), f'A1 {base}.{ext} exists')
            if not os.path.exists(p): continue
            s, f = ffprobe(p)
            dur = float(f['duration'])
            note(15.5 <= dur <= 16.5, f'A2 {base}.{ext} duration ~16s', f'{dur:.2f}s')
            note(int(s['channels']) == 2 and int(s['sample_rate']) == 44100,
                 f'A3 {base}.{ext} stereo 44.1k', f"{s['channels']}ch {s['sample_rate']}Hz")
            mv = max_volume(p)
            note(mv is not None and mv < -1.0, f'A4 {base}.{ext} peak < -1 dBFS', f'{mv} dB')
        sz = os.path.getsize(os.path.join(AUD, base + '.mp3'))
        note(sz < 500 * 1024, f'A5 {base}.mp3 < 500KB', f'{sz} bytes')
    # loop click check on the wavs: junction step vs signal's own variation
    import numpy as np
    for base in ['ringtone-aurora', 'ringtone-breeze']:
        w = wave.open(os.path.join(AUD, base + '.wav'), 'rb')
        n, ch = w.getnframes(), w.getnchannels()
        pcm = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(n, ch).astype(np.float64) / 32768
        ok = True
        for c in range(ch):
            x = pcm[:, c]
            js = abs(x[0] - x[-1]); p999 = np.percentile(np.abs(np.diff(x)), 99.9)
            if js > p999 * 3: ok = False
        note(ok, f'A6 {base}.wav loop junction click-free')
    # A7: unmistakable "ring... ring..." cadence — one ring per 4s bar:
    # ring window (0.0-2.2s of each bar) clearly louder than the breathing pause (2.6-4.0s)
    import numpy as np
    for base in ['ringtone-aurora', 'ringtone-breeze']:
        w = wave.open(os.path.join(AUD, base + '.wav'), 'rb')
        n, ch = w.getnframes(), w.getnchannels(); sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(n, ch).astype(np.float64) / 32768
        ratios = []
        for q in range(4):
            seg = pcm[q * 4 * sr:(q + 1) * 4 * sr]
            rr = np.sqrt(np.mean(seg[int(0.0 * sr):int(2.2 * sr)] ** 2))
            pr = np.sqrt(np.mean(seg[int(2.6 * sr):int(4.0 * sr)] ** 2))
            ratios.append(rr / pr if pr > 0 else 0)
        ok = all(r >= 1.4 for r in ratios)
        note(ok, f'A7 {base} has ring-pause cadence (4 rings, breathing pauses)',
             'ratios=' + ','.join(f'{r:.2f}' for r in ratios))

# ---------------- Part B: browser ----------------
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
    return wait_js(c, "!!document.getElementById('ringList')")
def ring_rows(c):
    # selected row is marked via aria-checked="true" (no .sel class)
    return c.js("Array.from(document.querySelectorAll('#ringList [data-ring]')).map(r=>({key:r.getAttribute('data-ring'),label:r.querySelector('.ringname').textContent.trim().split('\\n')[0],sel:r.getAttribute('aria-checked')==='true'}))")[0]
def make_test_wav(path):
    sr = 22050; n = int(sr * 0.8)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * 660 * i / sr) * (1 - i / n))) for i in range(n)))

def partB():
    print('== Part B: browser ==')
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
        try: targets(); break
        except Exception: pass
    else:
        proc.terminate(); raise SystemExit('chrome did not come up')
    try:
        t = [x for x in targets() if x['type'] == 'page'][0]
        c = CDP(t['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.5)
        hook_err(c); seed(c, 'Prabin QA')

        # B1: fresh default is Aurora Soft
        sel, _ = c.js("HUB.sound.getRingtone()")
        note(sel == 'aurora', 'B1 fresh install defaults to aurora', str(sel))
        base, _ = c.js("(()=>{const d=HUB.sound._debug(); return d.ringtone})()")
        note(base == 'aurora', 'B1b _debug ringtone is aurora', str(base))

        # B2: incoming-call demo plays the aurora mp3 (mp3 preferred)
        c.js("HUB.sound.playRingtone()"); time.sleep(0.8)
        dbg, _ = c.js("HUB.sound._debug()")
        note(bool(dbg and dbg.get('ringing') and 'ringtone-aurora.mp3' in str(dbg.get('ringSrc'))),
             'B2 incoming-call demo plays ringtone-aurora.mp3', str(dbg.get('ringSrc'))[-50:] if dbg else '')
        c.js("HUB.sound.stopRingtone()")
        drain_err(c, 'default-play')

        # B3: notification source unchanged
        c.js("HUB.sound.playNotification()"); time.sleep(0.6)
        dbg2, _ = c.js("HUB.sound._debug()")
        note(bool(dbg2 and 'audio/notify' in str(dbg2.get('noteSrc')) and dbg2.get('chimes', 0) >= 1),
             'B3 notification still uses audio/notify', str(dbg2.get('noteSrc'))[-30:] if dbg2 else '')

        for theme, dark in [('dark', True), ('light', False)]:
            set_theme(c, dark)
            note(open_me(c), f'[B4-{theme}] Me tab opens with ringList')
            rows = ring_rows(c)
            keys = [r['key'] for r in rows]
            note(keys == ['aurora', 'breeze', 'phone'], f'[B5-{theme}] picker lists aurora/breeze/phone in order', str(keys))
            labels = {r['key']: r['label'] for r in rows}
            note(labels.get('aurora') == 'Aurora Soft' and labels.get('breeze') == 'Aurora Breeze',
                 f'[B6-{theme}] picker labels translated', str(labels))
            note(any(r['key'] == 'aurora' and r['sel'] for r in rows), f'[B7-{theme}] aurora marked selected on fresh profile')
            note(no_overflow(c), f'[B8-{theme}] no horizontal overflow on picker')
            shot(c, f'ring-aurora-{theme}'); drain_err(c, f'picker-{theme}')

            # B9: preview plays once, selection untouched
            sel0, _ = c.js("HUB.sound.getRingtone()")
            st, _ = c.js("HUB.sound.preview('breeze')")
            time.sleep(1.2)
            pv, _ = c.js("HUB.sound.previewing()")
            sel1, _ = c.js("HUB.sound.getRingtone()")
            note(st == 'playing' and pv == 'breeze' and sel0 == sel1 == 'aurora',
                 f'[B9-{theme}] preview breeze plays, selection untouched', f'st={st} pv={pv} sel={sel1}')
            c.js("HUB.sound.stopPreview()")
            drain_err(c, f'preview-{theme}')

        # B10: existing 'phone' choice is preserved (never migrated)
        c.js("(()=>{HUB.store.state.prefs.ringtone='phone'; HUB.store.save(); return 1})()")
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(c); seed(c, 'Prabin QA')
        selp, _ = c.js("HUB.sound.getRingtone()")
        note(selp == 'phone', 'B10 saved phone choice stays phone', str(selp))
        open_me(c)
        rows = ring_rows(c)
        note(any(r['key'] == 'phone' and r['sel'] for r in rows), 'B10b picker marks phone selected')
        drain_err(c, 'phone-preserved')

        # B11: retired keys migrate to aurora
        for old in ['classic', 'warm', 'piano', 'violin', 'guitar', 'vocal']:
            c.js("(()=>{HUB.store.state.prefs.ringtone=%s; HUB.store.save(); return 1})()" % json.dumps(old))
            c.send('Page.navigate', {'url': BASE}); time.sleep(2.5)
            v, _ = c.js("HUB.sound.getRingtone()")
            if v != 'aurora':
                note(False, f'B11 migration {old}->aurora', str(v)); break
        else:
            note(True, 'B11 all retired keys migrate to aurora')
        drain_err(c, 'migration')

        # B12: custom upload -> select -> reload persists -> remove -> aurora
        hook_err(c); seed(c, 'Prabin QA'); open_me(c)
        # the Add button only renders after the IndexedDB probe (ringCustomReady)
        note(wait_js(c, "!!document.getElementById('ringAddBtn')", timeout=10),
             'B12a ring Add button appears after IDB probe')
        c.js("document.getElementById('ringAddBtn').click()")
        note(wait_js(c, "!!document.getElementById('ringFileInp')", timeout=10),
             'B12b file input created')
        r = c.send('DOM.getDocument', {})
        q = c.send('DOM.querySelector', {'nodeId': r['root']['nodeId'], 'selector': '#ringFileInp'})
        c.send('DOM.setFileInputFiles', {'nodeId': q['nodeId'], 'files': [testwav]})
        # belt-and-braces: make sure the change handler runs
        c.js("(()=>{const el=document.getElementById('ringFileInp'); if(el) el.dispatchEvent(new Event('change',{bubbles:true})); return 1})()")
        ok = wait_js(c, "HUB.sound.getRingtone()==='custom'", timeout=10)
        note(bool(ok), 'B12 custom upload -> selected')
        rows2 = ring_rows(c)
        note('custom' in [x['key'] for x in rows2], 'B12b picker shows custom row', str([x['key'] for x in rows2]))
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(c); seed(c, 'Prabin QA')
        sel4, _ = c.js("HUB.sound.getRingtone()")
        note(sel4 == 'custom', 'B12c custom persists across reload', str(sel4))
        c.js("HUB.sound.removeCustom().then(()=>1)")
        ok2 = wait_js(c, "HUB.sound.getRingtone()==='aurora'")
        note(bool(ok2), 'B12d remove custom -> falls back to aurora')
        drain_err(c, 'custom')

        # B13: real German lazy locale (object identity, new kh) + translated + rendered labels
        c.js("HUB.i18n.setLang('de')")
        ident = wait_js(c, "HUB.i18n._dict('de')!==HUB.i18n._dict('en')", timeout=20)
        note(bool(ident), 'B13 lazy de really loads (identity, kh guard passes)')
        vals, _ = c.js("({a:HUB.i18n._dict('de')['me.set.ringAurora'],b:HUB.i18n._dict('de')['me.set.ringBreeze'],c:HUB.i18n._dict('de')['me.set.ringBadFile']})")
        note(bool(vals and vals['a'] == 'Aurora sanft' and vals['b'] == 'Aurora-Brise'
                      and 'Aurora sanft' in vals['c'] and 'Classic Phone' not in vals['c']),
             'B13b de labels real translations (not fallback)', str(vals)[:120])
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(c); seed(c, 'Prabin QA'); open_me(c)
        rows3 = ring_rows(c)
        lab3 = {x['key']: x['label'] for x in rows3}
        note(lab3.get('aurora') == 'Aurora sanft', 'B13c picker renders German label', str(lab3))
        shot(c, 'ring-aurora-de'); drain_err(c, 'de')

        print('\n==== %d/%d checks passed, %d error groups ====' % (sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

partA()
partB()
