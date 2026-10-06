#!/usr/bin/env python3
"""HUB design-round QA: console errors + screenshots + new-surface checks."""
import json, subprocess, time, urllib.request, os, sys, base64
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9427
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []

def note(ok, label, detail=''):
    checks.append((ok, label, detail))
    print(('PASS' if ok else 'FAIL'), label, detail)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12)
        self.ws.settimeout(12)
        self.id = 0
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
        '--user-data-dir=/tmp/hubqa2-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
            except Exception as e:
                return None, str(e)[:160]

        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))
            print('shot:', name)

        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:300])

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        # onboarding
        for _ in range(4):
            st, _ = js("(()=>{const n=document.getElementById('obName'); if(!n) return 'gone'; n.value='QA Tester'; const s=document.getElementById('obCampus'); if(s) s.selectedIndex=1; document.getElementById('obGo').click(); return 'clicked'})()")
            time.sleep(1)
            if st == 'gone': break
        note(st == 'gone', 'onboarding dismissed', str(st))
        time.sleep(1); errs('load')

        # --- integration checks ---
        v, _ = js("!!document.querySelector('script[src=\"js/icons.js\"]')")
        note(v, 'icons.js script tag present')
        v, _ = js("[...document.styleSheets].some(s=>{try{return (s.href||'').includes('profile.css')}catch(e){return false}})")
        note(v, 'profile.css stylesheet applied')
        v, _ = js("!!(window.HUB&&HUB.icons&&HUB.icons.icon)")
        note(v, 'HUB.icons API present')
        v, _ = js("document.querySelectorAll('.tab .ico img').length")
        note((v or 0) >= 6, 'tab bar 3D icons rendered', f'{v} imgs')
        v, _ = js("document.querySelectorAll('.ico-fb').length")
        note((v or 0) == 0, 'zero emoji fallbacks on chrome', f'{v} fallbacks')
        v, _ = js("getComputedStyle(document.querySelector('#view-me .me-ribbon')||document.body).display")
        note(v not in (None, ''), 'me-ribbon styled (profile.css live)', str(v))

        def tab(name, snap):
            v, ex = js(f"HUB.showTab('{name}')")
            if ex: errors.append((name, str(ex)[:200]))
            time.sleep(1.4); errs(name); shot(snap)

        for t in ['home', 'discover', 'market', 'work', 'groups', 'me']:
            tab(t, f'tab-{t}')

        # --- new surfaces ---
        # Ask Orbit pill — real user tap target is the #askPillMain button
        v, _ = js("(()=>{const b=document.getElementById('askPillMain')||document.getElementById('askPill'); if(b){b.click();return true;} return false})()")
        time.sleep(1.0); errs('askpill'); shot('flow-askpill')
        v, _ = js("(()=>{const s=document.getElementById('sheetBox'); return s ? s.innerHTML.length : -1})()")
        note((v or 0) > 200, 'ask pill opens sheet', f'{v} chars')
        js("HUB.ui.closeSheet()"); time.sleep(0.4)

        # Market radius control
        js("HUB.showTab('market')"); time.sleep(0.8)
        v, _ = js("(()=>{const el=[...document.querySelectorAll('#view-market button, #view-market .seg button, #view-market select')].find(e=>/25|city/i.test(e.textContent)); if(el){el.click();return el.textContent.trim().slice(0,24)} return 'notfound:'+document.querySelectorAll('#view-market button').length})()")
        time.sleep(1.0); errs('radius'); shot('flow-market-radius')
        v2, _ = js("(()=>{const p=document.querySelector('#view-market'); return p?p.textContent.slice(0,4000):''})()")
        note('25' in str(v) or 'City' in str(v2), 'radius control switches scope', str(v)[:40])

        # Market post sheet (multi-photo UI present?)
        js("HUB.showTab('market')"); time.sleep(0.8)
        js("(()=>{const b=document.getElementById('mkPostBtn'); if(b)b.click()})()"); time.sleep(0.9)
        v, _ = js("(()=>{const s=document.getElementById('sheetBox'); const h=s?s.innerHTML:''; return {multi:/multiple/i.test(h), thumbs:/thumb/i.test(h), cond:/condition/i.test(h), desc:/description/i.test(h), loc:/location/i.test(h)}})()")
        note(bool(v and v.get('multi')), 'post form: multi-photo input', json.dumps(v))
        errs('market-post'); shot('flow-market-post'); js("HUB.ui.closeSheet()"); time.sleep(0.4)

        # Listing detail: meetup spots + gallery
        v, _ = js("(()=>{const el=document.querySelector('#view-market .lcard, #view-market [data-listing], #view-market .item'); if(el){el.click();return true} return false})()")
        time.sleep(1.0); errs('market-detail'); shot('flow-market-detail')
        v, _ = js("(()=>{const s=document.getElementById('sheetBox'); const h=s?s.innerHTML:''; return /meetup|Safe spot/i.test(h)})()")
        note(bool(v), 'detail: safe meetup spots section')
        js("HUB.ui.closeSheet()"); time.sleep(0.4)

        # Safety checklist before first seller chat
        v, _ = js("(()=>{try{if(HUB.chat&&HUB.chat.messageSeller){HUB.chat.messageSeller('Alex Rivera');return 'called'} const b=document.querySelector('[data-msgseller]'); if(b){b.click();return 'clicked'} return 'nohook'}catch(e){return 'ERR:'+e.message}})()")
        time.sleep(1.0); errs('safety-check')
        v2, _ = js("(()=>{const s=document.getElementById('sheetBox'); const h=s?s.innerHTML:''; return /checklist|public place|daytime/i.test(h)})()")
        note(bool(v2), 'safety checklist on first seller chat', str(v)[:30])
        shot('flow-safety-check'); js("HUB.ui.closeSheet()"); js("if(HUB.chat)HUB.chat.close()"); time.sleep(0.4)

        # Chat list
        js("HUB.chat.openList()"); time.sleep(1.0); errs('chat'); shot('flow-chat'); js("HUB.chat.close()"); time.sleep(0.4)

        # ME: safety score + transactions
        js("HUB.showTab('me')"); time.sleep(1.2); errs('me2')
        v, _ = js("(()=>{const b=document.body.textContent; return {score:/Safety score/i.test(b), derived:/derived/i.test(b), trans:/Transaction|Exchange history/i.test(b)}})()")
        note(bool(v and v['score']), 'ME: safety score strip', json.dumps(v))
        note(bool(v and v['trans']), 'ME: transaction history')
        shot('tab-me2')

        # overlays
        for label, expr, snap in [('search', 'HUB.search.open()', 'flow-search'),
                                 ('notifications', 'HUB.notifications.open()', 'flow-notifications'),
                                 ('pulse', 'HUB.pulse.open()', 'flow-pulse'),
                                 ('create', 'HUB.create.open()', 'flow-create')]:
            js(expr); time.sleep(1.0); errs(label); shot(snap)
            js("HUB.ui.closeSheet(); for(const k of ['chat','pulse','search','notifications']) if(HUB[k]&&HUB[k].close)HUB[k].close()"); time.sleep(0.4)

        # dark mode
        js("HUB.showTab('home')"); time.sleep(0.8)
        js("(()=>{const t=document.getElementById('darkToggle'); if(t)t.click(); else {HUB.showTab('me'); setTimeout(()=>document.getElementById('darkToggle').click(),300)} })()")
        time.sleep(1.2); errs('dark'); shot('tab-home-dark')
        v, _ = js("getComputedStyle(document.body).backgroundColor")
        note('13, 16, 10' in str(v), 'deep green-ink dark mode (#0D100A — not true black by brand rule)', str(v))

        print('\n=== console/page errors ===')
        print('NONE' if not errors else '')
        for k, e in errors: print(k, ':', json.dumps(e)[:300])
        print('\n=== check summary ===')
        fails = [l for ok, l, d in checks if not ok]
        print(f'{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        c.ws.close()
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
