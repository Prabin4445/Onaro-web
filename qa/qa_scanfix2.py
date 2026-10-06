#!/usr/bin/env python3
"""QA: scanner regression fixes (black viewfinder + "Use this page" legibility).

CDP (headless Chromium, fake camera device):
  F1 muted/playsInline JS properties set on the <video> (iOS black-video fix)
  F2 double camView entry -> exactly one live camera stream (orphan stopped)
  F3 watchdog: video that never plays -> explicit error card + working retry
  F4 blank-frame gate: SCAN._camBlank(black)=true, (white)=true, (noise)=false;
      black video never yields the camLocked tip
  F5 data-apply from camera -> saved-pages pill (count 1 + thumbnail);
      tapping the pill reaches pagesView with the saved page
  F6 zero console errors; 390+320px, dark+light

Also re-runs: qa_sharp, qa_cropfilter, qa_camdetection, qa_scandetect2.

Usage: python3 qa/qa_scanfix2.py
Exit 0 only when every check passes.
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HUB, 'qa'))
from qa_camdetection import CDP  # noqa: E402

CHROME = '/opt/meta-chromium/chrome'
fails, passes = [], []


def check(name, ok, detail=''):
    (passes if ok else fails).append(name)
    print(('PASS ' if ok else 'FAIL ') + name + ((' — ' + str(detail)) if detail else ''))


def static_checks():
    print('== static: fix markers present ==')
    src = open(os.path.join(HUB, 'js', 'scan.js')).read()
    for name, needle in [
        ('muted/playsInline props', 'vid.muted=true; vid.playsInline=true'),
        ('orphan-session guard', 'SCAN._camStop'),
        ('watchdog timer', 'wdTimer=setTimeout'),
        ('watchdog error card', 'function camFail('),
        ('blank gate in loop', 'SCAN._camBlank(dp)'),
        ('blank never locked', "blank?'scan.camHint'"),
        ('pages pill markup', 'data-pagespill'),
        ('pill paint', 'function paintPill()'),
        ('gateTake re-entry guard', "querySelector('.sc-camwrap')) return"),
    ]:
        check('static: ' + name, needle in src)
    css = open(os.path.join(HUB, 'css', 'scan.css')).read()
    check('static: pill css + hidden override',
          '.sc-pagespill' in css and '.sc-pagespill[hidden]{display:none}' in css)
    i18n = open(os.path.join(HUB, 'js', 'i18n.js')).read()
    for k in ['scan.camFail', 'scan.camFailHint', 'scan.tryAgain']:
        check('static: i18n key ' + k, i18n.count("'%s'" % k) >= 4, 'locales=%d' % i18n.count("'%s'" % k))


MOUNT_CAM = r"""
(function(tag){
  var out = {};
  try {
    HUB.scan._t.scanPages().length = 0;
    if (HUB.scan._t.camStop) { try { HUB.scan._t.camStop(); } catch(e){} }
    var body = document.createElement('div'); body.id = tag;
    document.body.appendChild(body);
    HUB.scan._t.scanCamView(body);
    out.mounted = !!body.querySelector('.sc-camwrap');
    var vid = body.querySelector('[data-vid]');
    out.mutedProp = !!(vid && vid.muted === true);
    out.playsInlineProp = !!(vid && vid.playsInline === true);
    window.__fixBodies = window.__fixBodies || {};
    window.__fixBodies[tag] = body;
  } catch(e){ out.err = String(e && e.stack || e); }
  return out;
})('%s')
"""

CLEANUP = r"""
(function(){
  try { HUB.scan._t.camStop(); } catch(e){}
  Object.keys(window.__fixBodies || {}).forEach(function(k){
    var b = window.__fixBodies[k]; if (b && b.parentNode) b.parentNode.removeChild(b);
  });
  window.__fixBodies = {};
  return true;
})()
"""


def run_tag(vp, theme, with_watchdog):
    tag = '%d-%s' % (vp, theme)
    port = 9361 + vp + (11 if theme == 'light' else 0) + (100 if with_watchdog else 0)
    chrome = subprocess.Popen(
        [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
         '--allow-file-access-from-files',
         '--use-fake-device-for-media-stream',
         '--use-fake-ui-for-media-stream',
         '--window-size=%d,844' % vp,
         '--remote-debugging-port=%d' % port, 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(40):
            try:
                pages = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % port, timeout=2))
                for pg in pages:
                    if pg.get('type') == 'page':
                        ws_url = pg['webSocketDebuggerUrl']
                        break
                if ws_url:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        check('chrome up %s' % tag, bool(ws_url))
        if not ws_url:
            return
        cdp = CDP(ws_url)
        ev0 = len(cdp.events)
        cdp.call('Runtime.enable'); cdp.call('Log.enable'); cdp.call('Page.enable')

        def ev(expr, await_promise=False):
            r = cdp.call('Runtime.evaluate',
                         {'expression': expr, 'returnByValue': True, 'awaitPromise': await_promise})
            return (r.get('result') or {}).get('value')

        cdp.call('Page.navigate', {'url': 'file://' + os.path.join(HUB, 'index.html')})
        ok = False
        for _ in range(60):
            if ev('!!(window.HUB&&HUB.scan&&HUB.scan._t)'):
                ok = True
                break
            time.sleep(0.5)
        check('app loads %s' % tag, ok)
        if not ok:
            return
        ev('document.body.classList.%s("dark")' % ('add' if theme == 'dark' else 'remove'))

        # ---- F1: muted/playsInline properties ----
        m = ev(MOUNT_CAM % 'fixA') or {}
        check('F1 camView mounts %s' % tag, m.get('mounted') is True, m.get('err', ''))
        check('F1 video.muted property %s' % tag, m.get('mutedProp') is True)
        check('F1 video.playsInline property %s' % tag, m.get('playsInlineProp') is True)

        # ---- F2: double entry -> exactly one live stream ----
        d = ev(r"""
        (function(){
          var out = {};
          try {
            window.__streams = [];
            var _g = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
            navigator.mediaDevices.getUserMedia = function(c){
              return _g(c).then(function(s){ window.__streams.push(s); return s; });
            };
            var b = document.createElement('div'); b.id = 'fixB';
            document.body.appendChild(b);
            HUB.scan._t.scanCamView(b);
            HUB.scan._t.scanCamView(b); /* second entry must kill the first session */
            window.__fixBodies = window.__fixBodies || {};
            window.__fixBodies['fixB'] = b;
            out.calls = window.__streams.length;
          } catch(e){ out.err = String(e && e.stack || e); }
          return out;
        })()""") or {}
        time.sleep(2.0)  # let both getUserMedia promises settle
        live = ev(r"""
        (function(){
          var n = 0;
          (window.__streams || []).forEach(function(s){
            s.getVideoTracks().forEach(function(tr){ if (tr.readyState === 'live') n++; });
          });
          return { calls: (window.__streams || []).length, liveTracks: n };
        })()""") or {}
        check('F2 two entries, one live stream %s' % tag,
              live.get('liveTracks') == 1, 'calls=%s live=%s' % (live.get('calls'), live.get('liveTracks')))
        ev(CLEANUP)

        # ---- F4: blank gate ----
        g = ev(r"""
        (function(){
          var out = {};
          try {
            var B = function(a){ return HUB.scan._t.camBlank(a); };
            function mk(fill){
              var a = new Uint8ClampedArray(320*180*4);
              if (fill === 'noise') {
                var s = 12345;
                for (var i = 0; i < a.length; i += 4) {
                  s = (s * 1103515245 + 12345) & 0x7fffffff;
                  var v = s % 256; a[i] = a[i+1] = a[i+2] = v; a[i+3] = 255;
                }
              } else if (fill === 'split') {
                for (var j = 0; j < a.length; j += 4) {
                  var v2 = ((j / 4) | 0) % 320 < 160 ? 10 : 240;
                  a[j] = a[j+1] = a[j+2] = v2; a[j+3] = 255;
                }
              } else {
                for (var k = 0; k < a.length; k += 4) { a[k] = a[k+1] = a[k+2] = fill; a[k+3] = 255; }
              }
              return a;
            }
            out.black = B(mk(0));
            out.white = B(mk(255));
            out.noise = B(mk('noise'));
            out.split = B(mk('split'));
          } catch(e){ out.err = String(e && e.stack || e); }
          return out;
        })()""") or {}
        check('F4 blank(black)=true %s' % tag, g.get('black') is True)
        check('F4 blank(white)=true %s' % tag, g.get('white') is True)
        check('F4 blank(noise)=false %s' % tag, g.get('noise') is False)
        check('F4 blank(half/half)=false %s' % tag, g.get('split') is False)

        # ---- F5: data-apply -> pill -> pagesView ----
        m5 = ev(MOUNT_CAM % 'fixC') or {}
        check('F5 camView mounts %s' % tag, m5.get('mounted') is True, m5.get('err', ''))
        vw_ok = False
        for _ in range(20):
            if ev("(function(){var v=document.querySelector('#fixC [data-vid]');return v&&v.videoWidth>0;})()"):
                vw_ok = True
                break
            time.sleep(0.5)
        check('F5 video renders frames %s' % tag, vw_ok)
        cap = ev(r"""
        (function(){
          var out = {};
          try {
            delete window.ImageCapture; /* deterministic: use the video-frame path */
            document.querySelector('#fixC [data-cap]').click();
            out.clicked = true;
          } catch(e){ out.err = String(e && e.stack || e); }
          return out;
        })()""") or {}
        applied_visible = False
        for _ in range(20):
            if ev("(function(){return !!document.querySelector('#fixC [data-apply]');})()"):
                applied_visible = True
                break
            time.sleep(0.5)
        check('F5 capture reaches review %s' % tag, applied_visible, (cap or {}).get('err', ''))
        if applied_visible:
            ev("(function(){document.querySelector('#fixC [data-apply]').click();})()")
            pill = None
            for _ in range(20):
                pill = ev(r"""
                (function(){
                  var p = document.querySelector('#fixC [data-pagespill]');
                  if (!p || p.hidden) return null;
                  var img = p.querySelector('[data-pillthumb] img');
                  var r = p.getBoundingClientRect();
                  return { count: document.querySelector('#fixC [data-pillcount]').textContent,
                           thumb: !!(img && img.src && img.src.indexOf('data:image') === 0),
                           visible: r.width > 0 && r.height > 0 };
                })()""")
                if pill:
                    break
                time.sleep(0.5)
            check('F5 pill appears after save %s' % tag, pill is not None)
            if pill:
                check('F5 pill count=1 %s' % tag, pill.get('count') == '1', 'count=%s' % pill.get('count'))
                check('F5 pill has thumbnail %s' % tag, pill.get('thumb') is True)
                check('F5 pill visible %s' % tag, pill.get('visible') is True)
                shot = cdp.call('Page.captureScreenshot', {'format': 'png'})
                if shot.get('data'):
                    fn = os.path.join(HUB, 'qa', 'fix2-pill-%s.png' % tag)
                    open(fn, 'wb').write(base64.b64decode(shot['data']))
                    check('F5 pill screenshot %s' % tag, True, fn)
                ev("(function(){document.querySelector('#fixC [data-pagespill]').click();})()")
                time.sleep(1.0)
                pv = ev(r"""
                (function(){
                  var g = document.querySelector('#fixC [data-g]');
                  return { pagesView: !!g, n: HUB.scan._t.scanPages().length };
                })()""") or {}
                check('F5 pill tap reaches pagesView %s' % tag, pv.get('pagesView') is True)
                check('F5 saved page present %s' % tag, pv.get('n') == 1, 'n=%s' % pv.get('n'))
        ev(CLEANUP)

        # ---- F3: watchdog (only on one tag; slow) ----
        if with_watchdog:
            w = ev(r"""
            (function(){
              var out = {};
              try {
                /* black-hole stream: getUserMedia resolves but the video
                   never renders a frame (no tracks) -> watchdog must fire */
                var _g = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                navigator.mediaDevices.getUserMedia = function(c){
                  return _g(c).then(function(){ return new MediaStream(); });
                };
                window.__gum0 = _g;
                HUB.scan._t.scanPages().length = 0;
                var b = document.createElement('div'); b.id = 'fixW';
                document.body.appendChild(b);
                HUB.scan._t.scanCamView(b);
                window.__fixBodies = window.__fixBodies || {};
                window.__fixBodies['fixW'] = b;
                out.mounted = true;
              } catch(e){ out.err = String(e && e.stack || e); }
              return out;
            })()""") or {}
            for _ in range(28):  # repair ladder: 3.5s + re-play 3s + re-acquire 3.5s
                _c = ev("(function(){return !!document.querySelector('#fixW [data-retry]');})()")
                if _c: break
                time.sleep(0.5)
            card = ev(r"""
            (function(){
              var r = document.querySelector('#fixW [data-retry]');
              if (!r) return null;
              var rr = r.getBoundingClientRect();
              return { visible: rr.width > 0, text: document.querySelector('#fixW .sc-sect').textContent };
            })()""")
            check('F3 watchdog error card %s' % tag, card is not None and card.get('visible'),
                  (card or {}).get('text', ''))
            if card:
                shot = cdp.call('Page.captureScreenshot', {'format': 'png'})
                if shot.get('data'):
                    fn = os.path.join(HUB, 'qa', 'fix2-watchdog-%s.png' % tag)
                    open(fn, 'wb').write(base64.b64decode(shot['data']))
                    check('F3 watchdog screenshot %s' % tag, True, fn)
                # restore getUserMedia, retry must re-enter the camera
                ev("(function(){ navigator.mediaDevices.getUserMedia = window.__gum0; })()")
                ev("(function(){document.querySelector('#fixW [data-retry]').click();})()")
                time.sleep(2.0)
                again = ev("(function(){return !!document.querySelector('#fixW .sc-camwrap');})()")
                check('F3 retry re-enters camView %s' % tag, again is True)
            ev(CLEANUP)

        # ---- F6: zero console errors ----
        real = []
        for e in cdp.ev(since=ev0):
            p = e.get('params', {})
            if e.get('method') == 'Log.entryAdded' and (p.get('entry') or {}).get('level') == 'error':
                real.append(str((p['entry'].get('text') or p['entry'].get('url')))[:160])
            elif e.get('method') == 'Runtime.consoleAPICalled' and p.get('type') == 'error':
                real.append('console.error called')
            elif e.get('method') == 'Runtime.exceptionThrown':
                real.append(str(p.get('exceptionDetails', {}).get('text'))[:160])
        check('F6 zero console errors %s' % tag, len(real) == 0, '; '.join(real[:3]))
    finally:
        try:
            chrome.terminate()
        except Exception:
            pass


def rerun(names):
    for n in names:
        print('== rerun %s ==' % n)
        p = subprocess.run([sys.executable, os.path.join(HUB, 'qa', n)],
                           capture_output=True, text=True, timeout=1200, cwd=HUB)
        tail = (p.stdout or '').strip().splitlines()
        print('\n'.join(tail[-4:]))
        check('rerun %s green' % n, p.returncode == 0, 'rc=%d' % p.returncode)


def main():
    static_checks()
    run_tag(390, 'dark', with_watchdog=True)
    run_tag(390, 'light', with_watchdog=False)
    run_tag(320, 'dark', with_watchdog=False)
    rerun(['qa_sharp.py', 'qa_cropfilter.py', 'qa_camdetection.py', 'qa_scandetect2.py'])
    print('\n==== %d passed, %d failed ====' % (len(passes), len(fails)))
    if fails:
        print('FAILURES:')
        for f in fails:
            print('  - ' + f)
        sys.exit(1)


if __name__ == '__main__':
    main()
