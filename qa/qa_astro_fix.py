#!/usr/bin/env python3
"""QA: horoscope reads same-origin data/horoscopes.json (CORS fix).
Uses the real store (full defaults) — seeds profile via HUB.store, like a real user."""
import json, subprocess, time, urllib.request, os, base64, datetime
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9431
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
SETUP = ("var p=HUB.store.state.profile; p.name='QA'; p.campus='Test Campus';"
         "p.dob='1998-08-29'; HUB.store.save(); HUB.showTab('home');")
def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubqafix3-prof', '--hide-scrollbars', '--allow-file-access-from-files', 'about:blank'],
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
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
            res = (r or {}).get('result', {}); return res.get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))
        # skip welcome via its own key, then set up profile through the real store
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        note(not js("window.__loaderr.splice(0).length"), 'no load errors', '')
        js(SETUP); time.sleep(3)
        card = js("(()=>{const c=document.getElementById('astroCard');return c?c.textContent:'NO CARD'})()") or ''
        note('Virgo' in card, 'home card shows Virgo sign', card[:60])
        note("hasn't arrived" not in card and 'unavailable' not in card.lower() and len(card) > 60,
             'home card snippet loaded from baked JSON', card[:90])
        js("document.getElementById('astroCard').click()"); time.sleep(2)
        full = js("(()=>{const e=document.getElementById('horoFull');return e?e.textContent:'NO SHEET'})()") or ''
        note(len(full) > 100 and 'unavailable' not in full.lower() and "hasn't arrived" not in full,
             'sheet shows full reading', full[:90])
        dl = js("(()=>{const e=document.getElementById('horoDateLine');return e?e.textContent:'NO'})()") or ''
        note(dl == '', 'no stale date line when fresh (file date = today)', repr(dl[:40]))
        shot('astro-horo-fixed')
        # stale path: backdate the baked file, clear today's cache, reload
        dp = '/home/hatch/workspace/hub/data/horoscopes.json'
        bak = open(dp).read()
        d = json.loads(bak)
        y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        d['date'] = y
        open(dp, 'w').write(json.dumps(d))
        js("localStorage.removeItem('orbit_horo_v1')")
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        js(SETUP); time.sleep(2)
        js("document.getElementById('astroCard').click()"); time.sleep(2)
        dl2 = js("(()=>{const e=document.getElementById('horoDateLine');return e?e.textContent:'NO'})()") or ''
        full2 = js("(()=>{const e=document.getElementById('horoFull');return e?e.textContent:'NO'})()") or ''
        note(y in dl2, 'stale reading labeled with its date', dl2[:60])
        note(len(full2) > 100, 'stale reading still shown (honest label)', full2[:60])
        card2 = js("(()=>{const c=document.getElementById('astroCard');return c?c.textContent:'NO'})()") or ''
        note("hasn't arrived" in card2, 'home card hides stale reading under Today title', card2[:70])
        shot('astro-horo-stale')
        open(dp, 'w').write(bak)
        print('restored horoscopes.json; date=', json.loads(bak)['date'])
        note(not js("window.__loaderr.splice(0).length"), 'no errors after all flows', '')
        print('RESULT:', 'ALL PASS' if all(checks) else 'FAILURES')
    finally:
        proc.terminate()
main()
