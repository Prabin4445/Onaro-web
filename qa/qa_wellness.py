#!/usr/bin/env python3
"""QA: Period & Wellness Daily feature (2026-09-30, incl. wave 2 food + knowledge hub).
Gender gates (female/other full, male restricted, missing -> complete profile),
card states, dashboard flows (log period, symptoms, mood, hydration, trackers,
notes, history, reminders, food plans, knowledge hub, privacy: hide/delete/export),
heavy-period nudge, storage isolation, 390+320px, dark+light, en+ne, zero console
errors. Screenshots visually verified."""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import websocket  # noqa: F401

PORT = 9451
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok:
        fails.append(n)

def j(c, expr, await_=False):
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip()
        if e.endswith(';'):
            e = e[:-1]
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q:
                instr = False
        elif ch in '"\'`':
            instr, q = True, ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ';' and depth == 0:
            top_semi = True
            break
    if not top_semi:
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'awaitPromise': await_, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

ERR_SRC = ("window.__huberr=[];"
           "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

def boot(c):
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.wellness&&HUB.i18n&&HUB.views&&HUB.views.daily);") is True:
            break
        time.sleep(0.5)
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    j(c, "window.__gateSkip=true; try{HUB.auth.close()}catch(e){} return 1;")
    time.sleep(0.6)
    j(c, "return !document.getElementById('saferecov');")

def shot(c, tag):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, 'wellness-%s.png' % tag), 'wb').write(base64.b64decode(r['data']))

def errs0(c, tag):
    e = j(c, "return window.__huberr.slice(0,8);")
    check(tag + ' zero console errors', not e, e)

def set_gender(c, g):
    j(c, "HUB.store.state.profile.gender='%s'; HUB.store.save(); HUB.showTab('daily'); return 1;" % g)
    time.sleep(0.7)

def card_text(c):
    return j(c, "return (document.getElementById('wlCard')||{textContent:''}).textContent;")

# ---------- static: no sensitive logging ----------
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'js', 'wellness.js'), encoding='utf-8').read()
check('no console.* in wellness.js', 'console.' not in src, [l for l in src.split('\n') if 'console.' in l][:2])

proc = None
def launch(width=390, height=844, prof='/tmp/hubqa-wellness', lang='en'):
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
    c.send('Runtime.enable')
    c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': width, 'height': height, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'%s',country:'US'}));}catch(e){}" % lang + ERR_SRC})
    c.send('Page.navigate', {'url': BASE})
    boot(c)
    return c

def dash_open(c):
    return j(c, "return !!document.getElementById('wlRoot');") is True

# ================= 390px light en =================
c = launch()
check('no saferecov overlay', j(c, "return !document.getElementById('saferecov');") is True)

# ---- missing gender ----
set_gender(c, '')
check('missing gender: complete-profile card', j(c, "return !!document.getElementById('wlUpdProf');") is True
      and 'Complete your profile' in (card_text(c) or ''))
check('missing gender: no dashboard access', j(c, "HUB.wellness.openDashboard(); return !!document.getElementById('wlRoot');") is False)
shot(c, 'card-nogender')

# ---- male restricted ----
set_gender(c, 'male')
tx = card_text(c) or ''
check('male: restricted card', 'Private wellness feature' in tx and 'available based on your profile settings' in tx, tx[:70])
check('male: no cycle data shown', j(c, """return (function(){var el=document.getElementById('wlCard');
  return !el.querySelector('#wlOpenDash')&&!el.querySelector('.wl-next')&&!/Estimated/.test(el.textContent);})();""") is True)
check('male: no dashboard access', j(c, "HUB.wellness.openDashboard(); return !!document.getElementById('wlRoot');") is False)
shot(c, 'card-restricted')
errs0(c, 'gates')

# ---- female setup ----
set_gender(c, 'female')
check('female: setup card with Get Started', j(c, "return !!document.getElementById('wlStart');") is True)
check('female: card order (after calc entry, before gym)', j(c, """return (function(){
  var h=document.getElementById('view-daily').innerHTML;
  var a=h.indexOf('wlCard'),b=h.indexOf('homeCalcEntry'),g=h.indexOf('Gym Fuel');
  return b>0&&a>b&&(g<0||a<g);})();""") is True)
shot(c, 'card-setup')

# ---- enable + dashboard ----
j(c, "document.getElementById('wlStart').click(); return 1;")
time.sleep(0.8)
check('Get Started opens dashboard', dash_open(c))
check('dashboard header', j(c, "return document.getElementById('wlPage').textContent.indexOf('Your Wellness')>=0;") is True)
check('medical disclaimer present', j(c, "return document.getElementById('wlPage').textContent.indexOf('not medical advice')>=0;") is True)
shot(c, 'dash-hero')

# ---- log period via sheet ----
check('dashboard sections use SVG icons', j(c, "return document.querySelectorAll('#wlPage .wl-ic').length>10;") is True)
check('hero ring rendered', j(c, "return !!document.querySelector('.wl-hero-ring svg.ring');") is True)
j(c, "document.getElementById('wlLogBtn').click(); return 1;")
time.sleep(0.6)
j(c, """document.getElementById('wlPStart').value='2026-09-06';
  document.getElementById('wlPEnd').value='2026-09-10';
  document.getElementById('wlPLen').value='28';
  document.getElementById('wlPSave').click(); return 1;""")
time.sleep(0.8)
st = j(c, """return {est:!!document.querySelector('.wl-next .n'),
  cal:document.querySelectorAll('.wl-cal-day.period').length,
  txt:document.getElementById('wlPage').textContent};""")
check('estimate shown after log', st['est'] is True)
check('calendar marks period days', st['cal'] >= 5, st['cal'])
check('estimate wording is soft', 'Estimated' in st['txt'] and 'Based on your recent cycle entries' in st['txt'])

# ---- symptoms / mood ----
j(c, "document.querySelector('[data-sym=cramps]').click(); return 1;")
shot(c, 'dash-chip-pop')
check('chip tap pops (mid-animation)', j(c, "return !!document.querySelector('#wlSymChips .wl-chip.wl-pop');") is True)
time.sleep(0.4)
j(c, "document.querySelector('[data-sym=head]').click(); return 1;")
time.sleep(0.4)
check('2 symptoms selected', j(c, "return document.querySelectorAll('#wlSymChips .wl-chip.on').length;") == 2)
j(c, "document.querySelector('[data-mood=good]').click(); return 1;")
time.sleep(0.4)
check('mood selected', j(c, "return document.querySelectorAll('#wlMoods .wl-mood.on').length;") == 1)
j(c, "var m=document.getElementById('wlMoodNote'); m.value='Feeling tired after class.'; m.dispatchEvent(new Event('change')); return 1;")
time.sleep(0.3)

# ---- hydration ----
for i in range(3):
    j(c, "document.querySelectorAll('#wlGlasses .wl-glass')[%d].click(); return 1;" % i)
    time.sleep(0.35)
check('hydration 3/8', j(c, "return document.querySelector('#wlPage').textContent.indexOf('3 / 8')>=0;") is True)
check('hydration glasses fill (no full re-render)', j(c, "return document.querySelectorAll('#wlGlasses .wl-glass.full').length;") == 3)
shot(c, 'dash-hyd-fill')

# ---- trackers ----
j(c, "document.querySelector('[data-tr=water]').click(); return 1;")
time.sleep(0.35)
j(c, "document.querySelector('[data-tr=sleep]').click(); return 1;")
time.sleep(0.35)
check('2 trackers on', j(c, "return document.querySelectorAll('#wlTrackers .wl-tracker.on').length;") == 2)

# ---- notes ----
j(c, "document.getElementById('wlNoteTxt').value='Had cramps this morning.'; document.getElementById('wlNoteAdd').click(); return 1;")
time.sleep(0.5)
check('note saved', j(c, "return document.getElementById('wlNoteList').textContent.indexOf('Had cramps this morning.')>=0;") is True)

# ---- history: log a second period -> first becomes history ----
j(c, "document.getElementById('wlLogBtn').click(); return 1;")
time.sleep(0.6)
j(c, """document.getElementById('wlPStart').value='2026-10-04';
  document.getElementById('wlPEnd').value='';
  document.getElementById('wlPSave').click(); return 1;""")
time.sleep(0.8)
check('history entry created', j(c, "return document.querySelectorAll('.wl-hist').length>=1;") is True)
j(c, "document.querySelector('.wl-hist').click(); return 1;")
time.sleep(0.7)
check('cycle detail sheet', j(c, "return !!document.querySelector('.wl-detail');") is True)
shot(c, 'dash-history')
j(c, "HUB.ui.closeSheet(); return 1;")
time.sleep(0.4)

# ---- wave 2: food ----
st = j(c, """return {phases:document.querySelectorAll('.wl-phase').length,
  now:document.querySelectorAll('.wl-phase .tag').length,
  diet:document.getElementById('wlPage').textContent.indexOf('Your period diet plan')>=0,
  mednote:document.getElementById('wlPage').textContent.indexOf('not medical advice')>=0};""")
check('food: 4 phases + diet plan', st['phases'] == 5, st)
check('food: current phase tagged Now', st['now'] >= 1, st)
check('food: general diet plan present', st['diet'] is True)
shot(c, 'dash-food')

# ---- wave 2: knowledge hub ----
check('hub: 4 articles', j(c, "return document.querySelectorAll('.wl-article').length;") == 4)
j(c, "document.querySelectorAll('.wl-article')[3].click(); return 1;")
time.sleep(0.4)
st = j(c, """return {open:document.querySelectorAll('.wl-article.open').length,
  txt:document.querySelectorAll('.wl-article')[3].textContent};""")
check('hub: article expands', st['open'] == 1)
check('hub: heavy-bleeding facts educational', 'longer than 7 days' in st['txt'] and 'Treatments exist' in st['txt'] and 'every hour' in st['txt'], st['txt'][:90])
shot(c, 'dash-hub')
errs0(c, 'dashboard-flows')

# ---- heavy-period nudge (10-day logged period) ----
j(c, "localStorage.removeItem('hub_wellness_v1'); return 1;")
c.send('Page.reload', {})
time.sleep(1.5)
boot(c)
set_gender(c, 'female')
j(c, "document.getElementById('wlStart').click(); return 1;")
time.sleep(0.8)
j(c, "document.getElementById('wlLogBtn').click(); return 1;")
time.sleep(0.6)
j(c, """document.getElementById('wlPStart').value='2026-09-01';
  document.getElementById('wlPEnd').value='2026-09-10';
  document.getElementById('wlPSave').click(); return 1;""")
time.sleep(0.8)
st = j(c, """return {nudge:!!document.querySelector('.wl-nudge'),
  txt:(document.querySelector('.wl-nudge')||{textContent:''}).textContent};""")
check('heavy nudge shown for 10-day period', st['nudge'] is True)
check('heavy nudge wording exact + informational', 'lasted longer than 7 days' in st['txt']
      and 'Consider speaking with a qualified healthcare professional if you are concerned' in st['txt']
      and 'diagnos' not in st['txt'].lower(), st['txt'][:80])
shot(c, 'dash-nudge')

# ---- reminders toggle ----
j(c, "document.querySelector('[data-rem=hydration]').click(); return 1;")
time.sleep(0.4)
check('reminder toggle off', j(c, "return !document.querySelector('[data-rem=hydration]').classList.contains('on');") is True)

# ---- hide card (reversible) ----
j(c, "document.getElementById('wlHideTgl').click(); return 1;")
time.sleep(0.5)
j(c, "document.getElementById('wlBack').click(); return 1;")
time.sleep(0.6)
check('hidden card row on Daily', j(c, "return !!document.querySelector('.wl-hidden-row');") is True)
check('hidden row shows no cycle data', j(c, "return /Estimated|period/i.test(document.querySelector('.wl-hidden-row').textContent||'');") is False)
j(c, "document.querySelector('.wl-hidden-row').click(); return 1;")
time.sleep(0.7)
check('hidden row reopens dashboard', dash_open(c))
j(c, "document.getElementById('wlHideTgl').click(); return 1;")
time.sleep(0.5)
j(c, "document.getElementById('wlBack').click(); return 1;")
time.sleep(0.6)
check('unhide restores full card', j(c, "return !!document.getElementById('wlOpenDash');") is True)

# ---- export button present ----
j(c, "document.getElementById('wlOpenDash').click(); return 1;")
time.sleep(0.7)
check('export button present', j(c, "return !!document.getElementById('wlExport');") is True)

# ---- delete data ----
j(c, "document.getElementById('wlDelete').click(); return 1;")
time.sleep(0.6)
check('delete confirm sheet', j(c, "return !!document.getElementById('wlDelYes');") is True)
j(c, "document.getElementById('wlDelYes').click(); return 1;")
time.sleep(0.8)
j(c, "document.getElementById('wlBack').click(); return 1;")
time.sleep(0.6)
check('delete resets to setup card', j(c, "return !!document.getElementById('wlStart');") is True)
errs0(c, 'privacy-flows')

# ---- storage isolation ----
st = j(c, """return {key:!!localStorage.getItem('hub_wellness_v1'),
  profClean:JSON.stringify(HUB.store.state.profile).indexOf('wellness')<0,
  entries:JSON.stringify(HUB.store.state).indexOf('hub_wellness')<0};""")
check('separate storage key', st['key'] is True)
check('no wellness data in public profile', st['profClean'] is True)
check('no wellness data in main store', st['entries'] is True)

# ---- other gender: full access ----
set_gender(c, 'other')
check('other: full access', j(c, "return !!document.getElementById('wlStart')||!!document.getElementById('wlOpenDash');") is True)
errs0(c, 'other-gender')
proc.terminate(); proc.wait(); proc = None

# ================= 320px =================
c = launch(width=320, height=568, prof='/tmp/hubqa-wellness-320')
set_gender(c, 'female')
check('320px: card renders', j(c, "return !!document.getElementById('wlCard');") is True)
check('320px: no horizontal overflow', j(c, "return document.documentElement.scrollWidth<=321;") is True,
      j(c, "return document.documentElement.scrollWidth;"))
j(c, "document.getElementById('wlStart').click(); return 1;")
time.sleep(0.8)
check('320px: dashboard opens', dash_open(c))
check('320px: no horizontal overflow (dash)', j(c, "return document.documentElement.scrollWidth<=321;") is True)
shot(c, 'dash-320')
errs0(c, '320px')
proc.terminate(); proc.wait(); proc = None

# ================= dark mode 390 =================
c = launch(prof='/tmp/hubqa-wellness-dark')
j(c, "HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme(); return 1;")
time.sleep(0.5)
set_gender(c, 'female')
check('dark: card renders', j(c, "return !!document.getElementById('wlCard');") is True)
j(c, "document.getElementById('wlStart').click(); return 1;")
time.sleep(0.8)
check('dark: dashboard opens', dash_open(c))
shot(c, 'dash-dark')
errs0(c, 'dark')
proc.terminate(); proc.wait(); proc = None

# ================= ne locale =================
c = launch(prof='/tmp/hubqa-wellness-ne', lang='ne')
set_gender(c, 'female')
tx = card_text(c) or ''
check('ne: translated card', 'महिनावारी' in tx, tx[:60])
errs0(c, 'ne-locale')
proc.terminate(); proc.wait(); proc = None

print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
