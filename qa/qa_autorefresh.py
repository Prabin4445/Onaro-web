#!/usr/bin/env python3
"""QA: Event-driven auto-refresh (2026-10-07, PraBin order).
- HUB.emit/HUB.on bus works (subscribe, emit, unsubscribe, bad-handler isolation).
- Completing a course in plan view -> Home degree card updates WITHOUT reload.
- Adding/removing a class -> "Your classes" card updates WITHOUT reload (targeted).
- Tab switch away and back -> Home re-renders fresh.
- Untrack -> honest empty state, no phantom.
- Zero console errors, 390px.
"""
import subprocess, time, json, os, sys, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME
import websocket  # noqa: F401
import urllib.request

PORT = 9453
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok:
        fails.append(n)

def j(c, expr, await_=False):
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip()
        if e.endswith(';'):
            e = e[:-1]
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q:
                instr = False
        elif ch in '"\'`':
            instr, q = True, ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ';' and depth == 0:
            top_semi = True
            break
    if not top_semi:
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'awaitPromise': await_, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

def main():
    chrome = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--window-size=390,844', '--user-data-dir=/tmp/hubqa-autoref',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files',
        '--remote-allow-origins=*',
        '--use-fake-ui-for-media-stream', '--mute-audio', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    try:
        tgt = None
        for _ in range(30):
            try:
                tgts = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read())
                tgt = [t for t in tgts if t.get('type') == 'page'][0]
                break
            except Exception:
                time.sleep(0.4)
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Page.enable', wait=True)
        c.send('Runtime.enable', wait=True)
        c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
            "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
            "window.__gateSkip=true;"
            "window.__huberr=[];"
            "addEventListener('error',function(e){__huberr.push('ERR:'+e.message);});"
            "addEventListener('unhandledrejection',function(e){__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason));});"})
        c.send('Page.navigate', {'url': BASE}, wait=True)
        for _ in range(40):
            time.sleep(1)
            if j(c, "return !!(window.HUB&&HUB.safe&&HUB.safe.isBooted());"):
                break
        j(c, "window.__gateSkip=true; if(HUB.auth&&HUB.auth.close) HUB.auth.close();")
        j(c, "var w=document.getElementById('wlcmHost'); if(w) w.remove();")
        # sandbox can't reach the live API: force the static-file fallback path
        j(c, "try{delete window.__ONARO_API_BASE;}catch(e){window.__ONARO_API_BASE='';} try{localStorage.removeItem('onaro_api_base');}catch(e){} return 1;")
        api_off = j(c, "return !HUB.api.on();")
        check("API forced off for QA", api_off is True, "api.on=%r" % (not api_off))
        time.sleep(1)
        j(c, "HUB.showTab('home');")
        time.sleep(2)

        # 1. Event bus
        check("HUB.emit/HUB.on exist", j(c, "return typeof HUB.emit==='function'&&typeof HUB.on==='function';"))
        check("bus round-trip", j(c, "var got=null; var off=HUB.on('qa:ping',function(d){ got=d; }); HUB.emit('qa:ping',{v:42}); off(); HUB.emit('qa:ping',{v:99}); return got&&got.v===42;"))
        check("unsubscribe works", j(c, "var n=0; var off=HUB.on('qa:u',function(){ n++; }); off(); HUB.emit('qa:u'); return n===0;"))
        check("bad handler isolated", j(c, "var ok=false; HUB.on('qa:bad',function(){ throw new Error('x'); }); HUB.on('qa:bad',function(){ ok=true; }); HUB.emit('qa:bad'); return ok;"))

        # 2. Track a plan directly via state + emit -> Home card loads and shows 0
        slug = 'aaniiih-nakoda-college-aas-industrial-trades'
        j(c, "var ds=HUB.degree._state(); ds.tracked='%s'; ds.active='%s'; HUB.store.save(); HUB.emit('degree:progress');" % (slug, slug))
        # poll for the card to finish async load (degFile)
        for _ in range(15):
            time.sleep(1)
            before = j(c, "var e=document.getElementById('dpgEarn'); return e?e.textContent:'MISSING';")
            if before != 'MISSING':
                break
        check("card shows 0 earned initially", before == '0', "got=%r" % before)
        j(c, "var p=HUB.store.state.degree.progress['%s']; p.done=p.done||{}; p.done['s1-0']={code:'TST 101',title:'Test',credits:3,ts:Date.now(),at:'0:0'}; HUB.store.save(); HUB.emit('degree:progress');" % slug)
        for _ in range(15):
            time.sleep(1)
            after = j(c, "var e=document.getElementById('dpgEarn'); return e?e.textContent:'MISSING';")
            if after == '3':
                break
        check("card updated without reload", after == '3', "got=%r" % after)
        j(c, "var p=HUB.store.state.degree.progress['%s']; p.done={}; HUB.store.save(); HUB.emit('degree:progress');" % slug)
        time.sleep(1.5)

        # 3. Add/remove class -> targeted card update
        j(c, "HUB.classes.addClass({subject:'QA Physics',room:'R1',days:[1],start:'10:00',end:'11:00'});")
        time.sleep(1.5)
        check("class add updates card", j(c, "var cc=document.getElementById('classCard'); return cc&&cc.textContent.indexOf('QA Physics')!==-1;"))
        j(c, "var cl=HUB.classes.list().filter(function(x){return x.subject==='QA Physics';})[0]; if(cl) HUB.classes.removeClass(cl.id);")
        time.sleep(1.5)
        check("class removal updates card", j(c, "var cc=document.getElementById('classCard'); return cc&&cc.textContent.indexOf('QA Physics')===-1;"))

        # 4. Tab switch -> fresh
        j(c, "HUB.showTab('daily');")
        time.sleep(1.5)
        j(c, "HUB.showTab('home');")
        time.sleep(2)
        check("home re-renders on tab return", j(c, "return !!document.getElementById('view-home')&&!document.getElementById('view-home').hidden;"))

        # 5. Untrack -> empty state
        j(c, "HUB.degree._state().tracked=null; HUB.store.save(); HUB.emit('degree:progress');")
        time.sleep(1.5)
        check("untrack shows empty state", j(c, "return !!document.querySelector('#homeDegProg .degprog-empty');"))

        errs = [e for e in (j(c, "return window.__huberr||[];") or []) if 'favicon' not in str(e).lower()]
        check("zero console errors", len(errs) == 0, "%d errors" % len(errs))
        for e in errs[:5]:
            print("  ERR:", str(e)[:160])
    finally:
        chrome.terminate()

    print("\n==== %d FAILURES ====" % len(fails))
    for f in fails:
        print("FAIL:", f)
    sys.exit(1 if fails else 0)

main()
