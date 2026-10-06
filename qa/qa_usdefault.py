#!/usr/bin/env python3
"""HUB QA: US-default country behavior (PraBin's order 2026-09-23).
Fresh profile /tmp/hubqa-usd (wiped), file:// load, 390px.
1. fresh + non-US timezone -> guessCountry()='US', currency '$', weather 'f'
2. auth login dial code defaults +1 on fresh
3. setCountry('NP') -> persists across reload
4. after NP: login dial code +977, currency 'NPR symbol', weather 'c'
5. institution search filters by country (US rows for US, none for NP filter)
6. zero console errors
"""
import sys, time, shutil
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
import qa_ask as Q

PROF = '/tmp/hubqa-usd'
SHOTDIR = '/home/hatch/workspace/hub/qa'
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)

def boot(c):
    ok = Q.js_wait(c, "return !document.getElementById('splash')", 25)
    note(ok, 'splash dismissed')
    ok = Q.js_wait(c, "return document.readyState==='complete' && !!window.HUB && !!HUB.i18n", 25)
    note(ok, 'boot')
    Q.disarm_gate(c); time.sleep(0.8); Q.disarm_gate(c)
    c.js(Q.JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
    time.sleep(0.5)

def login_dial(c):
    """Open the login overlay and read the selected country-code value."""
    c.js(Q.JS % "window.__gateSkip=true; try{HUB.auth.openLogin()}catch(e){} return 1")
    ok = Q.js_wait(c, "return !!document.querySelector('#aCC')", 8)
    v, _ = c.js(Q.JS % "var s=document.getElementById('aCC'); return s?s.value:''")
    c.js(Q.JS % "try{HUB.auth.close()}catch(e){} return 1")
    time.sleep(0.3)
    return ok, v

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = Q.subprocess.Popen([Q.CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % Q.PORT, '--remote-allow-origins=*', '--window-size=390,844',
        '--user-data-dir=%s' % PROF, '--hide-scrollbars', '--allow-file-access-from-files', Q.BASE],
        stdout=Q.subprocess.DEVNULL, stderr=Q.subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with Q.urllib.request.urlopen('http://localhost:%d/json/list' % Q.PORT, timeout=5) as r:
                    ts = Q.json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = Q.CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        Q.arm_hooks(c)
        # non-US timezone: Kathmandu
        c.send('Emulation.setTimezoneOverride', {'timezoneId': 'Asia/Kathmandu'})
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        boot(c)

        g, _ = c.js(Q.JS % "return HUB.i18n.guessCountry()")
        note(g == 'US', 'guessCountry() is US even with Asia/Kathmandu timezone', g)
        gc, _ = c.js(Q.JS % "return HUB.i18n.getCountry()")
        note(gc is None, 'fresh install has no saved country', str(gc))
        cur, _ = c.js(Q.JS % "return HUB.i18n.currencySymbol()")
        note(cur == '$', 'fresh currency is $', cur)
        wu, _ = c.js(Q.JS % "try{return HUB.wx.unit()}catch(e){return 'ERR:'+e.message}")
        note(wu == 'f', 'fresh US weather unit is f (Fahrenheit)', str(wu))

        ok, dial = login_dial(c)
        note(ok and dial == 'US', 'login dial code defaults to US (+1)', dial)

        # institution search respects country filter
        v, _ = c.js(Q.JS % ("return HUB.intl.loadColleges().then(function(rows){"
            "var us=HUB.intl.searchColleges('lincoln','US',10);"
            "var np=HUB.intl.searchColleges('lincoln','NP',10);"
            "return {n:rows.length, usN:us.length, usC:us.length?us[0][1]:'', npN:np.length}; })"), awaitPromise=True)
        note(bool(v) and v.get('n', 0) > 120000, 'schools+colleges merged rows load', str(v.get('n') if v else v))
        note(bool(v) and v.get('usN', 0) > 0 and v.get('usC') == 'United States',
             'US filter returns United States schools', str(v))
        note(bool(v) and v.get('npN', 0) == 0, 'NP filter returns zero US rows', str(v.get('npN') if v else v))

        # switch country to Nepal
        c.js(Q.JS % "HUB.i18n.setCountry('NP'); return 1")
        time.sleep(0.4)
        cur2, _ = c.js(Q.JS % "return HUB.i18n.currencySymbol()")
        note('Rs' in cur2 or '₨' in cur2 or 'रू' in cur2, 'currency follows Nepal selection', cur2)
        wu2, _ = c.js(Q.JS % "try{return HUB.wx.unit()}catch(e){return 'ERR:'+e.message}")
        note(wu2 == 'c', 'weather unit switches to c after Nepal selection', str(wu2))
        ok2, dial2 = login_dial(c)
        note(ok2 and dial2 == 'NP', 'login dial code follows Nepal selection (+977)', dial2)

        # reload: selection survives
        c.send('Page.reload'); Q.disarm_gate(c)
        okb = Q.js_wait(c, "return document.readyState==='complete' && !!window.HUB && !!HUB.i18n", 25)
        note(okb, 'reload')
        Q.disarm_gate(c); time.sleep(0.5)
        gc2, _ = c.js(Q.JS % "return HUB.i18n.getCountry()")
        note(gc2 == 'NP', 'saved country NP survives reload', str(gc2))
        wu3, _ = c.js(Q.JS % "try{return HUB.wx.unit()}catch(e){return 'ERR:'+e.message}")
        note(wu3 == 'c', 'weather unit still c after reload', str(wu3))

        bad = Q.collect_errors(c)
        note(not bad, 'zero console errors', '; '.join(bad)[:400])
        n = sum(checks); tot = len(checks)
        print('USDEFAULT QA: %d/%d' % (n, tot))
        sys.exit(0 if n == tot else 1)
    finally:
        proc.terminate()

main()
