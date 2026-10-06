import json, subprocess, time, urllib.request, base64
import websocket
CHROME='/opt/meta-chromium/chrome'; PORT=9453
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
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--window-size=414,900','--user-data-dir=/tmp/hubqa10-prof','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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
    js("HUB.notifications.open()");time.sleep(0.6)
    print('notif open:',js("!!document.getElementById('notifRoot')&&!document.getElementById('notifRoot').hidden"))
    js("HUB.showTab('me')");time.sleep(0.8)
    print('notif cleared on tab switch:',js("!document.getElementById('notifRoot')"))
    print('me visible:',js("!document.getElementById('view-me').hidden"))
    r=c.send('Page.captureScreenshot',{'format':'png'})
    open('/home/hatch/workspace/hub/qa/qa10-me-after-tabfix.png','wb').write(base64.b64decode(r['data']))
    print('discToggle present:',js("!!document.getElementById('discToggle')"))
    print('errors:',js("window.__huberr.splice(0)"))
finally:
    proc.terminate()
