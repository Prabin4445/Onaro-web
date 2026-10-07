#!/usr/bin/env python3
"""QA: Home "Degree progress" card (2026-10-07, PraBin order).
- Card renders directly above "Your classes" (#classCard).
- Numbers match hand-computed fixture (aaniiih AAS industrial trades:
  total 62, earned 3, left 59, pct 5, sem1 16cr, finishes Spring 2028).
- Tap card -> opens the enrolled plan tracker.
- Empty state when no plan enrolled (honest, never faked).
- 390px + 320px, zero console errors, zero horizontal overflow.
"""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME
import websocket  # noqa: F401

PORT = 9452
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
    j(c, "var r=document.getElementById('saferecov'); if(r) r.remove();"
         "var a=document.getElementById('authRoot'); if(a) a.hidden=true; return 1;")
    # scroll top->bottom so lazy icons load (AGENTS.md), then back to top
    j(c, "return new Promise(function(res){ var y=0; var iv=setInterval(function(){ y+=600; window.scrollTo(0,y);"
         "if(y>=document.body.scrollHeight){ clearInterval(iv); window.scrollTo(0,0); setTimeout(res,600);} },120); });", await_=True)
    time.sleep(0.4)
    r = c.send('Page.captureScreenshot', {'format': 'png'}, wait=True)
    open(path, 'wb').write(base64.b64decode(r['data']))
    print('shot', path)

SEED = """(function(){
  var st=HUB.store.state;
  st.degree={active:'aaniiih-nakoda-college-aas-industrial-trades',tracked:'aaniiih-nakoda-college-aas-industrial-trades',progress:{
    'aaniiih-nakoda-college-aas-industrial-trades':{
      done:{'s1-0':{code:'GS 110',credits:1,ts:1000},'s1-1~~0:1':{code:'M 101',credits:2,ts:2000,at:'0:1'}},
      startYear:2026, intake:{term:'fall',year:2026}, pace:0
    }}};
  HUB.store.save(); HUB.showTab('home'); return 1; })()"""

def boot(width):
    prof = '/tmp/hubqa-degprog-%d' % width
    subprocess.run(['rm', '-rf', prof])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + prof, '--hide-scrollbars', '--window-size=%d,844' % width, 'about:blank'])
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
    c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
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
    j(c, "var p=HUB.store.state.profile; p.name='QA Prog'; p.verified=true; HUB.store.save(); try{HUB.auth.close()}catch(e){} return 1;")
    time.sleep(1)
    j(c, "try{delete window.__ONARO_API_BASE;}catch(e){window.__ONARO_API_BASE='';} return 1;")
    time.sleep(0.5)
    return c, proc

def wait_fill(c, timeout=60):
    # wait until the card leaves skeleton/empty AND the count-up tween settles
    # (read dpgLeft twice 1.2s apart; stable + non-zero means done)
    last = None
    for _ in range(int(timeout / 0.6)):
        v = j(c, "return (document.getElementById('dpgLeft')||{}).textContent;")
        if v and v not in ('0', '') and v == last:
            return True
        last = v if v not in ('0', '') else last
        if j(c, "return !!document.querySelector('[data-degprog-empty]');"):
            return 'empty'
        time.sleep(0.6)
    return False

for width in (390, 320):
    c, proc = boot(width)
    # ---- 1. seeded plan: card above classes, numbers correct ----
    j(c, SEED)
    filled = wait_fill(c)
    check('%d: card filled (not stuck on skeleton)' % width, filled is True, filled)
    order = j(c, """return (function(){
      var hp=document.getElementById('homeDegProg');
      var cc=document.getElementById('classCard');
      if(!hp||!cc) return 'missing:'+!!hp+','+!!cc;
      var hsec=cc.closest('.hsec');
      var prev=hsec?hsec.previousElementSibling:null;
      return (prev&&prev.id==='homeDegProg')?'directly-above':'prev='+(prev?prev.id:'none');
    })();""")
    check('%d: card directly above Your classes' % width, order == 'directly-above', order)
    check('%d: credits left = 59' % width, j(c, "return document.getElementById('dpgLeft').textContent;") == '59')
    check('%d: this semester = 16' % width, j(c, "return document.getElementById('dpgSem').textContent;") == '16')
    check('%d: completed = 3' % width, j(c, "return document.getElementById('dpgEarn').textContent;") == '3')
    check('%d: pct = 5%%' % width, j(c, "return document.getElementById('dpgPct').textContent;") == '5%')
    fin = j(c, "return document.getElementById('dpgFin').textContent;")
    check('%d: finishes Spring 2028' % width, fin == 'Spring 2028', fin)
    semlbl = j(c, "return document.getElementById('dpgSemLbl').textContent;")
    check('%d: semester label Fall 2026' % width, semlbl == 'Fall 2026', semlbl)
    ring = j(c, "return document.querySelector('.dpg-bar').style.strokeDashoffset;")
    check('%d: ring swept (not full offset)' % width, ring not in ('', '339.3'), ring)
    ovf = j(c, "return document.documentElement.scrollWidth>window.innerWidth;")
    check('%d: zero horizontal overflow' % width, ovf is False, ovf)
    shot(c, 'qa/degprog-%d.png' % width)
    # ---- 2. tap card -> opens enrolled plan ----
    j(c, "document.getElementById('degprogCard').click(); return 1;")
    title = ''
    for _ in range(40):
        time.sleep(0.5)
        opened = j(c, "return !!document.querySelector('.degroot .deg-panel');")
        title = j(c, "return (document.getElementById('degTitle')||{}).textContent||'';")
        if opened and ('Industrial' in title or 'A.A.S.' in title):
            break
    check('%d: tap opens plan tracker' % width, opened is True)
    check('%d: tracker shows the enrolled plan' % width, 'Industrial' in title or 'A.A.S.' in title, title[:60])
    j(c, "var b=document.getElementById('degClose'); if(b) b.click(); return 1;")
    time.sleep(1)
    # ---- 3. empty state: no plan enrolled ----
    j(c, "(function(){ HUB.store.state.degree={active:null,tracked:null,progress:{}}; HUB.store.save(); HUB.showTab('home'); return 1; })()")
    time.sleep(2)
    empty = j(c, "return !!document.querySelector('[data-degprog-empty]');")
    check('%d: honest empty state with no plan' % width, empty is True)
    cta = j(c, "return (document.querySelector('.degprog-cta')||{}).textContent||'';")
    check('%d: empty CTA present' % width, 'Find my plan' in cta, cta.strip()[:40])
    shot(c, 'qa/degprog-empty-%d.png' % width)
    errs = j(c, "return window.__huberr||[];")
    check('%d: zero console errors' % width, not errs, str(errs)[:200])
    proc.terminate()

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
