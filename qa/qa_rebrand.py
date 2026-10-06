#!/usr/bin/env python3
"""Onaro rebrand QA: wordmark, title, Ask Onaro, visible strings, console errors."""
import json, subprocess, time, urllib.request, os, base64, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9441
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
        '--user-data-dir=/tmp/hubqa-rebrand-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)

        # 1. Welcome screen brand (before onboarding)
        wtxt, _ = js("(()=>{const b=document.querySelector('.wlcm-brand .brand-name'); return b?b.textContent.replace(/\\s+/g,' '):'MISSING'})()")
        shot('rebrand-welcome')
        note(wtxt and wtxt.strip().endswith('naro'), 'welcome wordmark reads Onaro', repr(wtxt))
        wtitle, _ = js("(()=>{const els=[...document.querySelectorAll('.wlcm h1,.wlcm h2,.wlcm-card h1,.wlcm-card h2,h1,h2')]; const el=els.find(e=>/Welcome to/.test(e.textContent)); return el?el.textContent.trim():'MISSING'})()")
        note(wtitle == 'Welcome to Onaro 🎉', 'welcome title', repr(wtitle))

        # 2. Complete onboarding
        for _ in range(4):
            st, _ = js("(()=>{const n=document.getElementById('obName'); if(!n) return 'gone'; n.value='QA Tester'; const s=document.getElementById('obCampus'); if(s) s.selectedIndex=1; document.getElementById('obGo').click(); return 'clicked'})()")
            time.sleep(1)
            if st == 'gone': break

        # 3. Document title + header wordmark
        title, _ = js("document.title")
        note(title == 'Onaro — Everything in your orbit', 'document title', repr(title))
        htxt, _ = js("(()=>{const b=document.querySelector('.brand-name'); return b?b.textContent.replace(/\\s+/g,' '):'MISSING'})()")
        note(htxt and htxt.strip().endswith('naro') and 'rbit' not in htxt, 'header wordmark reads Onaro', repr(htxt))
        aria, _ = js("(()=>{const b=document.querySelector('.brand-name'); return b?b.getAttribute('aria-label'):'MISSING'})()")
        note(aria == 'Onaro', 'wordmark aria-label', repr(aria))
        shot('rebrand-header')

        # 4. Ask pill label
        asklbl, _ = js("(()=>{const b=document.getElementById('askPillMain'); return b?b.textContent.trim():'MISSING'})()")
        note(asklbl == 'Ask Onaro', 'ask pill label', repr(asklbl))

        # 5. Open search, check title
        js("(()=>{const b=document.getElementById('searchBtn'); if(b) b.click()})()")
        time.sleep(1)
        stitle, _ = js("(()=>{const h=[...document.querySelectorAll('h2')].find(e=>/Search/.test(e.textContent)); return h?h.textContent.replace(/\\s+/g,' ').trim():'MISSING'})()")
        note(stitle == 'Search Onaro', 'search title', repr(stitle))
        js("if(HUB.search&&HUB.search.close)HUB.search.close()")

        # 6. No visible 'Orbit' text anywhere (word-boundary, Latin)
        orbits, _ = js("(()=>{const t=document.body.innerText||''; const m=t.match(/\\bOrbit\\b/g); return m?m.slice(0,5):[]})()")
        note(not orbits, 'no visible Latin Orbit text', repr(orbits))

        # 7. Tabs render
        for tab, sel in [('home', '#tab-home'), ('discover', '#tab-discover'), ('market', '#tab-market'), ('work', '#tab-work'), ('groups', '#tab-groups'), ('me', '#tab-me')]:
            js(f"(()=>{{const b=document.querySelector('{sel}'); if(b) b.click()}})()")
            time.sleep(0.8)
        shot('rebrand-tabs-me')

        # 8. Console errors
        errs, _ = js("window.__huberr.splice(0)")
        if errs: errors.append(('rebrand', errs))
        note(not errs, 'zero console errors', json.dumps(errs)[:200] if errs else '')
    finally:
        proc.terminate()

    fails = [l for ok, l in checks if not ok]
    print(f"\n{len(checks)-len(fails)}/{len(checks)} passed")
    if fails: print('FAILURES:', fails)
    raise SystemExit(1 if fails else 0)

main()
