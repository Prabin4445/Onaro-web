import subprocess, time, json, base64, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME
import urllib.request

PORT = 9457
def j(c, expr):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--allow-file-access-from-files',
    '--user-data-dir=/tmp/hubqa-degcap2', '--hide-scrollbars',
    'file:///home/hatch/workspace/hub/index.html'])
time.sleep(3)
tgt = None
for _ in range(20):
    try:
        tgts = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json').read())
        tgt = [t for t in tgts if t.get('type') == 'page'][0]; break
    except Exception: time.sleep(0.5)
assert tgt, 'no chrome target'
c = CDP(tgt['webSocketDebuggerUrl'])
c.send('Runtime.enable'); c.send('Page.enable')
c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
ok = False
for _ in range(40):
    if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.degree);") is True:
        ok = True; break
    time.sleep(0.5)
print('HUB ready:', ok)
j(c, """var p=HUB.store.state.profile; p.name='QA'; p.campus='The University of Texas at Dallas';
  p.verified=true; HUB.store.save(); try{HUB.auth.close()}catch(e){}
  var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1;""")
for _ in range(30):
    if j(c, "return !document.getElementById('splash');") is True: break
    time.sleep(0.5)
j(c, "HUB.showTab('home')"); time.sleep(2)
j(c, "var e=document.getElementById('homeDegEntry'); if(e) e.scrollIntoView({block:'center'}); return !!e;")
time.sleep(1.5)
st = j(c, """var e=document.getElementById('homeDegEntry'); if(!e) return {noentry:true};
  var svg=e.querySelector('svg.deg-cap-anim');
  return {svg:!!svg, an:svg?svg.getAnimations().map(a=>a.animationName+':'+a.playState):[],
    tas:svg&&svg.querySelector('.deg-tassel')?getComputedStyle(svg.querySelector('.deg-tassel')).animationName:null};""")
print('STATE:', json.dumps(st))
r = c.send('Page.captureScreenshot', {'format': 'png'})
p = '/home/hatch/workspace/hub/qa/degcap-verify.png'
open(p, 'wb').write(base64.b64decode(r['data']))
print('wrote', p, os.path.getsize(p), 'bytes')
proc.terminate(); proc.wait()
