#!/usr/bin/env python3
"""FULL functional check A v2: boot, welcome gate path, login gate, tabs,
home widgets, daily tools (capsule, events, appointments, gym, gymwork,
wellness, scanner, calc, gpa, astro, degree plans, professors)."""
import sys, time, json
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def wait_hub(h, tries=40):
    for _ in range(tries):
        time.sleep(1.5)
        if h.js("typeof (window.HUB&&HUB.showTab)") == 'function':
            return True
    return False

def click_text(h, txt, scope='document'):
    return h.js(f"""(()=>{{const els=[...{scope}.querySelectorAll('button,[role=button],a,.btn')].filter(e=>e.offsetParent!==null);
      const b=els.find(e=>e.textContent.trim().includes({json.dumps(txt)}));if(!b)return 'notfound';b.click();return 'clicked';}})()""")

def set_val(h, sel, val):
    return h.js(f"""(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return 'missing';
      e.focus();e.value={json.dumps(val)};e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));return 'set';}})()""")

def main():
    h = H(9471, '/tmp/hubqa-fulla')
    try:
        assert wait_hub(h), 'HUB never booted'
        h.note('boot: HUB loads', True)
        h.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
        # wait for welcome to appear (fresh install), confirming the front-door flow starts
        wlcm = False
        for _ in range(15):
            time.sleep(1)
            wlcm = bool(h.js("(()=>{const w=document.getElementById('wlcmHost');return w&&!w.hidden})()"))
            if wlcm: break
        h.note('welcome: fresh-install welcome appears', wlcm)
        # seed profile (as prior harnesses do) + dismiss welcome + disarm watchdog
        h.js("try{HUB.store.state.profile.name='PraBin';HUB.store.state.profile.campus='University of the Cumberlands';HUB.store.state.profile.gender='female';HUB.store.state.profile.dob='2002-03-15';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;if(HUB.safe&&HUB.safe.booted)HUB.safe.booted();}catch(e){}; 'ok'")
        time.sleep(1)
        # ---- login gate via the app's own gate() (what the boot poller calls) ----
        g = h.js("(()=>{try{return HUB.auth.gate()}catch(e){return 'threw:'+e.message}})()")
        time.sleep(1.2)
        has_close = bool(h.js("!!document.querySelector('#aClose')"))
        has_skip = bool(h.js("!!document.querySelector('#aSkip')"))
        h.note('login: gate opens login (gate()=' + str(g) + ')', has_close or has_skip)
        h.note('login: close (X) button present', has_close)
        h.note('login: Explore link present', has_skip)
        if has_skip:
            h.js("document.querySelector('#aSkip').click(); 'ok'")
            time.sleep(1)
            gone = bool(h.js("(()=>{const r=document.getElementById('authRoot');return !r||r.hidden})()"))
            h.note('login: Explore dismisses gate', gone)
            g2 = h.js("(()=>{try{HUB.auth.gate();const r=document.getElementById('authRoot');return r?r.hidden:'noroot'}catch(e){return 'threw'}})()")
            time.sleep(3)
            gone2 = bool(h.js("(()=>{const r=document.getElementById('authRoot');return !r||r.hidden})()"))
            h.note('login: gate stays dismissed (gateDismissed)', gone2, f'gate2={g2}')
        # ---- tabs ----
        for tab in ['home', 'daily', 'market', 'work', 'groups', 'me']:
            h.tab(tab)
            txt = str(h.js(f"(document.getElementById('view-{tab}')||{{}}).innerText||''"))
            h.note(f'tab {tab} renders clean', 'Something went wrong' not in txt and len(txt) > 30, f'len={len(txt)}')
        # ---- home widgets ----
        h.tab('home')
        home_txt = str(h.js("(document.getElementById('view-home')||{}).innerText||''"))
        h.note('home: degree progress card present', 'degree' in home_txt.lower())
        signs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
        h.note('home: horoscope card shows a sign', any(s in home_txt for s in signs))
        tiles = h.js("document.querySelectorAll('#view-home .gltile').length")
        h.note('home: glance tiles render', (tiles or 0) > 0, f'tiles={tiles}')
        sgn = h.js("(()=>{const s=HUB.astro.signForDob('2002-03-15');return s&&(s.n||s)})()")
        h.note('astro: signForDob(2002-03-15) = Pisces', sgn == 'Pisces', f'got={sgn}')
        cal = h.js("(()=>{try{HUB.astro.openCalendar();return !!document.querySelector('.chatroot:not([hidden])')||!document.getElementById('sheetHost').hidden;}catch(e){return 'threw:'+e.message}})()")
        h.note('astro: calendar opens', cal is True, str(cal))
        h.close_all()
        # ---- daily: capsule (real save button #cpSeal) ----
        h.tab('daily')
        h.js("HUB.views.daily.openCapsuleSheet(); 'ok'"); time.sleep(0.8)
        h.note('capsule: sheet opens', h.sheet())
        set_val(h, '#cpTitle', 'QA capsule')
        set_val(h, '#cpMsg', 'Hello future me')
        set_val(h, '#cpDate', '2027-01-01')
        h.js("document.getElementById('cpSeal').click(); 'ok'")
        time.sleep(1)
        ncap = h.js("(HUB.store.state.capsules||[]).length")
        h.note('capsule: saved to store', (ncap or 0) >= 1, f'capsules={ncap}')
        h.close_all()
        # delete the capsule via its UI delete button
        if (ncap or 0) >= 1:
            h.js("(()=>{const b=document.querySelector('[data-cdel]');if(b)b.click();return !!b})()")
            time.sleep(0.8)
            ncap2 = h.js("(HUB.store.state.capsules||[]).length")
            h.note('capsule: delete works', ncap2 == ncap - 1, f'after={ncap2}')
        # ---- daily: event (#efTitle + #efTime required, #efSave) ----
        h.js("HUB.views.daily.openEventFormSheet(); 'ok'"); time.sleep(0.8)
        h.note('event: form sheet opens', h.sheet())
        set_val(h, '#efTitle', 'QA study session')
        set_val(h, '#efTime', 'Sat · 6:00 PM')
        h.js("document.getElementById('efSave').click(); 'ok'")
        time.sleep(0.8)
        nev = h.js("(HUB.store.state.events||[]).length")
        h.note('event: saved to store', (nev or 0) >= 1, f'events={nev}')
        h.close_all()
        # ---- appointments ----
        h.js("(()=>{HUB.appts.addAppt({title:'QA dentist',date:new Date(Date.now()+86400000).toISOString().slice(0,10),time:'09:30'});return 'ok'})()")
        up = h.js("(HUB.appts.upcoming()||[]).length")
        h.note('appointments: add + upcoming works', (up or 0) >= 1, f'upcoming={up}')
        # ---- gym ----
        h.js("try{HUB.gym.openSetup()}catch(e){}; 'ok'"); time.sleep(0.8)
        h.note('gym: setup sheet opens', h.sheet())
        h.close_all()
        h.js("try{HUB.gymwork.open()}catch(e){}; 'ok'"); time.sleep(1.2)
        gw = h.js("(()=>{const d=document.querySelector('.chatroot:not([hidden]),#sheetHost:not([hidden])');return d?(d.innerText||'').length:0})()")
        h.note('gymwork: workout plans open with content', (gw or 0) > 40, f'len={gw}')
        h.js("try{HUB.gymwork.close()}catch(e){}; 'ok'"); h.close_all()
        # ---- wellness ----
        acc = h.js("(()=>{try{return HUB.wellness._access()}catch(e){return 'threw'}})()")
        h.js("try{HUB.wellness.openDashboard()}catch(e){}; 'ok'"); time.sleep(1.2)
        wtxt = h.js("(()=>{const d=document.querySelector('.chatroot:not([hidden])');return d?(d.innerText||'').length:0})()")
        h.note('wellness: dashboard opens for female profile', (wtxt or 0) > 40, f'access={acc} len={wtxt}')
        h.js("try{HUB.wellness.closeDashboard()}catch(e){}; 'ok'"); h.close_all()
        # ---- scanner ----
        scan_open = h.js("(()=>{const c=[...document.querySelectorAll('[data-scan-card]')];if(!c.length)return 'nocard';const b=c[0].querySelector('[data-act=\"scan\"],button');if(b)b.click();return 'clicked'})()")
        time.sleep(1.2)
        stxt = h.js("(()=>{const d=document.querySelector('.chatroot:not([hidden]),#sheetHost:not([hidden])');return d?(d.innerText||'').length:0})()")
        h.note('scanner: studio opens', (stxt or 0) > 20, f'open={scan_open} len={stxt}')
        h.close_all()
        # ---- calculator ----
        h.js("try{HUB.calc.openFull()}catch(e){}; 'ok'"); time.sleep(1)
        calc_open = h.js("!!document.querySelector('.calc-full,.chatroot:not([hidden]) .calc, #sheetHost:not([hidden]) .calc')") or h.sheet() or h.chatroot()
        h.note('calc: full calculator opens', bool(calc_open))
        ev1 = h.js("(()=>{try{const r=HUB.calc._eval('2+3*4');return r&&r.value!==undefined?r.value:r}catch(e){return 'threw:'+e.message}})()")
        h.note('calc: 2+3*4 = 14', str(ev1) in ('14', '14.0'), f'got={ev1}')
        ev2 = h.js("(()=>{try{const r=HUB.calc._eval('sqrt(144)');return r&&r.value!==undefined?r.value:r}catch(e){return 'threw:'+e.message}})()")
        h.note('calc: sqrt(144) = 12', str(ev2) in ('12', '12.0'), f'got={ev2}')
        h.js("try{HUB.calc.closeFull()}catch(e){}; 'ok'"); h.close_all()
        # ---- GPA ----
        h.js("try{HUB.gpa.addSheet()}catch(e){}; 'ok'"); time.sleep(0.8)
        h.note('gpa: add-course sheet opens', h.sheet())
        h.close_all()
        g = h.js("(()=>{try{const cs=HUB.gpa.courses();const r=HUB.gpa.calc(cs);return r&&r.gpa!==undefined?r.gpa:r}catch(e){return 'threw:'+e.message}})()")
        h.note('gpa: calc runs without throwing', not str(g).startswith('threw'), f'g={g}')
        # ---- degree plans (poll: API attempt times out in sandbox, local fallback loads) ----
        h.js("try{HUB.degree.open(null)}catch(e){}; 'ok'")
        rows = 0
        for _ in range(50):
            time.sleep(2)
            rows = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
            if isinstance(rows, int) and rows > 0:
                break
        h.note('degree: picker renders rows', isinstance(rows, int) and rows > 0, f'rows={rows}')
        h.note('degree: rows capped at 300', isinstance(rows, int) and rows <= 300, f'rows={rows}')
        if rows:
            set_val(h, '#degQ', 'East Carolina')
            time.sleep(2.5)
            rows2 = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
            txt2 = str(h.js("(document.querySelector('#degResults')||{}).textContent||''"))
            h.note('degree: search East Carolina narrows', isinstance(rows2, int) and 0 < rows2 < rows and 'East Carolina' in txt2, f'rows2={rows2}')
            opened = h.js("""(()=>{const r=[...document.querySelectorAll('#degResults .deg-planrow')].find(x=>/Nursing/i.test(x.textContent));if(r){r.click();return 'clicked'}return 'notfound'})()""")
            notice = ''
            for _ in range(25):
                time.sleep(1.2)
                notice = str(h.js("(document.querySelector('.deg-reqonly-notice')||{}).textContent||''"))
                if notice: break
            body = str(h.js("(document.querySelector('#degBody')||{}).textContent||''"))
            h.note('degree: ECU Nursing plan opens', opened == 'clicked' and 'Nursing' in body, f'open={opened}')
            h.note('degree: requirements-only notice renders', 'Requirements only' in notice, notice[:100])
            h.note('degree: no fake semesters in req-only plan', 'Semester 1' not in body and 'Fall 1' not in body)
            h.js("try{HUB.degree.close()}catch(e){}; 'ok'"); time.sleep(1)
            # normal semester plan: Texas Tech CS
            h.js("try{HUB.degree.open(null)}catch(e){}; 'ok'")
            for _ in range(40):
                time.sleep(2)
                r3 = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
                if isinstance(r3, int) and r3 > 0: break
            set_val(h, '#degQ', 'Texas Tech')
            time.sleep(2.5)
            opened2 = h.js("""(()=>{const rs=[...document.querySelectorAll('#degResults .deg-planrow')];const r=rs.find(x=>/Computer Science/i.test(x.textContent))||rs[0];if(r){r.click();return (r.textContent||'').slice(0,60)}return 'notfound'})()""")
            sems = 0
            for _ in range(25):
                time.sleep(1.2)
                sems = h.js("(document.querySelectorAll('#degBody .deg-sem, #degBody [class*=semhead], #degBody h3').length)")
                if isinstance(sems, int) and sems >= 4: break
            h.note('degree: semester plan opens with semesters', isinstance(sems, int) and sems >= 4, f'plan={opened2} sems={sems}')
            slug = h.js("(()=>{const p=HUB.degree._state;return p&&p.active||null})()")
            done_before = h.js("(()=>{try{const p=HUB.degree._state;const s=p.active;const d=(p.progress[s]&&p.progress[s].done)||{};return Object.keys(d).length}catch(e){return -1}})()")
            tog = h.js("(()=>{const c=document.querySelector('#degBody .deg-check');if(!c)return 'nocheck';c.click();return 'toggled'})()")
            time.sleep(1)
            done_after = h.js("(()=>{try{const p=HUB.degree._state;const s=p.active;const d=(p.progress[s]&&p.progress[s].done)||{};return Object.keys(d).length}catch(e){return -1}})()")
            h.note('degree: marking course complete updates progress', tog == 'toggled' and isinstance(done_after, int) and done_after == (done_before or 0) + 1,
                   f'slug={slug} before={done_before} after={done_after}')
            h.js("try{HUB.degree.close()}catch(e){}; 'ok'")
        h.close_all()
        # ---- professors ----
        h.js("try{HUB.professors.open()}catch(e){}; 'ok'"); time.sleep(2)
        ptxt = h.js("(()=>{const d=document.querySelector('.chatroot:not([hidden])')||document.getElementById('sheetHost');return d?(d.innerText||'').length:0})()")
        h.note('professors: directory opens with content', (ptxt or 0) > 40, f'len={ptxt}')
        h.js("try{HUB.professors.close()}catch(e){}; 'ok'"); h.close_all()
        errs = h.errs()
        h.note('ZERO JS errors across part A', not errs, str(errs)[:300])
        h.save('dark', 'fullcheckA')
    finally:
        h.done()

if __name__ == '__main__':
    main()
