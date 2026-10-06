#!/usr/bin/env python3
"""QA: HUB.perms permission manager.
Fresh profile -> explainer on first camera use -> grant remembered across reload
-> simulated deny -> rescue sheet with platform steps -> try-again works.
Photos: explainer only (no OS prompt), remembered. i18n es. Zero console errors.
"""
import json, subprocess, time, urllib.request, os, sys, base64, shutil, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []
net_urls = []

def check(n, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + n + ((' | ' + str(extra)) if extra else ''), flush=True)
    if not ok: fails.append(n)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl); self.id = 0; self.events = []
    def send(self, method, params=None, wait=True, timeout=90):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        if not wait: return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.id: return msg.get('result')
            self.events.append(msg)
        raise TimeoutError(method)
    def close(self):
        try: self.ws.close()
        except Exception: pass

def port_open(port):
    import socket
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('localhost', port)); return True
    except OSError: return False

HOOKS = ("window.__scanerr=[];"
         "window.__gateSkip=true;"
         "window.addEventListener('error',function(e){window.__scanerr.push('ERR:'+(e.message||e.error));});"
         "window.addEventListener('unhandledrejection',function(e){window.__scanerr.push('REJ:'+((e.reason&&e.reason.message)||e.reason));});")

def launch(name, w, h, dark, lang):
    port = 9480 + (abs(hash(name)) % 200)
    prof = '/tmp/hubqa-perms-' + re.sub(r'[^a-z0-9]+', '-', name)
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen(
        [CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
         f'--remote-debugging-port={port}', '--remote-allow-origins=*',
         '--hide-scrollbars', '--allow-file-access-from-files',
         f'--user-data-dir={prof}', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < 20:
        if port_open(port): break
        time.sleep(0.4)
    with urllib.request.urlopen(f'http://localhost:{port}/json/list') as r:
        tgt = [t for t in json.load(r) if t['type'] == 'page' and 'devtools' not in t['url']][0]
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source': HOOKS +
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'%s',country:'US'}));}catch(e){}" % lang})
    c.send('Runtime.enable'); c.send('Page.enable'); c.send('Network.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    if dark:
        c.send('Page.addScriptToEvaluateOnNewDocument',
               {'source': "try{localStorage.setItem('prefs',JSON.stringify({dark:true}));}catch(e){}"})
    c.send('Page.navigate', {'url': BASE})
    return proc, c, prof

def js(c, expr, await_promise=False, timeout=90):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True,
                                    'awaitPromise': await_promise}, wait=True, timeout=timeout)
    res = (r or {}).get('result', {})
    if res.get('subtype') == 'error':
        return {'__err': res.get('description')}
    if (r or {}).get('exceptionDetails'):
        return {'__err': json.dumps((r or {})['exceptionDetails'])[:300]}
    return res.get('value')

def wait_js(c, expr, timeout=25):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = js(c, expr)
        if v: return v
        time.sleep(0.5)
    return None

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    with open(os.path.join(QA, name), 'wb') as f:
        f.write(base64.b64decode(r['data']))

def drain_net(c):
    for e in c.events:
        if e.get('method') == 'Network.requestWillBeSent':
            net_urls.append(e['params']['request']['url'])
    c.events = [e for e in c.events if e.get('method') != 'Network.requestWillBeSent']

STUB_DENY = ("Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{"
             "getUserMedia:function(){var e=new Error('x');e.name='NotAllowedError';return Promise.reject(e);}}});1")
STUB_GRANT = ("Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{"
              "getUserMedia:function(){return Promise.resolve({getTracks:function(){return[{stop:function(){}}];}});}}});1")

def app_ready(c):
    return wait_js(c, "window.HUB&&HUB.perms&&HUB.i18n&&HUB.i18n.t('perm.allow')==='Allow'", 30)

procs = []
try:
    # ---------- round 1: explainer flow (390 dark, en) ----------
    proc, c, prof = launch('r1', 390, 844, True, 'en'); procs.append((proc, c))
    check('HUB.perms loads', bool(app_ready(c)))
    check('fresh camera status is prompt', js(c, "HUB.perms.status('camera')") == 'prompt')
    check('fresh photos status is prompt', js(c, "HUB.perms.status('photos')") == 'prompt')

    # first camera use -> explainer sheet (fire-and-forget, then sheet should appear)
    js(c, STUB_DENY)
    c.send('Runtime.evaluate', {'expression': "HUB.perms.ensure('camera').then(function(v){window.__ens=v;});1",
                                'returnByValue': True}, wait=False)
    ok = wait_js(c, "!!document.querySelector('.pm-sheet .pm-title')", 15)
    title = js(c, "document.querySelector('.pm-sheet .pm-title')?document.querySelector('.pm-sheet .pm-title').textContent:''")
    why = js(c, "document.querySelector('.pm-sheet .pm-why')?document.querySelector('.pm-sheet .pm-why').textContent:''")
    check('explainer appears on first camera use', bool(ok), title)
    check('explainer explains WHY (scanner/documents)', 'scan documents' in why.lower(), why[:60])
    check('explainer has Allow + Not now', bool(js(c, "!!(document.querySelector('[data-pm-yes]')&&document.querySelector('[data-pm-no]'))")))
    shot(c, 'perms-explainer-390-dark.png')

    # Not now -> no grant recorded, explainer shows again next time
    js(c, "document.querySelector('[data-pm-no]').click()")
    time.sleep(1)
    check('Not now resolves false', js(c, "window.__ens") is False)
    check('Not now does not record a grant', js(c, "HUB.perms.status('camera')") == 'prompt')
    c.send('Runtime.evaluate', {'expression': "HUB.perms.ensure('camera').then(function(v){window.__ens2=v;});1",
                                'returnByValue': True}, wait=False)
    check('explainer shows again after Not now', bool(wait_js(c, "!!document.querySelector('.pm-sheet')", 10)))

    # Allow -> real prompt (stubbed deny) -> rescue sheet
    js(c, "document.querySelector('[data-pm-yes]').click()")
    ok = wait_js(c, "!!document.querySelector('.pm-steps')", 15)
    steps = js(c, "document.querySelector('.pm-steps')?document.querySelector('.pm-steps').textContent:''")
    note = js(c, "document.querySelector('.pm-webnote')?document.querySelector('.pm-webnote').textContent:''")
    check('denied -> rescue sheet appears', bool(ok))
    check('rescue has exact desktop steps (site settings + Camera)', 'site settings' in steps and 'Camera' in steps, steps[:70])
    check('rescue is honest: browser settings, no app page', 'no separate' in note.lower() or 'browser' in note.lower(), note[:70])
    check('denied grant recorded', js(c, "HUB.perms.status('camera')") == 'denied')
    shot(c, 'perms-rescue-390-dark.png')

    # Try again (now stub grants) -> success, no more sheets
    js(c, STUB_GRANT)
    c.send('Runtime.evaluate', {'expression': "document.querySelector('[data-pm-retry]').click();1",
                                'returnByValue': True}, wait=False)
    check('try again resolves true after user fixes it', wait_js(c, "HUB.perms.status('camera')==='granted'", 15) is True)
    check('grant persisted in hub_perms_v1', 'granted' in str(js(c, "localStorage.getItem('hub_perms_v1')")))

    # reload -> grant remembered, no explainer re-ask
    c.send('Page.navigate', {'url': BASE})
    check('app reloads', bool(app_ready(c)))
    js(c, "HUB.perms.ensure('camera').then(function(v){window.__ens3=v;});1", await_promise=False)
    time.sleep(2)
    check('granted across reload (no re-ask)', js(c, "window.__ens3") is True)
    check('no explainer sheet after reload', not js(c, "!!document.querySelector('.pm-sheet')"))

    # photos: explainer only, Allow -> true immediately, remembered
    js(c, "HUB.perms._t.reset()")
    c.send('Runtime.evaluate', {'expression': "HUB.perms.ensure('photos').then(function(v){window.__ph=v;});1",
                                'returnByValue': True}, wait=False)
    ptitle = wait_js(c, "document.querySelector('.pm-sheet .pm-title')?document.querySelector('.pm-sheet .pm-title').textContent:''", 10)
    check('photos explainer appears first time', bool(ptitle), ptitle)
    js(c, "document.querySelector('[data-pm-yes]').click()")
    check('photos Allow resolves true (no OS prompt)', wait_js(c, "window.__ph===true", 10) is True)
    check('photos grant remembered', js(c, "HUB.perms.status('photos')") == 'granted')

    # location/notifications supported() sanity + no throw
    check('location supported() bool', js(c, "typeof HUB.perms.supported('location')") == 'boolean')
    check('notifications supported() bool', js(c, "typeof HUB.perms.supported('notifications')") == 'boolean')

    drain_net(c)
    errs = js(c, "window.__scanerr||[]")
    check('zero console errors (round 1)', not errs, str(errs)[:200])
    c.close(); proc.terminate()

    # ---------- round 2: iOS steps + es language (390 dark) ----------
    proc, c, prof = launch('r2', 390, 844, True, 'es'); procs.append((proc, c))
    check('app ready (es)', bool(wait_js(c, "window.HUB&&HUB.perms&&HUB.i18n.t('perm.allow')==='Permitir'", 30)))
    c.send('Emulation.setUserAgentOverride', {'userAgent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'})
    js(c, "HUB.perms._t.setState('camera','denied')")
    c.send('Runtime.evaluate', {'expression': "HUB.perms.ensure('camera');1", 'returnByValue': True}, wait=False)
    steps = wait_js(c, "document.querySelector('.pm-steps')?document.querySelector('.pm-steps').textContent:''", 15)
    check('iOS UA -> iPhone steps (Settings → Apps → Safari → Camera → Allow)',
          bool(steps) and 'Safari' in steps and 'Permitir' in steps, (steps or '')[:80])
    title = js(c, "document.querySelector('.pm-title')?document.querySelector('.pm-title').textContent:''")
    check('rescue title in Spanish', 'acceso' in title.lower(), title)
    drain_net(c)
    errs = js(c, "window.__scanerr||[]")
    check('zero console errors (round 2)', not errs, str(errs)[:200])
    c.close(); proc.terminate()

    # ---------- round 3: scanner wiring (320 light) ----------
    proc, c, prof = launch('r3', 320, 568, False, 'en'); procs.append((proc, c))
    check('app ready (r3)', bool(app_ready(c)))
    js(c, "HUB.perms._t.reset()")
    # open the scanner capture screen
    js(c, "window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; HUB.scan.tool('scan')")
    ok = wait_js(c, "!!document.querySelector('.scroot [data-m=\"take\"]')", 20)
    check('scanner capture screen opens', bool(ok))
    if ok:
        js(c, "document.querySelector('.scroot [data-m=\"take\"]').click()")
        check('camera button routes through perms explainer',
              bool(wait_js(c, "!!document.querySelector('.pm-sheet')", 10)))
        js(c, "try{document.querySelector('[data-pm-no]').click()}catch(e){}")
        time.sleep(0.6)
        js(c, "document.querySelector('.scroot [data-m=\"choose\"]').click()")
        check('photo button routes through perms explainer',
              bool(wait_js(c, "!!document.querySelector('.pm-sheet')", 10)))
        js(c, "try{document.querySelector('[data-pm-no]').click()}catch(e){}")
        time.sleep(0.6)
    shot(c, 'perms-scanner-320-light.png')
    drain_net(c)
    errs = js(c, "window.__scanerr||[]")
    check('zero console errors (round 3)', not errs, str(errs)[:200])
    c.close(); proc.terminate()

    ext = [u for u in net_urls if u.startswith('http')]
    check('zero http(s) network requests', not ext, str(ext[:3]))
finally:
    for proc, c in procs:
        try: c.close()
        except Exception: pass
        try: proc.terminate()
        except Exception: pass

print('\n==== %d FAILURES ====' % len(fails))
sys.exit(1 if fails else 0)
