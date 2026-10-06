#!/usr/bin/env python3
"""Live smoke test: verify both features on https://hub-preview.surge.sh"""
import subprocess, time, json, os, sys
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9461
BASE = 'https://hub-preview.surge.sh/index.html'
PROF = '/tmp/hubqa-live'
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok:
        fails.append(n)

def j(c, expr):
    e = '(function(){ ' + expr.strip() + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

subprocess.run(['rm', '-rf', PROF])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*',
    '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=390,844', 'about:blank'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(3)
    req = urllib.request.Request('http://127.0.0.1:%d/json/new?about:blank' % PORT, method='PUT')
    tgt = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                tgt = json.load(r); break
        except Exception:
            time.sleep(0.5)
    if not tgt:
        print("FAIL could not open chrome"); sys.exit(1)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
        "window.__huberr=[];"
        "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"})
    c.send('Page.navigate', {'url': BASE})
    # wait for app
    ok = False
    for _ in range(60):
        time.sleep(1)
        try:
            if j(c, "return !!(window.HUB&&HUB.call&&HUB.logout);"):
                ok = True; break
        except Exception:
            pass
    check('live site loads HUB.call+HUB.logout', ok)
    if not ok:
        print("fails=%d" % len(fails)); sys.exit(1)
    # 1. call timeout hook exists live
    check('live HUB.call._noAnswerMs hook', j(c, "return typeof HUB.call._noAnswerMs;") == 'function')
    # 2. i18n keys live
    check('live noAnswer i18n (en)', j(c, "return HUB.i18n.t('call.noAnswerT');") == 'No answer')
    # 3. logout play exists live
    check('live HUB.logout.play', j(c, "return typeof HUB.logout.play;") == 'function')
    # 4. logout CSS has MJ keyframes live (fetch css text)
    css_has = j(c, """return fetch('css/logout.css').then(r=>r.text()).then(t=>t.indexOf('lo-mwglide')>-1&&t.indexOf('lo-dooropen')>-1).catch(()=>false);""")
    # need awaitPromise for the fetch
    r = c.send('Runtime.evaluate', {'expression': '(function(){ return fetch("css/logout.css").then(r=>r.text()).then(t=>t.indexOf("lo-mwglide")>-1&&t.indexOf("lo-dooropen")>-1).catch(()=>false); })()', 'awaitPromise': True, 'returnByValue': True}, wait=True)
    css_ok = ((r or {}).get('result', {}) or {}).get('value')
    check('live logout.css has MJ keyframes', css_ok is True)
    errs = j(c, "return (window.__huberr||[]).slice(0,5);")
    check('zero console errors (live)', not errs, errs)
    c.ws.close()
finally:
    try: proc.terminate()
    except Exception: pass
print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
