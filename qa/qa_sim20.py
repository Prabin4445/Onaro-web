#!/usr/bin/env python3
"""HUB QA: empty-call -> "Simulate 20 people (demo)" button (js/call.js).
Covers: regular voice call lands in empty state -> new unmissable button
present -> tap -> 20 simulated tiles -> demo20Note label -> admin role ->
speaking glow activity -> admin mute works -> no overflow -> leave cleanly.
Dark + light at 390x844. Fresh profile. Also verifies lazy de locale loads
with new kh (object identity) and carries call.sim20."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9433
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-sim20'
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
    c.js("(()=>{const s=HUB.store.state; s.cgroups=s.cgroups||[]; if(!s.cgroups.find(g=>g.id==='qa-sim20-g')) s.cgroups.push({id:'qa-sim20-g',name:'QA Sim Group',emoji:'🧪',mine:true,live:true,members:[],chat:[]}); HUB.store.save(); return 'ok'})()")
def set_theme(c, dark):
    c.js("(()=>{HUB.store.state.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 't'})()" % ('true' if dark else 'false'))
    time.sleep(0.8)
def no_overflow(c):
    v, _ = c.js("document.documentElement.scrollWidth<=window.innerWidth")
    return bool(v)

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--user-data-dir={PROF}', '--allow-file-access-from-files', '--hide-scrollbars',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
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

        # lazy de locale: real load (object identity) + new key + kh guard
        lv, _ = c.js("HUB.i18n.loadLocale('de').then(ok=>({ok:ok,ident:HUB.i18n._dict('de')!==HUB.i18n._dict('en'),sim:HUB.i18n._dict('de')['call.sim20']}))", awaitPromise=True)
        note(bool(lv and lv.get('ok') and lv.get('ident')), 'lazy de locale really loads (identity)', str(lv)[:120])
        note(bool(lv and lv.get('sim') == '20 Personen simulieren (Demo)'), 'de call.sim20 translated', str((lv or {}).get('sim')))
        # back to english for the UI flow
        c.js("HUB.i18n.setLang('en')"); time.sleep(0.8)

        for theme, dark in [('dark', True), ('light', False)]:
            set_theme(c, dark)
            # start a REGULAR voice call — the path PraBin took
            c.js("HUB.call.start('qa-sim20-g')")
            ok = wait_js(c, "(()=>{const r=document.getElementById('callRoot'); return r&&!r.hidden&&!!document.getElementById('callSim20Btn')})()")
            note(bool(ok), f'[{theme}] regular call opens, empty state (self tile + sim button)')
            btn, _ = c.js("(()=>{const b=document.getElementById('callSim20Btn'); if(!b) return null; const r=b.getBoundingClientRect(); return {txt:b.textContent, vis:r.width>0&&r.height>0}})()")
            note(bool(btn and btn.get('vis')), f'[{theme}] "Simulate 20 people" button visible in empty state', str(btn)[:80])
            note(bool(btn and 'Simulate 20 people (demo)' in btn.get('txt', '')), f'[{theme}] button label honest (simulated/demo)', str((btn or {}).get('txt')))
            note(no_overflow(c), f'[{theme}] no horizontal overflow in empty state')
            shot(c, f'call-sim20-entry-{theme}'); drain_err(c, f'entry-{theme}')

            c.js("document.getElementById('callSim20Btn').click()")
            n = wait_js(c, "document.querySelectorAll('#callTiles [data-tile]').length>=21")
            tiles, _ = c.js("document.querySelectorAll('#callTiles [data-tile]').length")
            note(bool(n), f'[{theme}] tap -> 20 simulated tiles appear (self+20)', 'tiles=%s' % tiles)
            dbg, _ = c.js("HUB.call._debug()")
            note(bool(dbg and dbg.get('demo20')), f'[{theme}] session flagged demo20')
            note(bool(dbg and dbg.get('role') == 'admin'), f'[{theme}] flipped to admin', str((dbg or {}).get('role')))
            lbl, _ = c.js("document.getElementById('callDemoLabel').textContent")
            note('20 simulated people' in str(lbl), f'[{theme}] honest demo label', str(lbl)[:60])
            time.sleep(3.5)
            spk, _ = c.js("document.querySelectorAll('#callTiles .calltile.speaking').length")
            note(bool(spk and spk >= 1), f'[{theme}] speaking-glow activity among sims', 'speaking=%s' % spk)
            # admin mute on a simulated participant
            c.js("document.querySelector('#callTiles [data-tile=\"d0\"]').click()")
            mok = wait_js(c, "!!document.getElementById('callAdmMute')")
            note(bool(mok), f'[{theme}] admin sheet opens on sim tile')
            if mok:
                c.js("document.getElementById('callAdmMute').click()"); time.sleep(0.8)
                micon, _ = c.js("!!document.querySelector('#callTiles [data-tile=\"d0\"] .micon')")
                note(bool(micon), f'[{theme}] admin mute works on simulated participant')
            note(no_overflow(c), f'[{theme}] no horizontal overflow with 20-tile grid')
            shot(c, f'call-sim20-grid-{theme}'); drain_err(c, f'grid-{theme}')
            c.js("HUB.call.leave()"); time.sleep(0.8)
            left, _ = c.js("(()=>{const r=document.getElementById('callRoot'); return r.hidden&&!HUB.call.isActive()})()")
            note(bool(left), f'[{theme}] leave cleanly (root hidden, session gone)')
            drain_err(c, f'leave-{theme}')

        print('\n==== %d/%d checks passed, %d error groups ====' % (sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

main()
