#!/usr/bin/env python3
"""Focused degree probe: ECU req-only notice + TTU semester plan + toggle."""
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def set_val(h, sel, val):
    return h.js(f"""(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));return 'set';}})()""")

h = H(9477, '/tmp/hubqa-degprobe')
try:
    for _ in range(40):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
    h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
    h.setup('dark')
    h.js("localStorage.setItem('orbit_i18n', JSON.stringify({lang:'en',country:'US'})); window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
    time.sleep(1)
    h.js("HUB.degree.open(null); 'ok'")
    rows = 0
    for _ in range(55):
        time.sleep(2)
        rows = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
        if isinstance(rows, int) and rows > 0: break
    print('picker rows:', rows)
    set_val(h, '#degQ', 'East Carolina')
    time.sleep(3)
    opened = h.js("""(()=>{const r=[...document.querySelectorAll('#degResults .deg-planrow')].find(x=>/Nursing/i.test(x.textContent));if(r){r.click();return (r.textContent||'').slice(0,50)}return 'notfound'})()""")
    print('clicked row:', opened)
    notice = ''
    for i in range(45):
        time.sleep(2)
        notice = str(h.js("(document.querySelector('.deg-reqonly-notice')||{}).textContent||''"))
        if notice: break
    print(f'notice after ~{i*2}s:', notice[:120])
    body = str(h.js("(document.querySelector('#degBody')||{}).textContent||''"))
    print('ECU body has Nursing:', 'Nursing' in body, '| fake Semester 1:', 'Semester 1' in body, '| body len:', len(body))
    checks = h.js("document.querySelectorAll('#degBody .deg-check').length")
    print('ECU check buttons (req blocks):', checks)
    h.js("try{HUB.degree.close()}catch(e){}; 'ok'"); time.sleep(1.5)
    # TTU CS
    h.js("HUB.degree.open(null); 'ok'")
    for _ in range(55):
        time.sleep(2)
        r = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
        if isinstance(r, int) and r > 0: break
    set_val(h, '#degQ', 'Texas Tech')
    time.sleep(3)
    opened2 = h.js("""(()=>{const rs=[...document.querySelectorAll('#degResults .deg-planrow')];const r=rs.find(x=>/Computer Science/i.test(x.textContent));if(r){r.click();return (r.textContent||'').slice(0,60)}return 'notfound:'+rs.length})()""")
    print('clicked TTU row:', opened2)
    nchecks = 0
    for i in range(45):
        time.sleep(2)
        nchecks = h.js("document.querySelectorAll('#degBody .deg-check').length")
        if isinstance(nchecks, int) and nchecks > 10: break
    print(f'TTU course check buttons after ~{i*2}s:', nchecks)
    semheads = h.js("(()=>{const b=document.querySelector('#degBody');if(!b)return 'nobody';const hs=[...b.querySelectorAll('h3,h4,[class*=sem]')].slice(0,10).map(e=>e.className+'::'+(e.textContent||'').slice(0,30));return JSON.stringify(hs)})()")
    print('TTU semester headers:', semheads)
    st = h.js("(()=>{const s=HUB.degree._state();return JSON.stringify({active:s.active})})()")
    print('degree state:', st)
    before = h.js("(()=>{const s=HUB.degree._state();const d=(s.progress[s.active]&&s.progress[s.active].done)||{};return Object.keys(d).length})()")
    tog = h.js("(()=>{const c=document.querySelector('#degBody .deg-check');if(!c)return 'nocheck';c.click();return 'toggled'})()")
    time.sleep(1.2)
    after = h.js("(()=>{const s=HUB.degree._state();const d=(s.progress[s.active]&&s.progress[s.active].done)||{};return Object.keys(d).length})()")
    print(f'toggle: {tog} done before={before} after={after}')
    errs = h.errs()
    print('errors:', errs)
finally:
    h.done()
