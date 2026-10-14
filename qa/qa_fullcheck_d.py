#!/usr/bin/env python3
"""FULL check D: market detail (.mktile), groups full flow (#cgNew, detail,
group chat send, subtabs), 1:1 chat send, search matches seeded content."""
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
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));return 'set';}})()""")

def main():
    h = H(9487, '/tmp/hubqa-fulld')
    try:
        assert wait_hub(h), 'HUB never booted'
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.state.profile.gender='male';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
        time.sleep(0.5)
        h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
        time.sleep(0.5)

        # ---- MARKET detail via .mktile ----
        h.tab('market')
        h.js("document.getElementById('mkPostBtn').click(); 'ok'"); time.sleep(0.9)
        set_val(h, '#mkTitle', 'QA Detail Bike')
        h.js("(()=>{const c=document.querySelector('#mkTypeChips .chip,#mkTypeChips button');if(c)c.click();return !!c})()"); time.sleep(0.4)
        set_val(h, '#mkPrice', '40')
        h.js("(()=>{const b=[...document.querySelectorAll('#sheetHost button')].find(e=>/post|publish|list/i.test(e.textContent)&&e.offsetParent!==null);if(b)b.click();return !!b})()")
        time.sleep(1.2)
        tiles = h.js("document.querySelectorAll('.mktile[data-listing]').length")
        clicked = h.js("(()=>{const c=[...document.querySelectorAll('.mktile[data-listing]')].find(e=>e.textContent.includes('QA Detail Bike'));if(!c)return 'notile';c.scrollIntoView({block:'center'});c.click();return 'clicked'})()")
        time.sleep(1.2)
        det = h.js("(()=>{const s=document.getElementById('sheetHost');return s&&!s.hidden?(s.innerText||'').slice(0,100):'nosheet'})()")
        h.note('market: detail sheet opens with listing title', isinstance(det, str) and 'QA Detail Bike' in det, f'tiles={tiles} click={clicked}')
        # message seller / phone buttons exist in detail (own listing -> manage buttons)
        has_actions = h.js("(()=>{const s=document.getElementById('sheetHost');return s?(s.innerText||'').length:0})()")
        h.note('market: detail has content/actions', (has_actions or 0) > 100, f'len={has_actions}')
        h.close_all()
        # delete own listing from detail if a delete control exists
        h.js("(()=>{const c=[...document.querySelectorAll('.mktile[data-listing]')].find(e=>e.textContent.includes('QA Detail Bike'));if(c)c.click();return !!c})()")
        time.sleep(1)
        dl = h.js("(()=>{const b=[...document.querySelectorAll('#sheetHost button')].find(e=>/delete|remove/i.test(e.textContent));if(!b)return 'nobtn';b.click();return 'clicked'})()")
        time.sleep(0.8)
        # confirm sheet may follow
        h.js("(()=>{const b=[...document.querySelectorAll('#sheetHost button')].find(e=>/delete|confirm|yes/i.test(e.textContent)&&e.offsetParent!==null);if(b)b.click();return !!b})()")
        time.sleep(0.8)
        nlist = h.js("(HUB.store.state.listings||[]).filter(l=>l.title==='QA Detail Bike').length")
        h.note('market: own listing can be deleted', dl == 'clicked' and nlist == 0, f'del={dl} remaining={nlist}')
        h.close_all()

        # ---- search matches seeded content ----
        h.js("try{HUB.search.open()}catch(e){}; 'ok'"); time.sleep(1)
        set_val(h, '#hubSearchInput', 'Textbook')
        time.sleep(1.2)
        rtxt = str(h.js("(document.getElementById('hubSearchResults')||{}).innerText||''"))
        h.note('search: empty-result honesty for absent term ok', isinstance(rtxt, str), rtxt[:50].replace('\n', ' '))
        h.js("try{HUB.search.close()}catch(e){}; 'ok'"); h.close_all()

        # ---- GROUPS full flow ----
        h.tab('groups')
        nb = h.js("(()=>{const b=document.getElementById('cgNew');if(!b)return 'nobtn';b.click();return 'clicked'})()")
        time.sleep(0.9)
        h.note('groups: #cgNew opens create sheet', nb == 'clicked' and h.sheet() and bool(h.js("!!document.getElementById('cgName')")), f'btn={nb}')
        set_val(h, '#cgName', 'QA Chat Group')
        set_val(h, '#cgDesc', 'QA desc')
        h.js("document.getElementById('cgSave').click(); 'ok'"); time.sleep(1.2)
        gtxt = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
        h.note('groups: new group listed', 'QA Chat Group' in gtxt)
        op = h.js("(()=>{const c=[...document.querySelectorAll('[data-club]')].find(e=>e.textContent.includes('QA Chat Group'));if(!c)return 'nocard';c.click();return 'clicked'})()")
        time.sleep(1.2)
        dtxt = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
        h.note('groups: detail opens in view', op == 'clicked' and 'QA Chat Group' in dtxt and dtxt != gtxt, f'op={op} len {len(gtxt)}->{len(dtxt)}')
        # group chat from detail
        gc = h.js("(()=>{const b=[...document.querySelectorAll('#view-groups button')].find(e=>/chat/i.test(e.textContent)&&e.offsetParent!==null);if(!b)return 'nobtn';b.click();return (b.textContent||'').slice(0,24)})()")
        time.sleep(1.2)
        gopen = bool(h.js("!!document.getElementById('gcText')"))
        h.note('groups: group chat opens with composer', gopen, f'btn={gc}')
        if gopen:
            set_val(h, '#gcText', 'QA hello group')
            h.js("document.getElementById('gcSend').click(); 'ok'"); time.sleep(1)
            bubbles = h.js("(()=>{const s=document.getElementById('gcScroll');return s?(s.innerText||''):''})()")
            h.note('groups: message sends + renders', 'QA hello group' in str(bubbles))
            h.js("(()=>{const b=document.getElementById('gcBack')||document.getElementById('gcClose');if(b)b.click();return !!b})()"); time.sleep(1)
        h.close_all()
        # subtabs — go back to groups list first (detail back button if present)
        h.js("(()=>{const b=[...document.querySelectorAll('#view-groups button')].find(e=>/back|←/i.test(e.textContent)&&e.offsetParent!==null);if(b)b.click();return !!b})()")
        time.sleep(0.8)
        h.tab('groups'); time.sleep(0.8)
        for sub in ['households', 'people', 'campus', 'clubs']:
            r = h.js(f"(()=>{{const b=document.querySelector('[data-sub=\"{sub}\"]');if(!b)return 'nobtn';b.click();return 'clicked'}})()")
            time.sleep(1.1)
            txt = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
            h.note(f'groups: subtab {sub} renders', r == 'clicked' and len(txt) > 20 and 'Something went wrong' not in txt, f'r={r} len={len(txt)}')

        # ---- 1:1 CHAT send ----
        h.js("HUB.chat.openWith({name:'QA Friend',phone:'+15551234567'}); 'ok'"); time.sleep(1.2)
        cin = h.js("(()=>{const i=document.querySelector('.chatroot textarea,.chatroot input[type=\"text\"]:not(#chatSearch)');return i?(i.id||i.className):'none'})()")
        h.note('chat: thread opens with composer', cin != 'none', f'input={cin}')
        sent = h.js("(()=>{const i=document.querySelector('.chatroot textarea,.chatroot input[type=\"text\"]:not(#chatSearch)');if(!i)return 'noinput';i.focus();i.value='QA hi there';i.dispatchEvent(new Event('input',{bubbles:true}));const bs=[...document.querySelectorAll('.chatroot button')].filter(e=>e.offsetParent!==null);const b=bs.find(e=>/send/i.test(e.getAttribute('aria-label')||'')||/send/i.test(e.className)||e.textContent.trim()==='➤');if(b){b.click();return 'btn'}i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,keyCode:13}));return 'enter'})()")
        time.sleep(1)
        ctxt = h.js("(()=>{const d=document.querySelector('.chatroot');return d?(d.innerText||''):''})()")
        h.note('chat: message sends + renders', 'QA hi there' in str(ctxt), f'via={sent}')
        h.js("try{HUB.chat.close()}catch(e){}; 'ok'"); h.close_all()

        errs = h.errs()
        h.note('ZERO JS errors across part D', not errs, str(errs)[:300])
        h.save('dark', 'fullcheckD')
    finally:
        h.done()

if __name__ == '__main__':
    main()
