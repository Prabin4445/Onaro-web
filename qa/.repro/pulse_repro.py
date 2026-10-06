import json, subprocess, time, urllib.request, os
import websocket
CHROME='/opt/meta-chromium/chrome'; PORT=9461
BASE='file:///home/hatch/workspace/hub/index.html'
subprocess.Popen(['rm','-rf','/tmp/hubpulse'])
proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu',f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--window-size=414,900','--user-data-dir=/tmp/hubpulse','--hide-scrollbars','--allow-file-access-from-files',BASE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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
        v,_=js("typeof HUB!=='undefined'&&!!document.getElementById('wlcmHost')&&!document.getElementById('wlcmHost').hidden")
        if v: break
        time.sleep(1)
    time.sleep(2)
    js("window.__e=[];addEventListener('error',e=>__e.push(e.message))")
    js("document.getElementById('wlcmGo').click()"); time.sleep(1)
    # skip role by direct onboard
    js("HUB.store.state.profile.name='T';HUB.store.state.profile.audience='student';HUB.store.state.profile.campus='X';HUB.store.state.onboarded=true;HUB.store.save();HUB.showTab('home')"); time.sleep(1)
    v,exc=js("(()=>{try{HUB.pulse.open();return 'opened'}catch(e){return 'THROW:'+e.message+' | '+(e.stack||'').split('\\n')[1]}})()")
    print('open result:',v,exc)
    time.sleep(0.8)
    v,_=js("!!document.getElementById('hubPulseRows')")
    print('hubPulseRows:',v)
    e,_=js("window.__e.splice(0)")
    print('errors:',e)
    ws.close()
finally: proc.terminate()
