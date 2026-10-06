#!/usr/bin/env python3
"""Probe4: remaining unknowns. Prints precise behavior."""
import json, subprocess, time, urllib.request, os, shutil
import websocket
CHROME='/opt/meta-chromium/chrome'; BASE='file:///home/hatch/workspace/hub/index.html'; PORT=9771
class CDP:
    def __init__(self,u): self.ws=websocket.create_connection(u,timeout=12);self.ws.settimeout(12);self.id=0
    def send(self,m,p=None):
        self.id+=1;self.ws.send(json.dumps({'id':self.id,'method':m,'params':p or {}}));d=time.time()+15
        while time.time()<d:
            try:msg=json.loads(self.ws.recv())
            except Exception as e:raise TimeoutError(m+': '+str(e)[:60])
            if msg.get('id')==self.id:return msg.get('result')
        raise TimeoutError(m)
shutil.rmtree('/tmp/hubqa-p4',ignore_errors=True)
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--user-data-dir=/tmp/hubqa-p4','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def js(e):
    r=c.send('Runtime.evaluate',{'expression':e,'returnByValue':True,'awaitPromise':True});return (r or {}).get('result',{}).get('value')
def tab(t): js(f"HUB.showTab('{t}')");time.sleep(1.6)
def close_all():
    js("try{HUB.ui.closeSheet();}catch(e){};for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};");time.sleep(0.7)
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
    tab('home')
    # 1. header buttons
    for bid, mod in [('#searchBtn','search'),('#pulseBtn','pulse'),('#notifBtn','notifications')]:
        r=js(f"(()=>{{const e=document.querySelector('{bid}');if(!e)return 'missing';if(e.offsetParent===null)return 'hidden';e.click();return 'clicked';}})()")
        time.sleep(1.5)
        ov=js("!!document.querySelector('.chatroot:not([hidden])')")
        sh=js("!document.getElementById('sheetHost').hidden")
        print(f'1 {bid}: click={r} chatroot={ov} sheet={sh}')
        # direct API
        r2=js(f"try{{HUB.{mod}.open();'api-ok'}}catch(e){{'api-ERR:'+String(e).slice(0,60)}}")
        time.sleep(1.2)
        ov2=js("!!document.querySelector('.chatroot:not([hidden])')")
        print(f'   direct HUB.{mod}.open(): {r2} chatroot={ov2} errs={js("window.__huberr.splice(0)")}')
        close_all()
    # 2. market post FAB
    tab('market');time.sleep(1)
    print('2 mkPostBtn:',js("(()=>{const f=document.getElementById('mkPostBtn');return f?('cls='+f.className+' vis='+(f.offsetParent!==null)):'missing';})()"))
    r=js("(()=>{const f=document.getElementById('mkPostBtn');if(!f)return 'missing';f.classList.remove('hide');f.scrollIntoView({block:'center'});f.click();return 'clicked';})()")
    time.sleep(1.5)
    print('   after click: sheet=',js("!document.getElementById('sheetHost').hidden"),'errs=',js("window.__huberr.splice(0)"))
    print('   openPost type:',js("typeof HUB.views"))
    close_all()
    # 3. mkMsg
    js("document.querySelector('#view-market [data-listing]').click()");time.sleep(1.5)
    print('3 mkMsg:',js("(()=>{const b=document.getElementById('mkMsg');return b?b.textContent.trim():'missing';})()"))
    r=js("(()=>{try{document.getElementById('mkMsg').click();return 'clicked';}catch(e){return 'ERR:'+e.message.slice(0,60);}})()")
    time.sleep(1.8)
    print('   after: chatroot=',js("!!document.querySelector('.chatroot:not([hidden])')"),'sheet=',js("!document.getElementById('sheetHost').hidden"),'errs=',js("window.__huberr.splice(0)"))
    close_all()
    # 4. chat list thread
    js("document.getElementById('chatFab').click()");time.sleep(1.5)
    print('4 chatroot:',js("!!document.querySelector('.chatroot:not([hidden])')"))
    print('   threads:',js("document.querySelectorAll('.chatroot [data-thread]').length"))
    print('   thread html sample:',str(js("(()=>{const t=document.querySelector('.chatroot [data-thread]');return t?t.outerHTML.slice(0,160):'none';})()")))
    r=js("(()=>{const t=document.querySelector('.chatroot [data-thread]');if(!t)return 'none';t.click();return 'clicked';})()")
    time.sleep(1.8)
    print('   after click: chatText=',js("!!document.getElementById('chatText')"),'errs=',js("window.__huberr.splice(0)"))
    close_all()
    # 5. astro calendar
    r=js("try{HUB.astro.openCalendar();'called'}catch(e){'ERR:'+String(e).slice(0,80)}")
    time.sleep(1.5)
    print('5 astro.openCalendar:',r,'sheet=',js("!document.getElementById('sheetHost').hidden"),'errs=',js("window.__huberr.splice(0)"))
    close_all()
    # 6. gym reset
    tab('daily');time.sleep(1.5)
    print('6 gyReset:',js("(()=>{const b=document.getElementById('gyReset');return b?('vis='+(b.offsetParent!==null)+' txt='+b.textContent.trim().slice(0,20)):'missing';})()"))
    r=js("(()=>{const b=document.getElementById('gyReset');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
    time.sleep(1.5)
    print('   after: sheet=',js("!document.getElementById('sheetHost').hidden"),'gyResetNo=',js("!!document.querySelector('#gyResetNo')"),'errs=',js("window.__huberr.splice(0)"))
    close_all()
    # 7. households sub-tab content
    tab('groups');time.sleep(1)
    js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"households\"]');if(b)b.click();})()");time.sleep(1.5)
    print('7 hh cards:',js("document.querySelectorAll('#view-groups .hh-card').length"))
    print('   view text head:',str(js("document.getElementById('view-groups').innerText")).replace('\n','|')[:300])
    # 8. sync contacts
    js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"people\"]');if(b)b.click();})()");time.sleep(1.5)
    r=js("(()=>{const b=document.getElementById('pplSyncBtn');if(!b)return 'missing';b.click();return 'clicked';})()")
    time.sleep(1.8)
    print('8 sync: click=',r,'sheet=',js("!document.getElementById('sheetHost').hidden"),'frName=',js("!!document.getElementById('frName')"),'toast=',js("(()=>[...document.querySelectorAll('#toastHost .toast')].map(e=>e.textContent).join('|'))()"))
    print('   errs=',js("window.__huberr.splice(0)"))
    close_all()
    # 9. group chat from a live sample group
    js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"clubs\"]');if(b)b.click();})()");time.sleep(1.5)
    r=js("(()=>{const cd=document.querySelector('#view-groups [data-club]');if(!cd)return 'none';cd.scrollIntoView({block:'center'});cd.click();return 'clicked:'+cd.getAttribute('data-club');})()")
    time.sleep(2)
    print('9 club click:',r,'| on club page:',('Back to groups' in str(js("document.body.innerText"))))
    ch=js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Chat'||(x.id==='gcOpen'));return b?(b.click(),'clicked:'+(b.id||b.textContent.trim())):'none';})()")
    time.sleep(1.8)
    print('   chat btn:',ch,'gcText=',js("!!document.getElementById('gcText')"),'errs=',js("window.__huberr.splice(0)"))
    print('done')
finally:proc.terminate()
