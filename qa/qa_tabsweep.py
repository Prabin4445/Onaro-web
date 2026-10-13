#!/usr/bin/env python3
"""Fresh-install sweep: render every tab, assert no error boundary, no JS
errors, and non-trivial content. Catches the seed/migration crash class."""
import sys, time
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

TABS = ['home', 'daily', 'market', 'work', 'groups', 'me']

def main():
    h = H(9467, '/tmp/hubqa-tabsweep')
    try:
        for i in range(40):
            time.sleep(2)
            if h.js("typeof (window.HUB&&HUB.showTab)") == 'function':
                break
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}; 'ok'")
        time.sleep(1)
        h.js("try{HUB.auth.close()}catch(e){}; 'ok'")
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        for tab in TABS:
            h.js(f"HUB.showTab('{tab}'); 'ok'")
            time.sleep(1.6)
            txt = str(h.js(f"(document.getElementById('view-{tab}')||{{}}).innerText||''"))
            h.note(f'tab {tab} renders', 'Something went wrong' not in txt and len(txt) > 30,
                   f'len={len(txt)} head={txt[:60]!r}')
        # key overlays from fresh state
        for name, expr in [
            ('search', "HUB.search.open()"),
            ('chat', "HUB.chat.openList()"),
            ('notifications', "HUB.notifications.open()"),
            ('pulse', "HUB.pulse.open()"),
        ]:
            h.js(f"try{{ {expr}; }}catch(e){{}}; 'ok'")
            time.sleep(1)
            opened = bool(h.js("!!document.querySelector('.chatroot:not([hidden])')"))
            h.note(f'overlay {name} opens', opened, '')
            h.close_all()
        errs = h.errs()
        h.note('zero JS errors across sweep', not errs, str(errs)[:250])
        h.save('dark', 'tabsweep')
    finally:
        h.done()

if __name__ == '__main__':
    main()
