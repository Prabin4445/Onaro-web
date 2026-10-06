#!/usr/bin/env python3
"""MJ logout tribute: phase-accurate FROZEN screenshots (2026-09-30).

Freezes the strip's WAAPI animations at exact timeline points (verified:
anim.currentTime=T renders wall-time T correctly, delays accounted for).
One browser run per phase: boot, seed, ONE evaluate that plays+freezes,
then screenshot at leisure. Zero console errors asserted per run."""
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
    e = '(function(){ ' + expr.strip() + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

ERR_HOOK = ("try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
            "window.__huberr=[];"
            "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
            "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

def wait_true(c, expr, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if j(c, "return (%s);" % expr) is True:
            return True
        time.sleep(0.5)
    return False

def open_tab():
    req = urllib.request.Request('http://127.0.0.1:%d/json/new?about:blank' % PORT, method='PUT')
    last = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(0.5)
    raise RuntimeError('no chrome: %r' % (last,))

FREEZE_JS = """
  HUB.logout.play();
  var strip = document.getElementById('loStrip');
  if (!strip) return 'NO-STRIP';
  void strip.offsetWidth;
  var anims = strip.getAnimations({subtree:true});
  for (var i = 0; i < anims.length; i++) {
    try { anims[i].pause(); anims[i].currentTime = __T__; } catch (e) {}
  }
  void strip.offsetWidth;
  return 'frozen n=' + anims.length;
"""

def one_phase(name, t_ms):
    subprocess.run(['rm', '-rf', PROF])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=390,844', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(3)
        c = CDP(open_tab()['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.addScriptToEvaluateOnNewDocument', {'source': ERR_HOOK})
        c.send('Page.navigate', {'url': BASE})
        if not wait_true(c, "!!(window.HUB&&HUB.store&&HUB.logout&&HUB.logout.play)", 30):
            raise RuntimeError('boot failed')
        for _ in range(40):
            if j(c, "return !document.getElementById('splash');") is True:
                break
            time.sleep(0.5)
        j(c, """window.__gateSkip=true;
          var st=HUB.store.state;
          if(!st.auth||typeof st.auth!=='object') st.auth={session:null,users:[]};
          if(!Array.isArray(st.auth.users)) st.auth.users=[];
          st.auth.users=st.auth.users.filter(function(x){return x.id!=='qamj';})
            .concat([{id:'qamj',name:'QA MJ',campus:'QA Campus',verified:true}]);
          st.auth.session={uid:'qamj',at:Date.now(),remember:true};
          HUB.store.save(); HUB.auth.restore();
          try{HUB.auth.close()}catch(e){} return 1;""")
        time.sleep(0.8)
        fr = j(c, FREEZE_JS.replace('__T__', str(t_ms)))
        print('freeze T=%dms -> %s' % (t_ms, fr))
        r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True)
        p = os.path.join(OUT, name)
        with open(p, 'wb') as f:
            f.write(base64.b64decode(r['data']))
        print('shot ' + name)
        errs = j(c, "return (window.__huberr||[]).slice(0,8);")
        check('zero console errors [%s]' % name, not errs, errs)
        c.ws.close()
    finally:
        try: proc.terminate()
        except Exception: pass

one_phase('mj4-moonwalk.png', 1100)
one_phase('mj4-spin.png', 2650)
one_phase('mj4-dooropen.png', 3350)
one_phase('mj4-walkin.png', 3950)
print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
