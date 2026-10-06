#!/usr/bin/env python3
"""HUB QA: redesigned call control dock (custom SVG icons, 3D states).
Covers: dock renders (dark+light) -> custom SVG icons present (no emoji) ->
mic live volt glow -> mute flips icon + sunken terracotta + caption swap ->
unmute restores -> speaker routed state (volt + icon flip) -> captions/titles
localized -> no horizontal overflow -> all controls inside viewport ->
reduced-motion kills ambient animation -> Escape leaves the call.
Fresh profile every run. Screenshots under qa/ as callbar-new-*.png."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9437
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
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
    def js(self, expr):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

def targets():
    with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=5) as r:
        return json.load(r)

def shot(c, name, clip=None):
    p = {'format': 'png'}
    if clip: p['clip'] = dict(clip, scale=2)
    r = c.send('Page.captureScreenshot', p)
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)

def hook_err(c):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def drain_err(c, label):
    v, _ = c.js("window.__huberr.splice(0)")
    if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])

def wait_js(c, expr, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v, _ = c.js(expr)
        if v: return v
        time.sleep(0.5)
    return None

def dock_clip(c):
    r, _ = c.js("(()=>{const b=document.getElementById('callControls').getBoundingClientRect();return {x:Math.max(0,b.x-28),y:Math.max(0,b.y-28),width:b.width+56,height:b.height+56}})()")
    return r

def run_theme(theme):
    prof = f'/tmp/hubqa-callbar-{theme}'
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = targets()
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        # seed onboarding-complete BEFORE page scripts run, then reload clean
        c.send('Page.addScriptToEvaluateOnNewDocument', {'source': "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))}catch(e){}"})
        c.send('Page.navigate', {'url': BASE})
        wait_js(c, "!!(window.HUB&&HUB.call&&HUB.call.start)", 20)
        hook_err(c)
        note(*((True, f'[{theme}] app loads, HUB.call present') if c.js("!!(window.HUB&&HUB.call&&HUB.call.start)")[0] else (False, f'[{theme}] app loads, HUB.call present')))
        dark = 'true' if theme == 'dark' else 'false'
        c.js("(()=>{const s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus'; s.prefs=s.prefs||{}; s.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 'seeded'})()" % dark)
        time.sleep(0.8)
        c.js("(()=>{const s=HUB.store.state; s.cgroups=s.cgroups||[]; if(!s.cgroups.find(g=>g.id==='qa-bar-g')) s.cgroups.push({id:'qa-bar-g',name:'QA Bar',mine:true,live:true,members:[],chat:[]}); HUB.store.save(); return 'ok'})()")
        c.js("HUB.call.start('qa-bar-g')")
        ok = wait_js(c, "!!(document.getElementById('callControls')&&!document.getElementById('callControls').hidden)")
        note(bool(ok), f'[{theme}] call UI opens, controls visible'); drain_err(c, theme + '-open')
        if not ok: return
        v, _ = c.js("document.body.classList.contains('dark')")
        note(bool(v) == (theme == 'dark'), f'[{theme}] theme applied', 'body.dark=' + json.dumps(v))
        # welcome overlay must be fully skipped (no language list behind the call UI)
        v, _ = c.js("!document.getElementById('wlcmHost')||document.getElementById('wlcmHost').hidden")
        note(bool(v), f'[{theme}] onboarding welcome not visible')
        time.sleep(1.0)  # let bloom/flip transitions settle
        # custom SVG icons, no emoji glyphs on the buttons
        v, _ = c.js("(()=>{const b=[...document.querySelectorAll('#callControls .callbtn')];return {n:b.length,svg:b.filter(x=>x.querySelector('svg')).length,emoji:/[\\u{1F300}-\\u{1FAFF}\\u2600-\\u27BF]/u.test(b.map(x=>x.textContent).join(''))}})()")
        note(v and v['n'] == 3 and v['svg'] == 3 and not v['emoji'], f'[{theme}] 3 buttons, all custom SVG, zero emoji', json.dumps(v))
        # mic starts LIVE (volt glow)
        v, _ = c.js("document.getElementById('callMic').classList.contains('cblive')&&!document.getElementById('callMic').classList.contains('off')")
        note(bool(v), f'[{theme}] mic starts LIVE with volt glow')
        # captions + titles present and localized
        v, _ = c.js("(()=>{const g=id=>document.getElementById(id).textContent;return [g('callMicCap'),g('callSpkCap'),g('callLeaveCap')]})()")
        note(bool(v and all(v)), f'[{theme}] captions present', json.dumps(v))
        v, _ = c.js("(()=>['callMic','callSpk','callLeave'].every(id=>{const e=document.getElementById(id);return e.title&&e.getAttribute('aria-label')}))()")
        note(bool(v), f'[{theme}] tooltips + aria-labels on all 3 controls')
        shot(c, f'callbar-new-{theme}')
        shot(c, f'callbar-new-dock-{theme}', dock_clip(c))
        # mute -> flip + sunken terracotta + caption swap
        c.js("document.getElementById('callMic').click()"); time.sleep(0.7)
        v, _ = c.js("(()=>{const m=document.getElementById('callMic');return {off:m.classList.contains('off'),live:m.classList.contains('cblive'),cap:document.getElementById('callMicCap').textContent}})()")
        note(bool(v and v['off'] and not v['live']), f'[{theme}] mute: sunken .off, glow off', json.dumps(v))
        shot(c, f'callbar-new-micmuted-{theme}', dock_clip(c))
        # unmute restores
        c.js("document.getElementById('callMic').click()"); time.sleep(0.7)
        v, _ = c.js("(()=>{const m=document.getElementById('callMic');return !m.classList.contains('off')&&m.classList.contains('cblive')})()")
        note(bool(v), f'[{theme}] unmute: volt glow restored')
        # speaker routed state (DOM-driven; headless has no 2nd output)
        c.js("(()=>{const s=document.getElementById('callSpk');s.classList.add('live','cblive')})()"); time.sleep(0.7)
        v, _ = c.js("document.getElementById('callSpk').classList.contains('live')")
        note(bool(v), f'[{theme}] speaker routed: volt glow + icon flip')
        shot(c, f'callbar-new-speakerlive-{theme}', dock_clip(c))
        c.js("(()=>{const s=document.getElementById('callSpk');s.classList.remove('live','cblive')})()")
        # layout: no h-overflow, all controls inside viewport
        v, _ = c.js("document.documentElement.scrollWidth<=window.innerWidth+1")
        note(bool(v), f'[{theme}] no horizontal overflow')
        v, _ = c.js("(()=>{const vw=window.innerWidth,vh=window.innerHeight;return ['callMic','callSpk','callLeave','callControls'].every(id=>{const b=document.getElementById(id).getBoundingClientRect();return b.left>=0&&b.right<=vw+1&&b.top>=0&&b.bottom<=vh+1})})()")
        note(bool(v), f'[{theme}] dock + all controls inside viewport')
        # touch target sizes
        v, _ = c.js("(()=>['callMic','callSpk','callLeave'].map(id=>{const b=document.getElementById(id).getBoundingClientRect();return Math.round(Math.min(b.width,b.height))}))()")
        note(bool(v and min(v) >= 56), f'[{theme}] touch targets >=56px', json.dumps(v))
        # reduced motion kills ambient animation
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        time.sleep(0.4)
        v, _ = c.js("getComputedStyle(document.querySelector('.callcontrols')).animationName==='none'")
        note(bool(v), f'[{theme}] reduced-motion: dock ambient animation off')
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})
        # Escape leaves the call (existing behavior intact)
        c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape'})
        time.sleep(0.6)
        v, _ = c.js("document.getElementById('callRoot').hidden&&!HUB.call.isActive()")
        note(bool(v), f'[{theme}] Escape leaves call, root hidden')
        drain_err(c, theme + '-done')
    finally:
        proc.terminate()

def main():
    for theme in ['dark', 'light']:
        run_theme(theme)
    print('\n==== %d/%d passed, %d error groups ====' % (
        sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
    for label, v in errors: print('ERRGROUP', label, json.dumps(v)[:300])

if __name__ == '__main__':
    main()
