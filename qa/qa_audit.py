#!/usr/bin/env python3
"""Audit sweep: every tab + key overlays, dark + light, 390x844.
Screenshots + horizontal-overflow + overlay-viewport-containment assertions.
Fresh profiles, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9561
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)
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

OVERLAYS = [
    ('gpa-add',      "HUB.gpa.addSheet()"),
    ('gpa-edit',     "HUB.gpa.courseSheet((HUB.store.state.gpaCourses||[])[0]||null)"),
    ('wx-detail',    "HUB.wxhome.openDetail()"),
    ('glance-spend', "HUB.glance.openDetail('spend')"),
    ('gym-setup',    "HUB.gym.openSetup()"),
    ('capsule',      "HUB.views.daily.openCapsuleSheet()"),
    ('chat-list',    "HUB.chat.openList()"),
    ('search',       "HUB.search.open()"),
    ('notif',        "HUB.notifications.open()"),
    ('pulse',        "HUB.pulse.open()"),
]
CLOSE_JS = "try{HUB.ui.closeSheet();}catch(e){};for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){}"
CONTAIN_JS = """(()=>{const bad=[];const rs=['.sheethost','.chatroot','.mkzoom','.gy-bd','.gy-drawer','.wlcmhost'];
for(const s of rs){document.querySelectorAll(s).forEach(el=>{if(el.hidden||getComputedStyle(el).display==='none')return;
const r=el.getBoundingClientRect();
if(r.left<-1||r.right>innerWidth+1||r.top<-1||r.bottom>innerHeight+1)bad.push(s+' '+JSON.stringify([r.left|0,r.top|0,r.right|0,r.bottom|0]));});}
return bad;})()"""

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-audit-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir=/tmp/hubqa-audit-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
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
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def nox(label):
            v = js("(document.documentElement.scrollWidth<=innerWidth+1)")
            note(v, f'{theme}: {label} no horizontal overflow', f"scrollWidth={js('document.documentElement.scrollWidth')} innerWidth={js('innerWidth')}")

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()});")
        time.sleep(1)

        for tab in ['home', 'daily', 'market', 'work', 'groups', 'me']:
            js(f"HUB.showTab('{tab}');"); time.sleep(2.5)
            nox(f'tab {tab}')
            shot(f'audit-tab-{tab}-{theme}.png')
            # ask pill within viewport
            ap = js("(()=>{const e=document.getElementById('askPill');if(!e||e.hidden)return 'hidden';const r=e.getBoundingClientRect();return (r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1)?'ok':JSON.stringify([r.left|0,r.top|0,r.right|0,r.bottom|0]);})()")
            note(ap in ('ok', 'hidden'), f'{theme}: tab {tab} ask pill contained', str(ap))
        errs('tabs')

        for name, expr in OVERLAYS:
            js(CLOSE_JS); time.sleep(0.5)
            js(f"try{{{expr}}}catch(e){{window.__ovlerr=String(e&&e.message||e);}}")
            time.sleep(1.5)
            oerr = js("window.__ovlerr||null"); js("window.__ovlerr=null;")
            note(not oerr, f'{theme}: overlay {name} opens', oerr or '')
            bad = js(CONTAIN_JS)
            note(not bad, f'{theme}: overlay {name} viewport-contained', json.dumps(bad)[:220] if bad else '')
            shot(f'audit-ovl-{name}-{theme}.png')
            nox(f'overlay {name}')
            js(CLOSE_JS); time.sleep(0.8)
        errs('overlays')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run(th)
n = len(checks); p = sum(1 for ok, _ in checks if ok)
print(f'\n==== AUDIT {p}/{n} passed ====')
for ok, label in checks:
    if not ok: print('FAILED:', label)
