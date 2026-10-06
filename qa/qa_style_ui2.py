#!/usr/bin/env python3
"""Style Closet UI modernization + Runway QA (2026-10-01).

Covers the 2026-10-01 upgrade: glass entry card, floating clay icon, spring
easings, ink ripple, chip tap-pop, count-up, skeleton shimmer, and THE RUNWAY
3D card stack (skeleton -> staggered deal, drag swipe w/ momentum, arrows,
dots, wear-today logging, shuffle, reduced-motion path, i18n). Per theme
(dark/light), 390+320px, zero console errors.
"""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9462
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-style-ui2'
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
        time.sleep(0.4)
    return False

def shot(c, name, w=390, h=844):
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(0.6)
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
  var T=HUB.style._t, mk=function(n,cat,colors,seasons,occs,extra){
    var it={id:'qa-'+n.toLowerCase().replace(/[^a-z0-9]+/g,'-'),name:n,category:cat,colors:colors,
      seasons:seasons,occasions:occs,tags:[],price:0,favorite:false,status:'available',
      wearCount:0,lastWorn:null,photo:null,archived:false,created:Date.now()};
    if(extra) for(var k in extra) it[k]=extra[k];
    return it;
  };
  var DB=T.blank();
  DB.items=[
    mk('White Tee','tops',['white'],['spring','summer'],['casual','class'],{favorite:true}),
    mk('Blue Shirt','tops',['blue'],['spring','fall'],['work','class','interview']),
    mk('Black Jeans','bottoms',['black'],['fall','winter','spring'],['casual','class','dinner']),
    mk('Khaki Chinos','bottoms',['beige'],['spring','summer'],['work','interview','casual']),
    mk('Red Dress','dresses',['red'],['summer'],['party','dinner','wedding']),
    mk('Denim Jacket','jackets',['denim'],['spring','fall'],['casual','coffee']),
    mk('Gray Hoodie','sweaters',['gray'],['fall','winter'],['casual','gym','class']),
    mk('White Sneakers','shoes',['white'],['spring','summer'],['casual','class','gym']),
    mk('Brown Boots','shoes',['brown'],['fall','winter'],['dinner','work']),
    mk('Canvas Tote','bags',['beige'],['spring','summer'],['casual','class','work']),
    mk('Gold Watch','jewelry',['gold'],['spring','summer','fall','winter'],['dinner','work','wedding']),
    mk('Navy Blazer','jackets',['navy'],['fall','winter','spring'],['work','interview','dinner'])
  ];
  T.setDB(DB);
  return DB.items.length;
})()"""

def boot(c, dark):
    j(c, """(function(){ var st=HUB.store.state;
      st.auth={session:{uid:'qaui2',at:Date.now(),remember:true},
        users:[{id:'qaui2',name:'QA UI2',campus:'QA Campus',verified:true}]};
      st.prefs.dark=%s; st.profile={name:'QA UI2',gender:'male'};
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

def open_runway(c):
    """Open runway from the home menu; returns True when dealt cards are present."""
    j(c, "HUB.style.open(); return 1;")
    time.sleep(0.4)
    j(c, """(function(){ var b=[...document.querySelectorAll('#hubStyleRoot .sty-menu')]
      .find(x=>x.getAttribute('data-go')==='runway'); if(b) b.click(); return 1; })()""")
    return wait_true(c, "return document.querySelectorAll('.sty-rw-stage .rw-card').length>0;", 15)

def run_theme(dark):
    theme = 'dark' if dark else 'light'
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
        if not wait_true(c, "return !!(window.HUB&&HUB.style&&HUB.showTab);", 30):
            raise RuntimeError('no HUB.style')
        for _ in range(40):
            if j(c, "return !document.getElementById('splash');") is True:
                break
            time.sleep(0.5)
        check('[%s] seeded 12 items' % theme, boot(c, dark) == 12)

        # ---- A. entry card: glass + floating clay icon + count-up ----
        check('[%s] card renders' % theme,
              j(c, "return !!document.querySelector('[data-style-card]');") is True)
        check('[%s] card has glass gradient background' % theme,
              j(c, "return getComputedStyle(document.querySelector('[data-style-card]')).backgroundImage.indexOf('gradient')>=0;") is True)
        check('[%s] card clay icon floats (styFloat)' % theme,
              j(c, "return getComputedStyle(document.querySelector('.sty-cardhead .sty-clay')).animationName;") == 'styFloat')
        check('[%s] count-up rendered a number on card' % theme,
              j(c, "return document.querySelectorAll('[data-style-card] [data-count]').length;") >= 1)
        shot(c, 'ui2-%s-card.png' % theme)

        # ---- B. fast entrance (PERF 2026-10-02: no spring, no stagger) + ink ripple + chip pop ----
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.4)
        check('[%s] menu entrance is fast ease-out, no stagger' % theme,
              j(c, """return (function(){ var cs=getComputedStyle(document.querySelector('#hubStyleRoot .sty-menu'));
                var cs2=getComputedStyle(document.querySelectorAll('#hubStyleRoot .sty-menu')[7]);
                return cs.animationTimingFunction+'|'+cs.animationDuration+'|'+cs.animationDelay+'|'+cs2.animationDelay; })();""") == 'ease-out|0.22s|0s|0s')
        check('[%s] ink ripple fires on CTA press' % theme,
              j(c, """(function(){ var b=document.querySelector('#hubStyleRoot .sty-cta')||document.querySelector('[data-style-card] .sty-cta');
                if(!b) return 'nobtn';
                b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true,clientX:10,clientY:10}));
                return document.querySelectorAll('.sty-ink').length; })()""") >= 1)
        time.sleep(0.8)
        check('[%s] ripple element cleans up' % theme,
              j(c, "return document.querySelectorAll('.sty-ink').length;") == 0)
        j(c, """(function(){ var b=document.querySelector('#hubStyleRoot [data-go="styleme"]');
          if(b) b.click(); return 1; })()""")
        time.sleep(0.8)
        check('[%s] styleme view opens' % theme,
              j(c, "return document.querySelectorAll('#hubStyleRoot .sty-chips .chip:not(.static)').length;") >= 3)
        check('[%s] chip tap triggers sty-tap pop' % theme,
              j(c, """(function(){ var ch=document.querySelector('#hubStyleRoot .sty-chips .chip:not(.static)');
                if(!ch) return 'nochip';
                ch.click();
                var cs=getComputedStyle(ch);
                return ch.classList.contains('sty-tap')||cs.animationName==='styTap'?'POP':'none'; })()""") == 'POP')

        # ---- C. skeleton shimmer keyframes present (transform-only) ----
        check('[%s] styShimmer keyframes are transform-only' % theme,
              j(c, """(function(){ for(var i=0;i<document.styleSheets.length;i++){ try{
                  var rs=document.styleSheets[i].cssRules;
                  for(var k=0;k<rs.length;k++){ var r=rs[k];
                    if(r.type===7&&r.name==='styShimmer'){
                      var t=r.cssRules[r.cssRules.length-1].cssText;
                      return t.indexOf('transform')>=0&&t.indexOf('left')<0; } } }catch(e){} }
                return false; })()""") is True)

        # ---- D. THE RUNWAY ----
        # open fresh, catch the skeleton phase immediately
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.4)
        j(c, """(function(){ var b=[...document.querySelectorAll('#hubStyleRoot .sty-menu')]
          .find(x=>x.getAttribute('data-go')==='runway'); if(b) b.click(); return 1; })()""")
        time.sleep(0.15)
        check('[%s] runway skeleton shimmer shows during scoring' % theme,
              j(c, "return document.querySelectorAll('.sty-rw-stage .rw-skel').length;") >= 1)
        check('[%s] runway heading i18n' % theme,
              j(c, "return document.querySelector('.sty-rw-head h2').textContent;") == 'The Runway')
        check('[%s] runway dealt' % theme,
              wait_true(c, "return document.querySelectorAll('.sty-rw-stage .rw-card').length>0;", 15) is True)
        ncards = j(c, "return document.querySelectorAll('.sty-rw-stage .rw-card').length;")
        check('[%s] runway has 2-6 distinct look cards' % theme, 2 <= ncards <= 6, ncards)
        ndots = j(c, "return document.querySelectorAll('#styRwDots i').length;")
        check('[%s] dots match card count' % theme, ndots == ncards, (ndots, ncards))
        check('[%s] deal animation class applied' % theme,
              j(c, "return document.querySelectorAll('.sty-rw-stage .rw-card.rw-deal').length;") >= 1)
        check('[%s] front card is opacity 1, centered' % theme,
              j(c, """(function(){ var cd=document.querySelector('.sty-rw-stage .rw-card[data-i="0"]');
                if(!cd) return 'nocard';
                var cs=getComputedStyle(cd);
                return cs.opacity==='1'&&cs.transform!=='none'?'OK':cs.opacity+'/'+cs.transform; })()""") == 'OK')
        check('[%s] score chips render (harmony %%)' % theme,
              j(c, "return document.querySelector('.rw-chips').textContent.indexOf('%')>=0;") is True)
        check('[%s] runway no page overflow' % theme,
              j(c, "return document.documentElement.scrollWidth<=document.documentElement.clientWidth+1;") is True)
        shot(c, 'ui2-%s-runway.png' % theme)

        # drag swipe left -> next card (real pointer events via CDP)
        dot0 = j(c, "return [...document.querySelectorAll('#styRwDots i')].findIndex(x=>x.classList.contains('on'));")
        rect = j(c, """(function(){ var s=document.getElementById('styRwStage'); var r=s.getBoundingClientRect();
          return [r.left+r.width/2, r.top+200]; })()""")
        cx, cy = rect[0], rect[1]
        c.send('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': cx, 'y': cy, 'button': 'left', 'clickCount': 1})
        for k in range(1, 9):
            c.send('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': cx - k*25, 'y': cy, 'button': 'left', 'buttons': 1})
            time.sleep(0.01)
        c.send('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': cx - 200, 'y': cy, 'button': 'left'})
        time.sleep(1.0)
        dot1 = j(c, "return [...document.querySelectorAll('#styRwDots i')].findIndex(x=>x.classList.contains('on'));")
        check('[%s] swipe-left advances one card (momentum snap)' % theme, dot1 == dot0 + 1, (dot0, dot1))
        shot(c, 'ui2-%s-runway-2.png' % theme)

        # arrows go back
        j(c, "document.getElementById('styRwPrev').click(); return 1;")
        time.sleep(0.9)
        check('[%s] prev arrow returns to first card' % theme,
              j(c, "return [...document.querySelectorAll('#styRwDots i')].findIndex(x=>x.classList.contains('on'));") == 0)

        # wear today from runway logs + goes to calendar
        worn = j(c, """(function(){ var b=document.querySelector('.sty-rw-stage .rw-card[data-i="0"] .rw-wear');
          if(b){ b.click(); return 1; } return 0; })()""")
        time.sleep(1.4)
        check('[%s] runway wear-today clicked' % theme, worn == 1)
        check('[%s] runway wear logged to calendar' % theme,
              j(c, "return Object.keys(HUB.style._t.DB.cal).length;") >= 1)
        check('[%s] runway wear lands on calendar view' % theme,
              j(c, "return !!document.querySelector('.sty-cal-d.has.today');") is True)
        shot(c, 'ui2-%s-runway-worn.png' % theme)

        # shuffle re-deals the stack
        if not open_runway(c):
            check('[%s] shuffle runway reopen' % theme, False)
        else:
            j(c, "document.getElementById('styRwShuffle').click(); return 1;")
            time.sleep(0.3)
            check('[%s] shuffle shows skeleton then re-deals' % theme,
                  wait_true(c, "return document.querySelectorAll('.sty-rw-stage .rw-card').length>0;", 15) is True)

        # result-view runway button
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.4)
        j(c, """(function(){ var b=document.querySelector('#hubStyleRoot [data-go="styleme"]');
          if(b) b.click(); return 1; })()""")
        time.sleep(0.6)
        j(c, """(function(){
          for(var _v of ['casual','minimal','comfortable','auto']){
            var b=[...document.querySelectorAll('#hubStyleRoot [data-v]')]
              .find(x=>x.getAttribute('data-v')===_v); if(b) b.click(); }
          return 1; })()""")
        time.sleep(1.2)
        check('[%s] runway via result-view button' % theme,
              j(c, """(function(){ var b=document.querySelector('[data-r=runway]');
                if(b){ b.click(); return 1; } return 0; })()""") == 1 and
              wait_true(c, "return document.querySelectorAll('.sty-rw-stage .rw-card').length>0;", 15) is True)

        # ---- E. reduced motion: no skeleton, no deal animation ----
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.4)
        j(c, """(function(){ var b=[...document.querySelectorAll('#hubStyleRoot .sty-menu')]
          .find(x=>x.getAttribute('data-go')==='runway'); if(b) b.click(); return 1; })()""")
        time.sleep(0.5)
        check('[%s] reduced-motion: cards render without deal animation' % theme,
              j(c, "return document.querySelectorAll('.sty-rw-stage .rw-card').length;") >= 1 and
              j(c, "return document.querySelectorAll('.sty-rw-stage .rw-card.rw-deal').length;") == 0)
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})

        # ---- F. 320px + i18n ----
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': 320, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(0.8)
        check('[%s] 320px runway no overflow' % theme,
              j(c, "return document.documentElement.scrollWidth<=document.documentElement.clientWidth+1;") is True)
        shot(c, 'ui2-%s-runway-320.png' % theme, w=320)
        j(c, "HUB.i18n.setLang('es'); return 1;")
        check('[%s] es locale actually loaded' % theme,
              wait_true(c, "return HUB.i18n._dict('es')!==HUB.i18n._dict('en');", 15) is True)
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.8)
        j(c, """(function(){ var b=[...document.querySelectorAll('#hubStyleRoot .sty-menu')]
          .find(x=>x.getAttribute('data-go')==='runway'); if(b) b.click(); return 1; })()""")
        check('[%s] runway heading Spanish' % theme,
              wait_true(c, "return document.querySelectorAll('.sty-rw-stage .rw-card').length>0;", 15) and
              j(c, "return document.querySelector('.sty-rw-head h2').textContent;") == 'La Pasarela')
        j(c, "HUB.i18n.setLang('en'); return 1;")

        # ---- G. zero console errors ----
        errs = j(c, "return window.__huberr||[];")
        check('[%s] ZERO console errors' % theme, errs == [], str(errs)[:300])
    finally:
        proc.terminate()

if __name__ == '__main__':
    for dark in (True, False):
        run_theme(dark)
    print("\n==== %d FAIL ====" % len(fails))
    print("FAILURES:", fails if fails else "none — ALL GREEN")
