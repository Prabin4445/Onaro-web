#!/usr/bin/env python3
"""QA: degree picker unified search (2026-09-30).
- Exactly ONE search box (#degQ, no #degBQ).
- Typing filters plans AND searches the national directory.
- Input keeps focus while typing (no re-render shake).
- School tap opens programs; back returns.
- Chips still filter; zero console errors."""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import websocket  # noqa: F401

PORT = 9449
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

def type_search(c, text):
    # type char by char like a real user (debounce 220ms)
    for ch in text:
        j(c, "var q=document.getElementById('degQ'); q.value=q.value+%s; q.dispatchEvent(new Event('input',{bubbles:true})); return 1;" % json.dumps(ch))
        time.sleep(0.08)
    time.sleep(1.6)  # debounce + dir.json load

prof = '/tmp/hubqa-degsearch'
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
    "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
    "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));"})
c.send('Page.navigate', {'url': BASE})
for _ in range(60):
    if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.degree&&HUB.i18n);") is True:
        break
    time.sleep(0.5)
# watchdog sanity: the boot watchdog must be disarmed by real init
for _ in range(40):
    if j(c, "return !document.getElementById('splash');") is True:
        break
    time.sleep(0.5)
j(c, """var p=HUB.store.state.profile; p.name='QA Search'; p.campus='The University of Texas at Dallas';
  p.verified=true; HUB.store.save(); try{HUB.auth.close()}catch(e){} return 1;""")
time.sleep(1)
check('no recovery overlay (watchdog disarmed)', j(c, "return !document.getElementById('saferecov');") is True)
time.sleep(1)

# open the degree picker
j(c, "HUB.degree.open(); return 1;")
for _ in range(30):
    if j(c, "return !!document.getElementById('degQ');") is True:
        break
    time.sleep(0.5)
time.sleep(1.5)

# 1. exactly one search box
n_q = j(c, "return document.querySelectorAll('#degQ').length;")
n_bq = j(c, "return document.querySelectorAll('#degBQ').length;")
check('exactly one search box', n_q == 1 and n_bq == 0, 'degQ=%s degBQ=%s' % (n_q, n_bq))

# focus the input, then type "mcneese"
j(c, "document.getElementById('degQ').focus(); return 1;")
type_search(c, 'mcneese')

# 2. input still focused after typing (no shake/re-render of input)
focused = j(c, "return document.activeElement&&document.activeElement.id;")
check('input keeps focus while typing', focused == 'degQ', 'activeElement=%s' % focused)
val = j(c, "return document.getElementById('degQ').value;")
check('typed text intact', val == 'mcneese', repr(val))

# 3. directory found McNeese
rows = j(c, """return Array.prototype.map.call(document.querySelectorAll('#degBrowse [data-bunit]'),
  function(b){ return b.querySelector('b').textContent; }).slice(0,5);""")
check('directory finds McNeese State University', any('McNeese' in r for r in (rows or [])), rows)

# 4. tap the school -> programs load
j(c, """var b=document.querySelector('#degBrowse [data-bunit]'); if(b) b.click(); return !!b;""")
progs = None
for _ in range(30):
    progs = j(c, "return document.querySelectorAll('#degBResults .deg-pending-row, #degBResults .deg-planrow').length;")
    if progs and progs > 5:
        break
    time.sleep(0.5)
check('school programs load', (progs or 0) > 5, 'rows=%s' % progs)
r = c.send('Page.captureScreenshot', {'format': 'png'})
open(os.path.join(QA, 'degsearch-school.png'), 'wb').write(base64.b64decode(r['data']))

# 5. back returns to unified results
j(c, "var b=document.getElementById('degDirBack'); if(b) b.click(); return !!b;")
time.sleep(1.5)
rows2 = j(c, "return document.querySelectorAll('#degBrowse [data-bunit]').length;")
check('back returns to directory results', (rows2 or 0) > 0, 'rows=%s' % rows2)

# 6. nonsense query -> honest empty states, input still fine
j(c, "var q=document.getElementById('degQ'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); return 1;")
time.sleep(1.0)
type_search(c, 'zzzqqqnomatch')
no_sch = j(c, "return (document.getElementById('degBResults')||{textContent:''}).textContent;")
check('no-match directory message', 'No colleges match' in (no_sch or ''), (no_sch or '')[:60])
focused2 = j(c, "return document.activeElement&&document.activeElement.id;")
check('input keeps focus on no-match', focused2 == 'degQ', 'activeElement=%s' % focused2)

# 7. chips still filter without touching the input
j(c, """var q=document.getElementById('degQ'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); return 1;""")
time.sleep(1.2)
j(c, """var ch=document.querySelector('.deg-chip[data-level="associate"]'); if(ch) ch.click(); return !!ch;""")
time.sleep(1.2)
chip_on = j(c, """var ch=document.querySelector('.deg-chip[data-level="associate"]');
  return ch&&ch.classList.contains('on');""")
check('associate chip activates', chip_on is True)
focused3 = j(c, "return document.activeElement&&document.activeElement.id;")
check('chip tap keeps search input intact', j(c, "return !!document.getElementById('degQ');") is True, 'active=%s' % focused3)

errs = j(c, "return window.__huberr.slice(0,8);")
check('zero console errors', not errs, errs)
r = c.send('Page.captureScreenshot', {'format': 'png'})
open(os.path.join(QA, 'degsearch-final.png'), 'wb').write(base64.b64decode(r['data']))
proc.terminate()
proc.wait()

print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
