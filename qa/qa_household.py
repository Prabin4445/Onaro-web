#!/usr/bin/env python3
"""QA: Household groups upgrade — private households, auto-split bills,
swipe-to-delete/edit bills, admin manage (members), non-admin guards."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9481
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

def swipe_left(c, js):
    """Synthesize a leftward swipe on the first .hhb bill row."""
    return js("""(()=>{
      const row=document.querySelector('.hhb'); if(!row) return 'no-row';
      const r=row.getBoundingClientRect(), y=r.top+r.height/2;
      const pe=(type,x)=>row.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:y,pointerId:1,isPrimary:true}));
      pe('pointerdown',300); pe('pointermove',260); pe('pointermove',200); pe('pointermove',130); pe('pointerup',130);
      return document.querySelector('.hhb .hhb-inner').style.transform;
    })()""")

def run(theme, full):
    shutil.rmtree(f'/tmp/hubqa-hh-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-hh-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));window.confirm=function(){return true}")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='QA';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('groups');")
        time.sleep(1.2)
        js("document.querySelector('.seg [data-sub=\"households\"]').click()")
        time.sleep(1.0)
        errs('households list')

        v = js("document.querySelector('#view-groups').textContent")
        note('Apartment 204' in str(v) and 'New household' in str(v), f'{theme}: households list renders', str(v)[:60])
        v = js("document.querySelector('.hh-card.hh-glass')!==null")
        note(v, f'{theme}: list cards have glass treatment', str(v))
        v = js("document.querySelector('#view-groups').textContent.includes('Private household')")
        note(v, f'{theme}: private badge on cards', str(v))
        shot(f'hh-list-{theme}.png')

        # ---- create household ----
        js("document.getElementById('newHh').click()"); time.sleep(0.8)
        v = js("document.getElementById('sheetHost').hidden===false && !!document.getElementById('nhSave')")
        note(v, f'{theme}: new household sheet opens', str(v))
        v = js("document.getElementById('nhSave').parentElement.textContent.includes('Private household')")
        note(v, f'{theme}: create sheet notes private + auto-split', str(v))
        js("(()=>{document.getElementById('nhName').value='Test House';document.getElementById('nhMembers').value='QA, Alex, Maya';document.getElementById('nhSave').click();})()")
        time.sleep(1.2)
        errs('create household')
        v = js("document.querySelector('#view-groups').textContent")
        note('Test House' in str(v) and 'QA' in str(v) and 'Alex' in str(v) and 'Maya' in str(v), f'{theme}: detail shows name + members', str(v)[:80])
        v = js("!!document.getElementById('hhManage')")
        note(v, f'{theme}: admin sees Manage button', str(v))
        v = js("document.querySelector('#view-groups').textContent")
        note('👑' in str(v), f'{theme}: admin crown on member chip', str(v)[:40])
        shot(f'hh-detail-{theme}.png')

        if not full:
            errs('final'); return

        # ---- add bill $90: auto-split among all 3 ----
        js("document.getElementById('addBill').click()"); time.sleep(0.8)
        js("(()=>{document.getElementById('bItem').value='Dinner';const a=document.getElementById('bAmt');a.value='90';a.dispatchEvent(new Event('input',{bubbles:true}));})()")
        time.sleep(0.4)
        v = js("document.getElementById('bSplitNote').textContent")
        note('3 members' in str(v) and '$30' in str(v), f'{theme}: live split note 3 x $30', str(v))
        js("document.getElementById('bSave').click()"); time.sleep(1.0)
        errs('add bill')
        v = js("document.querySelectorAll('.hhb').length")
        note(v == 1, f'{theme}: bill row rendered', f'found={v}')
        v = js("document.querySelector('#view-groups').textContent")
        note('Alex owes you' in str(v) and 'Maya owes you' in str(v) and '$30' in str(v), f'{theme}: balances $30 each', str(v)[-160:])

        # ---- swipe-to-delete ----
        tx = swipe_left(c, js); time.sleep(0.5)
        note('translateX(-148px)' in str(tx), f'{theme}: swipe reveals actions', str(tx))
        shot(f'hh-swipe-{theme}.png')
        v = js("(()=>{const b=document.querySelector('.hhb [data-act=\"del\"]');if(!b)return 'no-btn';b.click();return 'clicked';})()")
        time.sleep(1.0)
        note(v == 'clicked', f'{theme}: delete action fires', str(v))
        v = js("document.querySelectorAll('.hhb').length")
        note(v == 0, f'{theme}: bill deleted via swipe', f'found={v}')
        errs('swipe delete')

        # ---- add + edit bill via fallback ... ----
        js("document.getElementById('addBill').click()"); time.sleep(0.8)
        js("(()=>{document.getElementById('bItem').value='Groceries';const a=document.getElementById('bAmt');a.value='60';a.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('bSave').click();})()")
        time.sleep(1.0)
        js("document.querySelector('.hhb-more').click()"); time.sleep(0.8)
        v = js("!!document.getElementById('baEdit') && !!document.getElementById('baDel')")
        note(v, f'{theme}: fallback ... opens Edit/Delete sheet', str(v))
        js("document.getElementById('baEdit').click()"); time.sleep(0.8)
        v = js("document.getElementById('bItem').value")
        note(v == 'Groceries', f'{theme}: edit sheet prefilled', str(v))
        js("(()=>{const a=document.getElementById('bAmt');a.value='120';a.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('bSave').click();})()")
        time.sleep(1.0)
        v = js("document.querySelector('#view-groups').textContent")
        note('$40' in str(v) and 'Groceries' in str(v), f'{theme}: edit recomputes shares to $40', str(v)[-120:])
        errs('bill edit')

        # ---- manage household: remove Maya ----
        js("document.getElementById('hhManage').click()"); time.sleep(0.8)
        v = js("!!document.getElementById('hhSave')")
        note(v, f'{theme}: manage sheet opens', str(v))
        shot(f'hh-manage-{theme}.png')
        js("document.querySelector('[data-rm=\"Maya\"]').click()"); time.sleep(0.6)
        js("(()=>{document.getElementById('hhAddName').value='Sam';document.getElementById('hhAddBtn').click();})()"); time.sleep(0.6)
        js("(()=>{document.getElementById('hhName').value='Test Villa';document.getElementById('hhSave').click();})()")
        time.sleep(1.2)
        errs('manage household')
        v = js("document.querySelector('#view-groups').textContent")
        note('Test Villa' in str(v) and 'Sam' in str(v), f'{theme}: rename + add member saved', str(v)[:80])
        # honest rule: Maya's existing $40 share survives on the old bill
        note('Maya owes you' in str(v) and '$40' in str(v), f'{theme}: removed member keeps old share (honest)', str(v)[-160:])
        # new bill splits among current members only
        js("document.getElementById('addBill').click()"); time.sleep(0.8)
        js("(()=>{document.getElementById('bItem').value='Internet';const a=document.getElementById('bAmt');a.value='30';a.dispatchEvent(new Event('input',{bubbles:true}));})()")
        time.sleep(0.4)
        v = js("document.getElementById('bSplitNote').textContent")
        note('3 members' in str(v) and '$10' in str(v), f'{theme}: new bill splits among QA+Alex+Sam', str(v))
        js("(()=>{const s=document.getElementById('bBy');s.value='Alex';document.getElementById('bSave').click();})()")
        time.sleep(1.0)
        v = js("document.querySelector('#view-groups').textContent")
        note('you owes Alex' in str(v) and '$10' in str(v), f'{theme}: new bill balances right', str(v)[-120:])

        # ---- non-admin view: Alex sees no admin controls ----
        js("HUB.store.state.profile.name='Alex';HUB.store.save();HUB.showTab('groups');"); time.sleep(1.2)
        v = js("!!document.getElementById('hhManage')")
        note(not v, f'{theme}: non-admin sees no Manage button', str(v))
        v = js("document.querySelectorAll('.hhb-actions button, .hhb-more').length")
        note(v == 0, f'{theme}: non-admin sees no bill actions', f'found={v}')
        errs('non-admin view')
        js("HUB.store.state.profile.name='QA';HUB.store.save()")
        errs('final')
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
