#!/usr/bin/env python3
"""QA: dark mode is the default on fresh install.
1. Fresh profile -> boot is dark, zero errors.
2. Toggle to light (real #darkToggle) -> persists across reload.
3. Toggle back to dark -> persists across reload.
Explicit saved prefs.dark always wins; default never overrides it."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9465
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)

proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
    '--user-data-dir=/tmp/hubqa-darkdefault', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
    c = CDP = None
    import types
    ws = websocket.create_connection(tgt['webSocketDebuggerUrl'], timeout=12); ws.settimeout(12); i = 0
    def send(method, params=None):
        global i; i += 1
        ws.send(json.dumps({'id': i, 'method': method, 'params': params or {}}))
        dl = time.time() + 15
        while time.time() < dl:
            try: msg = json.loads(ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:60])
            if msg.get('id') == i: return msg.get('result')
        raise TimeoutError(method)
    def js(expr):
        r = send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        return (r or {}).get('result', {}).get('value')
    def shot(name):
        r = send('Page.captureScreenshot', {'format': 'png'})
        open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
    def errs(label):
        v = js("window.__huberr.splice(0)")
        note(not v, label + ' zero errors', json.dumps(v)[:200] if v else '')

    js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
    time.sleep(4)
    errs('fresh boot')
    # seed profile to skip onboarding, WITHOUT touching prefs.dark
    js("HUB.store.state.profile.name='QA';HUB.store.state.profile.campus='Riverside State';HUB.store.save();"
       "var w=document.getElementById('wlcmHost');if(w)w.hidden=true;")
    time.sleep(0.8)

    # 1. fresh install -> dark
    v = js("document.body.classList.contains('dark')")
    note(v is True, 'fresh install boots dark (body.dark)', str(v))
    v = js("HUB.store.state.prefs.dark")
    note(v is True, 'fresh install seeds prefs.dark=true', str(v))
    js("HUB.showTab('home')"); time.sleep(1.2)
    shot('darkdefault-fresh-dark.png')

    # 2. toggle to light via the real UI toggle
    js("HUB.showTab('me')"); time.sleep(1.0)
    v = js("!!document.getElementById('darkToggle')")
    note(v, 'dark toggle present in Me tab', str(v))
    js("document.getElementById('darkToggle').click()"); time.sleep(0.8)
    v = js("document.body.classList.contains('dark')")
    note(v is False, 'toggle switches to light', str(v))
    v = js("HUB.store.state.prefs.dark")
    note(v is False, 'toggle saves prefs.dark=false', str(v))
    js("HUB.showTab('home')"); time.sleep(1.0)
    shot('darkdefault-toggled-light.png')

    # 3. reload -> light persists (explicit choice wins)
    send('Page.reload'); time.sleep(4)
    js("var w=document.getElementById('wlcmHost');if(w)w.hidden=true;")
    time.sleep(0.5)
    v = js("document.body.classList.contains('dark')")
    note(v is False, 'light persists across reload', str(v))
    v = js("HUB.store.state.prefs.dark")
    note(v is False, 'prefs.dark=false survives reload', str(v))

    # 4. toggle back to dark -> persists across reload
    js("HUB.showTab('me')"); time.sleep(1.0)
    js("document.getElementById('darkToggle').click()"); time.sleep(0.8)
    v = js("document.body.classList.contains('dark')")
    note(v is True, 'toggle switches back to dark', str(v))
    send('Page.reload'); time.sleep(4)
    js("var w=document.getElementById('wlcmHost');if(w)w.hidden=true;")
    time.sleep(0.5)
    v = js("document.body.classList.contains('dark')")
    note(v is True, 'dark persists across reload', str(v))
    errs('final')
finally:
    proc.terminate()

fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
