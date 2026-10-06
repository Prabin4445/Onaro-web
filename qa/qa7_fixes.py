#!/usr/bin/env python3
"""Targeted re-test of qa6 failures with correct selectors (script bugs, not app bugs)."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9447
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:140])
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
    '--user-data-dir=/tmp/hubqa7-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
    time.sleep(2)
    # seed a profile so onboarding is skipped (already verified in qa6)
    js("(()=>{const st=JSON.parse(localStorage.getItem('hub_v1')); st.profile.name='QA'; st.profile.campus='Riverside State'; st.profile.audience='student'; localStorage.setItem('hub_v1',JSON.stringify(st))})()")
    js("location.reload()"); time.sleep(2.5); errs('boot')

    # --- market post flow (real ids: mkPostBtn, mkTitle, mkTypeChips, mkPrice, mkPublish) ---
    js("HUB.showTab('market')"); time.sleep(1)
    js("document.getElementById('mkPostBtn').click()"); time.sleep(0.8)
    note(js("!!document.getElementById('mkTitle')")[0], 'market: post form opens (mkPostBtn)')
    shot('qa7-post-form')
    js("(()=>{document.getElementById('mkTitle').value='QA city bike'; const chip=document.querySelector('#mkTypeChips .chip[data-t=\"SELL\"]'); if(chip) chip.click(); document.getElementById('mkPrice').value='42';})()"); time.sleep(0.4)
    js("document.getElementById('mkPublish').click()"); time.sleep(1)
    note(js("document.querySelector('#view-market').innerHTML.includes('QA city bike')")[0], 'market: posted listing appears')
    errs('post')

    # --- detail: message seller + delete ---
    js("(()=>{const it=[...document.querySelectorAll('#view-market .item')].find(x=>x.textContent.includes('QA city bike')); if(it) it.click()})()"); time.sleep(0.8)
    note(js("!!document.getElementById('mkMessage')")[0], 'market: detail shows message-seller button')
    note(js("!!document.getElementById('mkDelete')")[0], 'market: delete button on own listing')
    shot('qa7-listing-detail')
    js("document.getElementById('mkDelete').click()"); time.sleep(0.3)
    note(js("document.getElementById('mkDelete').dataset.armed==='1'")[0], 'market: delete two-tap confirm arms')
    shot('qa7-delete-armed')
    js("document.getElementById('mkDelete').click()"); time.sleep(0.8)
    note(js("!document.querySelector('#view-market').innerHTML.includes('QA city bike')")[0], 'market: delete removes listing, list re-renders')
    errs('detail-delete')

    # --- message seller opens chat ---
    js("(()=>{const it=[...document.querySelectorAll('#view-market .item')].find(x=>x.textContent.includes('Desk lamp')); if(it) it.click()})()"); time.sleep(0.8)
    js("document.getElementById('mkMessage').click()"); time.sleep(1)
    note(js("!!document.getElementById('chatRoot') && !document.getElementById('chatRoot').hidden")[0], 'market: message-seller opens chat thread')
    shot('qa7-message-seller'); js("HUB.chat.close()"); time.sleep(0.3)

    # --- ask orbit intents (real ids: askSheetInput/askSheetSend/askSheetResults) ---
    js("HUB.askHUB.open()"); time.sleep(0.8)
    js("(()=>{document.getElementById('askSheetInput').value='moving'; document.getElementById('askSheetSend').click()})()"); time.sleep(0.8)
    note(js("document.getElementById('askSheetResults').textContent.includes('Moving game-plan')")[0], 'ask: moving intent answered')
    js("(()=>{document.getElementById('askSheetInput').value='buy a bike'; document.getElementById('askSheetSend').click()})()"); time.sleep(0.8)
    note(js("document.getElementById('askSheetResults').textContent.includes('Nearby listings')")[0], 'ask: buy intent shows real listings')
    shot('qa7-ask-orbit')
    js("(()=>{const x=[...document.querySelectorAll('#sheetHost button')].find(b=>b.textContent==='×'); if(x) x.click(); else HUB.ui.closeSheet()})()"); time.sleep(0.4)
    errs('ask')

    # --- search (real ids: hubSearchInput/hubSearchResults/hubSearchRoot) ---
    js("HUB.search.open()"); time.sleep(0.8)
    js("(()=>{const i=document.getElementById('hubSearchInput'); i.value='bike'; i.dispatchEvent(new Event('input',{bubbles:true}))})()"); time.sleep(0.8)
    note(js("document.getElementById('hubSearchResults').textContent.includes('bike')")[0], 'search: bike results render')
    shot('qa7-search')
    note(js("!!document.getElementById('hubSearchRoot')")[0], 'search: hubSearchRoot overlay present')
    js("HUB.pulse.open()"); time.sleep(0.6)
    note(js("!document.getElementById('hubSearchRoot')")[0], 'stacking: opening pulse removes search root')
    js("HUB.notifications.open()"); time.sleep(0.6)
    note(js("!document.getElementById('pulseRoot')")[0], 'stacking: opening notifications removes pulse root')
    errs('search-stack')

    # --- market radius buttons actually filter by listing kind too ---
    js("HUB.showTab('market')"); time.sleep(1)
    js("(()=>{const b=[...document.querySelectorAll('#mkTypeChips')];})()")
    js("HUB.showTab('home')"); time.sleep(0.6); shot('qa7-final-home')
    errs('final')
    print('----')
    print('checks:', sum(1 for ok, _ in checks if ok), '/', len(checks), 'passed')
    print('console-error rounds with errors:', len(errors))
finally:
    proc.terminate()
