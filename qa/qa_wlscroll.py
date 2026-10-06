#!/usr/bin/env python3
"""Focused QA: tapping a Daily wellness tracker must NOT reset scroll (the 'refresh' feel)."""
import subprocess, time, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME
import websocket  # noqa: F401
import urllib.request

PORT = 9457
fails = []
def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok: fails.append(n)

def j(c, expr):
    e = expr.strip()
    if not any(ch == ';' for ch in e):
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

prof = '/tmp/hubqa-wlscroll'
subprocess.run(['rm', '-rf', prof])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
    '--user-data-dir=' + prof, '--window-size=390,844', 'about:blank'])
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
c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
    "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"})
c.send('Page.navigate', {'url': 'file:///home/hatch/workspace/hub/index.html'})
for _ in range(60):
    if j(c, "window.HUB&&HUB.wellness&&HUB.store&&HUB.views&&HUB.views.daily") : break
    time.sleep(0.5)
j(c, "window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 1;")
time.sleep(0.6)
# female + enable wellness + open dashboard
j(c, "HUB.store.state.profile.gender='female'; HUB.store.save(); 1;")
j(c, "HUB.wellness.openDashboard(); 1;")
time.sleep(1.2)
check('dashboard open', j(c, "!!document.getElementById('wlPage')") is True)
# scroll down to the trackers section
y0 = j(c, "return (function(){var p=document.getElementById('wlPage'); p.scrollTop=900; return p.scrollTop;})();")
time.sleep(0.4)
check('scrolled down', (y0 or 0) > 500, y0)
# tap the first tracker tile
j(c, "return (function(){document.querySelector('#wlTrackers .wl-tracker').click(); return 1;})();")
time.sleep(0.8)
y1 = j(c, "return document.getElementById('wlPage').scrollTop;")
check('scroll preserved after tracker tap (no refresh feel)', abs((y1 or 0) - (y0 or 0)) < 40, 'before=%s after=%s' % (y0, y1))
check('tracker toggled on', j(c, "return document.querySelector('#wlTrackers .wl-tracker').classList.contains('on');") is True)
# tap a symptom chip too (same repaint path)
j(c, "return (function(){var p=document.getElementById('wlPage'); p.scrollTop=700; document.querySelector('.wl-sym').click(); return 1;})();")
time.sleep(0.8)
y2 = j(c, "return document.getElementById('wlPage').scrollTop;")
check('scroll preserved after symptom tap', abs((y2 or 0) - 700) < 40, y2)
e = j(c, "window.__huberr ? window.__huberr.slice(0,5) : [];")
check('zero console errors', not e, e)
proc.terminate()
print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
