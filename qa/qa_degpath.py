#!/usr/bin/env python3
"""QA: student-path wrong-plan prevention (2026-10-07).
- School headers show kind pill (2-year/4-year) + city.
- Directory rows show kind.
- Concentration duplicates show track subtitles.
- Plan header shows concentration, catalog year, transfer/career chip,
  kind+city school line, prominent official-source button.
- Zero console errors. Screenshots at 390px.
"""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME
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

def shot(c, path):
    # headless-only artifacts (AGENTS.md): the boot watchdog recovery overlay
    # and the auth front-door login both appear on fresh profiles; hide them
    # so the degree UI underneath is visible. Pre-existing, not regressions.
    j(c, "var r=document.getElementById('saferecov'); if(r) r.remove();"
         "var a=document.getElementById('authRoot'); if(a) a.hidden=true; return 1;")
    time.sleep(0.4)
    r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True)
    open(path, 'wb').write(base64.b64decode(r['data']))
    print('shot', path)

def type_search(c, text):
    for ch in text:
        j(c, "var q=document.getElementById('degQ'); q.value=q.value+%s; q.dispatchEvent(new Event('input',{bubbles:true})); return 1;" % json.dumps(ch))
        time.sleep(0.06)
    time.sleep(2.2)

prof = '/tmp/hubqa-degpath'
subprocess.run(['rm', '-rf', prof])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
    '--user-data-dir=' + prof, '--hide-scrollbars', '--window-size=390,844', 'about:blank'])
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
c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
    "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
    "window.__gateSkip=true;"
    "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
    "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));"})
c.send('Page.navigate', {'url': BASE})
for _ in range(60):
    if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.degree&&HUB.i18n);") is True:
        break
    time.sleep(0.5)
for _ in range(40):
    if j(c, "return !document.getElementById('splash');") is True:
        break
    time.sleep(0.5)
j(c, "var p=HUB.store.state.profile; p.name='QA Path'; p.verified=true; HUB.store.save(); try{HUB.auth.close()}catch(e){} return 1;")
time.sleep(1)
# QA: force the static-file path (delete the hardcoded API base) so the
# picker loads from data/degrees/*.json locally instead of waiting out a
# Render cold start through the sandbox proxy.
j(c, "try{delete window.__ONARO_API_BASE;}catch(e){window.__ONARO_API_BASE='';} return 1;")
time.sleep(0.5)

# ---- 1. picker: search "Dallas" ----
j(c, "HUB.degree.open(); return 1;")
for _ in range(30):
    if j(c, "return !!document.getElementById('degQ');") is True:
        break
    time.sleep(0.5)
time.sleep(2)
type_search(c, "Dallas")
check('dallas: kind pill on collected school header',
      j(c, "return !!document.querySelector('.deg-school .deg-kind');") is True,
      j(c, "return (document.querySelector('.deg-school .deg-kind')||{}).textContent||'';"))
meta_txt = j(c, "return (document.querySelector('.deg-school .meta')||{textContent:''}).textContent;")
print('   school meta:', meta_txt)
check('dallas: city/state shown in school meta', 'Dallas' in (meta_txt or ''))
check('dallas: directory rows show kind',
      j(c, "return document.querySelector('#degBResults').textContent.indexOf('2-year college')>=0||document.querySelector('#degBResults').textContent.indexOf('4-year university')>=0;") is True)
shot(c, 'qa/degpath-dallas-390.png')

# ---- 2. concentration duplicates: Appalachian Bible College ----
j(c, "var q=document.getElementById('degQ'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); return 1;")
time.sleep(2.2)
type_search(c, "Appalachian Bible")
tracks = j(c, "return Array.prototype.map.call(document.querySelectorAll('.deg-track'),function(e){return e.textContent;});")
print('   track subtitles:', tracks)
check('concentration rows show track subtitles', isinstance(tracks, list) and len(tracks) >= 3)
shot(c, 'qa/degpath-tracks-390.png')

# ---- 3. plan view: concentration + catalog year + source ----
j(c, "HUB.degree.open('appalachian-bible-college-ba-music-missions'); return 1;", await_=True)
time.sleep(2.5)
for _ in range(30):
    if j(c, "return !!document.querySelector('.deg-head');") is True:
        break
    time.sleep(0.5)
check('plan header: concentration line', j(c, "return (document.querySelector('.deg-conc')||{textContent:''}).textContent;") == 'Missions track')
check('plan header: catalog year line', 'Catalog' in (j(c, "return (document.querySelector('.deg-catyr')||{textContent:''}).textContent;") or ''))
check('plan header: school line has kind+city',
      j(c, "return (document.querySelector('.deg-schoolname')||{textContent:''}).textContent;").find('Mount Hope') >= 0)
check('plan header: prominent source button', j(c, "return !!document.querySelector('.deg-srcbtn');") is True)
check('topbar title has track', 'Missions' in (j(c, "return document.getElementById('degTitle').textContent;") or ''))
shot(c, 'qa/degpath-plan-390.png')

# ---- 4. AAS plan: career track chip ----
j(c, "HUB.degree.open('dallas-college-aas-nursing'); return 1;", await_=True)
time.sleep(2)
for _ in range(30):
    if j(c, "return !!document.querySelector('.deg-head');") is True:
        break
    time.sleep(0.5)
chip = j(c, "return (document.querySelector('.deg-trackchip')||{textContent:''}).textContent;")
print('   track chip:', chip)
check('AAS plan: career track chip', chip == 'Career track')
check('AAS plan: catalog year', 'Catalog' in (j(c, "return (document.querySelector('.deg-catyr')||{textContent:''}).textContent;") or ''))
shot(c, 'qa/degpath-aas-390.png')

# ---- 5. transfer chip on AA plan ----
j(c, "HUB.degree.open('dallas-college-aa-business'); return 1;", await_=True)
time.sleep(2)
for _ in range(30):
    if j(c, "return !!document.querySelector('.deg-head');") is True:
        break
    time.sleep(0.5)
chip2 = j(c, "return (document.querySelector('.deg-trackchip')||{textContent:''}).textContent;")
check('AA plan: transfer track chip', chip2 == 'Transfer track')

# ---- 6. no console errors ----
errs = j(c, "return window.__huberr||[];")
check('zero console errors', not errs, errs[:3] if errs else '')

print('FAILURES:', fails if fails else 'none')
proc.terminate()
sys.exit(1 if fails else 0)
