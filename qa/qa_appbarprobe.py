#!/usr/bin/env python3
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

h = H(9493, '/tmp/hubqa-appbar')
try:
    for _ in range(40):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
    h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
    h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
    time.sleep(1)
    # set viewport 390 via CDP
    h.c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(0.8)
    print(h.js("""JSON.stringify({
      iw: window.innerWidth,
      btns: [...document.querySelectorAll('.appbar .iconbtn')].map(b=>({id:b.id||'',cls:(b.className||'').slice(0,28),hidden:b.hidden,left:Math.round(b.getBoundingClientRect().left),right:Math.round(b.getBoundingClientRect().right)})),
      sw: document.documentElement.scrollWidth
    })"""))
    # logout scene structure
    print('logout API:', h.js("JSON.stringify(Object.keys(HUB.logout||{}))"))
finally:
    h.done()
