#!/usr/bin/env python3
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

h = H(9495, '/tmp/hubqa-logoutplay')
try:
    for _ in range(40):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
    h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
    h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.state.profile.gender='male';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
    h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
    # seed a local signed-in session (same seam qa_logout.py uses)
    h.js("""var st=HUB.store.state; st.auth=st.auth||{users:[],session:null};
      st.auth.users=[{id:'qa-lo1',name:'QA Logout',email:'qa@example.com',phoneE164:'+15551234567',cc:'US',pw:'x',salt:'x',campus:'QA Campus',verifiedVia:'email',faceId:null,createdAt:Date.now()}];
      st.auth.session={uid:'qa-lo1',at:Date.now(),remember:true};
      HUB.store.save(); HUB.auth.restore(); window.__gateSkip=true; try{HUB.auth.close()}catch(e){};
      'signedin='+(!!HUB.auth.currentUser())""")
    time.sleep(0.8)
    print('signed in:', h.js("!!HUB.auth.currentUser()"))
    h.js("HUB.logout.play(); 'ok'")
    for t in (0.4, 1.6, 3.2):
        time.sleep(t if t == 0.4 else (1.2 if t == 1.6 else 1.6))
        print(f't~{t}s:', h.js("""JSON.stringify({
          strip: !!document.querySelector('.lo-strip'),
          man: (()=>{const m=document.querySelector('.lo-man');if(!m)return null;const r=m.getBoundingClientRect();return {left:Math.round(r.left),tf:getComputedStyle(m).transform.slice(0,40)}})(),
          door: (()=>{const d=document.querySelector('.lo-door');return d?getComputedStyle(d).transform.slice(0,40):null})(),
          glow: (()=>{const g=document.querySelector('.lo-glow');return g?getComputedStyle(g).opacity:null})()
        })"""))
    # wait for completion: strip removes itself and login gate appears
    done = False
    for _ in range(14):
        time.sleep(1)
        done = bool(h.js("!document.querySelector('.lo-strip')"))
        if done: break
    print('strip removed after logout:', done)
    print('errors:', h.errs())
finally:
    h.done()
