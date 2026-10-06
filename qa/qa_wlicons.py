#!/usr/bin/env python3
"""QA: wl-* clay icons in Period & Wellness — every icon loads (naturalWidth>0),
zero .ico-fb fallbacks, screenshots at 390+320px, dark+light, zero console errors."""
import subprocess, time, json, os, sys, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import websocket  # noqa: F401
import urllib.request

PORT = 9459
fails = []
def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok: fails.append(n)

def j(c, expr, await_=False):
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip()
        if e.endswith(';'): e = e[:-1]
    # crude top-level-semicolon detection (same as qa_wellness.py)
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q: instr = False
        elif ch in '"\'`': instr, q = True, ch
        elif ch in '([{': depth += 1
        elif ch in ')]}': depth -= 1
        elif ch == ';' and depth == 0: top_semi = True; break
    if not top_semi: e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'awaitPromise': await_, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

ERR_SRC = ("window.__huberr=[];"
           "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

proc = None
def launch(width=390, height=844, prof='/tmp/hubqa-wlicons', dark=False):
    global proc
    subprocess.run(['rm', '-rf', prof])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + prof, '--hide-scrollbars', '--window-size=%d,%d' % (width, height), 'about:blank'])
    time.sleep(2.5)
    tgt = None
    for _ in range(30):
        try:
            tgts = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read())
            tgt = [t for t in tgts if t.get('type') == 'page'][0]
            break
        except Exception:
            time.sleep(0.4)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': width, 'height': height, 'deviceScaleFactor': 2, 'mobile': True})
    prefs = {'lang': 'en', 'country': 'US'}
    if dark: prefs['dark'] = True
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify(%s));}catch(e){}" % json.dumps(prefs) + ERR_SRC})
    c.send('Page.navigate', {'url': 'file:///home/hatch/workspace/hub/index.html'})
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.wellness&&HUB.icons&&HUB.views&&HUB.views.daily);") is True:
            break
        time.sleep(0.5)
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    j(c, "return (function(){window.__gateSkip=true; try{HUB.auth.close()}catch(e){} return 1;})();")
    time.sleep(0.6)
    check('no saferecov overlay', j(c, "return !document.getElementById('saferecov');") is True)
    return c

def shot(c, tag):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, 'wlicons-%s.png' % tag), 'wb').write(base64.b64decode(r['data']))

def icons_ok(c, tag):
    # force lazy images to load: sweep the dashboard scroll top->bottom
    j(c, """return (function(){var p=document.getElementById('wlPage'); if(!p)return 0;
      return p.scrollHeight;})();""", await_=False)
    for frac in (0.25, 0.5, 0.75, 1.0):
        j(c, "return (function(){var p=document.getElementById('wlPage'); if(p)p.scrollTop=p.scrollHeight*%s; return 1;})();" % frac)
        time.sleep(0.5)
    j(c, "return (function(){var p=document.getElementById('wlPage'); if(p)p.scrollTop=0; return 1;})();")
    time.sleep(1.0)
    res = j(c, """return (function(){
      var imgs=[].slice.call(document.querySelectorAll('img[data-icon^="wl-"]'));
      var bad=imgs.filter(function(i){return !(i.complete&&i.naturalWidth>0);}).map(function(i){return i.getAttribute('data-icon');});
      var fbs=[].slice.call(document.querySelectorAll('.ico-fb[data-icon^="wl-"]')).map(function(s){return s.getAttribute('data-icon');});
      var names=imgs.map(function(i){return i.getAttribute('data-icon');});
      return {n:imgs.length, bad:bad, fbs:fbs, names:names};
    })();""")
    check(tag + ' all wl icons loaded', res and not res['bad'] and res['n'] > 0,
          'loaded=%s bad=%s' % ((res or {}).get('n'), (res or {}).get('bad')))
    check(tag + ' zero wl emoji fallbacks', res and not res['fbs'], (res or {}).get('fbs'))
    return res

def errs0(c, tag):
    e = j(c, "return window.__huberr.slice(0,8);")
    check(tag + ' zero console errors', not e, e)

def setup_female(c):
    j(c, """return (function(){
      HUB.store.state.profile.gender='female'; HUB.store.save();
      HUB.showTab('daily'); return 1;})();""")
    time.sleep(0.9)
    # Get Started if present
    j(c, """return (function(){var b=document.getElementById('wlStart'); if(b){b.click();} return 1;})();""")
    time.sleep(0.9)

EXPECTED = ['wl-heart','wl-droplet','wl-calendar','wl-activity','wl-smile','wl-moon','wl-leaf',
            'wl-sprout','wl-flower','wl-bowl','wl-book','wl-clock','wl-bell','wl-shield','wl-lock',
            'wl-note','wl-sparkle','wl-mood-great','wl-mood-good','wl-mood-okay','wl-mood-low','wl-mood-hard']

# ============ 390px light ============
c = launch(390, 844)
setup_female(c)
shot(c, 'card-390-light')
# open dashboard
j(c, "return (function(){var b=document.getElementById('wlOpenDash'); if(b)b.click(); return 1;})();")
time.sleep(1.4)
check('dashboard open', j(c, "return !!document.getElementById('wlPage');") is True)
res = icons_ok(c, 'dash-390-light')
if res:
    missing = [e for e in EXPECTED if e not in (res.get('names') or [])]
    check('dash-390-light all 22 icon names present', not missing, missing)
shot(c, 'dash-390-light')
# scroll to mood row + trackers for screenshots
j(c, "return (function(){var p=document.getElementById('wlPage'); var m=document.getElementById('wlMoods'); if(m)p.scrollTop=m.offsetTop-140; return 1;})();")
time.sleep(0.7)
shot(c, 'moods-390-light')
j(c, "return (function(){var p=document.getElementById('wlPage'); var t=document.getElementById('wlTrackers'); if(t)p.scrollTop=t.offsetTop-140; return 1;})();")
time.sleep(0.7)
shot(c, 'trackers-390-light')
errs0(c, 'dash-390-light')
proc.terminate(); time.sleep(1)

# ============ 320px light ============
c = launch(320, 568, '/tmp/hubqa-wlicons320')
setup_female(c)
j(c, "return (function(){var b=document.getElementById('wlOpenDash'); if(b)b.click(); return 1;})();")
time.sleep(1.4)
res = icons_ok(c, 'dash-320-light')
shot(c, 'dash-320-light')
ov = j(c, "return document.documentElement.scrollWidth<=320;")
check('dash-320-light no page overflow', ov is True, 'scrollWidth>320')
errs0(c, 'dash-320-light')
proc.terminate(); time.sleep(1)

# ============ 390px dark ============
c = launch(390, 844, '/tmp/hubqa-wliconsdark', dark=True)
setup_female(c)
j(c, "return (function(){var b=document.getElementById('wlOpenDash'); if(b)b.click(); return 1;})();")
time.sleep(1.4)
res = icons_ok(c, 'dash-390-dark')
shot(c, 'dash-390-dark')
errs0(c, 'dash-390-dark')
proc.terminate()

print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
