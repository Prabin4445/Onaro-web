#!/usr/bin/env python3
"""QA: Micro-jobs redesign — glass cards, art tile, volt price pill.
Flows: post, filters, accept (incl. own-job block), mark done."""
import json, subprocess, time, urllib.request, os, base64, shutil, re
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9463
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
    shutil.rmtree(f'/tmp/hubqa-work-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-work-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        js("try{HUB.store.state.profile.name='QA';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('work');")
        time.sleep(1.5)
        errs('work render')

        v = js("document.querySelector('#view-work').textContent")
        txt = str(v)
        note('Micro-jobs' in txt and '★★★★★' in txt and re.search(r'\d+ done', txt), f'{theme}: header keeps stars + done count', txt[:60])
        v = js("document.querySelectorAll('#jobList .job').length")
        note(v == 3, f'{theme}: 3 glass job cards', f'found={v}')
        v = js("Array.from(document.querySelectorAll('#jobList .job-art')).map(e=>e.textContent)")
        note(v == ['📦', '🎨', '🛠️'], f'{theme}: category art tiles', str(v))
        v = js("Array.from(document.querySelectorAll('#jobList .job-pay')).map(e=>e.textContent)")
        note(v == ['$40', '$25', '$30'], f'{theme}: volt price pills', str(v))
        v = js("document.querySelector('#jobList').textContent")
        note('Sample' in str(v) and 'Open' in str(v), f'{theme}: status + Sample badges kept', str(v)[:60])
        shot(f'work-board-{theme}.png')

        # filters
        js("Array.from(document.querySelectorAll('#view-work .chip')).find(p=>p.dataset.f==='open').click()")
        time.sleep(0.8)
        v = js("document.querySelectorAll('#jobList .job').length")
        note(v == 3, f'{theme}: Open filter shows 3', f'found={v}')
        js("Array.from(document.querySelectorAll('#view-work .chip')).find(p=>p.dataset.f==='done').click()")
        time.sleep(0.8)
        v = js("document.querySelector('#jobList .empty')!==null")
        note(v, f'{theme}: Done filter empty state', str(v))
        js("Array.from(document.querySelectorAll('#view-work .chip')).find(p=>p.dataset.f==='all').click()")
        time.sleep(0.8)

        if not full:
            errs('final'); return

        # ---- post flow ----
        js("document.getElementById('postJobBtn').click()"); time.sleep(0.8)
        v = js("document.getElementById('sheetHost').hidden===false && !!document.getElementById('pjGo')")
        note(v, f'{theme}: + Post a job opens composer', str(v))
        shot(f'work-post-{theme}.png')
        js("(()=>{document.getElementById('pjTitle').value='QA walk my dog';document.getElementById('pjPay').value='20';document.getElementById('pjDesc').value='Friendly beagle, 30 min walk.';document.getElementById('pjGo').click();})()")
        time.sleep(1.0)
        errs('publish')
        v = js("document.querySelectorAll('#jobList .job').length")
        note(v == 4, f'{theme}: new job posted', f'found={v}')
        v = js("document.querySelector('#jobList .job .job-art').textContent")
        note(v == '🐾', f'{theme}: new job gets pet art tile', str(v))

        # own-job accept blocked
        js("document.getElementById('toastHost').innerHTML=''")  # clear stale publish toast
        js("document.querySelector('#jobList .job [data-accept]').click()"); time.sleep(0.6)
        v = js("Array.from(document.querySelectorAll('#toastHost .toast')).map(e=>e.textContent).join(' | ')")
        note('own job' in str(v).lower() or 'your own' in str(v).lower(), f'{theme}: cannot accept own job', str(v)[:60])

        # accept Taylor's job
        js("Array.from(document.querySelectorAll('#jobList .job')).find(j=>j.textContent.includes('Taylor Brooks')).querySelector('[data-accept]').click()")
        time.sleep(0.8)
        v = js("Array.from(document.querySelectorAll('#jobList .job')).find(j=>j.textContent.includes('Taylor Brooks')).textContent")
        note('ACCEPTED' in str(v).upper() and 'Mark done' in str(v), f'{theme}: accept flow works', str(v)[:70])

        # mark done -> jobsDone increments
        d0 = js("HUB.store.state.profile.jobsDone||0")
        js("Array.from(document.querySelectorAll('#jobList .job')).find(j=>j.textContent.includes('Taylor Brooks')).querySelector('[data-done]').click()")
        time.sleep(0.8)
        d1 = js("HUB.store.state.profile.jobsDone||0")
        note(d1 == d0 + 1, f'{theme}: mark done increments jobsDone', f'{d0}->{d1}')
        v = js("Array.from(document.querySelectorAll('#view-work .chip')).find(p=>p.dataset.f==='done').click()")
        time.sleep(0.8)
        v = js("document.querySelectorAll('#jobList .job').length")
        note(v == 1, f'{theme}: Done filter shows completed job', f'found={v}')
        shot(f'work-done-{theme}.png')
        errs('final')
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
