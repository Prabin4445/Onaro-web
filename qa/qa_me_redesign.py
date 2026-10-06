#!/usr/bin/env python3
"""ME tab glossy-3D redesign smoke QA: dark 390/320 + light 390 + rose-theme,
console-error siphon, element assertions. No app changes."""
import json, subprocess, time, urllib.request, base64, os, shutil, sys
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import CDP
CHROME='/opt/meta-chromium/chrome'; BASE='file:///home/hatch/workspace/hub/index.html'
OUT='/home/hatch/workspace/hub/qa'; PORT=9471; PROF='/tmp/hubqa-me-redesign'

def launch():
    shutil.rmtree(PROF, ignore_errors=True)
    proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
        f'--remote-debugging-port={PORT}','--remote-allow-origins=*',f'--user-data-dir={PROF}',
        '--hide-scrollbars','--allow-file-access-from-files',BASE],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list',timeout=3) as r: ts=json.load(r)
            tgt=next(x for x in ts if x['type']=='page' and 'devtools' not in x['url']); break
        except Exception: continue
    c=CDP(tgt['webSocketDebuggerUrl']); c.send('Runtime.enable'); c.send('Page.enable')
    time.sleep(4); return proc,c

def js(c,e):
    r=c.send('Runtime.evaluate',{'expression':e,'returnByValue':True,'awaitPromise':True})
    return (r or {}).get('result',{}).get('value')

def viewport(c,w,h):
    c.send('Emulation.setDeviceMetricsOverride',{'width':w,'height':h,'deviceScaleFactor':1,'mobile':True})

def shot(c,name):
    # scroll top->bottom so loading="lazy" icons actually fetch, then capture
    js(c,"window.scrollTo(0,0)"); time.sleep(0.4)
    js(c,"""(()=>new Promise(res=>{let y=0;const h=document.documentElement.scrollHeight;
      const t=setInterval(()=>{y+=700;window.scrollTo(0,y);if(y>=h){clearInterval(t);res();}},160);}))()""")
    time.sleep(1.2); js(c,"window.scrollTo(0,0)"); time.sleep(0.4)
    r=None; err=None
    for attempt in range(3):
        try:
            r=c.send('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True})
            break
        except Exception as e:
            err=e; time.sleep(2)
    if r is None:
        raise TimeoutError('captureScreenshot x3: '+str(err)[:80])
    p=os.path.join(OUT,name); open(p,'wb').write(base64.b64decode(r['data'])); print('SHOT',p); return p

def main():
    proc,c=launch()
    # seed returning-user i18n prefs BEFORE boot reads them, then reload so the
    # boot watchdog (15s) clears via HUB.safe.booted() instead of showing the
    # recovery overlay in late screenshots
    js(c,"try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))}catch(e){}")
    js(c,"location.reload()"); time.sleep(6)
    c.send('Runtime.enable')
    booted=js(c,"!!(window.HUB&&HUB.safe&&HUB.safe.isBooted&&HUB.safe.isBooted())")
    print('boot watchdog cleared:', booted)
    fails=[]
    def check(name,ok,detail=''):
        print(('PASS ' if ok else 'FAIL ')+name+(' '+str(detail)[:100] if detail else ''))
        if not ok: fails.append(name)
    # seed: profile + error siphon + hide welcome
    js(c,"window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
    js(c,"try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    js(c,"document.body.classList.add('dark')"); time.sleep(0.8)
    js(c,"HUB.showTab('me')"); time.sleep(2.2)
    # fresh signed-out profile -> the auth front door opens the login overlay;
    # __gateSkip is the app's own "explore without signing in" QA seam
    js(c,"window.__gateSkip=true; try{if(HUB.auth&&HUB.auth.close)HUB.auth.close()}catch(e){}"); time.sleep(0.6)

    # element assertions (dark)
    ids=['meEditBtn','ringList','darkToggle','soundToggle','pushToggle','verifyBtn','meScoreStrip','clearSamples','meLangBtn','meCountryBtn','resetAll','meReport','meModQ','meBlocked','meSkillAdd','meCampusBtn']
    missing=js(c,"(()=>["+",".join("'#%s'"%i for i in ids)+"].filter(s=>!document.querySelector(s)))()")
    check('all key elements present', not missing, str(missing))
    acct=js(c,"!!(document.getElementById('acLogin')||document.getElementById('acLogout'))")
    check('auth account card (login/logout) present', bool(acct))
    groups=js(c,"document.querySelectorAll('.me-setgroup').length")
    check('3 settings groups', groups==3, str(groups))
    sicos=js(c,"document.querySelectorAll('.me-setico').length")
    check('settings row icons rendered', sicos>=7, str(sicos))
    hero=js(c,"(()=>{const h=document.querySelector('#view-me .me-hero');if(!h)return 'missing';const r=h.getBoundingClientRect();return r.width>300&&r.top>=0?'ok':'bad:'+JSON.stringify(r);})()")
    check('hero banner rect sane @390', hero=='ok', str(hero))
    ringrows=js(c,"document.querySelectorAll('#ringList .ringrow').length")
    check('ringtone rows rendered', ringrows>=3, str(ringrows))

    viewport(c,390,844); time.sleep(0.6)
    shot(c,'me-redesign-dark-390.png')
    viewport(c,320,568); time.sleep(0.6)
    ovf=js(c,"document.documentElement.scrollWidth<=322")
    check('no horizontal overflow @320', bool(ovf), str(js(c,"document.documentElement.scrollWidth")))
    shot(c,'me-redesign-dark-320.png')

    # rose gender theme (female -> theme-rose), keep logic untouched
    viewport(c,390,844)
    js(c,"HUB.store.state.profile.gender='female';HUB.store.save();HUB.applyTheme();HUB.views.me.render(document.getElementById('view-me'))")
    time.sleep(1.2)
    rose=js(c,"document.body.classList.contains('theme-rose')")
    check('female profile -> theme-rose', bool(rose))
    acc=js(c,"getComputedStyle(document.body).getPropertyValue('--accent').trim()")
    check('accent is rose (not volt)', acc.lower() not in ('#c6f135','#d4f53f'), acc)
    shot(c,'me-redesign-dark-390-rose.png')
    js(c,"HUB.store.state.profile.gender='male';HUB.store.save();HUB.applyTheme();HUB.views.me.render(document.getElementById('view-me'))")
    time.sleep(1.0)
    back=js(c,"!document.body.classList.contains('theme-rose')")
    check('male profile -> volt restored', bool(back))

    # edit-profile sheet opens + renders
    js(c,"document.getElementById('meEditBtn').click()"); time.sleep(1.0)
    sheetok=js(c,"(()=>{const s=document.getElementById('sheetHost');return !s.hidden&&!!document.getElementById('peditSave');})()")
    check('edit-profile sheet opens', bool(sheetok))
    shot(c,'me-redesign-edit-sheet.png')
    js(c,"try{HUB.ui.closeSheet()}catch(e){}"); time.sleep(0.6)

    # score explainer sheet
    js(c,"document.getElementById('meScoreStrip').click()"); time.sleep(0.8)
    scok=js(c,"!document.getElementById('sheetHost').hidden")
    check('safety-score explainer opens', bool(scok))
    js(c,"try{HUB.ui.closeSheet()}catch(e){}"); time.sleep(0.6)

    # light mode
    js(c,"HUB.store.state.prefs.dark=false;HUB.store.save();HUB.applyTheme()"); time.sleep(1.0)
    shot(c,'me-redesign-light-390.png')
    lightbg=js(c,"getComputedStyle(document.body).backgroundColor")
    print('light body bg:', lightbg)

    errs=js(c,"window.__huberr.splice(0)")
    check('zero console errors', not errs, str(errs)[:200])
    proc.terminate()
    print('==== done:', 'FAILURES: '+','.join(fails) if fails else 'ALL GREEN')

main()
