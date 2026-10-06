#!/usr/bin/env python3
"""HUB QA: group voice calls (js/call.js) — loopback demo across 3 tabs.
Covers: start -> demo label -> tiles -> mute/unmute -> admin mutes member ->
promote subadmin -> subadmin mutes -> leave -> Escape (underlying layers
intact) -> 3D speaking glow on/off (real VAD) -> reduced-motion fallback.
Dark + light. Screenshots under qa/. Fresh profile every run."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9431
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-call'
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
def new_tab():
    req = urllib.request.Request(f'http://localhost:{PORT}/json/new?about:blank', method='PUT')
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)
def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
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
def seed_profile(c, name):
    # current onboarding needs a campus pick via custom picker; seed directly
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
    time.sleep(0.8)

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        f'--user-data-dir={PROF}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = targets()
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        cA = CDP(tgt['webSocketDebuggerUrl'])
        for c in [cA]:
            c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        hook_err(cA); time.sleep(2.5); seed_profile(cA, 'QA Ari'); drain_err(cA, 'load')
        # wait for boot before asserting (HUB.call exists before safeboot clears)
        wait_js(cA, "(window.HUB&&HUB.safe&&HUB.safe.isBooted())===true", 20)
        note(*((True, 'app loads, HUB.call present') if cA.js("!!(window.HUB&&HUB.call&&HUB.call.start)")[0] else (False, 'app loads, HUB.call present')))

        # seed group + open group chat + hit the call button
        cA.js("(()=>{const s=HUB.store.state; s.cgroups=s.cgroups||[]; if(!s.cgroups.find(g=>g.id==='qa-call-g')) s.cgroups.push({id:'qa-call-g',name:'QA Runners',emoji:'🏃',mine:true,live:true,members:['Maya Chen','Leo Park'],chat:[]}); HUB.store.save(); return 'ok'})()")
        time.sleep(0.5)
        cA.js("HUB.gchat.open('qa-call-g')"); time.sleep(1.0); drain_err(cA, 'gchat')
        has_btn, _ = cA.js("!!document.getElementById('gcCall')")
        note(bool(has_btn), '📞 call button in group chat header')
        grp_btn, _ = cA.js("(()=>{HUB.gchat.close(); return 'x'})()")
        cA.js("HUB.cgroups.openClub('qa-call-g')"); time.sleep(1.0)
        has_grp_btn, _ = cA.js("!!document.getElementById('cgCallBtn')")
        note(bool(has_grp_btn), '📞 call button on group page')
        # re-assert profile name right before the call (guards against store reload races)
        cA.js("(()=>{HUB.store.state.profile.name='QA Ari'; HUB.store.save(); return HUB.store.myName();})()")
        cA.js("document.getElementById('cgCallBtn').click()")
        # pickKind sheet (added after this harness was written): choose voice call
        pv = wait_js(cA, "!!document.getElementById('callPickVoice')", 8)
        if pv: cA.js("document.getElementById('callPickVoice').click()")
        ok = wait_js(cA, "(()=>{const r=document.getElementById('callRoot'); return r&&!r.hidden&&!!document.querySelector('#callTiles [data-tile=\"self\"]')})()", 15)
        note(bool(ok), 'call UI opens on start (self tile rendered)')
        demo, _ = cA.js("document.getElementById('callDemoLabel').textContent")
        note('signaling worker' in str(demo) and 'Demo' in str(demo), 'demo label honest (no real-call claim)', str(demo)[:70])
        mic_ok, _ = cA.js("(()=>{const d=HUB.call._debug(); return d&&d.hasLocalStream&&d.hasAnalyser})()")
        note(bool(mic_ok), 'mic captured (fake device) + VAD analyser on self')
        time.sleep(2.2)
        timer, _ = cA.js("document.getElementById('callTimer').textContent")
        import re as _re
        note(bool(_re.match(r'^\d+:\d\d', str(timer or ''))), 'call timer ticking', str(timer))
        shot(cA, 'call-ui-dark'); drain_err(cA, 'start')

        # self mute / unmute
        cA.js("document.getElementById('callMic').click()"); time.sleep(0.6)
        m1, _ = cA.js("HUB.call._debug().muted")
        note(bool(m1), 'self mute toggles')
        cA.js("document.getElementById('callMic').click()"); time.sleep(0.6)
        m2, _ = cA.js("HUB.call._debug().muted")
        note(not m2, 'self unmute toggles')

        # ---- tab B joins via the incoming banner ----
        tB = new_tab(); time.sleep(0.5)
        cB = CDP(next(t for t in targets() if t['id'] == tB['id'])['webSocketDebuggerUrl'])
        cB.send('Runtime.enable'); cB.send('Page.enable')
        cB.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(cB); seed_profile(cB, 'Maya Chen')
        cB.js("HUB.store.state.profile.name='Maya Chen'; HUB.gchat.findGroup('qa-call-g').mine=false; HUB.store.save()")
        time.sleep(1.0)
        ban = wait_js(cB, "(()=>{const r=document.getElementById('incallRoot'); return r&&!r.hidden})()", 12)
        note(bool(ban), 'incoming-call UI in second tab (loopback, fullscreen)')
        bsub, _ = cB.js("(()=>{const e=document.getElementById('incTag'); return e?(e.hidden?'':e.textContent):''})()")
        note('Demo' in str(bsub), 'incoming UI labeled demo/local-only', str(bsub)[:60])
        shot(cB, 'call-banner-dark')
        cB.js("document.getElementById('incAnswer').click()")
        pA = wait_js(cA, "(()=>{const d=HUB.call._debug(); return d&&d.peers.length===1?d.peerNames:0})()", 15)
        pB = wait_js(cB, "(()=>{const d=HUB.call._debug(); return d&&d.peers.length===1?d.peerNames:0})()", 15)
        note(bool(pA) and 'Maya Chen' in pA, 'tab A sees real peer (no fakes)', str(pA))
        note(bool(pB) and 'QA Ari' in pB, 'tab B sees real peer (no fakes)', str(pB))
        sig, _ = cA.js("(()=>{const d=HUB.call._debug(); if(!d) return 0; "
                         "const pcs=Object.keys(d.pcs||{}); "
                         "return pcs.length>0?1:(d.sig.offer+d.sig.answer)})()")
        note((sig or 0) >= 1, 'SDP offer/answer exchanged over loopback signaling', 'exchanged=%s' % sig)
        bPid, _ = cB.js("HUB.call._debug().peerId")
        tileB, _ = cA.js("!!document.querySelector('[data-tile=\"%s\"]')" % bPid)
        note(bool(tileB), 'peer tile rendered for Maya in tab A')
        pcs, _ = cA.js("HUB.call._debug().pcs")
        print('   pc states (tab A):', pcs)
        conn = wait_js(cA, "(()=>{const d=HUB.call._debug(); return d&&Object.keys(d.pcs).some(function(k){return d.pcs[k].indexOf('connected')===0})})()", 20)
        print('   media connected within 20s:', bool(conn), '| final:', cA.js("HUB.call._debug().pcs")[0])
        drain_err(cA, 'joinA'); drain_err(cB, 'joinB')

        # ---- 3D speaking glow: real VAD on/off via injected tone ----
        # (fake-device beep is non-deterministic; the tone drives the real
        # analyser -> RMS -> threshold -> hangover -> .speaking pipeline)
        cA.js("HUB.call._debugMicTap(false)")  # deterministic silence baseline
        cA.js("HUB.call._debugTone(true)")
        spk = wait_js(cA, "(()=>{const d=HUB.call._debug(); return d&&d.speaking.self===true})()", 10)
        note(bool(spk), 'VAD: speaking=true at high level (real RMS pipeline)')
        glow, _ = cA.js("(()=>{const el=document.querySelector('[data-tile=\"self\"]'); const cs=getComputedStyle(el); return {cls:el.classList.contains('speaking'), shadow:cs.boxShadow, anim:cs.animationName}})()")
        glow = glow or {}
        note(bool(glow.get('cls')), '3D glow class ON while speaking')
        note('198, 241, 53' in str(glow.get('shadow')), 'volt glow in computed box-shadow', str(glow.get('shadow'))[:80])
        note('callspeak' in str(glow.get('anim')), 'glow pulse animation running', str(glow.get('anim')))
        # remote tile uses the identical VAD-driven class path
        cA.js("HUB.call._debugSpeak('%s',true)" % bPid)
        rg, _ = cA.js("(()=>{const el=document.querySelector('[data-tile=\"%s\"]'); const cs=getComputedStyle(el); return {cls:el.classList.contains('speaking'), volt:cs.boxShadow.indexOf('198, 241, 53')>-1, anim:cs.animationName}})()" % bPid)
        rg = rg or {}
        note(bool(rg.get('cls')) and rg.get('volt') and rg.get('anim') == 'callspeak', 'remote tile 3D glow identical (volt + pulse)', str(rg)[:100])
        cA.js("HUB.call._debugSpeak('%s',false)" % bPid)
        cA.js("HUB.call._debugTone(false)")
        off = wait_js(cA, "(()=>{const d=HUB.call._debug(); return d&&d.speaking.self===false})()", 10)
        note(bool(off), 'VAD: speaking=false after silence (+500ms hangover)')
        cls_off, _ = cA.js("document.querySelector('[data-tile=\"self\"]').classList.contains('speaking')")
        note(not cls_off, '3D glow class fully OFF when silent')
        cA.js("HUB.call._debugMicTap(true)")  # restore mic tap

        # ---- admin mutes member ----
        cA.js("document.querySelector('[data-tile=\"%s\"]').click()" % bPid); time.sleep(0.8)
        sh, _ = cA.js("(()=>{const s=document.getElementById('callSheet'); return s&&!s.hidden&&!!document.getElementById('callAdmMute')})()")
        note(bool(sh), 'admin sheet opens on tile tap (in-call sheet, above overlay)')
        shot(cA, 'call-admin-dark')
        cA.js("document.getElementById('callAdmMute').click()"); time.sleep(1.2)
        mb, _ = cB.js("HUB.call._debug().mutedBy")
        note(mb == 'QA Ari', 'member force-muted by admin (target client)', 'mutedBy=%s' % mb)
        ntc, _ = cB.js("(()=>{const n=document.getElementById('callNotice'); return n&&!n.hidden?n.textContent:''})()")
        note('QA Ari' in str(ntc) and 'Request unmute' in str(ntc), 'muted user sees honest notice + request affordance')
        cap, _ = cA.js("(()=>{const el=document.querySelector('[data-tile=\"%s\"] .mutedby'); return el?el.textContent:''})()" % bPid)
        note('QA Ari' in str(cap), 'tile shows who muted whom', str(cap)[:40])
        # request unmute path (admin receives it)
        cB.js("document.getElementById('callReqUnmute').click()"); time.sleep(1.0)
        drain_err(cB, 'reqUnmute')
        # admin unmutes via sheet
        cA.js("document.querySelector('[data-tile=\"%s\"]').click()" % bPid); time.sleep(0.8)
        cA.js("document.getElementById('callAdmUnmute').click()"); time.sleep(1.2)
        mb2, _ = cB.js("HUB.call._debug().mutedBy")
        note(mb2 is None, 'admin unmute clears mutedBy on target')

        # ---- promote subadmin ----
        cA.js("document.querySelector('[data-tile=\"%s\"]').click()" % bPid); time.sleep(0.8)
        has_pr, _ = cA.js("!!document.getElementById('callAdmPromote')")
        note(bool(has_pr), 'admin sees Make-subadmin control')
        cA.js("document.getElementById('callAdmPromote').click()"); time.sleep(1.5)
        role_b, _ = cB.js("HUB.call._debug().role")
        admins, _ = cA.js("HUB.gchat.findGroup('qa-call-g').callAdmins")
        note(role_b == 'subadmin' and 'Maya Chen' in (admins or []), 'subadmin promoted + persisted g.callAdmins', '%s %s' % (role_b, admins))

        # ---- light-mode admin sheet shot ----
        cA.js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.8)
        cA.js("document.querySelector('[data-tile=\"%s\"]').click()" % bPid); time.sleep(0.8)
        shot(cA, 'call-admin-light')
        cA.js("document.getElementById('callSheet').hidden=true")
        cA.js("HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.5)

        # ---- tab C joins; subadmin mutes ----
        tC = new_tab(); time.sleep(0.5)
        cC = CDP(next(t for t in targets() if t['id'] == tC['id'])['webSocketDebuggerUrl'])
        cC.send('Runtime.enable'); cC.send('Page.enable')
        cC.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(cC); seed_profile(cC, 'Leo Park')
        cC.js("HUB.store.state.profile.name='Leo Park'; HUB.gchat.findGroup('qa-call-g').mine=false; HUB.store.save()")
        time.sleep(1.0)
        banC = wait_js(cC, "(()=>{const r=document.getElementById('incallRoot'); return r&&!r.hidden})()", 12)
        note(bool(banC), 'incoming UI in third tab')
        cC.js("document.getElementById('incAnswer').click()")
        cPid, _ = cC.js("HUB.call._debug().peerId")
        okC = wait_js(cB, "HUB.call._debug().peers.length===2", 15)
        note(bool(okC), 'subadmin tab sees both peers')
        # subadmin (tab B) mutes Leo; sheet must NOT offer promote (subadmin can't)
        cB.js("document.querySelector('[data-tile=\"%s\"]').click()" % cPid); time.sleep(0.8)
        shB, _ = cB.js("(()=>{const s=document.getElementById('callSheet'); return s&&!s.hidden&&!!document.getElementById('callAdmMute')&&!document.getElementById('callAdmPromote')})()")
        note(bool(shB), 'subadmin gets mute control, no promote control')
        cB.js("document.getElementById('callAdmMute').click()"); time.sleep(1.2)
        mbC, _ = cC.js("HUB.call._debug().mutedBy")
        note(mbC == 'Maya Chen', 'subadmin mute enforced on target', 'mutedBy=%s' % mbC)
        # speaker toggle: honest path in headless (no setSinkId) -> toast, no crash
        cB.js("document.getElementById('callSheet').hidden=true; document.getElementById('callSpk').click()"); time.sleep(0.8)
        drain_err(cB, 'speaker')

        # ---- leave + Escape layering ----
        cC.js("document.getElementById('callLeave').click()"); time.sleep(1.5)
        gone, _ = cC.js("HUB.call._debug()===null&&document.getElementById('callRoot').hidden")
        note(bool(gone), 'leave tears down session + hides UI')
        back2, _ = cA.js("(()=>{const d=HUB.call._debug(); return d&&d.peers.length===1})()")
        note(bool(back2), 'remaining tabs drop the departed peer')
        # Escape with call UI open: must leave the call, NOT close the group page beneath
        cA.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        cA.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        time.sleep(1.0)
        esc_ok, _ = cA.js("(()=>{const r=document.getElementById('callRoot'); const g=document.getElementById('view-groups'); return r.hidden&&!HUB.call.isActive()&&g&&g.textContent.indexOf('QA Runners')>-1})()")
        note(bool(esc_ok), 'Escape leaves call, underlying group page stays open')

        # ---- mic denied -> honest error + Retry ----
        cA.js("window.__origGUM=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices); navigator.mediaDevices.getUserMedia=function(){return Promise.reject(new DOMException('denied','NotAllowedError'))}")
        cA.js("document.getElementById('cgCallBtn').click()")
        pv2 = wait_js(cA, "!!document.getElementById('callPickVoice')", 8)
        if pv2: cA.js("document.getElementById('callPickVoice').click()")
        denied = wait_js(cA, "(()=>{const e=document.getElementById('callError'); return e&&!e.hidden&&!!document.getElementById('callRetry')})()", 12)
        note(bool(denied), 'mic denied shows honest error + Retry (no fake call)')
        shot(cA, 'call-micdenied-dark')
        cA.js("navigator.mediaDevices.getUserMedia=window.__origGUM")
        cA.js("document.getElementById('callRetry').click()")
        retry_ok = wait_js(cA, "(()=>{const r=document.getElementById('callRoot'); return r&&!r.hidden&&!!document.querySelector('#callTiles [data-tile=\"self\"]')})()", 15)
        note(bool(retry_ok), 'Retry re-acquires mic and joins call')
        cA.js("document.getElementById('callLeave').click()"); time.sleep(1.0)
        drain_err(cA, 'micdenied')

        # ---- light-mode call UI shot (tab B still in call) ----
        cB.js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.8)
        shot(cB, 'call-ui-light')
        lbl, _ = cB.js("document.getElementById('callDemoLabel').textContent")
        note('Demo' in str(lbl), 'demo label present in light mode too')

        # ---- prefers-reduced-motion: static ring, no pulse ----
        cB.js("document.getElementById('callMic').click()"); time.sleep(1.5)  # silence -> VAD stable
        cB.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        cB.js("HUB.applyTheme()"); time.sleep(0.6)
        f1, _ = cB.js("HUB.call._debugSpeak('self',true)")
        rm, _ = cB.js("(()=>{const el=document.querySelector('[data-tile=\"self\"]'); return getComputedStyle(el).animationName})()")
        note(bool(f1) and rm == 'none', 'reduced-motion: static ring, pulse animation off', 'animationName=%s' % rm)
        cB.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})
        cB.js("HUB.applyTheme()"); time.sleep(0.6)
        cB.js("HUB.call._debugSpeak('self',true)")
        rm2, _ = cB.js("(()=>{const el=document.querySelector('[data-tile=\"self\"]'); return getComputedStyle(el).animationName})()")
        note('callspeak' in str(rm2), 'full motion: 3D pulse restored', 'animationName=%s' % rm2)
        cB.js("document.getElementById('callLeave').click()"); time.sleep(1.0)

        for c, lab in [(cA, 'A'), (cB, 'B'), (cC, 'C')]: drain_err(c, 'final-' + lab)
        print('\n=== console errors ==='); print('NONE' if not errors else errors)
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        for c in [cA, cB, cC]:
            try: c.ws.close()
            except Exception: pass
    finally:
        proc.terminate()
if __name__ == '__main__': main()
