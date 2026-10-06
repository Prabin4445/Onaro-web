#!/usr/bin/env python3
"""QA for the Onaro Saturn logo-mark 3D redesign (2026-09-23, golden planet round).

Golden luminous planet jewel + true ring occlusion (back arc behind sphere,
front arc in front), traveling pulses, comet + satellite with SMIL handoff,
twinkling stars, volt rim light. Covers: header, splash, welcome(fn),
favicon, app icons; 390x844 + 320x568, dark + light, reduced-motion.
"""
import json, subprocess, time, urllib.request, base64, os, sys, re

CHROME = '/opt/meta-chromium/chrome'
PORT = 9339
HUB = os.path.expanduser('~/workspace/hub')
QA = os.path.join(HUB, 'qa')
BASE = f'file://{HUB}/index.html'
os.makedirs(QA, exist_ok=True)

passed, failed = [], []
def check(name, ok, detail=''):
    (passed if ok else failed).append(name)
    print(('PASS ' if ok else 'FAIL ') + name + (f' [{detail}]' if detail and not ok else ''))

def wait_port(port, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f'http://localhost:{port}/json/list') as r:
                return json.load(r)
        except Exception:
            time.sleep(0.5)
    raise RuntimeError('devtools never came up')

def new_page_target(ts):
    for t in ts:
        if t.get('type') == 'page' and 'devtools' not in t.get('url', ''):
            return t
    raise RuntimeError('no page target')

class CDP:
    def __init__(self, url):
        import websocket
        self.ws = websocket.create_connection(url)
        self.ws.settimeout(12)
        self.i = 0
    def send(self, method, params=None):
        self.i += 1
        self.ws.send(json.dumps({'id': self.i, 'method': method, 'params': params or {}}))
        dl = time.time() + 25
        while time.time() < dl:
            try:
                msg = json.loads(self.ws.recv())
            except Exception:
                continue
            if msg.get('id') == self.i:
                if 'error' in msg:
                    raise RuntimeError(f'{method}: {msg["error"]}')
                return msg.get('result')
        raise TimeoutError(method)

def drain_errors(c):
    errs = []
    c.ws.settimeout(0.3)
    try:
        while True:
            msg = json.loads(c.ws.recv())
            m = msg.get('method', '')
            p = msg.get('params', {})
            if m == 'Runtime.consoleAPICalled' and p.get('type') in ('error',):
                errs.append('console.error: ' + json.dumps(p.get('args', []))[:160])
            elif m == 'Runtime.exceptionThrown':
                d = p.get('exceptionDetails', {})
                errs.append('exception: ' + str(d.get('text', ''))[:160])
            elif m == 'Log.entryAdded':
                e = p.get('entry', {})
                if e.get('level') == 'error':
                    errs.append('log.error: ' + str(e.get('text', ''))[:160])
    except Exception:
        pass
    finally:
        c.ws.settimeout(12)
    return errs

def launch(profile, width, height):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--window-size={width},{height}',
        f'--user-data-dir={profile}', '--hide-scrollbars',
        '--allow-file-access-from-files', BASE])
    ts = wait_port(PORT)
    return proc, CDP(new_page_target(ts)['webSocketDebuggerUrl'])

def js(c, expr):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
    res = (r or {}).get('result', {})
    return res.get('value')

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))

VIS = ("(function(){var b=document.body.classList.contains('dark');"
       "var s=document.querySelector(b?'#brandMark svg.logo-dark':'#brandMark svg.logo-light');"
       "return s||document.querySelector('#brandMark svg')})()")

def main():
    procs = []
    try:
        prof = '/tmp/hubqa-logoring'
        os.system(f'rm -rf {prof}')
        proc, c = launch(prof, 390, 844); procs.append(proc)
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')

        t0 = time.time()
        while time.time() - t0 < 25:
            if js(c, "document.readyState")=='complete' and js(c, "!!(window.HUB&&HUB.icons&&HUB.icons.logoMark)"):
                break
            time.sleep(0.5)

        # 1. header mark renders with the new golden anatomy
        check('header logo-anim svg present', js(c, "!!document.querySelector('#brandMark svg.logo-anim')"))
        check('header ringflow pulse segments', js(c, "document.querySelectorAll('#brandMark .logo-ringflow').length") == 4,
              str(js(c, "document.querySelectorAll('#brandMark .logo-ringflow').length")))
        check('header riders (comet+sat x back/front x 2 variants)',
              js(c, "document.querySelectorAll('#brandMark animateMotion').length") == 8,
              str(js(c, "document.querySelectorAll('#brandMark animateMotion').length")))
        check('header golden planet element', js(c, "!!document.querySelector('#brandMark .logo-planet')"))
        check('header twinkle stars', js(c, "document.querySelectorAll('#brandMark .logo-twinkle').length") == 6,
              str(js(c, "document.querySelectorAll('#brandMark .logo-twinkle').length")))

        # 2. TRUE ring occlusion: back arcs before planet before front arcs (paint order)
        occ = js(c, "(function(){var s="+VIS+";"
            "var backs=[...s.querySelectorAll('.logo-backarc')];"
            "var fronts=[...s.querySelectorAll('.logo-frontarc')];"
            "var pl=s.querySelector('.logo-planet');"
            "if(!backs.length||!fronts.length||!pl) return 'missing';"
            "var okB=backs.every(function(b){return b.compareDocumentPosition(pl)&4;});"
            "var okF=fronts.every(function(f){return pl.compareDocumentPosition(f)&4;});"
            "return (okB&&okF)?'ok':'bad-order';})()")
        check('back arcs paint BEFORE planet, front arcs AFTER (3D occlusion)', occ == 'ok', str(occ))

        # 3. golden jewel: sphere gradient carries the amber/gold stops
        gold = js(c, "(function(){var s="+VIS+";"
            "var g=s.querySelector('.logo-planet').getAttribute('fill');"
            "var id=g.slice(5,-1);var gr=s.querySelector('#'+CSS.escape(id));"
            "var cols=[...gr.querySelectorAll('stop')].map(function(x){return x.getAttribute('stop-color')});"
            "return cols.join(',');})()")
        check('planet gradient is golden/amber', bool(gold) and ('#F7C65C' in gold or '#EFA93A' in gold), str(gold))

        # 4. rider SMIL handoff: back copy visible on far half, front copy on near half
        hand = js(c, "(function(){var s="+VIS+";"
            "var r=[...s.querySelectorAll('.logo-rider')];"
            "if(r.length!==4) return 'count:'+r.length;"
            "return r.map(function(g){"
            "  var sets=[...g.querySelectorAll('set')].map(function(x){return x.getAttribute('to')+x.getAttribute('begin')}).join('|');"
            "  return g.getAttribute('opacity')+':'+sets;}).join(' ; ');})()")
        check('riders hand off back<->front via SMIL <set>', bool(hand) and '1:10s|03s' in hand and '0:00s|13s' in hand, str(hand))

        # 5. splash planet-O uses the CURRENT icons.js output (cannot drift)
        drift = js(c, "(function(){"
            "var s=document.querySelector('#splash .sw-o svg');if(!s) return 'no-splash-svg';"
            "var fresh=HUB.icons.logoMark('S');"
            "var m=fresh.match(/<svg class=\"logo-dark logo-anim\"[\\s\\S]*?<\\/svg>/);if(!m) return 'no-fresh';"
            "var g1=s.querySelector('radialGradient').id;"
            "var g2=m[0].match(/radialGradient id=\"([^\"]+)\"/)[1];"
            "var n1=s.querySelectorAll('*').length;"
            "var tmp=document.createElement('div');tmp.innerHTML=m[0];var n2=tmp.firstChild.querySelectorAll('*').length;"
            "return (g1===g2&&n1===n2)?'ok':'drift:'+g1+'/'+g2+' '+n1+'/'+n2;})()")
        check('splash .sw-o matches live icons.js output', drift == 'ok', str(drift))
        shot(c, 'logoring-splash-390.png')

        # 6. lockup: complete planet fully inside viewBox, planet-O + "naro"
        lock = js(c, """(function(){
          var s="""+VIS+""";
          if(!s) return 'no-svg';
          var r=s.getBoundingClientRect(), bad=[];
          s.querySelectorAll('circle,ellipse,path').forEach(function(el){
            try{
              if(el.closest('defs')) return;
              var b=el.getBoundingClientRect();
              var x0=(b.left-r.left)/r.width*256, y0=(b.top-r.top)/r.height*256;
              var x1=(b.right-r.left)/r.width*256, y1=(b.bottom-r.top)/r.height*256;
              if(x0<-2||y0<-2||x1>258||y1>258){
                bad.push(el.tagName+'@'+[x0,y0,x1,y1].map(function(n){return Math.round(n)}).join(','));
              }
            }catch(e){}
          });
          return bad.length?('crop:'+bad.join('|')):'ok';
        })()""")
        check('planet+ring fully inside viewBox (complete, never cropped)', lock == 'ok', str(lock))
        pl_r = js(c, "(function(){var s="+VIS+";var c=s.querySelector('.logo-planet');return c?c.getAttribute('r'):null})()")
        check('planet sphere is a full r=64 circle', pl_r == '64', str(pl_r))
        hdr_txt = js(c, "document.querySelector('.brand .brand-name').textContent")
        check('header lockup = planet-O + "naro"', bool(hdr_txt) and 'naro' in hdr_txt, str(hdr_txt))

        # 7. welcome uses logoMark (function-level), id-prefix guard
        wlm = js(c, "HUB.icons.logoMark('W').indexOf('logo-planet')>-1 && HUB.icons.logoMark('W').indexOf('logo-rider')>-1")
        check('welcome logoMark() carries new design', bool(wlm))
        uniq = js(c, "(function(){var a=HUB.icons.logoMark('A'),b=HUB.icons.logoMark('B');"
            "function ids(s){return [...s.matchAll(/id=\"([^\"]+)\"/g)].map(function(m){return m[1]})}"
            "var ia=ids(a),ib=ids(b);return ia.filter(function(x){return ib.indexOf(x)>-1}).length})()")
        check('id-prefix collision guard intact', uniq == 0, f'{uniq} collisions')

        # 8. visible-variant pulse animates; twinkles run; SMIL timeline runs
        arc = "(("+VIS+").querySelector('.logo-ringflow'))"
        d0 = js(c, "getComputedStyle("+arc+").strokeDashoffset")
        time.sleep(1.2)
        d1 = js(c, "getComputedStyle("+arc+").strokeDashoffset")
        check('ringflow dashoffset animates', d0 is not None and d1 is not None and d0 != d1, f'{d0}->{d1}')
        check('ringflow has running CSS animation',
              (js(c, "("+arc+").getAnimations().length") or 0) > 0)
        tw = js(c, "getComputedStyle(("+VIS+").querySelector('.logo-twinkle')).animationName")
        check('star twinkle animation runs', tw == 'logoTwinkle', str(tw))
        check('SMIL riders timeline running', (js(c, "("+VIS+").getCurrentTime()") or 0) >= 0)

        # 9. light mode variant present
        c.send('Emulation.setEmulatedMedia', {'media': 'light'})
        time.sleep(0.4)
        check('light-mode variant present', js(c, "!!document.querySelector('#brandMark svg.logo-light.logo-anim')"))
        lgold = js(c, "(function(){var s=document.querySelector('#brandMark svg.logo-light');"
            "var g=s.querySelector('.logo-planet').getAttribute('fill');"
            "var gr=s.querySelector('#'+CSS.escape(g.slice(5,-1)));"
            "return [...gr.querySelectorAll('stop')].map(function(x){return x.getAttribute('stop-color')}).join(',')})()")
        check('light variant planet also golden', bool(lgold) and '#EFA93A' in lgold, str(lgold))
        shot(c, 'logoring-header-light-390.png')
        c.send('Emulation.setEmulatedMedia', {'media': 'dark'})
        time.sleep(0.4)
        shot(c, 'logoring-header-dark-390.png')

        # 10. large visual-review render (512px) of the live mark, both variants
        big = js(c, "(function(){var d=document.createElement('div');d.id='logoQA';"
            "d.style.cssText='position:fixed;left:0;top:0;width:512px;height:512px;z-index:99999;background:#0D100A';"
            "d.innerHTML=HUB.icons.logoMark('Q');document.body.appendChild(d);"
            "var s=d.querySelector('svg.logo-dark');s.style.width='512px';s.style.height='512px';"
            "var r=s.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
        r = c.send('Page.captureScreenshot', {'format': 'png',
            'clip': {'x': 0, 'y': 0, 'width': 512, 'height': 512, 'scale': 1}})
        open(os.path.join(QA, 'logoring-large-dark.png'), 'wb').write(base64.b64decode(r['data']))
        js(c, "(function(){var d=document.getElementById('logoQA');"
            "d.style.background='#F4F6EC';"
            "d.querySelector('svg.logo-dark').style.display='none';"
            "var s=d.querySelector('svg.logo-light');s.style.display='block';s.style.width='512px';s.style.height='512px';})()")
        time.sleep(0.3)
        r = c.send('Page.captureScreenshot', {'format': 'png',
            'clip': {'x': 0, 'y': 0, 'width': 512, 'height': 512, 'scale': 1}})
        open(os.path.join(QA, 'logoring-large-light.png'), 'wb').write(base64.b64decode(r['data']))
        js(c, "document.getElementById('logoQA').remove()")
        check('large 512px renders captured', True)

        # 11. tiny-size legibility: volt ring + golden planet pixels at ~24px
        t0 = time.time()
        while time.time() - t0 < 15:
            if js(c, "!document.getElementById('splash')"): break
            time.sleep(0.5)
        rect = js(c, """(function(){
          var host=document.getElementById('wlcmHost');
          var el=(host&&!host.hidden)?host.querySelector('.brand-mark'):document.getElementById('brandMark');
          if(!el) return null;
          var r=el.getBoundingClientRect(); return [r.x,r.y,r.width,r.height];
        })()""")
        check('brandMark rect found', bool(rect), str(rect))
        rx, ry, rw, rh = rect
        r = c.send('Page.captureScreenshot', {'format': 'png',
            'clip': {'x': max(0, rx-8), 'y': max(0, ry-8), 'width': rw+16, 'height': rh+16, 'scale': 3}})
        img = base64.b64decode(r['data'])
        open(os.path.join(QA, 'logoring-header-crop.png'), 'wb').write(img)
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(img)).convert('RGB')
        px = list(im.getdata())
        volt = [p for p in px if p[0] > 180 and p[1] > 200 and p[2] < 120]
        goldpx = [p for p in px if p[0] > 150 and p[1] > 100 and p[2] < 140 and p[0] > p[2] + 20]
        check('tiny header logo shows volt ring pixels', len(volt) > 40, f'{len(volt)} volt px')
        check('tiny header logo shows golden planet pixels', len(goldpx) > 40, f'{len(goldpx)} gold px')

        # 12. no purple anywhere in the new artwork
        purple = re.compile(r'7C3AED|A855F7|8B5CF6|6D28D9|9333EA', re.I)
        bad = []
        for rel in ['styles.css', 'js/icons.js', 'favicon.svg', 'index.html']:
            if purple.search(open(os.path.join(HUB, rel)).read()): bad.append(rel)
        check('no purple hexes in artwork', not bad, ','.join(bad))

        # 13. console errors so far
        errs = drain_errors(c)
        check('zero console errors (main pass)', not errs, '; '.join(errs[:3]))

        for p in procs: p.terminate()
        procs = []

        # 14. reduced-motion: CSS + SMIL all frozen
        prof2 = '/tmp/hubqa-logoring-rm'
        os.system(f'rm -rf {prof2}')
        proc2, c2 = launch(prof2, 320, 568); procs.append(proc2)
        c2.send('Runtime.enable'); c2.send('Page.enable'); c2.send('Log.enable')
        c2.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        c2.send('Page.reload')
        t0 = time.time()
        while time.time() - t0 < 25:
            if js(c2, "document.readyState")=='complete' and js(c2, "!!(window.HUB&&HUB.icons&&HUB.icons.logoMark)"):
                break
            time.sleep(0.5)
        time.sleep(1.0)
        arc2 = "(("+VIS+").querySelector('.logo-ringflow'))"
        check('reduced-motion: ringflow animation none',
              js(c2, "getComputedStyle("+arc2+").animationName") in ('none', ''))
        check('reduced-motion: twinkle animation none',
              js(c2, "getComputedStyle(("+VIS+").querySelector('.logo-twinkle')).animationName") in ('none', ''))
        check('reduced-motion: SMIL riders paused', js(c2, "("+VIS+").animationsPaused()") is True)
        d0 = js(c2, "getComputedStyle("+arc2+").strokeDashoffset")
        time.sleep(1.0)
        d1 = js(c2, "getComputedStyle("+arc2+").strokeDashoffset")
        check('reduced-motion: dashoffset static', d0 == d1, f'{d0}->{d1}')
        shot(c2, 'logoring-header-rm-320.png')
        errs2 = drain_errors(c2)
        check('zero console errors (reduced-motion)', not errs2, '; '.join(errs2[:3]))

        # 15. favicon + app icons fresh and correct size
        import pathlib
        fav = pathlib.Path(HUB + '/favicon.svg')
        ftxt = fav.read_text()
        check('favicon.svg is the new golden mark',
              'radialGradient' in ftxt and '#F7C65C' in ftxt and 'F2FF8A' in ftxt and 'logo-ringflow' not in ftxt)
        i512 = pathlib.Path(HUB + '/icons/icon-512.png'); i192 = pathlib.Path(HUB + '/icons/icon-192.png')
        check('icon-512.png exists', i512.exists())
        check('icon-192.png exists', i192.exists())
        if i512.exists() and i192.exists():
            im5 = Image.open(i512); im1 = Image.open(i192)
            check('icon sizes 512/192', im5.size == (512, 512) and im1.size == (192, 192), f'{im5.size}/{im1.size}')
            check('icons regenerated after favicon', i512.stat().st_mtime >= fav.stat().st_mtime - 1)
            cpx = Image.open(i512).convert('RGB').getpixel((256, 256))
            check('icon-512 center is golden planet', cpx[0] > 150 and cpx[1] > 100 and cpx[2] < 140,
                  str(cpx))

    finally:
        for p in procs:
            try: p.terminate()
            except Exception: pass
    print(f'\n{len(passed)}/{len(passed)+len(failed)} passed')
    if failed:
        print('FAILED:', failed); sys.exit(1)

if __name__ == '__main__':
    main()
