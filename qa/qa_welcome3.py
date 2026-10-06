#!/usr/bin/env python3
"""QA for the 3-step welcome flow (language -> country -> disclaimer+continue).
Fresh profiles, REAL onboarding (no seeding past it), dark + light, 390x844."""
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H, CDP

OUT = '/home/hatch/workspace/hub/qa'
passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS ' + name + (' ' + str(detail)[:90] if detail else ''))
    else: failed += 1; print('FAIL ' + name + ' ' + str(detail)[:160])

def in_viewport(h, sel):
    return h.js("(()=>{const e=document.querySelector('%s');if(!e)return 'missing';const r=e.getBoundingClientRect();return JSON.stringify({t:Math.round(r.top),b:Math.round(r.bottom),l:Math.round(r.left),r:Math.round(r.right),ih:innerHeight,iw:innerWidth});})()" % sel)

def run(theme, port, profile):
    global passed, failed
    h = H(port, profile)
    try:
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        if theme == 'dark': h.js("document.body.classList.add('dark')")
        else: h.js("document.body.classList.remove('dark')")
        h.js("HUB.ui.closeSheet&&HUB.ui.closeSheet()")
        time.sleep(1)
        # fresh profile -> welcome overlay must show automatically
        vis = h.js("(()=>{const w=document.getElementById('wlcmHost');return w&&!w.hidden})()")
        check(f'{theme}: welcome host visible on fresh boot', vis is True, vis)
        # ---- STEP 1: language screen
        s1 = h.js("(()=>{const b=document.getElementById('wlcmBody');return b&&!!b.querySelector('.wlcm-langs')&&!!b.querySelector('[data-wlang=\"es\"]')})()")
        check(f'{theme}: step1 language screen shown', s1 is True, s1)
        nogo1 = h.js("(()=>{const b=document.getElementById('wlcmBody');return b&&!b.querySelector('#wlcmGo')})()")
        check(f'{theme}: step1 has NO Continue button', nogo1 is True, nogo1)
        dots = h.js("(()=>[...document.querySelectorAll('.wlcm-dot')].map(d=>d.className))()")
        check(f'{theme}: 3 step dots, first active', isinstance(dots, list) and len(dots) == 3 and 'on' in dots[0], dots)
        v1 = json.loads(in_viewport(h, '.wlcm-card'))
        check(f'{theme}: step1 card within viewport', v1['t'] >= 0 and v1['b'] <= v1['ih'] + 1 and v1['l'] >= 0 and v1['r'] <= v1['iw'] + 1, v1)
        h.c.send('Page.captureScreenshot', {'format': 'png'})
        r = h.c.send('Page.captureScreenshot', {'format': 'png'})
        open(f'{OUT}/wlcm-step1-{theme}.png', 'wb').write(__import__('base64').b64decode(r['data']))
        # tap Spanish -> language screen must disappear, country dialog appears
        h.js("document.querySelector('[data-wlang=\"es\"]').click()")
        time.sleep(1.2)
        s2 = h.js("(()=>{const b=document.getElementById('wlcmBody');return b&&!!b.querySelector('.wlcm-countries')&&!b.querySelector('.wlcm-langs')})()")
        check(f'{theme}: step2 country dialog shown, language screen gone', s2 is True, s2)
        back = h.js("(()=>{const b=document.getElementById('wlcmBack');return b&&b.offsetParent!==null})()")
        check(f'{theme}: step2 Back button visible', back is True, back)
        nogo2 = h.js("(()=>{const b=document.getElementById('wlcmBody');return b&&!b.querySelector('#wlcmGo')})()")
        check(f'{theme}: step2 has NO Continue button', nogo2 is True, nogo2)
        esh1 = h.js("(()=>document.querySelector('#wlcmBody h1').textContent)()")
        check(f'{theme}: step2 rendered in Spanish', isinstance(esh1, str) and 'país' in esh1.lower(), esh1)
        v2 = json.loads(in_viewport(h, '.wlcm-card'))
        check(f'{theme}: step2 card within viewport', v2['b'] <= v2['ih'] + 1, v2)
        r = h.c.send('Page.captureScreenshot', {'format': 'png'})
        open(f'{OUT}/wlcm-step2-{theme}.png', 'wb').write(__import__('base64').b64decode(r['data']))
        # Back -> language screen returns
        h.js("document.getElementById('wlcmBack').click()")
        time.sleep(1.0)
        s1b = h.js("(()=>{const b=document.getElementById('wlcmBody');return b&&!!b.querySelector('.wlcm-langs')})()")
        check(f'{theme}: Back returns to language screen', s1b is True, s1b)
        # pick Nepali this time -> country dialog again, in Nepali
        h.js("document.querySelector('[data-wlang=\"ne\"]').click()")
        time.sleep(1.2)
        neh1 = h.js("(()=>document.querySelector('#wlcmBody h1').textContent)()")
        check(f'{theme}: step2 rendered in Nepali after re-pick', isinstance(neh1, str) and 'देश' in neh1, neh1)
        # pick Nepal -> dialog disappears, Continue appears
        h.js("document.querySelector('[data-wcc=\"NP\"]').click()")
        time.sleep(1.0)
        s3 = h.js("(()=>{const b=document.getElementById('wlcmBody');return b&&!!b.querySelector('#wlcmGo')&&!b.querySelector('.wlcm-countries')})()")
        check(f'{theme}: step3 Continue shown, country dialog gone', s3 is True, s3)
        disc = h.js("(()=>{const d=document.querySelector('.wlcm-disclaimer');return d&&d.textContent})()")
        check(f'{theme}: disclaimer visible', isinstance(disc, str) and 'law enforcement' in disc or isinstance(disc, str) and 'कानुन' in disc, (disc or '')[:60])
        go = json.loads(in_viewport(h, '#wlcmGo'))
        check(f'{theme}: Continue button reachable in viewport (the original bug)', go['t'] >= 0 and go['b'] <= go['ih'] + 1 and go['l'] >= 0 and go['r'] <= go['iw'] + 1, go)
        v3 = json.loads(in_viewport(h, '.wlcm-card'))
        check(f'{theme}: step3 card within viewport', v3['b'] <= v3['ih'] + 1, v3)
        nox = h.js("document.documentElement.scrollWidth<=innerWidth+1")
        check(f'{theme}: no horizontal overflow', nox is True, nox)
        r = h.c.send('Page.captureScreenshot', {'format': 'png'})
        open(f'{OUT}/wlcm-step3-{theme}.png', 'wb').write(__import__('base64').b64decode(r['data']))
        # Continue -> welcome hides, onboarding role sheet appears
        h.js("document.getElementById('wlcmGo').click()")
        time.sleep(1.5)
        hid = h.js("(()=>{const w=document.getElementById('wlcmHost');return !w||w.hidden})()")
        check(f'{theme}: welcome hidden after Continue', hid is True, hid)
        role = h.js("!!document.getElementById('obStudent')")
        check(f'{theme}: onboarding role step appears next', role is True, role)
        saved = h.js("(()=>{try{return JSON.parse(localStorage.getItem('orbit_i18n')||'{}')}catch(e){return null}})()")
        check(f'{theme}: lang+country persisted', isinstance(saved, dict) and saved.get('lang') == 'ne' and saved.get('country') == 'NP', saved)
        # lazy locale identity check: de must really load (kh guard passes)
        ld = h.js("HUB.i18n.loadLocale('de').then(ok=>({ok,ident:HUB.i18n._dict('de')!==HUB.i18n._dict('en'),k:HUB.i18n._dict('de')['welcome.step1Title']}))")
        time.sleep(2.5)
        check(f'{theme}: lazy de locale loads with new kh (no silent fallback)', isinstance(ld, dict) and ld.get('ok') and ld.get('ident') and ld.get('k') == 'Wähle deine Sprache', ld)
        errs = h.js("window.__huberr?window.__huberr.splice(0):[]")
        check(f'{theme}: zero uncaught console errors', not errs, errs)
    finally:
        h.done()
    return

run('dark', 9331, '/tmp/hubqa-wlcm-dark')
run('light', 9332, '/tmp/hubqa-wlcm-light')
print(f'\n==== RESULT: {passed} passed, {failed} failed ====')
sys.exit(1 if failed else 0)
