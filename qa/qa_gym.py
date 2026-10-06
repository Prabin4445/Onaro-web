#!/usr/bin/env python3
"""QA: Gym Fuel — setup, math, meals, supplements, progress report, i18n, dark."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:150])

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

port = 9489
profile = '/tmp/hubqa-gym'
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
          "delete HUB.store.state.gym; HUB.store.save(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
    time.sleep(2)

    # 1. empty state
    card = js(c, "document.querySelector('#view-daily').textContent")
    note('Gym Fuel' in card, 'gym card renders', '')
    note('Set up my plan' in card, 'setup empty state', '')
    note('Daily check-in' not in card and 'Gas near me' not in card, 'check-in + gas fully gone', '')
    shot(c, 'gym-setup')

    # 2. open setup, fill: male 25y 180lb 5'11" moderate gain target 190lb
    click(c, '#gySetup'); time.sleep(1)
    js(c, "document.getElementById('fAge').value='25'; document.getElementById('fW').value='180';"
          "document.getElementById('fT').value='190';"
          "document.getElementById('fFt').value='5'; document.getElementById('fIn').value='11';")
    # goal: click 'Build muscle' chip (3rd goal chip)
    js(c, "[...document.querySelectorAll('#sheetBox [data-f=\"goal\"]')].forEach(b=>{if(b.textContent.includes('Build muscle'))b.click()})")
    time.sleep(0.4)
    click(c, '#fSave'); time.sleep(2)

    # 3. verify math independently: 25M, 81.6466kg, 180.34cm, moderate 1.55, gain +300
    exp = js(c, """(function(){
      const wKg=180/2.20462, hCm=(5*12+11)*2.54;
      const bmr=10*wKg+6.25*hCm-5*25+5, tdee=bmr*1.55, cal=Math.round(tdee+300);
      const prot=Math.round(2.0*wKg), fat=Math.round(cal*0.25/9), carbs=Math.round((cal-prot*4-fat*9)/4);
      return cal+'|'+prot+'|'+fat+'|'+carbs+'|'+(wKg/Math.pow(hCm/100,2)).toFixed(1);
    })()""")
    card2 = js(c, "document.querySelector('#view-daily').textContent")
    ec, ep, ef, ecb, ebmi = exp.split('|')
    note(ec in card2, 'calorie target = %s' % ec, exp)
    note(ep + ' g' in card2 or ('Protein' in card2 and ep in card2), 'protein = %sg' % ep, '')
    note(ef in card2 and ecb in card2, 'fat/carbs = %s/%s' % (ef, ecb), '')
    note(ebmi in card2, 'BMI = %s' % ebmi, '')
    note('Overweight' in card2, 'BMI honestly labeled Overweight (muscular case)', '')
    note('Add measurements' in card2, 'body-fat prompts for measurements', '')
    shot(c, 'gym-card')

    # 4. add measurements via edit: neck 15in waist 32in -> Navy ~13%
    click(c, '#gyEdit'); time.sleep(1)
    js(c, "document.getElementById('fNeck').value='15'; document.getElementById('fW').value='180';"
          "document.getElementById('fWaist').value='32'; document.getElementById('fAge').value='25';"
          "document.getElementById('fT').value='190'; document.getElementById('fFt').value='5'; document.getElementById('fIn').value='11';")
    js(c, "[...document.querySelectorAll('#sheetBox [data-f=\"goal\"]')].forEach(b=>{if(b.textContent.includes('Build muscle'))b.click()})")
    time.sleep(0.3)
    click(c, '#fSave'); time.sleep(2)
    card3 = js(c, "document.querySelector('#view-daily').textContent")
    bfexp = js(c, """(function(){
      const l10=x=>Math.log(x)/Math.LN10, hCm=(5*12+11)*2.54;
      const d=495/(1.0324-0.19077*l10(32*2.54-15*2.54)+0.15456*l10(hCm))-450;
      return d.toFixed(1);
    })()""")
    note(bfexp + '%' in card3, 'Navy body fat = %s%%' % bfexp, bfexp)

    # 5. meals sheet
    click(c, '#gyMeals'); time.sleep(1.2)
    mh = js(c, "document.getElementById('sheetBox').textContent")
    note('Fuel day' in mh and 'Build muscle' in mh, 'meals sheet for gain goal', mh[:60])
    note('Overnight Oats' in mh or 'overnight oats' in mh, 'gain breakfast shown', '')
    note('Power Overnight Oats' in mh and 'Red Lentil Dal' in mh, 'recipes listed', '')
    note('≈' in mh, 'estimates marked with ≈', '')
    js(c, "try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.6)

    # 6. supplements sheet
    click(c, '#gySupp'); time.sleep(1.2)
    sh = js(c, "document.getElementById('sheetBox').textContent")
    note('Creatine monohydrate' in sh and 'Whey protein' in sh, 'supplement cards', '')
    note('not a steroid' in sh or 'not medical advice' in sh, 'honest supplement framing', sh[sh.find('Supplements are'):sh.find('Supplements are')+60] if 'Supplements are' in sh else '')
    js(c, "try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.6)

    # 7. info button (BMI)
    js(c, "[...document.querySelectorAll('#view-daily [data-info=\"bmi\"]')].forEach(b=>b.click())")
    time.sleep(1)
    ih = js(c, "document.getElementById('sheetBox').textContent")
    note('Body Mass Index' in ih, '(i) info sheet opens', ih[:60])
    js(c, "try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.6)

    # 8. progress: seed 14d + 7d logs, save today -> trend +1lb/wk -> on pace for gain
    js(c, """(()=>{const g=HUB.store.state.gym;
      const f=d=>{const t=new Date();t.setDate(t.getDate()-d);return t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0');};
      g.logs=[{d:f(14),w:178/2.20462,waist:0},{d:f(7),w:179/2.20462,waist:0}]; HUB.store.save();})()""")
    click(c, '#gyProg'); time.sleep(1)
    js(c, "document.getElementById('gW').value='180'")
    click(c, '#gSaveLog'); time.sleep(1.5)
    rh = js(c, "document.getElementById('sheetBox').textContent")
    note('On pace' in rh, 'report verdict: on pace for lean gain', rh[rh.find('On pace')-40:rh.find('On pace')+40] if 'On pace' in rh else rh[:100])
    note('Work on this' in rh, 'focus list present', '')
    note(js(c, "!!document.querySelector('#sheetBox .gy-line')"), 'trend chart renders', '')
    shot(c, 'gym-report')
    js(c, "try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.6)

    # 9. unit toggle -> metric
    click(c, '#gyUnit'); time.sleep(1.5)
    card4 = js(c, "document.querySelector('#view-daily').textContent")
    note('82 kg' in card4 or '81.6 kg' in card4, 'metric weight display', card4[card4.find('Gym Fuel'):card4.find('Gym Fuel')+200])
    click(c, '#gyUnit'); time.sleep(1.2)  # back to imperial

    # 10. Nepali
    js(c, "HUB.i18n.setLang('ne')"); time.sleep(1)
    js(c, "HUB.showTab('daily')"); time.sleep(2)
    neh = js(c, "document.querySelector('#view-daily').textContent")
    note('जिम फ्यूल' in neh, 'Nepali title', '')
    shot(c, 'gym-ne')
    js(c, "HUB.i18n.setLang('en')"); time.sleep(1)

    # 11. dark + errors
    js(c, "document.body.classList.add('dark')"); time.sleep(0.6)
    js(c, "HUB.showTab('daily')"); time.sleep(2)
    shot(c, 'gym-dark')
    errs = js(c, "window.__huberr.join(' | ')")
    note(not errs, 'zero console errors', (errs or '')[:250])

    print('\n%d/%d passed' % (sum(1 for ok, _ in checks if ok), len(checks)))
finally:
    proc.terminate()
