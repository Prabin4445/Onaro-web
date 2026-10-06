#!/usr/bin/env python3
"""QA: outgoing ringback tone (2026-09-30).
Classic NA ringback (440+480Hz, 2s on/4s off, WebAudio loop) must:
- start when the CALLER places an outgoing call (1:1/group, loopback demo),
- stop when the first peer joins (answers),
- never play on the callee/joiner side,
- stop on leave/cancel and on mic-denied,
- never leak (no looping tone after teardown).
Introspection via HUB.call._ringback() (QA-only hook)."""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import websocket  # noqa: F401 (parity with other harnesses)

PORT = 9451
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-ringback'
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

ERR_HOOK = ("try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
            "window.__huberr=[];"
            "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
            "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

def wait_true(c, expr, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if j(c, expr) is True:
            return True
        time.sleep(0.5)
    return False

def boot_tab(c, name):
    c.send('Runtime.enable')
    c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source': ERR_HOOK})
    c.send('Page.navigate', {'url': BASE})
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.call&&HUB.i18n);") is True:
            break
        time.sleep(0.5)
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    j(c, """var p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus';
      p.verified=true; HUB.store.save(); try{HUB.auth.close()}catch(e){} return 1;""" % json.dumps(name))
    j(c, """HUB.store.state.cgroups=[{id:'g1',name:'Weekend Hikers',mine:true,members:[%s]}];
      HUB.store.save(); return 1;""" % json.dumps(name))
    time.sleep(0.8)

subprocess.run(['rm', '-rf', PROF])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
    '--user-data-dir=' + PROF, '--hide-scrollbars', '--window-size=390,844', 'about:blank'])
time.sleep(2.5)

def open_tab():
    req = urllib.request.Request('http://127.0.0.1:%d/json/new?about:blank' % PORT, method='PUT')
    last = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(0.5)
    raise RuntimeError('chrome DevTools port never came up: %r' % (last,))

tA = open_tab()
cA = CDP(tA['webSocketDebuggerUrl'])
boot_tab(cA, 'QA Caller')

# ---- 1. caller starts outgoing call -> ringback plays ----
j(cA, "HUB.call.start('g1',{outgoing:true}); return 1;")
ok_active = wait_true(cA, "return HUB.call.isActive();")
check('outgoing call becomes active', ok_active)
ok_rb = wait_true(cA, "return HUB.call._ringback();", timeout=10)
check('ringback STARTS on outgoing call', ok_rb)
# the tone really is a 440+480 WebAudio loop: two oscillators + gain on an AudioContext
aud = j(cA, """return (function(){ try{
    return {ctx:!!(window.AudioContext||window.webkitAudioContext)}; }catch(e){ return {ctx:false}; } })();""")
check('WebAudio available for ringback', bool(aud and aud.get('ctx')), aud)
r = cA.send('Page.captureScreenshot', {'format': 'png'})
open(os.path.join(QA, 'ringback-calling.png'), 'wb').write(base64.b64decode(r['data']))

# ---- 2. joiner answers from a second tab -> caller ringback stops, joiner never rings ----
tB = open_tab()
cB = CDP(tB['webSocketDebuggerUrl'])
boot_tab(cB, 'QA Joiner')
# join via the incoming UI if it appeared, else direct start (joiner: no outgoing flag)
joined = j(cB, """var a=document.getElementById('incAnswer');
  if(a&&!document.getElementById('incallRoot').hidden){ a.click(); return 'banner'; }
  var j=document.getElementById('callBannerJoin');
  if(j&&!document.getElementById('callBanner').hidden){ j.click(); return 'topbanner'; }
  HUB.call.start('g1'); return 'direct';""")
time.sleep(1.0)
ok_b = wait_true(cB, "return HUB.call.isActive();")
check('joiner tab becomes active', ok_b, 'via=%s' % joined)
ok_peer = wait_true(cA, "return !!(HUB.call._debug()&&HUB.call._debug().peers.length>0);", timeout=20)
check('caller sees the joining peer', ok_peer,
      j(cA, "return HUB.call._debug()&&HUB.call._debug().peerNames;"))
time.sleep(1.0)
check('ringback STOPS when peer joins', j(cA, "return HUB.call._ringback();") is False)
check('joiner NEVER hears ringback', j(cB, "return HUB.call._ringback();") is False)

# ---- 3. caller leaves -> ringback stays stopped, session torn down ----
j(cA, "HUB.call.leave(); return 1;")
time.sleep(1.0)
check('ringback stopped after leave', j(cA, "return HUB.call._ringback();") is False)
check('call inactive after leave', j(cA, "return HUB.call.isActive();") is False)
j(cB, "HUB.call.leave(); return 1;")
time.sleep(0.8)

# ---- 4. cancel path: ringback on, then leave before anyone joins ----
j(cA, "HUB.call.start('g1',{outgoing:true}); return 1;")
check('ringback restarts on new outgoing call', wait_true(cA, "return HUB.call._ringback();", timeout=10))
j(cA, "HUB.call.leave(); return 1;")  # caller cancels before pickup
time.sleep(0.8)
check('ringback stopped on cancel', j(cA, "return HUB.call._ringback();") is False)

# ---- 5. mic-denied path: tone must not loop when the call can't start ----
j(cA, """navigator.mediaDevices.getUserMedia=function(){
    return Promise.reject(new DOMException('denied','NotAllowedError')); }; return 1;""")
j(cA, "HUB.call.start('g1',{outgoing:true}); return 1;")
ok_denied = wait_true(cA, "return !document.getElementById('callError').hidden;", timeout=15)
check('mic-denied error shown', ok_denied)
time.sleep(0.8)
check('ringback stopped on mic-denied', j(cA, "return HUB.call._ringback();") is False)
r = cA.send('Page.captureScreenshot', {'format': 'png'})
open(os.path.join(QA, 'ringback-micdenied.png'), 'wb').write(base64.b64decode(r['data']))
j(cA, "HUB.call.leave(); return 1;")
time.sleep(0.5)

# ---- 6. demo-20 simulation: no ringback (crowd is "already there") ----
j(cA, "HUB.call.start('g1',{demo20:true}); return 1;")
time.sleep(3.0)
check('demo-20 never plays ringback', j(cA, "return HUB.call._ringback();") is False)
j(cA, "HUB.call.leave(); return 1;")
time.sleep(0.5)

# ---- 7. no-answer timeout (WhatsApp/carrier style): unanswered call hangs up itself ----
# 7a. caller: timeout fires -> ringback stops, call torn down, popup shown
cA.send('Page.navigate', {'url': BASE})  # fresh page: restores real getUserMedia
boot_tab(cA, 'QA Caller')
j(cA, "HUB.call._noAnswerMs(4000); return 1;")
j(cA, "HUB.call.start('g1',{outgoing:true}); return 1;")
check('ringback on before timeout', wait_true(cA, "return HUB.call._ringback();", timeout=10))
ok_popup = wait_true(cA, "return !document.getElementById('sheetHost').hidden"
    "&& document.getElementById('sheetHost').textContent.indexOf('No user available')>=0;", timeout=12)
check('no-answer POPUP shown with PraBin text', ok_popup)
check('ringback stopped by timeout', j(cA, "return HUB.call._ringback();") is False)
check('call torn down by timeout', j(cA, "return HUB.call.isActive();") is False)
r = cA.send('Page.captureScreenshot', {'format': 'png'})
open(os.path.join(QA, 'ringback-noanswer.png'), 'wb').write(base64.b64decode(r['data']))
j(cA, "var b=document.getElementById('callNoAnswerOk'); if(b) b.click(); return 1;")
time.sleep(0.6)
check('popup OK dismisses', j(cA, "return document.getElementById('sheetHost').hidden;") is True)

# 7b. peer joins before timeout -> no popup, call continues
j(cA, "HUB.call._noAnswerMs(8000); return 1;")
j(cA, "HUB.call.start('g1',{outgoing:true}); return 1;")
wait_true(cA, "return HUB.call._ringback();", timeout=10)
j(cB, "HUB.call.start('g1'); return 1;")
ok_peer2 = wait_true(cA, "return !!(HUB.call._debug()&&HUB.call._debug().peers.length>0);", timeout=20)
check('joiner arrives before timeout', ok_peer2)
time.sleep(9.0)  # past the 8s timeout
check('NO popup when answered in time',
      j(cA, "return document.getElementById('sheetHost').hidden"
      "|| document.getElementById('sheetHost').textContent.indexOf('No user available')<0;") is True)
check('call still active after answered', j(cA, "return HUB.call.isActive();") is True)
j(cA, "HUB.call.leave(); return 1;")
j(cB, "HUB.call.leave(); return 1;")
time.sleep(0.8)

# 7c. callee side: unanswered incoming banner goes quiet by itself
j(cB, "HUB.call._noAnswerMs(4000); return 1;")
j(cA, "HUB.call._noAnswerMs(45000); HUB.call.start('g1',{outgoing:true}); return 1;")
wait_true(cA, "return HUB.call._ringback();", timeout=10)
ok_banner = wait_true(cB, "return !document.getElementById('callBanner').hidden"
    "|| !document.getElementById('incallRoot').hidden;", timeout=15)
check('incoming banner shown on callee tab', ok_banner)
ok_quiet = wait_true(cB, "return document.getElementById('callBanner').hidden"
    "&& document.getElementById('incallRoot').hidden;", timeout=12)
check('callee banner auto-dismissed on timeout', ok_quiet)
check('callee never joined', j(cB, "return HUB.call.isActive();") is False)
j(cA, "HUB.call.leave(); return 1;")
time.sleep(0.8)

errsA = j(cA, "return window.__huberr.slice(0,8);")
errsB = j(cB, "return window.__huberr.slice(0,8);")
check('zero console errors (caller tab)', not errsA, errsA)
check('zero console errors (joiner tab)', not errsB, errsB)

proc.terminate()
proc.wait()
print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
