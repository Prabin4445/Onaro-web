#!/usr/bin/env python3
"""FULL functional check B: market, work, groups, chat, create, search,
notifications, pulse, ask, ME (edit/skills/vault/language/country/reset),
persistence across reload, i18n locales."""
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

def click_text(h, txt, scope='document'):
    return h.js(f"""(()=>{{const els=[...{scope}.querySelectorAll('button,[role=button],a,.btn,.chip')].filter(e=>e.offsetParent!==null);
      const b=els.find(e=>e.textContent.trim().includes({json.dumps(txt)}));if(!b)return 'notfound';b.click();return 'clicked';}})()""")

def main():
    h = H(9479, '/tmp/hubqa-fullb')
    try:
        assert wait_hub(h), 'HUB never booted'
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.state.profile.gender='male';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
        time.sleep(0.5)
        h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
        time.sleep(0.5)

        # ---------- MARKET ----------
        h.tab('market')
        h.js("document.getElementById('mkPostBtn').click(); 'ok'"); time.sleep(0.9)
        h.note('market: post form opens', h.sheet())
        set_val(h, '#mkTitle', 'QA Textbook Calculus')
        # choose a type chip so price field shows (first chip in #mkTypeChips)
        h.js("(()=>{const c=document.querySelector('#mkTypeChips .chip,#mkTypeChips button');if(c)c.click();return !!c})()")
        time.sleep(0.4)
        set_val(h, '#mkPrice', '25')
        set_val(h, '#mkDesc', 'QA listing description')
        r = h.js("(()=>{const b=[...document.querySelectorAll('#sheetHost button')].find(e=>/post|publish|list/i.test(e.textContent)&&e.offsetParent!==null);if(b){b.click();return b.textContent.trim().slice(0,30)}return 'nobtn'})()")
        time.sleep(1)
        nlist = h.js("(HUB.store.state.listings||[]).length")
        h.note('market: listing saved to store', (nlist or 0) >= 1, f'listings={nlist} btn={r}')
        grid = str(h.js("(document.getElementById('view-market')||{}).innerText||''"))
        h.note('market: listing shows in grid', 'QA Textbook' in grid)
        # open detail
        h.js("(()=>{const c=document.querySelector('.mkcard');if(c)c.click();return !!c})()"); time.sleep(0.9)
        h.note('market: listing detail opens', h.sheet())
        h.close_all()
        # search filter
        set_val(h, '#mkSearch', 'Textbook')
        time.sleep(0.8)
        grid2 = str(h.js("(document.getElementById('view-market')||{}).innerText||''"))
        h.note('market: search filter finds listing', 'QA Textbook' in grid2)
        set_val(h, '#mkSearch', 'zzzznothing')
        time.sleep(0.8)
        grid3 = str(h.js("(document.getElementById('view-market')||{}).innerText||''"))
        h.note('market: search no-match hides listing', 'QA Textbook' not in grid3)
        set_val(h, '#mkSearch', '')

        # ---------- WORK ----------
        h.tab('work')
        h.js("document.getElementById('postJobBtn').click(); 'ok'"); time.sleep(0.9)
        h.note('work: post form opens', h.sheet())
        set_val(h, '#pjTitle', 'QA Lawn help')
        set_val(h, '#pjPay', '20')
        set_val(h, '#pjDesc', 'QA job description')
        h.js("document.getElementById('pjGo').click(); 'ok'"); time.sleep(1)
        njobs = h.js("(HUB.store.state.jobs||[]).length")
        h.note('work: job saved to store', (njobs or 0) >= 1, f'jobs={njobs}')
        wtxt = str(h.js("(document.getElementById('view-work')||{}).innerText||''"))
        h.note('work: job shows in list', 'QA Lawn help' in wtxt)
        h.close_all()

        # ---------- GROUPS ----------
        h.tab('groups')
        r = click_text(h, 'Create group')
        if r == 'notfound': r = click_text(h, 'New group')
        if r == 'notfound': r = click_text(h, '+')
        time.sleep(0.9)
        h.note('groups: create sheet opens', h.sheet(), f'btn={r}')
        if h.sheet():
            set_val(h, '#cgName', 'QA Study Group')
            set_val(h, '#cgDesc', 'QA group description')
            h.js("document.getElementById('cgSave').click(); 'ok'"); time.sleep(1)
        ngrp = h.js("(()=>{const s=HUB.store.state;const g=s.groups||s.cgroups||[];return g.length})()")
        gtxt = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
        h.note('groups: group created + listed', 'QA Study Group' in gtxt, f'storeGroups={ngrp}')
        # open group detail
        h.js("(()=>{const c=[...document.querySelectorAll('.gcard')].find(e=>e.textContent.includes('QA Study Group'));if(c)c.click();return !!c})()")
        time.sleep(1)
        h.note('groups: detail opens', h.sheet() or h.chatroot())
        h.close_all()
        # people tab
        r = click_text(h, 'People', "document.getElementById('view-groups')")
        time.sleep(0.9)
        ptxt = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
        h.note('groups: people tab renders', len(ptxt) > 30, f'btn={r} len={len(ptxt)}')
        # households tab
        r = click_text(h, 'Households', "document.getElementById('view-groups')")
        time.sleep(0.9)
        htxt = str(h.js("(document.getElementById('view-groups')||{}).innerText||''"))
        h.note('groups: households tab renders', len(htxt) > 20, f'btn={r} len={len(htxt)}')

        # ---------- CHAT ----------
        h.js("try{HUB.chat.openList()}catch(e){}; 'ok'"); time.sleep(1.2)
        h.note('chat: list opens', h.chatroot())
        h.js("try{HUB.chat.close()}catch(e){}; 'ok'"); h.close_all()

        # ---------- CREATE FAB ----------
        h.js("try{HUB.create.open()}catch(e){}; 'ok'"); time.sleep(0.9)
        ctxt = h.js("(()=>{const s=document.getElementById('sheetHost');return s?(s.innerText||'').length:0})()")
        h.note('create: FAB sheet opens with options', h.sheet() and (ctxt or 0) > 20, f'len={ctxt}')
        h.close_all()

        # ---------- SEARCH ----------
        h.js("try{HUB.search.open()}catch(e){}; 'ok'"); time.sleep(1)
        h.note('search: overlay opens', h.chatroot())
        inp = h.js("(()=>{const i=document.querySelector('.chatroot input');return i?i.id||i.className:'none'})()")
        h.js("(()=>{const i=document.querySelector('.chatroot input');if(i){i.focus();i.value='degree';i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true}));}return !!i})()")
        time.sleep(1.5)
        stxt = h.js("(()=>{const d=document.querySelector('.chatroot');return d?(d.innerText||'').length:0})()")
        h.note('search: typing returns results', (stxt or 0) > 60, f'input={inp} len={stxt}')
        h.js("try{HUB.search.close()}catch(e){}; 'ok'"); h.close_all()

        # ---------- NOTIFICATIONS ----------
        h.js("try{HUB.notifications.open()}catch(e){}; 'ok'"); time.sleep(1)
        h.note('notifications: overlay opens', h.chatroot())
        h.js("try{HUB.notifications.close()}catch(e){}; 'ok'"); h.close_all()

        # ---------- PULSE ----------
        h.js("try{HUB.pulse.open()}catch(e){}; 'ok'"); time.sleep(1)
        h.note('pulse: overlay opens', h.chatroot())
        h.js("try{HUB.pulse.close()}catch(e){}; 'ok'"); h.close_all()

        # ---------- ASK ONARO ----------
        h.js("(()=>{const b=document.getElementById('askPillMain');if(b)b.click();return !!b})()"); time.sleep(1)
        h.note('ask: sheet opens', h.sheet())
        set_val(h, '#askSheetInput', 'How do I see my degree plan?')
        h.js("(()=>{const b=document.getElementById('askSheetSend');if(b)b.click();return !!b})()")
        time.sleep(2.5)
        ares = h.js("(()=>{const r=document.getElementById('askSheetResults');return r?(r.innerText||'').length:0})()")
        h.note('ask: answer card appears', (ares or 0) > 20, f'len={ares}')
        h.close_all()

        # ---------- ME ----------
        h.tab('me')
        # add skill inline
        set_val(h, '#meSkillInput', 'QA Welding')
        h.js("(()=>{const b=document.getElementById('meSkillAdd');if(b)b.click();return !!b})()"); time.sleep(0.8)
        skills = h.js("JSON.stringify(HUB.store.state.profile.skills||[])")
        h.note('me: skill added', 'QA Welding' in str(skills), f'skills={skills}')
        # delete skill
        h.js("(()=>{const b=document.querySelector('[data-skill]');if(b)b.click();return !!b})()"); time.sleep(0.8)
        skills2 = h.js("JSON.stringify(HUB.store.state.profile.skills||[])")
        h.note('me: skill deleted', 'QA Welding' not in str(skills2), f'skills={skills2}')
        # edit profile: change name
        h.js("(()=>{const b=document.getElementById('meEditBtn');if(b)b.click();return !!b})()"); time.sleep(0.9)
        h.note('me: edit sheet opens', h.sheet())
        nm = h.js("(()=>{const i=document.querySelector('#sheetHost input');return i?i.id||i.className:'none'})()")
        h.js("(()=>{const inputs=[...document.querySelectorAll('#sheetHost input')];const n=inputs.find(i=>/name/i.test(i.id||'')||/name/i.test(i.name||''))||inputs[0];if(n){n.focus();n.value='PraBin QA';n.dispatchEvent(new Event('input',{bubbles:true}));}return !!n})()")
        r = h.js("(()=>{const b=[...document.querySelectorAll('#sheetHost button')].find(e=>/save/i.test(e.textContent)&&e.offsetParent!==null);if(b){b.click();return b.textContent.trim().slice(0,24)}return 'nobtn'})()")
        time.sleep(0.9)
        pname = h.js("HUB.store.state.profile.name")
        h.note('me: profile name saved', pname == 'PraBin QA', f'name={pname} firstInput={nm} btn={r}')
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.save()}catch(e){}; 'ok'")
        h.close_all()
        # vault add
        r = click_text(h, 'MEMORY', "document.getElementById('view-me')")
        if r == 'notfound': r = click_text(h, 'Vault', "document.getElementById('view-me')")
        if r == 'notfound': r = click_text(h, 'Add', "document.getElementById('view-me')")
        time.sleep(0.9)
        if h.sheet() and h.js("!!document.getElementById('memTitle')"):
            set_val(h, '#memTitle', 'QA ID card')
            h.js("document.getElementById('memSave').click(); 'ok'"); time.sleep(0.9)
            nmem = h.js("(HUB.store.state.memory||[]).length")
            h.note('me: vault item saved', (nmem or 0) >= 1, f'memory={nmem}')
        else:
            h.note('me: vault sheet opens', False, f'btn={r} sheet={h.sheet()}')
        h.close_all()
        # language switch to Spanish via i18n (same call the picker makes)
        h.js("HUB.i18n.setLang('es'); 'ok'")
        ok_es = False
        for _ in range(10):
            time.sleep(1)
            ok_es = bool(h.js("(()=>{try{return HUB.i18n._dict('es')!==HUB.i18n._dict('en')&&HUB.i18n.t('tabs.home')!==HUB.i18n._dict('en')['tabs.home']}catch(e){return false}})()"))
            if ok_es: break
        h.note('i18n: Spanish locale really loads + differs', ok_es)
        h.js("HUB.i18n.setLang('en'); 'ok'"); time.sleep(1.5)
        # language picker UI opens from ME
        h.js("(()=>{const b=document.getElementById('meLangBtn');if(b)b.click();return !!b})()"); time.sleep(0.9)
        h.note('me: language picker opens', h.sheet() or h.chatroot())
        h.close_all()
        # country picker via campus button
        h.js("(()=>{const b=document.getElementById('meCampusBtn');if(b)b.click();return !!b})()"); time.sleep(0.9)
        h.note('me: community/campus picker opens', h.sheet())
        h.close_all()
        # reset-all asks for confirmation (stub confirm, cancel path)
        h.js("window.__confirmAsked=false;window.confirm=()=>{window.__confirmAsked=true;return false}; 'ok'")
        r = click_text(h, 'Reset all', "document.getElementById('view-me')")
        if r == 'notfound': r = click_text(h, 'Reset', "document.getElementById('view-me')")
        time.sleep(0.8)
        asked = h.js("window.__confirmAsked")
        kept = h.js("(HUB.store.state.listings||[]).length")
        h.note('me: reset asks confirm + cancel keeps data', asked is True and (kept or 0) >= 1, f'btn={r} asked={asked} listings={kept}')
        h.js("delete window.confirm; 'ok'")

        # ---------- PERSISTENCE ----------
        h.c.send('Page.reload'); time.sleep(6)
        for _ in range(20):
            time.sleep(1.5)
            if h.js("typeof (window.HUB&&HUB.showTab)") == 'function': break
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        h.js("window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; var w=document.getElementById('wlcmHost');if(w)w.hidden=true; 'ok'")
        time.sleep(1)
        p_name = h.js("HUB.store.state.profile.name")
        p_list = h.js("(HUB.store.state.listings||[]).length")
        p_jobs = h.js("(HUB.store.state.jobs||[]).length")
        p_grp = h.js("(()=>{const s=HUB.store.state;return ((s.groups||s.cgroups||[]).length)})()")
        p_mem = h.js("(HUB.store.state.memory||[]).length")
        h.note('persist: profile name survives reload', p_name == 'PraBin', f'name={p_name}')
        h.note('persist: listing survives reload', (p_list or 0) >= 1, f'listings={p_list}')
        h.note('persist: job survives reload', (p_jobs or 0) >= 1, f'jobs={p_jobs}')
        h.note('persist: group survives reload', (p_grp or 0) >= 1 or 'QA Study Group' in str(h.js("(()=>{try{HUB.showTab('groups')}catch(e){}; return ''})()") or ''), f'groups={p_grp}')
        h.note('persist: vault item survives reload', (p_mem or 0) >= 1, f'memory={p_mem}')
        errs = h.errs()
        h.note('ZERO JS errors across part B', not errs, str(errs)[:300])
        h.save('dark', 'fullcheckB')
    finally:
        h.done()

if __name__ == '__main__':
    main()
