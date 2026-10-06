#!/usr/bin/env python3
"""Audit sweep round 2: deep views (listing detail, lightbox, job chat, club page,
household detail, people profile, me edit, appt add, ask sheet). Dark theme, 390x844."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9562
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

theme = 'dark'
CLOSE_JS = ("try{HUB.ui.closeSheet();}catch(e){};"
  "for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};"
  "['gyBd','gyDrawer'].forEach(function(id){var e=document.getElementById(id);if(e)e.remove();});"
  "document.querySelectorAll('.mkzoom').forEach(function(e){e.remove();});"
  "try{HUB.showTab('home');}catch(e){}")

shutil.rmtree(f'/tmp/hubqa-audit2-{theme}', ignore_errors=True)
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
    f'--user-data-dir=/tmp/hubqa-audit2-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        sw = js("document.documentElement.scrollWidth"); iw = js("innerWidth")
        note(sw <= iw + 1, f'{theme}: {label} no horizontal overflow', f'scrollWidth={sw} innerWidth={iw}')
    def click(sel):
        return js(f"(()=>{{const e=document.querySelector({sel!r});if(!e)return 'missing';e.scrollIntoView({{block:'center'}});e.click();return 'clicked';}})()")

    js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
    time.sleep(4)
    js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    js("document.body.classList.add('dark');")
    time.sleep(1)

    # 1. market listing detail
    js("HUB.showTab('market');"); time.sleep(2)
    note(click("[data-listing]") == 'clicked', f'{theme}: listing card clickable')
    time.sleep(1.5); shot('audit2-listing-dark.png'); nox('listing detail')
    # 2. photo lightbox
    ph = click("[data-photo]")
    note(ph == 'clicked', f'{theme}: listing photo clickable', ph)
    time.sleep(1.5)
    note(js("!!document.querySelector('.mkzoom:not([hidden])')"), f'{theme}: lightbox open')
    shot('audit2-lightbox-dark.png'); nox('lightbox')
    js(CLOSE_JS); time.sleep(1)

    # 3. job chat
    js("HUB.showTab('work');"); time.sleep(2)
    note(click("[data-jchat]") == 'clicked', f'{theme}: job chat button clickable')
    time.sleep(1.5); shot('audit2-jobchat-dark.png'); nox('job chat')
    js(CLOSE_JS); time.sleep(1)

    # 4. club page
    js("HUB.showTab('groups');"); time.sleep(2)
    note(click("[data-club]") == 'clicked', f'{theme}: club card clickable')
    time.sleep(1.5); shot('audit2-club-dark.png'); nox('club page')
    js(CLOSE_JS); time.sleep(1)

    # 5. household detail
    js("HUB.showTab('groups');"); time.sleep(2)
    hh = js("(()=>{const b=document.querySelector('[data-sub=\"hh\"]');if(b)b.click();return !!b;})()")
    time.sleep(1)
    note(click(".hh-card") == 'clicked', f'{theme}: household card clickable', f'hh-tab={hh}')
    time.sleep(1.5); shot('audit2-household-dark.png'); nox('household detail')
    js(CLOSE_JS); time.sleep(1)

    # 6. people profile
    js("HUB.showTab('groups');"); time.sleep(2)
    js("(()=>{const b=document.querySelector('[data-sub=\"people\"]');if(b)b.click();})()")
    time.sleep(1.5)
    pid = js("(()=>{const p=(HUB.people&&HUB.people.visiblePeople&&HUB.people.visiblePeople()[0])||null;if(p){HUB.people.openProfile(p.id);return p.id;}return null;})()")
    note(bool(pid), f'{theme}: people profile opens', str(pid))
    time.sleep(1.5); shot('audit2-people-dark.png'); nox('people profile')
    js(CLOSE_JS); time.sleep(1)

    # 7. me edit sheet
    js("HUB.showTab('me');"); time.sleep(2)
    note(click("#meEditBtn") == 'clicked', f'{theme}: me edit clickable')
    time.sleep(1.5); shot('audit2-meedit-dark.png'); nox('me edit')
    js(CLOSE_JS); time.sleep(1)

    # 8. appointment add sheet
    js("HUB.showTab('home');"); time.sleep(2.5)
    note(click("[data-appt-add]") == 'clicked', f'{theme}: appt add clickable')
    time.sleep(1.5); shot('audit2-apptadd-dark.png'); nox('appt add')
    js(CLOSE_JS); time.sleep(1)

    # 9. ask sheet
    js("try{HUB.askHUB.open()}catch(e){window.__askerr=String(e)}")
    time.sleep(1.5)
    note(not js("window.__askerr||null"), f'{theme}: ask sheet opens', js("window.__askerr||''"))
    shot('audit2-ask-dark.png'); nox('ask sheet')
    js(CLOSE_JS); time.sleep(1)
    errs('round2')
finally:
    proc.terminate()
n = len(checks); p = sum(1 for ok, _ in checks if ok)
print(f'\n==== AUDIT2 {p}/{n} passed ====')
for ok, label in checks:
    if not ok: print('FAILED:', label)
