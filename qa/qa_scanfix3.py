#!/usr/bin/env python3
"""QA: scanner turn 3 — levelness + camera resilience.

Part A (node): qa/scanlevel_driver.js warps synthetic fixtures and MEASURES
  output edge angles. Hard gate: every edge within +/-1.0deg of
  horizontal/vertical when detection IoU >= 0.85. Reports per-class maxima.

Part B (CDP, headless Chromium, fake camera):
  R1 static: 1080p constraints (ideal:1920, no 3840/min:1280), viewPages i18n x4,
      refineCapture wired into the shutter path
  R2 dead track mid-session -> repair ladder -> error card WITH diag code
  R3 "Use this page" -> camera dies -> falls back to pagesView (no dead camera)
  R4 three shutter->review->Use-this-page cycles -> pill count 3 -> pagesView has 3
  R5 zero console errors; 390+320px, dark+light

Also re-runs: qa_sharp, qa_cropfilter, qa_camdetection, qa_scandetect2, qa_scanfix2.

Usage: python3 qa/qa_scanfix3.py
Exit 0 only when every check passes.
"""
import base64
import json
import os
import re
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
    print(('PASS ' if ok else 'FAIL ') + name + ((' -- ' + str(detail)) if detail else ''))


def static_checks():
    print('== static ==')
    src = open(os.path.join(HUB, 'js', 'scan.js')).read()
    check('static: 1080p ideal width', 'width:{ideal:1920}' in src)
    check('static: 1080p ideal height', 'height:{ideal:1080}' in src)
    check('static: no 4K ideals', 'ideal:3840' not in src and 'ideal:2160' not in src)
    check('static: no min:1280 floor', 'min:1280' not in src)
    check('static: refineCapture exported', 'refineCapture:refineCapture' in src)
    check('static: shutter calls refineCapture', 'CV.refineCapture(fpx' in src)
    check('static: health monitor', 'function sampleHealth()' in src)
    check('static: diag code', "diag: '+esc(diag)" in src or 'diag: ' in src)
    check('static: repair ladder', 'fresh getUserMedia, once' in src)
    check('static: apply fallback flag', 'SCAN._camAfterApply=true' in src)
    i18n = open(os.path.join(HUB, 'js', 'i18n.js')).read()
    check('static: viewPages x4 locales', i18n.count("'scan.viewPages'") >= 4,
          'locales=%d' % i18n.count("'scan.viewPages'"))


def levelness_checks():
    print('== Part A: levelness (node) ==')
    p = subprocess.run([sys.executable, '-c', 'import sys; sys.exit(0)'], capture_output=True)
    r = subprocess.run(['node', os.path.join(HUB, 'qa', 'scanlevel_driver.js')],
                       capture_output=True, text=True, timeout=600, cwd=HUB)
    if r.returncode != 0:
        check('levelness: driver runs', False, (r.stderr or '')[:200])
        return
    per_class = {}
    n = 0
    for line in (r.stdout or '').strip().splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        d = json.loads(line)
        n += 1
        cls = d['fixture'].rsplit('-', 1)[0]
        ok = (d['maxDeg'] is not None and d['maxDeg'] <= 1.0) if d['iou'] >= 0.85 else True
        check('level %s %s (iou %.3f)' % (d['fixture'], d['test'], d['iou']), ok,
              'maxDeg=%s' % d['maxDeg'])
        per_class.setdefault(cls + '/' + d['test'], []).append(d['maxDeg'] or 0)
    check('levelness: 30 fixture measurements', n == 30, 'n=%d' % n)
    print('  -- per-class max deviation (deg) --')
    for k in sorted(per_class):
        print('  %-18s max %.3f' % (k, max(per_class[k])))


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
    window.__fixBodies = window.__fixBodies || {};
    window.__fixBodies[tag] = body;
  } catch(e){ out.err = String(e && e.stack || e); }
  return out;
})('%s')
"""

CLEANUP = r"""
(function(){
  try { HUB.scan._t.camStop(); } catch(e){}
  try {
    var _g = window.__gumReal;
    if (_g) navigator.mediaDevices.getUserMedia = _g;
  } catch(e){}
  Object.keys(window.__fixBodies || {}).forEach(function(k){
    var b = window.__fixBodies[k]; if (b && b.parentNode) b.parentNode.removeChild(b);
  });
  window.__fixBodies = {};
  try { HUB.scan._t.scanPages().length = 0; } catch(e){}
  return true;
})()
"""

POISON_GUM = r"""
(function(){
  /* remember the real one once, then return ended-track streams */
  if (!window.__gumReal) window.__gumReal = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  var _g = window.__gumReal;
  navigator.mediaDevices.getUserMedia = function(c){
    return _g(c).then(function(s){
      try { s.getVideoTracks().forEach(function(t){ t.stop(); }); } catch(e){}
      return s;
    });
  };
  return true;
})()
"""


def wait_for(ev, expr, timeout=15.0):
    for _ in range(int(timeout / 0.5)):
        if ev(expr):
            return True
        time.sleep(0.5)
    return False


def run_tag(vp, theme):
    tag = '%d-%s' % (vp, theme)
    port = 9381 + vp + (13 if theme == 'light' else 0)
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
        ev('delete window.ImageCapture')  # deterministic: video-frame capture path

        # ---- R2: dead track mid-session -> error card WITH diag code ----
        m = ev(MOUNT_CAM % 'fixR2') or {}
        check('R2 camView mounts %s' % tag, m.get('mounted') is True, m.get('err', ''))
        vw = wait_for(ev, "(function(){var v=document.querySelector('#fixR2 [data-vid]');return v&&v.videoWidth>0;})()")
        check('R2 video live %s' % tag, vw)
        if vw:
            ev(POISON_GUM)
            ev("(function(){var v=document.querySelector('#fixR2 [data-vid]');"
               "var t=v.srcObject.getVideoTracks()[0]; t.stop(); return t.readyState;})()")
            card = None
            for _ in range(30):  # health(2s) + ladder(~3.5s)
                card = ev(r"""
                (function(){
                  var r = document.querySelector('#fixR2 [data-retry]');
                  if (!r) return null;
                  var b = r.getBoundingClientRect();
                  var note = document.querySelector('#fixR2 .sc-col .sc-note');
                  return { visible: b.width > 0,
                           diag: (document.querySelector('#fixR2 .sc-col')||{textContent:''}).textContent };
                })()""")
                if card and card.get('visible'):
                    break
                time.sleep(0.5)
            has_diag = bool(card and re.search(r'diag:\s*v\d+p\dm\dc\d+\s+t-?\d+mu-?\d+\s+f-?\d+', card.get('diag', '')))
            check('R2 dead track -> error card %s' % tag, card is not None and card.get('visible'))
            check('R2 error card carries diag code %s' % tag, has_diag,
                  (card or {}).get('diag', '')[:80])
            if card and card.get('visible'):
                shot = cdp.call('Page.captureScreenshot', {'format': 'png'})
                if shot.get('data'):
                    fn = os.path.join(HUB, 'qa', 'fix3-deadcam-%s.png' % tag)
                    open(fn, 'wb').write(base64.b64decode(shot['data']))
                    check('R2 dead-cam screenshot %s' % tag, True, fn)
        ev(CLEANUP)

        # ---- R3: apply -> camera dies -> falls back to pagesView ----
        m = ev(MOUNT_CAM % 'fixR3') or {}
        check('R3 camView mounts %s' % tag, m.get('mounted') is True)
        vw = wait_for(ev, "(function(){var v=document.querySelector('#fixR3 [data-vid]');return v&&v.videoWidth>0;})()")
        check('R3 video live %s' % tag, vw)
        if vw:
            ev("(function(){document.querySelector('#fixR3 [data-cap]').click();})()")
            rev = wait_for(ev, "(function(){return !!document.querySelector('#fixR3 [data-apply]');})()")
            check('R3 capture reaches review %s' % tag, rev)
            if rev:
                ev(POISON_GUM)  # the post-apply camera will be dead
                ev("(function(){document.querySelector('#fixR3 [data-apply]').click();})()")
                pv = wait_for(ev, "(function(){return !!document.querySelector('#fixR3 [data-g]');})()", timeout=20)
                dead = ev("(function(){return !!document.querySelector('#fixR3 .sc-camwrap');})()")
                check('R3 dead camera after apply -> pagesView %s' % tag, pv)
                check('R3 no stranded dead camera %s' % tag, not dead)
                n = ev("(function(){return HUB.scan._t.scanPages().length;})()")
                check('R3 saved page survived %s' % tag, n == 1, 'n=%s' % n)
        ev(CLEANUP)

        # ---- R4: three use-page cycles -> pill count 3 ----
        m = ev(MOUNT_CAM % 'fixR4') or {}
        check('R4 camView mounts %s' % tag, m.get('mounted') is True)
        vw = wait_for(ev, "(function(){var v=document.querySelector('#fixR4 [data-vid]');return v&&v.videoWidth>0;})()")
        check('R4 video live %s' % tag, vw)
        cycles = 0
        for i in range(3):
            # wait for the (re)mounted camera to actually deliver frames before
            # tapping the shutter -- a premature tap is a silent no-op
            wait_for(ev, "(function(){var v=document.querySelector('#fixR4 [data-vid]');"
                         "return v&&v.videoWidth>0&&!v.paused;})()")
            ev("(function(){var c=document.querySelector('#fixR4 [data-cap]');if(c)c.click();})()")
            rev = wait_for(ev, "(function(){return !!document.querySelector('#fixR4 [data-apply]');})()")
            if not rev:
                break
            ev("(function(){document.querySelector('#fixR4 [data-apply]').click();})()")
            okc = wait_for(ev, "(function(){var p=document.querySelector('#fixR4 [data-pagespill]');"
                               "return p&&!p.hidden&&document.querySelector('#fixR4 [data-pillcount]').textContent=='%d';})()" % (i + 1))
            if okc:
                cycles += 1
            # wait for the next camView shutter before the next cycle
            wait_for(ev, "(function(){return !!document.querySelector('#fixR4 [data-cap]');})()")
        check('R4 three use-page cycles %s' % tag, cycles == 3, 'cycles=%d' % cycles)
        if cycles == 3:
            shot = cdp.call('Page.captureScreenshot', {'format': 'png'})
            if shot.get('data'):
                fn = os.path.join(HUB, 'qa', 'fix3-pill3-%s.png' % tag)
                open(fn, 'wb').write(base64.b64decode(shot['data']))
                check('R4 pill-3 screenshot %s' % tag, True, fn)
            ev("(function(){document.querySelector('#fixR4 [data-pagespill]').click();})()")
            time.sleep(1.0)
            n = ev("(function(){var g=document.querySelector('#fixR4 [data-g]');"
                   "return g?HUB.scan._t.scanPages().length:-1;})()")
            check('R4 pagesView holds 3 pages %s' % tag, n == 3, 'n=%s' % n)
        ev(CLEANUP)

        # ---- R5: zero console errors ----
        real = []
        for e in cdp.ev(since=ev0):
            p = e.get('params', {})
            if e.get('method') == 'Log.entryAdded' and (p.get('entry') or {}).get('level') == 'error':
                real.append(str((p.get('entry').get('text') or p.get('entry').get('url')))[:160])
            elif e.get('method') == 'Runtime.consoleAPICalled' and p.get('type') == 'error':
                real.append('console.error called')
            elif e.get('method') == 'Runtime.exceptionThrown':
                real.append(str(p.get('exceptionDetails', {}).get('text'))[:160])
        check('R5 zero console errors %s' % tag, len(real) == 0, '; '.join(real[:3]))
    finally:
        try:
            chrome.terminate()
        except Exception:
            pass


def rerun(names):
    for n in names:
        print('== rerun %s ==' % n)
        p = subprocess.run([sys.executable, os.path.join(HUB, 'qa', n)],
                           capture_output=True, text=True, timeout=1800, cwd=HUB)
        tail = (p.stdout or '').strip().splitlines()
        print('\n'.join(tail[-4:]))
        check('rerun %s green' % n, p.returncode == 0, 'rc=%d' % p.returncode)


def main():
    static_checks()
    levelness_checks()
    run_tag(390, 'dark')
    run_tag(390, 'light')
    run_tag(320, 'dark')
    rerun(['qa_sharp.py', 'qa_cropfilter.py', 'qa_camdetection.py', 'qa_scandetect2.py', 'qa_scanfix2.py'])
    print('\n==== %d passed, %d failed ====' % (len(passes), len(fails)))
    if fails:
        print('FAILURES:')
        for f in fails:
            print('  - ' + f)
        sys.exit(1)


if __name__ == '__main__':
    main()
