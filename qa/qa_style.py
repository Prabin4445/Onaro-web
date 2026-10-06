#!/usr/bin/env python3
"""Style Closet ruthless QA (2026-10-01).

One browser per theme (dark, light). Each: fresh profile, seed auth, boot,
Daily card, add-item UI, Style Me engine (incl. laundry exclusion), builder,
calendar, insights, packing, settings, i18n parity, screenshots at 390+320px
per theme, zero console errors. PraBin's bar: no excuses or mistakes.
"""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9461
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-style'
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
        # seed auth + theme
        j(c, """(function(){ var st=HUB.store.state;
          st.auth={session:{uid:'qast',at:Date.now(),remember:true},
            users:[{id:'qast',name:'QA Style',campus:'QA Campus',verified:true}]};
          st.prefs.dark=%s; st.profile={name:'QA Style',gender:'male'};
          HUB.store.save(); HUB.applyTheme();
          try{HUB.auth.close()}catch(e){}
          try{var w=document.getElementById('wlcmHost'); if(w) w.remove();}catch(e){}
          return 1; })()""" % ('true' if dark else 'false'))
        time.sleep(0.8)
        j(c, "HUB.showTab('daily'); return 1;")
        time.sleep(1.2)

        # 1. Daily card
        check('[%s] card renders' % theme,
              j(c, "return !!document.querySelector('[data-style-card]');") is True)
        check('[%s] clay icons loaded, no emoji fallback' % theme,
              j(c, "return document.querySelectorAll('[data-style-card] .ico-fb').length;") == 0)
        check('[%s] no page overflow' % theme,
              j(c, "return document.documentElement.scrollWidth<=document.documentElement.clientWidth+1;") is True)
        j(c, "var el=document.querySelector('[data-style-card]'); if(el) el.scrollIntoView({block:'center'}); return 1;")
        time.sleep(0.8)
        shot(c, 'st-%s-card.png' % theme)

        # 2. seed items -> Today's Look appears on card
        n = j(c, SEED_ITEMS)
        check('[%s] seeded 12 items' % theme, n == 12, n)
        j(c, "HUB.showTab('daily'); return 1;")
        time.sleep(1.0)
        check('[%s] today-look on card' % theme,
              j(c, "return !!document.querySelector('.sty-today');") is True)
        check('[%s] todayLook() returns 3+ items' % theme,
              j(c, "return (HUB.style.todayLook()||{items:[]}).items.length;") >= 3)

        # 3. add item via UI
        j(c, """(function(){ var b=document.querySelector('[data-style-card] [data-act="add"]');
          if(b) b.click(); return 1; })()""")
        time.sleep(0.8)
        check('[%s] add sheet opens' % theme,
              j(c, "return !!document.querySelector('#styFName');") is True)
        j(c, """(function(){
          document.getElementById('styFName').value='QA Leather Jacket';
          var cat=[...document.querySelectorAll('#styFCats [data-c]')].find(x=>x.getAttribute('data-c')==='jackets'); cat.click();
          [...document.querySelectorAll('#styFColors [data-c]')].filter(x=>x.getAttribute('data-c')==='black').forEach(x=>x.click());
          [...document.querySelectorAll('#styFOcc [data-c]')].filter(x=>x.getAttribute('data-c')==='dinner').forEach(x=>x.click());
          document.getElementById('styFSave').click(); return 1; })()""")
        time.sleep(0.8)
        check('[%s] item saved via UI (13 total)' % theme,
              j(c, "return HUB.style._t.DB.items.length;") == 13)
        check('[%s] toast shown' % theme,
              j(c, "return document.body.textContent.indexOf('Saved')>=0||document.getElementById('toastHost').textContent.length>0;") is True)
        shot(c, 'st-%s-closet.png' % theme)

        # 4. Style Me flow
        j(c, "HUB.style.open(); HUB.style._t; return 1;")
        time.sleep(0.3)
        j(c, """(function(){ HUB.style.open();
          var b=[...document.querySelectorAll('[data-go]')].find(x=>x.getAttribute('data-go')==='styleme');
          b.click(); return 1; })()""")
        time.sleep(0.8)
        check('[%s] styleme view opens' % theme,
              j(c, "return !!document.querySelector('#hubStyleRoot [data-v]');") is True)
        shot(c, 'st-%s-styleme.png' % theme)
        for _v in ['casual', 'minimal', 'comfortable', 'auto']:
            j(c, "var b=[...document.querySelectorAll('#hubStyleRoot [data-v]')].find(x=>x.getAttribute('data-v')==='%s'); if(b) b.click(); return 1;" % _v)
            time.sleep(0.5)
        time.sleep(0.8)
        res = j(c, "return document.querySelectorAll('.sty-look-it').length;")
        check('[%s] styleme result renders look (>=3)' % theme, res >= 3, res)
        check('[%s] own-all honest note' % theme,
              j(c, "return document.body.textContent.indexOf('already own everything')>=0;") is True)
        shot(c, 'st-%s-result.png' % theme)
        # try another
        j(c, "document.querySelector('[data-r=another]').click(); return 1;")
        time.sleep(0.8)
        check('[%s] try-another rerenders' % theme,
              j(c, "return document.querySelectorAll('.sty-look-it').length;") >= 3)

        # 5. laundry exclusion (engine level)
        excl = j(c, """(function(){ var T=HUB.style._t;
          var it=T.DB.items.find(x=>x.category==='jackets'); it.status='laundry'; T.setDB(T.DB);
          var r=T.styleMe({occasion:'casual',vibe:'minimal',feel:'comfortable',wx:'warm',count:6});
          return r.some(x=>x.id===it.id) ? 'LEAK' : 'OK'; })()""")
        check('[%s] laundry item excluded from Style Me' % theme, excl == 'OK', excl)

        # 6. Wear This -> calendar + streak
        j(c, "document.getElementById('styWearToday')||document.querySelector('[data-r=wear]'); return 1;")
        worn = j(c, """(function(){ var b=document.getElementById('styWearToday')||document.querySelector('[data-r=wear]');
          if(b){ b.click(); return 1; } return 0; })()""")
        time.sleep(0.8)
        check('[%s] wear logged to calendar' % theme,
              j(c, "return Object.keys(HUB.style._t.DB.cal).length;") >= 1)
        check('[%s] streak = 1' % theme,
              j(c, "return HUB.style.streak();") == 1)
        check('[%s] celebration particles fired' % theme,
              j(c, "return document.querySelectorAll('.sty-pop').length;") >= 10)
        check('[%s] unlock milestone toast' % theme,
              j(c, "return document.body.textContent.indexOf('outfits saved')>=0;") is True)
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.6)

        # 7. outfit builder -> save -> unlock toast
        j(c, """(function(){ var b=[...document.querySelectorAll('.sty-menu')].find(x=>x.getAttribute('data-go')==='builder');
          b.click(); return 1; })()""")
        time.sleep(0.8)
        j(c, """(function(){
          var slots=[...document.querySelectorAll('.sty-slot')];
          var tops=slots.find(x=>x.getAttribute('data-slot')==='tops'); tops.click(); return 1; })()""")
        time.sleep(0.6)
        j(c, """(function(){ var p=[...document.querySelectorAll('[data-pick]')][0]; if(p) p.click();
          document.getElementById('styOfName').value='QA Fit';
          document.getElementById('styOfSave').click(); return 1; })()""")
        time.sleep(0.8)
        check('[%s] outfit saved' % theme,
              j(c, "return HUB.style._t.DB.outfits.length;") == 2)

        # 8. calendar
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.5)
        j(c, """(function(){ var b=[...document.querySelectorAll('.sty-menu')].find(x=>x.getAttribute('data-go')==='calendar');
          b.click(); return 1; })()""")
        time.sleep(0.8)
        check('[%s] today cell marked worn' % theme,
              j(c, "return !!document.querySelector('.sty-cal-d.has.today');") is True)
        shot(c, 'st-%s-calendar.png' % theme)

        # 9. insights
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.5)
        j(c, """(function(){ var b=[...document.querySelectorAll('.sty-menu')].find(x=>x.getAttribute('data-go')==='insights');
          b.click(); return 1; })()""")
        time.sleep(1.0)
        check('[%s] progress ring renders' % theme,
              j(c, "return !!document.querySelector('.sty-ring .fg');") is True)
        check('[%s] never-worn row has 4 actions' % theme,
              j(c, "return document.querySelectorAll('[data-nact]').length;") >= 4)
        shot(c, 'st-%s-insights.png' % theme)

        # 10. packing
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.5)
        j(c, """(function(){ var b=[...document.querySelectorAll('.sty-menu')].find(x=>x.getAttribute('data-go')==='packing');
          b.click(); return 1; })()""")
        time.sleep(0.8)
        j(c, "document.getElementById('styPackGo').click(); return 1;")
        time.sleep(0.8)
        check('[%s] packing plan renders 5 days' % theme,
              j(c, "return document.querySelectorAll('#styPackOut .card').length;") == 5)
        shot(c, 'st-%s-packing.png' % theme)

        # 11. settings
        j(c, "HUB.style.open(); return 1;")
        time.sleep(0.5)
        j(c, """(function(){ var b=[...document.querySelectorAll('.sty-menu')].find(x=>x.getAttribute('data-go')==='settings');
          b.click(); return 1; })()""")
        time.sleep(0.8)
        j(c, """(function(){
          [...document.querySelectorAll('#styDR [data-dr]')].find(x=>x.getAttribute('data-dr')==='7').click();
          document.getElementById('styNewCat').value='qa-caps';
          document.getElementById('styAddCat').click(); return 1; })()""")
        time.sleep(0.6)
        check('[%s] settings persist' % theme,
              j(c, "return HUB.style._t.DB.settings.dontRepeat===7 && HUB.style._t.DB.cats.indexOf('qa-caps')>=0;") is True)
        shot(c, 'st-%s-settings.png' % theme)

        # 12. 320px key screens
        j(c, "HUB.showTab('daily'); return 1;")
        time.sleep(1.0)
        shot(c, 'st-%s-card-320.png' % theme, w=320, h=568)
        check('[%s] 320px no overflow' % theme,
              j(c, "return document.documentElement.scrollWidth<=321;") is True)

        # 13. i18n
        i18n = j(c, """(function(){ var d=HUB.i18n._dict;
          return [d('es')!==d('en'), d('es')['style.title'], d('ne')['style.title'], d('hi')['style.title']]; })()""")
        check('[%s] locales load + translate' % theme,
              i18n == [True, 'Armario de Estilo', 'स्टाइल क्लोजेट', 'स्टाइल क्लोज़ेट'], i18n)

        # 14. rose theme for female profile
        j(c, """(function(){ HUB.store.state.profile.gender='female'; HUB.store.save(); HUB.applyTheme(); HUB.style.open(); return 1; })()""")
        time.sleep(0.8)
        check('[%s] rose theme class on female' % theme,
              j(c, "return document.body.classList.contains('theme-rose');") is True)
        shot(c, 'st-%s-rose.png' % theme)

        errs = j(c, "return (window.__huberr||[]).slice(0,10);")
        check('[%s] ZERO console errors' % theme, not errs, errs)
        c.ws.close()
    finally:
        try: proc.terminate()
        except Exception: pass

run_theme(True)
run_theme(False)

print('\n==== %d checks, %d FAIL ===' % (0, len(fails)))
if fails:
    print('FAILS:', fails)
    sys.exit(1)
print('ALL GREEN')
