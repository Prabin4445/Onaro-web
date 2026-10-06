#!/usr/bin/env python3
"""QA: Time Capsule pill — bigger pill (14px), manifest line under pill,
manifesting line in (i) sheet, pill tap -> Daily tab. Fresh profiles, zero
console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9531
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)
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

def hook(c):
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Runtime.evaluate', {'expression':
        "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
        "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))"})

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-cappill-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-cappill-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        hook(c)
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')

        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(1.2)

        # 1. pill row exists with bigger font
        fs = js("(()=>{var p=document.querySelector('.caprow .cappill');return p?getComputedStyle(p).fontSize:'none'})()")
        note(fs == '14px', f'{theme}: pill font-size 14px', str(fs))
        # 2. manifest line under pill
        ml = js("(()=>{var m=document.querySelector('.capmanifest');return m?m.textContent:'none'})()")
        note(ml != 'none' and 'Manifest' in ml, f'{theme}: manifest line under pill', str(ml)[:80])
        errs('home render')
        shot(f'capsule-pill-{theme}.png')

        # 3. tap pill -> Daily tab
        js("document.querySelector('.caprow .cappill').click()"); time.sleep(1.0)
        on_daily = js("(()=>document.body.innerHTML.includes('Time Capsule')&&!!document.querySelector('#view-daily:not([hidden])'))()")
        daily_vis = js("(()=>{var v=document.querySelector('[data-view=\"daily\"]')||document.getElementById('view-daily');return v&&!v.hidden})()")
        note(bool(on_daily or daily_vis), f'{theme}: pill tap -> Daily tab', f'{on_daily}/{daily_vis}')
        errs('pill tap')

        # 4. back home, open (i) sheet -> manifesting line
        js("HUB.showTab('home')"); time.sleep(0.8)
        js("document.getElementById('homeCapInfo').click()"); time.sleep(0.8)
        mi = js("(()=>{var m=document.querySelector('.capmanifestline');return m?m.textContent:'none'})()")
        note(mi != 'none' and 'Manifest' in mi, f'{theme}: (i) sheet has manifesting line', str(mi)[:80])
        shot(f'capsule-info-{theme}.png')
        js("HUB.ui.closeSheet()"); time.sleep(0.5)
        errs('info sheet')
    finally:
        try: proc.terminate()
        except Exception: pass

for th in ('dark', 'light'):
    run(th)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
if fails: print('FAILURES:', fails); raise SystemExit(1)
