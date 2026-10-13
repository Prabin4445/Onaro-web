#!/usr/bin/env python3
"""QA: degree picker must NOT freeze with the full live index (15,404 plans).
Uses the local app build (file://) which reads the LIVE API (index.html sets
__ONARO_API_BASE to the Render API). Measures heartbeat responsiveness while
the picker renders, counts rendered rows, and exercises search + open plan."""
import sys, time
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def main():
    h = H(9451, '/tmp/hubqa-pickfix')
    try:
        h.setup('dark')
        # skip the auth gate via the app's own seam + seed i18n
        h.js("localStorage.setItem('orbit_i18n', JSON.stringify({lang:'en',country:'US'})); window.__gateSkip=true; try{HUB.auth.close()}catch(e){}; 'ok'")
        time.sleep(1)
        # heartbeat to detect main-thread blockage
        h.js("window.__hb=0; setInterval(function(){ window.__hb++; }, 100); 'hb'")
        # open degree plans
        t0 = time.time()
        h.js("window.__hb=0; HUB.degree.open(null); 'opened'")
        worst_gap = 0.0
        last_hb, last_t = 0, time.time()
        rows = 0
        for i in range(110):
            time.sleep(1)
            hb = h.js("window.__hb")
            now = time.time()
            if isinstance(hb, int):
                if hb == last_hb:
                    worst_gap = max(worst_gap, now - last_t)
                else:
                    last_hb, last_t = hb, now
            rows = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
            if isinstance(rows, int) and rows > 0:
                break
        dt = time.time() - t0
        h.note('picker renders without freeze', isinstance(rows, int) and rows > 0,
               f'rows={rows} after {dt:.1f}s, worst heartbeat gap={worst_gap:.1f}s')
        h.note('rendered rows capped (<=300)', isinstance(rows, int) and 0 < rows <= 300, f'rows={rows}')
        notice = h.js("(document.querySelector('#degResults')||{}).textContent||''")
        h.note('truncation notice shows true totals', isinstance(notice, str) and 'first 300 of' in notice,
               str(notice)[:120] if isinstance(notice, str) else str(notice))
        # search narrows and stays responsive
        h.js("var q=document.getElementById('degQ'); q.value='East Carolina'; q.dispatchEvent(new Event('input',{bubbles:true})); 'typed'")
        time.sleep(2.5)
        rows2 = h.js("document.querySelectorAll('#degResults .deg-planrow').length")
        txt2 = h.js("(document.querySelector('#degResults')||{}).textContent||''")
        h.note('search East Carolina works', isinstance(rows2, int) and rows2 > 0 and 'East Carolina' in str(txt2),
               f'rows={rows2}')
        # open the ECU Nursing plan -> requirements-only rendering
        opened = h.js("""(function(){var r=[].slice.call(document.querySelectorAll('#degResults .deg-planrow')).find(function(x){return /Nursing/i.test(x.textContent)}); if(r){r.click(); return 'clicked';} return 'not found';})()""")
        notice_txt = ''
        for i in range(30):
            time.sleep(1)
            notice_txt = h.js("(document.querySelector('.deg-reqonly-notice')||{}).textContent||''")
            if isinstance(notice_txt, str) and notice_txt:
                break
        body = str(h.js("(document.querySelector('#degBody')||{}).textContent||''"))
        h.note('ECU Nursing opens', opened == 'clicked' and 'Nursing' in body, f'open={opened}')
        h.note('requirements-only notice renders', isinstance(notice_txt, str) and 'Requirements only' in notice_txt,
               str(notice_txt)[:160])
        # plan must NOT show fake semester headers
        h.note('no fake semesters in req-only plan', 'Semester 1' not in body and 'Fall 1' not in body,
               body[:150].replace('\n', ' '))
        errs = h.errs()
        h.note('no JS errors', not errs, str(errs)[:200])
        h.save('dark', 'pickfix')
    finally:
        h.done()

if __name__ == '__main__':
    main()
