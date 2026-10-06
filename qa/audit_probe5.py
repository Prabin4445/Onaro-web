#!/usr/bin/env python3
"""Probe5: remaining unknowns, precise."""
import json, subprocess, time, urllib.request, os, shutil
import websocket
CHROME='/opt/meta-chromium/chrome'; BASE='file:///home/hatch/workspace/hub/index.html'; PORT=9791
OUT='/home/hatch/workspace/hub/qa/audit-missing'
class CDP:
    def __init__(self,u): self.ws=websocket.create_connection(u,timeout=12);self.ws.settimeout(12);self.id=0
    def send(self,m,p=None):
        self.id+=1;self.ws.send(json.dumps({'id':self.id,'method':m,'params':p or {}}));d=time.time()+15
        while time.time()<d:
            try:msg=json.loads(self.ws.recv())
            except Exception as e:raise TimeoutError(m+': '+str(e)[:60])
            if msg.get('id')==self.id:return msg.get('result')
        raise TimeoutError(m)
shutil.rmtree('/tmp/hubqa-p5',ignore_errors=True)
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--user-data-dir=/tmp/hubqa-p5','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def js(e):
    r=c.send('Runtime.evaluate',{'expression':e,'returnByValue':True,'awaitPromise':True});return (r or {}).get('result',{}).get('value')
def tab(t): js(f"HUB.showTab('{t}')");time.sleep(1.6)
def close_all():
    js("try{HUB.ui.closeSheet();}catch(e){};for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};const g=document.getElementById('gyBd');if(g)g.remove();const gd=document.querySelector('.gy-drawer');if(gd)gd.remove();");time.sleep(0.7)
def shot(n):
    import base64
    try:
        r=c.send('Page.captureScreenshot',{'format':'png'})
        open(f'{OUT}/{n}.png','wb').write(base64.b64decode(r['data']));return n+'.png'
    except Exception:return None
try:
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list',timeout=3) as r:ts=json.load(r)
            tgt=next(x for x in ts if x['type']=='page' and 'devtools' not in x['url']);break
        except Exception:continue
    c=CDP(tgt['webSocketDebuggerUrl']);c.send('Runtime.enable');c.send('Page.enable')
    js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
    time.sleep(5)
    js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    js("document.body.classList.add('dark')");time.sleep(1);tab('home')
    print('1 Jobs tile:')
    r=js("(()=>{const t=[...document.querySelectorAll('#view-home .gltile')].find(e=>e.textContent.includes('Jobs'));if(!t)return 'none';t.click();return 'clicked';})()")
    time.sleep(2)
    print('   click=',r,'| view-work visible=',js("!document.getElementById('view-work').hidden"),'| errs=',js("window.__huberr.splice(0)"))
    tab('home')
    print('2 appt-add location:',js("(()=>{const b=document.querySelector('[data-appt-add]');return b?('found in '+(b.closest('[id]')||{}).id):'missing';})()"))
    print('   class-manage location:',js("(()=>{const b=document.querySelector('[data-class-manage]');return b?('found in '+(b.closest('[id]')||{}).id+' txt='+b.textContent.trim().slice(0,20)):'missing';})()"))
    print('   home innerText has Add appt:',js("document.getElementById('view-home').innerText.includes('Add appointment')||document.getElementById('view-home').innerText.includes('Add appt')"))
    # appointments add via home card
    r=js("(()=>{const b=document.querySelector('[data-appt-add]');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    print('3 appt form:',r,'sheet=',js("!document.getElementById('sheetHost').hidden"),'apTitle=',js("!!document.getElementById('apTitle')"))
    if js("!!document.getElementById('apTitle')"):
        js("document.getElementById('apTitle').value='QA Appt P5';document.getElementById('apDate').value='2030-07-01';document.getElementById('apTime').value='09:00';document.getElementById('apSave').click()")
        time.sleep(1.8)
        print('   created:',js("HUB.store.state.appointments.some(a=>a.title==='QA Appt P5')"))
        before=js("HUB.store.state.appointments.length")
        js("(()=>{const d=[...document.querySelectorAll('[data-appt-del]')];if(d.length)d[d.length-1].click();return d.length;})()")
        time.sleep(1.8)
        after=js("HUB.store.state.appointments.length")
        print('   delete: before=',before,'after=',after,'sheet=',js("!document.getElementById('sheetHost').hidden"),'errs=',js("window.__huberr.splice(0)"))
    close_all()
    # classes
    r=js("(()=>{const b=document.querySelector('[data-class-manage]');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    print('4 class manage:',r,'sheet=',js("!document.getElementById('sheetHost').hidden"))
    if js("!document.getElementById('sheetHost').hidden"):
        js("document.getElementById('clsSubject').value='QA Phys P5';document.getElementById('clsStart').value='09:00';document.getElementById('clsEnd').value='10:00';(()=>{const c=[...document.querySelectorAll('#sheetHost input[type=checkbox]')][0];if(c)c.click();})();document.getElementById('clsAdd').click()")
        time.sleep(1.8)
        print('   created:',js("HUB.store.state.classes.some(c=>c.subject==='QA Phys P5')"))
        before=js("HUB.store.state.classes.length")
        js("(()=>{const d=[...document.querySelectorAll('[data-class-del]')];if(d.length)d[d.length-1].click();return d.length;})()")
        time.sleep(1.8)
        after=js("HUB.store.state.classes.length")
        print('   delete: before=',before,'after=',after,'sheet=',js("!document.getElementById('sheetHost').hidden"))
    close_all()
    # vault with title
    tab('me');time.sleep(1)
    js("(()=>{const t=document.getElementById('memTitle');if(t)t.value='QA Note';const n=document.getElementById('memNote');if(n)n.value='QA memory body';const s=document.getElementById('memSave');if(s){s.scrollIntoView({block:'center'});s.click();return 'clicked';}return 'missing';})()")
    time.sleep(1.8)
    print('5 vault added:',js("(HUB.store.state.memories||[]).some(m=>m.title==='QA Note')"),'errs=',js("window.__huberr.splice(0)"))
    before=js("(HUB.store.state.memories||[]).length")
    js("(()=>{const d=[...document.querySelectorAll('#view-me .memDel')];if(d.length){d[d.length-1].click();return 'clicked';}return 'none';})()")
    time.sleep(1.8)
    after=js("(HUB.store.state.memories||[]).length")
    print('   vault delete: before=',before,'after=',after,'confirm sheet=',js("!document.getElementById('sheetHost').hidden"))
    if after<before: shot('audit-missing-vaultdel-dark')
    # gym drawer
    tab('daily');time.sleep(1.5)
    r=js("(()=>{const b=document.getElementById('gySetup');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    print('6 gym drawer:',r,'fSave=',js("!!document.getElementById('fSave')"))
    if js("!!document.getElementById('fSave')"):
        js("document.getElementById('fAge').value='25';document.getElementById('fFt').value='5';document.getElementById('fIn').value='10';document.getElementById('fW').value='180';(()=>{const s=document.querySelector('.gy-drawer [data-f=\"sex\"][data-v=\"m\"]');if(s)s.click();const g=document.querySelector('.gy-drawer [data-f=\"goal\"][data-v=\"maintain\"]');if(g)g.click();})();document.getElementById('fSave').click()")
        time.sleep(2)
        print('   plan saved:',js("!!(HUB.store.state.gym&&HUB.store.state.gym.plan)"),'errs=',js("window.__huberr.splice(0)"))
        close_all();tab('daily');time.sleep(1.5)
        r=js("(()=>{const b=document.getElementById('gyReset');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
        time.sleep(1.5)
        conf=js("!!document.getElementById('gyResetGo')")
        print('   reset click:',r,'confirm sheet:',conf)
        if conf:
            shot('audit-missing-gymreset-dark')
            js("document.getElementById('gyResetNo').click()");time.sleep(1.2)
            print('   cancel keeps plan:',js("!!(HUB.store.state.gym&&HUB.store.state.gym.plan)"))
            js("(()=>{const b=document.getElementById('gyReset');if(b)b.click();})()");time.sleep(1.2)
            js("document.getElementById('gyResetGo').click()");time.sleep(1.8)
            print('   confirm clears plan:',js("!(HUB.store.state.gym&&HUB.store.state.gym.plan)"))
    close_all()
    # group chat + call
    tab('groups');time.sleep(1)
    js("document.getElementById('cgNew').click()");time.sleep(1.5)
    js("document.getElementById('cgName').value='QA Runners P5';document.getElementById('cgDesc').value='QA';(()=>{const sv=[...document.querySelectorAll('#sheetHost button')].find(b=>/^(create|save)/i.test(b.textContent.trim()));if(sv)sv.click();})()")
    time.sleep(2.5)
    js("(()=>{const b=document.getElementById('cgLive');if(b)b.click();})()");time.sleep(1.8)
    print('7 group live:',js("(()=>{const g=(HUB.store.state.cgroups||[]).find(g=>g.name==='QA Runners P5');return g?!!g.live:'nogroup';})()"))
    r=js("(()=>{const b=document.getElementById('cgChatBtn');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(2)
    print('   chat click:',r,'gcText=',js("!!document.getElementById('gcText')"),'errs=',js("window.__huberr.splice(0)"))
    if js("!!document.getElementById('gcText')"):
        js("document.getElementById('gcText').value='QA hello';document.getElementById('gcSend').click()");time.sleep(1.8)
        print('   sent:',js("(()=>{const p=document.querySelector('.chatroot');return p&&p.innerText.includes('QA hello');})()"))
        shot('audit-missing-groupchat-dark')
    close_all()
    r=js("(()=>{const b=document.getElementById('cgCallBtn');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(2.5)
    dbg=js("try{HUB.call._debug()}catch(e){'ERR:'+String(e).slice(0,60)}")
    print('8 call click:',r,'debug=',str(dbg)[:120],'errs=',js("window.__huberr.splice(0)"))
    shot('audit-missing-groupcall-dark')
    close_all()
    try: js("if(HUB.call&&HUB.call.leave)HUB.call.leave()")
    except Exception: pass
    # horoscope via card
    tab('home');time.sleep(1)
    r=js("(()=>{const cd=document.getElementById('astroCard');if(!cd)return 'missing';cd.click();return 'clicked';})()")
    time.sleep(1.8)
    print('9 horoscope card:',r,'sheet=',js("!document.getElementById('sheetHost').hidden"),'errs=',js("window.__huberr.splice(0)"))
    if js("!document.getElementById('sheetHost').hidden"): shot('audit-missing-horoscope-dark')
    close_all()
    # search no-results
    js("document.getElementById('searchBtn').click()");time.sleep(1.5)
    js("(()=>{const inp=document.querySelector('.chatroot input');if(inp){inp.value='zzznohitqq';inp.dispatchEvent(new Event('input',{bubbles:true}));}})()")
    time.sleep(1.5)
    print('10 search no-results text:',str(js("(()=>{const p=document.querySelector('.chatroot');return p?p.innerText.slice(0,200):'none';})()")).replace('\n','|'))
    shot('audit-missing-searchnores-dark')
    close_all()
    # chat empty state
    js("document.getElementById('chatFab').click()");time.sleep(1.5)
    print('11 chat empty text:',str(js("(()=>{const p=document.querySelector('.chatroot');return p?p.innerText.slice(0,200):'none';})()")).replace('\n','|'))
    shot('audit-missing-chatempty-dark')
    close_all()
    # sync retry
    tab('groups');time.sleep(1)
    js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"people\"]');if(b)b.click();})()");time.sleep(1.5)
    r=js("(()=>{const b=document.getElementById('pplSyncBtn');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(2.5)
    print('12 sync retry: click=',r,'frName=',js("!!document.getElementById('frName')"),'toast=',str(js("(()=>[...document.querySelectorAll('#toastHost .toast')].map(e=>e.textContent).join('|'))()"))[:80])
    close_all()
    # es 'Today'
    js("HUB.i18n.setLang('es')");tab('home');time.sleep(1.5)
    print('13 es Today context:',str(js("(()=>{const els=[...document.querySelectorAll('#view-home *')].filter(e=>e.children.length===0&&e.textContent.includes('Today'));return els.slice(0,3).map(e=>e.tagName+':'+e.textContent.trim().slice(0,40));})()"))[:200])
    js("HUB.i18n.setLang('en')")
    # market publish via mkPublish
    tab('market');time.sleep(1.5)
    js("document.getElementById('view-market').scrollTop=0;document.getElementById('mkPostBtn').classList.remove('hide')");time.sleep(2)
    js("document.getElementById('mkPostBtn').click()");time.sleep(1.5)
    print('14 post form:',js("!!document.getElementById('mkPublish')"))
    js("document.getElementById('mkTitle').value='QA Lamp P5';(()=>{const c=document.querySelector('#mkTypeChips .chip[data-t=\"SELL\"]');if(c)c.click();})();document.getElementById('mkPrice').value='25';document.getElementById('mkPublish').click()")
    time.sleep(2)
    print('    published:',js("HUB.store.state.listings.some(l=>l.title==='QA Lamp P5')"),'toast=',str(js("(()=>[...document.querySelectorAll('#toastHost .toast')].map(e=>e.textContent).join('|'))()"))[:60],'errs=',js("window.__huberr.splice(0)"))
    close_all()
    # work accept/delete inline
    tab('work');time.sleep(1.5)
    print('15 data-accept in view:',js("document.querySelectorAll('#view-work [data-accept]').length"),'data-jdel:',js("document.querySelectorAll('#view-work [data-jdel]').length"))
    r=js("(()=>{const b=document.querySelector('#view-work [data-accept]');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    print('    accept click:',r,'confirm sheet=',js("!document.getElementById('sheetHost').hidden"))
    if js("!document.getElementById('sheetHost').hidden"):
        shot('audit-missing-wkaccept-dark')
        js("(()=>{const go=[...document.querySelectorAll('#sheetHost button')].find(b=>/^(accept|confirm|yes)/i.test(b.textContent.trim()));if(go)go.click();})()");time.sleep(1.8)
        print('    accepted:',js("HUB.store.state.jobs.some(j=>j.acceptedBy&&j.status==='accepted')"))
    close_all()
    print('done')
finally: proc.terminate()
