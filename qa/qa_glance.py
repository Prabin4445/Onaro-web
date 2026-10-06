"""QA: 'Today at a glance' carousel rework (2026-09-30).
- free momentum swipe, no snap (tap vs drag still disambiguated)
- tiles smaller than before (158px -> 140px)
- per-tile signature icon animations running
- 390+320px, dark+light, en+de, zero console errors
"""
import subprocess, time, json, base64, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import urllib.request

PORT = 9461
fails = []
def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok: fails.append(n)

EXPECTED_ANIM = {'owed':'glJiggle','unread':'glPop','jobs':'glRock','bill':'glSway',
                 'events':'glHop','docs':'glFlutter','spend':'glFly'}

def j(c, expr):
    # wrap in IIFE: callers write `return ...;` / multi-statement bodies
    r = c.send('Runtime.evaluate', {'expression': '(()=>{' + expr + '})()', 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    p = os.path.join(QA, name + '.png')
    open(p, 'wb').write(base64.b64decode(r['data']))

def touch(c, ttype, points):
    c.send('Input.dispatchTouchEvent', {'type': ttype, 'touchPoints': points}, wait=True)

def boot(width, theme, lang):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--allow-file-access-from-files',
        f'--user-data-dir=/tmp/hubqa-glance2-{width}-{theme}-{lang}', '--hide-scrollbars',
        'file:///home/hatch/workspace/hub/index.html'])
    time.sleep(2.5)
    tgt = None
    for _ in range(30):
        try:
            tgts = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json').read())
            tgt = [t for t in tgts if t.get('type') == 'page'][0]; break
        except Exception: time.sleep(0.4)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': width, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    j(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.glance&&HUB.i18n&&HUB.ui);") is True: break
        time.sleep(0.5)
    j(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'" + lang + "',country:'US'}));"
         "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') +
         ";HUB.store.save();HUB.applyTheme();")
    j(c, """window.__gateSkip=true; /* same as tapping "Explore without signing in": boot poller never re-gates */
      var p=HUB.store.state.profile; p.name='QA Glance'; p.campus='The University of Texas at Dallas';
      p.verified=true; HUB.store.save();
      try{HUB.auth.close()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1;""")
    for _ in range(20):
        if j(c, "return !document.getElementById('splash');") is True: break
        time.sleep(0.5)
    j(c, "HUB.showTab('home'); try{HUB.glance._hold();}catch(e){}"); time.sleep(1.5)
    return proc, c

def run_case(width, theme, lang, tag):
    proc, c = boot(width, theme, lang)
    try:
        ok = j(c, "return !!document.getElementById('glanceFlow');")
        check(f'{tag} carousel present', ok is True)
        snap = j(c, "return getComputedStyle(document.getElementById('glanceFlow')).scrollSnapType;")
        check(f'{tag} no snap (free stop)', snap in ('none', ''), snap)
        tw = j(c, "return document.querySelector('.gltile').offsetWidth;")
        check(f'{tag} tiles smaller than 158px', isinstance(tw, (int, float)) and tw < 150, tw)
        n = j(c, "return document.querySelectorAll('.gltile').length;")
        check(f'{tag} 7 tiles render', n == 7, n)
        anims = j(c, """return Array.from(document.querySelectorAll('.gltile')).map(function(tl){
          var ico=tl.querySelector('.gltile-ico'); var an=ico?ico.getAnimations():[];
          return {k:tl.dataset.gl, n:an.map(function(a){return a.animationName+':'+a.playState;})};});""")
        allok = True
        for a in (anims or []):
            exp = EXPECTED_ANIM.get(a['k'])
            good = any(x.startswith(exp + ':running') for x in a['n']) if exp else False
            if not good: allok = False; print('   anim missing:', a)
        check(f'{tag} every tile icon animates', allok and len(anims or []) == 7)
        j(c, "document.getElementById('glanceWrap').scrollIntoView({block:'center'});"); time.sleep(1.0)
        shot(c, f'glance-{tag}')
        # tap first tile -> detail opens (owed -> bottom sheet).
        # Tap FIRST on a pristine strip (probe-verified); swipe test comes after.
        j(c, "HUB.glance._hold(); document.getElementById('glanceFlow').scrollLeft=0;"); time.sleep(0.4)
        r1 = j(c, """var t=document.querySelector('[data-gl="owed"]'); var r=t.getBoundingClientRect();
          return {x:r.left+r.width/2, y:r.top+r.height/2};""")
        touch(c, 'touchStart', [{'x': r1['x'], 'y': r1['y'], 'id': 2}]); time.sleep(0.1)
        touch(c, 'touchEnd', []); time.sleep(1.0)
        sheet = j(c, "return !document.getElementById('sheetHost').hidden;")
        check(f'{tag} tap opens tile detail', sheet is True)
        j(c, "HUB.ui.closeSheet();"); time.sleep(0.5)
        closed = j(c, "return document.getElementById('sheetHost').hidden;")
        check(f'{tag} detail closes cleanly', closed is True)
        # synthetic swipe: drag left => scrollLeft grows, settles, no snap-back
        pos = j(c, """var f=document.getElementById('glanceFlow'); var r=f.getBoundingClientRect();
          return {x:r.left+r.width/2, y:r.top+r.height/2};""")
        x0, y0 = pos['x'], pos['y']
        touch(c, 'touchStart', [{'x': x0, 'y': y0, 'id': 1}])
        for i in range(1, 9):
            touch(c, 'touchMove', [{'x': x0 - i * 22, 'y': y0, 'id': 1}]); time.sleep(0.03)
        shot(c, f'glance-{tag}-midswipe')
        touch(c, 'touchEnd', [])
        time.sleep(0.4)
        sl1 = j(c, "return document.getElementById('glanceFlow').scrollLeft;")
        time.sleep(1.6)
        sl2 = j(c, "return document.getElementById('glanceFlow').scrollLeft;")
        check(f'{tag} swipe moves strip', sl1 > 40, f'sl={sl1}')
        check(f'{tag} settles, no snap-back', sl2 > 30, f'sl2={sl2}')
        dots = j(c, """var d=document.getElementById('glanceDots');
          return d?Array.from(d.children).filter(function(s){return s.classList.contains('on')}).length:0;""")
        check(f'{tag} dots track position', dots == 1, dots)
        ov = j(c, "return {sw:document.documentElement.scrollWidth, iw:window.innerWidth};")
        check(f'{tag} no page overflow', ov['sw'] <= ov['iw'] + 1, ov)
        errs = j(c, "return window.__huberr.slice(0,6);")
        check(f'{tag} zero console errors', not errs, errs)
    finally:
        proc.terminate(); proc.wait()

run_case(390, 'dark', 'en', '390-dark-en')
run_case(390, 'light', 'en', '390-light-en')
run_case(320, 'dark', 'en', '320-dark-en')
run_case(390, 'light', 'de', '390-light-de')

print('FAILURES:', fails if fails else 'none')
sys.exit(1 if fails else 0)
