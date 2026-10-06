#!/usr/bin/env python3
"""QA: Gym Fuel drawer + live 3D ring — drawer opens right, ring fills live while typing."""
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

def setv(c, fid, val):
    # IIFE-wrapped: repeated top-level const declarations throw across evaluate calls
    return js(c, "(function(){var e=document.getElementById('"+fid+"');if(!e)return 'missing';e.focus();e.value='"+val+"';e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return e.value})()")
def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
def click(c, sel):
    js(c, "(()=>{const el=document.querySelector('%s'); if(el){el.scrollIntoView({block:'center'}); el.click(); return true} return false})()" % sel)
    time.sleep(1.2)

port = 9491
profile = '/tmp/hubqa-gymdr'
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
    time.sleep(2.5)
    js(c, "localStorage.clear()")
    js(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
    c.send('Page.navigate', {'url': BASE})
    for _ in range(30):
        time.sleep(1)
        if js(c, "typeof HUB!=='undefined' && !!HUB.gym && !!HUB.i18n") is True: break
    for _ in range(10):
        js(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        if js(c, "typeof window.__huberr")=='object': break
        time.sleep(1)
    assert js(c, "typeof window.__huberr")=='object', 'error hook did not install'
    js(c, "HUB.showTab('daily')")
    time.sleep(2.0)

    note(js(c, "!!document.getElementById('gySetup')"), 'empty state has setup button')
    click(c, '#gySetup')
    note(js(c, "!!document.getElementById('gyDrawer')"), 'drawer exists after setup click')
    note(js(c, "!!document.getElementById('gyBd')"), 'transparent backdrop exists')
    note(js(c, "document.getElementById('gyDrawer').classList.contains('show')"), 'drawer slid in (show class)')
    note(js(c, "getComputedStyle(document.getElementById('gyBd')).backgroundColor"), 'backdrop bg', js(c, "getComputedStyle(document.getElementById('gyBd')).backgroundColor"))
    note(js(c, "document.getElementById('gyDrawer').getBoundingClientRect().left > 40"), 'drawer docked right, card peeks left')
    shot(c, 'gym-drawer-open')

    # card behind renders draft state with placeholders
    note(js(c, "document.querySelector('.gy-hero [data-gy=\"kcal\"]') !== null"), 'card behind shows draft kcal hook')
    kcal0 = js(c, "document.querySelector('.gy-hero [data-gy=\"kcal\"]').textContent")
    note(kcal0 == '—', 'kcal placeholder before typing', repr(kcal0))
    off0 = js(c, "parseFloat(document.querySelector('.gy-hero [data-gy=\"ring\"]').style.strokeDashoffset || document.querySelector('.gy-hero [data-gy=\"ring\"]').getAttribute('stroke-dashoffset'))")
    C = 2*3.14159*52
    note(abs(off0 - C) < 2, 'ring empty at start (offset≈C)', off0)

    # type age + weight only -> partial ring fill, still placeholder
    setv(c, 'fAge', '25')
    setv(c, 'fW', '180')
    time.sleep(0.8)
    off1 = js(c, "parseFloat(document.querySelector('.gy-hero [data-gy=\"ring\"]').style.strokeDashoffset)")
    note(abs(off1 - C*0.5) < 4, 'ring half-filled green after 2/4 fields', round(off1,1))
    shot(c, 'gym-drawer-typing')

    # complete the form -> numbers tween live
    js(c, "document.getElementById('fFt').value='5'; document.getElementById('fFt').dispatchEvent(new Event('change',{bubbles:true}))")
    js(c, "document.getElementById('fIn').value='11'; document.getElementById('fIn').dispatchEvent(new Event('change',{bubbles:true}))")
    setv(c, 'fT', '190')
    time.sleep(1.2)
    kcal = js(c, "document.querySelector('.gy-hero [data-gy=\"kcal\"]').textContent")
    note(kcal not in ('—','0') and ',' in kcal, 'kcal tweened live behind drawer', repr(kcal))
    prot = js(c, "document.querySelector('.gy-hero [data-gy=\"prot\"]').textContent")
    note(prot not in ('—','0'), 'protein live', repr(prot))
    bmil = js(c, "document.querySelector('.gy-hero [data-gy=\"bmi\"]').textContent")
    note(bmil not in ('—','0'), 'BMI live', repr(bmil))
    off2 = js(c, "parseFloat(document.querySelector('.gy-hero [data-gy=\"ring\"]').style.strokeDashoffset)")
    note(abs(off2) < 2, 'ring full when complete', off2)
    note(js(c, "document.querySelector('.gy-hero .gy-live') !== null"), 'LIVE badge shown')
    note(js(c, "document.querySelector('.gy-hero .gy-sheen') !== null"), 'sheen element present')
    note(js(c, "document.querySelector('.gy-hero .gy-glow') !== null"), 'glow halo present')
    shot(c, 'gym-drawer-live')

    # pulse class fires on update
    setv(c, 'fW', '181')
    time.sleep(0.4)
    note(js(c, "document.querySelector('.gy-hero [data-gy=\"ring\"]').classList.contains('gy-pulse')"), 'ring pulse fires on keystroke')

    # save -> drawer closes, profile persists
    click(c, '#fSave')
    note(js(c, "!document.getElementById('gyDrawer')"), 'drawer removed after save')
    note(js(c, "HUB.gym._draft===null"), 'draft cleared after save')
    saved = js(c, "(JSON.parse(localStorage.getItem('hub_v1')).gym||{}).profile||{}")
    note(isinstance(saved, dict) and saved.get('age') == 25, 'profile saved', str(saved)[:100])
    shot(c, 'gym-drawer-saved')

    # reopen as edit -> prefill + cancel restores
    click(c, '#gyEdit')
    note(js(c, "document.getElementById('fAge').value==='25'"), 'edit prefills age')
    click(c, '#gyX')
    note(js(c, "!document.getElementById('gyDrawer') && HUB.gym._draft===null"), 'cancel closes + clears draft')
    note(js(c, "document.querySelector('.gy-hero [data-gy=\"kcal\"]')!==null && document.querySelector('.gy-hero [data-gy=\"kcal\"]').textContent!=='—'"), 'saved numbers remain after cancel')

    # nepali drawer
    js(c, "HUB.i18n.setLang('ne'); HUB.showTab('daily')")
    time.sleep(1.5)
    click(c, '#gyEdit')
    hint = js(c, "document.querySelector('#gyDrawer .hint').textContent")
    note('प्यानल' in hint or 'नम्बर' in hint, 'nepali draft hint', hint[:60])
    click(c, '#gyX')

    # ---- new features: runner animation, diet, generator, supplements ----
    js(c, "HUB.i18n.setLang('en'); HUB.showTab('daily')")
    time.sleep(1.0)
    note(js(c, "document.querySelectorAll('.gy-run').length>=1"), 'runner svg in card header')
    note(js(c, "document.querySelector('.gy-run .rn-belt')!==null"), 'treadmill belt element')
    note(js(c, "document.body.innerHTML.indexOf('💪')<0"), 'no flexed-arm emoji in gym UI')
    # diet chip -> vegetarian
    click(c, '#gyEdit')
    time.sleep(0.8)
    click(c, "#gyDrawer [data-f=diet][data-v=veg]")
    note(js(c, "HUB.gym._draft.diet==='veg'"), 'diet chip sets draft diet')
    click(c, '#fSave')
    time.sleep(0.8)
    saved = js(c, "(JSON.parse(localStorage.getItem('hub_v1')).gym||{}).profile||{}")
    note(isinstance(saved, dict) and saved.get('diet') == 'veg', 'diet persisted', str(saved.get('diet') if isinstance(saved,dict) else saved))
    # meals sheet: generator
    click(c, '#gyMeals')
    time.sleep(0.8)
    note(js(c, "!!document.getElementById('gyGenBtn')"), 'generator button present')
    note(js(c, "document.querySelector('.gy-gen .chip.on').textContent.indexOf('Vegetarian')>=0"), 'diet chip shown in generator')
    click(c, '#gyGenBtn')
    time.sleep(0.8)
    note(js(c, "document.querySelectorAll('#gyPlan .gy-food').length>=5"), 'plan generated with 5 slots', str(js(c, "document.querySelectorAll('#gyPlan .gy-food').length")))
    note(js(c, "document.querySelector('#gyPlan').textContent.indexOf('Beef')<0 && document.querySelector('#gyPlan').textContent.indexOf('Chicken')<0"), 'veg plan has no meat')
    note(js(c, "document.querySelector('#gyPlan').textContent.indexOf('Not AI')>=0"), 'honest on-device label')
    shot(c, 'gym-gen-plan')
    js(c, "HUB.ui.closeSheet()")
    # supplements sheet
    click(c, '#gySupp')
    time.sleep(0.8)
    for sec in ['Performance', 'Everyday basics', 'Skin & face']:
        note(js(c, "document.body.textContent.indexOf('%s')>=0" % sec), 'supp section: %s' % sec)
    note(js(c, "document.querySelectorAll('.gy-ev').length>=10"), 'evidence badges', str(js(c, "document.querySelectorAll('.gy-ev').length")))
    note(js(c, "document.body.textContent.indexOf('Collagen peptides')>=0"), 'collagen present')
    note(js(c, "document.body.textContent.indexOf('Hyaluronic acid')>=0"), 'hyaluronic acid present')
    note(js(c, "document.body.textContent.indexOf('Caffeine')>=0"), 'caffeine present')
    shot(c, 'gym-supplements')
    js(c, "HUB.ui.closeSheet()")

    errs = js(c, "window.__huberr.join(' | ')")
    note(errs == '', 'zero console errors', errs[:200] if errs else '(no errors)')

    passed = sum(1 for ok, _ in checks if ok); total = len(checks)
    print('\n==== %d/%d drawer QA passed ====' % (passed, total))
finally:
    proc.terminate()
