#!/usr/bin/env python3
"""MJ logout tribute: phase-accurate screenshots (2026-09-30).

Headless software rendering saturates the main thread during the CSS
animation, so CDP evaluates between play() and the shots skew the timing.
Fix: one browser run per phase — boot, seed, play(), then a single sleep and
a single screenshot with no evaluates in between. Deterministic animation,
so each run captures its phase accurately. Also asserts the full timeline
(strip removed ~5.2s, real sign-out, zero console errors)."""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9457
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-mjlogout'
OUT = os.path.dirname(os.path.abspath(__file__))
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok:
        fails.append(n)

def j(c, expr):
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip().rstrip(';')
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q: instr = False
        elif ch in '"\'':
            instr, q = True, ch
        elif ch in '([{': depth += 1
        elif ch in ')]}': depth -= 1
        elif ch == ';' and depth == 0:
            top_semi = True; break
    if not top_semi:
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

ERR_HOOK = ("try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
            "window.__huberr=[];"
            "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
            "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

def wait_true(c, expr, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if j(c, expr) is True:
            return True
        time.sleep(0.5)
    return False

def open_tab(port):
    req = urllib.request.Request('http://127.0.0.1:%d/json/new?about:blank' % port, method='PUT')
    last = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(0.5)
    raise RuntimeError('chrome DevTools port never came up: %r' % (last,))

def boot_and_seed(c):
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source': ERR_HOOK})
    c.send('Page.navigate', {'url': BASE})
    if not wait_true(c, "return !!(window.HUB&&HUB.store&&HUB.logout&&HUB.logout.play);", 30):
        raise RuntimeError('no HUB.logout.play')
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    j(c, """window.__gateSkip=true;
      (function(){ var st=HUB.store.state;
        if(!st.auth||typeof st.auth!=='object') st.auth={session:null,users:[]};
        if(!Array.isArray(st.auth.users)) st.auth.users=[];
        st.auth.users=st.auth.users.filter(function(x){return x.id!=='qamj';})
          .concat([{id:'qamj',name:'QA MJ',campus:'QA Campus',verified:true}]);
        st.auth.session={uid:'qamj',at:Date.now(),remember:true};
        HUB.store.save(); HUB.auth.restore();
        try{HUB.auth.close()}catch(e){}
      })(); return 1;""")
    time.sleep(0.8)
    if j(c, "return !!(HUB.auth&&HUB.auth.currentUser&&HUB.auth.currentUser());") is not True:
        raise RuntimeError('seeding login failed')

def one_phase(name, at_sec):
    """Fresh browser, boot, seed, play, sleep(at_sec), one screenshot. No evaluates after play."""
    subprocess.run(['rm', '-rf', PROF])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=390,844', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(3)
        c = CDP(open_tab(PORT)['webSocketDebuggerUrl'])
        boot_and_seed(c)
        j(c, "HUB.logout.play(); return 1;")
        t0 = time.time()
        while time.time() - t0 < at_sec:
            time.sleep(0.05)
        r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True)
        p = os.path.join(OUT, name)
        with open(p, 'wb') as f:
            f.write(base64.b64decode(r['data']))
        print('shot %s at %.2fs' % (name, time.time() - t0))
        errs = j(c, "return (window.__huberr||[]).slice(0,8);")
        check('zero console errors [%s]' % name, not errs, errs)
        c.ws.close()
    finally:
        try: proc.terminate()
        except Exception: pass

# timeline: 0-2.2 moonwalk, 2.2-3.1 spin, ~3.0 door opens, 3.5-4.35 walk-in, 5.2 done
one_phase('mj3-moonwalk.png', 1.1)
one_phase('mj3-spin.png', 2.65)
one_phase('mj3-dooropen.png', 3.35)
one_phase('mj3-walkin.png', 3.95)
one_phase('mj3-done.png', 5.9)

# timeline integrity in one final run: strip gone ~5.2s, login back, signed out
subprocess.run(['rm', '-rf', PROF])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
    '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=390,844', 'about:blank'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(3)
    c = CDP(open_tab(PORT)['webSocketDebuggerUrl'])
    boot_and_seed(c)
    j(c, "window.__loGone=0; new MutationObserver(function(m){for(var i=0;i<m.length;i++)for(var k=0;k<m[i].removedNodes.length;k++){var n=m[i].removedNodes[k];if(n.id==='loStrip')window.__loGone=Date.now();}}.bind(this)).observe(document.documentElement,{childList:true,subtree:true}); window.__loT=Date.now(); HUB.logout.play(); return 1;")
    gone = wait_true(c, "return (window.__loGone||0)>0;", 12)
    dt = j(c, "return (window.__loGone||0)-window.__loT;")
    check('strip removed by timeline', gone and 4800 <= dt <= 6500, 'removed after %sms' % dt)
    check('real sign-out ran (login back)', wait_true(c, "return !document.getElementById('authRoot').hidden;", 8))
    check('session cleared', j(c, "return !HUB.auth.currentUser();") is True)
    errs = j(c, "return (window.__huberr||[]).slice(0,8);")
    check('zero console errors [timeline]', not errs, errs)
    c.ws.close()
finally:
    try: proc.terminate()
    except Exception: pass

print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
