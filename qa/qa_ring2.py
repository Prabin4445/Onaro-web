#!/usr/bin/env python3
"""HUB QA: ringtone preview + custom ringtone (js/sound.js, js/me.js).
Covers: preview buttons play once w/o changing selection, second preview
stops the first, tap-again stops, sound-off blocks preview honestly,
custom file upload (IndexedDB) -> preview/select/persist-across-reload/
incoming-call uses blob / remove -> fallback to Classic / missing-file
fallback / 10MB cap / lazy de locale with new kh. Dark + light, 390x844."""
import json, subprocess, time, urllib.request, os, base64, shutil, wave, struct, math
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9434
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-ring2'
WAV = '/tmp/ring-qa.wav'
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
def seed(c):
    c.js("(()=>{const p=HUB.store.state.profile; p.name='Prabin QA'; p.campus='QA Campus'; HUB.store.save(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()")
def set_theme(c, dark):
    c.js("(()=>{HUB.store.state.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 't'})()" % ('true' if dark else 'false'))
    time.sleep(0.8)
def no_overflow(c):
    v, _ = c.js("document.documentElement.scrollWidth<=window.innerWidth")
    return bool(v)
def clear_toasts(c):
    c.js("var h=document.getElementById('toastHost'); if(h) h.innerHTML=''")
def toast_text(c):
    v, _ = c.js("(()=>{const h=document.getElementById('toastHost'); return h?h.textContent:''})()")
    return v or ''
def show_me(c):
    c.js("HUB.showTab('me')")
    return wait_js(c, "!!document.getElementById('ringList')")
def sel_ringtone(c):
    v, _ = c.js("HUB.sound.getRingtone()")
    return v

def make_wav():
    w = wave.open(WAV, 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
    frames = b''.join(struct.pack('<h', int(12000*math.sin(2*math.pi*440*i/22050))) for i in range(22050))
    w.writeframes(frames); w.close()

def upload_custom(c):
    # click "Use my own" -> hidden input appears -> set files via CDP -> dispatch change
    c.js("document.getElementById('ringAddBtn').click()")
    ok = wait_js(c, "!!document.getElementById('ringFileInp')")
    if not ok: return False
    doc = c.send('DOM.getDocument', {'depth': -1})
    q = c.send('DOM.querySelector', {'nodeId': doc['root']['nodeId'], 'selector': '#ringFileInp'})
    node_id = (q or {}).get('nodeId')
    if not node_id: return False
    c.send('DOM.setFileInputFiles', {'nodeId': node_id, 'files': [WAV]})
    c.js("document.getElementById('ringFileInp').dispatchEvent(new Event('change'))")
    return bool(wait_js(c, "!!document.querySelector('[data-ring=\"custom\"]')", timeout=20))

def main():
    make_wav()
    shutil.rmtree(PROF, ignore_errors=True)
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
        hook_err(c); seed(c)

        # lazy de locale: real load (object identity), new key translated, kh guard passes
        lv, _ = c.js("HUB.i18n.loadLocale('de').then(ok=>({ok:ok,ident:HUB.i18n._dict('de')!==HUB.i18n._dict('en'),my:HUB.i18n._dict('de')['me.set.ringMy'],pv:HUB.i18n._dict('de')['me.set.ringPreview']}))", awaitPromise=True)
        note(bool(lv and lv.get('ok') and lv.get('ident')), 'lazy de locale really loads (identity, new kh)', str(lv)[:160])
        note(bool(lv and lv.get('my') == 'Mein Klingelton' and lv.get('pv') == 'Anhören'), 'de ringtone strings translated', str((lv or {}).get('my')))
        c.js("HUB.i18n.setLang('en')"); time.sleep(1.0)

        for theme, dark in [('dark', True), ('light', False)]:
            set_theme(c, dark)
            c.js("HUB.sound.setRingtone('classic')")  # deterministic per-theme baseline (profile persists)
            note(bool(show_me(c)), f'[{theme}] Me tab shows ringtone list')
            rows, _ = c.js("document.querySelectorAll('#ringList [data-ring]').length")
            pvs, _ = c.js("document.querySelectorAll('#ringList .ringpv').length")
            note(rows >= 3 and pvs == rows, f'[{theme}] built-in rows, each with a preview button', f'rows={rows} pvs={pvs}')
            note(sel_ringtone(c) == 'classic', f'[{theme}] default ringtone is classic')

            # preview classic: plays, selection unchanged
            st, _ = c.js("HUB.sound.preview('classic')")
            time.sleep(0.6)
            pv, _ = c.js("HUB.sound.previewing()")
            ring, _ = c.js("HUB.sound.isRinging()")
            note(st == 'playing' and pv == 'classic' and not ring and sel_ringtone(c) == 'classic',
                 f'[{theme}] preview classic plays once, selection untouched', f'st={st} pv={pv}')
            # second preview stops the first
            c.js("HUB.sound.preview('warm')"); time.sleep(0.6)
            pv2, _ = c.js("HUB.sound.previewing()")
            note(pv2 == 'warm', f'[{theme}] starting warm preview stops classic', f'pv={pv2}')
            # tap-again stops
            st2, _ = c.js("HUB.sound.preview('warm')")
            pv3, _ = c.js("HUB.sound.previewing()")
            note(st2 == 'stopped' and pv3 is None, f'[{theme}] tapping the playing preview stops it')
            note(sel_ringtone(c) == 'classic', f'[{theme}] selection still classic after previews')

            # sound off: preview blocked honestly
            clear_toasts(c)
            c.js("HUB.sound.setOn(false)")
            st3, _ = c.js("HUB.sound.preview('vocal')")
            time.sleep(0.4)
            tt = toast_text(c)
            note(st3 == 'off' and 'Turn sound on' in tt, f'[{theme}] sound-off preview blocked with honest toast', tt[:60])
            c.js("HUB.sound.setOn(true)"); clear_toasts(c)

            # preview buttons are 44px+ touch targets
            sz, _ = c.js("(()=>{const b=document.querySelector('#ringList .ringpv'); const r=b.getBoundingClientRect(); return {w:r.width,h:r.height}})()")
            note(bool(sz and sz['w'] >= 44 and sz['h'] >= 44), f'[{theme}] preview button >=44px', str(sz))
            note(no_overflow(c), f'[{theme}] no horizontal overflow in settings')
            shot(c, f'ringpicker-{theme}'); drain_err(c, f'picker-{theme}')

            if theme == 'dark':
                # ---- custom ringtone flow (dark only, profile persists for light pass) ----
                note(upload_custom(c), '[dark] custom file upload -> "My ringtone" row appears')
                nm, _ = c.js("HUB.sound.customName()")
                note(bool(nm and 'ring-qa' in nm), '[dark] custom filename stored', str(nm))
                c.js("document.querySelector('[data-ring=\"custom\"] .ringpv').click()"); time.sleep(0.6)
                pvc, _ = c.js("HUB.sound.previewing()")
                note(pvc == 'custom', '[dark] custom preview plays', f'pv={pvc}')
                c.js("HUB.sound.stopPreview()")
                # select custom
                c.js("document.querySelector('[data-ring=\"custom\"]').click()"); time.sleep(0.4)
                note(sel_ringtone(c) == 'custom', '[dark] custom row selectable')
                # incoming-call path uses the blob
                c.js("HUB.sound.playRingtone()"); time.sleep(1.0)
                dbg, _ = c.js("HUB.sound._debug()")
                note(bool(dbg and dbg.get('ringing') and str(dbg.get('ringSrc','')).startswith('blob:')),
                     '[dark] incoming-call ringtone plays the custom blob', str((dbg or {}).get('ringSrc'))[:40])
                c.js("HUB.sound.stopRingtone()")
                shot(c, 'ringpicker-custom-dark'); drain_err(c, 'custom-dark')

        # reload: custom persists (IndexedDB) and stays selected
        c.js("HUB.sound.setRingtone('custom')")  # re-select after the light-pass baseline reset
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.5)
        hook_err(c); seed(c); set_theme(c, True)
        note(bool(show_me(c)), '[reload] Me tab renders after reload')
        note(bool(wait_js(c, "!!document.querySelector('[data-ring=\"custom\"]')", timeout=20)), '[reload] custom ringtone persists across reload')
        note(sel_ringtone(c) == 'custom', '[reload] custom still selected')
        shot(c, 'ringpicker-reload-dark')

        # remove custom -> falls back to classic
        clear_toasts(c)
        c.js("document.getElementById('ringRemoveBtn').click()"); time.sleep(0.8)
        gone, _ = c.js("!document.querySelector('[data-ring=\"custom\"]')")
        note(bool(gone) and sel_ringtone(c) == 'classic', '[remove] custom removed, falls back to classic')
        note('removed' in toast_text(c).lower(), '[remove] honest toast', toast_text(c)[:60])

        # missing-file fallback: select custom with empty IDB -> honest toast + classic rings
        clear_toasts(c)
        c.js("HUB.sound.setRingtone('custom')")
        c.js("HUB.sound.playRingtone()"); time.sleep(1.2)
        dbg2, _ = c.js("HUB.sound._debug()")
        tt2 = toast_text(c)
        note(bool(dbg2 and dbg2.get('ringing') and 'ringtone-classic' in str(dbg2.get('ringSrc','')) and sel_ringtone(c) == 'classic'),
             '[fallback] missing custom file -> classic rings, selection reset')
        note("Couldn't play your file" in tt2, '[fallback] honest toast shown', tt2[:60])
        c.js("HUB.sound.stopRingtone()"); clear_toasts(c)

        # 10MB cap
        big, _ = c.js("HUB.sound.setCustom(new File([new ArrayBuffer(11*1024*1024)],'big.mp3',{type:'audio/mpeg'})).then(()=> 'ok').catch(e=> e&&e.tooBig?'tooBig':'other')", awaitPromise=True)
        note(big == 'tooBig', '[cap] 11MB file rejected with tooBig')

        drain_err(c, 'final')
        print('\n==== %d/%d checks passed, %d error groups ====' % (sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

main()
