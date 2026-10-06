#!/usr/bin/env python3
"""QA: Gym Fuel Reset — setup -> log progress -> Reset (cancel keeps, confirm wipes)
-> setup screen returns -> new data recomputes. Fresh profiles, zero console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9541
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
FILL_SETUP = """(()=>{
var d=document;
function set(id,v){var e=d.getElementById(id);if(!e)return false;e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return true;}
if(!d.getElementById('gyDrawer')) return 'no-drawer';
set('fAge','30');set('fW','180');set('fFt','5');set('fIn','11');set('fT','190');
return 'filled';
})()"""
def run(theme):
    shutil.rmtree(f'/tmp/hubqa-gymreset-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-gymreset-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('daily');")
        time.sleep(1.5)
        errs('daily tab')
        # 1. setup screen shows (no profile)
        note(js("!!document.getElementById('gySetup')"), f'{theme}: setup CTA shown on fresh profile')
        note(js("!document.getElementById('gyReset')"), f'{theme}: no Reset button before setup')
        # 2. complete setup
        js("document.getElementById('gySetup').click()"); time.sleep(1)
        note(js(FILL_SETUP)=="filled", f'{theme}: setup drawer filled')
        js("document.getElementById('fSave').click()"); time.sleep(1.2)
        kcal = js("var e=document.querySelector('[data-gy=kcal]'); e?e.textContent.trim():'none'")
        note(kcal not in ('—','none',''), f'{theme}: setup saved, kcal ring shows {kcal}')
        note(js("!!document.getElementById('gyReset')"), f'{theme}: Reset button appears after setup')
        # 3. log progress
        js("document.getElementById('gyProg').click()"); time.sleep(1)
        js("document.getElementById('gSaveLog').click()"); time.sleep(1)
        nlogs = js("HUB.store.state.gym&&HUB.store.state.gym.logs?HUB.store.state.gym.logs.length:0")
        note(nlogs==1, f'{theme}: progress logged', f'n={nlogs}')
        # 4. Reset -> cancel keeps data
        js("document.getElementById('gyProg'); document.getElementById('gyReset').click()"); time.sleep(0.8)
        txt = js("document.getElementById('sheetBox')?document.getElementById('sheetBox').textContent:''")
        note('Nothing leaves your phone' in txt or 'clears your measurements' in txt, f'{theme}: confirm sheet shows honest copy')
        shot(f'gym-reset-{theme}.png')
        js("document.getElementById('gyResetNo').click()"); time.sleep(0.6)
        note(js("HUB.store.state.gym&&!!HUB.store.state.gym.profile"), f'{theme}: cancel keeps data')
        # 5. Reset -> confirm wipes
        js("document.getElementById('gyReset').click()"); time.sleep(0.8)
        js("document.getElementById('gyResetGo').click()"); time.sleep(1.2)
        note(js("!document.getElementById('gyReset') && !!document.getElementById('gySetup')"), f'{theme}: after confirm, setup screen returns')
        st = js("JSON.stringify({p:!!(HUB.store.state.gym&&HUB.store.state.gym.profile),l:(!HUB.store.state.gym||!HUB.store.state.gym.logs||HUB.store.state.gym.logs.length===0),u:HUB.store.state.gym&&HUB.store.state.gym.unit})")
        note(st and '"p":false' in st and '"l":true' in st, f'{theme}: profile+logs wiped', st)
        note(st and '"u":"imp"' in st, f'{theme}: unit pref preserved', st)
        errs('reset flow')
        shot(f'gym-reset-done-{theme}.png')
        # 6. new data from scratch
        js("document.getElementById('gySetup').click()"); time.sleep(1)
        js("document.querySelector('#gyDrawer [data-f=sex][data-v=f]').click()")
        js(FILL_SETUP); time.sleep(0.5)
        js("var e=document.getElementById('fW');e.value='150';e.dispatchEvent(new Event('input',{bubbles:true}));")
        js("document.getElementById('fSave').click()"); time.sleep(1.2)
        kcal2 = js("var e=document.querySelector('[data-gy=kcal]'); e?e.textContent.trim():'none'")
        note(kcal2 not in ('—','none','') and kcal2!=kcal, f'{theme}: new data recomputes ring', f'{kcal} -> {kcal2}')
        errs('second setup')
        shot(f'gym-reset-redone-{theme}.png')
    finally:
        proc.terminate(); proc.wait()
run('dark'); run('light')
fails=[l for ok,l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
if fails: print('FAILED:', fails); raise SystemExit(1)
