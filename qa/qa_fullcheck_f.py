#!/usr/bin/env python3
"""FULL check F: 1:1 chat full flow — openWith -> safety checklist -> ack ->
thread -> send -> persists."""
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def wait_hub(h, tries=40):
    for _ in range(tries):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function':
            return True
    return False

def set_val(h, sel, val):
    return h.js(f"""(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));return 'set';}})()""")

def main():
    h = H(9491, '/tmp/hubqa-fullf')
    try:
        assert wait_hub(h), 'HUB never booted'
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
        time.sleep(0.5)
        h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
        time.sleep(0.5)

        h.js("HUB.chat.openWith({name:'QA Friend',phone:'+15551234567'}); 'ok'"); time.sleep(1.2)
        h.note('chat: safety checklist sheet appears first', h.sheet())
        ack = h.js("(()=>{const bs=[...document.querySelectorAll('#sheetHost button')].filter(e=>e.offsetParent!==null);const b=bs[bs.length-1];if(!b)return 'nobtn';const t=b.textContent.trim().slice(0,26);b.click();return t})()")
        time.sleep(1.2)
        has = bool(h.js("!!document.getElementById('chatText')"))
        h.note('chat: thread opens after safety ack', has, f'ackBtn={ack}')
        if has:
            set_val(h, '#chatText', 'QA hi there')
            h.js("document.getElementById('chatSend').click(); 'ok'"); time.sleep(1)
            bub = str(h.js("(document.getElementById('chatBubbles')||{}).innerText||''"))
            h.note('chat: message renders in bubbles', 'QA hi there' in bub, f'{bub[:60]!r}')
            msgs = h.js("(()=>{const th=(HUB.store.state.threads||[]).find(t=>(t.messages||[]).some(m=>m.text==='QA hi there'));return th?th.messages.length:-1})()")
            h.note('chat: message saved in thread store', isinstance(msgs, int) and msgs >= 1, f'msgs={msgs}')
            # second message to same contact: no safety sheet again
            h.js("try{HUB.chat.close()}catch(e){}; 'ok'"); time.sleep(0.6)
            h.js("HUB.chat.openWith({name:'QA Friend',phone:'+15551234567'}); 'ok'"); time.sleep(1.2)
            has2 = bool(h.js("!!document.getElementById('chatText')"))
            h.note('chat: second open goes straight to thread (safety ack remembered)', has2)
            h.js("try{HUB.chat.close()}catch(e){}; 'ok'")
        errs = h.errs()
        h.note('ZERO JS errors across part F', not errs, str(errs)[:250])
        h.save('dark', 'fullcheckF')
    finally:
        h.done()

if __name__ == '__main__':
    main()
