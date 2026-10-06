#!/usr/bin/env python3
"""QA: Micro-jobs full lifecycle — post -> accept (ON HOLD) -> chat ->
release/reopen -> mark done -> delete. Owner vs accepter vs third-party
controls, both themes, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil, re
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9464
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []  # noqa: F841
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
    shutil.rmtree(f'/tmp/hubqa-jobs-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-jobs-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        def toasts():
            return str(js("document.getElementById('toastHost')?Array.from(document.querySelectorAll('#toastHost .toast')).map(e=>e.textContent).join(' | '):''"))
        def clearToasts():
            js("var h=document.getElementById('toastHost');if(h)h.innerHTML=''")
        def as_user(name):
            js(f"HUB.store.state.profile.name={json.dumps(name)};HUB.store.save();HUB.showTab('work');")
            time.sleep(0.8)
        def card_sel(jid):
            return f"document.querySelector('[data-job=\"{jid}\"]')"
        def has(sel_expr):
            return bool(js(f"!!({sel_expr})"))

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('work');")
        time.sleep(1.5)
        errs('work render')

        # ---- A. post a job as PraBin ----
        n0 = js("HUB.store.state.jobs.length")
        js("document.getElementById('postJobBtn').click()"); time.sleep(0.8)
        js("(()=>{document.getElementById('pjTitle').value='Ride share';document.getElementById('pjPay').value='54';document.getElementById('pjDesc').value='Airport run Friday morning.';document.getElementById('pjGo').click();})()")
        time.sleep(1.0)
        jid = js("HUB.store.state.jobs[0].id")
        note(js("HUB.store.state.jobs.length") == n0 + 1 and jid, f'{theme}: job posted', str(jid)[:12])
        v = js(f"{card_sel(jid)}.textContent")
        note('open' in str(v).lower() and '$54' in str(v), f'{theme}: new card OPEN + price', str(v)[:50])
        # owner view: delete control, NO accept button
        note(has(f"{card_sel(jid)}.querySelector('[data-jdel]')") and not has(f"{card_sel(jid)}.querySelector('[data-accept]')"),
             f'{theme}: owner sees Delete, no Accept button')
        shot(f'jobs-board-{theme}.png')

        # ---- B. Alex accepts -> ON HOLD + Chat ----
        as_user('Alex Rivera')
        note(has(f"{card_sel(jid)}.querySelector('[data-accept]')") and not has(f"{card_sel(jid)}.querySelector('[data-jdel]')")
             and not has(f"{card_sel(jid)}.querySelector('[data-done]')") and not has(f"{card_sel(jid)}.querySelector('[data-reopen]')"),
             f'{theme}: non-owner sees only Accept')
        clearToasts()
        js(f"{card_sel(jid)}.querySelector('[data-accept]').click()"); time.sleep(0.8)
        note('Accept this job' in str(js("document.querySelector('#sheetHost').textContent")), f'{theme}: accept confirm sheet')
        js("document.getElementById('cfGo').click()"); time.sleep(0.8)
        v = js(f"{card_sel(jid)}.textContent")
        note('on hold' in str(v).lower() and 'accepted by' in str(v).lower(), f'{theme}: accepted -> ON HOLD badge', str(v)[:80])
        note(has(f"{card_sel(jid)}.querySelector('.b-onhold')"), f'{theme}: amber b-onhold badge class')
        note(has(f"{card_sel(jid)}.querySelector('[data-jchat]')") and not has(f"{card_sel(jid)}.querySelector('[data-accept]')"),
             f'{theme}: accepter sees Chat, no Accept')
        shot(f'jobs-onhold-{theme}.png')

        # ---- C. third user cannot accept / sees no controls ----
        as_user('Sam Chen')
        v = js(f"{card_sel(jid)}.textContent")
        note('on hold' in str(v).lower() and not has(f"{card_sel(jid)}.querySelector('[data-accept]')")
             and not has(f"{card_sel(jid)}.querySelector('[data-jchat]')") and not has(f"{card_sel(jid)}.querySelector('[data-jdel]')"),
             f'{theme}: third user read-only on ON HOLD job')

        # ---- D. accepter opens job chat ----
        as_user('Alex Rivera')
        js(f"{card_sel(jid)}.querySelector('[data-jchat]').click()"); time.sleep(1.2)
        note(js("!document.getElementById('chatRoot').hidden"), f'{theme}: chat overlay opens')
        v = js("document.querySelector('#chatPanel .chathead h3').textContent")
        note('Ride share' in str(v) and 'PraBin' in str(v), f'{theme}: chat header job + other party', str(v)[:50])
        v = js("document.querySelector('#chatPanel .csys')?document.querySelector('#chatPanel .csys').textContent:''")
        note("You're chatting about" in str(v) and 'Ride share' in str(v), f'{theme}: job chat seed line', str(v)[:60])
        js("(()=>{var i=document.getElementById('chatText');i.value='Hi! I can do Friday morning.';document.getElementById('chatSend').click();})()")
        time.sleep(1.2)
        v = js("document.querySelector('#chatPanel').textContent")
        note('Hi! I can do Friday morning.' in str(v), f'{theme}: message sends in job thread')
        shot(f'jobs-chat-{theme}.png')
        js("HUB.chat.close()"); time.sleep(0.6)
        errs('chat')

        # ---- E. accepter releases -> OPEN again ----
        clearToasts()
        js(f"{card_sel(jid)}.querySelector('[data-release]').click()"); time.sleep(0.8)
        note('Release this job' in str(js("document.querySelector('#sheetHost').textContent")), f'{theme}: release confirm sheet')
        js("document.getElementById('cfGo').click()"); time.sleep(0.8)
        v = js(f"{card_sel(jid)}.textContent")
        note('open' in str(v).lower() and 'on hold' not in str(v).lower() and js(f"HUB.store.find('jobs',{json.dumps(jid)}).acceptedBy") is None,
             f'{theme}: release reopens job', str(toasts())[:60])

        # ---- F. accept again; owner reopens ----
        js(f"{card_sel(jid)}.querySelector('[data-accept]').click()"); time.sleep(0.6)
        js("document.getElementById('cfGo').click()"); time.sleep(0.8)
        as_user('PraBin')
        ctrls = ['data-jchat', 'data-done', 'data-reopen', 'data-jdel']
        note(all(has(f"{card_sel(jid)}.querySelector('[{k}]')") for k in ctrls), f'{theme}: owner sees Chat+Done+Reopen+Delete')
        clearToasts()
        js(f"{card_sel(jid)}.querySelector('[data-reopen]').click()"); time.sleep(0.8)
        note('Reopen this job' in str(js("document.querySelector('#sheetHost').textContent")), f'{theme}: reopen confirm sheet')
        js("document.getElementById('cfGo').click()"); time.sleep(0.8)
        v = js(f"{card_sel(jid)}.textContent")
        note('open' in str(v).lower() and 'reopened' in str(toasts()).lower(), f'{theme}: owner reopen works', str(toasts())[:50])

        # ---- G. accept, owner marks done, owner deletes ----
        as_user('Alex Rivera')
        js(f"{card_sel(jid)}.querySelector('[data-accept]').click()"); time.sleep(0.6)
        js("document.getElementById('cfGo').click()"); time.sleep(0.8)
        as_user('PraBin')
        clearToasts()
        js(f"{card_sel(jid)}.querySelector('[data-done]').click()"); time.sleep(0.8)
        note(js(f"HUB.store.find('jobs',{json.dumps(jid)}).status") == 'done', f'{theme}: mark done -> done', str(toasts())[:40])
        js("Array.from(document.querySelectorAll('#view-work .chip')).find(p=>p.dataset.f==='done').click()"); time.sleep(0.8)
        note(js("document.querySelectorAll('#jobList .job').length") == 1, f'{theme}: Done filter shows it')
        shot(f'jobs-done-{theme}.png')
        js("Array.from(document.querySelectorAll('#view-work .chip')).find(p=>p.dataset.f==='all').click()"); time.sleep(0.8)
        clearToasts()
        js(f"{card_sel(jid)}.querySelector('[data-jdel]').click()"); time.sleep(0.8)
        note('Delete this job' in str(js("document.querySelector('#sheetHost').textContent")), f'{theme}: delete confirm sheet')
        js("document.getElementById('cfGo').click()"); time.sleep(0.8)
        note(js(f"!HUB.store.find('jobs',{json.dumps(jid)})") and js("HUB.store.state.jobs.length") == n0,
             f'{theme}: delete removes job', str(toasts())[:40])

        # ---- H. non-owner never sees owner controls on open job ----
        js("document.getElementById('postJobBtn').click()"); time.sleep(0.6)
        js("(()=>{document.getElementById('pjTitle').value='QA temp job';document.getElementById('pjPay').value='10';document.getElementById('pjGo').click();})()")
        time.sleep(0.8)
        jid2 = js("HUB.store.state.jobs[0].id")
        as_user('Alex Rivera')
        note(has(f"{card_sel(jid2)}.querySelector('[data-accept]')")
             and not any(has(f"{card_sel(jid2)}.querySelector('[{k}]')") for k in ['data-jdel', 'data-done', 'data-reopen', 'data-release', 'data-jchat']),
             f'{theme}: open job: non-owner has zero owner controls')
        as_user('PraBin')
        js(f"HUB.store.remove('jobs',{json.dumps(jid2)});HUB.store.save();")

        errs('final')
    finally:
        proc.terminate()

run('dark')
run('light')
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
