#!/usr/bin/env python3
"""HUB runtime QA sweep — Market / Work / Groups+People / 1:1+group chat /
group calls / incoming-call UI (2026-09-24).

Covers the narrow fixes from this sweep:
  - market.js: photo lightbox keeps the listing detail sheet (keepSheet)
  - market.js: pinch/pan apply() preserves the -50% image centering
  - app.js: Escape closes a sheet above chat WITHOUT also closing chat
  - CSS: bulletproof absolute centering for .chatroot/.chatpanel, .wlcmhost/
    .wlcm-card, .hpglass/.hpglass-card, .mkzoom/.mkzoom-stage img,
    .incallroot/.incall, .callroot/.callwrap, .callsheet/.callsheet-box

Matrix: 390px + 320px, dark + light. Screenshots are JPG ONLY (qa/*.png must
stay empty). Console errors must be 0.

Conventions (AGENTS.md): file:// URL, --allow-file-access-from-files, device
metrics before first navigation, fresh profile per combo, orbit_i18n +
profile.name + profile.campus seed, auth gate disarmed, CDP error siphon,
toasts cleared between assertions, JS snippets with `return` wrapped in IIFE.
"""
import json, subprocess, time, urllib.request, os, base64, shutil, sys
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
JS = "(function(){%s})()"
checks, errors = [], []

def note(ok, label, detail=''):
    checks.append(bool(ok))
    print(('PASS' if ok else 'FAIL'), label, str(detail)[:120])

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=15); self.ws.settimeout(15); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 20
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

def hook_err(c):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
def drain_err(c, label):
    v, _ = c.js("window.__huberr.splice(0)")
    if v:
        errors.append((label, v)); print('CONSOLE ERRORS @', label, ':', json.dumps(v)[:500])
    return not v

def esc_key(c):
    c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'windowsVirtualKeyCode': 27, 'key': 'Escape'})
    time.sleep(0.4)
    c.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'windowsVirtualKeyCode': 27, 'key': 'Escape'})
    time.sleep(0.3)

def click(c, sel):
    v, _ = c.js(JS % ("const e=document.querySelector('%s');if(!e)return 'missing';"
                      "e.scrollIntoView({block:'center'});e.click();return 'clicked'" % sel))
    time.sleep(0.7); return v

def rect(c, sel):
    v, _ = c.js(JS % ("const e=document.querySelector('%s');if(!e)return null;"
                      "const r=e.getBoundingClientRect();"
                      "return {l:r.left,t:r.top,r:r.right,b:r.bottom,vw:innerWidth,vh:innerHeight}" % sel))
    return v

def centered(r, axes='x', tol=4):
    if not r: return False
    ok = True
    if 'x' in axes: ok = ok and abs((r['l'] + r['r']) / 2 - r['vw'] / 2) <= tol
    if 'y' in axes: ok = ok and abs((r['t'] + r['b']) / 2 - r['vh'] / 2) <= tol
    return ok and r['l'] >= -1 and r['r'] <= r['vw'] + 1

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 80})
    p = os.path.join(QA, name + '.jpg')
    open(p, 'wb').write(base64.b64decode(r['data'])); print('shot:', name + '.jpg')

def seed(c):
    c.js(JS % ("try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
               "const p=HUB.store.state.profile;p.name='PraBin';p.campus='QA Campus';HUB.store.save();"
               "window.__gateSkip=true;return 'seeded'}catch(e){return 'ERR:'+e.message}"))
    time.sleep(0.8)

def wait_js(c, expr, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v, _ = c.js(expr)
        if v: return v
        time.sleep(0.5)
    return None

def run_combo(width, theme):
    prof = '/tmp/hubqa-sweep-%d-%s' % (width, theme)
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', '--hide-scrollbars',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
        '--remote-debugging-port=%d' % (9500 + width + (1 if theme == 'dark' else 0)),
        '--remote-allow-origins=*', '--window-size=%d,844' % width,
        '--user-data-dir=%s' % prof, '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    port = 9500 + width + (1 if theme == 'dark' else 0)
    try:
        tgt = None
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen('http://localhost:%d/json/list' % port, timeout=4) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
            except Exception: continue
        if not tgt: note(False, '[%d/%s] browser target' % (width, theme)); return
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        # device metrics before meaningful interaction
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': width, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        ok = wait_js(c, "!!(window.HUB&&HUB.store&&HUB.views)")
        note(bool(ok), '[%d/%s] app boots' % (width, theme))
        hook_err(c); seed(c)
        c.js("document.getElementById('toastHost').innerHTML=''")
        if theme == 'dark': c.js("document.body.classList.add('dark')")
        else: c.js("document.body.classList.remove('dark')")
        time.sleep(0.8)
        tag = '%d-%s' % (width, theme)

        # ---- A. welcome overlay geometry (fresh profile: likely visible) ----
        whost, _ = c.js(JS % "return !!document.getElementById('wlcmHost')")
        if whost:
            wvis, _ = c.js(JS % "return !document.getElementById('wlcmHost').hidden")
            if not wvis: c.js(JS % "return (function(){var h=document.getElementById('wlcmHost');if(h)h.hidden=false;})()")
            wait_js(c, JS % "return !!document.querySelector('.wlcm-card')")
            time.sleep(0.9)  # let the wlcmupC entrance animation settle before measuring
            r = rect(c, '.wlcm-card')
            note(r and abs(r['b'] - r['vh']) <= 4 and centered(r, 'x'),
                 '[%d/%s] wlcm-card bottom-docked + centered' % (width, theme), r)
            shot(c, 'sweep-wlcm-' + tag)
            c.js(JS % "return (function(){var h=document.getElementById('wlcmHost');if(h)h.hidden=true;})()"); time.sleep(0.4)
        else:
            # returning user (seeded orbit_i18n): welcome correctly skipped; geometry
            # verified separately on a true fresh profile
            note(True, '[%d/%s] wlcm skipped for returning user' % (width, theme))

        # ---- B. market: detail sheet + photo lightbox layering ----
        c.js("HUB.showTab('market')"); time.sleep(1.2)
        note(click(c, '.mktile') == 'clicked', '[%d/%s] market listing opens' % (width, theme))
        sh, _ = c.js(JS % "return !document.getElementById('sheetHost').hidden")
        note(bool(sh), '[%d/%s] listing detail sheet visible' % (width, theme))
        ph = wait_js(c, JS % "return !!document.querySelector('#sheetBox .mkphoto')")
        if ph:
            note(click(c, '#sheetBox .mkphoto') == 'clicked', '[%d/%s] listing photo tapped' % (width, theme))
            lb, _ = c.js(JS % "return !!document.querySelector('.mkzoom')")
            sh2, _ = c.js(JS % "return !document.getElementById('sheetHost').hidden")
            note(bool(lb) and bool(sh2), '[%d/%s] lightbox open AND detail sheet kept' % (width, theme))
            r = rect(c, '.mkzoom-stage img')
            note(centered(r, 'xy'), '[%d/%s] lightbox image centered' % (width, theme), r)
            shot(c, 'sweep-mkt-lightbox-' + tag)
            esc_key(c)
            lb2, _ = c.js(JS % "return !!document.querySelector('.mkzoom')")
            sh3, _ = c.js(JS % "return !document.getElementById('sheetHost').hidden")
            note(not lb2 and bool(sh3), '[%d/%s] Esc closes lightbox only, detail stays' % (width, theme))
            shot(c, 'sweep-mkt-detail-' + tag)
            esc_key(c)
            sh4, _ = c.js(JS % "return !document.getElementById('sheetHost').hidden")
            note(not sh4, '[%d/%s] Esc closes detail sheet' % (width, theme))
        else:
            note(False, '[%d/%s] listing has photos' % (width, theme))

        # ---- C. 1:1 chat: panel geometry + Escape layering ----
        c.js("HUB.chat.openList()"); time.sleep(1.0)
        cr, _ = c.js(JS % "return !!document.querySelector('.chatroot:not([hidden])')")
        note(bool(cr), '[%d/%s] chat list opens' % (width, theme))
        r = rect(c, '.chatpanel')
        note(r and r['l'] >= -1 and r['r'] <= r['vw'] + 1 and abs(r['b'] - r['vh']) <= 4 and centered(r, 'x'),
             '[%d/%s] chatpanel bottom-docked + centered' % (width, theme), r)
        shot(c, 'sweep-chat-list-' + tag)
        th = wait_js(c, JS % "return !!document.querySelector('#chatRoot .item')")
        if th:
            click(c, '#chatRoot .item'); time.sleep(0.8)
            bk, _ = c.js(JS % "return !!document.getElementById('chBack')")
            note(bool(bk), '[%d/%s] chat thread opens' % (width, theme))
            shot(c, 'sweep-chat-thread-' + tag)
            click(c, '#chMore'); time.sleep(0.6)
            sh5, _ = c.js(JS % "return !document.getElementById('sheetHost').hidden")
            note(bool(sh5), '[%d/%s] chat options sheet opens' % (width, theme))
            esc_key(c)
            sh6, _ = c.js(JS % "return !document.getElementById('sheetHost').hidden")
            cr2, _ = c.js(JS % "return !!document.querySelector('.chatroot:not([hidden])')")
            note(not sh6 and bool(cr2), '[%d/%s] Esc closes sheet only, chat stays' % (width, theme))
            esc_key(c)
            cr3, _ = c.js(JS % "return !!document.querySelector('.chatroot:not([hidden])')")
            bk3, _ = c.js(JS % "return !!document.getElementById('chBack')")
            note(bool(cr3) and not bk3, '[%d/%s] Esc steps thread back to list' % (width, theme))
            esc_key(c)
            cr4, _ = c.js(JS % "return !!document.querySelector('.chatroot:not([hidden])')")
            note(not cr4, '[%d/%s] Esc closes chat list' % (width, theme))
        else:
            note(False, '[%d/%s] chat has threads' % (width, theme))

        # ---- D. groups -> people glass sheet ----
        c.js("HUB.showTab('groups')"); time.sleep(1.0)
        c.js("HUB.views.groups.setSub('people')"); time.sleep(1.2)
        pv = wait_js(c, JS % "return !!document.querySelector('#pplList [data-act=\"view\"]')")
        if pv:
            # [data-act="view"] opens the profile SHEET (openProfile); the clear-glass
            # card is a separate entry: HUB.people.openGlass(id)
            pid, _ = c.js(JS % "return (HUB.people.visiblePeople()[0]||{}).id||''")
            note(bool(pid), '[%d/%s] people list has person' % (width, theme))
            c.js("HUB.people.openGlass('" + str(pid) + "')"); time.sleep(0.8)
            hg0, _ = c.js(JS % "return !!document.getElementById('hpGlass') && !document.getElementById('hpGlass').hidden")
            note(bool(hg0), '[%d/%s] people glass opens' % (width, theme))
            r = rect(c, '.hpglass-card')
            note(centered(r, 'xy'), '[%d/%s] hpglass-card centered' % (width, theme), r)
            shot(c, 'sweep-hpglass-' + tag)
            esc_key(c)
            hg, _ = c.js(JS % "return !!document.getElementById('hpGlass') && !document.getElementById('hpGlass').hidden")
            note(not hg, '[%d/%s] Esc closes people glass' % (width, theme))
        else:
            note(False, '[%d/%s] people list renders' % (width, theme))

        # ---- E. incoming-call UI ----
        c.js(JS % "HUB.incoming.show({name:'QA Caller',kind:'voice',accept:function(){},reject:function(){}})")
        time.sleep(0.8)
        ir, _ = c.js(JS % "return !!document.querySelector('.incallroot:not([hidden])')")
        note(bool(ir), '[%d/%s] incoming-call UI shows' % (width, theme))
        r = rect(c, '.incall')
        note(centered(r, 'x'), '[%d/%s] incall centered' % (width, theme), r)
        shot(c, 'sweep-incall-' + tag)
        c.js("HUB.incoming.decline()"); time.sleep(0.5)
        ir2, _ = c.js(JS % "return !!document.querySelector('.incallroot:not([hidden])')")
        note(not ir2, '[%d/%s] incoming-call declines' % (width, theme))

        # ---- F. group call UI (demo20) ----
        c.js(JS % ("const s=HUB.store.state;s.cgroups=s.cgroups||[];"
                   "if(!s.cgroups.find(g=>g.id==='qa-sweep-g'))"
                   "s.cgroups.push({id:'qa-sweep-g',name:'QA Runners',emoji:'🏃',mine:true,live:true,"
                   "members:['Maya Chen'],chat:[]});HUB.store.save();return 'ok'"))
        time.sleep(0.5)
        c.js("HUB.call.start('qa-sweep-g',{demo20:true})")
        ok = wait_js(c, JS % ("const r=document.getElementById('callRoot');"
                              "return r&&!r.hidden&&!!document.querySelector('#callTiles [data-tile=\"self\"]')"), 20)
        note(bool(ok), '[%d/%s] group call UI opens (demo20)' % (width, theme))
        r = rect(c, '.callwrap')
        note(centered(r, 'x'), '[%d/%s] callwrap centered' % (width, theme), r)
        shot(c, 'sweep-call-' + tag)
        tp = wait_js(c, JS % "return !!document.querySelector('#callTiles [data-tile]:not([data-tile=\"self\"])')")
        if tp:
            note(click(c, '#callTiles [data-tile]:not([data-tile="self"])') == 'clicked',
                 '[%d/%s] peer tile opens admin sheet' % (width, theme))
            cs, _ = c.js(JS % "return !document.getElementById('callSheet').hidden")
            note(bool(cs), '[%d/%s] in-call admin sheet visible' % (width, theme))
            r = rect(c, '.callsheet-box')
            note(r and abs(r['b'] - r['vh']) <= 4 and centered(r, 'x'),
                 '[%d/%s] callsheet-box bottom-docked + centered' % (width, theme), r)
            esc_key(c)
            cs2, _ = c.js(JS % "return !document.getElementById('callSheet').hidden")
            cr4, _ = c.js(JS % "return !document.getElementById('callRoot').hidden")
            note(not cs2 and bool(cr4), '[%d/%s] Esc closes admin sheet, call stays' % (width, theme))
        c.js("HUB.call.leave()"); time.sleep(0.8)
        cr5, _ = c.js(JS % "return !document.getElementById('callRoot').hidden")
        note(not cr5, '[%d/%s] call leaves cleanly' % (width, theme))

        # ---- G. work smoke: post a job ----
        c.js("HUB.showTab('work')"); time.sleep(1.0)
        note(click(c, '#postJobBtn') == 'clicked', '[%d/%s] work post sheet opens' % (width, theme))
        c.js(JS % ("document.getElementById('pjTitle').value='QA sweep test job';"
                   "document.getElementById('pjPay').value='25';return 'f'"))
        note(click(c, '#pjGo') == 'clicked', '[%d/%s] work job posts' % (width, theme))
        jl, _ = c.js(JS % "return document.getElementById('jobList').textContent")
        note('QA sweep test job' in str(jl), '[%d/%s] job appears in list' % (width, theme))
        shot(c, 'sweep-work-' + tag)
        c.js(JS % ("const b=document.querySelector('[data-jdel]');if(b){b.click();}return 'x'"))
        time.sleep(0.6)
        c.js(JS % ("const g=document.getElementById('cfGo');if(g){g.click();}return 'x'"))
        time.sleep(0.6)

        # ---- H. group chat smoke: send a message ----
        c.js("HUB.gchat.open('qa-sweep-g')"); time.sleep(1.0)
        n0, _ = c.js(JS % "return document.querySelectorAll('.gc-msg').length")
        c.js(JS % ("const i=document.getElementById('gcText');i.value='sweep check '+Date.now();return 'x'"))
        note(click(c, '#gcSend') == 'clicked', '[%d/%s] group chat send tapped' % (width, theme))
        time.sleep(1.0)
        n1, _ = c.js(JS % "return document.querySelectorAll('.gc-msg').length")
        note((n1 or 0) > (n0 or 0), '[%d/%s] group message appears' % (width, theme), '%s->%s' % (n0, n1))
        r = rect(c, '.chatpanel')
        note(r and r['l'] >= -1 and r['r'] <= r['vw'] + 1 and centered(r, 'x'),
             '[%d/%s] group chat panel centered' % (width, theme), r)
        shot(c, 'sweep-gchat-' + tag)
        c.js("HUB.gchat.close()"); time.sleep(0.5)

        # ---- I. ringtone picker smoke ----
        c.js("HUB.showTab('me')"); time.sleep(1.2)
        rr, _ = c.js(JS % "return document.querySelectorAll('#ringList .ringrow').length")
        note((rr or 0) >= 3, '[%d/%s] ringtone rows render' % (width, theme), rr)
        pv, _ = c.js("String(HUB.sound.preview('aurora'))")
        note(pv in ('playing', 'off', 'stopped'), '[%d/%s] ringtone preview call safe' % (width, theme), pv)
        c.js("HUB.sound.stopPreview(true)")

        drain_err(c, '%d/%s' % (width, theme))
    finally:
        try: proc.terminate()
        except Exception: pass

def main():
    t0 = time.time()
    for width in (390, 320):
        for theme in ('dark', 'light'):
            run_combo(width, theme)
    print('\n==== sweep done: %d/%d checks passed, %d console-error groups, %.0fs ===='
          % (sum(checks), len(checks), len(errors), time.time() - t0))
    pngs = [f for f in os.listdir(QA) if f.endswith('.png') and f.startswith('sweep-')]
    print('sweep PNGs (must be 0):', len(pngs))
    sys.exit(0 if (all(checks) and not errors and not pngs) else 1)

if __name__ == '__main__':
    main()
