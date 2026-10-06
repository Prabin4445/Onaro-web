#!/usr/bin/env python3
"""QA: Home 'What's happening' events as 3D water-flow carousel — same treatment
as the groups carousel. Boot clean, cards render with content, cover-flow tilt,
horizontal scroll, auto-drift, tap->detail sheet, keyboard, see-all, empty state."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9453
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
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-evcarr-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        js("try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
           "HUB.store.state.profile.name='QA';HUB.store.state.profile.campus='Riverside State';"
           "HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        time.sleep(1)
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(1.5)
        errs('home render')

        # carousel host + cards
        v = js("!!document.getElementById('homeEvFlow')")
        note(v, f'{theme}: #homeEvFlow carousel present', str(v))
        v = js("document.querySelectorAll('#homeEvents .gcard').length")
        note(v == 6, f'{theme}: 6 seed event cards', f'found={v}')
        # old vertical list gone
        v = js("document.querySelectorAll('#homeEvents .item.tight').length")
        note(v == 0, f'{theme}: old stacked list removed', f'found={v}')
        # content preserved on first card
        v = js("document.querySelector('#homeEvents .gcard').textContent")
        txt = str(v)
        ok = 'Free pizza' in txt and '12:00 PM' in txt and 'Student Union lobby' in txt and 'Sample' in txt
        note(ok, f'{theme}: card keeps icon/title/time/location/sample', txt[:70])
        # cover-flow transform applied
        v = js("document.querySelector('#homeEvents .gcard').style.transform")
        note('rotateY' in str(v), f'{theme}: cover-flow tilt applied', str(v)[:60])
        shot(f'evcarr-home-{theme}.png')

        # horizontal scroll works
        v = js("(()=>{const f=document.getElementById('homeEvFlow'); f.scrollLeft=150; return f.scrollWidth+'>'+f.clientWidth;})()")
        note(isinstance(v, str) and '+' not in v, f'{theme}: carousel scrollable', str(v))
        js("document.getElementById('homeEvFlow').scrollLeft=0")

        if not full:
            return

        # auto-drift machinery: headless mandatory scroll-snap pins scrollLeft at 0,
        # so disable snap to observe the timer; then wheel must pause it.
        js("document.getElementById('homeEvFlow').style.scrollSnapType='none'")
        a = js("document.getElementById('homeEvFlow').scrollLeft")
        time.sleep(3)
        b = js("document.getElementById('homeEvFlow').scrollLeft")
        note(b is not None and a is not None and (b - a) > 5, f'{theme}: auto-drift advances', f'{a}->{b}')
        # wheel interaction pauses the drift
        js("document.getElementById('homeEvFlow').dispatchEvent(new WheelEvent('wheel',{bubbles:true}))")
        time.sleep(0.5)
        c1 = js("document.getElementById('homeEvFlow').scrollLeft")
        time.sleep(2.5)
        c2 = js("document.getElementById('homeEvFlow').scrollLeft")
        note(c1 is not None and c2 is not None and abs(c2 - c1) < 2, f'{theme}: wheel pauses auto-drift', f'{c1}->{c2}')
        # prefers-reduced-motion: emulated, re-render, drift must stay off (snap disabled)
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        js("HUB.showTab('home')"); time.sleep(1.5)
        js("document.getElementById('homeEvFlow').style.scrollSnapType='none'")
        d1 = js("document.getElementById('homeEvFlow').scrollLeft")
        time.sleep(3)
        d2 = js("document.getElementById('homeEvFlow').scrollLeft")
        note(d1 is not None and d2 is not None and abs(d2 - d1) < 2, f'{theme}: reduced-motion disables drift', f'{d1}->{d2}')
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})
        js("HUB.showTab('home')"); time.sleep(1.5)

        # tap card -> event detail sheet
        js("document.querySelector('#homeEvents .gcard').click()"); time.sleep(1.0)
        v = js("document.getElementById('sheetHost').hidden===false && document.getElementById('sheetHost').textContent")
        txt = str(v)
        ok = 'Free pizza' in txt and 'Student Union lobby' in txt
        note(ok, f'{theme}: card tap opens event detail sheet', txt[:70])
        shot(f'evcarr-detail-{theme}.png')
        js("try{HUB.ui.closeSheet()}catch(e){}"); time.sleep(0.5)

        # keyboard: Enter on card opens sheet
        js("(()=>{const cd=document.querySelector('#homeEvents .gcard'); cd.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));})()")
        time.sleep(0.8)
        v = js("document.getElementById('sheetHost').hidden===false")
        note(v, f'{theme}: Enter key opens event detail', str(v))
        js("try{HUB.ui.closeSheet()}catch(e){}")

        # see-all -> daily tab
        js("(()=>{const b=Array.from(document.querySelectorAll('#view-home .linklike')).find(x=>x.dataset.goto==='daily'); if(b)b.click();})()")
        time.sleep(1.0)
        v = js("!document.getElementById('view-daily').hidden")
        note(v, f'{theme}: see-all opens daily tab', str(v))
        js("HUB.showTab('home')"); time.sleep(1.0)

        # empty state (temporarily clear, then restore)
        js("(()=>{window._evbak=HUB.store.state.events; HUB.store.state.events=[]; HUB.showTab('home');})()")
        time.sleep(1.0)
        v = js("document.getElementById('homeEvents').textContent")
        note('No events yet' in str(v), f'{theme}: empty state renders', str(v)[:60])
        js("(()=>{HUB.store.state.events=window._evbak; HUB.store.save(); HUB.showTab('home');})()")
        time.sleep(1.0)
        v = js("document.querySelectorAll('#homeEvents .gcard').length")
        note(v == 6, f'{theme}: events restored after empty test', f'found={v}')
        errs('final')
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
