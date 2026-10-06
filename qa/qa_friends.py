#!/usr/bin/env python3
"""QA: Friends (contact sync / badges / invites) + household join requests."""
import json, subprocess, time, urllib.request, os, sys, base64, shutil
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9451
THEME = sys.argv[2] if len(sys.argv) > 2 else 'dark'
PROF = f'/tmp/hubqa-fr-{THEME}'
shutil.rmtree(PROF, ignore_errors=True)

errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((ok, label, detail))
    print(('PASS' if ok else 'FAIL'), label, detail)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
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
        f'--user-data-dir={PROF}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Runtime.enable'); c.send('Page.enable')

        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                res = (r or {}).get('result', {})
                if res.get('type') == 'undefined': return None, None
                return res.get('value'), (res.get('exceptionDetails') or {}).get('text')
            except Exception as e: return None, str(e)[:160]

        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, f'{name}-{THEME}.png'), 'wb').write(base64.b64decode(r['data']))
            print('shot:', name)

        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])

        def toast_clear(): js("document.getElementById('toastHost').innerHTML=''")
        def toast_text(): v, _ = js("document.getElementById('toastHost').innerText"); return v or ''

        def cleanup_overlays():
            js("HUB.ui.closeSheet(); for(const k of ['chat','pulse','search','notifications']) if(HUB[k]&&HUB[k].close)HUB[k].close()")

        # ---------- boot ----------
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        js("(()=>{const p=HUB.store.state.profile; p.name='QA Admin'; p.campus='Riverside'; p.audience='community'; HUB.store.save();})()")
        js("(()=>{const w=document.getElementById('wlcmHost'); if(w) w.hidden=true;})()")
        js("HUB.ui.closeSheet(); HUB.showTab('home')")
        if THEME == 'light':
            js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme()")
        time.sleep(1.2); errs('boot')
        v, _ = js("document.body.classList.contains('dark')")
        note((v is True) == (THEME == 'dark'), 'theme applied', THEME)
        v, _ = js("[...document.styleSheets].some(s=>{try{return (s.href||'').includes('friends.css')}catch(e){return false}})")
        note(bool(v), 'friends.css stylesheet applied')

        # ---------- FRIENDS ----------
        js("HUB.showTab('groups')"); time.sleep(0.8)
        js("document.querySelector('#view-groups [data-sub=\"people\"]').click()"); time.sleep(0.8)
        js("document.getElementById('pplFriendsBtn').click()"); time.sleep(0.8); errs('friends-open')
        v, _ = js("document.getElementById('pplList').innerText")
        note('No synced contacts yet' in str(v), 'friends empty state', str(v)[:60])
        shot('fr-empty')

        # mock Contact Picker: one known person + one stranger
        js("Object.defineProperty(navigator,'contacts',{value:{select:(a,b)=>Promise.resolve([{name:['Maya Chen'],tel:['+15550100']},{name:['Zed Nonuser'],tel:['+15550200']}])},configurable:true})")
        toast_clear()
        js("document.getElementById('pplSyncBtn').click()"); time.sleep(1.0); errs('sync')
        note('contacts synced' in toast_text(), 'picker sync toast', toast_text()[:50])
        v, _ = js("document.querySelectorAll('#pplList .fr-row').length")
        note(v == 2, 'two synced rows', str(v))
        v, _ = js("(()=>{const r=[...document.querySelectorAll('#pplList .fr-row')]; return r.map(x=>({t:x.innerText.slice(0,40), badge:!!x.querySelector('.fr-onaro'), inv:!!x.querySelector('[data-fract=\"invite\"]')}))})()")
        maya = next((x for x in v if 'Maya Chen' in x['t']), None)
        zed = next((x for x in v if 'Zed Nonuser' in x['t']), None)
        note(bool(maya and maya['badge'] and not maya['inv']), 'Maya Chen gets Onaro badge (matched person record)', json.dumps(maya))
        note(bool(zed and zed['inv'] and not zed['badge']), 'Zed Nonuser gets Invite action', json.dumps(zed))
        shot('fr-list')

        # permission-denied path -> manual sheet
        js("Object.defineProperty(navigator,'contacts',{value:{select:()=>Promise.reject(Object.assign(new Error('denied'),{name:'NotAllowedError'}))},configurable:true})")
        toast_clear()
        js("document.getElementById('pplSyncBtn').click()"); time.sleep(1.0); errs('denied')
        note('denied' in toast_text(), 'denied toast', toast_text()[:60])
        v, _ = js("!!document.getElementById('frName')")
        note(bool(v), 'denied opens manual sheet')
        # manual add persists
        js("document.getElementById('frName').value='Manual Friend'; document.getElementById('frPhone').value='+15550300'; document.getElementById('frSave').click()")
        time.sleep(0.8); errs('manual')
        v, _ = js("HUB.store.state.friends.length")
        note(v == 3, 'manual add persisted', str(v))
        v, _ = js("!![...document.querySelectorAll('#pplList .fr-row')].find(r=>r.innerText.includes('Manual Friend'))")
        note(bool(v), 'manual friend row visible')

        # invite: clipboard-copy fallback path
        js("window.__copied=null; Object.defineProperty(navigator,'clipboard',{value:{writeText:s=>{window.__copied=s;return Promise.resolve();}},configurable:true})")
        js("Object.defineProperty(navigator,'share',{value:undefined,configurable:true})")
        toast_clear()
        js("[...document.querySelectorAll('#pplList [data-fract=\"invite\"]')][0].click()"); time.sleep(1.0); errs('invite')
        v, _ = js("window.__copied")
        note(isinstance(v, str) and '#invite' in v, 'invite copies link fallback', str(v)[:70])
        # native share path
        js("window.__shared=null; Object.defineProperty(navigator,'share',{value:d=>{window.__shared=d;return Promise.resolve();},configurable:true})")
        js("[...document.querySelectorAll('#pplList [data-fract=\"invite\"]')][0].click()"); time.sleep(1.0)
        v, _ = js("window.__shared&&window.__shared.text")
        note(isinstance(v, str) and '#invite' in v, 'invite native share path', str(v)[:70])

        # remove with confirm
        js("window.confirm=()=>true")
        js("[...document.querySelectorAll('#pplList [data-fract=\"remove\"]')].find(b=>b.closest('.fr-row').innerText.includes('Manual Friend')).click()")
        time.sleep(0.8); errs('remove')
        v, _ = js("HUB.store.state.friends.length")
        note(v == 2, 'remove friend works', str(v))

        # ---------- HOUSEHOLD JOIN REQUESTS ----------
        cleanup_overlays(); js("HUB.showTab('groups')"); time.sleep(0.8)
        js("document.querySelector('#view-groups [data-sub=\"households\"]').click()"); time.sleep(0.6)
        js("document.getElementById('newHh').click()"); time.sleep(0.6)
        js("document.getElementById('nhName').value='QA House'; document.getElementById('nhSave').click()"); time.sleep(1.0); errs('hh-create')
        v, _ = js("(()=>{const h=HUB.store.state.households.find(x=>x.name==='QA House'); return h&&{id:h.id,admin:h.admin,members:h.members,reqs:(h.requests||[]).length}})()")
        note(bool(v) and v['admin'] == 'QA Admin', 'household created, QA Admin is admin', json.dumps(v))
        hh_id = v['id']
        v, _ = js("!!document.getElementById('hhInviteLink')")
        note(bool(v), 'admin sees invite-link button')
        js("document.getElementById('hhInviteLink').click()"); time.sleep(0.8); errs('invite-sheet')
        v, _ = js("document.getElementById('hhinvLink').value")
        note(isinstance(v, str) and '#hjoin=' in v and hh_id in v, 'invite link carries #hjoin hash + id', str(v)[:80])
        shot('fr-invite'); js("HUB.ui.closeSheet()"); time.sleep(0.4)

        # simulate the requester: different identity, deep link in
        js("HUB.store.state.profile.name='Requester Ron'; HUB.store.save()")
        js(f"location.hash='#hjoin={hh_id}&name='+encodeURIComponent('QA House')")
        js("HUB.cgroups.handleJoinHash()"); time.sleep(1.0); errs('hjoin')
        v, _ = js("(()=>({gate:!!document.getElementById('hhReqJoin'), bills:!!document.getElementById('addBill'), chips:[...document.querySelectorAll('.cgchip')].length}))()")
        note(bool(v) and v['gate'] and not v['bills'], 'non-member sees gate, no bills', json.dumps(v))
        v, _ = js("document.getElementById('view-groups').innerText.slice(0,200)")
        shot('fr-gate')
        js("document.getElementById('hhReqJoin').click()"); time.sleep(0.8); errs('req')
        note('Join request sent' in toast_text(), 'request sent toast', toast_text()[:40])
        v, _ = js("HUB.store.state.households.find(x=>x.id==='%s').requests.length" % hh_id)
        note(v == 1, 'request recorded', str(v))
        # duplicate request prevented
        js("HUB.store.state.profile.name='Requester Ron'; HUB.store.save(); HUB.cgroups.handleJoinHash()")
        v, _ = js("(()=>{const el=document.getElementById('hhReqJoin'); return el?el.disabled:'missing'})()")
        note(v is True, 'repeat visit shows pending (disabled)')
        # non-admin approve guard
        toast_clear()
        js("(()=>{const h=HUB.store.state.households.find(x=>x.id==='%s'); HUB.households.decideRequest(h,'Requester Ron',true)})()" % hh_id)
        time.sleep(0.5)
        note('not an admin' in toast_text().lower() or 'admin' in toast_text().lower(), 'non-admin approve blocked', toast_text()[:50])
        v, _ = js("(()=>{const h=HUB.store.state.households.find(x=>x.id==='%s'); return {reqs:h.requests.length, mem:h.members.length}})()" % hh_id)
        note(v['reqs'] == 1 and v['mem'] == 1, 'request/member unchanged after blocked approve', json.dumps(v))

        # admin view: requests card + notification
        js("HUB.store.state.profile.name='QA Admin'; HUB.store.save()")
        js(f"HUB.households.openHousehold('{hh_id}')"); time.sleep(1.0); errs('admin-view')
        v, _ = js("document.getElementById('view-groups').innerText")
        note('Join requests' in str(v) and 'Requester Ron' in str(v), 'admin sees request card', str(v)[str(v).find('Join requests')-20:str(v).find('Join requests')+60] if 'Join requests' in str(v) else 'missing')
        shot('fr-requests')
        # Manage area
        js("document.getElementById('hhManage').click()"); time.sleep(0.8); errs('manage')
        v, _ = js("document.getElementById('hhReqList').innerText")
        note('Requester Ron' in str(v), 'Manage sheet lists request', str(v)[:60])
        js("HUB.ui.closeSheet()"); time.sleep(0.4)
        # notification
        js("HUB.notifications.open()"); time.sleep(1.0); errs('notif')
        v, _ = js("document.getElementById('hubNotifRows').innerText")
        note('Requester Ron wants to join QA House' in str(v), 'notif row present', 'found' if 'Requester Ron' in str(v) else str(v)[:120])
        shot('fr-notif')
        js("(()=>{const el=[...document.querySelectorAll('#hubNotifRows .item')].find(e=>e.innerText.includes('Requester Ron')); if(el) el.click()})()")
        time.sleep(1.0)
        v, _ = js("document.getElementById('view-groups').innerText.includes('QA House')")
        note(bool(v), 'notif tap opens household')
        # approve from detail page
        js("(()=>{const b=document.querySelector('#view-groups [data-happr]'); if(b) b.click()})()")
        time.sleep(0.8); errs('approve')
        v, _ = js("(()=>{const h=HUB.store.state.households.find(x=>x.id==='%s'); return {mem:h.members, reqs:h.requests.length}})()" % hh_id)
        note('Requester Ron' in v['mem'] and v['reqs'] == 0, 'approve adds member, clears request', json.dumps(v))
        # second request -> approve from Manage sheet
        js("HUB.store.state.profile.name='Second Sam'; HUB.store.save()")
        js(f"location.hash='#hjoin={hh_id}'; HUB.cgroups.handleJoinHash()"); time.sleep(0.8)
        js("document.getElementById('hhReqJoin').click()"); time.sleep(0.6)
        js("HUB.store.state.profile.name='QA Admin'; HUB.store.save(); HUB.households.openHousehold('%s')" % hh_id); time.sleep(0.8)
        js("document.getElementById('hhManage').click()"); time.sleep(0.8)
        js("(()=>{const b=document.querySelector('#hhReqList [data-mhappr]'); if(b) b.click()})()"); time.sleep(0.8); errs('manage-approve')
        v, _ = js("HUB.store.state.households.find(x=>x.id==='%s').members" % hh_id)
        note('Second Sam' in v and len(v) == 3, 'Manage approve adds member', json.dumps(v))
        js("HUB.ui.closeSheet()"); time.sleep(0.3)

        # unknown household id -> honest landing
        js("location.hash='#hjoin=nope999&name='+encodeURIComponent('Ghost House'); HUB.cgroups.handleJoinHash()"); time.sleep(0.8); errs('unknown')
        v, _ = js("document.getElementById('sheetBox').innerText")
        note("You're invited!" in str(v) and 'backend' in str(v), 'unknown-id honest landing', str(v)[:90])
        js("HUB.ui.closeSheet()"); time.sleep(0.3)

        # community-group #join flow still works
        v, _ = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.live); return g&&g.id})()")
        note(bool(v), 'seed live group exists', str(v))
        if v:
            js(f"location.hash='#join={v}'; HUB.cgroups.handleJoinHash()"); time.sleep(1.0); errs('cgjoin')
            v2, _ = js("!!document.getElementById('cgBack')")
            note(bool(v2), 'community #join still opens group page')

        # ---------- regression sweep ----------
        cleanup_overlays()
        for tname in ['home', 'groups', 'me']:
            js(f"HUB.showTab('{tname}')"); time.sleep(1.0); errs(tname)
        shot('fr-final')

        print('\n==== SUMMARY', THEME, '====')
        passed = sum(1 for ok, _, _ in checks if ok)
        print(f'{passed}/{len(checks)} checks passed, {len(errors)} console-error groups')
        for ok, label, detail in checks:
            if not ok: print('  FAILED:', label, detail)
        for label, e in errors: print('  ERRORS @', label)
    finally:
        proc.terminate()

main()
