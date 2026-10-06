#!/usr/bin/env python3
"""QA: logout farewell inside the top bar (stick man -> door -> login).
Covers: appbar logout DOOR button (with Logout written on it) visible only when
logged in, appbar fits at 320/390px, in-topbar strip phases (walk / door opens /
wave bye / man enters / door shuts), strip contained in the top bar (no
fullscreen, no new page), tap-to-skip, Me-tab account-card logout, login page
landing, session actually cleared, zero console errors. 320+390px, dark+light."""
import json, subprocess, time, urllib.request, shutil, os, base64
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
QA = os.path.dirname(os.path.abspath(__file__))
checks, errors = [], []

def note(ok, label, detail=''):
    checks.append((bool(ok), label))
    print(('PASS ' if ok else 'FAIL ') + label, detail if not ok else '')

class CDP:
    def __init__(self, wsurl):
        import websocket
        self.ws = websocket.create_connection(wsurl, timeout=15); self.ws.settimeout(15); self.iid = 0
    def send(self, method, params=None):
        self.iid += 1
        self.ws.send(json.dumps({'id': self.iid, 'method': method, 'params': params or {}}))
        dl = time.time() + 20
        while time.time() < dl:
            m = json.loads(self.ws.recv())
            if m.get('id') == self.iid: return m.get('result')
        raise TimeoutError(method)

def targets(port):
    return json.load(urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=10))

def j(c, expr, awaitPromise=False):
    expr = "(function(){" + expr + "})()"
    try:
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
        if r and 'exceptionDetails' in r:
            ed = r['exceptionDetails']
            return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
        return (r or {}).get('result', {}).get('value')
    except Exception as e:
        return 'JSERR:' + str(e)[:120]

SEED = """var st=HUB.store.state;
st.auth=st.auth||{users:[],session:null};
st.auth.users=[{id:'qa-lo1',name:'QA Logout',email:'qa@example.com',phoneE164:'+15551234567',
cc:'US',pw:'x',salt:'x',campus:'QA Campus',verifiedVia:'email',faceId:null,createdAt:Date.now()}];
st.auth.session={uid:'qa-lo1',at:Date.now(),remember:true};
HUB.store.save(); HUB.auth.restore();
window.__gateSkip=true;
try{HUB.auth.close()}catch(e){}
var w=document.getElementById('wlcmHost'); if(w) w.remove();
return !!HUB.auth.currentUser();"""

def login_visible(c):
    return j(c, "var a=document.querySelector('.authroot'); return !!a&&!a.hidden&&getComputedStyle(a).display!=='none';")

def run_case(width, height, theme, port):
    tag = f'{width}x{height}-{theme}'
    prof = f'/tmp/hubqa-logout-{width}-{theme}'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={port}', '--remote-allow-origins=*', f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = targets(port)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': width, 'height': height, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(0.5)
        for _attempt in range(3):  # emulation can miss on a slow first paint; retry
            if j(c, "return window.innerWidth;") == width: break
            c.send('Emulation.setDeviceMetricsOverride',
                   {'width': width, 'height': height, 'deviceScaleFactor': 2, 'mobile': True})
            time.sleep(1.0)
        note(j(c, "return window.innerWidth;") == width, f'true {width}px viewport [{tag}]')
        j(c, "window.__huberr=[];addEventListener('error',function(e){__huberr.push('ERR:'+e.message)});"
             "addEventListener('unhandledrejection',function(e){__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))})")
        for _ in range(60):
            if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.auth&&HUB.logout&&HUB.i18n&&HUB.ui);") is True: break
            time.sleep(0.5)
        j(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
             "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        for _ in range(20):
            if j(c, "return !document.getElementById('splash');") is True: break
            time.sleep(0.5)
        def shot(name, jpeg=False):
            p = {'format': 'jpeg', 'quality': 60} if jpeg else {'format': 'png'}
            r = c.send('Page.captureScreenshot', p)
            open(os.path.join(QA, name + ('.jpg' if jpeg else '.png')), 'wb').write(base64.b64decode(r['data']))

        # ---- logged-in state: button visible, appbar fits ----
        note(j(c, SEED) is True, f'seed logged-in user [{tag}]')
        time.sleep(0.4)
        note(j(c, "var b=document.getElementById('logoutBtn'); return !!b&&!b.hidden;") is True,
             f'appbar logout button visible when logged in [{tag}]')
        note(j(c, "var l=document.querySelector('#logoutBtn .ldoor-label');"
                  "return !!l&&l.textContent.trim().length>1;") is True,
             f'door button has Logout written on it [{tag}]')
        note(j(c, "return !document.querySelector('#logoutBtn svg');") is True,
             f'door button is a door, not the old icon [{tag}]')
        note(j(c, "var a=document.querySelector('.appbar'); return a.scrollWidth<=window.innerWidth;") is True,
             f'appbar fits 6 icons, no h-overflow [{tag}]')
        note(j(c, "var bs=[...document.querySelectorAll('.appbar .iconbtn')].filter(b=>!b.hidden);"
                  "var vw=window.innerWidth;"
                  "return bs.length===6&&bs.every(b=>{var r=b.getBoundingClientRect();return r.left>=-1&&r.right<=vw+1;});") is True,
             f'all 6 appbar buttons inside viewport [{tag}]')
        note(j(c, "var n=document.querySelector('.brand-name');var r=n.getBoundingClientRect();"
                  "return r.width>60&&r.left>=-1;") is True,
             f'brand wordmark intact, not squeezed [{tag}]')
        note(j(c, "return document.documentElement.scrollWidth<="+str(width)+";") is True,
             f'page no h-overflow with new button [{tag}]')
        shot(f'logout-appbar-{width}-{theme}')

        # ---- in-topbar farewell via the door button ----
        # Defuse the wall-clock finish BEFORE clicking so phase seeks are deterministic.
        j(c, "window.__loTids=[];window.__oST=window.setTimeout;"
             "window.setTimeout=function(fn,ms){var id=window.__oST(fn,ms);"
             "if(ms>=2500&&ms<=4000)window.__loTids.push(id);return id;}; return 1;")
        j(c, "document.getElementById('logoutBtn').click(); return 1;")
        ok = False
        for _ in range(40):
            if j(c, "return !!document.getElementById('loStrip');") is True:
                ok = True; break
            time.sleep(0.15)
        note(ok, f'strip opens in top bar [{tag}]')
        j(c, "window.__loTids.forEach(function(id){clearTimeout(id);});"
             "window.setTimeout=window.__oST; return 1;")
        note(j(c, "return !!document.querySelector('.lo-strip .lo-man svg');") is True, f'stick man rendered [{tag}]')
        note(j(c, "return !!document.querySelector('.lo-strip .lo-door');") is True, f'door rendered [{tag}]')
        note(j(c, "var l=document.querySelector('.lo-strip .lo-door-label');"
                  "return !!l&&l.textContent.trim().length>1;") is True,
             f'animation door has Logout written in it [{tag}]')
        note(j(c, "var d=document.querySelector('.lo-strip .lo-door');"
                  "return d&&getComputedStyle(d).transform==='none';") is True,
             f'door begins closed [{tag}]')
        note(j(c, "return !!(HUB.auth&&HUB.auth.currentUser&&HUB.auth.currentUser());") is True,
             f'session stays active during the animation [{tag}]')
        # the whole point: everything plays inside the top bar — no fullscreen, no new page
        note(j(c, "var a=document.querySelector('.appbar').getBoundingClientRect();"
                  "var s=document.getElementById('loStrip').getBoundingClientRect();"
                  "return s.top>=a.top-2&&s.bottom<=a.bottom+2&&s.left>=a.left-2&&s.right<=a.right+2"
                  "&&s.height<window.innerHeight/2&&s.width<window.innerWidth;") is True,
             f'animation stays inside the top bar [{tag}]')
        # WAVE phase: restart the real lo-wave animation (a finished CSS animation is
        # dropped from getAnimations()) — each restart step its own CDP call, then poll.
        j(c, "var g=document.querySelector('.lo-strip .lo-waveg'); if(g){g.style.animation='none';} return 1;")
        j(c, "var g=document.querySelector('.lo-strip .lo-waveg'); if(g){void g.offsetWidth; g.style.animation='';} return 1;")
        for _ in range(20):
            n = j(c, "var g=document.querySelector('.lo-strip .lo-waveg'); return g?g.getAnimations().length:0;")
            if isinstance(n, int) and n > 0: break
            time.sleep(0.15)
        j(c, "var m=document.querySelector('.lo-strip .lo-man'); if(m)"
             "m.getAnimations().forEach(function(a){a.pause();a.currentTime=2000;});"
             "var g=document.querySelector('.lo-strip .lo-waveg'); if(g)"
             "g.getAnimations().forEach(function(a){a.pause();a.currentTime=2000;}); return 1;")
        note(j(c, "var g=document.querySelector('.lo-strip .lo-waveg'); if(!g) return 'nogroup';"
                  "var t=getComputedStyle(g).transform;"
                  "return t!=='none'&&t.indexOf('matrix')===0;") is True,
             f'stick man waves bye [{tag}]')
        # WALK phase: reset the man to walk-start (the wave check left him paused
        # at 2000), read x, seek to mid-stride, assert he travels right
        manx0 = j(c, "var m=document.querySelector('.lo-strip .lo-man'); if(m)"
                     "m.getAnimations().forEach(function(a){a.pause();a.currentTime=0;});"
                     "return m?m.getBoundingClientRect().left:-1;")
        j(c, "var m=document.querySelector('.lo-strip .lo-man'); if(m)"
             "m.getAnimations().forEach(function(a){a.pause();a.currentTime=800;}); return 1;")
        manx1 = j(c, "var m=document.querySelector('.lo-strip .lo-man'); return m?m.getBoundingClientRect().left:-1;")
        note(isinstance(manx1, (int, float)) and manx1 > manx0 + 25,
             f'stick man walks toward the door [{tag}]', f'{manx0}->{manx1}')
        # DOOR phase: seek the door to mid-swing (doorclose still in delay: no-op)
        j(c, "var d=document.querySelector('.lo-strip .lo-door'); if(d)"
             "d.getAnimations().forEach(function(a){a.pause();a.currentTime=1600;}); return 1;")
        note(j(c, "var d=document.querySelector('.lo-strip .lo-door'); if(!d) return 'gone';"
                  "var t=getComputedStyle(d).transform;"
                  "if(t.indexOf('matrix3d')!==0) return 'flat:'+t;"
                  "return Math.abs(parseFloat(t.slice(9).split(',')[0]))<0.92;") is True,
             f'door swings open in 3D [{tag}]')
        # GLOW phase: warm light spills when the door opens (glowin ends at 1.8s)
        j(c, "var g=document.querySelector('.lo-strip .lo-glow'); if(g)"
             "g.getAnimations().forEach(function(a){a.pause();a.currentTime=2000;}); return 1;")
        note(j(c, "var g=document.querySelector('.lo-strip .lo-glow'); if(!g) return 'gone';"
                  "return getComputedStyle(g).opacity==='1';") is True,
             f'warm light when the door opens [{tag}]')
        # ENTER phase: man in the doorway, fading into the light, door held open
        j(c, "var m=document.querySelector('.lo-strip .lo-man'); if(m)"
             "m.getAnimations().forEach(function(a){a.pause();a.currentTime=2800;});"
             "var d=document.querySelector('.lo-strip .lo-door'); if(d)"
             "d.getAnimations().forEach(function(a){a.pause();a.currentTime=2800;}); return 1;")
        note(j(c, "var m=document.querySelector('.lo-strip .lo-man'); if(!m) return 'gone';"
                  "return parseFloat(getComputedStyle(m).opacity)<1;") is True,
             f'stick man enters the doorway [{tag}]')
        # DOOR SHUT phase: doorclose finished -> rotateY(0); Chrome keeps the fill as an
        # identity matrix rather than 'none', so accept both serializations
        j(c, "var d=document.querySelector('.lo-strip .lo-door'); if(d)"
             "d.getAnimations().forEach(function(a){a.pause();a.currentTime=3450;}); return 1;")
        note(j(c, "var d=document.querySelector('.lo-strip .lo-door'); if(!d) return 'gone';"
                  "var t=getComputedStyle(d).transform;"
                  "return t==='none'||t==='matrix(1, 0, 0, 1, 0, 0)';") is True,
             f'door shuts behind him [{tag}]')
        shot(f'logout-strip-{width}-{theme}')
        # run the real end-of-timeline path (strip removal + sign-out)
        j(c, "try{HUB.logout._finish()}catch(e){} return 1;")
        time.sleep(0.5)
        note(j(c, "return !document.getElementById('loStrip');") is True, f'strip removed after timeline [{tag}]')
        note(j(c, "return !HUB.auth.currentUser();") is True, f'session cleared [{tag}]')
        note(login_visible(c) is True, f'login page opens [{tag}]')
        note(j(c, "var b=document.getElementById('logoutBtn'); return !!b&&b.hidden;") is True,
             f'logout button hidden after logout [{tag}]')
        shot(f'logout-login-{width}-{theme}')

        # ---- tap-to-skip ----
        j(c, "try{HUB.auth.close()}catch(e){} " + SEED)
        time.sleep(0.4)
        j(c, "document.getElementById('logoutBtn').click(); return 1;")
        time.sleep(0.6)
        note(j(c, "return !!document.getElementById('loStrip');") is True, f'strip opens (skip test) [{tag}]')
        j(c, "document.getElementById('loStrip').click(); return 1;")
        time.sleep(0.8)
        note(j(c, "return !document.getElementById('loStrip')&&!HUB.auth.currentUser();") is True,
             f'tap skips straight to signed-out [{tag}]')
        note(login_visible(c) is True, f'login page opens after skip [{tag}]')

        # ---- Me tab account-card logout also plays the in-topbar farewell ----
        j(c, "try{HUB.auth.close()}catch(e){} " + SEED)
        time.sleep(0.4)
        j(c, "document.querySelector('[data-tab=\"me\"]').click(); return 1;")
        time.sleep(0.8)
        note(j(c, "return !!document.getElementById('acLogout');") is True, f'account card logout btn present [{tag}]')
        j(c, "document.getElementById('acLogout').click(); return 1;")
        time.sleep(0.7)
        note(j(c, "return !!document.getElementById('loStrip');") is True, f'account-card logout plays farewell [{tag}]')
        shot(f'logout-acctcard-{width}-{theme}')
        time.sleep(3.5)
        note(j(c, "return !HUB.auth.currentUser();") is True, f'account-card logout signs out [{tag}]')
        note(login_visible(c) is True, f'login page opens (account card) [{tag}]')

        # ---- edge: double-tap makes exactly one strip, still signs out ----
        j(c, "try{HUB.auth.close()}catch(e){} " + SEED)
        time.sleep(0.4)
        j(c, "var b=document.getElementById('logoutBtn'); b.click(); b.click(); return 1;")
        time.sleep(0.7)
        note(j(c, "return document.querySelectorAll('#loStrip').length===1;") is True,
             f'double tap makes one strip [{tag}]')
        for _ in range(40):
            if j(c, "return !document.getElementById('loStrip');") is True: break
            time.sleep(0.2)
        note(j(c, "return !HUB.auth.currentUser();") is True, f'double-tap logout signs out [{tag}]')
        note(login_visible(c) is True, f'login page opens (double tap) [{tag}]')

        # ---- edge: prefers-reduced-motion skips the farewell, still signs out ----
        j(c, "try{HUB.auth.close()}catch(e){} " + SEED)
        time.sleep(0.4)
        c.send('Emulation.setEmulatedMedia',
               {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        j(c, "document.getElementById('logoutBtn').click(); return 1;")
        time.sleep(0.8)
        note(j(c, "return !document.getElementById('loStrip')&&!HUB.auth.currentUser();") is True,
             f'reduced-motion skips farewell, signs out [{tag}]')
        note(login_visible(c) is True, f'login page opens (reduced motion) [{tag}]')
        c.send('Emulation.setEmulatedMedia', {'features': []})

        errs = j(c, "return window.__huberr.splice(0);")
        note(not errs, f'zero console errors [{tag}]', json.dumps(errs)[:300] if errs else '')
    finally:
        try: proc.terminate()
        except Exception: pass

def main():
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None  # e.g. "390-light"
    port = 9481
    for w, h in [(390, 844), (320, 568)]:
        for th in ['dark', 'light']:
            if only and f'{w}-{th}' != only:
                port += 1; continue
            run_case(w, h, th, port); port += 1
    bad = [l for ok, l in checks if not ok]
    print('\n%d/%d checks passed' % (len(checks) - len(bad), len(checks)))
    if bad: print('FAILED:', bad)

if __name__ == '__main__':
    main()
