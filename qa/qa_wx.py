#!/usr/bin/env python3
"""QA: Home weather car-dashboard strip + glass detail (Open-Meteo stubbed).
Weather removed from Daily; strip below Appointments; tap->detail; unit
toggle; city search; GPS. Fresh profiles, zero console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9534
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)
class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

# ---- fetch + geolocation stubs injected before page scripts run ----
STUB = r"""
window.__wxStub = (function(){
  var days=[], codes=[0,61,2,3,80,1,95], hi=[92,88,90,91,87,93,89], lo=[74,73,75,76,72,74,73], pp=[10,60,20,30,70,10,80];
  for(var i=0;i<7;i++){ var d=new Date(); d.setDate(d.getDate()+i);
    days.push(d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')); }
  var ht=[], hv=[], hc=[], hp=[];
  for(var h=0;h<48;h++){ var t2=new Date(); t2.setHours(t2.getHours()+h,0,0,0);
    ht.push(t2.getFullYear()+'-'+String(t2.getMonth()+1).padStart(2,'0')+'-'+String(t2.getDate()).padStart(2,'0')+'T'+String(t2.getHours()).padStart(2,'0')+':00');
    hv.push(75+Math.round(12*Math.sin((h-9)/24*Math.PI*2))); hc.push(codes[h%7]); hp.push((h*7)%100); }
  return {current:{temperature_2m:79.2,relative_humidity_2m:76,apparent_temperature:87.1,weather_code:0,wind_speed_10m:2.3},
    hourly:{time:ht,temperature_2m:hv,weather_code:hc,precipitation_probability:hp},
    daily:{time:days,weather_code:codes,temperature_2m_max:hi,temperature_2m_min:lo,precipitation_probability_max:pp}};
})();
window.__geoStub = {results:[{name:'Dallas',admin1:'Texas',country:'United States',latitude:32.7767,longitude:-96.797}]};
/* honor the requested units like the real API: canned data is stored in F/mph */
window.__wxConvert = function(base, url){
  var d = JSON.parse(JSON.stringify(base));
  var tu = /temperature_unit=(\w+)/.exec(url||''), wu = /wind_speed_unit=(\w+)/.exec(url||'');
  if(tu && tu[1]==='celsius'){
    var f2c=function(f){return (f-32)*5/9;};
    d.current.temperature_2m=f2c(d.current.temperature_2m);
    d.current.apparent_temperature=f2c(d.current.apparent_temperature);
    d.hourly.temperature_2m=d.hourly.temperature_2m.map(f2c);
    d.daily.temperature_2m_max=d.daily.temperature_2m_max.map(f2c);
    d.daily.temperature_2m_min=d.daily.temperature_2m_min.map(f2c);
  }
  if(wu && wu[1]==='kmh'){ d.current.wind_speed_10m=d.current.wind_speed_10m*1.60934; }
  return d;
};
var _fetch = window.fetch.bind(window);
window.fetch = function(url, opts){
  var u = String(url||'');
  if(u.indexOf('api.open-meteo.com/v1/forecast')>=0)
    return Promise.resolve(new Response(JSON.stringify(window.__wxConvert(window.__wxStub,u)),{status:200,headers:{'Content-Type':'application/json'}}));
  if(u.indexOf('geocoding-api.open-meteo.com')>=0)
    return Promise.resolve(new Response(JSON.stringify(window.__geoStub),{status:200,headers:{'Content-Type':'application/json'}}));
  return _fetch(url, opts);
};
if(navigator.geolocation){ navigator.geolocation.getCurrentPosition = function(succ){ succ({coords:{latitude:32.7767,longitude:-96.797}}); }; }
"""

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-wx-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-wx-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Page.addScriptToEvaluateOnNewDocument', {'source': STUB})
        # reload AFTER injecting the stub (the CLI-arg page load already ran without it)
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name, elid=None):
            params = {'format': 'png'}
            if elid:
                js(f"var e=document.getElementById('{elid}');if(e)e.scrollIntoView({{block:'center'}});")
                time.sleep(0.6)
            r = c.send('Page.captureScreenshot', params)
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def clearToasts():
            js("var h=document.getElementById('toastHost');if(h)h.innerHTML=''")

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        # seed weather location (unit f) before showing home
        js("HUB.store.state.prefs.weatherLoc={name:'Dallas',lat:32.7767,lon:-96.797};HUB.store.state.prefs.weatherUnit='f';HUB.store.save();")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(3)
        errs('home render')

        # ---- strip present, below Appointments ----
        note(js("!!document.getElementById('wxStrip')"), f'{theme}: weather strip renders on Home')
        note(js("document.querySelector('link[data-wx-css]')!==null"), f'{theme}: wx.css injected')
        order = js("(()=>{const v=document.getElementById('view-home').innerHTML;return {a:v.indexOf('apptCard'),w:v.indexOf('wxStrip')};})()")
        note(order and order['a'] > 0 and order['w'] > order['a'], f'{theme}: strip sits BELOW Appointments card')
        strip_txt = str(js("document.getElementById('wxStrip').textContent"))
        note('Today' in strip_txt and 'Tomorrow' in strip_txt, f'{theme}: strip shows Today + Tomorrow')
        note('79°F' in strip_txt, f'{theme}: Today current temp 79°F in strip')
        note('88°F' in strip_txt, f'{theme}: Tomorrow max temp 88°F in strip')
        note('60%' in strip_txt, f'{theme}: Tomorrow rain signal 60% in strip')
        shot(f'wx-strip-{theme}.png', 'wxStrip')

        # ---- tap strip -> glass detail ----
        clearToasts()
        js("document.getElementById('wxStrip').click()"); time.sleep(1.5)
        note(js("!document.getElementById('sheetHost').hidden"), f'{theme}: detail sheet opens on strip tap')
        note(js("!!document.querySelector('#sheetBox .wxd-crystal')"), f'{theme}: glass crystal detail wrapper')
        body = str(js("document.getElementById('wxdBody').textContent"))
        note('Humidity' in body and 'Wind' in body, f'{theme}: detail has humidity + wind')
        note('Next 7 days' in body, f'{theme}: detail has 7-day forecast')
        note('Hourly' in body, f'{theme}: detail has hourly strip')
        note('Open-Meteo' in body, f'{theme}: source label Open-Meteo present')
        note('Tomorrow' in body, f'{theme}: day-1 labeled Tomorrow in 7-day list')
        shot(f'wx-detail-{theme}.png')
        errs('detail')

        # ---- unit toggle °F -> °C ----
        js("document.getElementById('wxdUnit').click()"); time.sleep(1.5)
        body2 = str(js("document.getElementById('wxdBody').textContent"))
        note('26°C' in body2, f'{theme}: unit toggle -> 26°C (was 79°F)')
        strip2 = str(js("document.getElementById('wxStrip').textContent"))
        note('26°C' in strip2, f'{theme}: strip repaints in °C too')
        errs('unit toggle')

        # ---- city search -> pick Dallas ----
        clearToasts()
        js("document.getElementById('wxdIn').value='Dal';document.getElementById('wxdGo').click()"); time.sleep(1.5)
        note('Dallas' in str(js("document.getElementById('wxdRes').textContent")), f'{theme}: search returns Dallas')
        js("document.querySelector('#wxdRes .wxres').click()"); time.sleep(1.5)
        note('Dallas' in str(js("document.getElementById('sheetBox').textContent")), f'{theme}: picked Dallas, sheet repaints')
        note(js("HUB.store.state.prefs.weatherLoc.name")== 'Dallas', f'{theme}: location persisted in prefs')
        errs('search')

        # ---- GPS path (stubbed geolocation) ----
        clearToasts()
        js("document.getElementById('wxdGps').click()"); time.sleep(1.5)
        note(js("!!HUB.store.state.prefs.weatherLoc"), f'{theme}: GPS sets location')
        errs('gps')

        # ---- close sheet, Daily has NO weather ----
        js("HUB.ui.closeSheet();HUB.showTab('daily');"); time.sleep(2)
        note(js("!document.getElementById('dyWxBody') && !document.getElementById('dyUnit')"), f'{theme}: Daily has no weather card')
        note(js("!!document.getElementById('dyCaps')"), f'{theme}: Daily keeps Time Capsule')
        note('Gym Fuel' in str(js("document.getElementById('view-daily').textContent")), f'{theme}: Daily keeps Gym Fuel')
        errs('daily')
        errs('final')
    finally:
        proc.terminate()

run('dark')
run('light')
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
