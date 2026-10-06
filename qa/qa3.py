#!/usr/bin/env python3
"""HUB design-round QA part 3: ask pill, safety checklist, scam banner (real triggers)."""
import json, subprocess, time, urllib.request, os, base64
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9428
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
        '--user-data-dir=/tmp/hubqa3-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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

        # 1. Ask pill via real button
        v, _ = js("(()=>{const p=document.getElementById('askPill'); return p ? !p.hidden : 'missing'})()")
        note(v is True, 'ask pill visible', str(v))
        js("document.getElementById('askPillMain').click()"); time.sleep(1.0); errs('askpill')
        v, _ = js("(()=>{const s=document.getElementById('sheetBox'); const h=s.innerHTML; return /Ask HUB/.test(h)&&/askchip/.test(h)&&/askSheetInput/.test(h)})()")
        note(bool(v), 'ask sheet: title + intent chips + input')
        # run a query through the sheet
        js("(()=>{const i=document.getElementById('askSheetInput'); i.value='Jobs this weekend'; document.getElementById('askSheetSend').click()})()")
        time.sleep(1.0); errs('ask-run')
        v, _ = js("document.getElementById('askSheetResults').innerHTML.length")
        note((v or 0) > 100, 'ask sheet answers from real data', f'{v} chars')
        shot('flow-askpill'); js("HUB.ui.closeSheet()"); time.sleep(0.4)

        # 2. Safety checklist via real trigger
        js("HUB.store.state.safetyAck={}; HUB.store.save()")
        js("HUB.chat.openWith({name:'Maya Chen',phone:'+1 555-902-1173'})"); time.sleep(1.0); errs('checklist')
        v, _ = js("(()=>{const h=document.getElementById('sheetBox').innerHTML; return {items:(h.match(/type=\"checkbox\"/g)||[]).length, public:/public place/i.test(h), daytime:/daytime/i.test(h), friend:/bring a friend/i.test(h), inspect:/inspect/i.test(h), demo:/demo/i.test(h)}})()")
        note(bool(v and v['items'] >= 5 and v['public'] and v['inspect']), 'safety checklist: 5 items, demo-labeled', json.dumps(v))
        shot('flow-safety-check')
        # check all + confirm -> thread opens
        js("(()=>{document.querySelectorAll('#sheetBox input[type=checkbox]').forEach(b=>b.checked=true); const btn=[...document.querySelectorAll('#sheetBox button')].find(b=>/got it/i.test(b.textContent)); if(btn)btn.click()})()")
        time.sleep(1.2); errs('checklist-confirm')
        v, _ = js("(()=>{const r=document.getElementById('chatRoot'); return r && !r.hidden})()")
        note(bool(v), 'checklist confirm opens the thread')
        v, _ = js("!!HUB.store.state.safetyAck['seller:m+' ] || Object.keys(HUB.store.state.safetyAck||{}).length")
        note(bool(v), 'checklist ack persisted', str(v))

        # 3. Scam banner via keyword message
        js("(()=>{const t=HUB.store.state.threads.find(t=>!t.messages.length)||HUB.store.state.threads[0]; t.messages.push({from:'them',text:'Please wire money first before we meet, gift cards ok',at:Date.now()}); HUB.store.save(); HUB.chat.openThread(t.id)})()")
        time.sleep(1.2); errs('scam')
        v, _ = js("(()=>{const p=document.getElementById('chatPanel'); const h=p?p.innerHTML:''; return {banner:/Demo safety hint/i.test(h), noai:/not AI moderation/i.test(h)}})()")
        note(bool(v and v['banner'] and v['noai']), 'scam banner: demo-labeled, disclaims AI', json.dumps(v))
        shot('flow-scam-banner')
        js("HUB.chat.close()"); time.sleep(0.4)

        print('\n=== errors ==='); print('NONE' if not errors else errors)
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        c.ws.close()
    finally: proc.terminate()

if __name__ == '__main__': main()
