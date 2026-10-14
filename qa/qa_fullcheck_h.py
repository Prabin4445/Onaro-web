#!/usr/bin/env python3
"""FULL check H: weather flow — set location, strip paints temp, detail opens,
city search works."""
import sys, time, json, re
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def set_val(h, sel, val):
    return h.js(f"""(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));return 'set';}})()""")

h = H(9499, '/tmp/hubqa-fullh')
try:
    for _ in range(40):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
    h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
    h.setup('dark')
    h.js("localStorage.setItem('orbit_i18n', JSON.stringify({lang:'en',country:'US'})); window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
    time.sleep(1)
    h.tab('home')
    strip0 = str(h.js("(document.getElementById('wxStrip')||{}).innerText||'nostrip'"))
    h.note('weather: strip present, asks to set location when unset', 'nostrip' not in strip0, strip0[:60].replace('\n', ' '))
    # set Williamsburg KY (Cumberlands) via the app's own setter
    h.js("HUB.wx.setLoc({name:'Williamsburg, KY',lat:36.98,lon:-84.20}); 'ok'")
    h.js("try{HUB.wxhome.refresh()}catch(e){}; 'ok'")
    txt = ''
    for i in range(15):
        time.sleep(1.5)
        txt = str(h.js("(document.getElementById('wxStrip')||{}).innerText||''"))
        if re.search(r'\d+\s*°', txt): break
    h.note('weather: strip paints live temperature', bool(re.search(r'\d+\s*°', txt)), txt[:80].replace('\n', ' '))
    # open detail
    h.js("document.getElementById('wxStrip').click(); 'ok'"); time.sleep(1.2)
    det = h.js("(()=>{const s=document.getElementById('sheetHost');return s&&!s.hidden?(s.innerText||'').length:0})()")
    h.note('weather: detail sheet opens', (det or 0) > 40, f'len={det}')
    # city search inside detail
    set_val(h, '#wxdIn', 'Lexington')
    h.js("(()=>{const b=document.getElementById('wxdGo');if(b)b.click();return !!b})()")
    res = ''
    for i in range(10):
        time.sleep(1.5)
        res = str(h.js("(document.getElementById('wxdRes')||{}).innerText||''"))
        if 'Lexington' in res: break
    h.note('weather: city search returns results', 'Lexington' in res, res[:80].replace('\n', ' '))
    h.close_all()
    errs = h.errs()
    h.note('ZERO JS errors across part H', not errs, str(errs)[:250])
    h.save('dark', 'fullcheckH')
finally:
    h.done()
