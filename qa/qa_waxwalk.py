#!/usr/bin/env python3
"""Wax-walker logout: phase screenshots + timeline integrity (2026-09-30).

One browser run per phase — boot, seed, play(), single sleep, single shot.
Also asserts the full timeline (strip removed ~2s, real sign-out, zero
console errors) and that the walker is big, grounded, and jointed."""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9459
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-waxwalk'
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
        st.auth.users=st.auth.users.filter(function(x){return x.id!=='qawx';})
          .concat([{id:'qawx',name:'QA Wax',campus:'QA Campus',verified:true}]);
        st.auth.session={uid:'qawx',at:Date.now(),remember:true};
        HUB.store.save(); HUB.auth.restore();
        try{HUB.auth.close()}catch(e){}
      })(); return 1;""")
    time.sleep(0.8)
    if j(c, "return !!(HUB.auth&&HUB.auth.currentUser&&HUB.auth.currentUser());") is not True:
        raise RuntimeError('seeding login failed')

def one_phase(name, at_sec):
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

# timeline: 0-0.9 walk in, 0.9 door opens, 0.9-1.4 walk in, 1.4 door shuts, 2.0 done
one_phase('wx-walk.png', 0.45)
one_phase('wx-door.png', 0.85)
one_phase('wx-enter.png', 1.15)

# geometry + timeline integrity in one final run
subprocess.run(['rm', '-rf', PROF])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
    '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=390,844', 'about:blank'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(3)
    c = CDP(open_tab(PORT)['webSocketDebuggerUrl'])
    boot_and_seed(c)
    j(c, "window.__loGone=0; window.__loT=Date.now(); new MutationObserver(function(m){for(var i=0;i<m.length;i++)for(var k=0;k<m[i].removedNodes.length;k++){var n=m[i].removedNodes[k];if(n.id==='loStrip')window.__loGone=Date.now();}}.bind(this)).observe(document.documentElement,{childList:true,subtree:true}); HUB.logout.play(); return 1;")
    time.sleep(0.5)
    g = j(c, """return (function(){
      var m=document.querySelector('.lo-man'); if(!m) return null;
      var r=m.getBoundingClientRect(), tr=m.closest('.lo-track').getBoundingClientRect();
      var svg=m.querySelector('svg');
      return {manH:r.height, trackH:tr.height, manBottom:tr.bottom-r.bottom,
              limbs:svg.querySelectorAll('g[class^=wx-]').length};
    })();""")
    check('walker built', g is not None, g)
    if g:
        check('walker is big (>=50px tall)', g['manH'] >= 50, 'h=%.1f' % g['manH'])
        check('feet near track bottom (<=8px)', g['manBottom'] <= 8, 'bottom=%.1f' % g['manBottom'])
        check('all 10 limb joints present', g['limbs'] == 10, g['limbs'])
    gone = wait_true(c, "return (window.__loGone||0)>0;", 12)
    dt = j(c, "return (window.__loGone||0)-window.__loT;")
    check('strip removed by timeline', gone and 1800 <= dt <= 2400, 'removed after %sms' % dt)
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
