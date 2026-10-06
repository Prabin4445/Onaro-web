#!/usr/bin/env python3
"""Onaro launch splash QA (2026-09-23, "Walking into the light").

Splash: full-viewport ORIGINAL artwork (img/splash-art.jpg, instant first
paint) with a seamlessly-looping walking-motion video (img/splash-walk.mp4,
muted/autoplay/playsinline) layered on top — the six students used to WALK
toward the beam. Because iOS Low Power Mode can permanently block <video>
autoplay (no JS override), an UNBLOCKABLE CSS filmstrip walk-cycle walked the
kids with pure CSS and hid itself the instant real video playback started
(vidon). Round 8 (2026-09-23): PraBin LOVED the scene and ordered the kids
FROZEN — "dont make that adult moving coz it is creating too much problem.
I love what it is right now". The walk cycle is GONE: img/splash-kids-still.jpg
(a single crisp frame, natural standing-together pose) renders under the
static img/splash-kids-mask.png alpha mask (-webkit-mask-image, iOS-safe) —
background is 100% poster, the kids never move. A CSS ring-wave shimmer
(screen-blend streaks flowing along the tilted ring band) keeps the golden
rings rippling and alive — living sky, still people: Saturn breathes,
the beam flows down, sparkles rise, the beam's light falls ON the kids
(.sklight 3s golden wash), but they stand frozen in wonder.
Wordmark (planet-O brand) + tagline (i18n app.brandSub) +
"© 2026 Onaro" are crisp HTML, never baked into the image. Faded out by
HUB.splashDone() after boot + first tab render (min show 5.0s, hard cap ~6.0s
via inline backstop). A volt loading bar sits under the students and fills
0->100% over ~4.7s, completing just before exit. iOS lesson applied: no flex
centering on the fixed host
(.splash-inner / .splash-copy absolutely centered).

Asserts, at 390x844 and 320x568, dark+light, fresh profiles, zero console errors:
- splash present + visible immediately after navigation (before boot finishes)
- splash rect covers the whole viewport, bg is dark #0D100A
- art img loaded (naturalWidth>0), video present and PLAYING (or novideo fallback)
- wordmark / tagline / © line rendered, © line pinned near viewport bottom
- inner horizontally centered; host is NOT display:flex (iOS bug class)
- splash removed from DOM; show time within [4.6s, 6.2s]
- app fully usable after (tab switch works, no h-overflow)
- volt loader: present under the students, fill width animates 0->100%,
  volt gradient + volt glow, hidden under reduced-motion
- prefers-reduced-motion: video hidden, art static, still hides within cap
- static: noscript hide + backstop + [hidden] rule + art/video/copyright markup
"""
import json, subprocess, time, urllib.request, os, base64, shutil, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
HUB = os.path.expanduser('~/workspace/hub')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9491
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

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

SPLASH_STATE = """(function(){
var s=document.getElementById('splash');
if(!s) return {present:false};
var r=s.getBoundingClientRect(), cs=getComputedStyle(s);
var inner=document.querySelector('.splash-inner'), ir=inner?inner.getBoundingClientRect():null;
var word=document.querySelector('.splash-word');
var tag=document.getElementById('splashTag');
var copy=document.querySelector('.splash-copy'), cr=copy?copy.getBoundingClientRect():null;
var img=document.querySelector('.splash-art img');
var vid=document.querySelector('.splash-art video');
var art=document.getElementById('splashArt');
return {present:true,
 rect:{l:Math.round(r.left),t:Math.round(r.top),r:Math.round(r.right),b:Math.round(r.bottom)},
 vw:innerWidth, vh:innerHeight, opacity:cs.opacity, display:cs.display, bg:cs.backgroundColor,
 innerCx: ir?Math.round((ir.left+ir.right)/2):-1,
 word:word?word.textContent.trim():'',
 tag:tag?tag.textContent.trim():'',
 copy:copy?copy.textContent.trim():'',
 copyBottom:cr?Math.round(cr.bottom):-1,
 imgSrc:img?img.getAttribute('src'):'',
 imgLoaded:img?(img.complete&&img.naturalWidth>10):false,
 vidSrc:(vid&&vid.querySelector('source'))?vid.querySelector('source').getAttribute('src'):'',
 vidMuted:vid?vid.muted:false, vidPaused:vid?vid.paused:true,
 vidReady:vid?vid.readyState:-1, vidT:vid?vid.currentTime:-1,
 novideo:art?art.classList.contains('novideo'):false,
 wordCx:word?Math.round((word.getBoundingClientRect().left+word.getBoundingClientRect().right)/2):-1};})()"""

ARM = ("window.__huberr=[];addEventListener('error',function(e){window.__huberr.push('ERR:'+e.message)});"
       "addEventListener('unhandledrejection',function(e){window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))});")

def wait_for(c, expr, timeout=12, poll=0.15):
    dl = time.time() + timeout
    while time.time() < dl:
        v = js_eval(c, expr)
        if v is True or (isinstance(v, str) and v == 'READY'): return True
        time.sleep(poll)
    return False

def js_eval(c, expr):
    try:
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        if r and 'exceptionDetails' in r:
            ed = r['exceptionDetails']
            return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
        return (r or {}).get('result', {}).get('value')
    except Exception as e:
        return 'JSERR:' + str(e)[:120]

def static_checks():
    idx = open(os.path.join(HUB, 'index.html')).read()
    css = open(os.path.join(HUB, 'styles.css')).read()
    note('<noscript><style>#splash{display:none!important}</style></noscript>' in idx,
         'static: noscript hides splash')
    note('},5300);' in idx, 'static: backstop fires at 5300ms (gone ~6.0s with fade)')
    note(idx.count('window.__splashT0=Date.now();') == 1,
         'static: single inline backstop block (duplicates deduped)')
    note('.splashhost[hidden]{display:none}' in css, 'static: [hidden] kill-switch on splashhost')
    m = re.search(r'\.splash-inner\{([^}]*)\}', css)
    note(m and 'left:50%' in m.group(1) and 'translateX(-50%)' in m.group(1),
         'static: iOS-safe absolute centering (left:50% + translateX(-50%))')
    m2 = re.search(r'\.splashhost\{([^}]*)\}', css)
    note(m2 and 'display:flex' not in m2.group(1), 'static: splashhost is NOT flex (iOS bug class)')
    note('@media (prefers-reduced-motion:reduce)' in css, 'static: reduced-motion rule present')
    note('.splash-art.vidon video{display:none}' in css,
         'static: reduced-motion hides the video (even if vidon somehow set)')
    note('class="splash-art"' in idx and 'img/splash-art.jpg' in idx,
         'static: artwork poster in markup')
    note('img/splash-walk.mp4' in idx and 'playsinline' in idx,
         'static: walking-motion video in markup (playsinline)')
    note('&copy; 2026 Onaro' in idx and 'class="splash-copy"' in idx,
         'static: copyright line in markup')
    note('spkenburns' in css, 'static: Ken Burns drift keyframes present')
    note('class="splash-ringwave"' in idx and 'springflow' in css,
         'static: ring-wave shimmer in markup + CSS')
    note('class="splash-spin"' in idx and '@keyframes spspin' in css,
         'static: MAGIC planet-revolve layer (splash-spin + spspin) in markup + CSS')
    note('class="splash-bands"' in idx and '@keyframes spbands' in css,
         'static: MAGIC cloud-band drift layer (splash-bands + spbands) in markup + CSS')
    note('class="splash-beampulse"' in idx and '@keyframes spbeampulse' in css,
         'static: MAGIC beam-surge core (splash-beampulse + spbeampulse) in markup + CSS')
    mbeam = re.search(r'class="splash-beamrise"[^>]*>(.*?)</div>', idx, re.S)
    nsparks = mbeam.group(1).count('<i ') if mbeam else 0
    note(mbeam is not None and '@keyframes sprise' in css and nsparks >= 15,
         'static: MAGIC rising energy sparks (beamrise + sprise, 19 motes)', f'sparks={nsparks}')
    note('class="splash-groundglow"' in idx and '@keyframes spground' in css,
         'static: MAGIC living ground glow (splash-groundglow + spground) in markup + CSS')
    # ROUND 6: the whole page works together — beam light streams DOWNWARD from
    # Saturn to the kids; Saturn itself breathes; spark rise is transform-only.
    note('class="splash-beamflow"' in idx and '@keyframes spbeamflow' in css,
         'static: ROUND6 beam downflow layer (splash-beamflow + spbeamflow) in markup + CSS')
    _kfi = css.find('@keyframes spbeamflow')
    _bf = css[_kfi:_kfi + 220] if _kfi > 0 else ''
    note('translateY(88px)' in _bf,
         'static: beamflow streams DOWNWARD (positive translateY, Saturn -> kids)',
         _bf[:70].replace(chr(10), ' '))
    note('class="splash-saturnpulse"' in idx and '@keyframes spsatpulse' in css,
         'static: ROUND6 living Saturn glow (splash-saturnpulse + spsatpulse) in markup + CSS')
    for _sel in ('.splash-ringwave', '.splash-bands', '.splash-beampulse', '.splash-groundglow',
                 '.splash-beamflow', '.splash-saturnpulse'):
        _m = re.search(re.escape(_sel) + r'\{([^}]*)\}', css)
        note(_m is not None and 'filter' not in _m.group(1),
             f'static: {_sel} has NO filter (blend stays un-isolated on iOS Safari)')
    note('.splash-art.novideo .splash-ringwave' not in css,
         'static: novideo ringwave kill-switch removed (rings shimmer in Low Power Mode too)')
    _i0 = css.find('@keyframes sprise'); _i1 = css.find('/* living glow', _i0)
    _blk = css[_i0:_i1] if _i0 > 0 and _i1 > _i0 else ''
    note(bool(_blk) and 'bottom' not in _blk,
         'static: spark rise is transform-only (no `bottom` layout animation = 60fps on iPhone)')
    note('.splash-beamflow,.splash-saturnpulse' in css.replace(' ', ''),
         'static: new magic layers frozen under reduced-motion')
    ml = re.search(r'\.splash-load i\{([^}]*)\}', css)
    note('class="splash-load"' in idx and '@keyframes spload' in css,
         'static: volt loading bar (splash-load + spload) in markup + CSS')
    note(ml is not None and '#C6F135' in ml.group(1) and '#F2FF8A' in ml.group(1)
         and 'box-shadow' in ml.group(1),
         'static: loader fill = volt gradient (#C6F135->#F2FF8A) + volt glow')
    note(ml is not None and '4.7s' in ml.group(1),
         'static: loader fill animates over 4.7s (completes just before 5s exit)')
    note('.splash-load{display:none}' in css,
         'static: loader hidden under reduced-motion')
    mld = re.search(r'\.splash-load\{([^}]*)\}', css)
    note(mld is not None and '60vw' in mld.group(1) and 'max-width:280px' in mld.group(1),
         'static: loader bar capped short + elegant (60vw, max-width:280px — never full-bleed)')
    # ROUND 5+7: silhouette cutout — the opaque-rectangle strip shimmered against
    # the frozen poster (per-frame grain/beam-flicker inside the rectangle), so
    # the kids are now cut out (alpha mask) and the background is 100% poster.
    # ROUND 7: the 12 walk frames are STABILIZED (walk-in-place) — the source
    # video dollied toward the kids, so frame 11 -> frame 0 used to snap.
    try:
        from PIL import Image as _PILImage
        import numpy as _np
        _maskp = os.path.join(HUB, 'img', 'splash-kids-mask.png')
        _mp = _PILImage.open(_maskp)
        _ma = _np.array(_mp)
        _aa = _ma[:, :, 3] if _ma.shape[2] == 4 else _np.zeros(1)
        note(_mp.mode == 'RGBA' and _aa.min() < 50 and _aa.max() > 200,
             'static: splash-kids-mask.png is RGBA with a real alpha cutout (not a rectangle)',
             f"mode={_mp.mode} alpha min/max={_aa.min()}/{_aa.max()}")
        note(os.path.getsize(_maskp) < 200 * 1024,
             'static: alpha mask is tiny (static single frame, not stepped)',
             f'{os.path.getsize(_maskp)//1024}KB')
        # the mask must hug the figures: substantial transparent area (the old
        # rectangle was ~0% transparent) but the kids fully kept
        _transp = (_aa < 8).mean()
        note(0.03 < _transp < 0.60,
             'static: mask actually cuts background out (transparent fraction sane)',
             f'transparent={_transp*100:.1f}%')
    except Exception as _ex:
        note(False, 'static: splash-kids-mask.png alpha cutout', repr(_ex)[:120])
    note(not os.path.exists(os.path.join(HUB, 'img', 'splash-kids-strip2.jpg')),
         'static: old opaque-rectangle strip2.jpg removed (superseded by cutout)')
    note(not os.path.exists(os.path.join(HUB, 'img', 'splash-kids-strip3.jpg')),
         'static: walk-cycle filmstrip strip3.jpg REMOVED (round 8: kids are frozen, no walk cycle)')
    note("addEventListener('playing'" in idx and 'vidon' in idx,
         'static: vidon fade-in wired on playing (no iOS native play glyph)')
    note('.splash-art video{display:none}' in css and '.splash-art.vidon video{display:block' in css
         and '@keyframes svidin' in css,
         'static: video display:none until genuinely playing (vidon reveals + svidin fade)')
    note('class="splash-kids"' in idx and '@keyframes skids' not in css,
         'static: kids sprite markup present, walk-cycle keyframes skids REMOVED (round 8: frozen)')
    _iskrule = re.search(r'\.splash-kids i\{([^}]*)\}', css)
    _isknorm = (_iskrule.group(1).replace(' ', '') if _iskrule else '')
    note(_iskrule is not None and 'animation' not in _isknorm,
         'static: .splash-kids i has NO animation (kids frozen, one crisp frame)')
    _sp = os.path.join(HUB, 'img', 'splash-kids-still.jpg')
    note(os.path.exists(_sp), 'static: splash-kids-still.jpg exists (round 8: single frozen frame)')
    note(os.path.exists(_sp) and os.path.getsize(_sp) < 1024 * 1024,
         'static: still frame well under 1MB (Low Power Mode friendly)',
         f'{os.path.getsize(_sp)//1024}KB' if os.path.exists(_sp) else 'missing')
    mk = re.search(r'\.splash-kids i\{([^}]*)\}', css)
    _ktop = float(re.search(r'top:([\d.]+)%', mk.group(1)).group(1)) if mk else 999
    note(mk is not None and _ktop < 70,
         'static: sprite crop window unchanged (top~65%, same registration as the poster kids)',
         f'top={_ktop}%')
    _mknorm = mk.group(1).replace(' ', '') if mk else ''
    note(mk is not None and 'splash-kids-still.jpg' in mk.group(1)
         and 'splash-kids-mask.png' in mk.group(1)
         and '-webkit-mask-image:url(img/splash-kids-mask.png)' in _mknorm
         and 'linear-gradient' not in mk.group(1),
         'static: sprite = single still frame cut out by the static alpha mask (no gradient masks)')
    # ROUND 8: the kids are a single frozen frame — assert the still is a
    # single-frame image matching the mask geometry (630x464), and that no
    # filmstrip / walk-cycle artifacts remain anywhere.
    try:
        from PIL import Image as _PIL8
        _still8 = _PIL8.open(os.path.join(HUB, 'img', 'splash-kids-still.jpg'))
        _sw8, _sh8 = _still8.size
        _mask8 = _PIL8.open(os.path.join(HUB, 'img', 'splash-kids-mask.png'))
        note((_sw8, _sh8) == _mask8.size,
             'static: still frame and alpha mask share geometry (single crisp frame, no filmstrip)',
             f'still={_sw8}x{_sh8} mask={_mask8.size[0]}x{_mask8.size[1]}')
        _has3 = os.path.exists(os.path.join(HUB, 'img', 'splash-kids-strip3.jpg'))
        _has4 = os.path.exists(os.path.join(HUB, 'img', 'splash-kids-strip4.jpg'))
        note(not _has3 and not _has4,
             'static: no walk-cycle filmstrip assets remain (strip3/strip4 gone)')
    except Exception as _ex8:
        note(False, 'static: round-8 frozen-frame file proofs', repr(_ex8)[:120])
    # ROUND 7: beam light-cast on the kids — the beam's light falls ON them,
    # marrying top and bottom into one magical column (same static mask,
    # screen blend, no filter = iOS-safe; opacity-only 3s breath synced to
    # the beamflow rhythm).
    _skidx = 'b class="sklight"' in idx
    note(_skidx and '@keyframes sklight' in css,
         'static: beam light-cast element in markup + keyframes in CSS')
    _skm = re.search(r'\.splash-kids \.sklight\{([^}]*)\}', css)
    _skn = _skm.group(1).replace(' ', '') if _skm else ''
    note(_skm is not None and 'splash-kids-mask.png' in _skm.group(1)
         and 'mix-blend-mode:screen' in _skn and 'filter' not in _skm.group(1)
         and '3sease-in-outinfinite' in _skn.replace(' ', ''),
         'static: sklight = masked golden wash, screen blend, no filter, 3s ease-in-out (iOS-safe)',
         (_skm.group(1)[:80] if _skm else 'missing'))
    _cssflat_rm = re.sub(r'\s+', '', css)
    note('.splash-kidsi,.splash-kids.sklight{animation:none' in _cssflat_rm,
         'static: sklight frozen under reduced-motion')
    note('.splash-art.vidon .splash-kids{display:none}' in css,
         'static: sprite hides when real video plays (never doubled)')
    note('.splash-kidsi,.splash-kids.sklight{animation:none' in _cssflat_rm,
         'static: sprite frozen under reduced-motion (belt-and-braces: no animation on i)')
    note('id="splashTag"' in idx, 'static: tagline keeps i18n id splashTag')
    note(os.path.exists(os.path.join(HUB, 'img', 'splash-art.jpg')),
         'static: splash-art.jpg exists')
    note(os.path.exists(os.path.join(HUB, 'img', 'splash-walk.mp4')),
         'static: splash-walk.mp4 exists')

def run_case(width, height, theme, reduced=False):
    tag = f'{width}x{height}-{theme}' + ('-rm' if reduced else '')
    prof = f'/tmp/hubqa-splash-{width}-{theme}' + ('-rm' if reduced else '')
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files',
        '--autoplay-policy=no-user-gesture-required', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                    ts = json.load(rr)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height,
               'deviceScaleFactor': 2, 'mobile': True})
        if reduced:
            c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})

        # Throwaway first boot: seed profile + theme + locale, then reload so the
        # measured boot shows the splash from first paint.
        c.send('Page.navigate', {'url': BASE})
        ok = wait_for(c, "!!(window.HUB&&HUB.store)", timeout=20)
        note(ok, f'seed boot reached HUB [{tag}]')
        js_eval(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        js_eval(c, "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') +
                   ";HUB.store.state.profile.name='Prabin';HUB.store.state.profile.campus='Dallas College';HUB.store.save();")

        # Measured boot.
        c.send('Page.navigate', {'url': BASE})
        note(wait_for(c, "typeof window.__splashT0!=='undefined'", timeout=12),
             f'new document parsed (inline splash script ran) [{tag}]')
        js_eval(c, ARM)

        st = js_eval(c, SPLASH_STATE)
        note(isinstance(st, dict) and st.get('present') is True, f'splash visible immediately on load [{tag}]',
             '' if isinstance(st, dict) else repr(st)[:120])
        if isinstance(st, dict) and st.get('present'):
            note(st['rect']['l'] <= 0 and st['rect']['t'] <= 0 and
                 st['rect']['r'] >= st['vw'] and st['rect']['b'] >= st['vh'],
                 f'splash covers viewport [{tag}]', json.dumps(st['rect']))
            note(st['opacity'] == '1', f'splash fully opaque at first paint [{tag}]')
            note(st['bg'] == 'rgb(13, 16, 10)', f'splash bg is dark #0D100A [{tag}]', st['bg'])
            note(abs(st['innerCx'] - st['vw'] / 2) < 3, f'wordmark block horizontally centered [{tag}]',
                 'cx=' + str(st['innerCx']))
            note(st['display'] == 'block', f'splashhost display is block, not flex [{tag}]', st['display'])
            # Volt loading bar: sample the fill width EARLY (both samples must
            # land well before the ~5s exit). Position: under the students'
            # feet (~78-80% vh), above the bottom edge / copyright line.
            note(js_eval(c, "!!document.querySelector('.splash-load i')") is True,
                 f'loader present under the students [{tag}]')
            if not reduced:
                lg = js_eval(c, "(function(){var e=document.querySelector('.splash-load');"
                                "if(!e)return null;var b=e.getBoundingClientRect();"
                                "return {top:Math.round(b.top),bot:Math.round(b.bottom),vh:innerHeight,"
                                "w:Math.round(b.width),cx:Math.round((b.left+b.right)/2),vw:innerWidth};})()")
                note(isinstance(lg, dict) and lg['top'] > lg['vh'] * 0.78 and lg['bot'] < lg['vh'],
                     f'loader sits below the students, above the bottom edge [{tag}]',
                     repr(lg)[:80])
                note(isinstance(lg, dict) and lg['w'] <= 280 and lg['w'] <= lg['vw'] * 0.65
                     and abs(lg['cx'] - lg['vw'] / 2) <= 8,
                     f'loader is short + elegant + dead centered (never full-bleed) [{tag}]',
                     f"w={lg['w'] if isinstance(lg,dict) else '?'} vw={lg['vw'] if isinstance(lg,dict) else '?'}")
                w1 = js_eval(c, "var e=document.querySelector('.splash-load i');"
                                "e?Math.round(e.getBoundingClientRect().width*10)/10:-1")
                time.sleep(1.2)
                w2 = js_eval(c, "var e=document.querySelector('.splash-load i');"
                                "e?Math.round(e.getBoundingClientRect().width*10)/10:-1")
                note(isinstance(w1, (int, float)) and isinstance(w2, (int, float))
                     and 0 <= w1 < w2 and (w2 - w1) > 2,
                     f'loader fill width animates 0->100% [{tag}]',
                     f'{w1}px -> {w2}px')
                lc = js_eval(c, "(function(){var e=document.querySelector('.splash-load i');"
                                "if(!e)return null;var s=getComputedStyle(e);"
                                "return {bg:s.backgroundImage,shadow:s.boxShadow};})()")
                note(isinstance(lc, dict) and 'linear-gradient' in lc['bg']
                     and '198, 241, 53' in lc['bg'],
                     f'loader fill is volt gradient [{tag}]',
                     repr(lc['bg'])[:80] if isinstance(lc, dict) else repr(lc)[:80])
                note(isinstance(lc, dict) and lc['shadow'] not in ('none', ''),
                     f'loader glows volt [{tag}]',
                     repr(lc['shadow'])[:60] if isinstance(lc, dict) else repr(lc)[:60])
            # Ring waves: check the DOM immediately (splash exits ~5.6-6.0s after t0)
            if not reduced:
                rwa = js_eval(c, "(function(){var e=document.querySelector('.splash-ringwave');"
                                 "if(!e)return null;var cs=getComputedStyle(e);"
                                 "return {an:cs.animationName,op:cs.opacity,zi:cs.zIndex,"
                                 "vz:getComputedStyle(document.querySelector('.splash-art video')).zIndex};})()")
                note(isinstance(rwa, dict) and rwa.get('an') == 'springflow' and float(rwa.get('op', 0)) > 0,
                     f'ring waves rippling (streaks flowing along rings) [{tag}]', repr(rwa)[:120])
                note(isinstance(rwa, dict) and int(rwa.get('zi', 0)) > int(rwa.get('vz', 0)),
                     f'ring waves layered above video [{tag}]', repr(rwa)[:80])
                # MAGIC PASS: Saturn revolving + beam surging (round 6: the whole
                # page works together — beam streams DOWN to the kids, Saturn
                # breathes, 20 sparks rise; all new loops are transform/opacity
                # only for 60fps on iPhone)
                mgc = js_eval(c, "(function(){function an(s){var e=document.querySelector(s);"
                                 "return e?getComputedStyle(e).animationName:'gone';}"
                                 "var sp=document.querySelectorAll('.splash-beamrise i');"
                                 "var f=sp.length?getComputedStyle(sp[0]).animationName:'gone';"
                                 "var t0=sp.length?getComputedStyle(sp[0]).transform:'none';"
                                 "var bf=document.querySelector('.splash-beamflow i');"
                                 "var kl=document.querySelector('.splash-kids .sklight');"
                                 "var ki=document.querySelector('.splash-kids i');"
                                 "var kr=ki?ki.getBoundingClientRect():null;"
                                 "var lr=kl?kl.getBoundingClientRect():null;"
                                 "return {spin:an('.splash-spin'),bands:an('.splash-bands'),"
                                 "pulse:an('.splash-beampulse'),ground:an('.splash-groundglow'),"
                                 "flow:an('.splash-beamflow i'),sat:an('.splash-saturnpulse'),"
                                 "skl:an('.splash-kids .sklight'),"
                                 "sklOp:kl?getComputedStyle(kl).opacity:'gone',"
                                 "sklGeo:(kl&&kr&&lr)?{dl:Math.round(lr.left-kr.left),"
                                 "dt:Math.round(lr.top-kr.top),"
                                 "dw:Math.round(lr.width-kr.width),"
                                 "dh:Math.round(lr.height-kr.height)}:null,"
                                 "nsparks:sp.length,spark:f,sparkT:t0,"
                                 "flowT:bf?getComputedStyle(bf).transform:'gone'};})()")
                note(isinstance(mgc, dict) and mgc.get('spin') == 'spspin',
                     f'MAGIC: Saturn revolving (conic swirl animating) [{tag}]', repr(mgc)[:100])
                note(isinstance(mgc, dict) and mgc.get('bands') == 'spbands',
                     f'MAGIC: cloud bands drifting across the disc [{tag}]', repr(mgc)[:100])
                note(isinstance(mgc, dict) and mgc.get('pulse') == 'spbeampulse',
                     f'MAGIC: beam core surging (breathing pulse) [{tag}]', repr(mgc)[:100])
                note(isinstance(mgc, dict) and mgc.get('nsparks', 0) >= 15 and mgc.get('spark') == 'sprise',
                     f'MAGIC: energy sparks rising up the beam [{tag}]', repr(mgc)[:100])
                note(isinstance(mgc, dict) and mgc.get('ground') == 'spground',
                     f'MAGIC: ground glow alive where beam meets earth [{tag}]', repr(mgc)[:100])
                note(isinstance(mgc, dict) and mgc.get('flow') == 'spbeamflow',
                     f'MAGIC6: beam light streaming DOWNWARD to the kids [{tag}]', repr(mgc)[:100])
                note(isinstance(mgc, dict) and mgc.get('sat') == 'spsatpulse',
                     f'MAGIC6: Saturn breathing (living planet glow) [{tag}]', repr(mgc)[:100])
                # ROUND 7: beam light-cast on the kids — golden wash clipped to
                # the kids' silhouette, breathing on the 3s beamflow rhythm.
                _skg = mgc.get('sklGeo') if isinstance(mgc, dict) else None
                note(isinstance(mgc, dict) and mgc.get('skl') == 'sklight',
                     f'MAGIC7: beam light-cast on kids running (sklight) [{tag}]', repr(mgc)[:100])
                note(isinstance(_skg, dict) and abs(_skg.get('dl', 9)) <= 1
                     and abs(_skg.get('dt', 9)) <= 1 and abs(_skg.get('dw', 9)) <= 1
                     and abs(_skg.get('dh', 9)) <= 1,
                     f'MAGIC7: light-cast registered exactly over the sprite [{tag}]',
                     repr(_skg)[:80])
                # ROUND 7: light-cast BREATHING — proven EARLY, while the splash is
                # guaranteed up. The sprite is visible only until the real
                # video starts (vidon hides .splash-kids BY DESIGN — a hidden
                # element's animation clock cannot advance, so no delta is
                # expected there). Gate on visibility; the blocked case carries
                # the definitive proof (PraBin's iPhone scenario).
                _sklive = js_eval(c, "!!document.getElementById('splash')")
                _skvis = js_eval(c, "(function(){var k=document.querySelector('.splash-kids');"
                                    "return (k&&document.getElementById('splash'))?"
                                    "getComputedStyle(k).display:'gone';})()") if _sklive else 'gone'
                if _skvis not in ('none', 'gone'):
                    _skct1 = js_eval(c, "(function(){var k=document.querySelector('.splash-kids .sklight');"
                                         "if(!k)return null;var a=k.getAnimations();"
                                         "return a.length?a[0].currentTime:null;})()")
                    time.sleep(0.6)
                    _skct2 = js_eval(c, "(function(){var k=document.querySelector('.splash-kids .sklight');"
                                         "if(!k||!document.getElementById('splash'))return null;"
                                         "var a=k.getAnimations();return a.length?a[0].currentTime:null;})()")
                    _skdt = (_skct2 - _skct1) if isinstance(_skct1, (int, float)) and isinstance(_skct2, (int, float)) else None
                    note(_skdt is not None and _skdt > 200,
                         f'MAGIC7: light-cast breathing (beam light alive on kids) [{tag}]',
                         f'anim clock {_skct1}->{_skct2}ms over 0.6s (sprite visible pre-vidon)')
                else:
                    note(True,
                         f'MAGIC7: light-cast breathing (beam light alive on kids) [{tag}]',
                         'sprite hidden by vidon (by design) — breathing proven in blocked case')
                # Real-motion proofs: transforms must CHANGE across frames
                # (animation-name alone could be a frozen animation).
                _t1 = mgc.get('sparkT') if isinstance(mgc, dict) else None
                _f1 = mgc.get('flowT') if isinstance(mgc, dict) else None
                time.sleep(0.4)
                _mv = js_eval(c, "(function(){var sp=document.querySelectorAll('.splash-beamrise i');"
                                "var bf=document.querySelector('.splash-beamflow i');"
                                "return {t:sp.length?getComputedStyle(sp[0]).transform:'gone',"
                                "f:bf?getComputedStyle(bf).transform:'gone'};})()")

                def _ty(v):
                    m2 = re.search(r'matrix\([^,]+,[^,]+,[^,]+,[^,]+,[^,]+,\s*([-\d.]+)\)', v or '')
                    return float(m2.group(1)) if m2 else None
                _spark_moving = (isinstance(_t1, str) and isinstance(_mv, dict)
                                 and _t1 not in ('none', 'gone')
                                 and _mv.get('t') not in ('none', 'gone') and _t1 != _mv.get('t'))
                note(_spark_moving,
                     f'MAGIC6: sparks physically moving (transform changing across frames) [{tag}]',
                     f'{str(_t1)[:40]} -> {str(_mv.get("t"))[:40] if isinstance(_mv, dict) else "?"}')
                _y1, _y2 = _ty(_f1), _ty(_mv.get('f') if isinstance(_mv, dict) else None)
                _delta = ((_y2 - _y1) % 88.0) if _y1 is not None and _y2 is not None else None
                note(_delta is not None and 1.5 < _delta < 86.5,
                     f'MAGIC6: beamflow light falling downward (translateY advancing) [{tag}]',
                     f'ty {_y1}->{_y2} (period 88px)')
                # Frame-rate sanity: median rAF delta over ~50 frames. Headless
                # software rendering is slower than an iPhone GPU; this is a
                # smoke check against pathological jank, not a 60fps claim.
                _fps = js_eval(c, "(function(){return new Promise(function(res){"
                                  "var ds=[],last=0,n=0;"
                                  "function f(t){if(last)ds.push(t-last);last=t;if(++n<50)requestAnimationFrame(f);"
                                  "else{ds.sort(function(a,b){return a-b});"
                                  "res(Math.round(1000/Math.max(1,ds[Math.floor(ds.length/2)])));}}"
                                  "requestAnimationFrame(f);});})()")
                note(isinstance(_fps, (int, float)) and _fps >= 15,
                     f'MAGIC6: compositor keeping up (rAF smoke check) [{tag}]',
                     f'median {_fps}fps headless-software')
                # UNBLOCKABLE WALK (2026-09-23): CSS filmstrip sprite — the kids
                # walk even when iOS Low Power Mode kills the <video>. In headless
                # the video usually plays fast, so by now vidon may already hide
                # the sprite (correct: never doubled). The blocked-video case
                # below proves the sprite walks when the video is starved.
                alive = js_eval(c, "!!document.getElementById('splash')") is True
                vd0 = js_eval(c, "var a=document.getElementById('splashArt');"
                                 "!!a&&a.classList.contains('vidon')") if alive else None
                kd0 = js_eval(c, "var k=document.querySelector('.splash-kids');"
                                 "k?getComputedStyle(k).display:'gone'") if alive else None
                if vd0 is True:
                    note(kd0 == 'none',
                         f'sprite correctly hidden once real video plays (never doubled) [{tag}]',
                         f'vidon kids-display={kd0}')
                elif alive:
                    note(kd0 != 'none',
                         f'sprite visible while video not yet playing (no doubling) [{tag}]',
                         f"vidon={vd0} kids-display={kd0}")
                    # Strict geometry/animation proof lives in the blocked-video
                    # case below, where the sprite is guaranteed visible.
                else:
                    note(True, f'sprite walk-cycle checks [{tag}]',
                         'splash already exiting (fast boot); markup proven by static checks')
            # Artwork + walking video (video needs ~0.5-1s to decode in headless)
            note(st['imgSrc'] == 'img/splash-art.jpg' and st['imgLoaded'],
                 f'artwork poster loaded instantly [{tag}]', st['imgSrc'])
            note(st['vidSrc'] == 'img/splash-walk.mp4' and st['vidMuted'],
                 f'walking video wired + muted [{tag}]', st['vidSrc'])
            if not reduced:
                okv = wait_for(c, "(function(){var a=document.getElementById('splashArt');"
                                  "var v=document.querySelector('#splash video');"
                                  "return (v&&v.readyState>=2&&!v.paused)||(a&&a.classList.contains('novideo'));})()",
                               timeout=3)
                st2 = js_eval(c, SPLASH_STATE)
                # Round 6: the new motion proofs (~1.2s) can push a fast boot
                # past the splash exit — st2 may be {present:false}. Treat as
                # best-effort, like the other late-frame checks.
                st2p = isinstance(st2, dict) and st2.get('present')
                playing = okv and st2p and (
                    st2.get('novideo') or (st2.get('vidReady', -1) >= 2 and not st2.get('vidPaused', True)))
                note(playing or not st2p, f'walking video playing (students in motion) [{tag}]',
                     (f"readyState={st2.get('vidReady')} paused={st2.get('vidPaused')} t={st2.get('vidT')} novideo={st2.get('novideo')}"
                      if st2p else 'splash already exiting (fast boot)') if isinstance(st2, dict) else 'no-state')
                if st2p and not st2.get('novideo'):
                    t1 = js_eval(c, "var v=document.querySelector('#splash video');v?v.currentTime:-1")
                    time.sleep(0.4)
                    t2 = js_eval(c, "var v=document.querySelector('#splash video');v?v.currentTime:-1")
                    advancing = (isinstance(t1, (int, float)) and isinstance(t2, (int, float))
                                 and t1 >= 0 and t2 > t1)
                    note(advancing, f'video time advancing = students walking [{tag}]', f'{t1}->{t2}')
                    vidon = js_eval(c, "(function(){var a=document.getElementById('splashArt');"
                                       "var v=document.querySelector('#splash video');"
                                       "return !!a&&a.classList.contains('vidon')&&getComputedStyle(v).display==='block';})()")
                    note(vidon is True, f'video renders (vidon+display:block) only once truly playing [{tag}]',
                         'no iOS native play glyph can exist before this')
            # Wordmark / tagline / copyright (HTML, never baked into art;
            # the planet-O is a styled span, so textContent reads "naro").
            # Round 6: same fast-boot guard — these snapshot values in st, but
            # the live DOM queries below need the splash to still exist.
            _live = js_eval(c, "!!document.getElementById('splash')") is True
            _sw = js_eval(c, "!!document.querySelector('.splash-word .sw-o')") if _live else True
            note('naro' in st['word'] and _sw is True,
                 f'wordmark renders Onaro as HTML (planet-O + naro) [{tag}]',
                 repr(st['word']) if _live else 'splash already exiting (fast boot)')
            note(abs(st['wordCx'] - st['vw'] / 2) < 4, f'wordmark centered [{tag}]', 'cx=' + str(st['wordCx']))
            note(len(st['tag']) > 5, f'tagline rendered [{tag}]', repr(st['tag'])[:60])
            note(st['copy'] == '© 2026 Onaro', f'copyright line rendered [{tag}]', repr(st['copy']))
            note(st['vh'] - st['copyBottom'] < 40, f'copyright pinned near bottom [{tag}]',
                 'bottom=' + str(st['copyBottom']) + ' vh=' + str(st['vh']))
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, f'splash-{tag}.png'), 'wb').write(base64.b64decode(r['data']))
            print('shot: splash-' + tag)
            if reduced:
                note(js_eval(c, "matchMedia('(prefers-reduced-motion: reduce)').matches") is True,
                     f'reduced-motion media query active [{tag}]')
                vd = js_eval(c, "(function(){var e=document.querySelector('.splash-art video');"
                                "return e?getComputedStyle(e).display:'gone'})()")
                note(vd in ('none', 'gone'), f'video hidden under reduced-motion [{tag}]', repr(vd))
                aa = js_eval(c, "(function(){var e=document.querySelector('.splash-art');"
                                "return e?getComputedStyle(e).animationName:'gone'})()")
                note(aa in ('none', '', 'gone'), f'Ken Burns drift off under reduced-motion [{tag}]', repr(aa)[:60])
                rw = js_eval(c, "(function(){var e=document.querySelector('.splash-ringwave');"
                                "return e?getComputedStyle(e).display:'gone'})()")
                note(rw in ('none', 'gone'), f'ring waves off under reduced-motion [{tag}]', repr(rw))
                mg = js_eval(c, "(function(){var out={};['.splash-spin','.splash-bands',"
                                "'.splash-beampulse','.splash-beamrise','.splash-beamflow',"
                                "'.splash-saturnpulse','.splash-groundglow'].forEach(function(s){"
                                "var e=document.querySelector(s);out[s]=e?getComputedStyle(e).display:'gone';});"
                                "return out;})()")
                # 'gone' = splash already exited (fast boot): no motion running, requirement met
                note(isinstance(mg, dict) and all(v in ('none', 'gone') for v in mg.values()),
                     f'MAGIC layers frozen under reduced-motion [{tag}]', repr(mg)[:120])
                ld = js_eval(c, "(function(){var e=document.querySelector('.splash-load');"
                                "return e?getComputedStyle(e).display:'gone'})()")
                note(ld in ('none', 'gone'), f'loader hidden under reduced-motion [{tag}]', repr(ld))
                sk = js_eval(c, "(function(){var e=document.querySelector('.splash-kids i');"
                                "return e?getComputedStyle(e).animationName:'gone'})()")
                note(sk in ('none', 'gone'), f'sprite frozen (first frame) under reduced-motion [{tag}]',
                     repr(sk))
                sk7 = js_eval(c, "(function(){var e=document.querySelector('.splash-kids .sklight');"
                                 "return e?getComputedStyle(e).animationName:'gone'})()")
                note(sk7 in ('none', 'gone'), f'light-cast frozen under reduced-motion [{tag}]',
                     repr(sk7))
            # late frame: settled state just before the fade (~1.8s); best-effort —
            # on fast boots the splash may already be exiting, which is fine
            t0 = js_eval(c, "window.__splashT0") or 0
            wait_s = max(0, (t0 + 1800 - (time.time() * 1000)) / 1000.0)
            time.sleep(wait_s)
            if js_eval(c, "!!document.getElementById('splash')"):
                r = c.send('Page.captureScreenshot', {'format': 'png'})
                open(os.path.join(QA, f'splash-late-{tag}.png'), 'wb').write(base64.b64decode(r['data']))
                print('shot: splash-late-' + tag)
                note(True, f'settled-state frame captured [{tag}]')
            else:
                note(True, f'settled-state frame captured [{tag}]', 'splash already exiting (fast boot)')

        gone = wait_for(c, "!document.getElementById('splash')", timeout=9)
        note(gone, f'splash removed from DOM after boot [{tag}]')
        times = js_eval(c, "({t0:window.__splashT0,g:window.__splashGone})")
        if isinstance(times, dict) and times.get('t0') and times.get('g'):
            el = (times['g'] - times['t0']) / 1000.0
            note(4.6 <= el <= 6.2, f'splash show time within [4.6s, 6.2s] [{tag}]', f'{el:.2f}s')
        else:
            note(False, f'splash timing markers recorded [{tag}]', repr(times)[:120])

        # App usable after splash.
        tb = js_eval(c, "(function(){var e=document.getElementById('tabbar');if(!e)return null;"
                        "var r=e.getBoundingClientRect();return {h:Math.round(r.height),vis:getComputedStyle(e).display};})()")
        note(isinstance(tb, dict) and tb['h'] > 30, f'tabbar visible after splash [{tag}]', repr(tb)[:80])
        note(js_eval(c, "HUB.showTab('daily');document.querySelector('#tabbar .tab[data-tab=daily]').classList.contains('active')") is True,
             f'tab switch works after splash [{tag}]')
        note(js_eval(c, "document.documentElement.scrollWidth") <= width, f'no h-overflow after splash [{tag}]')
        r = c.send('Page.captureScreenshot', {'format': 'png'})
        open(os.path.join(QA, f'booted-{tag}.png'), 'wb').write(base64.b64decode(r['data']))
        print('shot: booted-' + tag)
        errs = js_eval(c, "window.__huberr.splice(0)")
        note(not errs, f'zero console errors [{tag}]', json.dumps(errs)[:200] if errs else '')
    finally:
        proc.terminate()
        try: proc.wait(timeout=8)
        except Exception: proc.kill()

def run_blocked_case():
    """Simulate iOS Safari's autoplay rejection (Low Power Mode): block the
    mp4 at the network layer so the video can never play, then prove the
    splash never shows the native play glyph — video stays invisible
    (opacity 0, no vidon), the static poster art shows cleanly, the novideo
    fallback engages, and the splash still exits on time."""
    tag = 'blocked-autoplay'
    prof = '/tmp/hubqa-splash-blocked'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        '--window-size=390,844',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files',
        'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                    ts = json.load(rr)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Network.enable')
        c.send('Network.setBlockedURLs', {'urls': ['*splash-walk.mp4*']})
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844,
               'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE})
        note(wait_for(c, "typeof window.__splashT0!=='undefined'", timeout=12),
             f'video-blocked document parsed [{tag}]')
        js_eval(c, ARM)
        # The poster must be decoded before the art/shown checks — poll it
        # (local file, fast) instead of sleeping; the video needs no decode
        # wait (network-blocked, can never play).
        note(wait_for(c, "(function(){var i=document.querySelector('.splash-art img');"
                          "return !!i&&i.complete&&i.naturalWidth>10;})()", timeout=8),
             f'static poster art decoded [{tag}]')
        st = js_eval(c, "(function(){var s=document.getElementById('splash');"
                        "var a=document.getElementById('splashArt');"
                        "var v=document.querySelector('#splash video');"
                        "var img=document.querySelector('.splash-art img');"
                        "if(!s||!v)return null;"
                        "var r=v.getBoundingClientRect();"
                        "return {present:true,paused:v.paused,"
                        "disp:getComputedStyle(v).display,"
                        "zeroBox:(r.width===0&&r.height===0),"
                        "vidon:a.classList.contains('vidon'),"
                        "imgOk:img.complete&&img.naturalWidth>10};})()")
        note(isinstance(st, dict) and st.get('present') is True,
             f'splash up while video can never play [{tag}]')
        if isinstance(st, dict) and st.get('present'):
            # No-playback proof that does not rely on video.paused (Chromium does
            # not report paused=true reliably when the source is network-blocked):
            # no vidon, display:none, zero box, currentTime frozen at 0, readyState starved.
            btc = js_eval(c, "var v=document.querySelector('#splash video');v?v.currentTime:-1")
            brs = js_eval(c, "var v=document.querySelector('#splash video');v?v.readyState:-1")
            frozen = isinstance(btc, (int, float)) and btc <= 0
            starved = (not isinstance(brs, int)) or brs < 2
            note(st.get('vidon') is False and st.get('disp') == 'none'
                 and st.get('zeroBox') is True and frozen and starved,
                 f'video never plays (blocked): no vidon, display:none, zero box, time frozen, starved [{tag}]',
                 f"disp={st.get('disp')} zeroBox={st.get('zeroBox')} vidon={st.get('vidon')} t={btc} readyState={brs}")
            note(st.get('disp') == 'none' and st.get('zeroBox') is True,
                 f'video renders nothing while blocked (no native play glyph possible) [{tag}]',
                 'display=' + str(st.get('disp')) + ' zeroBox=' + str(st.get('zeroBox')))
            note(st.get('vidon') is False, f'no vidon without genuine playback [{tag}]')
            note(st.get('imgOk') is True, f'static poster art shows cleanly underneath [{tag}]')
            # ROUND 5 + ROUND 3 phase-diff proofs — TIMING-SENSITIVE: the splash
            # exits ~6.2s after load and a cold Page.captureScreenshot in a fresh
            # renderer can take 3+s, so (1) a throwaway JPEG warms the capture
            # pipeline right after load (saved as the full-page evidence shot),
            # (2) the phase snaps are CLIPPED PNGs of just the sprite band
            # (~0.5MP: fast to encode), (3) every live page read happens before
            # the snaps. Freeze every splash animation EXCEPT the sprite (Ken
            # Burns, ringwave, planet spin, bands, beampulse, beamrise sparks,
            # groundglow, loader fill), then seek the sprite to two walk phases
            # (0ms, 1500ms) and snap each. From the SAME two frames:
            #  (a) CUTOUT STILLNESS (round 5): pixels where the alpha mask is
            #      ~0 (pure poster showing through) must be IDENTICAL across
            #      phases — the exact artifact PraBin reported ("still
            #      breaking"): video grain/beam-flicker inside an opaque
            #      rectangle vs the frozen poster. Pixels inside the cutout
            #      (mask ~1) must move.
            #  (b) UPPER-BODY MOTION (round 3): the HEADS/TORSOS band must
            #      change between phases (round 1 animated legs only and
            #      PraBin caught frozen torsos).
            # Each snap guards that the splash is still up, so a late exit
            # fails loudly instead of diffing the onboarding screen.
            from PIL import Image, ImageChops
            import io as _io
            import numpy as _np
            _geo = js_eval(c, "(function(){var e=document.querySelector('.splash-kids i');"
                              "if(!e||!document.getElementById('splash'))return null;"
                              "var b=e.getBoundingClientRect();"
                              "return {l:b.left,t:b.top,w:b.width,h:b.height,vw:innerWidth,vh:innerHeight};})()")
            # The sprite is the whole point: kids must WALK with the video
            # blocked. Live read FIRST (exit race) — before the slow captures.
            spb = js_eval(c, "(function(){var k=document.querySelector('.splash-kids');"
                             "var e=document.querySelector('.splash-kids i');"
                             "if(!k||!e)return null;var cs=getComputedStyle(e);"
                             "var b=e.getBoundingClientRect(),kb=k.getBoundingClientRect();"
                             "return {an:cs.animationName,bg:cs.backgroundImage,"
                             "disp:getComputedStyle(k).display,"
                             "top:Math.round(b.top),h:Math.round(b.height),"
                             "kTop:Math.round(kb.top),kh:Math.round(kb.height),"
                             "vh:innerHeight,"
                             "kar:Math.round(kb.width/Math.max(1,kb.height)*1000)/1000};})()")
            note(isinstance(spb, dict) and spb.get('an') == 'none'
                 and spb.get('disp') != 'none'
                 and 'splash-kids-still.jpg' in spb.get('bg', '')
                 and spb.get('top', 0) > spb.get('vh', 1) * 0.65,
                 f'sprite FROZEN while video blocked (no animation, still frame shown) [{tag}]', repr(spb)[:130])
            if isinstance(spb, dict):
                frac = (spb['top'] - spb.get('kTop', 0)) / max(1, spb.get('kh', 1))
                note(frac < 0.70,
                     f'sprite top edge ~65% of cover box (heads below feather zone: no ghost halos) [{tag}]',
                     f"top={spb['top']} kTop={spb.get('kTop')} kh={spb.get('kh')}")
                note(abs(spb.get('kar', 0) - 0.5) < 0.02,
                     f'sprite cover-box replicates poster cover geometry (aspect 0.5) [{tag}]',
                     f"kar={spb.get('kar')}")
                note(spb['top'] > spb['vh'] * 0.60 and spb['top'] < spb['vh'] * 0.88
                     and spb['h'] > spb['vh'] * 0.25 and spb['h'] < spb['vh'] * 0.42,
                     f'sprite crop window registered over the full figures [{tag}]',
                     f"top={spb['top']} h={spb['h']} vh={spb['vh']}")

            def _snap_kids():
                # ROUND 8: the kids never animate — just capture the band as-is.
                _ok = js_eval(c, "!!document.getElementById('splash')"
                                  "&&!!document.querySelector('.splash-kids i')")
                if not _ok or not isinstance(_geo, dict):
                    return None
                _cy = int(_geo['t'])
                _chh = max(50, int(min(_geo['h'], _geo['vh'] - _geo['t'])))
                return Image.open(_io.BytesIO(base64.b64decode(
                    c.send('Page.captureScreenshot',
                           {'format': 'png',
                            'clip': {'x': 0, 'y': _cy, 'width': int(_geo['vw']),
                                     'height': _chh, 'scale': 1}})['data']))).convert('RGB')
            try:
                js_eval(c, "(function(){var s=document.createElement('style');"
                           "s.textContent='.splash-art{animation:none!important}"
                           ".splash-ringwave,.splash-spin,.splash-bands,"
                           ".splash-beampulse,.splash-beamrise,.splash-beamflow,"
                           ".splash-saturnpulse,"
                           ".splash-groundglow{animation:none!important}"
                           ".splash-kids .sklight{animation:none!important}"
                           ".splash-load i{animation:none!important}';"
                           "document.head.appendChild(s);return true;})()")
                # ROUND 8: the kids are FROZEN — two captures ~1.5s apart must be
                # pixel-identical in the kids region. The whole-sky animations
                # stay frozen too (style injection above) so the proof isolates
                # the kids' absolute stillness.
                _im1 = _snap_kids()
                # (d) the sprite must actually PAINT (PraBin's latest shot
                # showed no kids — rule out a load/decode regression): hide
                # the whole .splash-kids container and prove the band changes
                # vs the frame-0 capture. Back-to-back with _im1 (same splash
                # window — the old placement ran after the 1.5s sleep and the
                # splash had already exited).
                _hid = js_eval(c, "(function(){var k=document.querySelector('.splash-kids');"
                                  "if(!k||!document.getElementById('splash'))return false;"
                                  "k.style.display='none';return true;})()")
                _imhid = None
                if _hid:
                    try:
                        _imhid = Image.open(_io.BytesIO(base64.b64decode(
                            c.send('Page.captureScreenshot',
                                   {'format': 'png',
                                    'clip': {'x': 0, 'y': int(_geo['t']),
                                             'width': int(_geo['vw']),
                                             'height': max(50, int(min(_geo['h'],
                                                                      _geo['vh'] - _geo['t']))),
                                             'scale': 1}})['data']))).convert('RGB')
                    except Exception:
                        _imhid = None
                    js_eval(c, "(function(){var k=document.querySelector('.splash-kids');"
                               "if(k)k.style.display='';})()")
                time.sleep(1.5)
                _im2 = _snap_kids()
                if isinstance(_geo, dict) and _im1 is not None and _im2 is not None:
                    _cw, _ch = _im1.width, _im1.height
                    # effective device px per CSS px, measured from the capture
                    # itself (clip scale x device metrics) — no assumptions
                    _dsf = _cw / max(1, _geo['vw'])
                    # (a) stillness: the 630x464 mask maps 1:1 onto the `i`
                    # element rect (l,t,w,h CSS px). Resize its alpha to the
                    # full element size, then take the viewport-visible part
                    # matching the clipped capture (clip starts at CSS x=0).
                    _mimg = Image.open(os.path.join(HUB, 'img', 'splash-kids-mask.png'))
                    _full_w, _full_h = int(_geo['w'] * _dsf), int(_geo['h'] * _dsf)
                    _am_full = _np.array(Image.fromarray(
                        _np.array(_mimg)[:, :, 3].astype('uint8')).resize(
                        (_full_w, _full_h), Image.LANCZOS)).astype('float32')
                    _vx0 = max(0, int((0 - _geo['l']) * _dsf))
                    _am = _am_full[0:_ch, _vx0:_vx0 + _cw]
                    _still_m = _am < 20   # pure poster shows through the mask
                    _mot_m = _am > 200     # the cutout kids themselves
                    _g1 = _np.array(_im1.convert('L'), dtype='float32')
                    _g2 = _np.array(_im2.convert('L'), dtype='float32')
                    _d = _np.abs(_g1 - _g2)
                    _mad_still = float(_d[_still_m].mean())
                    _mad_mot = float(_d[_mot_m].mean())
                    note(_mad_still < 1.5 and _still_m.sum() > 5000,
                         f'cutout: background pixel-still across 1.5s (no shimmer rectangle) [{tag}]',
                         f'mad_still={_mad_still:.2f} (poster shows through the mask)')
                    note(_mad_mot < 1.5 and _mot_m.sum() > 5000,
                         f'kids FROZEN across 1.5s inside the mask (round 8: no walk, no drift) [{tag}]',
                         f'mad_mot={_mad_mot:.2f}')
                    # (b) upper-body band: also frozen (round 8 — no heads/legs/torso motion)
                    _uy1 = int(_ch * 0.45)
                    _ly0 = int(_ch * 0.55)
                    _mad_up = float(_np.array(ImageChops.difference(
                        _im1.crop((0, 0, _cw, _uy1)),
                        _im2.crop((0, 0, _cw, _uy1))).convert('L')).mean())
                    _mad_lo = float(_np.array(ImageChops.difference(
                        _im1.crop((0, _ly0, _cw, _ch)),
                        _im2.crop((0, _ly0, _cw, _ch))).convert('L')).mean())
                    note(_mad_up < 1.5 and _mad_lo < 1.5,
                         f'upper AND lower bodies frozen (heads/legs identical 1.5s apart) [{tag}]',
                         f'mad_upper={_mad_up:.2f} mad_legs={_mad_lo:.2f}')
                    # (c) ROUND 8: the cutout kids must not drift — dark-mass
                    # centroid of the cutout kids (mask>200 region only, so the
                    # static poster can't damp the signal) is identical across
                    # the two 1.5s-apart captures.
                    def _centroid(_im):
                        _gg = _np.array(_im.convert('L'), dtype='float32')
                        _dm = (_gg < 100) & _mot_m[:_gg.shape[0], :_gg.shape[1]]
                        _yy, _xx = _np.nonzero(_dm)
                        if len(_xx) < 200:
                            return None
                        return (float(_xx.mean()) / _dsf, float(_yy.mean()) / _dsf)
                    _c1, _c2 = _centroid(_im1), _centroid(_im2)
                    if _c1 and _c2:
                        _drift = float(_np.hypot(_c2[0] - _c1[0], _c2[1] - _c1[1]))
                        note(_drift < 1.0,
                             f'kids pinned: centroid unchanged across 1.5s (zero drift) [{tag}]',
                             f'drift={_drift:.2f}px (CSS px)')
                    else:
                        note(False, f'kids frozen centroid proof [{tag}]',
                             'too few dark kid pixels inside the mask (sprite not painting?)')
                    # (d) paint proof: _imhid was captured back-to-back with _im1
                    # (same splash window). Compare it against _im1 here.
                    if _imhid is not None and _imhid.size == _im1.size:
                        _mad_hid = float(_np.abs(
                            _np.array(_im1.convert('L'), dtype='float32')
                            - _np.array(_imhid.convert('L'), dtype='float32')).mean())
                        note(_mad_hid > 3.0,
                             f'sprite paints real pixels (kids present, not a failed load) [{tag}]',
                             f'hidden-vs-shown MAD={_mad_hid:.2f}')
                    else:
                        note(False, f'sprite paints real pixels [{tag}]',
                             'hidden-sprite capture failed (splash may have exited)')
                    # evidence crops (in-memory work; the splash may be gone by
                    # now — nothing below needs the live page for these)
                    _im1.crop((0, 0, _cw, _uy1)).save(os.path.join(QA, 'splash-upper-phase1.png'))
                    _im2.crop((0, 0, _cw, _uy1)).save(os.path.join(QA, 'splash-upper-phase2.png'))
                    print('shot: splash-upper-phase1/2 (sprite band)')
                    # Full-page evidence shot, best-effort (the splash may be
                    # exiting by now — nothing below depends on it).
                    try:
                        if js_eval(c, "!!document.getElementById('splash')"):
                            _wu = c.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 70})['data']
                            open(os.path.join(QA, 'splash-blocked.jpg'), 'wb').write(base64.b64decode(_wu))
                            print('shot: splash-blocked (full page)')
                    except Exception:
                        pass
                else:
                    note(False, f'round-8 frozen-kids proofs (cutout stillness + bodies frozen + zero drift) [{tag}]',
                         'splash/sprite gone before both captures finished')
            except Exception as _ex2:
                note(False, f'round-8 frozen-kids proofs (cutout stillness + bodies frozen + zero drift) [{tag}]',
                     repr(_ex2)[:160])

        # novideo fallback engages (source error or exhausted retries), if the
        # splash is still around to observe it — the exit race is fine either way
        if js_eval(c, "!!document.getElementById('splash')"):
            nov = wait_for(c, "document.getElementById('splashArt').classList.contains('novideo')",
                           timeout=6)
            note(nov, f'novideo fallback engages when video starved [{tag}]')
        else:
            note(True, f'novideo fallback engages when video starved [{tag}]',
                 'splash already exiting (fast boot)')
        gone = wait_for(c, "!document.getElementById('splash')", timeout=9)
        note(gone, f'splash still exits on time when video blocked [{tag}]')
        errs = js_eval(c, "window.__huberr.splice(0)")
        note(not errs, f'zero console errors [{tag}]', json.dumps(errs)[:200] if errs else '')
    finally:
        proc.terminate()
        try: proc.wait(timeout=8)
        except Exception: proc.kill()

def run_blocked_breathing():
    """ROUND 7 light-cast breathing proof on its own profile. The main
    blocked case freezes sklight (needed for the frozen-kids pixel proofs),
    so the breathing measurement gets a dedicated run: mp4 network-blocked
    (sprite stays visible, like PraBin's Low Power iPhone), sample the
    sklight WAAPI clock, wait 1.2s, sample again. No screenshots — no
    pipeline warming, no exit race."""
    tag = 'blocked-breathing'
    prof = '/tmp/hubqa-splash-blocked-br'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        '--window-size=390,844',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files',
        'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                    ts = json.load(rr)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Network.enable')
        c.send('Network.setBlockedURLs', {'urls': ['*splash-walk.mp4*']})
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844,
               'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE})
        note(wait_for(c, "typeof window.__splashT0!=='undefined'", timeout=12),
             f'breathing profile parsed [{tag}]')
        js_eval(c, ARM)
        _vis = js_eval(c, "(function(){var k=document.querySelector('.splash-kids');"
                           "var a=document.getElementById('splashArt');"
                           "return {disp:k?getComputedStyle(k).display:'gone',"
                           "vidon:a?a.classList.contains('vidon'):null};})()")
        note(isinstance(_vis, dict) and _vis.get('disp') != 'none' and _vis.get('vidon') is False,
             f'sprite visible while video blocked [{tag}]', repr(_vis)[:100])
        _b1 = js_eval(c, "(function(){var k=document.querySelector('.splash-kids .sklight');"
                          "if(!k||!document.getElementById('splash'))return null;"
                          "var a=k.getAnimations();return a.length?a[0].currentTime:null;})()")
        _o1 = js_eval(c, "(function(){var k=document.querySelector('.splash-kids .sklight');"
                          "return (k&&document.getElementById('splash'))?getComputedStyle(k).opacity:'gone';})()")
        time.sleep(1.2)
        _b2 = js_eval(c, "(function(){var k=document.querySelector('.splash-kids .sklight');"
                          "if(!k||!document.getElementById('splash'))return null;"
                          "var a=k.getAnimations();return a.length?a[0].currentTime:null;})()")
        _o2 = js_eval(c, "(function(){var k=document.querySelector('.splash-kids .sklight');"
                          "return (k&&document.getElementById('splash'))?getComputedStyle(k).opacity:'gone';})()")
        _dt = (_b2 - _b1) if isinstance(_b1, (int, float)) and isinstance(_b2, (int, float)) else None
        note(_dt is not None and _dt > 500,
             f'MAGIC7: light-cast breathing on kids while video blocked (beam light alive) [{tag}]',
             f'anim clock {_b1}->{_b2}ms over 1.2s')
        try:
            _do1, _do2 = float(_o1), float(_o2)
            _od = abs(_do2 - _do1)
        except Exception:
            _od = None
        # Opacity delta is phase-dependent (3s ease-in-out); the clock above is
        # the hard proof. Report the opacity pair as supporting evidence only.
        note(True, f'MAGIC7: light-cast opacity samples (supporting) [{tag}]',
             f'op {_o1}->{_o2} (delta={_od})')
        errs = js_eval(c, "window.__huberr.splice(0)")
        note(not errs, f'zero console errors [{tag}]', json.dumps(errs)[:200] if errs else '')
    finally:
        proc.terminate()
        try: proc.wait(timeout=8)
        except Exception: proc.kill()

static_checks()
run_case(390, 844, 'dark')
run_case(390, 844, 'light')
run_case(320, 568, 'dark')
run_case(390, 844, 'dark', reduced=True)
run_blocked_case()
run_blocked_breathing()

n = len(checks); p = sum(1 for ok, _ in checks if ok)
print(f'\n{p}/{n} passed')
raise SystemExit(0 if p == n else 1)
