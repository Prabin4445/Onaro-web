#!/usr/bin/env python3
"""Recapture the two mistimed dark Ask screenshots with correct target card."""
import sys, time, shutil
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
import qa_ask as Q

PROF = '/tmp/hubqa-askshot'

def boot_dark(c):
    ok = Q.js_wait(c, "return !document.getElementById('splash')", 25)
    print('splash gone:', ok)
    c.js(Q.JS % ("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
                 "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus';"
                 "s.prefs.dark=true; HUB.store.save(); return 1"))
    c.send('Page.reload')
    ok = Q.js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && !!window.HUB && !!HUB.ai", 25)
    print('boot:', ok)
    Q.disarm_gate(c); time.sleep(0.8); Q.disarm_gate(c)
    c.js(Q.JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
    time.sleep(0.5)

def last_card(c):
    return Q.JS % "var cs=document.querySelectorAll('#askSheetResults .card'); return cs.length?cs[cs.length-1]:null"

def ask_new(c, q):
    before, _ = c.js(Q.JS % "return document.querySelectorAll('#askSheetResults .card').length")
    c.js(Q.JS % ("var i=document.getElementById('askSheetInput'); i.value=%s;"
                 "i.dispatchEvent(new Event('input',{bubbles:true})); return 1" % Q.json.dumps(q)))
    c.js(Q.JS % "document.getElementById('askSheetSend').click(); return 1")
    ok = Q.js_wait(c, "return document.querySelectorAll('#askSheetResults .card').length>%d" % (before or 0), 8)
    print('ask %r ->' % q, ok)
    return ok

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    chrome = Q.subprocess.Popen([Q.CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
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
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        boot_dark(c)
        print('sheet open:', Q.open_sheet(c))
        time.sleep(0.5)
        ask_new(c, 'help')
        time.sleep(0.6)
        c.shot('ask-guide-dark.jpg')
        ask_new(c, 'how do i rate a professor')
        time.sleep(0.5)
        # click [data-walk] on the FRESH (first = newest-prepended) card
        c.js(Q.JS % "var cs=document.querySelectorAll('#askSheetResults .card'); var nc=cs[0];"
                    "var w=nc.querySelector('[data-walk]'); if(w) w.click(); return 1")
        time.sleep(0.6)
        v, _ = c.js(Q.JS % "var cs=document.querySelectorAll('#askSheetResults .card'); return cs[0].textContent.slice(0,40)")
        print('walker card:', v)
        c.shot('ask-walker-dark.jpg')
        errs = Q.collect_errors(c)
        print('console errors:', errs if errs else 'NONE')
    finally:
        chrome.terminate()

main()
