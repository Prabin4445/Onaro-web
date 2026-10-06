import json, subprocess, time, urllib.request, os
import websocket
CHROME='/opt/meta-chromium/chrome'; PORT=9460
BASE='file:///home/hatch/workspace/hub/index.html'
subprocess.Popen(['rm','-rf','/tmp/hubreg'])
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--window-size=414,900','--user-data-dir=/tmp/hubreg','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
state={'id':0}
try:
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list',timeout=3) as r: ts=json.load(r)
            tgt=next(t for t in ts if t['type']=='page' and 'devtools' not in t['url']); break
        except Exception: continue
    ws=websocket.create_connection(tgt['webSocketDebuggerUrl'],timeout=12); ws.settimeout(12)
    def send(m,p=None):
        state['id']+=1
        ws.send(json.dumps({'id':state['id'],'method':m,'params':p or {}}))
        dl=time.time()+15
        while time.time()<dl:
            msg=json.loads(ws.recv())
            if msg.get('id')==state['id']: return msg.get('result')
        raise TimeoutError(m)
    send('Runtime.enable')
    def js(e):
        r=send('Runtime.evaluate',{'expression':e,'returnByValue':True})
        res=(r or {}).get('result',{}); return res.get('value'), (r or {}).get('exceptionDetails')
    for _ in range(20):
        v,_=js("typeof HUB!=='undefined'")
        if v: break
        time.sleep(1)
    time.sleep(3)
    js("window.__e=[];addEventListener('error',e=>__e.push(e.message+' @ '+(e.filename||'').split('/').pop()+':'+(e.lineno||'')))")
    js("HUB.i18n.setLang('fr')"); time.sleep(2)
    v,_=js("document.documentElement.lang")
    print('lang=',v)
    e,_=js("window.__e.splice(0)")
    print('errors:',e)
    ws.close()
finally: proc.terminate()
