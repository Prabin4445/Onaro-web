#!/usr/bin/env python3
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def set_val(h, sel, val):
    return h.js(f"""(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));return 'set';}})()""")

h = H(9481, '/tmp/hubqa-degprobe3')
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
    set_val(h, '#degQ', 'Texas Tech')
    time.sleep(3)
    print('click:', h.js("""(()=>{const rs=[...document.querySelectorAll('#degResults .deg-planrow')];const r=rs.find(x=>/Computer Science/i.test(x.textContent));if(r){r.click();return (r.textContent||'').slice(0,50)}return 'notfound'})()"""))
    for i in range(40):
        time.sleep(2)
        n = h.js("document.querySelectorAll('#degBody .deg-sem').length")
        if isinstance(n, int) and n > 0: break
    print(f'sem sections after ~{i*2}s:', n)
    print(h.js("""JSON.stringify({
      tiles: document.querySelectorAll('#degBody .deg-tile').length,
      checksInBody: document.querySelectorAll('#degBody .deg-check').length,
      checksAnywhere: document.querySelectorAll('.deg-check').length,
      tilesAnywhere: document.querySelectorAll('.deg-tile').length,
      bodyLen: (document.querySelector('#degBody')||{}).innerHTML ? document.querySelector('#degBody').innerHTML.length : -1,
      notice: (document.querySelector('.deg-reqonly-notice')||{}).textContent || null,
      active: (()=>{try{return HUB.degree._state().active}catch(e){return 'err'}})()
    })"""))
    print('body head:', str(h.js("(document.querySelector('#degBody')||{}).innerHTML||''"))[:400])
    # expand first semester if collapsed, then click first check
    print('expand:', h.js("(()=>{const b=document.querySelector('#degBody [data-semtgl]');if(b){b.click();return 'clicked'}return 'none'})()"))
    time.sleep(1)
    print('checks after expand:', h.js("document.querySelectorAll('#degBody .deg-check').length"))
    before = h.js("(()=>{const s=HUB.degree._state();const d=(s.progress[s.active]&&s.progress[s.active].done)||{};return Object.keys(d).length})()")
    print('toggle:', h.js("(()=>{const c=document.querySelector('#degBody .deg-check');if(!c)return 'nocheck';c.click();return 'toggled'})()"))
    time.sleep(1.2)
    after = h.js("(()=>{const s=HUB.degree._state();const d=(s.progress[s.active]&&s.progress[s.active].done)||{};return Object.keys(d).length})()")
    print(f'done before={before} after={after}')
    print('errors:', h.errs())
finally:
    h.done()
