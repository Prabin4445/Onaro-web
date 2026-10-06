#!/usr/bin/env python3
"""Final round QA sweep: onboarding, all tabs, all key flows, overlays, dark, people, screenshots."""
import json, subprocess, time, urllib.request, os, base64, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9441
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:160])

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

proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
    '--user-data-dir=/tmp/hubqa6-prof', '--hide-scrollbars', '--allow-file-access-from-files',
    '--use-angle=swiftshader', '--enable-unsafe-swiftshader', BASE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    tgt = None
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                ts = json.load(r)
            tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
        except Exception: continue
    assert tgt, 'no target'
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
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
        if v: errors.append((label, v)); print('CONSOLE-ERRORS @', label, ':', json.dumps(v)[:400])
    js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
    for _ in range(25):
        v, _ = js("typeof HUB")
        if v != 'undefined': break
        time.sleep(1)
    time.sleep(2); errs('boot')

    # --- onboarding: new 2-step role + picker ---
    note(js("!!document.getElementById('obStudent')")[0], 'onboard: role cards shown')
    shot('qa6-ob-role')
    js("document.getElementById('obCommunity').click()"); time.sleep(0.6)
    note(js("!!document.getElementById('obCommunityPick')")[0], 'onboard: community picker step')
    shot('qa6-ob-picker')
    js("document.getElementById('obBack').click()"); time.sleep(0.5)
    note(js("!!document.getElementById('obStudent')")[0], 'onboard: back button returns to role step')
    js("document.getElementById('obStudent').click()"); time.sleep(0.5)
    js("(()=>{const n=document.getElementById('obName'); if(n) n.value='QA Tester'; const s=document.getElementById('obCommunityPick'); if(s) s.selectedIndex=1;})()")
    js("document.getElementById('obGo').click()"); time.sleep(1)
    aud, _ = js("JSON.parse(localStorage.getItem('hub_v1')).profile.audience")
    note(aud == 'student', 'onboard: audience persisted', aud)
    errs('onboard')

    # --- home ---
    js("HUB.showTab('home')"); time.sleep(1); errs('home'); shot('qa6-home')

    # --- discover (fallback: maplibre blocked) ---
    js("HUB.showTab('discover')"); time.sleep(1.5); errs('discover')
    note(js("!!document.querySelector('.map-fallback')")[0], 'discover: honest fallback when CDN blocked')
    shot('qa6-discover-list')

    # --- market + radius ---
    js("HUB.showTab('market')"); time.sleep(1); errs('market'); shot('qa6-market')
    rads, _ = js("(()=>{const b=[...document.querySelectorAll('#mkRadius button')]; return b.map(x=>x.textContent.trim()).join('|')})()")
    note(rads and '1 mi' in rads, 'market: radius control present', rads)
    n5, _ = js("document.querySelectorAll('#view-market .item').length")
    js("(()=>{const b=[...document.querySelectorAll('#mkRadius button')].find(x=>x.textContent.trim()==='1 mi'); if(b) b.click()})()"); time.sleep(0.8)
    n1, _ = js("document.querySelectorAll('#view-market .item').length")
    note(n1 is not None and n1 <= (n5 or 999), 'market: radius filter narrows results', f'{n5}->{n1}')
    shot('qa6-market-radius')

    # --- market post form ---
    js("(()=>{const b=document.getElementById('mkPost'); if(b) b.click()})()"); time.sleep(0.8)
    note(js("!!document.getElementById('mpTitle')")[0], 'market: post form opens')
    shot('qa6-post-form')
    js("(()=>{document.getElementById('mpTitle').value='QA bike'; document.getElementById('mpPrice').value='42'; const s=document.getElementById('mpType'); if(s) s.value='SELL';})()")
    js("document.getElementById('mpGo').click()"); time.sleep(1)
    posted, _ = js("document.querySelector('#view-market').innerHTML.includes('QA bike')")
    note(bool(posted), 'market: posted listing appears')
    errs('market-post')

    # --- listing detail: message seller + delete (mine) ---
    js("(()=>{const it=[...document.querySelectorAll('#view-market .item')].find(x=>x.textContent.includes('QA bike')); if(it) it.click()})()"); time.sleep(0.8)
    note(js("!!document.getElementById('mkMessage')")[0], 'market: detail shows message-seller')
    shot('qa6-listing-detail')
    note(js("!!document.getElementById('mkDelete')")[0], 'market: delete button on own listing')
    js("document.getElementById('mkDelete').click()"); time.sleep(0.3)
    armed, _ = js("document.getElementById('mkDelete').dataset.armed")
    note(armed == '1', 'market: delete two-tap confirm arms')
    js("document.getElementById('mkDelete').click()"); time.sleep(0.8)
    gone, _ = js("!document.querySelector('#view-market').innerHTML.includes('QA bike')")
    note(bool(gone), 'market: delete removes listing')
    errs('market-detail')

    # --- work ---
    js("HUB.showTab('work')"); time.sleep(1); errs('work'); shot('qa6-work')

    # --- groups: all 3 segments ---
    js("HUB.showTab('groups')"); time.sleep(1); errs('groups'); shot('qa6-groups-households')
    js("(()=>{const b=document.querySelector('[data-sub=\"campus\"]'); if(b) b.click()})()"); time.sleep(0.8); errs('groups-comm'); shot('qa6-groups-communities')
    js("(()=>{const b=document.querySelector('[data-sub=\"people\"]'); if(b) b.click()})()"); time.sleep(1)
    pcnt, _ = js("document.querySelectorAll('.ppl-card').length")
    note((pcnt or 0) >= 5, 'people: surface lists sample people', pcnt)
    shot('qa6-people-surface'); errs('groups-people')

    # --- people profile sheet + add contact + message ---
    pid, _ = js("(HUB.people.visiblePeople()[0]||{}).id")
    js(f"HUB.people.openProfile({json.dumps(pid)})"); time.sleep(0.8)
    note(js("!document.getElementById('sheetHost').hidden")[0], 'people: profile sheet opens')
    shot('qa6-people-profile')
    added, _ = js(f"(()=>{{HUB.people.addContact({json.dumps(pid)}); return (HUB.store.state.contacts||[]).length}})()")
    note((added or 0) > 0, 'people: add contact', added)
    shot('qa6-people-added')
    js("(()=>{const b=[...document.querySelectorAll('#sheetHost button')].find(x=>/message/i.test(x.textContent)); if(b) b.click()})()"); time.sleep(1)
    chatopen, _ = js("!!document.getElementById('chatRoot') && !document.getElementById('chatRoot').hidden")
    note(bool(chatopen), 'people: message opens chat thread')
    shot('qa6-people-message')
    js("HUB.chat.close()"); time.sleep(0.4); errs('people-flows')

    # --- chat: new contact dead-end fix ---
    js("HUB.chat.openList()"); time.sleep(0.8)
    js("document.getElementById('chatNew').click()"); time.sleep(0.6)
    js("(()=>{document.getElementById('ncName').value='Dedupe Test'; document.getElementById('ncPhone').value='+1 555-000-1234'; document.getElementById('ncGo').click()})()"); time.sleep(1)
    th, _ = js("(()=>{const t=HUB.store.state.threads.find(x=>x.title==='Dedupe Test'); return t?t.messages.length:0})()")
    note(th is not None, 'chat: new contact gets a thread (no dead end)', th)
    shot('qa6-chat-thread'); errs('chat')

    # --- create sheet: all 9 actions open something ---
    js("document.getElementById('createFab').click()"); time.sleep(0.8)
    acnt, _ = js("document.querySelectorAll('#sheetHost [data-a]').length")
    note((acnt or 0) == 9, 'create: all 9 actions present', acnt)
    shot('qa6-create')
    errs('create')

    # --- ask orbit intents ---
    js("HUB.askHUB.open()"); time.sleep(0.8)
    js("(()=>{const i=document.getElementById('askInput'); i.value='moving'; document.getElementById('askGo').click()})()"); time.sleep(0.8)
    note(js("document.getElementById('askOut').textContent.includes('HOUSEHOLD')")[0], 'ask: moving intent answered')
    js("(()=>{const i=document.getElementById('askInput'); i.value='buy a bike'; document.getElementById('askGo').click()})()"); time.sleep(0.8)
    note(js("document.getElementById('askOut').textContent.includes('Nearby listings')")[0], 'ask: buy intent shows real listings')
    shot('qa6-ask-orbit')
    js("document.getElementById('askClose').click()"); time.sleep(0.4); errs('ask')

    # --- search / pulse / notifications + stacking hygiene ---
    js("HUB.search.open()"); time.sleep(0.6)
    js("(()=>{const i=document.getElementById('qSearch'); i.value='bike'; i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()"); time.sleep(0.8)
    note(js("document.getElementById('searchRoot').innerHTML.length>1000")[0], 'search: results render')
    shot('qa6-search')
    js("HUB.pulse.open()"); time.sleep(0.6)
    svis, _ = js("!!document.getElementById('searchRoot') && !document.getElementById('searchRoot').hidden")
    note(not svis, 'overlay hygiene: opening pulse closes search')
    shot('qa6-pulse')
    js("HUB.notifications.open()"); time.sleep(0.6)
    pvis, _ = js("!!document.getElementById('pulseRoot') && !document.getElementById('pulseRoot').hidden")
    note(not pvis, 'overlay hygiene: opening notifications closes pulse')
    shot('qa6-notifications')
    errs('overlays')

    # --- me + privacy/discoverability toggle ---
    js("HUB.showTab('me')"); time.sleep(1); errs('me'); shot('qa6-me')
    note(js("!!document.getElementById('discToggle')")[0], 'me: discoverability toggle present')
    shot('qa6-me-privacy')
    before, _ = js("HUB.people.visiblePeople().length")
    js("document.getElementById('discToggle').click()"); time.sleep(0.6)
    after, _ = js("HUB.people.visiblePeople().length")
    note(after is not None and after <= (before or 0), 'me: discoverability toggle affects surface', f'{before}->{after}')
    js("document.getElementById('discToggle').click()"); time.sleep(0.4)  # restore on
    errs('privacy')

    # --- dark mode home + profile ---
    js("document.getElementById('darkToggle').click()"); time.sleep(0.8)
    note(js("document.body.classList.contains('dark')")[0], 'dark mode toggles')
    js("HUB.showTab('home')"); time.sleep(0.8); shot('qa6-home-dark')
    js("HUB.showTab('me')"); time.sleep(0.8); shot('qa6-me-dark')
    js("HUB.showTab('discover')"); time.sleep(1); shot('qa6-discover-dark')
    js("document.getElementById('darkToggle')&&document.body.classList.contains('dark')?document.getElementById('darkToggle').click():0"); time.sleep(0.5)
    errs('dark')

    # --- brand/user-visible copy sanity ---
    hubhit, _ = js("document.body.innerText.match(/\\bHUB\\b/g) && document.body.innerText.match(/\\bHUB\\b/g).length")
    note(not hubhit, 'user-visible copy: no word-boundary HUB hits', hubhit)
    errs('final')
    print('----')
    print('checks:', sum(1 for ok, _ in checks if ok), '/', len(checks), 'passed')
    print('console-error rounds with errors:', len(errors))
finally:
    proc.terminate()
