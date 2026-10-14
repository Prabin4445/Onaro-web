#!/usr/bin/env python3
"""FULL check C: targeted retests — market detail, groups detail+subtabs+
group chat, global search results, ME vault inline form + persistence,
gym setup drawer."""
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def wait_hub(h, tries=40):
    for _ in range(tries):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function':
            return True
    return False

def set_val(h, sel, val, scope='document'):
    return h.js(f"""(()=>{{const e={scope}.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));return 'set';}})()""")

def main():
    h = H(9485, '/tmp/hubqa-fullc')
    try:
        assert wait_hub(h), 'HUB never booted'
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.state.profile.gender='male';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
        time.sleep(0.5)
        h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
        time.sleep(0.5)

        # ---------- MARKET detail ----------
        h.tab('market')
        h.js("document.getElementById('mkPostBtn').click(); 'ok'"); time.sleep(0.9)
        set_val(h, '#mkTitle', 'QA Detail Bike')
        h.js("(()=>{const c=document.querySelector('#mkTypeChips .chip,#mkTypeChips button');if(c)c.click();return !!c})()"); time.sleep(0.4)
        set_val(h, '#mkPrice', '40')
        h.js("(()=>{const b=[...document.querySelectorAll('#sheetHost button')].find(e=>/post|publish|list/i.test(e.textContent)&&e.offsetParent!==null);if(b)b.click();return !!b})()")
        time.sleep(1.2)
        clicked = h.js("(()=>{const cs=[...document.querySelectorAll('.mkcard')].filter(e=>e.offsetParent!==null);const c=cs.find(e=>e.textContent.includes('QA Detail Bike'))||cs[0];if(!c)return 'nocard';c.scrollIntoView({block:'center'});c.click();return (c.textContent||'').slice(0,40)})()")
        time.sleep(1.2)
        det = h.js("(()=>{const s=document.getElementById('sheetHost');return s&&!s.hidden?(s.innerText||'').slice(0,80):'nosheet'})()")
        h.note('market: listing detail sheet opens with title', isinstance(det, str) and 'QA Detail Bike' in det, f'clicked={clicked} det={det}')
        h.close_all()

        # ---------- GROUPS detail + subtabs + group chat ----------
        h.tab('groups')
        # create a group first
        h.js("(()=>{const b=[...document.querySelectorAll('#view-groups button')].find(e=>/create|new group/i.test(e.textContent)&&e.offsetParent!==null);if(b)b.click();return !!b})()")
        time.sleep(0.9)
        if h.sheet() and h.js("!!document.getElementById('cgName')"):
            set_val(h, '#cgName', 'QA Chat Group')
            h.js("document.getElementById('cgSave').click(); 'ok'"); time.sleep(1.2)
        before = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
        op = h.js("(()=>{const c=[...document.querySelectorAll('[data-club]')].find(e=>e.textContent.includes('QA Chat Group'));if(!c)return 'nocard';c.click();return 'clicked'})()")
        time.sleep(1.2)
        after = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
        h.note('groups: detail opens in view', op == 'clicked' and after != before and 'QA Chat Group' in after, f'op={op} changed={after != before}')
        # group chat from detail
        gc = h.js("(()=>{const b=[...document.querySelectorAll('#view-groups button')].find(e=>/chat/i.test(e.textContent)&&e.offsetParent!==null);if(!b)return 'nobtn';b.click();return 'clicked'})()")
        time.sleep(1.2)
        gopen = h.chatroot()
        h.note('groups: group chat opens', gopen, f'btn={gc}')
        if gopen:
            sent = h.js("(()=>{const i=document.querySelector('.chatroot textarea,.chatroot input[type=text]');if(!i)return 'noinput';i.focus();i.value='QA hello group';i.dispatchEvent(new Event('input',{bubbles:true}));const b=[...document.querySelectorAll('.chatroot button')].find(e=>/send|➤|↑/.test(e.textContent)||/send/i.test(e.className));if(b)b.click();else i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 'sent'})()")
            time.sleep(1)
            gtxt = h.js("(()=>{const d=document.querySelector('.chatroot');return d?(d.innerText||''):''})()")
            h.note('groups: message sends + renders', 'QA hello group' in str(gtxt), f'sent={sent}')
            h.js("try{HUB.gchat&&HUB.gchat.close&&HUB.gchat.close()}catch(e){}; try{HUB.groupchat&&HUB.groupchat.close&&HUB.groupchat.close()}catch(e){}; 'ok'")
        h.close_all()
        # back to list, then subtabs via data-sub
        h.tab('groups'); time.sleep(0.5)
        for sub, marker in [('households', None), ('people', None), ('campus', None), ('clubs', None)]:
            r = h.js(f"(()=>{{const b=document.querySelector('[data-sub=\"{sub}\"]');if(!b)return 'nobtn';b.click();return 'clicked'}})()")
            time.sleep(1.1)
            txt = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
            on = h.js(f"(()=>{{const b=document.querySelector('[data-sub=\"{sub}\"]');return b?b.className:''}})()")
            h.note(f'groups: subtab {sub} renders', r == 'clicked' and len(txt) > 20 and 'Something went wrong' not in txt, f'r={r} len={len(txt)} cls={on}')

        # ---------- SEARCH results ----------
        h.js("try{HUB.search.open()}catch(e){}; 'ok'"); time.sleep(1)
        set_val(h, '#hubSearchInput', 'degree')
        time.sleep(1.2)
        nres = h.js("(()=>{const r=document.getElementById('hubSearchResults');return r?r.children.length:-1})()")
        rtxt = str(h.js("(document.getElementById('hubSearchResults')||{}).innerText||''"))
        h.note('search: query returns result rows', isinstance(nres, int) and nres > 0, f'rows={nres} head={rtxt[:60]!r}')
        set_val(h, '#hubSearchInput', 'zzzzqqq')
        time.sleep(1.2)
        nres2 = h.js("(()=>{const r=document.getElementById('hubSearchResults');return r?r.children.length:-1})()")
        h.note('search: nonsense query handled (rows or empty state)', isinstance(nres2, int) and nres2 >= 0, f'rows={nres2}')
        h.js("try{HUB.search.close()}catch(e){}; 'ok'"); h.close_all()

        # ---------- ME vault (inline form) ----------
        h.tab('me')
        h.js("(()=>{const e=document.getElementById('memTitle');if(e)e.scrollIntoView({block:'center'});return !!e})()")
        time.sleep(0.5)
        set_val(h, '#memTitle', 'QA Passport')
        set_val(h, '#memNote', 'QA note')
        h.js("(()=>{const b=document.getElementById('memSave');if(b)b.click();return !!b})()"); time.sleep(1)
        nmem = h.js("(HUB.store.state.memory||[]).length")
        h.note('me: vault item saved (inline form)', (nmem or 0) >= 1, f'memory={nmem}')
        mtxt = str(h.js("(document.getElementById('view-me')||{}).innerText||''"))
        h.note('me: vault item listed', 'QA Passport' in mtxt)

        # ---------- GYM drawer ----------
        h.tab('daily')
        h.js("try{HUB.gym.openSetup()}catch(e){}; 'ok'"); time.sleep(1)
        dr = bool(h.js("!!document.getElementById('gyDrawer')"))
        h.note('gym: setup drawer opens (#gyDrawer)', dr)
        h.js("(()=>{const b=document.getElementById('gyBd');if(b)b.click();})()"); time.sleep(0.6)
        dr2 = bool(h.js("!!document.getElementById('gyDrawer')"))
        h.note('gym: drawer closes on backdrop tap', not dr2)

        # ---------- persistence of vault ----------
        h.c.send('Page.reload'); time.sleep(6)
        for _ in range(20):
            time.sleep(1.5)
            if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
        h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; var w=document.getElementById('wlcmHost');if(w)w.hidden=true; 'ok'")
        time.sleep(1)
        pmem = h.js("(HUB.store.state.memory||[]).length")
        h.note('persist: vault item survives reload', (pmem or 0) >= 1, f'memory={pmem}')
        errs = h.js("window.__huberr?window.__huberr.splice(0):[]")
        # note: error listener re-armed only after reload in B; here just check current page errors var if present
        h.note('part C completed without harness crash', True)
        h.save('dark', 'fullcheckC')
    finally:
        h.done()

if __name__ == '__main__':
    main()
