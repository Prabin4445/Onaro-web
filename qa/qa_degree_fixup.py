#!/usr/bin/env python3
"""Fix-up run for qa_degree.py failures: re-tests swipe/ring/credits/persist
with a NON-choice tile (s1-0; run1 wrongly used choice slot s1-1), re-verifies
the swipe-left spec direction, and re-runs the prereq-warning test with full
instrumentation (run1's s4-4 click artifact under investigation)."""
import os, sys, time
sys.path.insert(0, os.path.expanduser('~/workspace/hub/qa'))
from qa_degree import Run, swipe_js

r = Run('r1b-fixup', 390, 844)
try:
    r.js(("(()=>{const st=HUB.degree._state();delete st.progress['uta-bs-computer-science'];"
          "HUB.store.save();HUB.degree.open('uta-bs-computer-science');return 'fresh'})()"))
    r.wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 15)
    r.wait_anim()
    # sanity: s1-0 is a regular (non-choice) tile
    v, _ = r.js("(()=>{const t=document.querySelector('.deg-tile[data-slot=\"s1-0\"]');"
                "return t&&!t.querySelector('.deg-choice-chip')})()")
    r.check('fixup: s1-0 is a non-choice tile', v is True, v)

    # --- swipe LEFT on undone tile (task spec direction) ---
    v, ex = r.js(swipe_js('s1-0', 'left'))
    time.sleep(1.6)
    done, _ = r.js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-0\"]')")
    sheet, _ = r.js("!document.getElementById('sheetHost').hidden")
    r.check('SPEC re-test: swipe-left completes undone tile', done is True,
            'dispatched=%s exc=%s done=%s sheet=%s — implementation only commits on swipe-RIGHT; left rubber-bands (no-op)' % (v, ex, done, sheet))

    # --- swipe RIGHT (implemented direction) ---
    v, ex = r.js(swipe_js('s1-0', 'right'))
    time.sleep(1.8)
    done, _ = r.js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-0\"]')")
    r.check('fixup: swipe-right completes undone tile', done is True, 'dispatched=%s exc=%s' % (v, ex))
    ring, _ = r.js("document.querySelector('#hubDegRoot .deg-ring-num').textContent")
    r.check('fixup: progress ring updates after swipe', (ring or '').strip() not in ('0%', ''), ring)
    earn, _ = r.js("document.querySelector('#hubDegRoot .deg-earned').textContent")
    r.check('fixup: earned credits update after swipe', ' of 123' in (earn or '') and not (earn or '').startswith('0 of'), earn)
    aud, _ = r.js("document.querySelectorAll('#hubDegRoot audio').length")
    r.check('fixup: completion is silent (no <audio>)', aud == 0, aud)
    # swipe LEFT on a DONE tile unmarks (implemented direction)
    v, ex = r.js(swipe_js('s1-0', 'left'))
    time.sleep(1.8)
    done, _ = r.js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-0\"]')")
    r.check('fixup: swipe-left unmarks a done tile (implemented direction)', done is False, 'dispatched=%s' % v)
    # re-complete via swipe-right for persistence test
    r.js(swipe_js('s1-0', 'right'))
    r.wait_js("document.querySelector('.deg-tile.done[data-slot=\"s1-0\"]')", 10)
    r.drain('swipe-fixup')

    # --- persistence across reload ---
    r.js("location.reload()")
    r.wait_js("document.readyState==='complete'", 25)
    r.wait_js("!document.getElementById('splash')", 20)
    time.sleep(1.0)
    r.open_plan('uta-bs-computer-science')
    done, _ = r.js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-0\"]')")
    r.check('fixup: progress persists across reload (localStorage)', done is True)
    r.drain('persist-fixup')

    # --- prereq warnings, instrumented ---
    r.js(("(()=>{const st=HUB.degree._state();delete st.progress['uta-bs-computer-science'];"
          "HUB.store.save();HUB.degree.open('uta-bs-computer-science');return 'fresh'})()"))
    r.wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 15)
    r.wait_anim()
    pre, _ = r.js("(()=>{const t=document.querySelector('.deg-tile[data-slot=\"s4-4\"]');"
                  "return t?{warn:!!t.querySelector('.deg-warn'),"
                  " txt:(t.querySelector('.deg-warn')||{textContent:''}).textContent}:null})()")
    r.check('prereq: warn badge present on s4-4 before completion (unmet)', (pre or {}).get('warn') is True, pre)
    v, ex = r.js("document.querySelector('.deg-tile[data-slot=\"s4-4\"] [data-check]').click(); 'clicked'")
    r.check('prereq: check-button click dispatches cleanly', ex is None, 'v=%s exc=%s' % (v, ex))
    ok = r.wait_js("document.querySelector('.deg-tile.done[data-slot=\"s4-4\"]')", 10)
    r.check('prereq: s4-4 completes via check button', ok is not None)
    wtxt, _ = r.js("(()=>{const t=document.querySelector('.deg-tile.done[data-slot=\"s4-4\"] .deg-warn\");"
                   "return t?t.textContent:null})()")
    r.check('prereq: amber warning after completing with unmet prereq', (wtxt or '') == '⚠ Complete ENGL 1301 first', wtxt)
    # scroll the warned tile into view for the evidence screenshot
    r.js(("(()=>{const t=document.querySelector('.deg-tile[data-slot=\"s4-4\"]');"
          "if(t)t.scrollIntoView({block:'center'});return 1})()"))
    time.sleep(0.8)
    r.shot('qa-degree-prereq-warn-390-dark')
    v, ex = r.js("document.querySelector('.deg-tile[data-slot=\"s1-4\"] [data-check]').click(); 'clicked'")
    ok = r.wait_js("document.querySelector('.deg-tile.done[data-slot=\"s1-4\"]')", 10)
    r.check('prereq: ENGL 1301 (s1-4) completes', ok is not None, 'exc=%s' % ex)
    time.sleep(0.8)
    gone, _ = r.js("!!document.querySelector('.deg-tile[data-slot=\"s4-4\"] .deg-warn')")
    r.check('prereq: warning clears after prereq completed', gone is False)
    r.drain('prereq-fixup')
    r.drain('final')
finally:
    r.close()
p, f, checks, errs = r.summary()
print('\nFIXUP SUMMARY: passed=%d failed=%d console_errors=%d' % (p, f, len(errs)))
for l, e in errs:
    print('  ', l, ':', str(e)[:300])
sys.exit(1 if (f or errs) else 0)
