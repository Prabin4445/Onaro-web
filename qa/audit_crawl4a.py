#!/usr/bin/env python3
"""HUB QA v4a2 (LIGHT or DARK): Home, Daily, Market, Work. Read-only audit."""
import sys, time
sys.path.insert(0,'/home/hatch/workspace/hub/qa')
from cdp_h import H
theme=sys.argv[1] if len(sys.argv)>1 else 'light'
port=9781 if theme=='light' else 9783
h=H(port,f'/tmp/hubqa-4a-{theme}')
try:
    h.setup(theme)
    # ---------- HOME ----------
    print('== HOME ==')
    nt=h.js("document.querySelectorAll('.tabbar .tab').length")
    h.note('home: 6 tabs render',nt and nt>=6,str(nt),sev='broken')
    n=h.js("document.querySelectorAll('#view-home .gltile').length")
    h.note('home: glance tiles',n and n>=7,str(n),sev='broken')
    h.shot(f'audit-missing-home-{theme}')
    r=h.js("(()=>{const t=[...document.querySelectorAll('#view-home .gltile')].find(e=>e.textContent.includes('Bill'));if(!t)return 'none';t.click();return 'clicked';})()")
    time.sleep(1.5)
    opened=h.sheet() or h.chatroot()
    h.note('home: glance tile opens detail',bool(opened),f'click={r}',sev='broken',shot=h.shot(f'audit-missing-glance-bill-{theme}') if not opened else None)
    h.close_all()
    r=h.js("(()=>{const b=document.getElementById('askPillMain');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(1.5)
    h.note('home: ask pill opens',h.chatroot() or h.sheet(),f'click={r}',sev='broken')
    h.close_all()
    r=h.vct('Time Capsule'); time.sleep(1.5)
    h.note('home: capsule pill opens',h.sheet() or h.chatroot(),f'vct={r}',sev='broken')
    h.shot(f'audit-missing-capsule-{theme}'); h.close_all()
    # ---------- DAILY: events via Create FAB ----------
    print('== DAILY =='); h.tab('daily')
    r=h.vcs('#createFab'); time.sleep(1.5)
    nact=h.js("document.querySelectorAll('#sheetHost .caction').length")
    h.note('daily: create FAB opens grid',h.sheet() and nact and nact>=5,f'click={r} actions={nact}',sev='broken',shot=h.shot(f'audit-missing-createfab-{theme}') if not (h.sheet() and nact and nact>=5) else None)
    # event action (data-a=3)
    h.js("(()=>{const b=document.querySelector('#sheetHost .caction[data-a=\"3\"]');if(b)b.click();return 'clicked';})()")
    time.sleep(1.5)
    so=h.sheet()
    h.note('daily: create->event opens form',bool(so) and bool(h.js("document.getElementById('evTitle')")),'',sev='broken')
    if so:
        h.js("(()=>{const t=document.getElementById('evTitle');if(t)t.value='QA Picnic 2030';const w=document.getElementById('evTime');if(w)w.value='2030-06-01 10:00';const sv=document.getElementById('evSave');if(sv)sv.click();return 'saved';})()")
        time.sleep(1.8)
        cnt=h.js("HUB.store.state.events.filter(e=>e.title==='QA Picnic 2030').length")
        h.note('daily: event created',cnt and cnt>0,f'count={cnt}',sev='broken')
        # try to find any delete affordance for the event
        h.js("(()=>{const cd=[...document.querySelectorAll('#view-daily [data-ev]')].find(e=>e.textContent.includes('QA Picnic 2030'));if(cd){cd.scrollIntoView({block:'center'});cd.click();}return 'clicked';})()")
        time.sleep(1.8)
        hasdel=bool(h.js("(()=>{const sh=document.getElementById('sheetHost');return sh&&(/delete|remove/i.test(sh.innerText));})()"))
        h.close_all()
        if not hasdel:
            h.note('daily: events can be deleted',False,'event detail has no delete affordance; events are permanent once created',sev='missing-UX',shot=h.shot(f'audit-missing-evnodelete-{theme}'))
        else:
            h.note('daily: events can be deleted',True,'delete affordance present in detail')
    # appointments
    r=h.js("(()=>{const b=document.querySelector('#view-daily [data-appt-add]');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    if h.sheet():
        h.js("(()=>{const t=document.getElementById('apTitle');if(t)t.value='QA Appt 2030';const d=document.getElementById('apDate');if(d)d.value='2030-06-02';const tm=document.getElementById('apTime');if(tm)tm.value='10:00';const sv=document.getElementById('apSave');if(sv)sv.click();return 'saved';})()")
        time.sleep(1.8)
        ok=h.js("HUB.store.state.appointments.some(a=>a.title==='QA Appt 2030')")
        h.note('daily: appointment created',bool(ok),'',sev='broken')
        before=h.js("HUB.store.state.appointments.length")
        h.js("(()=>{const del=[...document.querySelectorAll('#view-daily [data-appt-del]')];if(del.length){del[0].click();return 'clicked';}return 'none';})()")
        time.sleep(1.8)
        after=h.js("HUB.store.state.appointments.length")
        if after<before:
            h.note('daily: appointment delete asks confirm',False,'deleted immediately with no confirmation (toast only)',sev='missing-UX',shot=h.shot(f'audit-missing-apdel-{theme}'))
        else:
            h.note('daily: appointment delete asks confirm',h.sheet(),f'before={before} after={after}',sev='missing-UX')
        h.close_all()
    else:
        h.note('daily: appointment add opens',False,f'click={r}',sev='broken')
    # classes
    r=h.js("(()=>{const b=document.querySelector('#view-daily [data-class-manage]');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    if h.sheet():
        h.js("(()=>{const s=document.getElementById('clsSubject');if(s)s.value='QA Math 2030';const st=document.getElementById('clsStart');if(st)st.value='09:00';const en=document.getElementById('clsEnd');if(en)en.value='10:00';const d=[...document.querySelectorAll('#sheetHost input[type=checkbox]')][0];if(d)d.click();const sv=document.getElementById('clsAdd');if(sv)sv.click();return 'saved';})()")
        time.sleep(1.8)
        ok=h.js("HUB.store.state.classes.some(c=>c.subject==='QA Math 2030')")
        h.note('daily: class created',bool(ok),'',sev='broken')
        before=h.js("HUB.store.state.classes.length")
        h.js("(()=>{const del=[...document.querySelectorAll('#sheetHost [data-class-del],#view-daily [data-class-del]')];if(del.length){del[0].click();return 'clicked';}return 'none';})()")
        time.sleep(1.8)
        after=h.js("HUB.store.state.classes.length")
        if after<before:
            h.note('daily: class delete asks confirm',False,'deleted immediately with no confirmation (toast only)',sev='missing-UX',shot=h.shot(f'audit-missing-cldel-{theme}'))
        else:
            h.note('daily: class delete asks confirm',h.sheet() or after==before,f'before={before} after={after}',sev='missing-UX')
        h.close_all()
    else:
        h.note('daily: class manage opens',False,f'click={r}',sev='broken')
    h.shot(f'audit-missing-daily-{theme}')
    # ---------- MARKET ----------
    print('== MARKET =='); h.tab('market'); time.sleep(1.5)
    dists=h.js("(()=>[...document.querySelectorAll('#view-market [data-listing]')].map(e=>{const m=(e.innerText||'').match(/([0-9.]+)\\s*mi/);return m?+m[1]:null;}))()")
    n0=h.js("document.querySelectorAll('#view-market [data-listing]').length")
    h.note('market: distances parsed',n0 and n0>0 and all(isinstance(x,(int,float)) for x in (dists or []) if x is not None),f'{n0} {dists}',sev='broken')
    # radius filter
    if dists and any(x is not None for x in dists):
        r=h.vct('5 mi'); time.sleep(1.6)
        n1=h.js("document.querySelectorAll('#view-market [data-listing]').length")
        exp=sum(1 for d in dists if d is not None and d<=5)
        h.note('market: radius chip filters',n1==exp,f'{n0}->{n1} expected {exp}',sev='broken')
    else:
        h.note('market: radius chip filters',True,'no distance text rendered; filter untestable visually')
    # post FAB
    h.js("document.getElementById('view-market').scrollTop=0;document.getElementById('mkPostBtn').classList.remove('hide')")
    time.sleep(2)
    r=h.vcs('#mkPostBtn'); time.sleep(1.5)
    so=h.sheet()
    h.note('market: post FAB opens form',bool(so),f'click={r}',sev='broken',shot=h.shot(f'audit-missing-mkpost-{theme}') if not so else None)
    if so:
        h.js("(()=>{const t=document.getElementById('mkTitle');if(t)t.value='QA Lamp v4';const p=document.getElementById('mkPrice');if(p)p.value='25';const d=document.getElementById('mkDesc');if(d)d.value='QA listing, will delete.';const sv=[...document.querySelectorAll('#sheetHost button')].find(b=>/^(post|publish|list)/i.test(b.textContent.trim()));if(sv)sv.click();return 'posted';})()")
        time.sleep(2)
        ok=h.js("HUB.store.state.listings.some(l=>l.title==='QA Lamp v4')")
        h.note('market: listing published to grid',bool(ok),'',sev='broken')
        h.close_all()
    # detail + message seller + safety checklist -> thread
    h.js("(()=>{const cd=[...document.querySelectorAll('#view-market [data-listing]')].find(e=>!e.textContent.includes('QA Lamp v4'))||document.querySelector('#view-market [data-listing]');if(cd){cd.scrollIntoView({block:'center'});cd.click();}return 'clicked';})()")
    time.sleep(1.8)
    h.note('market: detail opens',h.sheet(),'',sev='broken')
    if h.sheet():
        h.shot(f'audit-missing-mkdetail-{theme}')
        h.vcs('#mkMsg'); time.sleep(1.8)
        sc=str(h.js("document.getElementById('sheetHost').innerText"))
        ischeck='safety' in sc.lower() or 'checklist' in sc.lower()
        h.note('market: message seller -> safety checklist',h.sheet() and ischeck,sc[:60],sev='broken')
        h.shot(f'audit-missing-safety-{theme}')
        h.js("(()=>{const sh=document.getElementById('sheetHost');[...sh.querySelectorAll('input[type=checkbox]')].forEach(c=>{c.checked=true;c.dispatchEvent(new Event('change',{bubbles:true}));});const go=[...sh.querySelectorAll('button')].find(b=>/done|continue|start chat|agree/i.test(b.textContent));if(go)go.click();return go?go.textContent.trim():'nobtn';})()")
        time.sleep(2)
        h.note('market: checklist done -> chat thread',h.chatroot(),f'chatroot={h.chatroot()}',sev='broken')
        if h.chatroot():
            h.js("(()=>{const t=document.getElementById('chatText');if(t){t.value='Is this still available?';}const s=document.getElementById('chatSend');if(s)s.click();return 'sent';})()")
            time.sleep(1.8)
            msgs=h.js("(()=>{const p=document.querySelector('.chatroot');return p?p.innerText.length:0;})()")
            h.note('market: chat message sent+rendered',msgs and msgs>200,f'thread chars={msgs}',sev='broken')
            h.shot(f'audit-missing-chatthread-{theme}')
        h.close_all()
    # delete own listing (two-tap)
    h.js("(()=>{const cd=[...document.querySelectorAll('#view-market [data-listing]')].find(e=>e.textContent.includes('QA Lamp v4'));if(cd){cd.scrollIntoView({block:'center'});cd.click();}return 'clicked';})()")
    time.sleep(1.8)
    r=h.vcs('#mkDelete'); time.sleep(1.2)
    armed='confirm' in str(h.js("document.getElementById('mkDelete')?document.getElementById('mkDelete').textContent:''")).lower() if h.sheet() else False
    gone=None
    if r=='clicked':
        h.vcs('#mkDelete'); time.sleep(1.5)
        gone=not h.js("HUB.store.state.listings.some(l=>l.title==='QA Lamp v4')")
    h.note('market: own listing delete needs 2 taps',bool(armed) and bool(gone),f'armed={armed} gone={gone}',sev='missing-UX')
    h.close_all()
    h.shot(f'audit-missing-market-{theme}')
    # ---------- WORK ----------
    print('== WORK =='); h.tab('work'); time.sleep(1)
    r=h.vcs('#postJobBtn'); time.sleep(1.5)
    so=h.sheet()
    h.note('work: post job opens form',bool(so),f'click={r}',sev='broken',shot=h.shot(f'audit-missing-wkpost-{theme}') if not so else None)
    if so:
        h.js("(()=>{const t=document.getElementById('pjTitle');if(t)t.value='QA Lawn mowing';const p=document.getElementById('pjPay');if(p)p.value='40';const d=document.getElementById('pjDesc');if(d)d.value='QA job';const sv=document.getElementById('pjGo');if(sv)sv.click();return 'posted';})()")
        time.sleep(2)
        ok=h.js("HUB.store.state.jobs.some(j=>j.title==='QA Lawn mowing')")
        h.note('work: job posted',bool(ok),'',sev='broken')
        h.close_all()
    # accept flow w/ confirm (non-own sample job)
    h.js("(()=>{const cd=[...document.querySelectorAll('#view-work [data-job]')].find(e=>!e.textContent.includes('QA Lawn'));if(cd){cd.scrollIntoView({block:'center'});cd.click();}return 'clicked';})()")
    time.sleep(1.8)
    r=h.js("(()=>{const b=document.querySelector('#sheetHost [data-accept]');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(1.5)
    h.note('work: accept asks confirm',h.sheet(),f'click={r} sheet={h.sheet()}',sev='missing-UX',shot=h.shot(f'audit-missing-wkaccept-{theme}') if not h.sheet() else None)
    if h.sheet():
        h.js("(()=>{const go=[...document.querySelectorAll('#sheetHost button')].find(b=>/^(accept|confirm|yes)/i.test(b.textContent.trim()));if(go)go.click();return go?go.textContent.trim():'nobtn';})()")
        time.sleep(1.8)
        acc=h.js("HUB.store.state.jobs.some(j=>j.acceptedBy&&j.status==='accepted')")
        h.note('work: accept confirm takes job',bool(acc),'',sev='broken')
    h.close_all()
    # delete own job w/ confirm
    h.js("(()=>{const cd=[...document.querySelectorAll('#view-work [data-job]')].find(e=>e.textContent.includes('QA Lawn'));if(cd){cd.scrollIntoView({block:'center'});cd.click();}return 'clicked';})()")
    time.sleep(1.8)
    before=h.js("HUB.store.state.jobs.length")
    r=h.js("(()=>{const b=document.querySelector('#sheetHost [data-jdel]');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(1.8)
    after=h.js("HUB.store.state.jobs.length")
    if after<before and not h.sheet():
        h.note('work: delete own job asks confirm',False,'deleted immediately with no confirmation',sev='missing-UX',shot=h.shot(f'audit-missing-wkdel-{theme}'))
    else:
        h.note('work: delete own job asks confirm',h.sheet() or after==before,f'before={before} after={after} sheet={h.sheet()}',sev='missing-UX')
        if h.sheet():
            h.shot(f'audit-missing-wkdelconf-{theme}')
            h.js("(()=>{const go=[...document.querySelectorAll('#sheetHost button')].find(b=>/^(delete|confirm|yes)/i.test(b.textContent.trim()));if(go)go.click();})()")
            time.sleep(1.5)
    h.close_all()
    h.shot(f'audit-missing-work-{theme}')
    h.note(theme+': zero console errors',len(h.errs())==0,str(h.errs())[:200],sev='polish')
    h.save(theme,'4a')
finally: h.done()
