#!/usr/bin/env python3
"""QA: typography upgrade — self-hosted Inter 400-800, Space Grotesk display, Noto Devanagari."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9441
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
SETUP = ("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
         "var p=HUB.store.state.profile; p.name='QA'; p.campus='Test Campus';"
         "HUB.store.save(); HUB.showTab('home');")
def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubqf-prof', '--hide-scrollbars', '--allow-file-access-from-files', 'about:blank'],
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
        js(SETUP); time.sleep(4)
        # 1. faces actually loaded (no more fake-bold synthesis)
        for w in ['400','500','600','700','800']:
            note(js(f"document.fonts.check('{w} 16px \"Inter\"')"), f'Inter {w} loaded (real, not synthesized)', '')
        note(js("document.fonts.check('700 16px \"Space Grotesk\"')"), 'Space Grotesk 700 loaded', '')
        note(js("document.fonts.check('500 16px \"Space Grotesk\"')"), 'Space Grotesk 500 loaded', '')
        note(js("document.fonts.check('16px \"Noto Sans Devanagari\"', 'अ')"), 'Noto Sans Devanagari covers Devanagari', '')
        # 2. applied where intended
        gf = js("getComputedStyle(document.querySelector('.greet')).fontFamily")
        note('Space Grotesk' in (gf or ''), 'hero greeting uses display font', gf)
        bf = js("getComputedStyle(document.body).fontFamily")
        note('Inter' in (bf or ''), 'body uses Inter', bf)
        note('Noto Sans Devanagari' in (bf or ''), 'Devanagari in body stack', '')
        bn = js("getComputedStyle(document.querySelector('.brand-name')).fontFamily")
        note('Space Grotesk' in (bn or ''), 'brand wordmark uses display font', '')
        # 3. no external font requests (fully self-hosted now)
        ext = js("performance.getEntriesByType('resource').map(r=>r.name).filter(u=>u.includes('fonts.g'))")
        note(not ext, 'zero Google Fonts network requests', str(ext))
        # 4. Nepali render check
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'ne',country:'NP'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js(SETUP.replace("'en'", "'ne'")); time.sleep(3)
        shot('font-nepali')
        note(not js("window.__loaderr.splice(0).length"), 'no errors in Nepali render', '')
        # 5. dark + light screenshots
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js(SETUP); time.sleep(3)
        shot('font-light')
        js("document.body.classList.add('dark')"); time.sleep(1)
        shot('font-dark')
        note(not js("window.__loaderr.splice(0).length"), 'no errors after all flows', '')
        print('RESULT:', 'ALL PASS' if all(checks) else 'FAILURES')
    finally:
        proc.terminate()
main()
