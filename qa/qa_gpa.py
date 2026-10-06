#!/usr/bin/env python3
"""QA: GPA calculator — add courses, live GPA, delete, clear-all, persistence.
Fresh profiles, zero console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9521
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

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-gpa-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-gpa-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        def toasts():
            return str(js("document.getElementById('toastHost')?Array.from(document.querySelectorAll('#toastHost .toast')).map(e=>e.textContent).join(' | '):''"))
        def clearToasts():
            js("var h=document.getElementById('toastHost');if(h)h.innerHTML=''")

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(2)
        errs('home render')

        # ---- card present, between classes and appointments ----
        note(js("!!document.getElementById('gpaCard')"), f'{theme}: GPA card renders on Home')
        order = js("""(()=>{const v=document.getElementById('view-home').innerHTML;
          const a=v.indexOf('gpaCard'), b=v.indexOf('apptCard');
          return {gpa:a, appt:b, classesBefore:(v.indexOf('classCard')>-1&&v.indexOf('classCard')<a)||(v.indexOf('clsCard')>-1)};})()""")
        note(order and order['gpa'] > 0 and (order['appt'] == -1 or order['gpa'] < order['appt']),
             f'{theme}: GPA card sits before Appointments card')
        note('Add your courses' in str(js("document.getElementById('gpaCard').textContent")),
             f'{theme}: empty state shown')
        note(js("document.querySelector('link[data-gpa-css]')!==null"), f'{theme}: gpa.css injected')
        shot(f'gpa-empty-{theme}.png')

        # ---- add Math 201 (3cr, A default) ----
        clearToasts()
        js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.8)
        note('Subject' in str(js("document.querySelector('#sheetHost').textContent")), f'{theme}: add sheet opens')
        note(js("document.querySelector('[data-ggrade=\"A\"]').classList.contains('on')"), f'{theme}: grade A selected by default')
        js("(()=>{document.getElementById('gpaSubj').value='Math 201';document.getElementById('gpaCr').value='3';document.getElementById('gpaSave').click();})()")
        time.sleep(1.0)
        note('Math 201 added' in toasts(), f'{theme}: add toast', toasts()[:50])
        v = js("document.getElementById('gpaCard').textContent")
        note('Math 201' in str(v) and '4.00' in str(v), f'{theme}: 1 course -> GPA 4.00', str(v)[:60])

        # ---- validation: empty subject / zero credits ----
        js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.6)
        clearToasts()
        js("(()=>{document.getElementById('gpaSubj').value='';document.getElementById('gpaCr').value='3';document.getElementById('gpaSave').click();})()")
        time.sleep(0.5)
        note('Enter a subject name' in toasts(), f'{theme}: empty subject rejected')
        clearToasts()
        js("(()=>{document.getElementById('gpaSubj').value='Chem';document.getElementById('gpaCr').value='';document.getElementById('gpaSave').click();})()")
        time.sleep(0.5)
        note('Enter the credit hours' in toasts(), f'{theme}: empty credits rejected')
        js("HUB.ui.closeSheet()"); time.sleep(0.5)

        # ---- add English (4cr, B) -> GPA (12+12)/7 = 3.43 ----
        clearToasts()
        js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.6)
        js("(()=>{document.getElementById('gpaSubj').value='English';document.getElementById('gpaCr').value='4';document.querySelector('[data-ggrade=\"B\"]').click();document.getElementById('gpaSave').click();})()")
        time.sleep(1.0)
        v = js("document.getElementById('gpaCard').textContent")
        note('3.43' in str(v), f'{theme}: GPA 3.43 for A(3)+B(4)', str(v)[:80])
        note('7 credits' in str(v) and '2 courses' in str(v), f'{theme}: 7 credits + 2 courses chips')
        note(js("document.querySelectorAll('#gpaCard .gp-A').length") == 1 and js("document.querySelectorAll('#gpaCard .gp-B').length") == 1,
             f'{theme}: grade pills A + B color-coded')
        shot(f'gpa-{theme}.png')

        # ---- persistence across reload ----
        c.send('Page.reload'); time.sleep(4)
        js("try{var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js("HUB.showTab('home');"); time.sleep(2)
        v = js("document.getElementById('gpaCard').textContent")
        note('Math 201' in str(v) and 'English' in str(v) and '3.43' in str(v),
             f'{theme}: courses persist after reload')
        errs('post-reload')

        # ---- delete English -> GPA 4.00 ----
        clearToasts()
        n = js("HUB.gpa.courses().find(c=>c.subject==='English').id")
        js(f"document.querySelector('[data-gpa-del=\"{n}\"]').click()"); time.sleep(1.0)
        v = js("document.getElementById('gpaCard').textContent")
        note('English' not in str(v) and '4.00' in str(v), f'{theme}: delete -> GPA 4.00, English gone')
        note('1 courses' in str(v), f'{theme}: 1 course chip')

        # ---- clear all (confirm) -> empty ----
        clearToasts()
        js("document.querySelector('[data-gpa-clear]').click()"); time.sleep(0.6)
        note('Clear all courses' in str(js("document.querySelector('#sheetHost').textContent")), f'{theme}: clear confirm sheet')
        js("document.getElementById('cfNo').click()"); time.sleep(0.5)  # cancel first
        note(js("HUB.gpa.courses().length") == 1, f'{theme}: cancel keeps courses')
        js("document.querySelector('[data-gpa-clear]').click()"); time.sleep(0.6)
        js("document.getElementById('cfGo').click()"); time.sleep(1.0)
        v = js("document.getElementById('gpaCard').textContent")
        note(js("HUB.gpa.courses().length") == 0 and 'Add your courses' in str(v) and '0.00' in str(v),
             f'{theme}: clear all -> empty state, GPA 0.00')
        note('Calculator cleared' in toasts(), f'{theme}: cleared toast')

        errs('final')
    finally:
        proc.terminate()

run('dark')
run('light')
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
