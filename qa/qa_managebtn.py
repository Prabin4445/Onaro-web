import subprocess, time, json, base64, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from qa import CDP, CHROME, QA

PORT = 9459
checks = []
def check(name, ok, extra=""):
    checks.append((name, bool(ok), extra))
    print(("PASS " if ok else "FAIL ") + name + ((" | " + str(extra)) if extra else ""))

def j(c, expr):
    # NOTE: expressions are auto-wrapped in an IIFE — bare `return` at top level
    # is a SyntaxError in Runtime.evaluate and fails SILENTLY (no value).
    r = c.send('Runtime.evaluate', {'expression': '(()=>{' + expr + '})()', 'returnByValue': True}, wait=True)
    res = (r or {}).get('result', {})
    return res.get('value')

def run_case(width, theme):
    global proc
    prof = '/tmp/hubqa-managebtn-%d-%s' % (width, theme)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--allow-file-access-from-files',
        f'--user-data-dir={prof}', '--hide-scrollbars',
        'file:///home/hatch/workspace/hub/index.html'])
    time.sleep(2.5)
    import urllib.request
    for _ in range(30):
        try:
            data = urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json').read()
            tgts = json.loads(data)
            tgt = [t for t in tgts if t.get('type') == 'page'][0]
            break
        except Exception: time.sleep(0.4)
    import websocket
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844,
            'deviceScaleFactor': 2, 'mobile': True})
    # skip the auth gate: straight to tabs (must be set before the boot poller fires)
    j(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));"
         "window.__gateSkip=true;")
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.i18n&&HUB.ui);") is True: break
        time.sleep(0.5)
    j(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
         "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
    # onboarding via the real UI (proven qa.py pattern) — never strip wlcmHost manually
    for _ in range(3):
        st0 = j(c, "(()=>{const n=document.getElementById('obName'); if(!n) return 'gone';"
                   "n.value='QA Btn'; const cp=document.getElementById('obCampus'); if(cp) cp.selectedIndex=1;"
                   "document.getElementById('obGo').click(); return 'clicked'})()")
        time.sleep(1.0)
        if st0 == 'gone': break
    time.sleep(1.0)
    for _ in range(20):
        if j(c, "return !document.getElementById('splash');") is True: break
        time.sleep(0.5)
    j(c, "HUB.showTab('home')")
    time.sleep(1.5)
    # scroll classes header into view
    j(c, """var b=document.querySelector('[data-class-manage]');
      if(b){ b.scrollIntoView({block:'center'}); } return !!b;""")
    time.sleep(0.8)
    st = j(c, """var b=document.querySelector('[data-class-manage]'); if(!b) return null;
      var cs=getComputedStyle(b); var r=b.getBoundingClientRect();
      return {bg:cs.backgroundColor, br:cs.borderRadius, bw:cs.borderWidth, bs:cs.borderStyle,
        pad:cs.padding, tag:b.tagName, x:r.x, y:r.y, w:r.width, h:r.height,
        noX:document.documentElement.scrollWidth<=window.innerWidth+1};""")
    check(f'{width}px/{theme} manage btn exists', st is not None)
    if st:
        check(f'{width}px/{theme} looks like button (bg not transparent)', st['bg'] not in ('rgba(0, 0, 0, 0)', 'transparent'), st['bg'])
        check(f'{width}px/{theme} pill radius', '999' in st['br'], st['br'])
        check(f'{width}px/{theme} has border', st['bs'] != 'none' and st['bw'] != '0px', st['bw'] + ' ' + st['bs'])
        check(f'{width}px/{theme} inside viewport', st['x'] >= 0 and st['x'] + st['w'] <= width + 1, f"x={st['x']:.0f} w={st['w']:.0f}")
        check(f'{width}px/{theme} no page overflow', st['noX'] is True)
        # tap it -> classes manager should open
        j(c, "document.querySelector('[data-class-manage]').click()")
        time.sleep(1.0)
        opened = j(c, "return !!document.querySelector('.sheethost:not([hidden])') || !!document.querySelector('.sheet:not([hidden])') || document.body.innerHTML.includes('Add class') || document.body.textContent.includes('Add class');")
        check(f'{width}px/{theme} tap opens manager', opened is True)
        r = c.send('Page.captureScreenshot', {'format': 'png'})
        open(os.path.join(QA, f'managebtn-{width}-{theme}.png'), 'wb').write(base64.b64decode(r['data']))
    errs = j(c, "return window.__huberr.slice(0,5);")
    check(f'{width}px/{theme} zero console errors', not errs, errs)
    proc.terminate(); proc.wait()

run_case(390, 'light')
run_case(390, 'dark')
run_case(320, 'light')
fails = [n for n, ok, _ in checks if not ok]
print('TOTAL %d/%d' % (len(checks) - len(fails), len(checks)))
sys.exit(1 if fails else 0)
