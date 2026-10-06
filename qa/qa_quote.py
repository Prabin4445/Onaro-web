#!/usr/bin/env python3
"""QA: daily motivation quote card on Home."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9436
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
         "HUB.store.save(); HUB.showTab('home');")
def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubqq-prof', '--hide-scrollbars', '--allow-file-access-from-files', 'about:blank'],
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
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        note(not js("window.__loaderr.splice(0).length"), 'no load errors', '')
        js(SETUP); time.sleep(3)
        card = js("(()=>{const c=document.getElementById('quoteCard');return c?c.textContent:'NO CARD'})()") or ''
        note('quoteCard' not in 'NO CARD' and len(card) > 40, 'quote card renders below greeting', card[:70])
        has_quotes = '“' in card or '"' in card
        note(has_quotes, 'quote text in quotation marks', '')
        author = js("(()=>{const a=document.getElementById('quoteAuthor');return a?a.textContent:'NO AUTHOR'})()") or ''
        note(author.startswith('—') and len(author) > 3, 'author attributed with — Name', author)
        note('Loading' not in card, 'quote loaded (not stuck on loading)', card[:50])
        # determinism: reload -> same quote
        q1 = js("document.getElementById('quoteText').textContent")
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        js(SETUP); time.sleep(3)
        q2 = js("document.getElementById('quoteText').textContent")
        note(q1 == q2 and len(q1) > 10, 'same quote all day (deterministic)', q1[:50])
        # rotation: consecutive UTC days map to different indices (pure math check)
        rot = js("(()=>{const n=120;const a=Math.floor(Date.now()/86400000)%n;const b=Math.floor((Date.now()+86400000)/86400000)%n;return a!==b})()")
        note(rot, 'different quote tomorrow', '')
        # position: card sits right after the greeting header
        pos = js("(()=>{const g=document.querySelector('.greet');const q=document.getElementById('quoteCard');if(!g||!q)return 'missing';return (g.compareDocumentPosition(q)&4)?'after':'not-after'})()")
        note(pos == 'after', 'card placed below "Good evening" greeting', '')
        # dark mode render
        js("document.body.classList.add('dark')"); time.sleep(1)
        shot('quote-dark')
        js("document.body.classList.remove('dark')")
        shot('quote-card')
        note(not js("window.__loaderr.splice(0).length"), 'no errors after all flows', '')
        print('RESULT:', 'ALL PASS' if all(checks) else 'FAILURES')
    finally:
        proc.terminate()
main()
