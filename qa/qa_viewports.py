#!/usr/bin/env python3
"""Viewport sweep: 390x844 phone and 1280x800 desktop, boot->home, screenshots + errors."""
import json, subprocess, time, urllib.request, os, base64, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
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
def run(port, profile, w, h, tag):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={port}', '--remote-allow-origins=*', f'--window-size={w},{h}',
        f'--user-data-dir={profile}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl']); c.send('Runtime.enable'); c.send('Page.enable')
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                return (r or {}).get('result', {}).get('value')
            except Exception as e: return None
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        for _ in range(25):
            if js("typeof HUB!=='undefined'&&!!document.getElementById('wlcmHost')&&!document.getElementById('wlcmHost').hidden"): break
            time.sleep(1)
        js("document.getElementById('wlcmGo').click()"); time.sleep(1.0)
        js("document.getElementById('obStudent').click()"); time.sleep(0.5)
        js("document.getElementById('obName').value='Viewport QA';document.getElementById('obName').dispatchEvent(new Event('input',{bubbles:true}))")
        js("document.getElementById('obPickBtn').click()"); time.sleep(2.0)
        js("(()=>{const rows=[...document.querySelectorAll('#intlResults .intl-row')];if(rows.length)rows[0].click()})()"); time.sleep(1.5)
        js("HUB.showTab('home')"); time.sleep(1.2)
        v = js("window.__huberr.splice(0)")
        e = js("document.documentElement.scrollWidth")
        hscroll = js("document.body.scrollWidth > window.innerWidth + 1")
        print(tag, 'errors:', json.dumps(v)[:200], '| docScrollW:', e, '| hscroll:', hscroll)
        for tab, name in [('home',tag+'-home'),('discover',tag+'-discover'),('market',tag+'-market'),('me',tag+'-me')]:
            js(f"HUB.showTab('{tab}')"); time.sleep(0.9)
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))
            print('shot:', name)
        js("HUB.i18n.setLang('ar');HUB.showTab('home')"); time.sleep(1.2)
        r = c.send('Page.captureScreenshot', {'format': 'png'})
        open(os.path.join(QA, tag + '-ar-rtl.png'), 'wb').write(base64.b64decode(r['data']))
        print('shot:', tag + '-ar-rtl')
        js("HUB.i18n.setLang('en')")
    finally:
        proc.terminate()
run(9481, '/tmp/hubvp390', 390, 844, 'v390')
run(9482, '/tmp/hubvpdesk', 1280, 800, 'vdesk')
print('done')
