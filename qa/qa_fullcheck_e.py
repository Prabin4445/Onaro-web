#!/usr/bin/env python3
"""FULL check E: 1:1 chat send via #chatText/#chatSend; groups post-save state."""
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
    h = H(9489, '/tmp/hubqa-fulle')
    try:
        assert wait_hub(h), 'HUB never booted'
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
        time.sleep(0.5)
        h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
        time.sleep(0.5)

        # ---- 1:1 chat ----
        h.js("HUB.chat.openWith({name:'QA Friend',phone:'+15551234567'}); 'ok'"); time.sleep(1.2)
        has = bool(h.js("!!document.getElementById('chatText')"))
        h.note('chat: thread opens with composer (#chatText)', has)
        if has:
            set_val(h, '#chatText', 'QA hi there')
            h.js("document.getElementById('chatSend').click(); 'ok'"); time.sleep(1)
            bub = str(h.js("(document.getElementById('chatBubbles')||{}).innerText||''"))
            nmsg = h.js("(()=>{const th=(HUB.store.state.threads||[])[0];return th?(th.messages||[]).length:-1})()")
            h.note('chat: message renders in bubbles', 'QA hi there' in bub, f'bubbles={bub[:60]!r}')
            h.note('chat: message saved to thread store', isinstance(nmsg, int) and nmsg >= 1, f'msgs={nmsg}')
            # reply persistence across reopen
            h.js("try{HUB.chat.close()}catch(e){}; 'ok'"); time.sleep(0.6)
            h.js("try{HUB.chat.openList()}catch(e){}; 'ok'"); time.sleep(1)
            rows = str(h.js("(document.getElementById('chatRows')||{}).innerText||''"))
            h.note('chat: thread listed after reopen', 'QA Friend' in rows, f'rows={rows[:60]!r}')
            h.js("try{HUB.chat.close()}catch(e){}; 'ok'")
        h.close_all()

        # ---- groups: what does the view show right after creating a group? ----
        h.tab('groups')
        h.js("(()=>{const b=document.getElementById('cgNew');if(b)b.click();return !!b})()"); time.sleep(0.9)
        set_val(h, '#cgName', 'QA Probe Group')
        h.js("document.getElementById('cgSave').click(); 'ok'"); time.sleep(1.2)
        state = h.js("""JSON.stringify({
          hasSeg: !!document.querySelector('#view-groups [data-sub]'),
          hasCard: !!document.querySelector('#view-groups [data-club]'),
          hasChatBtn: [...document.querySelectorAll('#view-groups button')].some(b=>/group chat/i.test(b.textContent)),
          buttons: [...document.querySelectorAll('#view-groups button')].slice(0,14).map(b=>(b.textContent||'').trim().slice(0,22))
        })""")
        h.note('groups: post-save view state', True, str(state)[:280])
        st = json.loads(state) if isinstance(state, str) else {}
        h.note('groups: create lands on group page (chat btn, no seg bar)', st.get('hasChatBtn') is True and st.get('hasSeg') is False, str(st)[:160])
        errs = h.errs()
        h.note('ZERO JS errors across part E', not errs, str(errs)[:250])
        h.save('dark', 'fullcheckE')
    finally:
        h.done()

if __name__ == '__main__':
    main()
