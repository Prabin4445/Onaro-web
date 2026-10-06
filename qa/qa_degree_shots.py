#!/usr/bin/env python3
"""Retake screenshots obscured by the welcome sheet: set orbit_i18n so the
welcome flow doesn't reappear, complete a few tiles, capture."""
import os, sys, time
sys.path.insert(0, os.path.expanduser('~/workspace/hub/qa'))
from qa_degree import Run

r = Run('r5-shots', 390, 844)
try:
    # suppress the welcome flow permanently for this profile
    r.js("localStorage.setItem('orbit_i18n', JSON.stringify({lang:'en',country:'US'}))")
    # semester view with progress
    r.js(("(()=>{const st=HUB.degree._state();delete st.progress['uta-bs-computer-science'];"
          "HUB.store.save();HUB.degree.open('uta-bs-computer-science');return 1})()"))
    r.wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 15)
    r.wait_anim()
    for slot in ['s1-0', 's1-2', 's1-4']:
        r.js("document.querySelector('.deg-tile[data-slot=\"%s\"] [data-check]').click()" % slot)
        time.sleep(0.9)
    r.wait_js("document.querySelectorAll('#hubDegRoot .deg-tile.done').length>=3", 10)
    r.wait_anim()
    r.shot('qa-degree-semester-390-dark')
    # prereq warning visible
    r.js("document.querySelector('.deg-tile[data-slot=\"s4-4\"] [data-check]').click()")
    r.wait_js("document.querySelector('.deg-tile.done[data-slot=\"s4-4\"] .deg-warn')", 10)
    r.js(("(()=>{const t=document.querySelector('.deg-tile[data-slot=\"s4-4\"]');"
          "if(t)t.scrollIntoView({block:'center'});return 1})()"))
    time.sleep(1.0)
    r.wait_anim()
    r.shot('qa-degree-prereq-warn-390-dark')
    # transfer view
    r.open_plan('dallas-college-aa-business')
    r.js("document.getElementById('degTabXfer').click()")
    r.wait_js("document.querySelector('#hubDegRoot .deg-xsummary')", 10)
    r.wait_anim()
    r.shot('qa-degree-transfer-390-dark')
    r.drain('shots')
finally:
    r.close()
print('shots retaken')
