#!/usr/bin/env python3
"""Debug: when does .lo-strip disappear during HUB.logout.play()?"""
import subprocess, time, json, os, sys
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP

PORT = 9458
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-mjdbg'

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

subprocess.run(['rm', '-rf', PROF])
proc = subprocess.Popen(['/opt/meta-chromium/chrome', '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
    '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=390,844', 'about:blank'])
time.sleep(3)

def open_tab():
    req = urllib.request.Request('http://127.0.0.1:%d/json/new?about:blank' % PORT, method='PUT')
    for _ in range(60):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.5)
    raise RuntimeError('no chrome')

try:
    c = CDP(open_tab()['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"})
    c.send('Page.navigate', {'url': BASE})
    t0 = time.time()
    while time.time() - t0 < 30:
        if j(c, "!!(window.HUB&&HUB.logout&&HUB.logout.play)"):
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
        /* spy on strip removal */
        window.__loGoneAt=0;
        new MutationObserver(function(muts){
          for(var i=0;i<muts.length;i++){ var m=muts[i];
            for(var k=0;k<m.removedNodes.length;k++){
              var n=m.removedNodes[k];
              if(n.id==='loStrip'||(n.querySelector&&n.querySelector('#loStrip'))){
                window.__loGoneAt=Math.round(performance.now()-window.__loT0);
              } } } }).observe(document.documentElement,{childList:true,subtree:true});
      })(); return 1""")
    time.sleep(1)
    print('logged in:', j(c, "!!HUB.auth.currentUser()"))
    j(c, "window.__loT0=performance.now(); HUB.logout.play(); return 1")
    t0 = time.time()
    for i in range(14):
        el = time.time() - t0
        strip = j(c, "!!document.getElementById('loStrip')")
        login = j(c, "!document.getElementById('authRoot').hidden")
        gone = j(c, "window.__loGoneAt||0")
        user = j(c, "!!(HUB.auth.currentUser&&HUB.auth.currentUser())")
        print("t=%.1f strip=%s loginBack=%s user=%s goneAt=%s" % (el, strip, login, user, gone))
        time.sleep(0.5)
finally:
    try: proc.terminate()
    except Exception: pass
