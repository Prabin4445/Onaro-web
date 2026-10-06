#!/usr/bin/env python3
"""QA: stale loopback-call announcements must never ring a phantom incoming
call (esp. before login); fresh ones still ring; no record -> silence.
Fix: 20s announcement heartbeat + 120s staleness expiry in
checkActiveCallAtLoad + showBanner idempotency. (2026-09-30)"""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import websocket  # noqa: F401 (parity with other harnesses)

PORT = 9448
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok:
        fails.append(n)

def j(c, expr, await_=False):
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip()
        if e.endswith(';'):
            e = e[:-1]
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q:
                instr = False
        elif ch in '"\'`':
            instr, q = True, ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ';' and depth == 0:
            top_semi = True
            break
    if not top_semi:
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'awaitPromise': await_, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

ERR_HOOK = ("window.__huberr=[];"
            "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
            "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

def boot(c):
    """Wait for app boot, then bypass the auth gate (sanctioned pattern)."""
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.call&&HUB.i18n&&HUB.incoming);") is True:
            break
        time.sleep(0.5)
    j(c, """var p=HUB.store.state.profile; p.name='QA Phantom'; p.campus='The University of Texas at Dallas';
      p.verified=true; HUB.store.save(); window.__gateSkip=true;
      try{HUB.auth.close()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1;""")
    for _ in range(20):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    for _ in range(40):
        if j(c, "return document.readyState;") == "complete":
            break
        time.sleep(0.5)
    time.sleep(2.0)  # let window 'load' handlers (checkActiveCallAtLoad) run

def seed_group(c):
    j(c, """HUB.store.state.cgroups=[{id:'g1',name:'Weekend Hikers',mine:true,members:['QA Phantom']}];
      HUB.store.save(); return 1;""")

def inc_state(c):
    return j(c, """var r=document.getElementById('incallRoot');
      if(!r) return {present:false};
      return {present:true, hidden:!!r.hidden,
        name:(document.getElementById('incName')||{textContent:''}).textContent};""")

def scenario(name, record_js):
    tag = name
    prof = '/tmp/hubqa-phantomcall-%s' % name
    subprocess.run(['rm', '-rf', prof])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + prof, '--hide-scrollbars', '--window-size=390,844', 'about:blank'])
    time.sleep(2.5)
    tgt = None
    for _ in range(30):
        try:
            tgts = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read())
            tgt = [t for t in tgts if t.get('type') == 'page'][0]
            break
        except Exception:
            time.sleep(0.4)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable')
    c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    # error hook injected before ANY page script, survives navigations
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source': ERR_HOOK})
    c.send('Page.navigate', {'url': BASE})
    boot(c)
    seed_group(c)
    if record_js:
        j(c, record_js)
        time.sleep(0.3)
        c.send('Page.navigate', {'url': BASE})
        boot(c)
    st = inc_state(c)
    rec = j(c, "return localStorage.getItem('onaro_call_active');")
    errs = j(c, "return window.__huberr.slice(0,8);")
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, 'phantomcall-%s.png' % tag), 'wb').write(base64.b64decode(r['data']))
    check(tag + ' zero console errors', not errs, errs)
    proc.terminate()
    proc.wait()
    return st, rec

# ---- 1. stale record (10 min old): must NOT ring, must be deleted ----
st, rec = scenario('stale',
    "(function(){localStorage.setItem('onaro_call_active',JSON.stringify("
    "{groupId:'g1',callId:'stale1',by:'Prabin',at:Date.now()-600000}));return 1;})()")
check('stale: no incoming UI', st.get('hidden', True) is True or not st['present'], st)
check('stale: announcement deleted', rec in (None, 'null'), rec)

# ---- 2. fresh record: must ring with caller name ----
st, rec = scenario('fresh',
    "(function(){localStorage.setItem('onaro_call_active',JSON.stringify("
    "{groupId:'g1',callId:'fresh1',by:'Prabin',at:Date.now()}));return 1;})()")
check('fresh: incoming UI shown', st['present'] and st.get('hidden') is False, st)
check('fresh: caller name shown', st.get('name') == 'Prabin', st)

# ---- 3. no record: silence ----
st, rec = scenario('none', None)
check('none: no incoming UI', st.get('hidden', True) is True or not st['present'], st)

print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
