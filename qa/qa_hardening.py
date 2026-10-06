#!/usr/bin/env python3
"""HUB hardening QA: safeboot recovery, state resilience, fetch retries,
leak checks, true 320/390px layouts, zero console errors.

Covers: corrupt hub_v1, partial valid state, data-file 404, unhandled
rejection capture, recovery overlay + backup-before-reset, no external PII
transmission, no overlay accumulation, true narrow viewports.
"""
import json, subprocess, time, urllib.request, os, sys, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
os.makedirs(QA, exist_ok=True)
CHROME = '/opt/meta-chromium/chrome'
PORT = 9341
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROFILE = '/tmp/hubqa-hardening'
ALLOWED_HOSTS = ('file://', 'data:', 'blob:', 'open-meteo.com')

import websocket

checks = []
def note(ok, label):
    checks.append((bool(ok), label))
    print(('PASS' if ok else 'FAIL'), '-', label)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl)
        self.id = 0
    def send(self, method, params=None, wait=True):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        if not wait: return None
        deadline = time.time() + 25
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.id:
                return msg.get('result')
        raise TimeoutError(method)

def new_target():
    for _ in range(40):
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list') as r:
                for t in json.load(r):
                    if t['type'] == 'page' and 'devtools' not in t['url']:
                        return t
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError('no page target')

shutil.rmtree(PROFILE, ignore_errors=True)
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
    '--allow-file-access-from-files', '--hide-scrollbars',
    f'--user-data-dir={PROFILE}', BASE])
time.sleep(3)
tgt = new_target()
c = CDP(tgt['webSocketDebuggerUrl'])
c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable'); c.send('Network.enable')
# Fresh-profile boot fix: set the returning-user i18n marker BEFORE any page
# script runs (welcome overlay would otherwise wait for user input and the
# 15s watchdog would fire — correct app behavior, wrong for QA).
c.send('Page.addScriptToEvaluateOnNewDocument',
       {'source': "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"})

net_urls, log_errors = [], []
def drain():
    """Pull pending CDP events (log entries, network requests)."""
    c.ws.settimeout(0.05)
    try:
        while True:
            try: msg = json.loads(c.ws.recv())
            except Exception: break
            m = msg.get('method')
            if m == 'Log.entryAdded':
                e = msg['params']['entry']
                if e.get('level') in ('error',):
                    log_errors.append(e.get('text', '')[:200])
            elif m == 'Runtime.exceptionThrown':
                d = msg['params'].get('exceptionDetails', {})
                log_errors.append('EXC:' + str(d.get('text', ''))[:200])
            elif m == 'Network.requestWillBeSent':
                net_urls.append(msg['params']['request']['url'])
    finally:
        c.ws.settimeout(None)

def js(expr, await_=False):
    # CDP Runtime.evaluate: bare `return` at top level is a SyntaxError —
    # always wrap in an IIFE (async when awaiting a promise).
    expr = ("(async function(){" if await_ else "(function(){") + expr + "})()"
    r = c.send('Runtime.evaluate', {'expression': expr, 'awaitPromise': await_,
                                   'returnByValue': True}, wait=True)
    res = (r or {}).get('result', {})
    return res.get('value'), res.get('exceptionDetails')

def reload_and_ready():
    c.send('Page.reload')
    for _ in range(60):
        v, _ = js("document.readyState")
        if v == 'complete': break
        time.sleep(0.5)
    arm_siphon()

def arm_siphon():
    js("window.__huberr=[];"
       "addEventListener('error',function(e){__huberr.push('ERR:'+e.message)});"
       "addEventListener('unhandledrejection',function(e){__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))});"
       "return 1;")

def wait_boot(tag, seed=True):
    # returning-user i18n marker: skips the 3-step welcome so boot completes
    for _ in range(60):
        v, _ = js("return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.ui&&HUB.i18n);")
        if v is True: break
        time.sleep(0.5)
    js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'})); return 1;")
    if seed:
        # seed past onboarding like the other harnesses
        js("var p=HUB.store.state.profile; p.name='QA Hard'; p.campus='The University of Texas at Dallas';"
           "p.verified=true; HUB.store.save(); window.__gateSkip=true;"
           "try{HUB.auth.close()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1;")
    for _ in range(30):
        v, _ = js("return !document.getElementById('splash');")
        if v is True: break
        time.sleep(0.5)
    for _ in range(30):
        v, _ = js("return (window.HUB&&HUB.safe&&HUB.safe.isBooted())===true;")
        if v is True: break
        time.sleep(0.5)
    note(v is True, f'app booted cleanly [{tag}]')
    drain()

def shot(name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))

def overflow_check(tag):
    v, _ = js("return {w:window.innerWidth, sw:document.documentElement.scrollWidth};")
    note(v and v['sw'] <= v['w'], f'no horizontal overflow [{tag}] (innerWidth={v["w"]}, scrollWidth={v["sw"]})')

def set_viewport(w, h):
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(0.5)

def assert_viewport(w, tag):
    # the metrics override reliably takes effect on the next page load;
    # assert after a reload, with a short poll for the renderer to apply it
    v = None
    for _ in range(10):
        v, _ = js("return window.innerWidth;")
        if v == w: break
        time.sleep(0.5)
    note(v == w, f'true {w}px viewport [{tag}] (innerWidth={v})')

try:
    # ---------- Phase 1: 390px boot ----------
    set_viewport(390, 844)
    reload_and_ready()
    assert_viewport(390, '390')
    wait_boot('390')
    shot('hard_home_390')
    overflow_check('390 home')
    drain()

    # ---------- Phase 2: 320px boot ----------
    set_viewport(320, 568)
    reload_and_ready()
    assert_viewport(320, '320')
    wait_boot('320')
    shot('hard_home_320')
    overflow_check('320 home')
    drain()

    # ---------- Phase 3: corrupt hub_v1 ----------
    js("localStorage.setItem('hub_v1','{\"broken\":'); return 1;")
    reload_and_ready()
    wait_boot('corrupt-state')
    v, _ = js("return Object.keys(localStorage).filter(function(k){return k.indexOf('hub_v1.corrupt.')===0;}).length;")
    note(v and v >= 1, f'corrupt state backed up before reseed (backups={v})')
    v, _ = js("return !!(HUB.store.state&&HUB.store.state.profile);")
    note(v is True, 'state reseeded with defaults after corruption')
    drain()

    # ---------- Phase 4: partial valid state ----------
    js("localStorage.setItem('hub_v1', JSON.stringify({_v:3, profile:{name:'KeepMe'}})); return 1;")
    reload_and_ready()
    # check preservation BEFORE the seeding step overwrites the name
    for _ in range(60):
        v, _ = js("return !!(window.HUB&&HUB.store&&HUB.store.state);")
        if v is True: break
        time.sleep(0.5)
    js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'})); return 1;")
    v, _ = js("return {kept:HUB.store.state.profile.name, threads:Array.isArray(HUB.store.state.threads),"
              " households:Array.isArray(HUB.store.state.households), listings:Array.isArray(HUB.store.state.listings)};")
    note(v and v.get('kept') == 'KeepMe', 'existing profile value preserved through backfill')
    note(v and v.get('threads') and v.get('households') and v.get('listings'),
         'missing top-level keys backfilled (threads/households/listings are arrays)')
    wait_boot('partial-state')
    drain()

    # ---------- Phase 5: unhandled rejection capture ----------
    before, _ = js("return HUB.safe.errCount();")
    js("setTimeout(function(){ Promise.reject(new Error('qa-probe-rej')); },0); return 1;")
    time.sleep(1.5); drain()
    after, _ = js("return HUB.safe.errCount();")
    v, _ = js("return JSON.stringify(HUB.safe.errors().slice(-3));")
    note(after == before + 1 and 'qa-probe-rej' in (v or ''),
         'unhandled rejection captured in local error ring (no console noise)')
    v, _ = js("return !document.getElementById('saferecov');")
    note(v is True, 'post-boot error stays silent (no recovery overlay while booted)')
    drain()

    # ---------- Phase 6: recovery overlay + backup-before-reset ----------
    js("localStorage.setItem('hub_v1', JSON.stringify({_v:3, profile:{name:'ResetMe'}})); HUB.store.save(); return 1;")
    js("HUB.safe.showRecovery('qa-probe'); return 1;")
    time.sleep(0.8)
    v, _ = js("return !!document.getElementById('saferecov');")
    note(v is True, 'recovery overlay renders on demand')
    shot('hard_recovery')
    v, _ = js("return !!document.getElementById('srReset');")
    note(v is True, 'recovery overlay offers Reload + Reset actions')
    js("document.getElementById('srReset').click(); return 1;")
    for _ in range(60):
        v, _ = js("document.readyState")
        if v == 'complete': break
        time.sleep(0.5)
    arm_siphon()
    wait_boot('after-reset')
    v, _ = js("return Object.keys(localStorage).filter(function(k){return k.indexOf('hub_v1.reset.')===0;}).length;")
    note(v and v >= 1, f'reset backed up prior data first (reset backups={v})')
    drain()

    # ---------- Phase 7: fetch resilience ----------
    t0 = time.time()
    v, exc = js("return HUB.safe.fetchJSON('data/__nope__.json',{retries:1,timeout:1200}).then(function(){return 'resolved';}).catch(function(e){return 'rejected:'+e.message;});", await_=True)
    dt = time.time() - t0
    note(v and v.startswith('rejected') and dt < 8, f'missing data file rejects after bounded retries ({dt:.1f}s, no hang)')
    v, exc = js("return HUB.safe.fetchJSON('data/quotes.json').then(function(j){return (j&&j.quotes||[]).length;});", await_=True)
    note(v and v > 100, f'existing data file loads via resilient fetch ({v} quotes)')
    drain()

    # ---------- Phase 8: degree overlay open/close x3 ----------
    js("HUB.store.state.profile.campus='The University of Texas at Dallas'; HUB.store.save(); return 1;")
    for i in range(3):
        js("HUB.degree.open(); return 1;")
        time.sleep(1.0)
        js("HUB.degree.close(); return 1;")
        time.sleep(0.4)
    v, _ = js("return document.querySelectorAll('.degroot').length;")
    note(v == 0, 'degree overlay fully removed after repeated open/close (no DOM accumulation)')
    drain()

    # ---------- Phase 9: network allowlist ----------
    drain()
    bad = [u for u in set(net_urls) if not u.startswith(ALLOWED_HOSTS)]
    note(not bad, f'no off-device requests outside allowlist ({len(set(net_urls))} unique URLs seen)'
         + ('' if not bad else ' BAD: ' + str(bad[:3])))

    # ---------- Phase 10: error-ring hygiene ----------
    v, _ = js("return JSON.stringify(HUB.safe.errors().map(function(e){return e.kind+':'+String(e.msg).slice(0,60);}));")
    unexpected = [e for e in json.loads(v or '[]')
                  if 'qa-probe-rej' not in e and 'recovery shown' not in e]
    note(not unexpected, f'error ring holds only the intentional probes ({len(json.loads(v or "[]"))} entries)')
    herr, _ = js("return window.__huberr.filter(function(m){return m.indexOf('qa-probe-rej')<0;});")
    note(not herr, f'no page-level uncaught errors besides the probe ({(herr or [])[:2]})')
    note(not [e for e in log_errors if 'qa-probe' not in e and 'net::' not in e],
         f'zero CDP console errors ({len(log_errors)} raw entries)')

finally:
    drain()
    try: proc.terminate()
    except Exception: pass

fails = [l for ok, l in checks if not ok]
print(f'\n==== HARDENING QA: {len(checks)-len(fails)}/{len(checks)} passed ====')
if fails:
    print('FAILURES:'); [print(' -', l) for l in fails]
    sys.exit(1)
