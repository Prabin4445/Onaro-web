#!/usr/bin/env python3
"""QA: GPA calculator polish — live grade-reactive background, animated GPA
number, band glow, instant picker feedback, delete/new-row animations.
Fresh profiles, zero console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9522
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

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-gpa2-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-gpa2-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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

        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(1)

        # card placement: between classes card and appointments card
        pos = js("(()=>{const h=document.getElementById('view-home').innerHTML;"
                 "return [h.indexOf('Your classes'),h.indexOf('gpaCard'),h.indexOf('Appointments')];})()")
        note(pos[0] >= 0 and pos[1] > pos[0] and pos[2] > pos[1],
             f'{theme}: GPA card between classes and appointments', str(pos))

        # open add sheet
        js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.6)
        note(js("!!document.querySelector('.gpa-form')"), f'{theme}: add sheet has .gpa-form wrapper')
        note('gg-A' in str(js("document.querySelector('.gpa-form').className")), f'{theme}: form starts gg-A')
        gt_a = js("getComputedStyle(document.querySelector('.gpa-form')).getPropertyValue('--gt').trim()")

        # tap F -> background shifts red
        js("document.querySelector('[data-ggrade=\"F\"]').click()"); time.sleep(0.7)
        cls = str(js("document.querySelector('.gpa-form').className"))
        gt_f = js("getComputedStyle(document.querySelector('.gpa-form')).getPropertyValue('--gt').trim()")
        note('gg-F' in cls, f'{theme}: tap F -> form gg-F', cls)
        note(gt_f != gt_a, f'{theme}: --gt tint changed A->F', f'{gt_a} -> {gt_f}')
        note('239,68,68' in gt_f or '239, 68, 68' in gt_f, f'{theme}: F tint is red', gt_f)
        shot(f'gpa2-sheet-gradeF-{theme}.png')

        # tap B -> teal
        js("document.querySelector('[data-ggrade=\"B\"]').click()"); time.sleep(0.7)
        gt_b = js("getComputedStyle(document.querySelector('.gpa-form')).getPropertyValue('--gt').trim()")
        note('gg-B' in str(js("document.querySelector('.gpa-form').className")), f'{theme}: tap B -> form gg-B')
        note('20,184,166' in gt_b or '20, 184, 166' in gt_b, f'{theme}: B tint is teal', gt_b)
        if theme == 'light':
            shot('gpa2-sheet-gradeB-light.png')

        # tap A -> volt, screenshot
        js("document.querySelector('[data-ggrade=\"A\"]').click()"); time.sleep(0.7)
        note('gg-A' in str(js("document.querySelector('.gpa-form').className")), f'{theme}: tap A -> form gg-A')
        if theme == 'dark':
            shot('gpa2-sheet-gradeA-dark.png')

        # add course: Math 201, 3cr, A -> GPA 4.00, hero gb5
        js("document.getElementById('gpaSubj').value='Math 201';document.getElementById('gpaCr').value='3';"
           "document.getElementById('gpaSave').click()")
        time.sleep(0.3)
        samples = []
        for _ in range(7):
            samples.append(js("document.querySelector('#gpaCard .gpa-num')?document.querySelector('#gpaCard .gpa-num').textContent:''"))
            time.sleep(0.12)
        final = js("document.querySelector('#gpaCard .gpa-num').textContent")
        note(final == '4.00', f'{theme}: GPA 4.00 after Math A', final)
        note(len(set(samples)) > 1, f'{theme}: GPA number counted up (animated)', str(samples[:4]))
        note('gb5' in str(js("document.querySelector('#gpaCard .gpa-hero').className")), f'{theme}: hero gb5 volt band')
        note('gb5' in str(js("document.querySelector('#gpaCard').className")), f'{theme}: card gb5 border')
        note(js("!!document.querySelector('#gpaCard .gpa-row.gpa-new')"), f'{theme}: new row entrance class')
        shot(f'gpa2-card-{theme}.png')
        errs('add-course')

        # add English 4cr B -> GPA (12+12)/7 = 3.43, band gb4 teal
        js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.5)
        js("document.querySelector('[data-ggrade=\"B\"]').click()")
        js("document.getElementById('gpaSubj').value='English';document.getElementById('gpaCr').value='4';"
           "document.getElementById('gpaSave').click()")
        time.sleep(1.0)
        final = js("document.querySelector('#gpaCard .gpa-num').textContent")
        note(final == '3.43', f'{theme}: GPA 3.43 after English B', final)
        note('gb4' in str(js("document.querySelector('#gpaCard .gpa-hero').className")), f'{theme}: hero gb4 teal band')

        # add History 3cr F -> GPA (12+12+0)/10 = 2.40, band gb3 amber
        js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.5)
        js("document.querySelector('[data-ggrade=\"F\"]').click()")
        js("document.getElementById('gpaSubj').value='History';document.getElementById('gpaCr').value='3';"
           "document.getElementById('gpaSave').click()")
        time.sleep(1.0)
        final = js("document.querySelector('#gpaCard .gpa-num').textContent")
        note(final == '2.40', f'{theme}: GPA 2.40 after History F', final)
        note('gb3' in str(js("document.querySelector('#gpaCard .gpa-hero').className")), f'{theme}: hero gb3 amber band')

        # delete History (F) -> slide-away then GPA back to 3.43
        n0 = js("document.querySelectorAll('#gpaCard .gpa-row').length")
        js("var rows=document.querySelectorAll('#gpaCard .gpa-row');rows[rows.length-1].querySelector('.gpa-del').click()")
        time.sleep(0.1)
        note(js("!!document.querySelector('#gpaCard .gpa-row.gpa-leave')"), f'{theme}: delete plays leave animation')
        time.sleep(0.8)
        n1 = js("document.querySelectorAll('#gpaCard .gpa-row').length")
        note(n1 == n0 - 1, f'{theme}: row removed after animation', f'{n0}->{n1}')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '3.43', f'{theme}: GPA back to 3.43')

        # clear-all confirm -> empty state, gb0
        js("document.querySelector('[data-gpa-clear]').click()"); time.sleep(0.5)
        js("document.getElementById('cfGo').click()"); time.sleep(1.0)
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '0.00', f'{theme}: cleared -> 0.00')
        note('gb0' in str(js("document.querySelector('#gpaCard .gpa-hero').className")), f'{theme}: hero gb0 neutral')
        note(js("!!document.querySelector('#gpaCard .gpa-empty')"), f'{theme}: empty state shown')
        clearToasts()
        errs('delete+clear')

        # persistence across reload (dark only, keeps runtime sane)
        if theme == 'dark':
            js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.5)
            js("document.getElementById('gpaSubj').value='Bio';document.getElementById('gpaCr').value='4';"
               "document.getElementById('gpaSave').click()"); time.sleep(1.0)
            c.send('Page.reload'); time.sleep(5); hook(c)
            js("try{HUB.store.state.profile.name='PraBin';var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
            js("document.body.classList.add('dark'); HUB.showTab('home');"); time.sleep(1)
            note(js("document.querySelectorAll('#gpaCard .gpa-row').length") == 1, 'dark: course persists after reload')
            note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '4.00', 'dark: GPA persists after reload')
            errs('reload')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run(th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== {ok}/{tot} passed ====')
bad = [l for o, l in checks if not o]
if bad: print('FAILURES:', bad)
