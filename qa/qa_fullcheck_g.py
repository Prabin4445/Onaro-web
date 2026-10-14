#!/usr/bin/env python3
"""FULL check G: home weather widget + degree Track -> home progress card."""
import sys, time, json, re
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def set_val(h, sel, val):
    return h.js(f"""(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));return 'set';}})()""")

h = H(9497, '/tmp/hubqa-fullg')
try:
    for _ in range(40):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
    h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
    h.setup('dark')
    h.js("localStorage.setItem('orbit_i18n', JSON.stringify({lang:'en',country:'US'})); window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
    time.sleep(1)
    h.tab('home')
    home = str(h.js("(document.getElementById('view-home')||{}).innerText||''"))
    has_temp = bool(re.search(r'\d+\s*°', home))
    h.note('home: weather widget shows a temperature', has_temp, [m for m in re.findall(r'.{0,18}\d+\s*°.{0,10}', home)][:2])
    prog_before = h.js("(()=>{const c=document.querySelector('#view-home');return c?(c.innerText.match(/Degree progress[\\s\\S]{0,120}/)||[''])[0]:''})()")
    print('progress card before:', str(prog_before)[:120].replace('\n', ' '))
    # open TTU CS and track it
    h.js("HUB.degree.open(null); 'ok'")
    for _ in range(55):
        time.sleep(2)
        r = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
        if isinstance(r, int) and r > 0: break
    set_val(h, '#degQ', 'Texas Tech')
    time.sleep(3)
    h.js("""(()=>{const rs=[...document.querySelectorAll('#degResults .deg-planrow')];const r=rs.find(x=>/Computer Science/i.test(x.textContent));if(r)r.click();return !!r})()""")
    tracked = False
    for i in range(45):
        time.sleep(2)
        b = h.js("(()=>{const b=document.getElementById('degTrack');return b?b.textContent.trim():'notyet'})()")
        if b == 'notyet': continue
        h.js("document.getElementById('degTrack').click(); 'ok'")
        tracked = True
        break
    time.sleep(1)
    act = h.js("(()=>{try{return HUB.degree._state().active}catch(e){return null}})()")
    h.note('degree: Track this plan sets active plan', bool(tracked and act), f'active={act}')
    h.js("try{HUB.degree.close()}catch(e){}; 'ok'")
    h.tab('home'); time.sleep(1.5)
    home2 = str(h.js("(document.getElementById('view-home')||{}).innerText||''"))
    h.note('home: progress card shows tracked plan', 'Computer Science' in home2 or 'Texas Tech' in home2,
           [ln for ln in home2.split('\n') if 'Computer' in ln or 'Texas' in ln][:2])
    errs = h.errs()
    h.note('ZERO JS errors across part G', not errs, str(errs)[:250])
    h.save('dark', 'fullcheckG')
finally:
    h.done()
