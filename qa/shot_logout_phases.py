#!/usr/bin/env python3
"""Visual probe: in-topbar logout farewell phase screenshots with the wall-clock
finish defused, so each phase can be sought and captured at leisure. Not an
assertion harness — qa_logout.py does the asserting. Writes qa/logout-phase-*.png
(full page) plus qa/logout-topbar-*.png (2x zoom of the top bar)."""
import json, subprocess, time, urllib.request, shutil, os, base64, sys
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
QA = os.path.dirname(os.path.abspath(__file__))

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

def j(c, expr):
    expr = "(function(){" + expr + "})()"
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
    if r and 'exceptionDetails' in r: return 'THREW'
    return (r or {}).get('result', {}).get('value')

def main():
    width, theme = (int(sys.argv[1]), sys.argv[2]) if len(sys.argv) > 2 else (390, 'dark')
    height = 844
    port = 9501
    prof = '/tmp/hubqa-lophase'; shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={port}', '--remote-allow-origins=*', f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = json.load(urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=10))
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        c = CDP(tgt['webSocketDebuggerUrl']); c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': width, 'height': height, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(0.5)
        for _ in range(60):
            if j(c, "return !!(window.HUB&&HUB.store&&HUB.auth&&HUB.logout);"): break
            time.sleep(0.5)
        j(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
             "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') +
             ";HUB.store.save();HUB.applyTheme();")
        for _ in range(20):
            if j(c, "return !document.getElementById('splash');"): break
            time.sleep(0.5)
        j(c, """var st=HUB.store.state; st.auth=st.auth||{users:[],session:null};
st.auth.users=[{id:'q1',name:'Q',email:'q@e.com',phoneE164:'',cc:'US',pw:'x',salt:'x',campus:'',verifiedVia:'email',faceId:null,createdAt:Date.now()}];
st.auth.session={uid:'q1',at:Date.now(),remember:true}; HUB.store.save(); HUB.auth.restore();
window.__gateSkip=true; try{HUB.auth.close()}catch(e){}
var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1;""")
        time.sleep(0.5)
        def shot(name):
            print('pre-shot strip:', j(c, "return !!document.getElementById('loStrip');"), name)
            time.sleep(0.6)  # let the compositor paint the sought pose
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            raw = base64.b64decode(r['data'])
            p = os.path.join(QA, name + '.png')
            open(p, 'wb').write(raw)
            # 2x zoom of the top bar for close inspection
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(raw))
                wpx, _ = img.size
                crop = img.crop((0, 0, wpx, int(wpx * 0.42)))
                crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
                crop.save(os.path.join(QA, name.replace('logout-phase-', 'logout-topbar-') + '.png'))
            except Exception as e:
                print('zoom skipped:', e)
            print('saved', p)
        # idle: the door button with Logout written on it, sitting in the top bar
        shot(f'logout-phase-door-{width}-{theme}')
        # capture + defuse the wall-clock finish so the strip can't vanish mid-shoot
        j(c, "window.__loTids=[];window.__oST=window.setTimeout;"
             "window.setTimeout=function(fn,ms){var id=window.__oST(fn,ms);"
             "if(ms>=2500&&ms<=4000)window.__loTids.push(id);return id;};"
             "document.getElementById('logoutBtn').click(); return 1;")
        for _ in range(40):
            if j(c, "return !!document.getElementById('loStrip');"): break
            time.sleep(0.15)
        j(c, "window.__loTids.forEach(function(id){clearTimeout(id);});"
             "window.setTimeout=window.__oST; return window.__loTids.length;")
        print('defused, strip:', j(c, "return !!document.getElementById('loStrip');"))
        def seek_sel(sel, t):
            j(c, f"document.querySelectorAll('{sel}').forEach(function(e){{"
                 f"e.getAnimations().forEach(function(a){{a.pause();a.currentTime={t};}});}}); return 1;")
        def seek_man(t):
            seek_sel('.lo-strip .lo-man', t)
        def seek_door(t):
            seek_sel('.lo-strip .lo-door', t)
        def seek_glow(t):
            seek_sel('.lo-strip .lo-glow', t)
        def seek_shadow(t):
            seek_sel('.lo-strip .lo-manshadow', t)
        def seek_wave(t):
            # the wave animation is dropped from getAnimations() once it finishes on the
            # CSS clock, so restart the real lo-wave animation and then seek the fresh one.
            # Each step MUST be its own CDP call; poll for the fresh animation.
            j(c, "var g=document.querySelector('.lo-strip .lo-waveg'); if(g){g.style.animation='none';} return 1;")
            j(c, "var g=document.querySelector('.lo-strip .lo-waveg'); if(g){void g.offsetWidth; g.style.animation='';} return 1;")
            for _ in range(20):
                n = j(c, "var g=document.querySelector('.lo-strip .lo-waveg'); return g?g.getAnimations().length:0;")
                if isinstance(n, int) and n > 0: break
                time.sleep(0.15)
            j(c, f"var g=document.querySelector('.lo-strip .lo-waveg'); if(g)"
                 f"g.getAnimations().forEach(function(a){{a.pause();a.currentTime={t};}}); return 1;")
        seek_man(800); seek_shadow(800); shot(f'logout-phase-walk-{width}-{theme}')
        seek_door(1600); seek_glow(1600); shot(f'logout-phase-dooropen-{width}-{theme}')
        seek_man(2000); seek_shadow(2000); seek_wave(2000); seek_door(2000); seek_glow(2000)
        shot(f'logout-phase-wave-{width}-{theme}')
        seek_door(2800); seek_man(2800); seek_shadow(2800); seek_glow(2800)
        shot(f'logout-phase-enter-{width}-{theme}')
        seek_door(3450); seek_man(3200); seek_shadow(3200)
        shot(f'logout-phase-shut-{width}-{theme}')
        print('done')
    finally:
        try: proc.terminate()
        except Exception: pass

if __name__ == '__main__':
    main()
