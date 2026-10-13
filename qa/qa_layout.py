#!/usr/bin/env python3
"""Layout sweep: at 320/390/402 px widths, every tab must have NO horizontal
overflow (document scrollWidth <= innerWidth) and no visible element may
extend past the right edge. This is the iPhone clipping class of bug."""
import sys, time
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

OVERFLOW_JS = """(function(){
  var iw=window.innerWidth;
  var bad=[];
  function clippedBy(e){
    var p=e.parentElement;
    while(p && p!==document.body){
      var cs=getComputedStyle(p);
      if(cs.overflowX==='hidden'||cs.overflowX==='auto'||cs.overflowX==='scroll'||cs.overflowX==='clip') return true;
      p=p.parentElement;
    }
    return false;
  }
  var els=document.querySelectorAll('body *');
  for(var i=0;i<els.length;i++){
    var e=els[i];
    if(e.offsetParent===null) continue;
    var r=e.getBoundingClientRect();
    if(r.width>0 && r.right>iw+1 && !clippedBy(e)) bad.push(e.tagName+'.'+String(e.className).slice(0,30)+' right='+Math.round(r.right));
    if(bad.length>=5) break;
  }
  return JSON.stringify({sw:document.documentElement.scrollWidth, iw:iw, bad:bad});
})()"""

def main():
    import json as J
    for width in (320, 390, 402):
        h = H(9471, f'/tmp/hubqa-layout{width}')
        try:
            # resize: the harness launches default size; emulate via CDP metrics
            h.c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
            for i in range(40):
                time.sleep(1)
                if h.js("typeof (window.HUB&&HUB.showTab)") == 'function':
                    break
            h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}; try{HUB.auth.close()}catch(e){}; 'ok'")
            time.sleep(1)
            for tab in ('home', 'daily', 'market', 'work', 'groups', 'me'):
                h.js(f"HUB.showTab('{tab}'); 'ok'")
                time.sleep(1.2)
                res = J.loads(h.js(OVERFLOW_JS))
                ok = res['sw'] <= res['iw'] + 1 and not res['bad']
                h.note(f'{width}px tab {tab} no-h-overflow', ok,
                       f"sw={res['sw']} iw={res['iw']} bad={res['bad'][:2]}")
            h.save('dark', f'layout{width}')
        finally:
            h.done()

if __name__ == '__main__':
    main()
