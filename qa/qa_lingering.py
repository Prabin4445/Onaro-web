#!/usr/bin/env python3
"""QA: lingering dialogs/toasts fix (2026-10-07, PraBin iPhone report).
 1. Toast visible duration < 1.6s (was 2.7s)
 2. New toast replaces old one (no stacking)
 3. Toasts cleared on tab switch
"""
import subprocess, time, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME

PORT = 9481
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

def boot():
    prof = '/tmp/hubqa-lingering'
    subprocess.run(['rm', '-rf', prof])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
        '--user-data-dir=' + prof, '--hide-scrollbars', '--window-size=390,844', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    tgt = None
    for _ in range(30):
        try:
            tgts = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read())
            tgt = [t for t in tgts if t.get('type') == 'page'][0]
            break
        except Exception:
            time.sleep(0.4)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable')
    c.send('Page.enable')
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}"
        "window.__gateSkip=true;"
        "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"})
    c.send('Page.navigate', {'url': BASE})
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.ui&&HUB.ui.toast)") is True:
            break
        time.sleep(0.5)
    j(c, "try{HUB.auth.close()}catch(e){} return 1;")
    time.sleep(1)
    return c, proc

def main():
    c, proc = boot()
    try:
        dur = j(c, """return (async()=>{
          const t0=performance.now();
          HUB.ui.toast('test toast 1');
          const host=document.getElementById('toastHost');
          if(!host||!host.children.length) return -1;
          for(let i=0;i<100;i++){ await new Promise(r=>setTimeout(r,50));
            if(!host.children.length) return (performance.now()-t0)/1000; }
          return 99;
        })()""", await_=True)
        check("toast duration <1.6s", isinstance(dur,(int,float)) and 0 < dur < 1.6,
              f"{dur:.2f}s" if isinstance(dur,(int,float)) else dur)

        stk = j(c, """return (async()=>{
          HUB.ui.toast('a'); HUB.ui.toast('b'); HUB.ui.toast('c');
          await new Promise(r=>setTimeout(r,150));
          const n=document.getElementById('toastHost').children.length;
          await new Promise(r=>setTimeout(r,1900));
          const n2=document.getElementById('toastHost').children.length;
          return n+'/'+n2;
        })()""", await_=True)
        check("no stacking (1 then 0)", stk == '1/0', stk)

        clr = j(c, """return (async()=>{
          HUB.ui.toast('will clear');
          await new Promise(r=>setTimeout(r,150));
          const b=document.getElementById('toastHost').children.length;
          if(HUB.ui.clearToasts) HUB.ui.clearToasts();
          await new Promise(r=>setTimeout(r,150));
          const a=document.getElementById('toastHost').children.length;
          return b+'/'+a;
        })()""", await_=True)
        check("clearToasts works", clr == '1/0', clr)

        errs = j(c, "return (window.__huberr||[]).slice(0,5)")
        check("zero console errors", not errs, str(errs)[:200])
    finally:
        proc.terminate()

    with open(os.path.expanduser('~/workspace/hub/js/auth.js')) as f:
        src = f.read()
    check("no 520ms artificial delay", 'setTimeout(function(){ close()' not in src, "removed")
    check("dismiss-before-backend", 'close();\n      done(true);\n      finishFirebaseLogin' in src, "ok")
    with open(os.path.expanduser('~/workspace/hub/js/store.js')) as f:
        ssrc = f.read()
    check("toast 1200ms timeout", '},1200);' in ssrc, "ok")

    print(f"\n{7-len(fails)}/7 passed")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
