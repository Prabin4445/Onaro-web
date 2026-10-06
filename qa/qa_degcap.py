import subprocess, time, json, base64, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import urllib.request, websocket

PORT = 9451
def j(c, expr):
    # NOTE: expressions are auto-wrapped in an IIFE — bare `return` at top level
    # is a SyntaxError in Runtime.evaluate and fails SILENTLY (no value).
    r = c.send('Runtime.evaluate', {'expression': '(()=>{' + expr + '})()', 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

fails = []
def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok: fails.append(n)

for width, theme in [(390, 'light'), (390, 'dark')]:
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--allow-file-access-from-files',
        f'--user-data-dir=/tmp/hubqa-degcap-{width}-{theme}', '--hide-scrollbars',
        'file:///home/hatch/workspace/hub/index.html'])
    time.sleep(2.5)
    tgt = None
    for _ in range(30):
        try:
            tgts = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json').read())
            tgt = [t for t in tgts if t.get('type') == 'page'][0]; break
        except Exception: time.sleep(0.4)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    # skip the auth gate: straight to tabs (must be set before the boot poller fires)
    j(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));"
         "window.__gateSkip=true;")
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.degree&&HUB.i18n&&HUB.ui);") is True: break
        time.sleep(0.5)
    j(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
         "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
    # onboarding via the real UI (proven qa.py pattern) — never strip wlcmHost manually
    for _ in range(3):
        st0 = j(c, "(()=>{const n=document.getElementById('obName'); if(!n) return 'gone';"
                   "n.value='QA Cap'; const cp=document.getElementById('obCampus'); if(cp) cp.selectedIndex=1;"
                   "document.getElementById('obGo').click(); return 'clicked'})()")
        time.sleep(1.0)
        if st0 == 'gone': break
    time.sleep(1.0)
    for _ in range(20):
        if j(c, "return !document.getElementById('splash');") is True: break
        time.sleep(0.5)
    j(c, "HUB.showTab('home')"); time.sleep(1.5)
    j(c, "var e=document.getElementById('homeDegEntry'); if(e) e.scrollIntoView({block:'center'}); return !!e;")
    time.sleep(1.0)
    st = j(c, """var e=document.getElementById('homeDegEntry'); if(!e) return null;
      var svg=e.querySelector('svg.deg-cap-anim'); if(!svg) return {svg:false};
      var cs=getComputedStyle(svg); var an=svg.getAnimations().map(a=>a.animationName+':'+a.playState);
      var tas=e.querySelector('.deg-tassel'); var tcs=tas?getComputedStyle(tas):null;
      return {svg:true, anim:cs.animationName, an:an,
        tasselAnim:tcs?tcs.animationName:null,
        spark:!!e.querySelector('.deg-spark')};""")
    check(f'{width}/{theme} svg cap present', st and st.get('svg') is True, st)
    if st and st.get('svg'):
        check(f'{width}/{theme} bob animation running', 'degBob' in str(st.get('an')), st.get('an'))
        check(f'{width}/{theme} tassel animation running', (st.get('tasselAnim') or '') == 'degTassel', st.get('tasselAnim'))
        check(f'{width}/{theme} sparkle present', st.get('spark') is True)
    # two phase screenshots to show motion
    for i in range(2):
        r = c.send('Page.captureScreenshot', {'format': 'png'})
        open(os.path.join(QA, f'degcap-{width}-{theme}-{i}.png'), 'wb').write(base64.b64decode(r['data']))
        time.sleep(1.6)
    # tap still opens tracker
    j(c, "document.getElementById('homeDegEntry').click()"); time.sleep(1.2)
    opened = j(c, "return !!document.getElementById('hubDegRoot');")
    check(f'{width}/{theme} tap opens tracker', opened is True)
    j(c, "try{HUB.degree.close()}catch(e){}")
    errs = j(c, "return window.__huberr.slice(0,5);")
    check(f'{width}/{theme} zero console errors', not errs, errs)
    proc.terminate(); proc.wait()

print('TOTAL %d/%d' % (4*5 - len(fails), 4*5 - 0) if False else 'done, fails=%d' % len(fails))
sys.exit(1 if fails else 0)
