#!/usr/bin/env python3
"""HUB QA: group-call mute polish (PraBin's order).
Covers: Mute-all button shows the 3D clay mic-mute icon (no speaker glyph),
admin mutes a participant -> tile badge shows the 3D mic-mute icon,
the new soft mute cue plays (HUB.sound.playMuteCue) instead of the generic
notification chime, unmute clears the badge, mute-all mutes everyone,
dark + light screenshots, zero console errors. Single tab, demo20 mode.
Fresh profile every run."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9432
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-callmute'
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
def seed_profile(c, name):
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
    time.sleep(0.8)

BADGE_JS = "(()=>{const t=document.querySelector('#callTiles .calltile[data-tile=\"%s\"] .micon'); if(!t) return null; const img=t.querySelector('img[data-icon=\"call-micmute\"]'); return {img:!!img, rendered:img?(img.complete&&img.naturalWidth>0):false, fallback:!!t.querySelector('.ico-fb'), speakerGlyph:t.textContent.indexOf('\\uD83D\\uDD07')>=0}})()"

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
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        hook_err(c); time.sleep(2.5); seed_profile(c, 'QA Ari'); drain_err(c, 'load')
        note(*((True, 'app loads, HUB.call + playMuteCue present') if c.js("!!(window.HUB&&HUB.call&&HUB.call.start&&HUB.sound&&HUB.sound.playMuteCue)")[0] else (False, 'app loads, HUB.call + playMuteCue present')))

        c.js("(()=>{const s=HUB.store.state; s.cgroups=s.cgroups||[]; if(!s.cgroups.find(g=>g.id==='qa-call-g')) s.cgroups.push({id:'qa-call-g',name:'QA Runners',emoji:'\U0001F3C3',mine:true,live:true,members:['Maya Chen','Leo Park'],chat:[]}); HUB.store.save(); return 'ok'})()")
        time.sleep(0.5)
        c.js("HUB.call.start('qa-call-g',{demo20:true})")
        ok = wait_js(c, "(()=>{const r=document.getElementById('callRoot'); return r&&!r.hidden&&!!document.querySelector('#callTiles [data-tile=\"self\"]')})()", 15)
        note(bool(ok), 'demo20 call UI opens (self tile rendered)')
        peers = wait_js(c, "(()=>{const d=HUB.call._debug(); return d&&d.peers.length>=2?d.peers:0})()", 20)
        note(bool(peers), 'demo20 peers arrive', 'peers=%s' % (len(peers) if peers else 0))
        note(bool(c.js("HUB.call._demoPause(true)")[0]), 'demo simulation paused (deterministic mutes)')

        # ---- Mute-all button iconography ----
        ma, _ = c.js("(()=>{const b=document.getElementById('callMuteAll'); if(!b||b.hidden) return null; const img=b.querySelector('img[data-icon=\"call-micmute\"]'); return {img:!!img, rendered:img?(img.complete&&img.naturalWidth>0):false, fallback:!!b.querySelector('.ico-fb'), speakerGlyph:b.innerHTML.indexOf('\\uD83D\\uDD07')>=0}})()")
        note(bool(ma and ma['img']), 'Mute-all button carries the 3D mic-mute icon', json.dumps(ma))
        note(bool(ma and ma['rendered'] and not ma['fallback']), 'Mute-all icon actually renders (no emoji fallback)')
        note(bool(ma and not ma['speakerGlyph']), 'Mute-all button has NO speaker glyph')

        # ---- pick an unmuted peer tile ----
        tgt_pid, _ = c.js("(()=>{const tiles=[...document.querySelectorAll('#callTiles .calltile[data-tile]')].filter(function(el){return el.getAttribute('data-tile')!=='self'&&!el.querySelector('.micon')}); return tiles.length?tiles[0].getAttribute('data-tile'):null})()")
        note(bool(tgt_pid), 'unmuted peer tile found for the test', 'pid=%s' % tgt_pid)
        m0, _ = c.js("HUB.sound._debug().mutes"); ch0, _ = c.js("HUB.sound._debug().chimes")

        # ---- admin mutes the peer via the tile sheet ----
        c.js("document.querySelector('#callTiles .calltile[data-tile=\"%s\"]').click()" % tgt_pid); time.sleep(0.6)
        has_mb, _ = c.js("!!document.getElementById('callAdmMute')")
        note(bool(has_mb), 'admin sheet offers Mute for the peer')
        c.js("document.getElementById('callAdmMute').click()"); time.sleep(0.8)
        bdg, _ = c.js(BADGE_JS % tgt_pid)
        note(bool(bdg and bdg['img']), 'muted tile badge shows the 3D mic-mute icon', json.dumps(bdg))
        note(bool(bdg and bdg['rendered'] and not bdg['fallback']), 'badge icon actually renders (no fallback)')
        note(bool(bdg and not bdg['speakerGlyph']), 'badge has NO speaker glyph')
        muted_flag, _ = c.js("(()=>{const box=document.querySelector('#callTiles .calltile[data-tile=\"%s\"] .mutedby'); return box?box.textContent:''})()" % tgt_pid)
        note('Muted by' in str(muted_flag) or 'muted' in str(muted_flag).lower(), 'tile shows muted-by label', str(muted_flag)[:40])
        m1, _ = c.js("HUB.sound._debug().mutes"); ch1, _ = c.js("HUB.sound._debug().chimes")
        note(m1 == (m0 or 0) + 1, 'soft mute cue played on mute (mutes %s->%s)' % (m0, m1))
        note(ch1 == ch0, 'generic notification chime NOT played for the mute toast (chimes %s->%s)' % (ch0, ch1))
        toast_txt, _ = c.js("document.getElementById('toastHost').textContent")
        note('was muted' in str(toast_txt), 'mute toast shown', str(toast_txt)[:40])
        shot(c, 'callmute-muted-dark')

        # ---- unmute clears the badge ----
        c.js("document.querySelector('#callTiles .calltile[data-tile=\"%s\"]').click()" % tgt_pid); time.sleep(0.6)
        c.js("document.getElementById('callAdmUnmute').click()"); time.sleep(0.8)
        gone, _ = c.js("(()=>{const t=document.querySelector('#callTiles .calltile[data-tile=\"%s\"] .micon'); return !t})()" % tgt_pid)
        note(bool(gone), 'unmute clears the badge')
        m2, _ = c.js("HUB.sound._debug().mutes")
        note(m2 == (m1 or 0) + 1, 'soft cue played on unmute too (mutes %s->%s)' % (m1, m2))

        # ---- mute-all coherence ----
        c.js("document.getElementById('callMuteAll').click()"); time.sleep(1.0)
        allbadged, _ = c.js("(()=>{const tiles=[...document.querySelectorAll('#callTiles .calltile[data-tile]')].filter(function(el){return el.getAttribute('data-tile')!=='self'}); if(!tiles.length) return 0; const ok=tiles.filter(function(el){const i=el.querySelector('.micon img[data-icon=\"call-micmute\"]'); return i&&i.complete&&i.naturalWidth>0}); return ok.length+'/'+tiles.length})()")
        note(allbadged and str(allbadged).split('/')[0] == str(allbadged).split('/')[1], 'mute-all: every peer tile wears the 3D mic-mute badge', str(allbadged))
        nospeak, _ = c.js("(()=>{return [...document.querySelectorAll('#callTiles .micon')].every(function(el){return el.textContent.indexOf('\\uD83D\\uDD07')<0})})()")
        note(bool(nospeak), 'no speaker glyph in any tile badge')

        # ---- light mode ----
        c.js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme()"); time.sleep(0.8)
        shot(c, 'callmute-muted-light')
        light_badge, _ = c.js("(()=>{return !!document.querySelector('#callTiles .micon img[data-icon=\"call-micmute\"]')})()")
        note(bool(light_badge), '3D mic-mute badge present in light mode too')

        c.js("document.getElementById('callLeave').click()"); time.sleep(1.0)
        drain_err(c, 'final')
        print('\n=== console errors ==='); print('NONE' if not errors else errors)
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        try: c.ws.close()
        except Exception: pass
    finally:
        proc.terminate()
if __name__ == '__main__': main()
