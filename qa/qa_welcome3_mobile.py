#!/usr/bin/env python3
"""390x844 mobile-emulation check: all 3 welcome steps fit the viewport,
Continue reachable without scrolling."""
import sys, time, json, base64
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS ' + name)
    else: failed += 1; print('FAIL ' + name + ' ' + str(detail)[:140])

h = H(9333, '/tmp/hubqa-wlcm-mob')
try:
    h.c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(6)  # let boot + welcome render
    vis = h.js("(()=>{const w=document.getElementById('wlcmHost');return w&&!w.hidden})()")
    check('mobile: welcome visible', vis is True)
    def rect(sel):
        return json.loads(h.js("(()=>{const e=document.querySelector('%s');if(!e)return 'null';const r=e.getBoundingClientRect();return JSON.stringify({t:Math.round(r.top),b:Math.round(r.bottom),l:Math.round(r.left),r:Math.round(r.right)});})()" % sel))
    def fits(name, sel):
        r = rect(sel)
        check(name, r['t'] >= 0 and r['b'] <= 844 and r['l'] >= 0 and r['r'] <= 390, r)
    fits('mobile: step1 card fits 390x844', '.wlcm-card')
    r = h.c.send('Page.captureScreenshot', {'format': 'png'})
    open('/home/hatch/workspace/hub/qa/wlcm-mob-step1.png', 'wb').write(base64.b64decode(r['data']))
    h.js("document.querySelector('[data-wlang=\"hi\"]').click()"); time.sleep(1.2)
    fits('mobile: step2 card fits 390x844', '.wlcm-card')
    back = h.js("(()=>{const b=document.getElementById('wlcmBack');const r=b.getBoundingClientRect();return r.top>=0&&r.bottom<=844})()")
    check('mobile: step2 Back reachable', back is True)
    r = h.c.send('Page.captureScreenshot', {'format': 'png'})
    open('/home/hatch/workspace/hub/qa/wlcm-mob-step2.png', 'wb').write(base64.b64decode(r['data']))
    h.js("document.querySelector('[data-wcc=\"IN\"]').click()"); time.sleep(1.0)
    fits('mobile: step3 card fits 390x844', '.wlcm-card')
    go = rect('#wlcmGo')
    check('mobile: Continue reachable without scrolling', go['b'] <= 844 and go['t'] >= 0, go)
    nox = h.js("document.documentElement.scrollWidth<=390+1")
    check('mobile: no horizontal overflow', nox is True)
    errs = h.js("window.__huberr?window.__huberr.splice(0):[]")
    check('mobile: zero uncaught errors', not errs, errs)
finally:
    h.done()
print(f'==== MOBILE: {passed} passed, {failed} failed ====')
sys.exit(1 if failed else 0)
