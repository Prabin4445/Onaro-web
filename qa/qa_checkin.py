#!/usr/bin/env python3
"""QA: Daily tab 'Daily check-in' — form, streak, memory, week strip, i18n, dark."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

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

def click(c, sel):
    js(c, "(()=>{const el=document.querySelector('%s'); if(el){el.scrollIntoView({block:'center'}); el.click(); return true} return false})()" % sel)
    time.sleep(1.0)

port = 9487
profile = '/tmp/hubqa-ck'
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
          "HUB.store.state.checkins={}; HUB.store.save(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('home');")
    time.sleep(1.5)
    click(c, '#tabbar [data-tab="daily"]')
    time.sleep(2)

    # 1. card renders with form (no entry today)
    card = js(c, "document.querySelector('#view-daily').textContent")
    note('Daily check-in' in card, 'check-in card renders', '')
    note('Gas near me' not in card, 'gas card fully gone', '')
    moods = js(c, "document.querySelectorAll('#view-daily [data-ckm]').length")
    note(moods == 5, '5 mood buttons', str(moods))
    note(js(c, "!!document.getElementById('ckNote')"), 'note input present', '')
    note(js(c, "!!document.getElementById('ckSave')"), 'save button present', '')
    shot(c, 'ck-form')

    # 2. save without mood -> rejected
    click(c, '#ckSave')
    time.sleep(0.8)
    note(js(c, "document.body.textContent.includes('Pick a mood first')"), 'mood required before save', '')

    # 3. pick mood 4 (🙂), add note, save
    click(c, '#view-daily [data-ckm="4"]')
    time.sleep(0.5)
    note(js(c, "document.querySelector('#view-daily [data-ckm=\"4\"]').classList.contains('on')"), 'mood 4 selected', '')
    js(c, "document.getElementById('ckNote').value='Test day note'")
    click(c, '#ckSave')
    time.sleep(1.5)
    card2 = js(c, "document.querySelector('#view-daily').textContent")
    note('Good' in card2 and 'Test day note' in card2, 'today entry shows mood + note', card2[:120])
    note('1-day streak' in card2, 'streak starts at 1', '')
    shot(c, 'ck-saved')

    # 4. persists in localStorage
    saved = js(c, "(()=>{try{const s=JSON.parse(localStorage.getItem('hub_v1')); const k=Object.keys(s.checkins||{}); return k.length+'|'+JSON.stringify(s.checkins[k[0]]);}catch(e){return 'ERR:'+e}})()")
    note(saved and saved.startswith('1|') and '"m":4' in saved, 'check-in persists in localStorage', saved[:80])

    # 5. streak across days: seed yesterday + day-before, re-render
    js(c, """(()=>{const e=HUB.store.state.checkins; const k=Object.keys(e)[0];
      const d1=new Date(); d1.setDate(d1.getDate()-1);
      const d2=new Date(); d2.setDate(d2.getDate()-2);
      const f=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
      e[f(d1)]={m:5,note:'yesterday',at:Date.now()}; e[f(d2)]={m:3,note:'',at:Date.now()};
      HUB.store.save(); HUB.showTab('daily');})()""")
    time.sleep(1.5)
    card3 = js(c, "document.querySelector('#view-daily').textContent")
    note('3-day streak' in card3, 'streak counts 3 consecutive days', '')

    # 6. memory: seed 7 days ago, re-render
    js(c, """(()=>{const e=HUB.store.state.checkins;
      const d=new Date(); d.setDate(d.getDate()-7);
      const f=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
      e[f(d)]={m:2,note:'rough week',at:Date.now()-7*864e5};
      HUB.store.save(); HUB.showTab('daily');})()""")
    time.sleep(1.5)
    card4 = js(c, "document.querySelector('#view-daily').textContent")
    note('A week ago' in card4 and 'rough week' in card4, 'memory resurfaces 7-day-old entry', card4[card4.find('past self')-0:][:80] if 'past self' in card4 else '')

    # 7. week strip: 7 cells, today marked
    cells = js(c, "document.querySelectorAll('#view-daily .ckday').length")
    note(cells == 7, '7-day strip', str(cells))
    note(js(c, "!!document.querySelector('#view-daily .ckday.today')"), 'today cell marked', '')

    # 8. tap a past day with entry -> sheet; tap empty day -> no-entry message
    js(c, """(()=>{const ds=[...document.querySelectorAll('#view-daily .ckday')];
      const withMood=ds.find(d=>d.querySelector('.ckmo').textContent.trim()!=='·'&&!d.classList.contains('today'));
      if(withMood) withMood.click();})()""")
    time.sleep(1.2)
    sh = js(c, "document.getElementById('sheetBox').textContent")
    note(sh and ('yesterday' in sh or 'Low' in sh or 'Okay' in sh), 'past day sheet opens with entry', (sh or '')[:70])
    js(c, "try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.6)

    # 9. edit flow: prefilled form
    click(c, '#ckEdit')
    time.sleep(1.2)
    note(js(c, "document.querySelector('#view-daily [data-ckm=\"4\"]').classList.contains('on')"), 'edit prefills mood 4', '')
    note(js(c, "document.getElementById('ckNote').value"), 'edit prefills note', '')
    # change to mood 5 and save
    click(c, '#view-daily [data-ckm="5"]')
    click(c, '#ckSave')
    time.sleep(1.2)
    note('Amazing' in js(c, "document.querySelector('#view-daily').textContent"), 'edit updates mood to Amazing', '')

    # 10. Nepali
    js(c, "HUB.i18n.setLang('ne')"); time.sleep(1.2)
    js(c, "HUB.showTab('daily')"); time.sleep(1.5)
    neh = js(c, "document.querySelector('#view-daily').textContent")
    note('दैनिक चेक-इन' in neh, 'Nepali title', '')
    note('एक हप्ता अघि' in neh or 'तपाईंको विगतको आत्म' in neh, 'Nepali memory label', '')
    shot(c, 'ck-ne')
    js(c, "HUB.i18n.setLang('en')"); time.sleep(1)

    # 11. dark mode + errors
    js(c, "document.body.classList.add('dark')"); time.sleep(0.8)
    js(c, "HUB.showTab('daily')"); time.sleep(1.5)
    shot(c, 'ck-dark')
    errs = js(c, "window.__huberr.join(' | ')")
    note(not errs, 'zero console errors', (errs or '')[:250])

    print('\n%d/%d passed' % (sum(1 for ok, _ in checks if ok), len(checks)))
finally:
    proc.terminate()
