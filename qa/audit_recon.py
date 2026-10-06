#!/usr/bin/env python3
"""Recon: dump HUB module APIs + clickable inventory per tab, dark & light.
Fresh profile per theme. 390x844 mobile emulation, iPhone UA."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) '
             'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 '
             'Mobile/15E148 Safari/604.1')

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
    prof = f'/tmp/hubqa-recon-{theme}'
    shutil.rmtree(prof, ignore_errors=True)
    port = 9731 if theme == 'dark' else 9732
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={port}', '--remote-allow-origins=*',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Network.enable', {})
        c.send('Network.setUserAgentOverride', {'userAgent': IPHONE_UA, 'userAgentMetadata': {'mobile': True}})
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Page.reload')
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        time.sleep(5)
        # dismiss welcome, seed name, set theme
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js("document.body.classList.%s('dark');" % ('add' if theme == 'dark' else 'remove'))
        time.sleep(1)
        apis = js("""(()=>{const o={};for(const k of Object.keys(window.HUB||{})){try{o[k]=Object.keys(HUB[k]||{}).slice(0,80);}catch(e){o[k]='?'}}return o;})()""")
        open(f'/tmp/recon-apis-{theme}.json', 'w').write(json.dumps(apis, indent=1))
        inv = {}
        for tab in ['home', 'daily', 'market', 'work', 'groups', 'me']:
            js(f"HUB.showTab('{tab}');"); time.sleep(2)
            elts = js("""(()=>{const r=[];document.querySelectorAll('#view-active button,#views .view.active button,button,a,[data-tap],[onclick],[data-listing],[data-club],[data-photo],[data-jchat],[data-sub]').forEach(e=>{const v=e.getAttribute('data-sub')||e.getAttribute('data-listing')||e.getAttribute('data-club')||e.getAttribute('data-jchat');r.push({tag:e.tagName,txt:(e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,40),id:e.id||'',cls:(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className||'').toString().slice(0,60),attr:v||'',hidden:e.hidden||e.offsetParent===null});});return r.slice(0,120);})()""")
            # simpler: all visible buttons in active view
            elts = js("""(()=>{const v=document.querySelector('#views .view.active')||document.body;const r=[];v.querySelectorAll('button,[data-tap],a[href]').forEach(e=>{const t=(e.innerText||e.getAttribute('aria-label')||e.title||'').trim().slice(0,45);r.push({tag:e.tagName,txt:t,id:e.id||'',cls:String(e.className||'').slice(0,70),vis:e.offsetParent!==null});});return r;})()""")
            inv[tab] = elts
        open(f'/tmp/recon-inv-{theme}.json', 'w').write(json.dumps(inv, indent=1))
        print(f'{theme}: apis={len(apis)} tabs inventoried')
    finally:
        proc.terminate()

for t in ['dark', 'light']:
    run(t)
print('done')
