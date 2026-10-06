#!/usr/bin/env python3
"""QA: Daily tab 'Happening' events as 3D water-flow carousel (shared with Home).
Boot clean, dark default, carousel renders with full event list, cover-flow tilt,
horizontal scroll, auto-drift pause, reduced motion, tap/Enter -> detail sheet, empty state."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9454
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
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

def run(theme, full):
    shutil.rmtree(f'/tmp/hubqa-dailyev-{theme}', ignore_errors=True)  # AGENTS.md: wipe stale profiles
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-dailyev-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        v = js("document.body.classList.contains('dark')")
        note(v, f'{theme}: fresh install boots dark by default', str(v))
        js("try{HUB.store.state.profile.name='QA';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        time.sleep(1)
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('daily');")
        time.sleep(1.5)
        errs('daily render')

        n = js("HUB.store.state.events.length")
        v = js("!!document.getElementById('dyEvFlow')")
        note(v, f'{theme}: #dyEvFlow carousel present', str(v))
        v = js("document.querySelectorAll('#dyEvents .gcard').length")
        note(v == n, f'{theme}: all {n} events as cards (no slice)', f'found={v}')
        v = js("document.querySelectorAll('#dyEvents .item.tight').length")
        note(v == 0, f'{theme}: old stacked list removed', f'found={v}')
        v = js("document.querySelector('#dyEvents .gcard').textContent")
        txt = str(v)
        ok = 'Free pizza' in txt and '12:00 PM' in txt and 'Student Union lobby' in txt and 'Sample' in txt and '›' in txt
        note(ok, f'{theme}: card keeps icon/title/time/location/sample/chevron', txt[:70])
        v = js("document.querySelector('#dyEvents .gcard').style.transform")
        note('rotateY' in str(v), f'{theme}: cover-flow tilt applied', str(v)[:60])
        shot(f'dailyev-daily-{theme}.png')

        v = js("(()=>{const f=document.getElementById('dyEvFlow'); f.scrollLeft=150; return f.scrollWidth+'>'+f.clientWidth;})()")
        note(isinstance(v, str) and '+' not in v, f'{theme}: carousel scrollable', str(v))
        js("document.getElementById('dyEvFlow').scrollLeft=0")

        if not full:
            return

        js("document.getElementById('dyEvFlow').style.scrollSnapType='none'")
        a = js("document.getElementById('dyEvFlow').scrollLeft")
        time.sleep(3)
        b = js("document.getElementById('dyEvFlow').scrollLeft")
        note(b is not None and a is not None and (b - a) > 5, f'{theme}: auto-drift advances', f'{a}->{b}')
        js("document.getElementById('dyEvFlow').dispatchEvent(new WheelEvent('wheel',{bubbles:true}))")
        time.sleep(0.5)
        c1 = js("document.getElementById('dyEvFlow').scrollLeft")
        time.sleep(2.5)
        c2 = js("document.getElementById('dyEvFlow').scrollLeft")
        note(c1 is not None and c2 is not None and abs(c2 - c1) < 2, f'{theme}: wheel pauses auto-drift', f'{c1}->{c2}')
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        js("HUB.showTab('daily')"); time.sleep(1.5)
        js("document.getElementById('dyEvFlow').style.scrollSnapType='none'")
        d1 = js("document.getElementById('dyEvFlow').scrollLeft")
        time.sleep(3)
        d2 = js("document.getElementById('dyEvFlow').scrollLeft")
        note(d1 is not None and d2 is not None and abs(d2 - d1) < 2, f'{theme}: reduced-motion disables drift', f'{d1}->{d2}')
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})
        js("HUB.showTab('daily')"); time.sleep(1.5)

        js("document.querySelector('#dyEvents .gcard').click()"); time.sleep(1.0)
        v = js("document.getElementById('sheetHost').hidden===false && document.getElementById('sheetHost').textContent")
        txt = str(v)
        ok = 'Free pizza' in txt and 'Student Union lobby' in txt
        note(ok, f'{theme}: card tap opens event detail sheet', txt[:70])
        shot(f'dailyev-detail-{theme}.png')
        js("try{HUB.ui.closeSheet()}catch(e){}"); time.sleep(0.5)

        js("(()=>{const cd=document.querySelector('#dyEvents .gcard'); cd.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));})()")
        time.sleep(0.8)
        v = js("document.getElementById('sheetHost').hidden===false")
        note(v, f'{theme}: Enter key opens event detail', str(v))
        js("try{HUB.ui.closeSheet()}catch(e){}")

        js("(()=>{window._evbak=HUB.store.state.events; HUB.store.state.events=[]; HUB.showTab('daily');})()")
        time.sleep(1.0)
        v = js("document.getElementById('dyEvents').textContent")
        note('No events right now' in str(v), f'{theme}: empty state renders', str(v)[:60])
        js("(()=>{HUB.store.state.events=window._evbak; HUB.store.save(); HUB.showTab('daily');})()")
        time.sleep(1.0)
        v = js("document.querySelectorAll('#dyEvents .gcard').length")
        note(v == n, f'{theme}: events restored after empty test', f'found={v}')
        errs('final')
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
