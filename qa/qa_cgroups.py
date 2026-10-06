#!/usr/bin/env python3
"""QA: Community Groups feature — boot clean, discovery carousel, search,
create->live, join requests, admin approve, notifications, lazy locales."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9447
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
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

def run(theme, full):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-cgroups-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='QA'; HUB.store.save(); var w=document.getElementById('wlcmHost'); if(w) w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('groups');")
        time.sleep(1.5)
        errs('groups tab render')

        # clubs is the default sub: search input present
        v = js("!!document.getElementById('cgSearch')")
        note(v, f'{theme}: clubs discovery is default sub', str(v))
        # seeded live groups in the 3D carousel (4 live seeds within 50 mi)
        v = js("document.querySelectorAll('#view-groups .gcard').length")
        note(v == 4, f'{theme}: 4 live seed groups in carousel', f'found={v}')
        # cover-flow transforms applied
        v = js("(()=>{const c=document.querySelector('#view-groups .gcard'); return c?c.style.transform+'|'+c.style.opacity:'nocard';})()")
        note(isinstance(v, str) and 'rotateY' in v, f'{theme}: cover-flow transform applied', str(v)[:70])
        # distance labels present
        v = js("document.querySelector('#view-groups .gcard').textContent")
        note('mi away' in str(v), f'{theme}: distance label on card', str(v)[:60])
        shot(f'cg-discovery-{theme}.png')

        # carousel scrolls horizontally
        v = js("(()=>{const f=document.querySelector('#view-groups .flow'); if(!f) return 'noflow'; f.scrollLeft=150; return f.scrollWidth+'>'+f.clientWidth;})()")
        note(isinstance(v, str) and 'noflow' not in v, f'{theme}: carousel scrollable', str(v))

        # search filters
        js("const si=document.getElementById('cgSearch'); si.value='pubg'; si.dispatchEvent(new Event('input',{bubbles:true}));")
        time.sleep(0.8)
        v = js("Array.from(document.querySelectorAll('#cgResults .gcard h3')).map(h=>h.textContent).join('|')")
        note(v == 'PUBG Squad', f'{theme}: search filters to PUBG Squad', str(v))
        js("const si2=document.getElementById('cgSearch'); si2.value=''; si2.dispatchEvent(new Event('input',{bubbles:true}));")
        time.sleep(0.8)

        if not full:
            js("HUB.showTab('home');"); time.sleep(1.5)
            v = js("document.querySelectorAll('#homeCg .gcard').length")
            note(v == 4, f'{theme}: home groups-near-you carousel', f'found={v}')
            shot(f'cg-home-{theme}.png')
            return

        # --- create group ---
        js("document.getElementById('cgNew').click()"); time.sleep(0.8)
        v = js("!!document.getElementById('cgName')")
        note(v, f'{theme}: create sheet opens', str(v))
        js("document.getElementById('cgName').value='Test Climbers';")
        js("document.getElementById('cgDesc').value='Evening climbing crew, all levels.';")
        js("document.getElementById('cgSave').click()"); time.sleep(1.0)
        v = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Test Climbers'); return g?((g.mine&&!g.live)?'draft-ok':'state-bad'):'missing';})()")
        note(v == 'draft-ok', f'{theme}: group created as draft', str(v))
        errs('create group')
        # make it live from the detail page
        v = js("!!document.getElementById('cgLive')")
        note(v, f'{theme}: detail page shows make-live (admin)', str(v))
        js("document.getElementById('cgLive').click()"); time.sleep(1.0)
        v = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Test Climbers'); return g&&g.live?'live-ok':'bad';})()")
        note(v == 'live-ok', f'{theme}: group went live', str(v))
        # back to discovery: new group in carousel
        js("document.getElementById('cgBack').click()"); time.sleep(1.0)
        v = js("Array.from(document.querySelectorAll('#cgResults .gcard h3')).map(h=>h.textContent).join('|')")
        note('Test Climbers' in str(v), f'{theme}: live group in discovery carousel', str(v)[:80])

        # --- notifications: join request row -> opens group page ---
        js("HUB.notifications.open()"); time.sleep(1.2)
        v = js("document.getElementById('hubNotifRows').textContent")
        note('Riley Patel' in str(v) and 'Weekend Hikers' in str(v), f'{theme}: join-request notification row', str(v)[:80])
        shot(f'cg-notif-{theme}.png')
        js("(()=>{const el=Array.from(document.querySelectorAll('#hubNotifRows .item')).find(e=>e.textContent.includes('Riley Patel')); if(el) el.click();})()")
        time.sleep(1.0)
        v = js("!!document.getElementById('cgBack') && document.querySelector('#view-groups .greet').textContent.includes('Weekend Hikers')")
        note(v, f'{theme}: notif tap opens group page', str(v))
        errs('notifications')

        # --- admin approve ---
        v = js("!!document.querySelector('[data-appr=\"Riley Patel\"]')")
        note(v, f'{theme}: pending request visible to admin', str(v))
        js("document.querySelector('[data-appr=\"Riley Patel\"]').click()"); time.sleep(1.0)
        v = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers'); return 'members:'+g.members.join(',')+' req:'+g.requests.length;})()")
        note('Riley Patel' in str(v) and 'req:0' in str(v), f'{theme}: approve adds member, clears request', str(v))

        # --- request access as non-member ---
        gid = js("HUB.store.state.cgroups.find(g=>g.name==='Math Study Group').id")
        js(f"HUB.cgroups.openClub('{gid}')"); time.sleep(1.0)
        shot(f'cg-detail-{theme}.png')
        v = js("!!document.getElementById('cgReq')")
        note(v, f'{theme}: request-access button for non-member', str(v))
        js("document.getElementById('cgReq').click()"); time.sleep(1.0)
        v = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Math Study Group'); return g.requests.map(r=>r.name).join(',');})()")
        note('QA' in str(v), f'{theme}: join request recorded', str(v))
        v = js("document.getElementById('view-groups').textContent.includes('Request sent')")
        note(v, f'{theme}: request-sent state shown', str(v))
        errs('join flows')

        # --- home section ---
        js("HUB.showTab('home');"); time.sleep(1.5)
        v = js("document.querySelectorAll('#homeCg .gcard').length")
        note(v == 5, f'{theme}: home carousel shows 5 live groups (4 seeds + Test Climbers)', f'found={v}')
        shot(f'cg-home-{theme}.png')
        errs('home section')

        # --- lazy locale loads with new kh (no silent fallback) ---
        v = js("HUB.i18n.loadLocale('fr').then(ok=>'loaded:'+ok+'|has:'+!!HUB.i18n._dict('fr')['cg.title'])")
        note(v == 'loaded:true|has:true', f'{theme}: lazy fr locale validates new kh', str(v))
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
