#!/usr/bin/env python3
"""QA: laser notification chime wiring + on/off toggle (headless Chromium)."""
import json, subprocess, time, urllib.request, os, sys
import websocket

CHROME = '/opt/meta-chromium/chrome'
PORT = 9331
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl)
        self.id = 0
    def send(self, method, params=None, wait=True):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        if not wait: return None
        deadline = time.time() + 25
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.id:
                return msg.get('result')
        raise TimeoutError(method)

def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (" " + str(detail) if detail else ""))
    if not cond: fails.append(name)

proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
    '--user-data-dir=/tmp/hubqa-laser', '--hide-scrollbars',
    '--autoplay-policy=no-user-gesture-required', BASE])
time.sleep(3)
try:
    with urllib.request.urlopen(f'http://localhost:{PORT}/json/list') as r:
        tgt = [t for t in json.load(r) if t['type'] == 'page' and 'devtools' not in t['url']][0]
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable')
    def js(expr):
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, wait=True)
        res = (r or {}).get('result', {})
        return res.get('value'), res.get('exceptionDetails')
    JS = "(function(){%s})()"
    js("window.__huberr=[];window.addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
       "window.addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+(e.reason&&e.reason.message||e.reason)));")

    # wait for boot
    for _ in range(40):
        v, _ = js(JS % "return (window.HUB&&HUB.sound&&HUB.store)?1:0")
        if v: break
        time.sleep(0.5)
    check("app booted with HUB.sound", v == 1)

    # disarm auth gate like other harnesses
    js(JS % "try{window.__gateSkip=true;HUB.auth.close();var w=document.getElementById('wlcmHost');if(w)w.remove();}catch(e){} return 1")

    # 1. playNotification with sound ON does not throw, wires to notify.mp3?v=5
    v, e = js(JS % "try{HUB.sound.setOn(true);HUB.sound.playNotification();var d=HUB.sound._debug();return d.noteSrc||'none';}catch(x){return 'THROW:'+x.message}")
    check("playNotification no-throw, noteSrc set", isinstance(v, str) and 'notify' in v, v)
    check("cache-busting ?v=5 on notify", isinstance(v, str) and 'v=5' in v, v)

    # 2. debug counters: chime counted
    v, _ = js(JS % "return HUB.sound._debug().chimes")
    check("chime counter incremented", v >= 1, v)

    # 3. sound OFF: playNotification is a silent no-op (no throw, no new chime)
    v, _ = js(JS % "var a=HUB.sound._debug().chimes;HUB.sound.setOn(false);try{HUB.sound.playNotification();}catch(x){return 'THROW'}var b=HUB.sound._debug().chimes;return (b===a)?'silent-ok':'CHIMED:'+b")
    check("sound OFF silences notification", v == 'silent-ok', v)

    # 4. sound back ON works again (wait out the 800ms anti-storm throttle first)
    time.sleep(1.0)
    v, _ = js(JS % "HUB.sound.setOn(true);var a=HUB.sound._debug().chimes;HUB.sound.playNotification();return HUB.sound._debug().chimes===a+1?'ok':'no'")
    check("sound ON re-arms chime", v == 'ok', v)

    # 5. settings toggle UI exists and flips prefs
    v, _ = js(JS % "try{HUB.me&&HUB.me.open?HUB.me.open('settings'):0;}catch(e){} return 1")
    time.sleep(1.0)
    v, _ = js(JS % "var el=document.getElementById('soundToggle');return el?'found:'+el.classList.contains('on'):'missing'")
    check("settings sound toggle present", isinstance(v, str) and v.startswith('found'), v)

    # 6. ringtone untouched (aurora default still wired)
    v, _ = js(JS % "return HUB.sound.getRingtone()")
    check("call ringtone untouched", v == 'aurora', v)

    # 7. mute cue is a silent no-op (removed on his order)
    v, _ = js(JS % "try{HUB.sound.playMuteCue();HUB.sound.playMuteCue();var d=HUB.sound._debug();return (d.mutes===undefined&&!document.querySelector('audio'))?'silent':'NOISY';}catch(x){return 'THROW:'+x.message}")
    check("mute cue silent no-op", v == 'silent', v)

    # 8. calculator: no sound chip, no click synth left
    v, _ = js(JS % "try{HUB.calc&&HUB.calc.cardHTML?1:0}catch(e){0}; return 1")
    v, _ = js(JS % "var h='';try{h=HUB.calc.cardHTML()}catch(e){} return h.indexOf('calcSndBtn')<0?'no-chip':'CHIP-STILL-THERE'")
    check("calc header sound chip removed", v == 'no-chip', v)
    v, _ = js(JS % "return (typeof HUB.calc._sndStats==='undefined')?'gone':'STILL-THERE'")
    check("calc _sndStats hook removed", v == 'gone', v)

    # 7. zero console errors
    v, _ = js("window.__huberr.length")
    check("zero console errors", v == 0, v)
finally:
    proc.terminate()

print("\n%d failures" % len(fails))
sys.exit(1 if fails else 0)
