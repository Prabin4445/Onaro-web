#!/usr/bin/env python3
"""HUB QA: speaker-mute toggle + raise-hand + loudspeaker/earpiece route switch.
Fresh profile, 3 tabs (A=admin, B=member, C=member) over loopback signaling.
Dark + light at 390x844. Screenshots under qa/."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9432
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-call2'
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
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
    time.sleep(0.8)
def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
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
        cA.send('Runtime.enable'); cA.send('Page.enable'); cA.send('Log.enable')
        hook_err(cA); time.sleep(2.5); seed_profile(cA, 'QA Ari'); drain_err(cA, 'load')
        cA.js("(()=>{const s=HUB.store.state; s.cgroups=s.cgroups||[]; if(!s.cgroups.find(g=>g.id==='qa-sh-g')) s.cgroups.push({id:'qa-sh-g',name:'QA Speakers',emoji:'🔊',mine:true,live:true,members:['Maya Chen','Leo Park'],chat:[]}); HUB.store.save(); return 'ok'})()")
        time.sleep(0.5)
        cA.js("HUB.cgroups.openClub('qa-sh-g')"); time.sleep(1.0)
        cA.js("document.getElementById('cgCallBtn').click()")
        pk = wait_js(cA, "!!document.getElementById('callPickVoice')", 8)  # call-kind picker
        if pk: cA.js("document.getElementById('callPickVoice').click()")
        ok = wait_js(cA, "(()=>{const r=document.getElementById('callRoot'); return r&&!r.hidden&&!!document.querySelector('#callTiles [data-tile=\"self\"]')})()", 15)
        note(bool(ok), 'call UI opens (self tile)')
        mic_ok, _ = cA.js("(()=>{const d=HUB.call._debug(); return d&&d.hasLocalStream})()")
        note(bool(mic_ok), 'mic captured on fake device')

        # ---- speaker mute: initial state ----
        s0, _ = cA.js("(()=>{const d=HUB.call._debug(); const spk=document.getElementById('callSpk'); return {m:d.speakerMuted, off:spk.classList.contains('off'), cap:document.getElementById('callSpkCap').textContent}})()")
        s0 = s0 or {}
        note(s0.get('m') is False and not s0.get('off') and s0.get('cap') == 'Speaker', 'speaker starts ON (audio flowing, caption Speaker)', str(s0))

        cB = None
        tB = new_tab(); time.sleep(0.5)
        cB = CDP(next(x for x in targets() if x['id'] == tB['id'])['webSocketDebuggerUrl'])
        cB.send('Runtime.enable'); cB.send('Page.enable')
        cB.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(cB); seed_profile(cB, 'Maya Chen')
        cB.js("HUB.store.state.profile.name='Maya Chen'; HUB.gchat.findGroup('qa-sh-g').mine=false; HUB.store.save()")
        time.sleep(1.0)
        ban = wait_js(cB, "(()=>{const b=document.getElementById('callBanner'); return b&&!b.hidden})()", 12)
        note(bool(ban), 'Maya sees incoming banner')
        cB.js("document.getElementById('callBannerJoin').click()")
        bPid, _ = cB.js("HUB.call._debug().peerId")
        aPid, _ = cA.js("HUB.call._debug().peerId")
        au = wait_js(cA, "(()=>{const a=document.getElementById('callAu_%s'); return a?{muted:a.muted}:0})()" % bPid, 15)
        note(bool(au) and au.get('muted') is False, 'remote audio element attached, unmuted initially', str(au))

        # ---- tap speaker: REAL mute of remote audio ----
        cA.js("document.getElementById('callSpk').click()"); time.sleep(0.7)
        s1, _ = cA.js("(()=>{const d=HUB.call._debug(); const els=[...document.querySelectorAll('#callAudio audio')]; const spk=document.getElementById('callSpk'); return {m:d.speakerMuted, n:els.length, allMuted:els.every(a=>a.muted), off:spk.classList.contains('off'), cap:document.getElementById('callSpkCap').textContent, slash:document.querySelector('#callSpk .cb-back').innerHTML.indexOf('M4 4')>-1}})()")
        s1 = s1 or {}
        note(s1.get('m') is True, 'speakerMuted=true after tap', str(s1))
        note(s1.get('n', 0) >= 1 and s1.get('allMuted') is True, 'ALL remote <audio> elements really muted', str(s1))
        note(s1.get('off') is True and s1.get('cap') == 'Speaker off' and s1.get('slash') is True, 'OFF state unmistakable: .off + "Speaker off" + slash icon', str(s1))
        shot(cA, 'call-speakeroff-dark')
        # light-mode OFF screenshot
        cA.js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.8)
        shot(cA, 'call-speakeroff-light')
        cA.js("HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.5)

        # ---- tap again: restore ----
        cA.js("document.getElementById('callSpk').click()"); time.sleep(0.7)
        s2, _ = cA.js("(()=>{const d=HUB.call._debug(); const els=[...document.querySelectorAll('#callAudio audio')]; const spk=document.getElementById('callSpk'); return {m:d.speakerMuted, allMuted:els.every(a=>a.muted), off:spk.classList.contains('off'), cap:document.getElementById('callSpkCap').textContent}})()")
        s2 = s2 or {}
        note(s2.get('m') is False and s2.get('allMuted') is False and not s2.get('off') and s2.get('cap') == 'Speaker', 'second tap restores audio + normal state', str(s2))

        # ---- late joiner inherits mute ----
        cA.js("document.getElementById('callSpk').click()"); time.sleep(0.5)  # mute ON
        tC = new_tab(); time.sleep(0.5)
        cC = CDP(next(x for x in targets() if x['id'] == tC['id'])['webSocketDebuggerUrl'])
        cC.send('Runtime.enable'); cC.send('Page.enable')
        cC.send('Page.navigate', {'url': BASE}); time.sleep(3.0)
        hook_err(cC); seed_profile(cC, 'Leo Park')
        cC.js("HUB.store.state.profile.name='Leo Park'; HUB.gchat.findGroup('qa-sh-g').mine=false; HUB.store.save()")
        time.sleep(1.0)
        wait_js(cC, "(()=>{const b=document.getElementById('callBanner'); return b&&!b.hidden})()", 12)
        cC.js("document.getElementById('callBannerJoin').click()")
        cPid, _ = cC.js("HUB.call._debug().peerId")
        auC = wait_js(cA, "(()=>{const a=document.getElementById('callAu_%s'); return a?{muted:a.muted}:0})()" % cPid, 15)
        note(bool(auC) and auC.get('muted') is True, 'late joiner audio inherits muted state', str(auC))
        cA.js("document.getElementById('callSpk').click()"); time.sleep(0.5)  # mute OFF again
        drain_err(cA, 'speaker'); drain_err(cB, 'speaker'); drain_err(cC, 'speaker')

        # ---- raise hand: self ----
        cA.js("document.getElementById('callHand').click()"); time.sleep(0.8)
        h1, _ = cA.js("(()=>{const d=HUB.call._debug(); const hb=document.querySelector('[data-tile=\"self\"] .handbadge'); const hand=document.getElementById('callHand'); return {hr:d.handRaised, glow:hand.classList.contains('cblive'), cap:document.getElementById('callHandCap').textContent, badge:!!hb, txt:hb?hb.textContent:''}})()")
        h1 = h1 or {}
        note(h1.get('hr') is True, 'handRaised=true after tap', str(h1))
        note(h1.get('glow') is True and h1.get('cap') == 'Lower hand', 'hand dome volt glow + caption flips to Lower hand', str(h1))
        note(h1.get('badge') is True and 'Hand raised' in str(h1.get('txt')), 'self tile shows raised-hand badge', str(h1))
        shot(cA, 'call-hand-dark')
        # everyone else sees it
        hbB, _ = cB.js("(()=>{const hb=document.querySelector('[data-tile=\"%s\"] .handbadge'); return hb?hb.textContent:''})()" % aPid)
        note('Hand raised' in str(hbB), 'peer tab sees the raised-hand badge', str(hbB)[:40])
        hbC, _ = cC.js("!!document.querySelector('[data-tile=\"%s\"] .handbadge')" % aPid)
        note(bool(hbC), 'third tab sees the badge too')
        cA.js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.8)
        shot(cA, 'call-hand-light')
        cA.js("HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.5)
        # lower own hand
        cA.js("document.getElementById('callHand').click()"); time.sleep(0.8)
        h2, _ = cA.js("(()=>{const d=HUB.call._debug(); return {hr:d.handRaised, badge:!!document.querySelector('[data-tile=\"self\"] .handbadge')}})()")
        note((h2 or {}).get('hr') is False and not (h2 or {}).get('badge'), 'tap again lowers own hand, badge gone')
        hbB2, _ = cB.js("!!document.querySelector('[data-tile=\"%s\"] .handbadge')" % aPid)
        note(not hbB2, 'badge cleared on peer tab')
        drain_err(cA, 'hand'); drain_err(cB, 'hand'); drain_err(cC, 'hand')

        # ---- admin flow: mute member, member raises hand, Let speak ----
        cA.js("document.querySelector('[data-tile=\"%s\"]').click()" % bPid); time.sleep(0.8)
        cA.js("document.getElementById('callAdmMute').click()"); time.sleep(1.2)
        mb, _ = cB.js("HUB.call._debug().mutedBy")
        note(mb == 'QA Ari', 'member muted by admin first', 'mutedBy=%s' % mb)
        cB.js("document.getElementById('callHand').click()"); time.sleep(1.0)
        hrB, _ = cB.js("HUB.call._debug().handRaised")
        note(bool(hrB), 'muted member raises hand')
        cA.js("document.querySelector('[data-tile=\"%s\"]').click()" % bPid); time.sleep(0.8)
        ls, _ = cA.js("(()=>{const b=document.getElementById('callAdmLetSpeak'); return b?b.textContent:''})()")
        note(ls == 'Let speak', 'admin sees "Let speak" for raised hand', repr(ls))
        shot(cA, 'call-letspeak-dark')
        cA.js("document.getElementById('callAdmLetSpeak').click()"); time.sleep(1.5)
        fin, _ = cB.js("(()=>{const d=HUB.call._debug(); return {muted:d.muted, mutedBy:d.mutedBy, hr:d.handRaised}})()")
        fin = fin or {}
        note(fin.get('muted') is False and fin.get('mutedBy') is None, 'Let speak unmuted the member', str(fin))
        note(fin.get('hr') is False, 'Let speak lowered the hand on target', str(fin))
        goneA, _ = cA.js("!!document.querySelector('[data-tile=\"%s\"] .handbadge')" % bPid)
        goneC, _ = cC.js("!!document.querySelector('[data-tile=\"%s\"] .handbadge')" % bPid)
        note(not goneA and not goneC, 'badge cleared on all views after Let speak')
        drain_err(cA, 'letspeak'); drain_err(cB, 'letspeak'); drain_err(cC, 'letspeak')

        # ---- subadmin flow: promote Leo, Maya raises hand, Leo lets her speak ----
        cA.js("document.querySelector('[data-tile=\"%s\"]').click()" % cPid); time.sleep(0.8)
        pr, _ = cA.js("!!document.getElementById('callAdmPromote')")
        note(bool(pr), 'admin sees promote control for Leo')
        cA.js("document.getElementById('callAdmPromote').click()"); time.sleep(1.5)
        roleC, _ = cC.js("HUB.call._debug().role")
        note(roleC == 'subadmin', 'Leo promoted to subadmin', str(roleC))
        cB.js("document.getElementById('callHand').click()"); time.sleep(1.0)
        cC.js("document.querySelector('[data-tile=\"%s\"]').click()" % bPid); time.sleep(0.8)
        sub, _ = cC.js("(()=>{const s=document.getElementById('callSheet'); return {ls:!!document.getElementById('callAdmLetSpeak'), pr:!!document.getElementById('callAdmPromote'), open:s&&!s.hidden}})()")
        sub = sub or {}
        note(sub.get('open') and sub.get('ls') and not sub.get('pr'), 'subadmin sees Let speak, no promote control', str(sub))
        cC.js("document.getElementById('callAdmLetSpeak').click()"); time.sleep(1.5)
        hrB2, _ = cB.js("HUB.call._debug().handRaised")
        note(hrB2 is False, 'subadmin Let speak lowers hand everywhere', 'hr=%s' % hrB2)
        goneA2, _ = cA.js("!!document.querySelector('[data-tile=\"%s\"] .handbadge')" % bPid)
        note(not goneA2, 'badge cleared on admin view too')
        drain_err(cA, 'subadmin'); drain_err(cB, 'subadmin'); drain_err(cC, 'subadmin')

        # ---- route switch: honest handling ----
        cap_info, _ = cA.js("(()=>{const b=document.getElementById('callRoute'); const n=document.getElementById('callRouteNote'); const d=HUB.call._debug(); return {dis:b.disabled, noteHidden:n.hidden, note:n.textContent, devs:d.routeDevs, hasSink:typeof document.createElement('audio').setSinkId==='function'}})()")
        cap_info = cap_info or {}
        print('   route caps:', cap_info)
        if cap_info.get('dis'):
            note(not cap_info.get('noteHidden') and 'controlled by your phone' in str(cap_info.get('note')), 'route control honestly disabled + note where unsupported', str(cap_info.get('note'))[:70])
        else:
            # enabled in headless (3 outputs): the genuine path — pill live, note hidden
            note(cap_info.get('noteHidden') is True and cap_info.get('devs', 0) >= 2, 'route control enabled where platform exposes 2+ outputs (genuine path)', str(cap_info))
        # simulated-supported: 2 fake outputs, spy setSinkId, devicechange -> refreshRoute
        sim, _ = cA.js("""(()=>{
          const md=navigator.mediaDevices;
          window.__origEnum=md.enumerateDevices.bind(md);
          md.enumerateDevices=()=>Promise.resolve([{deviceId:'fake-out-1',kind:'audiooutput',label:'Loudspeaker'},{deviceId:'fake-out-2',kind:'audiooutput',label:'Earpiece'}]);
          window.__sinkCalls=[];
          window.__origSink=HTMLMediaElement.prototype.setSinkId;
          HTMLMediaElement.prototype.setSinkId=function(id){ window.__sinkCalls.push(id); return Promise.resolve(); };
          md.dispatchEvent(new Event('devicechange'));
          return 'stubbed';
        })()""")
        en2 = wait_js(cA, "(()=>{const b=document.getElementById('callRoute'); return !b.disabled&&document.getElementById('callRouteNote').hidden})()", 10)
        note(bool(en2), 'route pill enables when platform exposes 2+ outputs', str(sim))
        cA.js("document.getElementById('callRoute').click()"); time.sleep(0.8)
        rt, _ = cA.js("(()=>({calls:window.__sinkCalls, cap:document.getElementById('callRouteCap').textContent, faceEar:document.querySelector('#callRoute .cb-face').innerHTML.indexOf('M6.62')>-1}))()")
        rt = rt or {}
        note('fake-out-2' in (rt.get('calls') or []), 'route tap GENUINELY calls setSinkId with 2nd device', str(rt))
        note(rt.get('cap') == 'Earpiece' and rt.get('faceEar') is True, 'route pill shows Earpiece + handset icon', str(rt))
        cA.js("document.getElementById('callRoute').click()"); time.sleep(0.8)
        rt2, _ = cA.js("(()=>({calls:window.__sinkCalls, cap:document.getElementById('callRouteCap').textContent}))()")
        note((rt2 or {}).get('cap') == 'Loudspeaker' and 'fake-out-1' in ((rt2 or {}).get('calls') or []), 'route tap cycles back to Loudspeaker', str(rt2))
        # honestly-disabled path: only 1 output -> pill disabled + honest note, never a fake switch
        cA.js("navigator.mediaDevices.enumerateDevices=()=>Promise.resolve([{deviceId:'only-1',kind:'audiooutput',label:''}]); navigator.mediaDevices.dispatchEvent(new Event('devicechange'))")
        dis2 = wait_js(cA, "(()=>{const b=document.getElementById('callRoute'); const n=document.getElementById('callRouteNote'); return b.disabled&&!n.hidden&&n.textContent.indexOf('controlled by your phone')>-1})()", 10)
        note(bool(dis2), 'route pill honestly disabled + note when <2 outputs')
        cA.js("delete navigator.mediaDevices.enumerateDevices; HTMLMediaElement.prototype.setSinkId=window.__origSink; navigator.mediaDevices.dispatchEvent(new Event('devicechange'))")
        time.sleep(1.0)
        drain_err(cA, 'route')

        # ---- regression: layout fit + Escape + errors ----
        fit, _ = cA.js("(()=>{const de=document.documentElement; const btns=[...document.querySelectorAll('.callcontrols .callbtn')].map(b=>{const r=b.getBoundingClientRect(); return r.left>=0&&r.right<=innerWidth&&r.width>=56}); const route=document.getElementById('callRoute').getBoundingClientRect(); return {sw:de.scrollWidth, iw:innerWidth, btns:btns, routeIn:route.left>=0&&route.right<=innerWidth}})()")
        fit = fit or {}
        note(fit.get('sw', 9999) <= fit.get('iw', 0), 'no horizontal overflow at 390px', str(fit))
        note(all(fit.get('btns') or []) and fit.get('routeIn'), 'all controls in-viewport, >=56px targets', str(fit))
        cA.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        cA.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        time.sleep(1.0)
        esc_ok, _ = cA.js("(()=>{const r=document.getElementById('callRoot'); return r.hidden&&!HUB.call.isActive()})()")
        note(bool(esc_ok), 'Escape leaves the call')
        cB.js("document.getElementById('callLeave').click()"); time.sleep(1.0)
        cC.js("document.getElementById('callLeave').click()"); time.sleep(1.0)
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
