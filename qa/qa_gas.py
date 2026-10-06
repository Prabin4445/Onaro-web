#!/usr/bin/env python3
"""QA: Daily tab 'Gas near me' — stations, miles, directions, EIA avg, reports, i18n, dark."""
import json, subprocess, time, urllib.request, os, base64, math
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []

def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:160])

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 20
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

def js(c, expr):
    try:
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
        return (r or {}).get('result', {}).get('value')
    except Exception as e: return 'JSERR:' + str(e)[:120]

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)

def waitfor(c, expr, timeout=25):
    for _ in range(timeout * 2):
        v = js(c, expr)
        if v: return v
        time.sleep(0.5)
    return None

def click(c, sel):
    js(c, "(()=>{const el=document.querySelector('%s'); if(el){el.scrollIntoView({block:'center'}); el.click(); return true} return false})()" % sel)
    time.sleep(1.0)

def havmi(a, b, c2, d):
    p = math.pi / 180; x = (c2 - a) * p; y = (d - b) * p
    h = math.sin(x / 2) ** 2 + math.cos(a * p) * math.cos(c2 * p) * math.sin(y / 2) ** 2
    return round(2 * 3958.8 * math.asin(math.sqrt(h)), 1)

port = 9481
profile = '/tmp/hubqa-gas'
subprocess.run(['rm', '-rf', profile])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox',
    '--remote-debugging-port=%d' % port, '--remote-allow-origins=*', '--window-size=414,900',
    '--user-data-dir=%s' % profile, '--hide-scrollbars', '--allow-file-access-from-files',
    '--use-angle=swiftshader', '--enable-unsafe-swiftshader', BASE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    tgt = None
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen('http://localhost:%d/json/list' % port, timeout=3) as r:
                ts = json.load(r)
            tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
        except Exception: continue
    assert tgt, 'no target'
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
    js(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
    js(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
    c.send('Page.navigate', {'url': BASE}); time.sleep(7)
    js(c, "var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community';"
          "HUB.store.state.prefs.gasLoc={name:'Dallas, TX',lat:32.78306,lon:-96.80667}; HUB.store.save();"
          "try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('home');")
    time.sleep(1.5)

    # stub external fetches (sandbox browser egress is limited); EIA JSON loads from disk for real
    js(c, """window.__realFetch=window.fetch.bind(window);
    window.__stations={elements:[
      {type:'node',id:1,lat:32.79,lon:-96.81,tags:{name:'Exxon',amenity:'fuel'}},
      {type:'node',id:2,lat:32.77,lon:-96.80,tags:{name:'Shell',amenity:'fuel'}},
      {type:'node',id:3,lat:32.80,lon:-96.82,tags:{name:'QuikTrip #1234',amenity:'fuel'}}
    ]};
    window.fetch=function(url,opts){url=String(url);
      if(url.indexOf('nominatim.openstreetmap.org/reverse')>=0) return Promise.resolve({ok:true,json:function(){return Promise.resolve({address:{'ISO3166-2-lvl4':'US-TX'}});}});
      if(url.indexOf('overpass')>=0) return Promise.resolve({ok:true,json:function(){return Promise.resolve(window.__stations);}});
      return window.__realFetch(url,opts);}""")

    # 1. open daily, gas card present
    click(c, '#tabbar [data-tab="daily"]')
    time.sleep(3)
    gsec = js(c, "(()=>{const h=document.querySelector('#view-daily').textContent; return h.includes('Gas near me') && h.includes('⛽');})()")
    note(gsec, 'gas card renders on Daily')
    shot(c, 'gas-card')

    # 2. EIA average row: Texas state average $3.81, week ending 2026-09-14
    avg = js(c, "document.getElementById('dyGasAvg').textContent")
    note(avg and '$3.81' in avg, 'Texas regular EIA avg $3.81', (avg or '')[:100])
    note(avg and 'Texas state average' in avg, 'labeled Texas state average', (avg or '')[:100])
    note(avg and 'Sep 14, 2026' in avg, 'week-ending date shown', (avg or '')[:100])
    note(avg and 'Regular' not in avg or 'Regular' in avg, 'avg box non-empty', (avg or '')[:60])

    # 3. stations: 3 rows, sorted by distance, miles match haversine
    rows = js(c, "[...document.querySelectorAll('#dyGasList .item')].map(r=>r.textContent)")
    note(len(rows or []) == 3, '3 station rows', str(len(rows or [])))
    if rows:
        note('Exxon' in rows[0], 'nearest station first (Exxon)', rows[0][:60])
        LAT, LON = 32.78306, -96.80667
        exp = {'Exxon': havmi(LAT, LON, 32.79, -96.81), 'Shell': havmi(LAT, LON, 32.77, -96.80), 'QuikTrip #1234': havmi(LAT, LON, 32.80, -96.82)}
        for name, mi in exp.items():
            s = '%.1f mi' % mi
            found = any(name in r and s in r for r in rows)
            note(found, 'miles accurate: %s %s' % (name, s), str([r[:50] for r in rows]))

    # 4. directions link -> google maps with coords
    href = js(c, "document.querySelector('#dyGasList a[href*=google]').getAttribute('href')")
    note(href and href.startswith('https://www.google.com/maps/dir/?api=1&destination='), 'google maps directions link', (href or '')[:90])
    note(href and '32.79,-96.81' in href, 'destination = station coords', (href or '')[:90])

    # 5. grade chip -> diesel: Gulf Coast regional average $6.03
    click(c, '#view-daily [data-gg="diesel"]')
    time.sleep(2.5)
    davg = js(c, "document.getElementById('dyGasAvg').textContent")
    note(davg and '$6.03' in davg, 'diesel EIA avg $6.03', (davg or '')[:100])
    note(davg and 'Gulf Coast regional average' in davg, 'labeled Gulf Coast regional average', (davg or '')[:100])

    # 6. report flow: open sheet, note says device-only, save $3.59
    click(c, '#view-daily [data-gg="regular"]')
    time.sleep(2)
    click(c, '#dyGasList [data-grep]')
    time.sleep(1)
    sh = js(c, "document.getElementById('sheetBox').textContent")
    note(sh and 'Report price' in sh, 'report sheet opens', (sh or '')[:60])
    note(sh and 'only on this device' in sh, 'sheet says device-only (no false sharing)', (sh or '')[:80])
    js(c, "document.getElementById('gpVal').value='3.59'")
    click(c, '#gpSave')
    time.sleep(1.5)
    rows2 = js(c, "[...document.querySelectorAll('#dyGasList .item')].map(r=>r.textContent)")
    note(rows2 and any('$3.59' in r and 'reported' in r for r in rows2), 'reported price $3.59 saved, marked reported', str([r[:70] for r in rows2 or []]))

    # 7. invalid price rejected
    click(c, '#dyGasList [data-grep]')
    time.sleep(1)
    js(c, "document.getElementById('gpVal').value='0'")
    click(c, '#gpSave')
    time.sleep(1)
    toast = js(c, "document.body.textContent.includes('valid price')")
    note(toast, 'invalid price (0) rejected with message', '')
    js(c, "try{HUB.ui.closeSheet();}catch(e){}")

    # 8. persists in localStorage
    saved = js(c, "(()=>{try{const s=JSON.parse(localStorage.getItem('hub_v1')); const k=Object.keys(s.gasReports||{}); return k.length+' keys: '+k.join(',');}catch(e){return 'ERR:'+e}})()")
    note(saved and saved.startswith('1 keys'), 'report persists in localStorage', saved)

    # 9. Nepali
    js(c, "HUB.i18n.setLang('ne')"); time.sleep(1.5)
    js(c, "HUB.showTab('daily')"); time.sleep(2.5)
    neh = js(c, "document.querySelector('#view-daily').textContent.includes('नजिकैको पेट्रोल')")
    note(neh, 'Nepali gas title', '')
    click(c, '#dyGasList [data-grep]'); time.sleep(1)
    nesh = js(c, "document.getElementById('sheetBox').textContent")
    note(nesh and 'केवल यही उपकरणमा' in nesh, 'Nepali report note is device-only', (nesh or '')[:60])
    js(c, "try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.6)
    shot(c, 'gas-ne')
    js(c, "HUB.i18n.setLang('en')"); time.sleep(1)

    # 10. dark mode + console errors
    js(c, "document.body.classList.add('dark')"); time.sleep(1)
    js(c, "HUB.showTab('daily')"); time.sleep(2)
    shot(c, 'gas-dark')
    errs = js(c, "window.__huberr.join(' | ')")
    note(not errs, 'zero console errors', (errs or '')[:250])

    print('\n%d/%d passed' % (sum(1 for ok, _ in checks if ok), len(checks)))
finally:
    proc.terminate()
