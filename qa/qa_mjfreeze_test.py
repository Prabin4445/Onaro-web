#!/usr/bin/env python3
"""Test WAAPI freeze semantics: does anim.currentTime=T account for CSS delay?"""
import subprocess, time, json, os, sys
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9459
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-mjfreeze'

def j(c, expr):
    e = expr.strip()
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

subprocess.run(['rm', '-rf', PROF])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
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
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"})
    c.send('Page.navigate', {'url': BASE})
    t0 = time.time()
    while time.time() - t0 < 30:
        if j(c, "return !!(window.HUB&&HUB.logout&&HUB.logout.play);"):
            break
        time.sleep(0.5)
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
    # freeze test: play, force reflow, list animations with timing, set currentTime=3350, report door transform
    info = j(c, """
      HUB.logout.play();
      void document.getElementById('loStrip').offsetWidth;
      var anims = document.getAnimations();
      var out = ['n=' + anims.length];
      for (var i = 0; i < anims.length; i++) {
        var a = anims[i], el = a.effect.target, tm = a.effect.getTiming();
        var cls = el.className && el.className.baseVal !== undefined ? '[svg-el]' : String(el.className).split(' ')[0];
        out.push(cls + ' delay=' + tm.delay + ' dur=' + tm.duration + ' iter=' + tm.iterations);
      }
      // now freeze at T=3350 for ALL, then read the door's computed transform + glow opacity
      for (var k = 0; k < anims.length; k++) { try { anims[k].pause(); anims[k].currentTime = 3350; } catch (e) {} }
      void document.getElementById('loStrip').offsetWidth;
      var door = document.querySelector('.lo-door');
      var glow = document.querySelector('.lo-glow');
      out.push('door@3350=' + getComputedStyle(door).transform);
      out.push('glowOpacity@3350=' + getComputedStyle(glow).opacity);
      // and the man's translate
      var man = document.querySelector('.lo-man');
      out.push('man@3350=' + getComputedStyle(man).transform + ' opacity=' + getComputedStyle(man).opacity);
      return out;
    """)
    for line in (info or []):
        print(line)
    c.ws.close()
finally:
    try: proc.terminate()
    except Exception: pass
