#!/usr/bin/env python3
"""Shared CDP harness for HUB QA v4 (read-only audit; no app changes)."""
import json, subprocess, time, urllib.request, os, shutil, sys
import websocket
CHROME='/opt/meta-chromium/chrome'; BASE='file:///home/hatch/workspace/hub/index.html'
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
class H:
    def __init__(self,port,profile):
        self.port=port;self.profile=profile;self.findings=[]
        shutil.rmtree(profile,ignore_errors=True)
        self.proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',f'--remote-debugging-port={port}','--remote-allow-origins=*',f'--user-data-dir={profile}','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{port}/json/list',timeout=3) as r:ts=json.load(r)
                tgt=next(x for x in ts if x['type']=='page' and 'devtools' not in x['url']);break
            except Exception:continue
        self.c=CDP(tgt['webSocketDebuggerUrl']);self.c.send('Runtime.enable');self.c.send('Page.enable')
        time.sleep(5)
    def js(self,e):
        try:
            r=self.c.send('Runtime.evaluate',{'expression':e,'returnByValue':True,'awaitPromise':True})
            v=(r or {}).get('result',{}).get('value')
            return v
        except Exception as ex: return f'__EVAL_ERR__:{str(ex)[:80]}'
    def clean(self,s):
        return str(s).encode('utf-8','replace').decode('utf-8','replace')
    def tab(self,t): self.js(f"HUB.showTab('{t}')");time.sleep(1.6)
    def vcs(self,sel):
        return self.js(f"(()=>{{const e=document.querySelector('{sel}');if(!e)return 'missing';const cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')return 'hidden-skip';if(e.offsetParent===null&&cs.position!=='fixed')return 'hidden-skip';e.scrollIntoView({{block:'center'}});e.click();return 'clicked';}})()")
    def vct(self,txt,scope="document"):
        return self.js(f"(()=>{{const els=[...{scope}.querySelectorAll('button,[role=button],.gltile,.ev,.mkcard')].filter(e=>e.offsetParent!==null);const b=els.find(e=>e.textContent.trim().includes('{txt}'));if(!b)return false;const cls=b.className||'';if(String(cls).includes('gltile')||b.classList.contains('ev')||b.classList.contains('mkcard')){{b.click();return 'tile';}}b.click();return b.id||b.textContent.trim().slice(0,24);}})()")
    def sheet(self): return bool(self.js("!document.getElementById('sheetHost').hidden"))
    def chatroot(self): return bool(self.js("!!document.querySelector('.chatroot:not([hidden])')"))
    def toast(self):
        self.js("document.getElementById('toastHost').innerHTML=''");time.sleep(0.2)
        return None
    def shot(self,name):
        p=f'{OUT}/{name}.png'
        try:
            r=self.c.send('Page.captureScreenshot',{'format':'png'})
            with open(p,'wb') as f:import base64;f.write(base64.b64decode(r['data']))
        except Exception:return None
        return p
    def close_all(self):
        self.js("try{HUB.ui.closeSheet();}catch(e){};for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};const g=document.getElementById('gyBd');if(g)g.remove();const gd=document.querySelector('.gy-drawer');if(gd)gd.remove();")
        time.sleep(0.7)
    def errs(self): return self.js("window.__huberr?window.__huberr.splice(0):[]")
    def note(self,name,ok,detail='',sev=None,shot=None):
        print(('PASS ' if ok else 'FAIL ')+name+' '+self.clean(detail)[:110])
        if not ok:
            self.findings.append({'name':name,'sev':sev or 'broken','detail':self.clean(detail)[:200],'shot':shot})
            if sev: print(f'  FINDING [{sev}] {self.clean(detail)[:200]}')
    def save(self,theme,tag):
        p=f'{OUT}/findings-{theme}-{tag}.json'
        json.dump(self.findings,open(p,'w'),indent=1,ensure_ascii=True)
        print(f'==== {theme} {tag} done: {len(self.findings)} findings -> {p}')
    def setup(self,theme):
        self.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        self.js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        if theme=='dark': self.js("document.body.classList.add('dark')")
        else: self.js("document.body.classList.remove('dark')")
        time.sleep(1); self.tab('home')
    def done(self): self.proc.terminate()
