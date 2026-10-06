#!/usr/bin/env python3
"""HUB QA v4b (LIGHT or DARK): Glance, Groups, Me, Gym reset, Global, Astro, i18n, Persistence."""
import sys, time
sys.path.insert(0,'/home/hatch/workspace/hub/qa')
from cdp_h import H
theme=sys.argv[1] if len(sys.argv)>1 else 'light'
port=9785 if theme=='light' else 9787
h=H(port,f'/tmp/hubqa-4b-{theme}')
try:
    h.setup(theme)
    # ---------- GLANCE ----------
    print('== GLANCE =='); h.tab('home')
    tiles=h.js("(()=>[...document.querySelectorAll('#view-home .gltile')].map(e=>e.textContent.trim().replace(/\\n/g,' ').slice(0,40)))()")
    print('tiles:',h.clean(str(tiles))[:300])
    for key in ['Bill','Unread','Jobs','events','Docs','Spending']:
        r=h.js(f"(()=>{{const t=[...document.querySelectorAll('#view-home .gltile')].find(e=>e.textContent.includes('{key}'));if(!t)return 'none';t.click();return 'clicked';}})()")
        time.sleep(1.5)
        opened=h.sheet() or h.chatroot()
        h.note(f'glance: {key} tile opens detail',bool(opened) or r=='none',f'click={r}',sev='broken')
        h.close_all(); h.tab('home')
    # ---------- GROUPS ----------
    print('== GROUPS =='); h.tab('groups'); time.sleep(1)
    r=h.vcs('#cgNew'); time.sleep(1.5)
    if h.sheet():
        h.js("(()=>{const n=document.getElementById('cgName');if(n)n.value='QA Runners v4';const d=document.getElementById('cgDesc');if(d)d.value='QA group, will delete.';const sv=[...document.querySelectorAll('#sheetHost button')].find(b=>/^(create|save)/i.test(b.textContent.trim()));if(sv)sv.click();return 'saved';})()")
        time.sleep(2.5)
        onpage='Back to groups' in str(h.js("document.body.innerText"))
        h.note('groups: created + on page',bool(onpage),'',sev='broken')
        # make live via #cgLive
        r2=h.vcs('#cgLive'); time.sleep(1.8)
        live=h.js("(()=>{const g=(HUB.store.state.cgroups||[]).find(g=>g.name==='QA Runners v4');return g?!!g.live:'nogroup';})()")
        h.note('groups: Make live publishes',live is True,f'click={r2} live={live}',sev='broken')
        h.shot(f'audit-missing-group-live-{theme}')
        # invite -> share sheet
        r3=h.vcs('#cgInviteBtn'); time.sleep(1.5)
        inv=h.js("document.getElementById('sheetHost').innerText")
        haslink='http' in str(inv) or 'join=' in str(inv) or 'copy' in str(inv).lower()
        h.note('groups: invite opens share sheet',h.sheet() and haslink,str(inv)[:70],sev='broken',shot=h.shot(f'audit-missing-group-invite-{theme}') if not (h.sheet() and haslink) else None)
        h.close_all()
        # chat as member
        r4=h.vcs('#cgChatBtn'); time.sleep(1.8)
        gc=bool(h.js("document.getElementById('gcText')"))
        h.note('groups: member chat opens',gc,f'click={r4}',sev='broken',shot=h.shot(f'audit-missing-groupchat-{theme}') if not gc else None)
        if gc:
            h.js("(()=>{const t=document.getElementById('gcText');if(t)t.value='QA hello group';const s=document.getElementById('gcSend');if(s)s.click();return 'sent';})()")
            time.sleep(1.8)
            sent=h.js("(()=>{const p=document.querySelector('.chatroot');return p&&p.innerText.includes('QA hello group');})()")
            h.note('groups: group chat message sent+rendered',bool(sent),'',sev='broken')
            h.shot(f'audit-missing-groupchat-open-{theme}')
        h.close_all()
        # call button (HUB.call expected missing)
        hascall=bool(h.js("typeof HUB!=='undefined'&&!!HUB.call"))
        r5=h.vcs('#cgCallBtn'); time.sleep(1.5)
        h.close_all()
        h.note('groups: call button without HUB.call',hascall,f'HUB.call exists={hascall} click={r5}',sev='broken' if not hascall else None,shot=h.shot(f'audit-missing-groupcall-{theme}') if not hascall else None)
        h.close_all()
    else:
        h.note('groups: create form opens',False,'New button did not open form',sev='broken')
    # back to groups list, request-to-join on a live sample group
    h.js("(()=>{const b=document.getElementById('cgBack');if(b)b.click();})()"); time.sleep(1.5)
    h.js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"clubs\"]');if(b)b.click();})()"); time.sleep(1.5)
    r=h.js("(()=>{const cd=[...document.querySelectorAll('#view-groups [data-club]')].find(e=>e.textContent.includes('Sample'));if(!cd)return 'none';cd.scrollIntoView({block:'center'});cd.click();return 'clicked';})()")
    time.sleep(2)
    member=bool(h.js("document.getElementById('cgChatBtn')"))
    if not member:
        r2=h.vcs('#cgReq'); time.sleep(1.8)
        req=h.js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>/request/i.test(x.textContent));return b?(b.disabled?'requested-disabled':b.textContent.trim().slice(0,20)):'none';})()")
        h.note('groups: request-to-join works',r2=='clicked' or req=='requested-disabled',f'click={r2} state={req}',sev='broken')
        h.shot(f'audit-missing-groupreq-{theme}')
    else:
        h.note('groups: request-to-join (already member)',True,'sample group had me as member; join flow untestable here',sev=None)
    h.js("(()=>{const b=document.getElementById('cgBack');if(b)b.click();})()"); time.sleep(1.2)
    # households sub-tab
    h.js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"households\"]');if(b)b.click();})()"); time.sleep(1.8)
    nc=h.js("document.querySelectorAll('#view-groups .hh-card').length")
    h.note('groups: households sub-tab shows cards',nc and nc>0,f'cards={nc}',sev='broken',shot=h.shot(f'audit-missing-households-{theme}') if not (nc and nc>0) else None)
    # people sub-tab: sync fallback
    h.js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"people\"]');if(b)b.click();})()"); time.sleep(1.5)
    h.js("document.getElementById('toastHost').innerHTML=''")
    r=h.vcs('#pplSyncBtn'); time.sleep(1.8)
    fb=bool(h.js("document.getElementById('frName')"))
    h.note('groups: sync contacts fallback sheet',bool(fb),f'click={r}',sev='broken',shot=h.shot(f'audit-missing-sync-{theme}') if not fb else None)
    h.close_all()
    # person profile: verified badge + message gate
    r=h.js("(()=>{const cd=[...document.querySelectorAll('#view-groups [data-person]')].find(e=>e.textContent.includes('Sample'));if(!cd)return 'none';cd.scrollIntoView({block:'center'});cd.click();return 'clicked';})()")
    time.sleep(1.8)
    body=str(h.js("document.body.innerText"))
    vb='✓' in body and 'Verified' in body
    h.note('groups: sample person shows Verified badge',vb,'badge present' if vb else 'no badge',sev='honest-label' if vb else None,shot=h.shot(f'audit-missing-verified-{theme}') if vb else None)
    r2=h.vct('Message'); time.sleep(1.5)
    gate='mutual' in str(h.js("document.getElementById('sheetHost').innerText")).lower() or h.chatroot()
    h.note('groups: message non-mutual -> mutual gate',bool(gate),f'click={r2}',sev='broken' if not gate else None)
    h.close_all()
    # ---------- ME ----------
    print('== ME =='); h.tab('me'); time.sleep(1)
    h.shot(f'audit-missing-me-{theme}')
    # profile edit
    r=h.vcs('#meEditBtn'); time.sleep(1.5)
    if h.sheet():
        h.js("(()=>{const n=document.getElementById('peditName');if(n)n.value='PraBin QA';const sv=document.getElementById('peditSave');if(sv)sv.click();return 'saved';})()")
        time.sleep(1.8)
        ok=h.js("HUB.store.state.profile.name")== 'PraBin QA'
        h.note('me: profile name edits+saves',bool(ok),'',sev='broken')
        h.close_all()
    else:
        h.note('me: edit profile opens',False,'edit button did not open form',sev='broken')
    # vault: inline form add + delete (confirm check)
    h.js("(()=>{const n=document.getElementById('memNote');if(n){n.value='QA memory note';}const sv=document.getElementById('memSave');if(sv){sv.scrollIntoView({block:'center'});sv.click();return 'clicked';}return 'missing';})()")
    time.sleep(1.8)
    added=h.js("(HUB.store.state.memories||[]).some(m=>m.note==='QA memory note')")
    h.note('me: vault note adds',bool(added),'',sev='broken')
    if added:
        before=h.js("(HUB.store.state.memories||[]).length")
        h.js("(()=>{const d=[...document.querySelectorAll('#view-me .memDel')];if(d.length){d[d.length-1].click();return 'clicked';}return 'none';})()")
        time.sleep(1.8)
        after=h.js("(HUB.store.state.memories||[]).length")
        if after<before:
            h.note('me: vault delete asks confirm',False,'memory deleted immediately with no confirmation (toast only)',sev='missing-UX',shot=h.shot(f'audit-missing-vaultdel-{theme}'))
        else:
            h.note('me: vault delete asks confirm',h.sheet(),f'before={before} after={after}',sev='missing-UX')
        h.close_all()
    # skills: inline add + remove (confirm check)
    h.js("(()=>{const i=document.getElementById('meSkillInput');if(i)i.value='QA Skill';const b=document.getElementById('meSkillAdd');if(b){b.click();return 'clicked';}return 'missing';})()")
    time.sleep(1.8)
    before=h.js("(HUB.store.state.profile.skills||[]).length")
    h.js("(()=>{const d=[...document.querySelectorAll('#view-me [data-skill]')];if(d.length){d[d.length-1].click();return 'clicked';}return 'none';})()")
    time.sleep(1.8)
    after=h.js("(HUB.store.state.profile.skills||[]).length")
    if after<before:
        h.note('me: skill remove asks confirm',False,'skill removed immediately with no confirmation',sev='missing-UX',shot=h.shot(f'audit-missing-skilldel-{theme}'))
    else:
        h.note('me: skill remove asks confirm',h.sheet(),f'before={before} after={after}',sev='missing-UX')
    h.close_all()
    # safety score demo label
    ss=str(h.js("document.getElementById('view-me').innerText"))
    h.note('me: safety score labeled demo','demo' in ss.lower(),'',sev='honest-label' if 'demo' not in ss.lower() else None)
    # ---------- GYM RESET ----------
    print('== GYM =='); h.tab('daily'); time.sleep(1)
    h.js("HUB.store.state.gym={sex:'m',age:25,ft:5,inch:10,lb:180,act:'mod',goal:'maintain',unit:'imp',plan:{cal:2400},progress:[]};HUB.store.save();HUB.showTab('daily');")
    time.sleep(1.8)
    has=h.js("!!document.getElementById('gyReset')")
    r=h.vcs('#gyReset') if has else 'missing'
    time.sleep(1.5)
    conf=bool(h.js("document.getElementById('gyResetGo')"))
    h.note('gym: reset asks in-app confirm',bool(conf),f'btn={r} confirm={conf}',sev='missing-UX',shot=h.shot(f'audit-missing-gymreset-{theme}') if not conf else None)
    if conf:
        h.shot(f'audit-missing-gymreset-sheet-{theme}')
        h.vcs('#gyResetNo'); time.sleep(1.2)
        intact=bool(h.js("HUB.store.state.gym&&HUB.store.state.gym.plan"))
        h.note('gym: reset cancel keeps plan',intact,'',sev='broken')
        h.vcs('#gyReset'); time.sleep(1.2)
        h.vcs('#gyResetGo'); time.sleep(1.8)
        cleared=not h.js("HUB.store.state.gym&&HUB.store.state.gym.plan")
        h.note('gym: reset confirm clears plan',bool(cleared),'',sev='broken')
    h.close_all()
    # ---------- GLOBAL ----------
    print('== GLOBAL =='); h.tab('home')
    for bid,mod in [('#searchBtn','search'),('#pulseBtn','pulse'),('#notifBtn','notifications')]:
        r=h.vcs(bid); time.sleep(1.5)
        ov=h.chatroot()
        h.note(f'global: {mod} opens via header',bool(ov),f'click={r}',sev='broken',shot=h.shot(f'audit-missing-{mod}-{theme}') if not ov else None)
        h.close_all()
    # search query + no-results
    h.vcs('#searchBtn'); time.sleep(1.5)
    h.js("(()=>{const inp=document.querySelector('.chatroot input');if(inp){inp.value='zzznohitqq';inp.dispatchEvent(new Event('input',{bubbles:true}));}return 'typed';})()")
    time.sleep(1.5)
    txt=str(h.js("(()=>{const p=document.querySelector('.chatroot');return p?p.innerText.slice(0,300):'none';})()"))
    empty='no result' in txt.lower() or 'nothing' in txt.lower() or 'no match' in txt.lower()
    h.note('global: search no-results state',bool(empty),txt[:80],sev='missing-UX',shot=h.shot(f'audit-missing-searchnores-{theme}') if not empty else None)
    h.close_all()
    # chat empty state (fresh profile threads) -> seed via openWith
    h.vcs('#chatFab'); time.sleep(1.5)
    nthreads=h.js("document.querySelectorAll('.chatroot [data-thread]').length")
    if nthreads==0:
        h.shot(f'audit-missing-chatempty-{theme}')
        h.note('global: chat list empty state shown', 'no conversation' in str(h.js("document.querySelector('.chatroot').innerText")).lower() or 'empty' in str(h.js("document.querySelector('.chatroot').innerText")).lower(),'threads=0',sev='missing-UX')
    h.close_all()
    # ---------- ASTRO ----------
    print('== ASTRO ==')
    h.js("HUB.astro.openCalendar()"); time.sleep(1.5)
    h.note('astro: calendar opens',h.sheet(),'',sev='broken',shot=h.shot(f'audit-missing-cal-{theme}') if not h.sheet() else None)
    if h.sheet(): h.shot(f'audit-missing-calendar-{theme}')
    h.close_all()
    r=h.js("try{HUB.astro.openHoroscope();'called'}catch(e){'ERR:'+String(e).slice(0,60)}")
    time.sleep(1.5)
    h.note('astro: horoscope opens',h.sheet(),str(r),sev='broken')
    h.close_all()
    # ---------- I18N ----------
    print('== I18N ==')
    h.js("HUB.i18n.setLang('es')"); h.tab('home'); time.sleep(1.5)
    scan=h.js("(()=>{const en=['Unread','Jobs','Events','Spending','Today','Groups','Market','Work','Daily'];const txt=document.body.innerText;return en.filter(w=>txt.includes(w));})()")
    h.note('i18n: es home has no English leftovers',len(scan or [])==0,str(scan)[:120],sev='i18n')
    h.shot(f'audit-missing-i18n-es-home-{theme}')
    for lg in ['ne','hi']:
        h.js(f"HUB.i18n.setLang('{lg}')"); h.tab('home'); time.sleep(1.5)
        h.shot(f'audit-missing-i18n-{lg}-home-{theme}')
    h.js("HUB.i18n.setLang('en')")
    # ---------- PERSISTENCE ----------
    print('== PERSIST ==')
    h.js("HUB.store.state.profile.name='PersistProbe';HUB.store.save();")
    h.c.send('Page.reload'); time.sleep(6)
    h.js("try{var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    nm=h.js("HUB.store.state.profile.name")
    h.note('persist: profile name survives reload',nm=='PersistProbe',str(nm),sev='broken')
    h.note(theme+': zero console errors',len(h.errs())==0,str(h.errs())[:200],sev='polish')
    h.save(theme,'4b')
finally: h.done()
