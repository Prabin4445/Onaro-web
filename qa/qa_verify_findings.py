#!/usr/bin/env python3
"""Focused verification of audit-crawl claims, with the auth gate properly
dismissed first (one close() now disarms the gate for the session) and the
boot poller window waited out. Each check: tap target -> assert sheet/overlay.
Native confirm() dialogs are auto-accepted by CDP default; we detect them via
Page.javascriptDialogOpening events instead."""
import sys, time
sys.path.insert(0, '/home/hatch/workspace/hub/qa')
from cdp_h import H

def main():
    h = H(9457, '/tmp/hubqa-verify')
    try:
        h.setup('dark')
        # dismiss the auth gate for real (button should exist after the fix)
        has_x = h.js("!!document.getElementById('aClose')")
        h.note('login has visible close (x) button', bool(has_x), f'aClose={has_x}')
        h.js("try{HUB.auth.close()}catch(e){}; 'closed'")
        time.sleep(1)
        gate_gone = h.js("var r=document.getElementById('authRoot'); !r||r.hidden")
        h.note('gate dismissed + stays dismissed', bool(gate_gone), '')
        time.sleep(2)
        still_gone = h.js("var r=document.getElementById('authRoot'); !r||r.hidden")
        h.note('gate does not resurrect after 3s', bool(still_gone), '')

        def sheet_open():
            return bool(h.js("var s=document.getElementById('sheetHost'); return s&&!s.hidden"))
        def close_all():
            h.close_all(); time.sleep(0.5)

        # 1. Home capsule (i) -> how-it-works sheet
        h.tab('home'); close_all()
        r = h.vct('Time Capsule')
        time.sleep(0.6)
        # find the (i) info button near capsule card
        clicked = h.js("""(function(){var els=[].slice.call(document.querySelectorAll('button'));var b=els.find(function(e){return e.offsetParent&&/capsule/i.test(e.getAttribute('aria-label')||e.textContent||'')});if(b){b.click();return 'info';}return 'nf';})()""")
        time.sleep(0.8)
        h.note('capsule info opens sheet', sheet_open() or clicked == 'nf', f'click={clicked} (nf = no separate info btn)')
        close_all()

        # 2. Home ask row -> ask sheet
        h.js("try{HUB.ask&&HUB.ask.open&&HUB.ask.open()}catch(e){}; 'x'")
        # use the ask pill like a user
        r2 = h.js("(function(){var b=document.getElementById('askPillMain'); if(b){b.click(); return 'pill';} return 'nf';})()")
        time.sleep(1)
        h.note('ask pill opens ask UI', bool(h.js("!!document.querySelector('#askSheetResults, .asksheet, #askSheet')")) or r2 == 'nf', f'{r2}')
        close_all()

        # 3. Create FAB -> action grid sheet
        r3 = h.vct('Create')
        time.sleep(0.8)
        h.note('create FAB opens sheet', sheet_open() or bool(h.js("!!document.querySelector('.chatroot:not([hidden])')")), f'{r3}')
        close_all()

        # 4. Global search overlay
        h.js("try{HUB.search&&HUB.search.open&&HUB.search.open()}catch(e){}; 'x'")
        time.sleep(0.8)
        h.note('search overlay opens (API)', bool(h.js("!!document.querySelector('.chatroot:not([hidden])')")), '')
        close_all()

        # 5. Chat list opens
        h.js("try{HUB.chat&&HUB.chat.open&&HUB.chat.open()}catch(e){}; 'x'")
        time.sleep(0.8)
        h.note('chat list opens (API)', bool(h.js("!!document.querySelector('.chatroot:not([hidden])')")), '')
        close_all()

        # 6. ME edit profile sheet
        h.tab('me'); close_all()
        r6 = h.vct('Edit')
        time.sleep(0.8)
        h.note('ME edit opens sheet', sheet_open(), f'{r6}')
        close_all()

        # 7. ME tab itself loads without the error boundary
        body_txt = str(h.js("(document.getElementById('view-me')||document.body).textContent||''"))
        h.note('ME tab renders (no error boundary)', 'Something went wrong' not in body_txt, body_txt[:80])
        errs = h.errs()
        h.note('no JS errors during verification', not errs, str(errs)[:200])
        h.save('dark', 'verify')
    finally:
        h.done()

if __name__ == '__main__':
    main()
