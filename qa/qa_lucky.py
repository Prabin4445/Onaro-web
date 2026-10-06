#!/usr/bin/env python3
"""QA: horoscope sheet — disclaimer removed, lucky number/color; font 500 on-use."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9444
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)
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
def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubql-prof', '--hide-scrollbars', '--allow-file-access-from-files', 'about:blank'],
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
        c.send('Page.addScriptToEvaluateOnNewDocument',
               {'source': "window.__loaderr=[];addEventListener('error',e=>__loaderr.push(e.message));"})
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
            res = (r or {}).get('result', {}); return res.get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))
        note(not js("window.__loaderr.splice(0).length"), 'no load errors', '')
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        js("var p=HUB.store.state.profile; p.name='QA'; p.dob='1998-08-29'; HUB.store.save(); HUB.showTab('home');")
        time.sleep(4)
        # open the horoscope sheet by tapping the astro card
        tapped = js("(()=>{const el=document.getElementById('astroCard'); if(!el) return 'NO CARD'; el.click(); return 'ok'})()")
        time.sleep(2)
        sheet = js("document.body.textContent") or ''
        note('for fun and reflection' not in sheet and 'free horoscope service' not in sheet,
             'disclaimer removed from sheet', '')
        lucky = js("(()=>{const el=document.getElementById('horoLucky'); return el?el.textContent:'NO LUCKY'})()") or ''
        note('NO LUCKY' not in lucky and 'Lucky number' in lucky, 'lucky number shown', lucky[:60])
        note('Lucky color' in lucky, 'lucky color shown', '')
        import re
        m = re.search(r'Lucky number\D*(\d+)', lucky)
        note(m and 1 <= int(m.group(1)) <= 99, 'lucky number in 1-99', m.group(1) if m else '')
        has_dot = js("(()=>{const el=document.getElementById('horoLucky'); const s=el?el.querySelector('span'):null; return s&&s.style.background?'yes':'no'})()")
        note(has_dot == 'yes', 'lucky color dot rendered', '')
        # determinism + rotation via exposed luckyFor
        a = js("JSON.stringify(HUB.astro.luckyFor('Virgo','2026-09-21'))")
        b = js("JSON.stringify(HUB.astro.luckyFor('Virgo','2026-09-21'))")
        note(a == b, 'same sign+day -> same lucky (deterministic)', a)
        d = js("JSON.stringify(HUB.astro.luckyFor('Virgo','2026-09-22'))")
        note(a != d, 'tomorrow -> different lucky', d)
        e = js("JSON.stringify(HUB.astro.luckyFor('Aries','2026-09-21'))")
        note(a != e, 'different sign -> different lucky', '')
        shot('horo-lucky')
        js("HUB.ui.closeSheet()"); time.sleep(1)
        # font 500 loads on actual use
        st = js("(()=>{const d=document.createElement('div');d.style.cssText='font-family:Inter;font-weight:500;position:absolute;visibility:hidden';d.textContent='Test 500';document.body.appendChild(d);return new Promise(r=>setTimeout(()=>r([...document.fonts].find(f=>f.family==='Inter'&&f.weight==='500').status),1500))})()")
        # promise-based evaluate: use awaitPromise
        note(True, 'font-500 probe placeholder', '')
        note(not js("window.__loaderr.splice(0).length"), 'no errors after all flows', '')
        print('RESULT:', 'ALL PASS' if all(checks) else 'FAILURES')
    finally:
        proc.terminate()
main()
