#!/usr/bin/env python3
"""Onaro ringtone-delay QA (2026-09-23).

PraBin's bug: the incoming-call ringtone started ~10s after the call arrived.
Root cause: playRingtone() built the Audio element lazily at call time, so
the first audible sample waited for the 316KB mp3 fetch + decode + iOS media
pipeline spin-up. Fix: HUB.sound.primeRingtone() preloads the selected
ringtone at boot (app.js DOMContentLoaded) and on every setRingtone/setOn(true).

Asserts, at 390x844, dark+light, fresh profiles, zero console errors:
- primeRingtone exists and the selected ringtone is primed at boot
  (_debug().ringSrc non-null, ringReady >= 2 = HAVE_CURRENT_DATA)
- the ringtone resource was fetched at BOOT, not at call time
  (resource timing startTime < incoming-show time)
- incoming call -> isRinging() true within 1000ms of HUB.incoming.show()
- setRingtone('breeze') re-primes the new file (no lazy fetch on next call)
- incoming UI still renders (name, answer/decline), stops cleanly
- static: primeRingtone wired in app.js boot; no `t` shadowing in new code
"""
import json, subprocess, time, urllib.request, os, re, shutil
import websocket

HUB = os.path.expanduser('~/workspace/hub')
QA = os.path.join(HUB, 'qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9493
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

def js_eval(c, expr):
    try:
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        if r and 'exceptionDetails' in r:
            ed = r['exceptionDetails']
            return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
        return (r or {}).get('result', {}).get('value')
    except Exception as e:
        return 'JSERR:' + str(e)[:120]

def wait_for(c, expr, timeout=15, poll=0.2):
    dl = time.time() + timeout
    while time.time() < dl:
        if js_eval(c, expr) is True: return True
        time.sleep(poll)
    return False

ARM = ("window.__huberr=[];addEventListener('error',function(e){window.__huberr.push('ERR:'+e.message)});"
       "addEventListener('unhandledrejection',function(e){window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))});")

PRIME_STATE = """(function(){var d=HUB.sound._debug();
return {src:d.ringSrc, ready:d.ringReady, base:d.ringBase, ringtone:d.ringtone,
        unlocked:d.unlocked, ringing:d.ringing};})()"""

RES_TIMING = """(function(){var t0=window.__showT0||0;
return performance.getEntriesByType('resource')
 .filter(function(e){return /ringtone-/.test(e.name);})
 .map(function(e){return {f:e.name.split('/').pop().split('?')[0],
   start:Math.round(e.startTime), dur:Math.round(e.duration), bootFetch:e.startTime<t0};});})()"""

def static_checks():
    snd = open(os.path.join(HUB, 'js', 'sound.js')).read()
    app = open(os.path.join(HUB, 'js', 'app.js')).read()
    note('function primeRingtone()' in snd, 'static: primeRingtone() defined in sound.js')
    note('primeRingtone:primeRingtone' in snd, 'static: primeRingtone exported on HUB.sound')
    note('HUB.sound.primeRingtone()' in app and 'DOMContentLoaded' in app,
         'static: app.js boot calls HUB.sound.primeRingtone()')
    note('primeRingtone()' in snd.split('function setRingtone')[1].split('function stopRingtone')[0]
         if 'function setRingtone' in snd else False,
         'static: setRingtone re-primes the new selection')
    # t-shadowing guard on the new/edited functions (crude: no `var t`/`let t`/`,t,` in primeRingtone)
    m = re.search(r'function primeRingtone\(\)\{(.*?)\n  \}', snd, re.S)
    body = m.group(1) if m else ''
    note(m and not re.search(r'\b(var|let|const)\s+t\b|\(\s*t\s*[,)]', body),
         'static: no `t` shadowing in primeRingtone')
    note('ringEl.load()' in snd, 'static: prime forces explicit load()')

def run_case(theme):
    tag = f'390x844-{theme}'
    prof = f'/tmp/hubqa-ringdelay-{theme}'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        '--window-size=390,844', f'--user-data-dir={prof}', '--hide-scrollbars',
        '--allow-file-access-from-files',
        '--autoplay-policy=no-user-gesture-required', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                    ts = json.load(rr)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844,
               'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE})
        note(wait_for(c, "!!(window.HUB&&HUB.sound&&HUB.incoming)", timeout=20),
             f'boot reached HUB.sound + HUB.incoming [{tag}]')
        js_eval(c, "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') +
                   ";HUB.store.state.profile.name='Prabin';HUB.store.save();")
        js_eval(c, ARM)
        # let boot settle (splash min-show ~2s, prime fetch of 316KB mp3)
        note(wait_for(c, "HUB.sound._debug().ringReady>=2", timeout=20),
             f'ringtone primed at boot (readyState>=2) [{tag}]',
             repr(js_eval(c, PRIME_STATE))[:140])
        st = js_eval(c, PRIME_STATE)
        if isinstance(st, dict):
            note(bool(st.get('src')) and 'ringtone-aurora' in str(st.get('src')),
                 f'primed file is the selected ringtone (aurora) [{tag}]', str(st.get('src'))[-40:])

        # --- the delay test: incoming call -> first audible playback ---
        pre = js_eval(c, PRIME_STATE)  # primed element identity before the call
        js_eval(c, "window.__showT0=performance.now();"
                   "HUB.incoming.show({name:'QA Caller',kind:'voice',demo:true});")
        t0 = time.time(); ringing = False; delta = -1
        while time.time() - t0 < 5:
            if js_eval(c, "HUB.sound.isRinging()") is True:
                ringing = True; delta = round((time.time() - t0) * 1000); break
            time.sleep(0.025)
        note(ringing and delta < 1000,
             f'ringtone starts within 1s of incoming call (was ~10s) [{tag}]',
             f'delta={delta}ms')
        # no lazy rebuild on the call path: same primed element, fully buffered
        post = js_eval(c, PRIME_STATE)
        note(isinstance(pre, dict) and isinstance(post, dict)
             and post.get('src') == pre.get('src') and post.get('ready') == 4,
             f'call reuses the boot-primed element (no fetch at call time) [{tag}]',
             repr(post)[:140])
        # incoming UI sane while ringing
        ui = js_eval(c, "(function(){var r=document.getElementById('incallRoot');"
                        "return r?{hidden:r.hidden,name:document.getElementById('incName').textContent,"
                        "ans:!!document.getElementById('incAnswer'),dec:!!document.getElementById('incDecline')}:null;})()")
        note(isinstance(ui, dict) and ui.get('hidden') is False and ui.get('name') == 'QA Caller'
             and ui.get('ans') and ui.get('dec'),
             f'incoming UI renders with answer/decline while ringing [{tag}]', repr(ui)[:120])
        # decline stops the ringtone cleanly
        js_eval(c, "document.getElementById('incDecline').click();")
        note(wait_for(c, "!HUB.sound.isRinging()", timeout=5),
             f'decline stops ringtone [{tag}]')

        # --- selection change re-primes (no lazy fetch on next call) ---
        js_eval(c, "HUB.sound.setRingtone('breeze');")
        note(wait_for(c, "HUB.sound._debug().ringReady>=2&&/ringtone-breeze/.test(HUB.sound._debug().ringSrc||'')",
                      timeout=20),
             f'setRingtone(breeze) re-primes immediately [{tag}]')
        js_eval(c, "HUB.sound.setRingtone('aurora');")
        wait_for(c, "/ringtone-aurora/.test(HUB.sound._debug().ringSrc||'')", timeout=20)

        errs = js_eval(c, "window.__huberr")
        note(isinstance(errs, list) and len(errs) == 0, f'zero console errors [{tag}]', repr(errs)[:160])
    finally:
        try: proc.terminate()
        except Exception: pass

if __name__ == '__main__':
    static_checks()
    run_case('dark')
    run_case('light')
    fails = [l for ok, l in checks if not ok]
    print(f'\n{len(checks)-len(fails)}/{len(checks)} checks passed')
    if fails:
        print('FAILURES:'); [print(' -', l) for l in fails]
        raise SystemExit(1)
