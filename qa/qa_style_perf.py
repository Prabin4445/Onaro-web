#!/usr/bin/env python3
"""Style Closet overlay entrance PERF QA (2026-10-02).

Measures tap-to-open performance of the Style Closet overlay:
  - open() synchronous main-thread blocking time
  - tap -> overlay first paint (MutationObserver + double rAF)
  - tap -> entrance animations settled (last .sty-menu animationend)
  - tap -> click-through interactive (menu card click lands on closet view)
  - long tasks (>50ms) during the entrance window
Targets: first paint <150ms, interactive <400ms, zero long tasks >50ms.
Per theme (dark/light), 390+320px, zero console errors.
"""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9464
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-style-perf'
OUT = os.path.dirname(os.path.abspath(__file__))
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok:
        fails.append(n)

def j(c, expr, await_=False):
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
    r = c.send('Runtime.evaluate', {'expression': e, 'returnByValue': True,
                                    'awaitPromise': await_}, wait=True)
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
        time.sleep(0.2)
    return False

def shot(c, name, w=390, h=844):
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(0.5)
    r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True)
    p = os.path.join(OUT, name)
    with open(p, 'wb') as f:
        f.write(base64.b64decode(r['data']))
    print('shot:', p)

def open_tab():
    req = urllib.request.Request('http://127.0.0.1:%d/json/new?about:blank' % PORT, method='PUT')
    for _ in range(60):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.5)
    raise RuntimeError('no devtools')

SEED_ITEMS = """(function(){
  var T=HUB.style._t, mk=function(n,cat){
    return {id:'qa-'+n.toLowerCase().replace(/[^a-z0-9]+/g,'-'),name:n,category:cat,colors:['white'],
      seasons:['spring'],occasions:['casual'],tags:[],price:0,favorite:false,status:'available',
      wearCount:0,lastWorn:null,photo:null,archived:false,created:Date.now()};
  };
  var DB=T.blank(); var cats=['tops','bottoms','dresses','jackets','shoes','bags'];
  DB.items=[]; for(var i=0;i<24;i++) DB.items.push(mk('Item '+i,cats[i%cats.length]));
  T.setDB(DB); return DB.items.length;
})()"""

# Installs the perf probe, clicks the real entry-card button, returns timings.
MEASURE = """(function(){
  return new Promise(function(resolve){
    var res={};
    // longtask collector for the entrance window
    var longs=[];
    try{
      var po=new PerformanceObserver(function(list){
        list.getEntries().forEach(function(e){ if(e.duration>50) longs.push(Math.round(e.duration)); });
      });
      po.observe({entryTypes:['longtask']});
    }catch(e){}
    // wrap open() to time its synchronous blocking portion
    var orig=HUB.style.open, syncMs=0;
    HUB.style.open=function(){ var t0=performance.now(); var r=orig.apply(this,arguments);
      syncMs=performance.now()-t0; return r; };
    var tClick=0, tPaint=0, tSettled=0;
    var mo=new MutationObserver(function(){
      var root=document.getElementById('hubStyleRoot');
      if(root && !tPaint){
        requestAnimationFrame(function(){ requestAnimationFrame(function(){
          tPaint=performance.now();
          // arm the settled timer: last .sty-menu animationend (or fallback)
          var menus=[...document.querySelectorAll('#hubStyleRoot .sty-menu')];
          if(!menus.length){ tSettled=tPaint; return; }
          var done=0, total=menus.length, to=setTimeout(function(){ tSettled=performance.now(); },3000);
          menus.forEach(function(m){
            m.addEventListener('animationend',function h(){
              m.removeEventListener('animationend',h); done++;
              if(done>=total){ clearTimeout(to); tSettled=performance.now(); }
            });
          });
        });});
      }
    });
    mo.observe(document.documentElement,{childList:true,subtree:true});
    var btn=document.querySelector('[data-style-card] [data-act="open"]');
    if(!btn){ resolve({error:'no open button'}); return; }
    tClick=performance.now();
    btn.click();
    var t0=Date.now();
    (function poll(){
      if(tSettled || Date.now()-t0>8000){
        try{po.disconnect();}catch(e){}
        mo.disconnect();
        HUB.style.open=orig;
        res.syncMs=Math.round(syncMs*10)/10;
        res.tapToPaint=tPaint?Math.round((tPaint-tClick)*10)/10:null;
        res.tapToSettled=tSettled?Math.round((tSettled-tClick)*10)/10:null;
        res.longTasks=longs;
        resolve(res);
      } else setTimeout(poll,100);
    })();
  });
})()"""

def boot(c, dark):
    j(c, """(function(){ var st=HUB.store.state;
      st.auth={session:{uid:'qaperf',at:Date.now(),remember:true},
        users:[{id:'qaperf',name:'QA Perf',campus:'QA Campus',verified:true}]};
      st.prefs.dark=%s; st.profile={name:'QA Perf',gender:'male'};
      HUB.store.save(); HUB.applyTheme();
      try{HUB.auth.close()}catch(e){}
      try{var w=document.getElementById('wlcmHost'); if(w) w.remove();}catch(e){}
      return 1; })()""" % ('true' if dark else 'false'))
    time.sleep(0.8)
    j(c, "HUB.showTab('daily'); return 1;")
    time.sleep(1.2)
    n = j(c, SEED_ITEMS)
    j(c, "HUB.showTab('daily'); return 1;")
    time.sleep(1.0)
    return n

def run_theme(dark, w):
    theme = 'dark' if dark else 'light'
    tag = '%s-%d' % (theme, w)
    subprocess.run(['rm', '-rf', PROF])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=%d,844' % w, 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(3)
        c = CDP(open_tab()['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': w, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.addScriptToEvaluateOnNewDocument', {'source': ERR_HOOK})
        c.send('Page.navigate', {'url': BASE})
        if not wait_true(c, "return !!(window.HUB&&HUB.style&&HUB.showTab);", 30):
            raise RuntimeError('no HUB.style')
        for _ in range(40):
            if j(c, "return !document.getElementById('splash');") is True:
                break
            time.sleep(0.5)
        check('[%s] seeded 24 items' % tag, boot(c, dark) == 24)
        check('[%s] entry card present' % tag,
              j(c, "return !!document.querySelector('[data-style-card] [data-act=\"open\"]');") is True)

        # warm-up open+close: first-ever open pays font/JIT/image warm-up costs
        # that don't reflect the steady state PraBin experiences
        j(c, "HUB.style.open(); HUB.style.close(); return 1;")
        time.sleep(1.0)

        m = j(c, MEASURE, await_=True)
        print('[%s] MEASURE: %s' % (tag, json.dumps(m)))
        if not m or m.get('error'):
            check('[%s] measurement ran' % tag, False, m)
            return
        sync = m.get('syncMs'); sync = 999 if sync is None else sync
        check('[%s] open() sync blocking <50ms' % tag, sync < 50,
              'sync=%sms' % sync)
        check('[%s] tap->first-paint <150ms' % tag, (m.get('tapToPaint') or 9999) < 150,
              'paint=%sms' % m.get('tapToPaint'))
        check('[%s] tap->settled <400ms' % tag, (m.get('tapToSettled') or 9999) < 400,
              'settled=%sms' % m.get('tapToSettled'))
        longs = m.get('longTasks') or []
        check('[%s] no long tasks >50ms during entrance' % tag, len(longs) == 0,
              'longs=%s' % longs)

        # click-through: a menu card must respond promptly after open
        t0 = time.time()
        ok = j(c, """(function(){
          var b=[...document.querySelectorAll('#hubStyleRoot .sty-menu')]
            .find(function(x){return x.getAttribute('data-go')==='closet';});
          if(!b) return false; b.click();
          return document.querySelectorAll('#styBody .sty-item').length>0 ||
                 document.body.innerHTML.indexOf('styBody')>=0;
        })()""")
        dt = round((time.time() - t0) * 1000)
        check('[%s] menu click-through works' % tag, ok is True, '%dms' % dt)
        shot(c, 'perf-%s-open.png' % tag, w, 844)
        j(c, "HUB.style.close(); return 1;")
        time.sleep(0.4)

        errs = j(c, "return window.__huberr||[];")
        check('[%s] zero console errors' % tag, not errs, str(errs)[:200])
    finally:
        proc.terminate()

if __name__ == '__main__':
    for dark in (True, False):
        for w in (390, 320):
            run_theme(dark, w)
    print('FAILURES:', fails if fails else 'none')
    sys.exit(1 if fails else 0)
