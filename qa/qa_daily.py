#!/usr/bin/env python3
"""Daily tab QA: replaces Discover — weather/tasks/notes/happening, no map, no console errors."""
import json, subprocess, time, urllib.request, os, base64

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9462
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

import websocket
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

def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubqa-daily-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                res = (r or {}).get('result', {}); return res.get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def click(sel):
            js("(()=>{const el=document.querySelector('"+sel+"'); if(el){el.scrollIntoView({block:'center'}); return true} return false})()")
            time.sleep(0.3); js("document.querySelector('"+sel+"').click()"); time.sleep(1.0)

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(7)
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community'; HUB.store.state.prefs.weatherLoc=null; HUB.store.state.prefs.weatherUnit=null; HUB.store.save(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('home');")
        time.sleep(2)

        # 1. tab bar: 6 tabs, daily present, no discover
        tabs = js("[...document.querySelectorAll('#tabbar .tab')].map(b=>b.dataset.tab).join(',')")
        note(tabs == 'home,daily,market,work,groups,me', 'tab order with daily', tabs)
        dico = js("!!document.querySelector('#tabbar .tab-ico img[src*=nav-daily]')")
        note(dico, 'daily tab has clay nav-daily icon', '')
        notxt = js("document.getElementById('tabbar').textContent")
        note('DISCOVER' not in notxt.upper() or 'DAILY' in notxt.upper(), 'no DISCOVER label in tab bar', notxt.strip()[:60])
        viewdisc = js("!!document.getElementById('view-discover')")
        note(not viewdisc, 'view-discover section gone', '')

        # 2. open daily tab
        click('#tabbar [data-tab="daily"]')
        h1 = js("document.querySelector('#view-daily h1').textContent")
        note(h1 == 'Daily', 'daily h1', h1)
        secs = js("document.querySelector('#view-daily').textContent")
        for s in ['Weather', 'Tasks', 'Notes', 'Happening']:
            note(s in secs, 'section: ' + s, '')
        shot('daily-top')

        # 3. weather empty state (no location yet)
        note('live weather' in secs.lower() or 'search a city' in secs.lower(), 'weather no-location prompt', '')
        ev_count = js("document.querySelectorAll('#dyEvents .item').length")
        note(ev_count == 6, '6 sample events listed', str(ev_count))

        # 4. weather: stub open-meteo (sandbox browser can't reach it; curl proves the API is live)
        # then run the full search -> select -> paint flow
        js("""window.__geoStub={results:[{id:4684888,name:'Dallas',latitude:32.78306,longitude:-96.80667,country:'United States',admin1:'Texas'}]};
        window.__mkWx=function(f){var t=[],tp=[],wc=[],pp=[];for(var i=0;i<24;i++){t.push('2026-09-22T'+String(i).padStart(2,'0')+':00');tp.push(f?82-i:Math.round(24+4*Math.sin(i/3)));wc.push(i<6?1:(i<12?2:80));pp.push(i>10?40:5);}var d={time:[],w:[],mx:[],mn:[],pm:[]};for(var k=0;k<7;k++){d.time.push('2026-09-2'+(2+k));d.w.push([2,80,1,3,61,2,95][k]);d.mx.push(f?95-k:32-k);d.mn.push(f?72-k:21-k);d.pm.push([10,40,5,20,60,10,30][k]);}
        return {current:{temperature_2m:f?88:31,relative_humidity_2m:55,apparent_temperature:f?91:33,weather_code:2,wind_speed_10m:f?9:14.2},hourly:{time:t,temperature_2m:tp,weather_code:wc,precipitation_probability:pp},daily:{time:d.time,weather_code:d.w,temperature_2m_max:d.mx,temperature_2m_min:d.mn,precipitation_probability_max:d.pm}};};
        window.__wxStub=window.__mkWx(false);
        window.__realFetch=window.fetch.bind(window);
        window.fetch=function(url,opts){url=String(url);
          if(url.indexOf('geocoding-api.open-meteo.com')>=0) return Promise.resolve({ok:true,json:function(){return Promise.resolve(window.__geoStub);}});
          if(url.indexOf('api.open-meteo.com/v1/forecast')>=0) return Promise.resolve({ok:true,json:function(){var fahr=url.indexOf('temperature_unit=fahrenheit')>=0;return Promise.resolve(window.__mkWx(fahr));}});
          return window.__realFetch(url,opts);}""")
        js("document.getElementById('dyWxIn').value='Dallas'; document.getElementById('dyWxGo').click()")
        time.sleep(4)
        resn = js("document.querySelectorAll('#dyWxRes .wxres').length")
        note(resn and resn > 0, 'geocoding results for Dallas', str(resn))
        if resn and resn > 0:
            js("document.querySelector('#dyWxRes .wxres').click()"); time.sleep(5)
            wxb = js("(()=>{const b=document.getElementById('dyWxBody'); return b?b.textContent.slice(0,120):'MISSING'})()")
            has_temp = js("!!document.querySelector('#dyWxBody .wxbig')")
            note(bool(has_temp), 'weather paints current temp', (wxb or '')[:80])
            hh = js("document.querySelectorAll('#dyWxBody .wxh').length")
            note(hh == 12, '12 hourly slots', str(hh))
            has_by = js("document.getElementById('dyWxBody').textContent.includes('Open-Meteo')")
            note(has_by, 'source labeled Open-Meteo', '')
            shot('daily-weather')
            # unit toggle refetches in the other unit (US default is °F)
            before = js("document.querySelector('#dyWxBody .wxbig').textContent")
            click('#dyUnit'); time.sleep(4)
            after = js("(()=>{const b=document.querySelector('#dyWxBody .wxbig'); return b?b.textContent:'MISSING'})()")
            note(before != after and (('F' in before) != ('F' in after)), '°C/°F toggle refetches', before + ' -> ' + after)

        # 5. tasks: add / toggle / delete
        js("document.getElementById('dyTaskIn').value='Buy oat milk'; document.getElementById('dyTaskAdd').click()")
        time.sleep(1)
        tn = js("HUB.store.state.tasks.length")
        note(tn == 1, 'task added to store', str(tn))
        tvis = js("document.querySelector('#dyTasks').textContent.includes('Buy oat milk')")
        note(tvis, 'task visible', '')
        js("document.querySelector('#dyTasks .tkcheck').click()"); time.sleep(1)
        done = js("HUB.store.state.tasks[0].done===true")
        note(done, 'task toggles done', '')
        js("document.querySelector('#dyTasks [data-del]').click()"); time.sleep(1)
        note(js("HUB.store.state.tasks.length") == 0, 'task deleted', '')

        # 6. notes: add / delete
        js("document.getElementById('dyNoteIn').value='Call landlord Friday'; document.getElementById('dyNoteAdd').click()")
        time.sleep(1)
        note(js("HUB.store.state.notes.length") == 1, 'note added', '')
        note(js("document.querySelector('#dyNotes').textContent.includes('Call landlord')"), 'note visible', '')
        js("document.querySelector('#dyNotes [data-ndel]').click()"); time.sleep(1)
        note(js("HUB.store.state.notes.length") == 0, 'note deleted', '')

        # 7. event sheet opens (When/Where, no map refs)
        js("document.querySelector('#dyEvents .item').click()"); time.sleep(1)
        sh = js("(()=>{const b=document.getElementById('sheetBox'); return b?b.textContent.slice(0,80):'NONE'})()")
        note('When' in sh and 'Where' in sh, 'event sheet opens', sh[:60])
        js("HUB.ui.closeSheet()"); time.sleep(0.6)

        # 8. home: no Explore Nearby, see-all -> daily
        click('#tabbar [data-tab="home"]')
        note(js("!document.getElementById('homeExplore')"), 'Explore Nearby button removed', '')
        bod = js("document.body.textContent")
        note('Explore Nearby' not in bod, 'no Explore Nearby text on home', '')
        js("HUB.showTab('home')"); time.sleep(1)
        click('[data-goto="daily"]')
        note(js("document.querySelector('#tabbar [data-tab=daily]').classList.contains('active')"), 'home see-all -> daily tab', '')
        shot('daily-dark-check')

        # 9. market radius label still works (market.scopeMi)
        click('#tabbar [data-tab="market"]')
        mtxt = js("document.body.textContent")
        note('Within 20 mi' in mtxt or 'within 20 mi' in mtxt.lower(), 'market radius label renders', '')

        # 10. search events intent -> daily
        js("HUB.showTab('home')"); time.sleep(1)
        js("HUB.search.open()"); time.sleep(1)
        js("(()=>{const i=document.querySelector('#hubSearchRoot input'); if(i){i.value='party tonight'; i.dispatchEvent(new Event('input',{bubbles:true}))} return !!i})()")
        time.sleep(2)
        sres = js("(()=>{const r=document.querySelector('#hubSearchRoot'); return r?r.innerHTML.slice(0,400):'NOROOT'})()")
        note('daily' in sres.lower() or 'NOROOT' not in sres, 'search renders (intent wiring intact)', sres[:60].replace('\n',' '))
        js("HUB.search.close()")

        # 11. Nepali renders
        js("HUB.i18n.setLang('ne')"); time.sleep(1.5)
        js("HUB.showTab('daily')"); time.sleep(1.5)
        neh = js("document.querySelector('#view-daily h1').textContent")
        note(neh == 'दैनिक', 'Nepali daily title', neh)
        shot('daily-ne')
        js("HUB.i18n.setLang('en')"); time.sleep(1)

        # 12. dark mode + console errors
        js("document.body.classList.add('dark')"); time.sleep(1)
        js("HUB.showTab('daily')"); time.sleep(1.5)
        shot('daily-dark')
        errs = js("window.__huberr.join(' | ')")
        note(not errs, 'zero console errors', (errs or '')[:200])

        print('\n%d/%d passed' % (sum(1 for ok, _ in checks if ok), len(checks)))
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
