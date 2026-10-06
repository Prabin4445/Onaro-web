import json, subprocess, time, urllib.request
import websocket
CHROME='/opt/meta-chromium/chrome'; PORT=9451
BASE='file:///home/hatch/workspace/hub/index.html'
class CDP:
    def __init__(self,w):
        self.ws=websocket.create_connection(w,timeout=12);self.ws.settimeout(12);self.id=0
    def send(self,m,p=None):
        self.id+=1;self.ws.send(json.dumps({'id':self.id,'method':m,'params':p or {}}))
        d=time.time()+15
        while time.time()<d:
            try:msg=json.loads(self.ws.recv())
            except Exception as e:raise TimeoutError(str(e)[:80])
            if msg.get('id')==self.id:return msg.get('result')
        raise TimeoutError(m)
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--window-size=414,900','--user-data-dir=/tmp/hubqa9-prof','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    tgt=None
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list',timeout=3) as r:ts=json.load(r)
            tgt=next(t for t in ts if t['type']=='page' and 'devtools' not in t['url']);break
        except Exception:continue
    c=CDP(tgt['webSocketDebuggerUrl']);c.send('Runtime.enable');c.send('Page.enable')
    def js(e):
        r=c.send('Runtime.evaluate',{'expression':e,'returnByValue':True});res=(r or {}).get('result',{});return res.get('value')
    js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message))")
    for _ in range(25):
        if js("typeof HUB")!='undefined':break
        time.sleep(1)
    time.sleep(2)
    js("(()=>{const st=JSON.parse(localStorage.getItem('hub_v1'));st.profile.name='QA';st.profile.campus='Riverside State';st.profile.audience='student';localStorage.setItem('hub_v1',JSON.stringify(st))})()")
    js("location.reload()");time.sleep(2.5)
    js("HUB.showTab('market')");time.sleep(1)
    js("(()=>{const it=[...document.querySelectorAll('#view-market .item')].find(x=>x.textContent.includes('Desk lamp'));if(it)it.click()})()");time.sleep(0.8)
    js("document.getElementById('mkMsg').click()");time.sleep(1)
    print('safety checklist shown:',js("!!document.getElementById('safetyGo')"))
    r=c.send('Page.captureScreenshot',{'format':'png'})
    open('/home/hatch/workspace/hub/qa/qa9-safety-check.png','wb').write(__import__('base64').b64decode(r['data']))
    js("document.getElementById('safetySkip').click()");time.sleep(1)
    print('chat thread opens after skip:',js("!!document.getElementById('chatRoot')&&!document.getElementById('chatRoot').hidden"))
    r=c.send('Page.captureScreenshot',{'format':'png'})
    open('/home/hatch/workspace/hub/qa/qa9-chat-thread.png','wb').write(__import__('base64').b64decode(r['data']))
    # second time: no checklist, straight to thread
    js("HUB.chat.close()");time.sleep(0.4)
    js("HUB.showTab('market')");time.sleep(0.8)
    js("(()=>{const it=[...document.querySelectorAll('#view-market .item')].find(x=>x.textContent.includes('Desk lamp'));if(it)it.click()})()");time.sleep(0.8)
    js("document.getElementById('mkMsg').click()");time.sleep(1)
    print('2nd time: no checklist:',js("!document.getElementById('safetyGo')"))
    print('2nd time: thread direct:',js("!!document.getElementById('chatRoot')&&!document.getElementById('chatRoot').hidden"))
    print('errors:',js("window.__huberr.splice(0)"))
finally:
    proc.terminate()
