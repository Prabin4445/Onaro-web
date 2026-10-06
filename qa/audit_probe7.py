#!/usr/bin/env python3
"""Probe7: capture delete-no-confirm screenshots (appt, class)."""
import json, subprocess, time, urllib.request, os, shutil, base64
import websocket
CHROME='/opt/meta-chromium/chrome'; BASE='file:///home/hatch/workspace/hub/index.html'; PORT=9795
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
shutil.rmtree('/tmp/hubqa-p7',ignore_errors=True)
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--user-data-dir=/tmp/hubqa-p7','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def js(e):
    r=c.send('Runtime.evaluate',{'expression':e,'returnByValue':True,'awaitPromise':True});return (r or {}).get('result',{}).get('value')
def shot(n):
    r=c.send('Page.captureScreenshot',{'format':'png'})
    open(f'{OUT}/{n}.png','wb').write(base64.b64decode(r['data']))
try:
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list',timeout=3) as r:ts=json.load(r)
            tgt=next(x for x in ts if x['type']=='page' and 'devtools' not in x['url']);break
        except Exception:continue
    c=CDP(tgt['webSocketDebuggerUrl']);c.send('Runtime.enable');c.send('Page.enable')
    time.sleep(5)
    js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    js("document.body.classList.add('dark')");time.sleep(1)
    js("HUB.showTab('home')");time.sleep(1.6)
    # appointment: add then show the delete affordance, screenshot BEFORE deleting
    js("document.querySelector('[data-appt-add]').click()");time.sleep(1.5)
    js("document.getElementById('apTitle').value='QA Appt Shot';document.getElementById('apDate').value='2030-07-02';document.getElementById('apTime').value='09:00';document.getElementById('apSave').click()");time.sleep(1.8)
    print('appt added:',js("HUB.store.state.appointments.some(a=>a.title==='QA Appt Shot')"))
    shot('audit-missing-apptcard-dark')
    before=js("HUB.store.state.appointments.length")
    js("(()=>{const d=[...document.querySelectorAll('[data-appt-del]')];if(d.length){d[d.length-1].scrollIntoView({block:'center'});} })()");time.sleep(0.8)
    shot('audit-missing-apdel-dark')
    js("(()=>{const d=[...document.querySelectorAll('[data-appt-del]')];if(d.length)d[d.length-1].click();})()");time.sleep(1.5)
    print('appt delete: before=',before,'after=',js("HUB.store.state.appointments.length"),'sheet=',js("!document.getElementById('sheetHost').hidden"))
    # class: manage sheet with delete affordance
    js("document.querySelector('[data-class-manage]').click()");time.sleep(1.5)
    shot('audit-missing-cldel-dark')
    before=js("HUB.store.state.classes.length")
    js("(()=>{const d=[...document.querySelectorAll('[data-class-del]')];if(d.length)d[d.length-1].click();})()");time.sleep(1.5)
    print('class delete: before=',before,'after=',js("HUB.store.state.classes.length"),'sheet=',js("!document.getElementById('sheetHost').hidden"))
    print('done')
finally: proc.terminate()
