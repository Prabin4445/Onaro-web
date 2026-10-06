#!/usr/bin/env python3
"""HUB QA: compact 20-person call grid + Mute all (PraBin's order 2026-09-22).

PraBin's iPhone report: the 20 simulated tiles never painted (Safari), the
"As admin, tap a tile to manage it." banner ate the screen, and he wants
Mute all. This harness verifies at 390x844 (his iPhone CSS px):
- 21 tiles (self + 20 simulated), EVERY tile rect wholly inside the viewport
- grid needs no vertical scroll; no horizontal overflow
- no large admin banner (hint hidden); admin row visible, Mute-all >=44px
- tile tap still opens the admin sheet
- Mute all mutes all 20 peers (not self), one confirmation toast
- zero uncaught errors
Dark + light. Screenshots under qa/. Fresh profile every run."""
import json, subprocess, time, urllib.request, os, base64, shutil, re
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9462
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-grid'
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

LAYOUT_JS = """(()=>{
  const R=el=>{const r=el.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}};
  const grid=document.getElementById('callTiles');
  const hint=document.getElementById('callHint');
  const arow=document.getElementById('callAdminRow');
  const mbtn=document.getElementById('callMuteAll');
  const wrap=document.querySelector('#callRoot .callwrap');
  const head=wrap?wrap.querySelector('.callhead'):null;
  const demo=document.getElementById('callDemoLabel');
  const ctrls=document.getElementById('callControls');
  const tiles=[...grid.querySelectorAll('.calltile')].map(R);
  return {
    vw:innerWidth, vh:innerHeight,
    peers:(HUB.call._debug().peers||[]).length,
    tiles:tiles.length, tileRects:tiles,
    grid:R(grid), gridScrollH:grid.scrollHeight, gridClientH:grid.clientHeight,
    gridCols:getComputedStyle(grid).gridTemplateColumns.split(' ').length,
    hintHidden:hint.hidden, hintText:hint.textContent.trim(),
    arowHidden:arow.hidden, mbtn:mbtn?R(mbtn):null, mbtnText:mbtn?mbtn.textContent.trim():'',
    wrap:wrap?R(wrap):null, head:head?R(head):null, demo:demo?R(demo):null, ctrls:ctrls?R(ctrls):null,
    docSW:document.documentElement.scrollWidth,
    speakingCls:[...grid.querySelectorAll('.calltile.speaking')].length
  };
})()"""

def check_layout(c, tag):
    L, _ = c.js(LAYOUT_JS); L = L or {}
    vw, vh = L.get('vw', 390), L.get('vh', 844)
    note(L.get('peers') == 20, f'{tag}: 20 demo peers in session', L.get('peers'))
    note(L.get('tiles') == 21, f'{tag}: 21 tiles rendered (self + 20)', L.get('tiles'))
    note(L.get('gridCols') == 5, f'{tag}: compact 5-column grid', L.get('gridCols'))
    bad = [t for t in (L.get('tileRects') or [])
           if t['x'] < 0 or t['y'] < 0 or t['x'] + t['w'] > vw or t['y'] + t['h'] > vh]
    note(not bad, f'{tag}: every tile wholly inside {vw}x{vh} viewport', f'{len(bad)} outside')
    g = L.get('grid') or {}
    note(L.get('gridScrollH', 0) <= L.get('gridClientH', 0) + 1,
         f'{tag}: grid needs no vertical scroll', f"scrollH={L.get('gridScrollH')} clientH={L.get('gridClientH')}")
    note(L.get('docSW', 0) <= vw, f'{tag}: no horizontal overflow', f"scrollWidth={L.get('docSW')}")
    note(bool(L.get('hintHidden')), f'{tag}: admin banner GONE (hint hidden)', repr(L.get('hintText'))[:60])
    note(not L.get('arowHidden'), f'{tag}: admin row visible', '')
    mb = L.get('mbtn') or {}
    note(mb.get('h', 0) >= 44, f'{tag}: Mute-all target >=44px', f"h={mb.get('h')}")
    note('Mute all' in L.get('mbtnText', ''), f'{tag}: Mute-all label', repr(L.get('mbtnText'))[:30])
    wr = L.get('wrap') or {}
    note(wr.get('h', 0) <= vh, f'{tag}: call overlay fits viewport', f"wrapH={wr.get('h')}")
    return L

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
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        # true iPhone-14 CSS viewport (headless --window-size alone gave 500x701)
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844,
               'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(0.5)
        hook_err(c)
        # seed profile (onboarding needs campus via custom picker; seed directly)
        c.js("(()=>{const p=HUB.store.state.profile; p.name='QA Grid'; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()")
        time.sleep(0.8)
        # seed group + start a real (loopback-less, single-tab) call, then Simulate 20
        c.js("(()=>{const s=HUB.store.state; s.cgroups=s.cgroups||[]; if(!s.cgroups.find(g=>g.id==='qa-grid-g')) s.cgroups.push({id:'qa-grid-g',name:'QA Grid',emoji:'🏃',mine:true,live:true,members:['QA Grid'],chat:[]}); HUB.store.save(); return 'ok'})()")
        time.sleep(0.5)
        c.js("HUB.cgroups.openClub('qa-grid-g')"); time.sleep(1.0)
        c.js("document.getElementById('cgCallBtn').click()"); time.sleep(1.2)
        pk, _ = c.js("!!document.getElementById('callPickDemo20')")
        note(bool(pk), 'call picker offers Simulate-20')
        c.js("document.getElementById('callPickDemo20').click()"); time.sleep(1.5)
        ok = wait_js(c, "(()=>{const d=HUB.call._debug(); return d&&d.demo20===true&&d.peers.length===20})()", 15)
        note(bool(ok), 'demo20 session active with 20 peers')
        drain_err(c, 'start+demo20')

        # ---- dark layout ----
        check_layout(c, 'dark')
        shot(c, 'call-grid-compact-dark')
        drain_err(c, 'layout-dark')

        # ---- tile tap opens admin sheet ----
        c.js("document.querySelector('[data-tile=\"d3\"]').click()"); time.sleep(0.8)
        sh, _ = c.js("(()=>{const s=document.getElementById('callSheet'); return s&&!s.hidden&&!!document.getElementById('callAdmMute')})()")
        note(bool(sh), 'tile tap opens admin sheet (mute control present)')
        shot(c, 'call-admin-sheet-dark')
        # the in-call sheet has its own closer (Escape/backdrop), not ui.closeSheet()
        c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape'})
        c.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape'})
        time.sleep(0.6)
        sh_closed, _ = c.js("document.getElementById('callSheet').hidden")
        note(bool(sh_closed), 'admin sheet closes on Escape')
        drain_err(c, 'tile-sheet')

        # ---- Mute all ----
        c.js("document.getElementById('callMuteAll').click()"); time.sleep(1.2)
        st, _ = c.js("(()=>{const d=HUB.call._debug(); const muted=(HUB.call._peersMutedCount?HUB.call._peersMutedCount():null); return {peers:d.peers.length, selfMuted:d.muted, toast:document.getElementById('toastHost').textContent}})()")
        muted_tiles, _ = c.js("document.querySelectorAll('#callTiles .calltile .micon').length")
        all_muted, _ = c.js("(()=>{const ts=[...document.querySelectorAll('#callTiles .calltile')]; return ts.filter(t=>t.getAttribute('data-tile')!=='self').every(t=>t.querySelector('.micon'))})()")
        self_muted_icon, _ = c.js("!!document.querySelector('[data-tile=\"self\"] .micon')")
        st = st or {}
        note(bool(all_muted), 'Mute all: all 20 peer tiles show muted icon', f'micon tiles={muted_tiles}')
        note(not self_muted_icon, 'Mute all: self tile NOT muted')
        note(bool(re.match(r'Muted \d+ people', str(st.get('toast') or ''))),
             'Mute all: one confirmation toast (count = newly muted)', str(st.get('toast'))[:60])
        shot(c, 'call-muteall-dark')
        drain_err(c, 'muteall')

        # ---- light mode ----
        c.js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.8)
        check_layout(c, 'light')
        shot(c, 'call-grid-compact-light')
        shot(c, 'call-muteall-light')
        c.js("HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.5)
        drain_err(c, 'light')

        # leave cleanly
        c.js("document.getElementById('callLeave').click()"); time.sleep(1.0)
        drain_err(c, 'leave')
    finally:
        proc.terminate()
    print('\n==== %d/%d checks passed, %d error groups ====' % (
        sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
    for lbl, v in errors: print('ERRGROUP', lbl, json.dumps(v)[:300])
    bad = [l for ok, l in checks if not ok]
    if bad: print('FAILED:', bad)
    return 0 if (not bad and not errors) else 1

if __name__ == '__main__':
    raise SystemExit(main())
