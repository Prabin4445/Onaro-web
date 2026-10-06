#!/usr/bin/env python3
"""HUB QA: floating water bubbles for the "People in {campus}" head row.
Covers: bubbles render on Home (>=5), each .hp-av runs the hpFloat animation
(WAAPI), float clock advances (motion proof), ::after sheen runs hpSheen,
per-bubble phase stagger (--hd distinct), initials + names unchanged,
tap bubble opens that person's profile card (name matches, badge row intact,
close returns to Home), infinite forward marquee (two identical sets, 30s
seamless loop, track glides left on its own, touch pauses / resume ~2s,
duplicate tap opens the right card), reduced-motion emulation freezes/kills
the bubbles AND the marquee, dark + light, 390px, zero console errors. Fresh profile every run."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9434
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-bubbles'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)

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
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
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
def seed_profile(c, name):
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
    time.sleep(0.8)
def close_all(c):
    c.js("(()=>{HUB.ui.closeSheet(); if(HUB.people&&HUB.people.closeGlass) HUB.people.closeGlass(); return 1})()"); time.sleep(0.4)

JS = "(function(){%s})()"
def wait_splash_gone(c, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if c.js(JS % "return !document.getElementById('splash')")[0]: return True
        time.sleep(0.5)
    return False

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
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
        hook_err(c); time.sleep(2.5); seed_profile(c, 'QA Ari'); drain_err(c, 'load')
        note(wait_splash_gone(c), 'splash dismissed before checks')
        c.js(JS % "HUB.showTab('home')")
        t0 = time.time()
        while time.time() - t0 < 10:
            if c.js(JS % "return !!document.querySelector('#homePplSec')")[0]: break
            time.sleep(0.5)
        note(c.js(JS % "return !!document.querySelector('#homePplSec')")[0], 'home people row painted')

        # 1. bubble row renders on Home
        n, _ = c.js(JS % "return document.querySelectorAll('#homePplSec .hp-head').length")
        note(isinstance(n, int) and n >= 5, 'bubble row renders (>=5 bubbles)', str(n))
        vis, _ = c.js(JS % "const s=document.querySelector('#homePplSec'); if(!s) return false; const r=s.getBoundingClientRect(); return r.width>0&&r.height>0")
        note(vis, 'bubble row section visible')
        title, _ = c.js(JS % "const h=document.querySelector('#homePplSec h2'); return h?h.textContent:''")
        note(isinstance(title, str) and 'QA Campus' in title, 'row title carries the campus', title)
        names, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-name')).map(e=>e.textContent).join('|')")
        note(isinstance(names, str) and 'Priya' in names and 'Diego' in names, 'initials names intact', names)
        inits, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-av')).map(e=>e.textContent.trim()).join('|')")
        note('PN' in inits and 'DM' in inits, 'avatar initials intact', inits)

        # 2. every bubble runs the float animation (WAAPI)
        anims, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-av')).map(e=>e.getAnimations().map(a=>a.animationName||'?'))")
        note(isinstance(anims, list) and all('hpFloat' in (a or []) for a in anims),
             'every bubble runs hpFloat', json.dumps(anims)[:160])
        # 3. motion proof: WAAPI clock advances (phase-independent)
        t1, _ = c.js(JS % "const a=document.querySelector('#homePplSec .hp-av').getAnimations()[0]; return a?a.currentTime:null")
        time.sleep(0.9)
        t2, _ = c.js(JS % "const a=document.querySelector('#homePplSec .hp-av').getAnimations()[0]; return a?a.currentTime:null")
        dt = (t2 - t1) if isinstance(t1, (int, float)) and isinstance(t2, (int, float)) else -1
        note(dt > 400, 'float clock advances (motion proof)', 'dt=%s' % dt)
        # 4. orbiting sheen on ::after
        sheen, _ = c.js(JS % "const e=document.querySelector('#homePplSec .hp-av'); return getComputedStyle(e,'::after').getPropertyValue('animation-name')")
        note(sheen == 'hpSheen', 'orbiting sheen runs hpSheen on ::after', sheen)
        gloss, _ = c.js(JS % "const e=document.querySelector('#homePplSec .hp-av'); return getComputedStyle(e,'::before').getPropertyValue('background-image').slice(0,20)")
        note(isinstance(gloss, str) and 'gradient' in gloss, 'static crescent gloss on ::before', gloss)
        # 5. per-bubble phase stagger
        hds, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-head')).map(e=>getComputedStyle(e).getPropertyValue('--hd'))")
        uniq = len(set(hds or []))
        note(isinstance(hds, list) and uniq >= 3, 'phase stagger (--hd distinct)', 'uniq=%d of %d' % (uniq, len(hds or [])))
        # 5b. FREE DRIFT: bounding boxes genuinely wander (not just a fixed bob)
        dw, _ = c.js(JS % "return document.querySelectorAll('#homePplSec .hp-drift').length")
        note(dw == n, 'every bubble has a drift wrapper', '%s/%s' % (dw, n))
        danims, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-drift')).map(e=>e.getAnimations().map(a=>a.animationName||'?'))")
        note(isinstance(danims, list) and all(any((a or '').startswith('hpDrift') for a in (x or [])) for x in danims),
             'every wrapper runs a hpDrift wander path', json.dumps(danims)[:160])
        d1, _ = c.js(JS % "const a=document.querySelector('#homePplSec .hp-drift').getAnimations()[0]; return a?a.currentTime:null")
        time.sleep(0.9)
        d2, _ = c.js(JS % "const a=document.querySelector('#homePplSec .hp-drift').getAnimations()[0]; return a?a.currentTime:null")
        ddt = (d2 - d1) if isinstance(d1, (int, float)) and isinstance(d2, (int, float)) else -1
        note(ddt > 400, 'drift clock advances (wander motion proof)', 'dt=%s' % ddt)
        dpds, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-drift')).map(e=>getComputedStyle(e).getPropertyValue('--dpd'))")
        note(isinstance(dpds, list) and len(set(dpds or [])) >= 3, 'drift periods vary per bubble', 'uniq=%d' % len(set(dpds or [])))
        # bounding-box wander, measured RELATIVE to the gliding track: the
        # marquee itself carries every head leftward, so subtract the track's
        # own translation to isolate each bubble's personal drift.
        TX = "const _mt=document.querySelector('#homePplSec .hp-marquee');const _mm=getComputedStyle(_mt).transform;if(_mm==='none')return 0;const _p=_mm.match(/matrix\\(([^)]+)\\)/);return _p?parseFloat(_p[1].split(',')[4]):0"
        r1, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-av')).map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top]})")
        tx1, _ = c.js(JS % TX)
        time.sleep(2.0)
        r2, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-av')).map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top]})")
        tx2, _ = c.js(JS % TX)
        moved = movedx = 0; maxrdx = 0; tdx = 0
        if isinstance(tx1, (int, float)) and isinstance(tx2, (int, float)): tdx = tx2 - tx1
        if isinstance(r1, list) and isinstance(r2, list) and len(r1) == len(r2):
            for a, b in zip(r1, r2):
                dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
                rdx = abs((b[0] - a[0]) - tdx)
                maxrdx = max(maxrdx, rdx)
                if dx > 3 or dy > 3: moved += 1
                if rdx > 3: movedx += 1
        note(moved >= 5, 'heads wander (bounding boxes move over 2s)', 'moved=%d' % moved)
        note(movedx >= 4, 'heads drift SIDEWAYS on their own (beyond the forward glide)', 'movedx=%d tdx=%.1f' % (movedx, tdx))
        note(maxrdx < 18, 'drift stays contained relative to the gliding track', 'maxrdx=%.1f' % maxrdx)
        # neighbors must not collide: worst pairwise gap sampled twice
        gaps = []
        for _ in range(2):
            g, _ = c.js(JS % "const es=Array.from(document.querySelectorAll('#homePplSec .hp-av')); const rs=es.map(e=>e.getBoundingClientRect()); const out=[]; for(let i=1;i<rs.length;i++){out.push(rs[i].left-rs[i-1].right)} return out")
            if isinstance(g, list): gaps += g
            time.sleep(1.0)
        mingap = min(gaps) if gaps else -999
        note(mingap > -8, 'heads never collide (neighbor gaps stay open)', 'mingap=%.1f' % mingap)
        # 5c. INFINITE FORWARD MARQUEE: two identical sets, track glides left
        mq, _ = c.js(JS % "return !!document.querySelector('#homePplSec .hp-marquee')")
        note(mq, 'marquee track present')
        man, _ = c.js(JS % "const e=document.querySelector('#homePplSec .hp-marquee'); return e?getComputedStyle(e).animationName:''")
        note(man == 'hpMarquee', 'track runs hpMarquee', man)
        mdur, _ = c.js(JS % "const e=document.querySelector('#homePplSec .hp-marquee'); return e?getComputedStyle(e).animationDuration:''")
        note(mdur == '30s', 'slow dreamy 30s cycle', mdur)
        halves, _ = c.js(JS % "const hs=Array.from(document.querySelectorAll('#homePplSec .hp-marquee .hp-head'));const N=hs.filter(h=>!h.hasAttribute('aria-hidden')).length;const s1=hs.slice(0,N).map(h=>h.dataset.hp).join(',');const s2=hs.slice(N).map(h=>h.dataset.hp).join(',');const hid=hs.slice(N).every(h=>h.getAttribute('aria-hidden')==='true');return [hs.length,N,s1===s2,hid]")
        note(isinstance(halves, list) and halves[0] == 2 * halves[1] and halves[2],
             'two identical head sets (seamless loop)', json.dumps(halves)[:160])
        note(isinstance(halves, list) and halves[3], 'duplicate set aria-hidden')
        wmatch, _ = c.js(JS % "const hs=Array.from(document.querySelectorAll('#homePplSec .hp-marquee .hp-head'));const N=hs.length/2;let _ok=true;for(let i=0;i<N;i++){if(hs[i].offsetWidth!==hs[i+N].offsetWidth){_ok=false;break}}return _ok")
        note(wmatch, 'per-index widths match across halves (-50% lands exact)')
        def mtx():
            v, _ = c.js(JS % "const e=document.querySelector('#homePplSec .hp-marquee');const m=getComputedStyle(e).transform;if(m==='none')return 0;const p=m.match(/matrix\\(([^)]+)\\)/);return p?parseFloat(p[1].split(',')[4]):0")
            return v
        x1 = mtx(); time.sleep(2.5); x2 = mtx()
        dx = (x2 - x1) if isinstance(x1, (int, float)) and isinstance(x2, (int, float)) else 0
        note(dx < -15, 'track glides FORWARD (leftward) on its own', 'dx=%.1f over 2.5s' % dx)
        # touch pauses the glide, lifting the finger resumes it
        c.js(JS % "document.querySelector('#homePplSec .hp-marquee').dispatchEvent(new Event('touchstart'))")
        time.sleep(0.3)
        paused, _ = c.js(JS % "const e=document.querySelector('#homePplSec .hp-marquee');return e.classList.contains('hp-paused')&&getComputedStyle(e).animationPlayState==='paused'")
        note(paused, 'touchstart pauses the auto-glide')
        c.js(JS % "document.querySelector('#homePplSec .hp-marquee').dispatchEvent(new Event('touchend'))")
        time.sleep(2.6)
        resumed, _ = c.js(JS % "const e=document.querySelector('#homePplSec .hp-marquee');return !e.classList.contains('hp-paused')&&getComputedStyle(e).animationPlayState==='running'")
        note(resumed, 'glide resumes ~2s after touchend')
        # tap a DUPLICATE bubble -> the right person's card opens
        c.js(JS % "const hs=document.querySelectorAll('#homePplSec .hp-marquee .hp-head');hs[hs.length/2].click()")
        time.sleep(0.7)
        dname, _ = c.js(JS % "const hs=document.querySelectorAll('#homePplSec .hp-marquee .hp-head');const b=hs[hs.length/2];const f=HUB.store.state.people.find(x=>x&&x.id===b.dataset.hp);const nm=f?f.name:HUB.store.state.profile.name;const h=document.querySelector('#hpGlassCard .hpglass-name');const open=!document.getElementById('hpGlass').hidden;return [b.dataset.hp,nm,h?h.textContent:'',open]")
        note(isinstance(dname, list) and dname[3] and dname[1] == dname[2],
             'tap DUPLICATE bubble opens the right person\'s card', json.dumps(dname)[:120])
        c.js(JS % "HUB.people.closeGlass()"); time.sleep(0.4)
        shot(c, 'bubbles-dark')

        # 6. tap a bubble -> that person's profile card opens (name matches, badge intact)
        pname, _ = c.js(JS % "const b=document.querySelector('#homePplSec .hp-head'); const p=HUB.store.state.people.find(x=>x&&x.id===b.dataset.hp); return p?p.name:''")
        c.js(JS % "document.querySelector('#homePplSec .hp-head').click()")
        time.sleep(0.7)
        open_, _ = c.js(JS % "const g=document.getElementById('hpGlass'); return g&&!g.hidden")
        cname, _ = c.js(JS % "const h=document.querySelector('#hpGlassCard .hpglass-name'); return h?h.textContent:''")
        note(open_ and cname == pname, 'tap bubble opens that person\'s card (name matches)', '%r -> %r' % (pname, cname))
        bdg, _ = c.js(JS % "const b=document.querySelector('#hpGlassCard .hp-badges'); return b?getComputedStyle(b).display:''")
        note(bdg not in ('', 'none'), 'badge row intact on the profile card', bdg)
        shot(c, 'bubbles-profile-open')
        c.js(JS % "HUB.people.closeGlass()")
        time.sleep(0.4)
        closed, _ = c.js(JS % "return !!document.getElementById('hpGlass').hidden")
        note(closed, 'closeGlass returns to Home cleanly')
        drain_err(c, 'dark-interactions')

        # 7. light theme: bubbles still float, tap still works
        c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme(); HUB.showTab('home'); return 1")
        time.sleep(0.8)
        la, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-av')).every(e=>e.getAnimations().length>=1)")
        note(la, 'bubbles animate in light theme')
        c.js(JS % "document.querySelectorAll('#homePplSec .hp-head')[1].click()")
        time.sleep(0.7)
        lname, _ = c.js(JS % "const b=document.querySelectorAll('#homePplSec .hp-head')[1]; const p=HUB.store.state.people.find(x=>x&&x.id===b.dataset.hp); const h=document.querySelector('#hpGlassCard .hpglass-name'); return (p?p.name:'')+'|'+(h?h.textContent:'')")
        note(isinstance(lname, str) and '|' in lname and lname.split('|')[0] == lname.split('|')[1] and lname.split('|')[0],
             'tap opens matching profile in light theme', lname)
        shot(c, 'bubbles-light')
        close_all(c); drain_err(c, 'light-interactions')

        # 8. reduced-motion: bubbles freeze
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        c.send('Page.reload'); time.sleep(2.5)
        seed_profile(c, 'QA Ari')
        note(wait_splash_gone(c), 'splash dismissed under reduced-motion')
        c.js(JS % "HUB.showTab('home')")
        t0 = time.time()
        while time.time() - t0 < 10:
            if c.js(JS % "return document.querySelectorAll('#homePplSec .hp-av').length>=5")[0]: break
            time.sleep(0.5)
        rn, _ = c.js(JS % "return document.querySelectorAll('#homePplSec .hp-av').length")
        ra, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-av')).reduce((s,e)=>s+e.getAnimations().length,0)")
        ct1, _ = c.js(JS % "const a=document.querySelector('#homePplSec .hp-av').getAnimations()[0]; return a?a.currentTime:'none'")
        time.sleep(0.8)
        ct2, _ = c.js(JS % "const a=document.querySelector('#homePplSec .hp-av').getAnimations()[0]; return a?a.currentTime:'none'")
        frozen = (ra == 0) or (ct1 == 'none' and ct2 == 'none') or (isinstance(ct1, (int, float)) and isinstance(ct2, (int, float)) and abs(ct2 - ct1) < 100)
        note(rn >= 5 and frozen, 'reduced-motion freezes all bubbles', 'bubbles=%s anims=%s clock=%s->%s' % (rn, ra, ct1, ct2))
        rma, _ = c.js(JS % "return Array.from(document.querySelectorAll('#homePplSec .hp-marquee')).reduce((s,e)=>s+e.getAnimations().length,0)")
        note(rma == 0, 'reduced-motion kills the marquee glide too', 'marquee anims=%s' % rma)
        shot(c, 'bubbles-reduced-motion')
        drain_err(c, 'reduced-motion')

        # 9. zero console errors
        note(not errors, 'zero console errors', json.dumps(errors)[:300])
        ok = sum(1 for p, _ in checks if p); tot = len(checks)
        print('==== %d/%d passed ====' % (ok, tot))
        return 0 if ok == tot else 1
    finally:
        proc.terminate()

if __name__ == '__main__':
    raise SystemExit(main())
