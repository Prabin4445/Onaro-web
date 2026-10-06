#!/usr/bin/env python3
"""HUB QA part 4: verify openThread fix + scam banner visible + market radius on-tab."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9429
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)
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
        '--user-data-dir=/tmp/hubqa4-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                res = (r or {}).get('result', {}); return res.get('value'), res.get('exceptionDetails')
            except Exception as e: return None, str(e)[:160]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:300])
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        for _ in range(4):
            st, _ = js("(()=>{const n=document.getElementById('obName'); if(!n) return 'gone'; n.value='QA Tester'; const s=document.getElementById('obCampus'); if(s) s.selectedIndex=1; document.getElementById('obGo').click(); return 'clicked'})()")
            time.sleep(1)
            if st == 'gone': break
        time.sleep(1); errs('load')

        # market tab + radius on-tab
        js("HUB.showTab('market')"); time.sleep(1.2); errs('market')
        v, _ = js("(()=>{const p=[...document.querySelectorAll('#view-market .seg button, #view-market [data-r]')]; return p.map(b=>b.textContent.trim()).join('|')})()")
        note('1' in str(v) and 'City' in str(v), 'radius control visible on market tab', str(v)[:60])
        js("(()=>{const b=[...document.querySelectorAll('#view-market button')].find(e=>/^25/.test(e.textContent.trim())); if(b)b.click()})()")
        time.sleep(1.0); errs('radius25')
        v, _ = js("document.querySelector('#view-market').textContent.includes('Within 25 mi')")
        note(bool(v), 'pill updates to Within 25 mi')
        shot('flow-market-radius')

        # checklist -> confirm -> thread VISIBLE (the fix)
        js("HUB.store.state.safetyAck={}; HUB.store.save()")
        js("HUB.chat.openWith({name:'Maya Chen',phone:'+1 555-902-1173'})"); time.sleep(1.0); errs('checklist')
        js("(()=>{document.querySelectorAll('#sheetBox input[type=checkbox]').forEach(b=>b.checked=true); const btn=[...document.querySelectorAll('#sheetBox button')].find(b=>/got it/i.test(b.textContent)); if(btn)btn.click()})()")
        time.sleep(1.2); errs('confirm')
        v, _ = js("(()=>{const r=document.getElementById('chatRoot'); return r && !r.hidden && document.getElementById('chatPanel').innerHTML.includes('Maya Chen')})()")
        note(bool(v), 'FIXED: thread opens visible after checklist confirm')
        shot('flow-thread-open')

        # scam banner visible in open thread
        js("(()=>{const t=HUB.store.state.threads.find(t=>t.title==='Maya Chen'); t.messages.push({from:'them',text:'wire money first, gift cards ok',at:Date.now()}); HUB.store.save(); HUB.chat.openThread(t.id)})()")
        time.sleep(1.2); errs('scam')
        v, _ = js("(()=>{const h=document.getElementById('chatPanel').innerHTML; return /Demo safety hint/.test(h) && /not AI moderation/.test(h)})()")
        note(bool(v), 'scam banner rendered in visible thread')
        shot('flow-scam-banner')
        js("HUB.chat.close()")

        print('\n=== errors ==='); print('NONE' if not errors else errors)
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        c.ws.close()
    finally: proc.terminate()
if __name__ == '__main__': main()
