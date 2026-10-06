#!/usr/bin/env python3
"""Laundry Mode one-off visual check."""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9462
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-style-lau'
OUT = os.path.dirname(os.path.abspath(__file__))
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok: fails.append(n)

def j(c, expr):
    e = expr.strip()
    if e.startswith('return '): e = e[7:].rstrip().rstrip(';')
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q: instr = False
        elif ch in '"\'': instr, q = True, ch
        elif ch in '([{': depth += 1
        elif ch in ')]}': depth -= 1
        elif ch == ';' and depth == 0: top_semi = True; break
    if not top_semi: e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

def wait_true(c, expr, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if j(c, expr) is True: return True
        time.sleep(0.4)
    return False

def shot(c, name, w=390, h=844):
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(0.6)
    r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True)
    p = os.path.join(OUT, name)
    open(p, 'wb').write(base64.b64decode(r['data']))
    print('shot:', p)

def open_tab():
    req = urllib.request.Request('http://127.0.0.1:%d/json/new?about:blank' % PORT, method='PUT')
    for _ in range(60):
        try:
            with urllib.request.urlopen(req, timeout=5) as r: return json.load(r)
        except Exception: time.sleep(0.5)
    raise RuntimeError('no devtools')

ERR_HOOK = ("try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
            "window.__huberr=[];"
            "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
            "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

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
    assert wait_true(c, "return !!(window.HUB&&HUB.style&&HUB.showTab);", 30)
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True: break
        time.sleep(0.5)
    j(c, """(function(){ var st=HUB.store.state;
      st.auth={session:{uid:'qal',at:Date.now(),remember:true},users:[{id:'qal',name:'QA',campus:'QA',verified:true}]};
      st.prefs.dark=true; st.profile={name:'QA',gender:'male'};
      HUB.store.save(); HUB.applyTheme();
      try{HUB.auth.close()}catch(e){}
      try{var w=document.getElementById('wlcmHost'); if(w) w.remove();}catch(e){}
      return 1; })()""")
    time.sleep(0.8)
    # seed one laundry + one borrowed item, then open laundry view
    j(c, """(function(){ var T=HUB.style._t, DB=T.blank();
      DB.items=[
        {id:'l1',name:'White Tee',category:'tops',colors:['white'],seasons:['summer'],occasions:['casual'],tags:[],price:0,favorite:false,status:'laundry',wearCount:2,lastWorn:null,photo:null,archived:false,created:Date.now()},
        {id:'l2',name:'Denim Jacket',category:'jackets',colors:['denim'],seasons:['fall'],occasions:['casual'],tags:[],price:0,favorite:false,status:'borrowed',wearCount:0,lastWorn:null,photo:null,archived:false,created:Date.now()},
        {id:'l3',name:'Black Jeans',category:'bottoms',colors:['black'],seasons:['winter'],occasions:['casual'],tags:[],price:0,favorite:false,status:'available',wearCount:1,lastWorn:null,photo:null,archived:false,created:Date.now()}
      ]; T.setDB(DB); return 1; })()""")
    time.sleep(0.4)
    j(c, "HUB.style.open(); return 1;")
    time.sleep(0.6)
    j(c, """(function(){ var b=[...document.querySelectorAll('.sty-menu')].find(x=>x.getAttribute('data-go')==='laundry');
      b.click(); return 1; })()""")
    time.sleep(0.8)
    check('laundry view opens', j(c, "return !!document.querySelector('.sty-laugrp');") is True)
    check('2 non-available rows', j(c, "return document.querySelectorAll('[data-lau]').length;") == 2, j(c, "return document.querySelectorAll('[data-lau]').length;"))
    shot(c, 'st-dark-laundry.png')
    # wash one: click back-to-closet
    j(c, "document.querySelector('[data-lau]').click(); return 1;")
    time.sleep(0.8)
    check('wash back -> 1 row left', j(c, "return document.querySelectorAll('[data-lau]').length;") == 1)
    check('status now available', j(c, "return HUB.style._t.DB.items.find(x=>x.id==='l1').status;") == 'available')
    errs = j(c, "return (window.__huberr||[]).slice(0,10);")
    check('ZERO console errors', not errs, errs)
    # closet grid renders with laundry item (ST_EMOJI regression guard)
    j(c, "HUB.style.open(); return 1;")
    time.sleep(0.5)
    j(c, """(function(){ var b=[...document.querySelectorAll('.sty-menu')].find(x=>x.getAttribute('data-go')==='closet');
      b.click(); return 1; })()""")
    time.sleep(0.8)
    check('closet grid renders with borrowed badge', j(c, "return !!document.querySelector('.sty-st');") is True)
    errs = j(c, "return (window.__huberr||[]).slice(0,10);")
    check('ZERO console errors (grid)', not errs, errs)
    shot(c, 'st-dark-closet-grid.png')
    c.ws.close()
finally:
    try: proc.terminate()
    except Exception: pass
print('\n==== %d FAIL ===' % len(fails))
if fails: print('FAILS:', fails); sys.exit(1)
print('LAUNDRY CHECK GREEN')
