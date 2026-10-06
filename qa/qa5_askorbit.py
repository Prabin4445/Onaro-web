#!/usr/bin/env python3
"""Focused check: Ask Orbit pill -> #askPillMain opens sheet (real user tap target)."""
import json, subprocess, time, urllib.request, os, base64
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9431
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors = []

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12)
        self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ' recv: ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubqa5-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url'])
                break
            except Exception: continue
        else: raise RuntimeError('no chrome target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')

        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                res = (r or {}).get('result', {})
                return res.get('value'), res.get('exceptionDetails')
            except Exception as e: return None, str(e)[:160]

        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))
            print('shot:', name)

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        for _ in range(4):
            st, _ = js("(()=>{const n=document.getElementById('obName'); if(!n) return 'gone'; n.value='QA Tester'; const s=document.getElementById('obCampus'); if(s) s.selectedIndex=1; document.getElementById('obGo').click(); return 'clicked'})()")
            time.sleep(1)
            if st == 'gone': break
        print('onboarding:', st)
        time.sleep(1)

        v, _ = js("(()=>{const b=document.getElementById('askPillMain'); if(!b) return 'NOBTN'; b.click(); return 'clicked'})()")
        time.sleep(1.2)
        print('askPillMain click:', v)
        errs = js("window.__huberr.splice(0)")
        print('errors after ask tap:', json.dumps(errs))
        h, _ = js("(()=>{const s=document.getElementById('sheetBox'); return s ? s.innerHTML.slice(0, 120) : 'NO SHEETBOX'})()")
        print('sheetBox head:', str(h)[:200])
        t, _ = js("(()=>{const s=document.getElementById('sheetBox'); return s ? s.textContent.slice(0, 120) : ''})()")
        print('sheetBox text head:', str(t)[:200])
        hv, _ = js("document.getElementById('sheetHost').hidden")
        print('sheetHost.hidden =', hv, '(false means sheet is visible)')
        ok = (not hv) and ('Ask Onaro' in str(t))
        print(('PASS' if ok else 'FAIL'), 'ask Orbit sheet opens on real pill tap')
        shot('flow-askorbit')
        # also check ask header icon (ask-hub png) rendered, not emoji fallback
        fb, _ = js("(()=>{const s=document.getElementById('sheetBox'); return s ? s.querySelectorAll('.ico-fb').length : -1})()")
        print('emoji fallbacks in ask sheet:', fb)
        print('console errors:', 'NONE' if not errs[0] else json.dumps(errs[0])[:300])
        c.ws.close()
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
