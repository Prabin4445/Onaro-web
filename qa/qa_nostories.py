#!/usr/bin/env python3
"""QA: Stories feature fully removed — app boots clean, all tabs render, no story UI."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9443
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
def run(theme):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-nostories-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Runtime.enable'); c.send('Page.enable')
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        v = js("window.__huberr.splice(0)")
        note(not v, f'{theme}: boot with zero console errors', json.dumps(v)[:200] if v else '')
        # seed profile, hide welcome, set theme
        js("try{var st=JSON.parse(localStorage.getItem('hub_v1')||'null'); if(st){st.profile=st.profile||{}; st.profile.name='QA'; localStorage.setItem('hub_v1',JSON.stringify(st));} var w=document.getElementById('wlcmHost'); if(w) w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()});")
        time.sleep(1)
        # story absence checks
        v = js("typeof HUB.stories")
        note(v == 'undefined', f'{theme}: HUB.stories undefined', str(v))
        v = js("!!document.getElementById('storyTrayHost')||!!document.getElementById('storyHighlightsHost')")
        note(v is False, f'{theme}: no story DOM hosts', str(v))
        v = js("document.documentElement.innerHTML.includes('data-story-new')")
        note(v is False, f'{theme}: no data-story-new buttons', str(v))
        # every tab renders
        for tab in ['home', 'daily', 'market', 'work', 'groups', 'me']:
            js(f"HUB.showTab('{tab}')")
            time.sleep(1.2)
            v = js(f"(()=>{{const el=document.getElementById('view-{tab}'); return el? (el.hidden?'hidden':el.textContent.length) : 'missing';}})()")
            note(isinstance(v, int) and v > 200, f'{theme}: tab {tab} renders', f'chars={v}')
            errs = js("window.__huberr.splice(0)")
            note(not errs, f'{theme}: tab {tab} zero errors', json.dumps(errs)[:200] if errs else '')
            if tab in ('home', 'me'):
                shot(f'nostory-{tab}-{theme}.png')
        # tab bar has no dead tabs
        v = js("Array.from(document.querySelectorAll('#tabbar .tab')).map(b=>b.dataset.tab).join(',')")
        note(v == 'home,daily,market,work,groups,me', f'{theme}: tab bar intact', str(v))
    finally:
        proc.terminate()
for theme in ['dark', 'light']:
    run(theme)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
