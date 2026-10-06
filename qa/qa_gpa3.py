#!/usr/bin/env python3
"""QA: GPA swipe-to-edit/delete — swipe-left reveals Edit/Delete, edit sheet
prefilled with live grade-reactive bg, confirm delete, live GPA recalc,
fallback ⋯ sheet. Fresh profiles, zero console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9523
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

def hook(c):
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Runtime.evaluate', {'expression':
        "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
        "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))"})

SWIPE_JS = """(()=>{
var row=document.querySelector('#gpaCard [data-gswipe]');
if(!row) return 'no-row';
var r=row.getBoundingClientRect();
function pe(type,x){row.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:r.top+20,pointerId:1,isPrimary:true,pointerType:'touch'}));}
pe('pointerdown',r.left+260);pe('pointermove',r.left+160);pe('pointermove',r.left+110);pe('pointerup',r.left+110);
return row.querySelector('.gpa-inner').style.transform||'(none)';
})()"""

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-gpa3-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-gpa3-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        hook(c)
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def clearToasts():
            js("var h=document.getElementById('toastHost');if(h)h.innerHTML=''")
        def add_course(subj, cr, grade):
            js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.5)
            js(f"document.querySelector('[data-ggrade=\"{grade}\"]').click()")
            js(f"document.getElementById('gpaSubj').value='{subj}';document.getElementById('gpaCr').value='{cr}';"
               "document.getElementById('gpaSave').click()"); time.sleep(1.0)

        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(1)

        # seed: Math 3cr A + English 4cr B -> GPA 3.43
        add_course('Math 201', '3', 'A')
        add_course('English', '4', 'B')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '3.43', f'{theme}: seeded GPA 3.43')
        note(js("document.querySelectorAll('#gpaCard [data-gswipe]').length") == 2, f'{theme}: 2 swipe rows rendered')
        note(js("document.querySelectorAll('#gpaCard .gpa-swactions').length") == 2, f'{theme}: 2 hidden action trays')
        note(js("!!document.querySelector('#gpaCard .gpa-more')"), f'{theme}: ⋯ fallback button present')
        errs('seed')

        # --- swipe left reveals Edit/Delete ---
        js("document.getElementById('gpaCard').scrollIntoView({block:'center'})"); time.sleep(0.5)
        tx = js(SWIPE_JS)
        note(tx == 'translateX(-148px)', f'{theme}: swipe snaps open at -148px', tx)
        note(js("!!document.querySelector('#gpaCard [data-gpa-edit]')"), f'{theme}: Edit button revealed')
        note(js("!!document.querySelector('#gpaCard [data-gpa-del]')"), f'{theme}: Delete button revealed')
        note(js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[0]).visibility") == 'visible',
             f'{theme}: swiped row tray visible')
        note(js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[1]).visibility") == 'hidden',
             f'{theme}: closed row tray hidden (no bleed-through)')
        shot(f'gpa3-swipe-{theme}.png')

        # --- Edit: prefilled sheet, grade-reactive bg on open ---
        js("document.querySelector('#gpaCard [data-gpa-edit]').click()"); time.sleep(0.7)
        note(js("!!document.querySelector('.gpa-form')"), f'{theme}: edit sheet opened')
        note(js("document.getElementById('gpaSubj').value") == 'Math 201', f'{theme}: subject prefilled')
        note(js("document.getElementById('gpaCr').value") == '3', f'{theme}: credits prefilled')
        note(js("document.querySelector('.gpa-segbtn.on').dataset.ggrade") == 'A', f'{theme}: grade A preselected')
        note('gg-A' in str(js("document.querySelector('.gpa-form').className")), f'{theme}: form opens gg-A (prefilled grade)')
        note('Edit course' in str(js("document.querySelector('.gpa-form h2').textContent")), f'{theme}: edit title shown')
        shot(f'gpa3-edit-{theme}.png')

        # change A -> C, save -> GPA (6+12)/7 = 2.57, band gb3
        js("document.querySelector('[data-ggrade=\"C\"]').click()"); time.sleep(0.4)
        note('gg-C' in str(js("document.querySelector('.gpa-form').className")), f'{theme}: bg shifts to gg-C live')
        js("document.getElementById('gpaSave').click()"); time.sleep(1.2)
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '2.57', f'{theme}: GPA recalculated to 2.57')
        note('gb3' in str(js("document.querySelector('#gpaCard .gpa-hero').className")), f'{theme}: hero band gb3 amber')
        note(js("document.querySelector('#gpaCard .gpa-inner .gp-pill').textContent") == 'C', f'{theme}: grade pill updated to C')
        errs('edit')

        # --- swipe Delete with confirm ---
        js("window.__confirmOK=true; window.confirm=function(){return window.__confirmOK;}")
        n0 = js("document.querySelectorAll('#gpaCard [data-gswipe]').length")
        tx = js(SWIPE_JS)
        note(tx == 'translateX(-148px)', f'{theme}: swipe open again', tx)
        js("document.querySelector('#gpaCard [data-gpa-del]').click()"); time.sleep(0.15)
        note(js("!!document.querySelector('#gpaCard .gpa-inner.gpa-leave')"), f'{theme}: delete slide-away animation')
        time.sleep(0.9)
        n1 = js("document.querySelectorAll('#gpaCard [data-gswipe]').length")
        note(n1 == n0 - 1, f'{theme}: row removed', f'{n0}->{n1}')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '3.00', f'{theme}: GPA reverts to 3.00 (English B only)')
        note('gb4' in str(js("document.querySelector('#gpaCard .gpa-hero').className")), f'{theme}: band back to gb4 teal')
        errs('delete')

        # --- ⋯ fallback sheet: Edit + Delete ---
        js("document.querySelector('#gpaCard .gpa-more').click()"); time.sleep(0.6)
        note(js("!!document.getElementById('gmEdit') && !!document.getElementById('gmDel')"), f'{theme}: ⋯ opens Edit/Delete sheet')
        js("document.getElementById('gmEdit').click()"); time.sleep(0.6)
        note(js("document.getElementById('gpaSubj').value") == 'English', f'{theme}: ⋯ Edit opens prefilled sheet')
        note('gg-B' in str(js("document.querySelector('.gpa-form').className")), f'{theme}: prefilled bg gg-B')
        js("HUB.ui.closeSheet()"); time.sleep(0.4)
        js("document.querySelector('#gpaCard .gpa-more').click()"); time.sleep(0.6)
        js("document.getElementById('gmDel').click()"); time.sleep(1.0)
        note(js("document.querySelectorAll('#gpaCard [data-gswipe]').length") == 0, f'{theme}: ⋯ Delete removes row')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '0.00', f'{theme}: GPA 0.00, empty state')
        note(js("!!document.querySelector('#gpaCard .gpa-empty')"), f'{theme}: empty state shown')
        clearToasts()
        errs('fallback')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run(th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== {ok}/{tot} passed ====')
bad = [l for o, l in checks if not o]
if bad: print('FAILURES:', bad)
