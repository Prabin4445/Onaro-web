"""QA: calculator Daily entry card + full-page overlay.
390+320px (true emulation), dark+light, en+de.
Checks: entry card renders w/ animated SVG icon (getAnimations running),
tap opens full overlay with WORKING calculator (2+2=4, sin(30deg)=0.5),
Escape + close button return to Daily intact, no overflow, zero console errors.
"""
import subprocess, time, json, base64, os, sys
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import websocket  # noqa: F401  (kept for parity with other harnesses)

PORT = 9453
fails = []
def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok: fails.append(n)

def j(c, expr, await_=False):
    # Runtime.evaluate has no top-level `return`: single expressions are
    # IIFE-wrapped with a return; multi-statement scripts run as-is.
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip()
        if e.endswith(';'): e = e[:-1]
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q: instr = False
        elif ch in '"\'`': instr, q = True, ch
        elif ch in '([{': depth += 1
        elif ch in ')]}': depth -= 1
        elif ch == ';' and depth == 0: top_semi = True; break
    if not top_semi:
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'awaitPromise': await_, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

def tap(c, sel):
    j(c, "var b=document.querySelector('%s'); if(b) b.click(); return !!b;" % sel)
    time.sleep(0.6)

LANGS = {'en': 'en', 'de': 'de'}
for width, theme, lang in [(390, 'light', 'en'), (390, 'dark', 'en'),
                           (320, 'light', 'en'), (390, 'light', 'de')]:
    tag = '%dpx/%s/%s' % (width, theme, lang)
    prof = '/tmp/hubqa-calcentry-%d-%s-%s' % (width, theme, lang)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + prof, '--hide-scrollbars',
        'file:///home/hatch/workspace/hub/index.html'])
    time.sleep(2.5)
    tgt = None
    for _ in range(30):
        try:
            tgts = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT).read())
            tgt = [t for t in tgts if t.get('type') == 'page'][0]; break
        except Exception: time.sleep(0.4)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': width, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    check(tag + ' true viewport', j(c, 'return window.innerWidth;') == width)
    j(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.calc&&HUB.i18n&&HUB.ui);") is True: break
        time.sleep(0.5)
    j(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'%s',country:'US'}));"
         "HUB.store.state.prefs.dark=%s;HUB.store.save();HUB.applyTheme();" % (lang, 'true' if theme == 'dark' else 'false'))
    if lang == 'de':
        ok = j(c, "HUB.i18n.loadLocale('de').then(function(s){ if(s) HUB.i18n.setLang('de'); return HUB.i18n._dict('de')!==HUB.i18n._dict('en'); })", True)
        check(tag + ' de locale loaded', ok is True)
        time.sleep(0.5)
    j(c, """var p=HUB.store.state.profile; p.name='QA Calc'; p.campus='The University of Texas at Dallas';
      p.verified=true; HUB.store.save(); window.__gateSkip=true;
      try{HUB.auth.close()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1;""")
    for _ in range(20):
        if j(c, "return !document.getElementById('splash');") is True: break
        time.sleep(0.5)
    j(c, "HUB.showTab('daily')")
    for _ in range(20):
        if j(c, "return !!document.getElementById('homeCalcEntry');") is True: break
        time.sleep(0.5)

    # ---- entry card ----
    st = j(c, """var e=document.getElementById('homeCalcEntry'); if(!e) return null;
      var svg=e.querySelector('svg.ce-anim');
      var k1=e.querySelector('.ce-k1'), d0=e.querySelector('.ce-d0');
      var an=[];
      [k1,d0].forEach(function(el){ if(el) el.getAnimations().forEach(function(a){ an.push(a.animationName+':'+a.playState); }); });
      var keys=svg?svg.querySelectorAll('.ce-k').length:0;
      var r=e.getBoundingClientRect();
      e.scrollIntoView({block:'center'});
      return {svg:!!svg, an:an, keys:keys, x:r.x, w:r.width,
        sub:document.querySelector('#homeCalcEntry .hrow-s').textContent};""")
    check(tag + ' entry card renders', st is not None, st)
    if st:
        check(tag + ' animated svg icon', st['svg'] is True)
        running = [a for a in st['an'] if 'running' in a]
        check(tag + ' icon animations running', len(running) > 0, st['an'][:4])
        check(tag + ' 9 keys in icon', st['keys'] == 9, st['keys'])
        check(tag + ' card inside viewport', st['x'] >= 0 and st['x'] + st['w'] <= width + 1,
              'x=%.0f w=%.0f' % (st['x'], st['w']))
        check(tag + ' localized sub', len(st['sub']) > 3, st['sub'][:40])
    time.sleep(0.6)
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, 'calcentry-%s-entry.png' % tag.replace('/', '-')), 'wb').write(base64.b64decode(r['data']))

    # ---- open overlay ----
    tap(c, '#homeCalcEntry')
    ov = j(c, """var o=document.getElementById('hubCalcRoot');
      if(!o) return null;
      var r=o.getBoundingClientRect();
      return {present:true, full:r.width>=innerWidth-2&&r.height>=innerHeight-2,
        calc:!!o.querySelector('#calcRoot'), close:!!document.getElementById('calcFullClose')};""")
    check(tag + ' overlay opens full-screen', ov and ov['full'] is True, ov)
    check(tag + ' calculator mounted', ov and ov['calc'] is True)
    check(tag + ' close control present', ov and ov['close'] is True)
    time.sleep(0.5)
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, 'calcentry-%s-overlay.png' % tag.replace('/', '-')), 'wb').write(base64.b64decode(r['data']))

    # ---- calculator works: 2+2=4 ----
    j(c, "document.querySelector('#hubCalcRoot [data-ck=ac]').click()")
    for k in ['k2', 'plus', 'k2', 'eq']:
        j(c, "document.querySelector('#hubCalcRoot [data-ck=%s]').click()" % k)
    time.sleep(0.4)
    res = j(c, "return document.querySelector('#hubCalcRoot #calcRes').textContent;")
    check(tag + ' 2+2=4', res is not None and '= 4' in res, res)

    # ---- sin(30deg)=0.5 ----
    mode = j(c, "return document.querySelector('#hubCalcRoot #calcModeBtn').textContent;")
    j(c, "document.querySelector('#hubCalcRoot [data-ck=ac]').click()")
    if mode and 'RAD' in mode.upper():
        j(c, "document.querySelector('#hubCalcRoot #calcModeBtn').click()")
        time.sleep(0.3)
    for k in ['sin', 'k3', 'k0', 'rp', 'eq']:
        j(c, "document.querySelector('#hubCalcRoot [data-ck=%s]').click()" % k)
    time.sleep(0.4)
    res2 = j(c, "return document.querySelector('#hubCalcRoot #calcRes').textContent;")
    check(tag + ' sin(30deg)=0.5', res2 is not None and '0.5' in res2, res2)

    # ---- Escape closes, Daily intact ----
    j(c, "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
    time.sleep(0.5)
    gone = j(c, "return !document.getElementById('hubCalcRoot');")
    back = j(c, "return !!document.getElementById('homeCalcEntry');")
    check(tag + ' Escape closes overlay', gone is True)
    check(tag + ' Daily intact after close', back is True)

    # ---- reopen, close button ----
    tap(c, '#homeCalcEntry')
    time.sleep(0.4)
    tap(c, '#calcFullClose')
    gone2 = j(c, "return !document.getElementById('hubCalcRoot');")
    check(tag + ' close button works', gone2 is True)

    nox = j(c, "return document.documentElement.scrollWidth<=window.innerWidth+1;")
    check(tag + ' no page overflow', nox is True)
    errs = j(c, "return window.__huberr.slice(0,6);")
    check(tag + ' zero console errors', not errs, errs)
    proc.terminate(); proc.wait()

print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
