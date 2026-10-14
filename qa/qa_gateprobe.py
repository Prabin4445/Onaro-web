#!/usr/bin/env python3
import sys, time
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

h = H(9473, '/tmp/hubqa-gateprobe')
try:
    for i in range(14):
        time.sleep(2)
        st = h.js("""JSON.stringify({
          wlcm: !!document.getElementById('wlcmHost') && !document.getElementById('wlcmHost').hidden,
          authRoot: !!document.getElementById('authRoot'),
          authHidden: document.getElementById('authRoot') ? document.getElementById('authRoot').hidden : null,
          aSkip: !!document.getElementById('aSkip'),
          aClose: !!document.getElementById('aClose'),
          splash: !!document.getElementById('splash'),
          splashOut: document.getElementById('splash') ? document.getElementById('splash').className : null,
          sheetHidden: document.getElementById('sheetHost') ? document.getElementById('sheetHost').hidden : null,
          user: (()=>{try{return !!HUB.auth.currentUser()}catch(e){return 'na'}})()
        })""")
        print(f't+{(i+1)*2}s', st)
        if isinstance(st, str) and '"aSkip":true' in st:
            break
finally:
    h.done()
