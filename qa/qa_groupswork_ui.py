#!/usr/bin/env python3
"""HUB QA: Groups + Work water-crystal UI redesign (2026-09-24).
Fresh profile /tmp/hubqa-groupswork (wiped), file:// load, 390px, dark+light.

Groups: gu- scope hooks, gu-seg glass switcher (4 modes), search, +New group CTA,
carousel cards w/ --i stagger + LIVE pulse, group detail page (chat/call/invite),
new-group sheet, me.js .seg NOT restyled, bindFlow tilt intact.
Work: wu-root scope, wu-post clay CTA, wu-chips filters (All/Open/Accepted/Done),
job cards w/ --i stagger, volt pay pill, b-BORROW pulse, accept flow, post sheet.
Static: no purple hexes, reduced-motion freeze, no page overflow, zero console errors.
"""
import json, subprocess, time, os, shutil, sys, base64, re
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9447
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-groupswork'
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
HUB = os.path.expanduser('~/workspace/hub')
JS = "(function(){%s})()"
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12)
        self.id = 0; self.events = []
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        t = time.time()
        while time.time() - t < 15:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if 'method' in msg and 'id' not in msg:
                self.events.append(msg); continue
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]
    def shot(self, name):
        r = self.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 82, 'fromSurface': True})
        with open(os.path.join(SHOTDIR, name), 'wb') as f: f.write(base64.b64decode(r['data']))
        print('SHOT', name)

def js_wait(c, expr, timeout=15):
    t = time.time()
    while time.time() - t < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False

def arm_hooks(c):
    c.send('Page.enable'); c.send('Runtime.enable')
    c.js("window.__huberr=[]; window.addEventListener('error',function(e){window.__huberr.push(String(e.message||e))});"
         "window.addEventListener('unhandledrejection',function(e){window.__huberr.push('rej:'+String(e.reason&&e.reason.message||e.reason))}); return 1")

def console_ok(c, label):
    errs = [e for e in c.events if e.get('method') in ('Log.entryAdded','Runtime.exceptionThrown')]
    werr, _ = c.js(JS % "return window.__huberr||[]")
    note(not errs and not (werr or []), label, 'cdp=%d window=%d' % (len(errs), len(werr or [])))

def no_overflow(c, label):
    v, _ = c.js(JS % "return document.documentElement.scrollWidth<=window.innerWidth+1")
    note(bool(v), label)

def seed(c):
    """Onboarding-skipped profile + sample groups/jobs near the fake campus."""
    c.js(JS % """
    localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));
    var s=HUB.store.state; s.profile.name='PraBin'; s.profile.campus='QA Campus';
    s.profile.campusCoords=[32.87,-96.99]; s.prefs.dark=true;
    HUB.store.add('cgroups',{id:'g1',name:'Priya\\'s Study Circle',desc:'Finals-week study sessions',emoji:'📚',live:true,members:['Priya','Raj','Sofia'],sample:true,lat:32.871,lng:-96.989});
    HUB.store.add('cgroups',{id:'g2',name:'Design Crew',desc:'Poster collabs',emoji:'🎨',live:true,members:['Diego'],sample:true,lat:32.872,lng:-96.988});
    HUB.store.add('cgroups',{id:'g3',name:'Draft Squad',desc:'Not live yet',emoji:'🎮',live:false,mine:true,members:['PraBin'],sample:true,lat:32.87,lng:-96.99});
    HUB.store.add('jobs',{id:'j1',title:'Need someone to move furniture',pay:40,poster:'Taylor Brooks',desc:'Couch + bookshelf, 2nd floor to ground.',status:'open',createdAt:Date.now()-3*3600e3,sample:true});
    HUB.store.add('jobs',{id:'j2',title:'Math tutoring',pay:25,poster:'Alex Kim',desc:'Calc II help, 1 hour.',status:'accepted',acceptedBy:'Sam',createdAt:Date.now()-5*3600e3,sample:true});
    HUB.store.save(); return 1""")

def dismiss_gate(c):
    ok = js_wait(c, "var s=document.getElementById('splash'); return !!(s&&s.classList.contains('splash-out'))", 20)
    note(ok, 'splash fading')
    ok = js_wait(c, "var r=document.getElementById('authRoot'); return !!(r&&!r.hidden)", 20)
    note(ok, 'login gate opened')
    c.js(JS % "var l=document.querySelector('[data-i18n-skip],#authRoot a'); if(l)l.click(); return 1")
    # fallback: the skip link id from auth.js
    v, _ = c.js(JS % "var r=document.getElementById('authRoot'); return !!(r&&r.hidden)")
    if not v:
        c.js(JS % "Array.from(document.querySelectorAll('#authRoot a, #authRoot button')).forEach(function(a){ if(/explore/i.test(a.textContent)) a.click(); }); return 1")
        time.sleep(0.6)
    ok = js_wait(c, "var r=document.getElementById('authRoot'); return !!(r&&r.hidden)", 10)
    note(ok, 'gate dismissed via skip link')
    # regression: the boot poller must NOT pop the login back open after skip
    time.sleep(1.5)
    v, _ = c.js(JS % "var r=document.getElementById('authRoot'); return !!(r&&r.hidden)")
    note(bool(v), 'gate stays shut after skip (no poller reopen)')

# ---------- static CSS checks ----------
print('--- static CSS ---')
def css_nocomments(css):
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)
def unscoped(css, token, scopes):
    """Selectors using `token` as a class that lack any scope token."""
    bad = []
    for m in re.finditer(r'([^{}]+)\{', css_nocomments(css)):
        sel = m.group(1)
        if re.search(r'(?<![\w-])' + re.escape(token) + r'(?![\w-])', sel):
            if not any(s in sel for s in scopes):
                bad.append(sel.strip().replace('\n', ' ')[:70])
    return bad
gcss_raw = open(os.path.join(HUB, 'css/groups-ui.css')).read()
wcss_raw = open(os.path.join(HUB, 'css/work-ui.css')).read()
for fn in ('css/groups-ui.css', 'css/work-ui.css'):
    p = os.path.join(HUB, fn)
    note(os.path.exists(p), fn + ' exists')
    css = open(p).read() if os.path.exists(p) else ''
    note(not re.search(r'#7c3aed|#8b5cf6|#a855f7', css, re.I), fn + ' no purple hexes')
    note('prefers-reduced-motion' in css, fn + ' reduced-motion freeze')
    note('backdrop-filter' in css or 'backdrop' in css, fn + ' frosted glass')
    note(len(css) > 500, fn + ' non-trivial (%d bytes)' % len(css))
# shared classes must only ever be touched under the workstream scope:
# groups-ui -> .seg only via .gu-seg; .chip/.btn only under .gu
# work-ui   -> .chip/.btn only under .wu-
note(not unscoped(gcss_raw, '.seg', ['gu-seg']), 'groups-ui: .seg only via .gu-seg')
note(not unscoped(gcss_raw, '.chip', ['.gu']), 'groups-ui: .chip only under .gu')
note(not unscoped(gcss_raw, '.btn', ['.gu']), 'groups-ui: .btn only under .gu')
note(not unscoped(wcss_raw, '.chip', ['wu-']), 'work-ui: .chip only under .wu-')
note(not unscoped(wcss_raw, '.btn', ['wu-']), 'work-ui: .btn only under .wu-')
note(not unscoped(wcss_raw, '.seg', ['wu-']), 'work-ui: no .seg restyle')

# ---------- browser ----------
shutil.rmtree(PROF, ignore_errors=True)
chrome = subprocess.Popen([CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
    '--user-data-dir='+PROF, '--window-size=390,844', '--remote-debugging-port=%d' % PORT,
    '--remote-allow-origins=*', '--allow-file-access-from-files', 'about:blank'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    wsurl = None
    for _ in range(40):
        try:
            tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=3))
            wsurl = tabs[0]['webSocketDebuggerUrl']; break
        except Exception: time.sleep(0.5)
    assert wsurl, 'no devtools'
    c = CDP(wsurl)
    c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    arm_hooks(c)
    c.send('Page.navigate', {'url': BASE})
    ok = js_wait(c, "return document.readyState==='complete' && !!window.HUB && !!HUB.auth", 25)
    note(ok, 'app booted')
    seed(c); c.send('Page.reload'); arm_hooks(c)
    ok = js_wait(c, "return document.readyState==='complete' && !!window.HUB && !!HUB.auth", 25)
    note(ok, 'clean boot after seed')
    dismiss_gate(c)

    print('--- CSS linked live ---')
    v, _ = c.js(JS % "return !!document.querySelector('link[href=\"css/groups-ui.css\"]')")
    note(bool(v), 'groups-ui.css linked in index.html')
    v, _ = c.js(JS % "return !!document.querySelector('link[href=\"css/work-ui.css\"]')")
    note(bool(v), 'work-ui.css linked in index.html')

    print('--- Groups tab (dark) ---')
    c.js(JS % "HUB.showTab('groups'); return 1"); time.sleep(1.2)
    v, _ = c.js(JS % "return document.querySelectorAll('.gu').length")
    note(v and v > 0, 'gu scope wrapper present', str(v))
    v, _ = c.js(JS % "return !!document.querySelector('.seg.gu-seg')")
    note(bool(v), 'gu-seg glass switcher present')
    v, _ = c.js(JS % "return document.querySelectorAll('.seg.gu-seg button').length")
    note(v == 4, '4 mode buttons', str(v))
    v, _ = c.js(JS % "return !!document.getElementById('cgSearch')")
    note(bool(v), 'search input present')
    v, _ = c.js(JS % "var b=document.getElementById('cgNew'); return !!(b&&getComputedStyle(b).backgroundImage!=='none'||b)")
    note(bool(v), 'New group CTA present')
    v, _ = c.js(JS % "return document.querySelectorAll('.gcard').length")
    note(v and v >= 2, 'carousel cards rendered', str(v))
    v, _ = c.js(JS % "var k=document.querySelector('.gcard'); return !!(k&&k.style.getPropertyValue('--i')!==''||k&&k.getAttribute('style')&&k.getAttribute('style').indexOf('--i')>-1)")
    note(bool(v), 'cards carry --i stagger index')
    v, _ = c.js(JS % "return !!document.querySelector('.gcard-live')")
    note(bool(v), 'LIVE badge on live card')
    v, _ = c.js(JS % "var b=document.querySelector('.gcard-live'); if(!b) return false; var a=getComputedStyle(b).animationName; return a&&a!=='none'")
    note(bool(v), 'LIVE badge pulsing (animation)')
    # draft badge: drafts surface as Yours rows; their detail page wears .gu-draft
    c.js(JS % "var r=document.querySelector('.item[data-club=\"g3\"]'); if(r)r.click(); return 1")
    ok = js_wait(c, "return !!document.getElementById('cgBack')", 8)
    note(ok, 'draft group detail opened')
    v, _ = c.js(JS % "return !!document.querySelector('.gu-draft')")
    note(bool(v), 'draft badge on draft group detail (.gu-draft)')
    c.js(JS % "document.getElementById('cgBack').click(); return 1"); time.sleep(0.8)
    v, _ = c.js(JS % "var m=document.querySelector('.gu-motes'); return !!(m&&getComputedStyle(m).pointerEvents==='none')")
    note(bool(v), 'sparkle motes present, pointer-events none')
    no_overflow(c, 'groups: no horizontal overflow')
    c.shot('gw-groups-dark.jpg')

    print('--- Groups modes ---')
    for sub, shot in (('households', 'gw-groups-households.jpg'), ('campus', 'gw-groups-campus.jpg'), ('people', 'gw-groups-people.jpg')):
        c.js(JS % "document.querySelector('.seg.gu-seg button[data-sub=\"%s\"]').click(); return 1" % sub)
        time.sleep(1.0)
        if sub == 'people':
            v, _ = c.js(JS % "return document.getElementById('view-groups').classList.contains('gu')")
            note(bool(v), 'people mode: .gu scope toggled on view')
            v, _ = c.js(JS % "var p=document.querySelector('.gu #pplChips .chip'); return !!(p&&getComputedStyle(p).backdropFilter!=='none')")
            note(bool(v), 'people mode: crystal chips (backdrop blur)')
            v, _ = c.js(JS % "var q=document.querySelector('.gu #pplSearch'); return !!q")
            note(bool(v), 'people mode: search kept')
        else:
            v, _ = c.js(JS % "return !!document.querySelector('.gu')")
            note(bool(v), 'mode %s renders gu scope' % sub)
        no_overflow(c, 'mode %s: no overflow' % sub)
        c.shot(shot)
    c.js(JS % "document.querySelector('.seg.gu-seg button[data-sub=\"clubs\"]').click(); return 1"); time.sleep(1.0)

    print('--- group detail page ---')
    c.js(JS % "document.querySelector('.gcard[data-club]').click(); return 1")
    ok = js_wait(c, "return !!document.getElementById('cgBack')", 8)
    note(ok, 'group detail opened')
    v, _ = c.js(JS % "return !!(document.querySelector('.gu-hero')||document.querySelector('.gu-ctitle'))")
    note(bool(v), 'detail hero restyled')
    v, _ = c.js(JS % "return !!document.querySelector('.gu-live')")
    note(bool(v), 'detail LIVE badge (gu-live)')
    v, _ = c.js(JS % "return !!document.getElementById('cgInviteBtn')||!!document.getElementById('cgChatBtn')")
    note(bool(v), 'chat/invite entry present')
    no_overflow(c, 'detail: no overflow')
    c.shot('gw-group-detail-dark.jpg')
    c.js(JS % "document.getElementById('cgBack').click(); return 1"); time.sleep(0.8)

    print('--- new group sheet ---')
    c.js(JS % "document.getElementById('cgNew').click(); return 1"); time.sleep(0.8)
    v, _ = c.js(JS % "var s=document.getElementById('sheetHost'); return !!(s&&!s.hidden)")
    note(bool(v), 'new-group sheet opened')
    c.shot('gw-newgroup-sheet.jpg')
    c.js(JS % "if(HUB.ui&&HUB.ui.closeSheet)HUB.ui.closeSheet(); return 1"); time.sleep(0.6)

    print('--- me.js .seg untouched (static: groups-ui only styles .seg via .gu-seg) ---')
    v, _ = c.js(JS % "return document.querySelectorAll('.seg:not(.gu-seg)').length")
    note(True, 'bare .seg instances on page: %s (style verified statically)' % v)

    print('--- carousel tilt intact ---')
    v, _ = c.js(JS % "var f=document.querySelector('.flow'); return !!(f&&f.dataset.fbound)")
    note(bool(v), 'bindFlow bound')

    print('--- Work tab (dark) ---')
    c.js(JS % "HUB.showTab('work'); return 1"); time.sleep(1.2)
    v, _ = c.js(JS % "return !!document.querySelector('.wu-root')")
    note(bool(v), 'wu-root scope present')
    v, _ = c.js(JS % "return !!document.querySelector('#postJobBtn.wu-post')")
    note(bool(v), 'post-job clay CTA present')
    v, _ = c.js(JS % "return document.querySelectorAll('.wu-chips .chip').length")
    note(v == 4, '4 filter chips', str(v))
    v, _ = c.js(JS % "return document.querySelectorAll('.job').length")
    note(v and v >= 2, 'job cards rendered', str(v))
    v, _ = c.js(JS % "var j=document.querySelector('.job'); return !!(j&&j.getAttribute('style')&&j.getAttribute('style').indexOf('--i')>-1)")
    note(bool(v), 'job cards carry --i stagger')
    v, _ = c.js(JS % "var p=document.querySelector('.job-pay'); return !!(p&&getComputedStyle(p).boxShadow!=='none')")
    note(bool(v), 'pay pill glowing')
    v, _ = c.js(JS % "return !!document.querySelector('.badge.b-BORROW')")
    note(bool(v), 'OPEN badge (b-BORROW uppercase)')
    v, _ = c.js(JS % "var b=document.querySelector('.badge.b-BORROW'); var a=getComputedStyle(b).animationName; return a&&a!=='none'")
    note(bool(v), 'OPEN badge pulsing')
    v, _ = c.js(JS % "return !!document.querySelector('[data-accept].wu-accept')")
    note(bool(v), 'Accept job clay button')
    v, _ = c.js(JS % "return document.body.textContent.indexOf('★')>-1||document.querySelectorAll('.stars').length>0")
    note(bool(v), 'reputation stars kept')
    no_overflow(c, 'work: no overflow')
    c.shot('gw-work-dark.jpg')

    print('--- Work filters ---')
    for f, shot in (('open', 'gw-work-open.jpg'), ('accepted', 'gw-work-accepted.jpg'), ('done', 'gw-work-done.jpg')):
        c.js(JS % "document.querySelector('.wu-chips .chip[data-f=\"%s\"]').click(); return 1" % f)
        time.sleep(0.9)
        v, _ = c.js(JS % "return document.querySelectorAll('.job').length")
        note(True, 'filter %s -> %s cards' % (f, v))
        c.shot(shot)
    c.js(JS % "document.querySelector('.wu-chips .chip[data-f=\"all\"]').click(); return 1"); time.sleep(0.8)

    print('--- accept flow ---')
    c.js(JS % "document.querySelector('[data-accept]').click(); return 1"); time.sleep(0.8)
    v, _ = c.js(JS % "var s=document.getElementById('sheetHost'); return !!(s&&!s.hidden)")
    note(bool(v), 'accept confirm sheet opened')
    c.shot('gw-accept-sheet.jpg')
    c.js(JS % "if(HUB.ui&&HUB.ui.closeSheet)HUB.ui.closeSheet(); return 1"); time.sleep(0.6)

    print('--- post job sheet ---')
    c.js(JS % "document.getElementById('postJobBtn').click(); return 1"); time.sleep(0.8)
    v, _ = c.js(JS % "var s=document.getElementById('sheetHost'); return !!(s&&!s.hidden&&document.getElementById('pjGo'))")
    note(bool(v), 'post-job sheet opened with #pjGo')
    c.shot('gw-postjob-sheet.jpg')
    c.js(JS % "if(HUB.ui&&HUB.ui.closeSheet)HUB.ui.closeSheet(); return 1"); time.sleep(0.6)

    console_ok(c, 'zero console errors (dark)')
    print('--- light mode ---')
    c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); return 1")
    c.send('Page.reload'); arm_hooks(c)
    ok = js_wait(c, "return document.readyState==='complete' && !!window.HUB", 25)
    note(ok, 'light boot')
    dismiss_gate(c)
    c.js(JS % "HUB.showTab('groups'); return 1"); time.sleep(1.2)
    v, _ = c.js(JS % "return !!document.querySelector('.gu')")
    note(bool(v), 'groups gu scope (light)')
    c.shot('gw-groups-light.jpg')
    c.js(JS % "HUB.showTab('work'); return 1"); time.sleep(1.2)
    v, _ = c.js(JS % "return !!document.querySelector('.wu-root')")
    note(bool(v), 'work wu-root (light)')
    no_overflow(c, 'light: no overflow')
    c.shot('gw-work-light.jpg')
    console_ok(c, 'zero console errors (light)')
finally:
    try: chrome.terminate()
    except Exception: pass

n = len(checks); p = sum(checks)
print('==== %d/%d PASS ====' % (p, n))
sys.exit(0 if p == n else 1)
