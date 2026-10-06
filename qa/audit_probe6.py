#!/usr/bin/env python3
"""Probe6: final retests with corrected selectors/keys."""
import json, subprocess, time, urllib.request, os, shutil
import websocket
CHROME='/opt/meta-chromium/chrome'; BASE='file:///home/hatch/workspace/hub/index.html'; PORT=9793
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
shutil.rmtree('/tmp/hubqa-p6',ignore_errors=True)
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--user-data-dir=/tmp/hubqa-p6','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def js(e):
    r=c.send('Runtime.evaluate',{'expression':e,'returnByValue':True,'awaitPromise':True});return (r or {}).get('result',{}).get('value')
def tab(t): js(f"HUB.showTab('{t}')");time.sleep(1.6)
def close_all():
    js("try{HUB.ui.closeSheet();}catch(e){};for(const k of ['chat','pulse','search','notifications','gchat','groupchat'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};const g=document.getElementById('gyBd');if(g)g.remove();const gd=document.querySelector('.gy-drawer');if(gd)gd.remove();");time.sleep(0.7)
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
    js("document.body.classList.add('dark')");time.sleep(1)
    # 1. vault with correct key state.memory
    tab('me');time.sleep(1)
    js("(()=>{const t=document.getElementById('memTitle');if(t)t.value='QA Note P6';const n=document.getElementById('memNote');if(n)n.value='QA memory body P6';const s=document.getElementById('memSave');if(s){s.scrollIntoView({block:'center'});s.click();return 'clicked';}return 'missing';})()")
    time.sleep(1.8)
    added=js("(HUB.store.state.memory||[]).some(m=>m.title==='QA Note P6')")
    print('1 vault added:',added,'errs=',js("window.__huberr.splice(0)"))
    if added:
        before=js("(HUB.store.state.memory||[]).length")
        js("(()=>{const d=[...document.querySelectorAll('#view-me .memDel')];if(d.length){d[d.length-1].click();return 'clicked';}return 'none';})()")
        time.sleep(1.8)
        after=js("(HUB.store.state.memory||[]).length")
        print('   vault delete: before=',before,'after=',after,'confirm sheet=',js("!document.getElementById('sheetHost').hidden"))
        if after<before: shot('audit-missing-vaultdel-dark')
    close_all()
    # 2. gym drawer with fT
    tab('daily');time.sleep(1.5)
    js("(()=>{const b=document.getElementById('gySetup');if(b){b.scrollIntoView({block:'center'});b.click();return 'clicked';}return 'missing';})()")
    time.sleep(1.5)
    js("document.getElementById('fAge').value='25';document.getElementById('fFt').value='5';document.getElementById('fIn').value='10';document.getElementById('fW').value='180';document.getElementById('fT').value='170';(()=>{const s=document.querySelector('.gy-drawer [data-f=\"sex\"][data-v=\"m\"]');if(s)s.click();const g=document.querySelector('.gy-drawer [data-f=\"goal\"][data-v=\"maintain\"]');if(g)g.click();})();document.getElementById('fSave').click()")
    time.sleep(2)
    prof=js("!!(HUB.store.state.gym&&HUB.store.state.gym.profile)")
    print('2 gym profile saved:',prof,'errs=',js("window.__huberr.splice(0)"),'toast=',str(js("(()=>[...document.querySelectorAll('#toastHost .toast')].map(e=>e.textContent).join('|'))()"))[:60])
    close_all();tab('daily');time.sleep(1.8)
    r=js("(()=>{const b=document.getElementById('gyReset');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    conf=js("!!document.getElementById('gyResetGo')")
    print('   reset click:',r,'confirm sheet:',conf)
    if conf:
        shot('audit-missing-gymreset-dark')
        js("document.getElementById('gyResetNo').click()");time.sleep(1.2)
        print('   cancel keeps profile:',js("!!(HUB.store.state.gym&&HUB.store.state.gym.profile)"))
        js("(()=>{const b=document.getElementById('gyReset');if(b)b.click();})()");time.sleep(1.2)
        js("document.getElementById('gyResetGo').click()");time.sleep(1.8)
        print('   confirm clears profile:',js("!(HUB.store.state.gym&&HUB.store.state.gym.profile)"))
    close_all()
    # 3. search no-results (gchat closed)
    tab('home')
    js("document.getElementById('searchBtn').click()");time.sleep(1.5)
    print('3 search open:',js("!!document.querySelector('.chatroot:not([hidden])')"))
    js("(()=>{const inp=document.querySelector('.chatroot input');if(inp){inp.value='zzznohitqq';inp.dispatchEvent(new Event('input',{bubbles:true}));return 'typed';}return 'noinput';})()")
    time.sleep(1.8)
    txt=str(js("(()=>{const p=document.querySelector('.chatroot');return p?p.innerText.slice(0,250):'none';})()")).replace('\n','|')
    print('   no-results text:',txt)
    shot('audit-missing-searchnores-dark')
    close_all()
    # 4. sync contacts (check mode)
    tab('groups');time.sleep(1)
    js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"people\"]');if(b)b.click();})()");time.sleep(1.5)
    print('4 people sub visible:',js("!!document.getElementById('view-groups')"),'pplSyncBtn:',js("!!document.getElementById('pplSyncBtn')"))
    r=js("(()=>{const b=document.getElementById('pplSyncBtn');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(2.5)
    print('   click:',r,'frName=',js("!!document.getElementById('frName')"),'toast=',str(js("(()=>[...document.querySelectorAll('#toastHost .toast')].map(e=>e.textContent).join('|'))()"))[:80],'errs=',js("window.__huberr.splice(0)"))
    if js("!!document.getElementById('frName')"): shot('audit-missing-sync-dark')
    close_all()
    # 5. horoscope with DOB
    js("HUB.store.state.profile.dob='2000-05-15';HUB.store.save()")
    tab('home');time.sleep(1.5)
    r=js("(()=>{const cd=[...document.querySelectorAll('#view-home .card')].find(e=>/horoscope|zodiac|🔮/i.test(e.textContent));if(!cd)return 'none';cd.scrollIntoView({block:'center'});cd.click();return 'clicked';})()")
    time.sleep(2)
    print('5 horoscope:',r,'sheet=',js("!document.getElementById('sheetHost').hidden"),'errs=',js("window.__huberr.splice(0)"))
    if js("!document.getElementById('sheetHost').hidden"): shot('audit-missing-horoscope-dark')
    close_all()
    # 6. work own-job delete confirm
    tab('work');time.sleep(1)
    js("document.getElementById('postJobBtn').click()");time.sleep(1.5)
    js("document.getElementById('pjTitle').value='QA Own Job';document.getElementById('pjPay').value='30';document.getElementById('pjGo').click()");time.sleep(2)
    print('6 own job posted:',js("HUB.store.state.jobs.some(j=>j.title==='QA Own Job')"))
    print('   data-jdel in view:',js("document.querySelectorAll('#view-work [data-jdel]').length"))
    before=js("HUB.store.state.jobs.length")
    r=js("(()=>{const b=[...document.querySelectorAll('#view-work [data-jdel]')].find(x=>x.closest('[data-job]')&&x.closest('[data-job]').textContent.includes('QA Own Job'))||document.querySelector('#view-work [data-jdel]');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.8)
    after=js("HUB.store.state.jobs.length")
    print('   delete click:',r,'before=',before,'after=',after,'confirm sheet=',js("!document.getElementById('sheetHost').hidden"))
    if js("!document.getElementById('sheetHost').hidden"): shot('audit-missing-wkdel-dark')
    close_all()
    print('done')
finally: proc.terminate()
