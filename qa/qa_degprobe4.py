#!/usr/bin/env python3
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def set_val(h, sel, val):
    return h.js(f"""(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));return 'set';}})()""")

h = H(9483, '/tmp/hubqa-degprobe4')
try:
    for _ in range(40):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
    h.setup('dark')
    h.js("localStorage.setItem('orbit_i18n', JSON.stringify({lang:'en',country:'US'})); window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
    time.sleep(1)
    h.js("HUB.degree.open(null); 'ok'")
    for _ in range(55):
        time.sleep(2)
        r = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
        if isinstance(r, int) and r > 0: break
    set_val(h, '#degQ', 'East Carolina')
    time.sleep(3)
    print('click:', h.js("""(()=>{const r=[...document.querySelectorAll('#degResults .deg-planrow')].find(x=>/Nursing/i.test(x.textContent));if(r){r.click();return (r.textContent||'').slice(0,50)}return 'notfound'})()"""))
    found = False
    for i in range(45):
        time.sleep(2)
        found = bool(h.js("!!document.querySelector('.deg-reqonly-notice')"))
        if found: break
    print(f'notice element present after ~{i*2}s:', found)
    print(h.js("""JSON.stringify({
      noticeText: (document.querySelector('.deg-reqonly-notice')||{}).textContent || null,
      reqBlocks: document.querySelectorAll('#degBody .deg-reqonly').length,
      checks: document.querySelectorAll('#degBody .deg-check').length,
      semSections: document.querySelectorAll('#degBody .deg-sem').length,
      active: (()=>{try{return HUB.degree._state().active}catch(e){return 'err'}})()
    })"""))
    print('body head:', str(h.js("(document.querySelector('#degBody')||{}).innerHTML||''"))[:500])
    print('errors:', h.errs())
finally:
    h.done()
