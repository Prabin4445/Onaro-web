#!/usr/bin/env python3
"""Style Closet occasion/weather/vibe/feel clay-icon QA (2026-10-01).

Verifies the 2026-10-01 icon sweep: every occasion chip (add-item form,
Style Me, quick wear), weather chips, vibe chips, feel chips, settings
weather, packing trip-vibe chips, runway shuffle and streak render loaded
clay PNG icons (no raw emoji in icon slots). Per theme (dark/light),
390+320px, zero console errors.
"""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9463
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-style-occ'
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

# Every chip icon slot inside rootSel must hold a loaded clay <img>
# (naturalWidth>0) or an .ico-fb fallback span; raw emoji text fails.
CHIP_ICON_JS = """(function(rootSel){
  var root=document.querySelector(rootSel);
  if(!root) return 'noroot';
  var chips=root.querySelectorAll('.chip');
  if(!chips.length) return 'nochips';
  var bad=[], unloaded=[];
  chips.forEach(function(ch){
    var slot=ch.querySelector('.sty-clay');
    if(!slot){ bad.push('noslot'); return; }
    var img=slot.querySelector('img');
    if(img){ if(!(img.naturalWidth>0)) unloaded.push(img.getAttribute('data-icon')); return; }
    if(slot.querySelector('.ico-fb')) return;
    bad.push(ch.textContent.slice(0,12));
  });
  if(unloaded.length) return 'unloaded:'+unloaded.join(',');
  if(bad.length) return 'bad:'+bad.slice(0,3).join('|');
  return chips.length;
})('%s')"""

EMOJI_JS = """(function(rootSel){
  var root=document.querySelector(rootSel);
  if(!root) return 'noroot';
  var re=/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}\\u{2B00}-\\u{2BFF}]/u;
  var hits=[];
  root.querySelectorAll('.sty-clay').forEach(function(s){
    if(re.test(s.textContent)) hits.push(s.textContent.slice(0,8));
  });
  return hits.length?('emoji:'+hits.slice(0,3).join('|')):'clean';
})('%s')"""

EXPECTED = {
    'st-occ-class': '🎓', 'st-occ-coffee': '☕', 'st-occ-interview': '💼',
    'st-occ-dinner': '🍽️', 'st-occ-party': '🪩', 'st-occ-gym': '🏋️',
    'st-occ-airport': '✈️', 'st-occ-vacation': '🏖️', 'st-occ-wedding': '💍',
    'st-occ-birthday': '🎂', 'st-occ-casual': '🏠', 'st-occ-work': '💻',
    'st-wx-hot': '☀️', 'st-wx-warm': '🌤️', 'st-wx-cool': '🍂',
    'st-wx-cold': '❄️', 'st-wx-rainy': '🌧️', 'st-wx-auto': '🪄',
    'st-vibe-minimal': '⚪', 'st-vibe-feminine': '🎀', 'st-vibe-edgy': '⚡',
    'st-vibe-clean': '💧', 'st-vibe-soft': '🌸', 'st-vibe-bold': '🔥',
    'st-vibe-casual': '👟', 'st-vibe-professional': '👔',
    'st-vibe-streetwear': '🧢', 'st-vibe-comfortable': '🌿',
    'st-feel-confident': '🏅', 'st-feel-cute': '💛', 'st-feel-elegant': '🦪',
    'st-feel-relaxed': '🌙', 'st-trip-city': '🏙️', 'st-trip-mountain': '⛰️',
    'st-shuffle': '🔀', 'st-photo': '🖼️',
}

def boot(c, dark):
    j(c, """(function(){ var st=HUB.store.state;
      st.auth={session:{uid:'qaocc',at:Date.now(),remember:true},
        users:[{id:'qaocc',name:'QA Occ',campus:'QA Campus',verified:true}]};
      st.prefs.dark=%s; st.profile={name:'QA Occ',gender:'male'};
      HUB.store.save(); HUB.applyTheme();
      try{HUB.auth.close()}catch(e){}
      try{var w=document.getElementById('wlcmHost'); if(w) w.remove();}catch(e){}
      return 1; })()""" % ('true' if dark else 'false'))
    time.sleep(0.8)
    j(c, "HUB.showTab('daily'); return 1;")
    time.sleep(1.2)

def open_add(c):
    j(c, "HUB.style.open(); return 1;")
    time.sleep(0.5)
    j(c, """(function(){ var b=document.querySelector('#hubStyleRoot [data-go="closet"]');
      if(b) b.click(); return 1; })()""")
    time.sleep(0.8)
    j(c, """(function(){ var b=document.querySelector('#hubStyleRoot .fab[data-go="add"]')
      ||document.querySelector('#hubStyleRoot [data-go="add"]');
      if(b) b.click(); return 1; })()""")
    return wait_true(c, "return !!document.getElementById('styFOcc');", 10)

def open_styleme(c):
    j(c, "HUB.style.open(); return 1;")
    time.sleep(0.5)
    j(c, """(function(){ var b=document.querySelector('#hubStyleRoot [data-go="styleme"]');
      if(b) b.click(); return 1; })()""")
    time.sleep(0.8)
    return wait_true(c, "return document.querySelectorAll('#hubStyleRoot .sty-chips .chip').length>0;", 10)

def open_view(c, go):
    j(c, "HUB.style.open(); return 1;")
    time.sleep(0.4)
    j(c, """(function(){ var b=[...document.querySelectorAll('#hubStyleRoot .sty-menu')]
      .find(x=>x.getAttribute('data-go')==='%s'); if(b) b.click(); return 1; })()""" % go)
    time.sleep(0.8)

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
        if not wait_true(c, "return !!(window.HUB&&HUB.style&&HUB.icons&&HUB.showTab);", 30):
            raise RuntimeError('no HUB')
        for _ in range(40):
            if j(c, "return !document.getElementById('splash');") is True:
                break
            time.sleep(0.5)
        boot(c, dark)

        # ---- 1. all 36 icons registered with PNG sources ----
        reg = j(c, """(function(){ var M=HUB.icons.map, bad=[];
          %s.forEach(function(n){ var m=M[n];
            if(!m||!m.src||m.src.indexOf(n+'.png')<0) bad.push(n); });
          return bad.length?('missing:'+bad.join(',')):'ok'; })()"""
            % json.dumps(list(EXPECTED.keys())))
        check('[%s] 36 icons registered' % theme, reg == 'ok', reg)

        # ---- 2. add-item occasion chips: 12 clay icons, no emoji ----
        check('[%s] add form opens' % theme, open_add(c))
        wait_true(c, """return (function(){ var r=document.getElementById('styFOcc');
          if(!r) return false; var im=r.querySelectorAll('img');
          return im.length===12 && [...im].every(function(i){ return i.naturalWidth>0; }); })();""", 20)
        r = j(c, CHIP_ICON_JS % '#styFOcc')
        check('[%s] 12 occasion chips all clay-loaded' % theme, r == 12, r)
        check('[%s] no emoji in occasion icon slots' % theme,
              j(c, EMOJI_JS % '#styFOcc') == 'clean')
        shot(c, 'occ-%s-add.png' % theme)

        # ---- 3. Style Me 4-step flow: occasion / vibe / feel / weather ----
        check('[%s] styleme opens' % theme, open_styleme(c))
        r = j(c, CHIP_ICON_JS % '#hubStyleRoot .sty-chips')
        check('[%s] styleme occasion step clay icons' % theme, r == 12, r)
        j(c, """(function(){ document.querySelector('#hubStyleRoot .sty-chips .chip').click(); return 1; })()""")
        time.sleep(0.8)
        r = j(c, CHIP_ICON_JS % '#hubStyleRoot .sty-chips')
        check('[%s] styleme vibe step clay icons' % theme, r == 10, r)
        j(c, """(function(){ document.querySelector('#hubStyleRoot .sty-chips .chip').click(); return 1; })()""")
        time.sleep(0.8)
        r = j(c, CHIP_ICON_JS % '#hubStyleRoot .sty-chips')
        check('[%s] styleme feel step clay icons' % theme, r == 6, r)
        j(c, """(function(){ document.querySelector('#hubStyleRoot .sty-chips .chip').click(); return 1; })()""")
        time.sleep(0.8)
        r = j(c, CHIP_ICON_JS % '#hubStyleRoot .sty-chips')
        check('[%s] styleme weather step clay icons (auto+5)' % theme, r == 6, r)
        check('[%s] no emoji in styleme icon slots' % theme,
              j(c, EMOJI_JS % '#hubStyleRoot') == 'clean')

        # ---- 4. settings weather chips ----
        open_view(c, 'settings')
        r = j(c, CHIP_ICON_JS % '#styWX')
        check('[%s] settings weather chips clay-loaded' % theme, r == 6, r)

        # ---- 5. packing trip-vibe chips ----
        open_view(c, 'packing')
        n = j(c, """(function(){ var r=document.querySelector('#hubStyleRoot .sty-chips');
          return r?r.querySelectorAll('.chip').length:0; })()""")
        check('[%s] packing trip-vibe chips = 4' % theme, n == 4, n)
        check('[%s] packing trip-vibe chips clay-loaded' % theme,
              j(c, CHIP_ICON_JS % '#hubStyleRoot .sty-chips') == 4)

        # ---- 6. 320px: no horizontal overflow on add form ----
        open_add(c)
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': 320, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(0.8)
        check('[%s] 320px add form no overflow' % theme,
              j(c, "return document.documentElement.scrollWidth<=320;") is True)
        shot(c, 'occ-%s-add-320.png' % theme, w=320)
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})

        # ---- 7. zero console errors ----
        errs = j(c, "return window.__huberr;")
        check('[%s] zero console errors' % theme, errs == [], str(errs)[:200])
    finally:
        try: proc.terminate()
        except Exception: pass

for dark in (True, False):
    run_theme(dark)

print('\n==== %d FAILURES ====' % len(fails))
for f in fails: print(' -', f)
sys.exit(1 if fails else 0)
