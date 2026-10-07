/* HUB CALC — Onaro-branded scientific calculator (Daily tab, "daily life").
   Own tokenizer + recursive-descent parser; eval() is never used.
   Brand: crystal-glass 3D keys, volt = key, dark #0D100A surfaces.
   UX (PraBin's order): better than the Casio — NO shift layers (every function
   is one tap), tap-to-place cursor editing, long-press DEL = clear all,
   live result preview as you type, tap-to-copy on the result.
   Honest limits: decimal results only — not exact fractions like a Casio
   natural-textbook display. History + Ans persist on this device. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const ui=()=>HUB.ui, st=()=>HUB.store.state;

/* ================= expression engine =================
   The display holds PRETTY text (× ÷ − √ sin⁻¹ …). toCanon() maps it back
   to parser tokens before evaluation. */
function CalcError(code){ this.code=code; }
CalcError.prototype=new Error();

function mode(){ return (st().calcMode==='rad')?'rad':'deg'; }
function lastAns(){ const v=st().calcAns; return (typeof v==='number'&&isFinite(v))?v:0; }

function toCanon(s){
  return String(s||'')
    .replace(/\n/g,'') /* wrap="soft" inserts none, but strip defensively */
    .replace(/sin\u207B\u00B9\(/g,'asin(').replace(/cos\u207B\u00B9\(/g,'acos(').replace(/tan\u207B\u00B9\(/g,'atan(')
    .replace(/\u221A\(/g,'sqrt(')
    .replace(/\u00D7/g,'*').replace(/\u00F7/g,'/').replace(/\u2212/g,'-')
    .replace(/\u207B\u00B9/g,'^(-1)');
}

function tokenize(s){
  const toks=[]; let i=0;
  const isDigit=function(c){ return c>='0'&&c<='9'; };
  const FUNCS=['asinh','acosh','atanh','sinh','cosh','tanh','cbrt','logb','root','asin','acos','atan','sqrt','sin','cos','tan','log','ln'];
  function needMul(){
    const p=toks[toks.length-1];
    return p&&(p.type==='num'||p.type==='rparen'||p.type==='post'||p.type==='var');
  }
  while(i<s.length){
    const c=s[i];
    if(c===' '){ i++; continue; }
    if(isDigit(c)||c==='.'){
      let j=i, dot=false;
      while(j<s.length&&(isDigit(s[j])||(!dot&&s[j]==='.'))){ if(s[j]==='.')dot=true; j++; }
      if(s[j]==='E'||s[j]==='e'){ /* scientific entry: 1.5E3 (fmt() emits 1e+21) */
        let k=j+1; if(s[k]==='+'||s[k]==='-')k++;
        if(k<s.length&&isDigit(s[k])){ while(k<s.length&&isDigit(s[k]))k++; j=k; }
      }
      const num=parseFloat(s.slice(i,j));
      if(!isFinite(num)) throw new CalcError('overflow');
      if(needMul()) toks.push({type:'op',op:'*'});
      toks.push({type:'num',v:num}); i=j; continue;
    }
    if(c==='\u03C0'){ if(needMul())toks.push({type:'op',op:'*'}); toks.push({type:'num',v:Math.PI}); i++; continue; }
    if(c==='e'){ if(needMul())toks.push({type:'op',op:'*'}); toks.push({type:'num',v:Math.E}); i++; continue; }
    if(c==='x'||c==='X'){ /* graph variable: 2x -> 2*x, x(2) -> x*(2) */
      if(needMul())toks.push({type:'op',op:'*'}); toks.push({type:'var'}); i++; continue; }
    if(c==='('){ if(needMul())toks.push({type:'op',op:'*'}); toks.push({type:'lparen'}); i++; continue; }
    if(c===')'){ toks.push({type:'rparen'}); i++; continue; }
    if(c===','){ toks.push({type:'comma'}); i++; continue; } /* multi-arg functions: logb(2,8), root(4,16) */
    if('+-*/^'.indexOf(c)>=0){ toks.push({type:'op',op:c}); i++; continue; }
    if(c==='!'){ toks.push({type:'post',op:'!'}); i++; continue; }
    if(c==='%'){ toks.push({type:'post',op:'%'}); i++; continue; }
    if(c==='P'||c==='C'){ toks.push({type:'op',op:c}); i++; continue; }
    let fn=null;
    for(let f=0;f<FUNCS.length;f++){ const w=FUNCS[f]; if(s.indexOf(w,i)===0&&s[i+w.length]==='('){ fn=w; break; } }
    if(fn){ if(needMul())toks.push({type:'op',op:'*'}); toks.push({type:'func',fn:fn}); i+=fn.length; continue; }
    if(s.indexOf('Ans',i)===0){ if(needMul())toks.push({type:'op',op:'*'}); toks.push({type:'num',v:lastAns()}); i+=3; continue; }
    throw new CalcError('syntax');
  }
  return toks;
}

function isInt(x){ return Math.abs(x-Math.round(x))<1e-9; }
function fact(x){
  if(x<0||!isInt(x)||x>170) throw new CalcError('domain');
  let r=1; const n=Math.round(x);
  for(let i=2;i<=n;i++) r*=i;
  return r;
}
function nPr(n,r){
  if(n<0||r<0||!isInt(n)||!isInt(r)||r>n) throw new CalcError('domain');
  return fact(n)/fact(n-r);
}
function nCr(n,r){
  if(n<0||r<0||!isInt(n)||!isInt(r)||r>n) throw new CalcError('domain');
  return fact(n)/(fact(r)*fact(n-r));
}
function powFn(b,e){
  if(b===0&&e<0) throw new CalcError('div0');
  if(b===0&&e===0) throw new CalcError('domain');
  const r=Math.pow(b,e);
  if(isNaN(r)) throw new CalcError('domain');
  if(!isFinite(r)) throw new CalcError('overflow');
  return r;
}
const FN_ARITY={sin:1,cos:1,tan:1,asin:1,acos:1,atan:1,log:1,ln:1,sqrt:1,
  sinh:1,cosh:1,tanh:1,asinh:1,acosh:1,atanh:1,cbrt:1,logb:2,root:2};
function applyFn(fn,args,md){
  if(args.length!==(FN_ARITY[fn]||1)) throw new CalcError('syntax');
  const x=args[0];
  const toRad=function(v){ return md==='deg'?v*Math.PI/180:v; };
  const fromRad=function(v){ return md==='deg'?v*180/Math.PI:v; };
  switch(fn){
    case 'sin': return Math.sin(toRad(x));
    case 'cos': return Math.cos(toRad(x));
    case 'tan': {
      if(Math.abs(Math.cos(toRad(x)))<1e-12) throw new CalcError('domain');
      return Math.tan(toRad(x));
    }
    case 'asin': if(Math.abs(x)>1) throw new CalcError('domain'); return fromRad(Math.asin(x));
    case 'acos': if(Math.abs(x)>1) throw new CalcError('domain'); return fromRad(Math.acos(x));
    case 'atan': return fromRad(Math.atan(x));
    case 'log': if(x<=0) throw new CalcError('domain'); return Math.log10(x);
    case 'ln': if(x<=0) throw new CalcError('domain'); return Math.log(x);
    case 'sqrt': if(x<0) throw new CalcError('domain'); return Math.sqrt(x);
    case 'sinh': return Math.sinh(x);
    case 'cosh': return Math.cosh(x);
    case 'tanh': return Math.tanh(x);
    case 'asinh': return Math.asinh(x);
    case 'acosh': if(x<1) throw new CalcError('domain'); return Math.acosh(x);
    case 'atanh': if(Math.abs(x)>=1) throw new CalcError('domain'); return Math.atanh(x);
    case 'cbrt': return Math.cbrt(x);
    case 'logb': { /* logb(base,value): log of value in the given base */
      const b=args[0], v=args[1];
      if(b<=0||b===1||v<=0) throw new CalcError('domain');
      return Math.log(v)/Math.log(b);
    }
    case 'root': { /* root(n,x): nth root of x; odd n allows negative x */
      const n=args[0], v=args[1];
      if(!isInt(n)||n===0) throw new CalcError('domain');
      const ni=Math.round(n);
      if(v<0){ if(ni%2===0) throw new CalcError('domain'); return -Math.pow(-v,1/ni); }
      if(v===0&&ni<0) throw new CalcError('div0');
      return Math.pow(v,1/ni);
    }
  }
  throw new CalcError('syntax');
}

/* ================= advanced numeric engine =================
   Casio-class operations, original Onaro implementation: definite integrals
   (adaptive Simpson), numeric derivatives, summation, equation solving
   (bisection scan), polar/rectangular conversion, integer base conversion.
   All failures surface as friendly CalcError codes, never raw NaN/Infinity. */
function simpsonQ(f,a,b,fa,fm,fb){ return (b-a)/6*(fa+4*fm+fb); }
function adSimpson(f,a,b,tol,whole,fa,fm,fb,depth){
  const m=(a+b)/2, lm=(a+m)/2, rm=(m+b)/2;
  const flm=f(lm), frm=f(rm);
  const left=simpsonQ(f,a,m,fa,flm,fm), right=simpsonQ(f,m,b,fm,frm,fb);
  const delta=left+right-whole;
  if(depth<=0||Math.abs(delta)<=15*tol) return left+right+delta/15;
  return adSimpson(f,a,m,tol/2,left,fa,flm,fm,depth-1)+adSimpson(f,m,b,tol/2,right,fm,frm,fb,depth-1);
}
function numIntegrate(f,a,b){
  if(!isFinite(a)||!isFinite(b)) throw new CalcError('domain');
  if(a===b) return 0;
  const sgn=a<b?1:-1, lo=Math.min(a,b), hi=Math.max(a,b);
  const fa=f(lo), fm=f((lo+hi)/2), fb=f(hi); /* probe throws friendly domain errors */
  const v=adSimpson(f,lo,hi,1e-10,simpsonQ(f,lo,hi,fa,fm,fb),fa,fm,fb,14);
  if(!isFinite(v)) throw new CalcError('overflow');
  return sgn*v;
}
function numDeriv(f,x0){
  if(!isFinite(x0)) throw new CalcError('domain');
  const h=1e-5*Math.max(1,Math.abs(x0));
  const d=(f(x0+h)-f(x0-h))/(2*h);
  if(!isFinite(d)) throw new CalcError('domain');
  return d;
}
function numSigma(f,a,b){
  if(!isFinite(a)||!isFinite(b)) throw new CalcError('domain');
  let lo=Math.round(a), hi=Math.round(b);
  if(lo>hi){ const tmp=lo; lo=hi; hi=tmp; }
  if(hi-lo>200000) throw new CalcError('overflow');
  let s=0;
  for(let k=lo;k<=hi;k++){
    const v=f(k);
    if(typeof v!=='number'||!isFinite(v)) throw new CalcError('domain');
    s+=v;
  }
  if(!isFinite(s)) throw new CalcError('overflow');
  return s;
}
function numSolve(f){
  const roots=[];
  function add(r){ for(let i=0;i<roots.length;i++) if(Math.abs(roots[i]-r)<1e-7) return; roots.push(r); }
  function val(x){ try{ const v=f(x); return (typeof v==='number'&&isFinite(v))?v:NaN; }catch(e){ return NaN; } }
  function bisect(a,b){
    for(let i=0;i<64;i++){
      const m=(a+b)/2, fm=val(m);
      if(!isFinite(fm)) return null;
      if(Math.abs(fm)<1e-12||(b-a)<1e-13) return m;
      const fa=val(a);
      if(!isFinite(fa)) return null;
      if(fa*fm<=0) b=m; else a=m;
    }
    return (a+b)/2;
  }
  function scan(lo,hi,n){
    let px=lo, pv=val(lo);
    if(isFinite(pv)&&Math.abs(pv)<1e-10) add(lo);
    for(let i=1;i<=n;i++){
      const x=lo+(hi-lo)*i/n, v=val(x);
      if(isFinite(v)){
        if(Math.abs(v)<1e-10) add(x);
        else if(isFinite(pv)&&pv*v<0){
          const r=bisect(px,x);
          if(r!==null&&Math.abs(val(r))<1e-7) add(r); /* verify: skip discontinuities like 1/x */
        }
      }
      px=x; pv=v;
    }
  }
  scan(-100,100,400);
  if(!roots.length) scan(-10000,10000,800);
  return roots.sort(function(a,b){ return a-b; });
}
/* pol: (x,y)->{r,th}; rec: (r,th)->{x,y}. Angle follows the current DEG/RAD mode. */
function polRec(kind,p,q){
  if(!isFinite(p)||!isFinite(q)) throw new CalcError('domain');
  const md=mode();
  if(kind==='pol'){
    const r=Math.hypot(p,q);
    let th=Math.atan2(q,p); if(md==='deg') th=th*180/Math.PI;
    if(!isFinite(r)||!isFinite(th)) throw new CalcError('overflow');
    return {a:r,b:th};
  }
  let th=q; if(md==='deg') th=th*Math.PI/180;
  const x=p*Math.cos(th), y=p*Math.sin(th);
  if(!isFinite(x)||!isFinite(y)) throw new CalcError('overflow');
  return {a:x,b:y};
}
function baseConvert(text,base){
  const s=String(text==null?'':text).trim().replace(/_/g,'');
  const m=/^([-+]?)(0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|[0-9]+)$/.exec(s);
  if(!m) throw new CalcError('syntax');
  const neg=m[1]==='-', body=m[2];
  /* parseInt(s,0) does NOT honor 0b/0o prefixes (only 0x): parse prefix-aware */
  const v=/^0[xX]/.test(body)?parseInt(body.slice(2),16)
        :/^0[bB]/.test(body)?parseInt(body.slice(2),2)
        :/^0[oO]/.test(body)?parseInt(body.slice(2),8)
        :parseInt(body,10);
  if(!isFinite(v)||Math.abs(v)>9007199254740991) throw new CalcError('overflow');
  const a=Math.abs(v);
  const digs=base===10?String(a):a.toString(base).toUpperCase();
  return (neg?'-':'')+digs;
}
function memVal(){ const v=st().calcMem; return (typeof v==='number'&&isFinite(v))?v:0; }
function curVal(){
  const el=inp();
  if(el&&el.value){ const r=evaluate(el.value); if(r.ok) return r.value; }
  return lastAns();
}

function parseAll(toks,md,env){
  let p=0;
  function peek(){ return toks[p]; }
  function next(){ return toks[p++]; }
  function err(code){ throw new CalcError(code); }
  function parseE(){
    let v=parseT();
    for(;;){
      const tk=peek();
      if(tk&&tk.type==='op'&&(tk.op==='+'||tk.op==='-')){ next(); const r=parseT(); v=(tk.op==='+')?v+r:v-r; }
      else return v;
    }
  }
  function parseT(){
    let v=parseF();
    for(;;){
      const tk=peek();
      if(tk&&tk.type==='op'&&(tk.op==='*'||tk.op==='/'||tk.op==='P'||tk.op==='C')){
        next(); const r=parseF();
        if(tk.op==='*') v=v*r;
        else if(tk.op==='/'){ if(r===0) err('div0'); v=v/r; }
        else v=(tk.op==='P')?nPr(v,r):nCr(v,r);
      } else return v;
    }
  }
  function parseF(){
    const b=parseU(), tk=peek();
    if(tk&&tk.type==='op'&&tk.op==='^'){ next(); return powFn(b,parseF()); }
    return b;
  }
  function parseU(){
    const tk=peek();
    if(tk&&tk.type==='op'&&(tk.op==='-'||tk.op==='+')){ next(); const v=parseU(); return (tk.op==='-')?-v:v; }
    return parsePost();
  }
  function parsePost(){
    let v=parsePrim();
    for(;;){
      const tk=peek();
      if(tk&&tk.type==='post'){ next(); v=(tk.op==='!')?fact(v):v/100; }
      else return v;
    }
  }
  function parsePrim(){
    const tk=next();
    if(!tk) err('syntax');
    if(tk.type==='num') return tk.v;
    if(tk.type==='var'){ /* graph variable: only meaningful with an {x} environment */
      if(!env||typeof env.x!=='number'||!isFinite(env.x)) err(env?'domain':'syntax');
      return env.x;
    }
    if(tk.type==='func'){
      const lp=next(); if(!lp||lp.type!=='lparen') err('paren');
      const args=[];
      try{ args.push(parseE()); }catch(e){ if(e&&e.code==='syntax'&&p>=toks.length) err('paren'); throw e; }
      for(;;){
        const cm=peek();
        if(cm&&cm.type==='comma'){ next(); args.push(parseE()); }
        else break;
      }
      const rp=next(); if(!rp||rp.type!=='rparen') err('paren');
      return applyFn(tk.fn,args,md);
    }
    if(tk.type==='lparen'){
      let v;
      try{ v=parseE(); }catch(e){ if(e&&e.code==='syntax'&&p>=toks.length) err('paren'); throw e; }
      const rp=next(); if(!rp||rp.type!=='rparen') err('paren');
      return v;
    }
    err('syntax');
  }
  if(!toks.length) err('empty');
  const v=parseE();
  if(p<toks.length) err('syntax');
  if(!isFinite(v)) err('overflow');
  return v;
}

/* Public evaluate on PRETTY text: {ok:1,value} or {ok:0,code}.
   Optional env {x:number} enables the graph variable. */
function evaluate(prettyExpr,md,env){
  try{
    const v=parseAll(tokenize(toCanon(prettyExpr)),md||mode(),env);
    return {ok:1,value:v};
  }catch(e){
    return {ok:0,code:(e&&e.code)||'syntax'};
  }
}

/* Decimal formatting: 10 significant digits, exponential beyond 1e12 / 1e-9.
   MODE/SETUP display format: 'norm' (default), 'fix' (Fix N decimals),
   'sci' (scientific). Formatting is display-only; Ans keeps full precision. */
function fmt(v){
  if(!isFinite(v)) throw new CalcError('overflow');
  if(v===0) return '0';
  const a=Math.abs(v);
  const f=st().calcFmt||'norm';
  function expForm(n){
    let s=v.toExponential(n);
    s=s.replace(/(\.\d*[1-9])0+e/,'$1e').replace(/\.0+e/,'e');
    return s;
  }
  if(f==='sci'){
    let n=st().calcFixN; if(!(n>=0&&n<=9)) n=4;
    return expForm(n);
  }
  if(f==='fix'){
    let n=st().calcFixN; if(!(n>=0&&n<=9)) n=2;
    if(a>=1e12||a<1e-9) return expForm(n);
    return v.toFixed(n);
  }
  if(a>=1e12||a<1e-9) return expForm(8);
  return String(parseFloat(v.toPrecision(10)));
}

function errText(code){
  switch(code){
    case 'div0': return t('calc.errDiv0');
    case 'domain': return t('calc.errDomain');
    case 'paren': return t('calc.errParen');
    case 'overflow': return t('calc.errOverflow');
    case 'empty': return t('calc.errSyntax');
    default: return t('calc.errSyntax');
  }
}

/* ================= UI (cursor-based editing) ================= */
let fresh=false; /* true right after '=': next value key starts a new expression */

/* ---- key click sound: REMOVED 2026-09-29 on PraBin's order ----
   ("remove sound effect from all except ringtone and notification").
   The WebAudio click synth + header toggle chip are gone; only the app's
   ringtone and notification sounds remain. Key feel is now glow + scale-press. */

/* ---- key press glow: volt flash on every key ----
   pointerdown adds it immediately (finger-down feel on touch); press() re-flashes
   so physical-keyboard presses glow too. Removed on release or a short timeout.
   Kept alongside the existing :active scale-press feedback. */
const keyGlowT={};
function flashKey(id){
  if(!id) return;
  const b=document.querySelector('#calcRoot [data-ck="'+id+'"]'); if(!b) return;
  b.classList.add('kglow');
  clearTimeout(keyGlowT[id]);
  keyGlowT[id]=setTimeout(function(){ b.classList.remove('kglow'); },200);
}

/* ---- display readability: multi-line textarea, caret-always-visible, volt typing glow ----
   PraBin: "when someone starts typing, the screen goes down and up as they move it,
   let the user see what they're typing." The expression is a readonly <textarea>:
   it wraps to new lines, auto-grows downward up to DISP_MAXLINES, then scrolls —
   native iOS tap-to-place cursor + native drag-scroll. fitArea() re-grows on every
   mutation and keeps the caret in view vertically (mirror-div measurement). */
const DISP_LH=1.3, DISP_MAXLINES=4;
let glowT=0, caretMirror=null;
function caretY(el){
  /* vertical offset of the caret from the content top, via a hidden mirror div */
  if(!caretMirror){
    caretMirror=document.createElement('div');
    caretMirror.setAttribute('aria-hidden','true');
    const ms0=caretMirror.style;
    ms0.position='absolute'; ms0.visibility='hidden'; ms0.top='0'; ms0.left='0';
    ms0.pointerEvents='none';
    ms0.whiteSpace='pre-wrap'; ms0.overflowWrap='anywhere'; ms0.wordBreak='break-word';
    ms0.padding='0'; ms0.border='0'; ms0.margin='0';
    document.body.appendChild(caretMirror);
  }
  const cs=getComputedStyle(el), ms=caretMirror.style;
  ms.width=el.clientWidth+'px';
  ms.fontSize=cs.fontSize; ms.fontFamily=cs.fontFamily; ms.fontWeight=cs.fontWeight;
  ms.lineHeight=cs.lineHeight; ms.letterSpacing=cs.letterSpacing; ms.textAlign=cs.textAlign;
  const pos=(el.selectionStart==null)?el.value.length:el.selectionStart;
  const before=el.value.slice(0,pos).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  caretMirror.innerHTML=before+'<span id="calcCaretMk">\u200b</span>';
  const mk=caretMirror.querySelector('#calcCaretMk');
  return mk?mk.offsetTop:0;
}
function revealCaret(el){
  try{
    if(!el.value){ el.scrollTop=0; return; }
    const y=caretY(el);
    const lh=parseFloat(getComputedStyle(el).lineHeight)||32;
    const top=el.scrollTop, vh=el.clientHeight;
    if(y<top) el.scrollTop=Math.max(0,y-lh);
    else if(y+lh>top+vh) el.scrollTop=y+lh-vh+4;
  }catch(e){}
}
function fitArea(el){
  if(!el) return;
  el.style.height='auto'; /* re-grow from content */
  const fs=parseFloat(getComputedStyle(el).fontSize)||32;
  const maxH=Math.ceil(fs*DISP_LH*DISP_MAXLINES);
  el.style.height=Math.min(el.scrollHeight,maxH)+'px';
  revealCaret(el); /* long expressions: keep the caret / newest chars in view */
}
function pulseGlow(){
  const d=document.querySelector('#calcRoot .calc-disp'); if(!d) return;
  d.classList.add('calc-glow');
  const rm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(!rm){ /* replay the pulse: remove + force reflow + re-add */
    d.classList.remove('calc-pulse'); void d.offsetWidth; d.classList.add('calc-pulse');
  }
  clearTimeout(glowT);
  glowT=setTimeout(function(){ d.classList.remove('calc-glow'); },750); /* settle */
}

function hist(){ const h=st().calcHist; return Array.isArray(h)?h:[]; }
function pushHist(e,r){
  const h=hist(); h.unshift({e:e,r:r});
  st().calcHist=h.slice(0,12); HUB.store.save();
}
function inp(){ return document.getElementById('calcExpr'); }

function kd(id,label,ins,cls,aria){ return {id:id,label:label,ins:ins,cls:cls||'calc-key',aria:aria||label}; }
function rows(){
  const R=[];
  R.push([
    kd('mode','',null,'calc-key mode','DEG/RAD'),
    kd('lp','(', '(', 'calc-key fn'),
    kd('rp',')', ')', 'calc-key fn'),
    kd('del','DEL',null,'calc-key warn','Delete — long-press to clear all'),
    kd('ac','AC',null,'calc-key warn','All clear')
  ]);
  R.push([
    kd('sin','sin','sin(','calc-key fn'), kd('cos','cos','cos(','calc-key fn'),
    kd('tan','tan','tan(','calc-key fn'),
    kd('asin','sin\u207B\u00B9','sin\u207B\u00B9(','calc-key fn'),
    kd('acos','cos\u207B\u00B9','cos\u207B\u00B9(','calc-key fn')
  ]);
  R.push([
    kd('atan','tan\u207B\u00B9','tan\u207B\u00B9(','calc-key fn'),
    kd('log','log','log(','calc-key fn'), kd('ln','ln','ln(','calc-key fn'),
    kd('p10','10\u02E3','10^(','calc-key fn'), kd('pex','e\u02E3','e^(','calc-key fn')
  ]);
  R.push([
    kd('sqrt','\u221A','\u221A(','calc-key fn'),
    kd('sq','x\u00B2','^2','calc-key fn'), kd('cb','x\u00B3','^3','calc-key fn'),
    kd('rc','x\u207B\u00B9','\u207B\u00B9','calc-key fn'),
    kd('pi','\u03C0','\u03C0','calc-key fn')
  ]);
  R.push([
    kd('eu','e','e','calc-key fn'),
    kd('npr','nPr','P','calc-key fn'), kd('ncr','nCr','C','calc-key fn'),
    kd('fact','!','!','calc-key fn'), kd('pct','%','%','calc-key fn')
  ]);
  R.push([kd('k7','7','7'),kd('k8','8','8'),kd('k9','9','9'),
    kd('kdiv','\u00F7','\u00F7','calc-key op'),kd('kpow','^','^','calc-key op')]);
  R.push([kd('k4','4','4'),kd('k5','5','5'),kd('k6','6','6'),
    kd('kmul','\u00D7','\u00D7','calc-key op'),kd('exp','EXP','E','calc-key fn')]);
  R.push([kd('k1','1','1'),kd('k2','2','2'),kd('k3','3','3'),
    kd('kmin','\u2212','\u2212','calc-key op'),kd('ans','Ans','Ans','calc-key fn')]);
  R.push([kd('k0','0','0'),kd('dot','.','.'),
    kd('plus','+','+','calc-key op'),kd('eq','=','=','calc-key eq span2','Equals')]);
  return R;
}

/* Advanced bank (PraBin's "all this" list): one-tap keys, NO shift layer —
   the dedicated-keys design is what makes ours easier than the Casio.
   Multi-argument operations (integral, derivative, sum, solve, pol/rec,
   base conversion) open a small lab sheet with labeled fields, which is
   easier for students than cursor-template navigation. */
function advRows(){
  const R=[];
  R.push([
    kd('lab-int','\u222B','', 'calc-key fn','Definite integral'),
    kd('lab-der','d/dx','', 'calc-key fn','Derivative at a point'),
    kd('lab-sum','\u03A3','', 'calc-key fn','Summation'),
    kd('lab-sol','x=?','', 'calc-key fn','Solve f(x) = 0'),
    kd('lab-pol','Pol/Rec','', 'calc-key fn','Polar-rectangular conversion')
  ]);
  R.push([
    kd('sinh','sinh','sinh(','calc-key fn'), kd('cosh','cosh','cosh(','calc-key fn'),
    kd('tanh','tanh','tanh(','calc-key fn'), kd('asinh','sinh\u207B\u00B9','asinh(','calc-key fn'),
    kd('acosh','cosh\u207B\u00B9','acosh(','calc-key fn')
  ]);
  R.push([
    kd('atanh','tanh\u207B\u00B9','atanh(','calc-key fn'),
    kd('cbrt','\u221B','cbrt(','calc-key fn'), kd('nthroot','\u207F\u221A','root(','calc-key fn'),
    kd('logb','log\u2090','logb(','calc-key fn'),
    kd('kx','x','x','calc-key fn','Variable x')
  ]);
  R.push([
    kd('ran','Ran#',null,'calc-key fn','Random number'),
    kd('mplus','M+',null,'calc-key fn','Memory add'),
    kd('mminus','M\u2212',null,'calc-key fn','Memory subtract'),
    kd('mr','MR',null,'calc-key fn','Memory recall'),
    kd('lab-base','BASE','', 'calc-key fn','Base converter')
  ]);
  return R;
}

function gridHTML(){
  const U=ui();
  const bank=st().calcAdv?advRows():rows();
  return bank.map(function(r){
    return '<div class="calc-row">'+r.map(function(k){
      const lbl=(k.id==='mode')?U.esc(mode()==='deg'?t('calc.deg'):t('calc.rad')):U.esc(k.label);
      return '<button type="button" class="'+U.esc(k.cls)+'" data-ck="'+U.esc(k.id)+'" aria-label="'+U.esc(k.aria)+'">'+lbl+'</button>';
    }).join('')+'</div>';
  }).join('');
}
/* re-render the key grid after an ADV toggle; re-binds fresh buttons */
function paintGrid(){
  const grid=document.getElementById('calcGrid'); if(!grid) return;
  grid.innerHTML=gridHTML();
  bindKeys(grid);
  syncAdv();
}
function syncAdv(){
  const b=document.getElementById('calcAdvBtn'); if(!b) return;
  const on=!!st().calcAdv;
  b.classList.toggle('on',on);
  b.setAttribute('aria-pressed',on?'true':'false');
}

/* REPLAY: up/down recall of previous expressions from history.
   hist() is newest-first (unshift). ▲ walks older, ▼ walks newer;
   walking off either end restores the draft the user was typing. */
let replayIdx=-1, replayDraft='';
function replayNav(older){
  const h=hist(), el=inp(); if(!el||!h.length) return;
  if(replayIdx===-1){
    if(!older) return; /* ▼ with nothing recalled: stay on the draft */
    replayDraft=el.value; replayIdx=0;
  }else{
    replayIdx+=older?1:-1;
    if(replayIdx>=h.length||replayIdx<0){
      replayIdx=-1; el.value=replayDraft;
      const p=el.value.length;
      try{ el.setSelectionRange(p,p); }catch(e){}
      fresh=false; paint(); pulseGlow(); return;
    }
  }
  el.value=h[replayIdx].e;
  const p2=el.value.length;
  try{ el.setSelectionRange(p2,p2); }catch(e2){}
  fresh=false; paint(); pulseGlow();
}

/* In-app graph keypad: [label, insert, optional extra class]. Digits, ops, x, ^,
   parens, sin/cos/tan/ln/log/sqrt/pi/e, DEL and cursor keys. Rows are readonly
   (no iOS keyboard); all input flows through gPadIns/gPadDel into the ACTIVE
   row, and caret moves go through gPadMove. */
const GPADKEYS=[
 ['sin','sin('],['cos','cos('],['(','('],[')',')'],['DEL','DEL'],
 ['7','7'],['8','8'],['9','9'],['\u00F7','\u00F7'],['^','^'],
 ['4','4'],['5','5'],['6','6'],['\u00D7','\u00D7'],['x','x'],
 ['1','1'],['2','2'],['3','3'],['\u2212','\u2212'],['\u221A','\u221A('],
 ['0','0','span2'],['.','.'],['\u03C0','\u03C0'],['+','+'],
 ['tan','tan('],['ln','ln('],['log','log('],['e','e','span2'],
 ['\u25C0','\u25C0'],['\u25B6','\u25B6']
];
/* Calc header 3D clay icons (2026): icon-only clay chips replace the old emoji/text
   buttons so the header row fits narrow screens. The clay graph icon could not
   be generated, so the "go to graph" state keeps the chart emoji inside the
   clay chip (same emoji-fallback pattern as HUB.icons.fallback). */
function calcViewIcon(v){
  if(v==='graph') return HUB.icons.icon('calc-keypad');
  if(HUB.icons.map&&HUB.icons.map['calc-graph']) return HUB.icons.icon('calc-graph');
  return '<span class="calc-emoji">\uD83D\uDCC8</span>';
}
function cardHTML(){
  const U=ui();
  /* strip the leading abacus emoji from the i18n title; the clay icon replaces it */
  const titleTx=U.esc(t('calc.title').replace(/^\uD83E\uDDEE\s*/,''));
  return '<div class="card calc-card" id="calcRoot">'+
    '<div class="calc-top"><h3 class="calc-ttl">'+HUB.icons.icon('calc-title','calc-tico')+'<span>'+titleTx+'</span></h3>'+
    '<div class="calc-chips">'+
    '<button type="button" class="chip calc-hbtn calc-advbtn" id="calcAdvBtn" aria-label="Advanced functions" aria-pressed="false">'+HUB.icons.icon('calc-adv')+'</button>'+
    '<button type="button" class="chip calc-hbtn" id="calcViewBtn" aria-label="Toggle graphing calculator" aria-pressed="false">'+calcViewIcon(st().calcView)+'</button>'+
    '<button type="button" class="chip calc-hbtn" id="calcSetBtn" aria-label="'+U.esc(t('calc.settings'))+'">'+HUB.icons.icon('calc-set')+'</button>'+
    '<button type="button" class="chip calc-degchip" id="calcModeBtn" aria-label="DEG/RAD">'+U.esc(mode()==='deg'?t('calc.deg'):t('calc.rad'))+'</button>'+
    '</div></div>'+
    '<p class="sub" style="margin:6px 0 10px">'+U.esc(t('calc.sub'))+'</p>'+
    '<div class="calc-normal" id="calcNormal">'+
    '<div class="calc-disp"><textarea class="calc-expr" id="calcExpr" rows="1" wrap="soft" readonly inputmode="none" autocomplete="off" '+
      'aria-label="'+U.esc(t('calc.title'))+'" placeholder="0"></textarea>'+
      '<div class="calc-res" id="calcRes" title="'+U.esc(t('calc.tapCopy'))+'"></div></div>'+
    '<div class="calc-grid" id="calcGrid">'+gridHTML()+'</div>'+
    '<div class="row between" style="margin:14px 0 6px"><h4 style="margin:0">'+U.esc(t('calc.history'))+'</h4>'+
    '<div class="row" style="gap:6px">'+
    '<button type="button" class="chip calc-rpbtn" id="calcRpUp" aria-label="Recall older calculation">\u25B2</button>'+
    '<button type="button" class="chip calc-rpbtn" id="calcRpDown" aria-label="Recall newer calculation">\u25BC</button>'+
    '<button type="button" class="linklike" id="calcClearHist">'+U.esc(t('calc.clearHist'))+'</button>'+
    '</div></div>'+
    '<div id="calcHist"></div>'+
    '<p class="hint" style="margin-top:6px">'+U.esc(t('calc.tapReuse'))+'<br>'+U.esc(t('calc.delHint'))+'</p>'+
    '</div>'+
    '<div class="calc-graph" id="calcGraph" hidden>'+
      '<div class="calc-grow" id="calcFnRows"></div>'+
      '<div class="calc-cvwrap"><canvas id="calcCanvas"></canvas><div class="calc-trace" id="calcTrace" hidden></div></div>'+
      '<div class="calc-gtools">'+
        '<button type="button" class="chip calc-gbtn" id="calcZoomOut" aria-label="Zoom out">\u2212</button>'+
        '<button type="button" class="chip calc-gbtn" id="calcZoomIn" aria-label="Zoom in">\uFF0B</button>'+
        '<button type="button" class="chip calc-gbtn" id="calcZoomReset" aria-label="Reset view">\u27F2</button>'+
      '</div>'+
      '<div class="calc-gpad" id="calcGpad" role="group">'+
        GPADKEYS.map(function(k,i){
          return '<button type="button" class="calc-key gk'+(k[2]?' '+k[2]:'')+'" data-gk="'+U.esc(k[1])+'" id="gk'+i+'">'+U.esc(k[0])+'</button>';
        }).join('')+
      '</div>'+
    '</div>'+
  '</div>';
}

/* Live preview: re-evaluated on every keystroke; blank until the expression is valid. */
function paint(){
  const el=inp(), rs=document.getElementById('calcRes');
  if(!el||!rs) return;
  fitArea(el); /* multi-line: grow downward, keep caret in view */
  const v=el.value;
  if(!v){ rs.textContent=''; rs.classList.remove('calc-err'); return; }
  const r=evaluate(v);
  if(r.ok){ rs.textContent='= '+fmt(r.value); rs.classList.remove('calc-err'); }
  else { rs.textContent=''; rs.classList.remove('calc-err'); }
}

function paintHist(){
  const host=document.getElementById('calcHist'); if(!host) return;
  const U=ui(), h=hist();
  if(!h.length){ host.innerHTML='<p class="sub">'+U.esc(t('calc.histEmpty'))+'</p>'; return; }
  host.innerHTML=h.map(function(item,i){
    return '<button type="button" class="calc-hrow" data-hi="'+i+'"><span class="calc-hexpr">'+U.esc(item.e)+'</span><span class="calc-hres">= '+U.esc(item.r)+'</span></button>';
  }).join('');
  host.querySelectorAll('[data-hi]').forEach(function(b){
    b.onclick=function(){
      const item=hist()[+b.dataset.hi]; if(!item) return;
      const el=inp(); el.value=item.e; fresh=false;
      el.setSelectionRange(el.value.length,el.value.length); paint(); pulseGlow();
    };
  });
}

function flashErr(code){
  const rs=document.getElementById('calcRes'); if(!rs) return;
  rs.textContent=errText(code); rs.classList.add('calc-err');
}

function commit(){
  const el=inp(); if(!el) return;
  const prettyExpr=el.value;
  if(!prettyExpr){ flashErr('empty'); return; }
  const r=evaluate(prettyExpr);
  if(!r.ok){ flashErr(r.code); return; }
  const out=fmt(r.value);
  pushHist(prettyExpr,out);
  st().calcAns=r.value; HUB.store.save();
  el.value=out; el.setSelectionRange(out.length,out.length);
  fresh=true; paint(); paintHist();
}

function isValueStart(ins){
  if(!ins) return false;
  const c=ins[0];
  return ('0123456789.(\u03C0'.indexOf(c)>=0)||c==='e'||c==='x'||ins==='Ans'||
    /^(sin|cos|tan|sinh|cosh|tanh|asinh|acosh|atanh|log|ln|logb|cbrt|root)\($/.test(ins)||/^sin\u207B\u00B9\($/.test(ins)||
    /^cos\u207B\u00B9\($/.test(ins)||/^tan\u207B\u00B9\($/.test(ins)||ins==='\u221A(';
}

function insertAt(el,s){
  const v=el.value;
  let a=el.selectionStart, b=el.selectionEnd;
  if(a==null||b==null){ a=b=v.length; }
  el.value=v.slice(0,a)+s+v.slice(b);
  const pos=a+s.length;
  try{ el.setSelectionRange(pos,pos); }catch(e){}
  try{ el.focus({preventScroll:true}); }catch(e2){ try{el.focus();}catch(e3){} }
}

function delChar(){
  const el=inp(); if(!el) return;
  if(fresh){ el.value=''; fresh=false; paint(); return; }
  const v=el.value;
  let a=el.selectionStart, b=el.selectionEnd;
  if(a==null||b==null){ a=b=v.length; }
  if(a!==b){ el.value=v.slice(0,a)+v.slice(b); try{el.setSelectionRange(a,a);}catch(e){} }
  else if(a>0){ el.value=v.slice(0,a-1)+v.slice(a); try{el.setSelectionRange(a-1,a-1);}catch(e){} }
  try{ el.focus({preventScroll:true}); }catch(e2){}
  paint();
}

function flashMem(){
  const rs=document.getElementById('calcRes'); if(!rs) return;
  rs.textContent='M = '+fmt(memVal()); rs.classList.remove('calc-err');
}

function pressKey(id,ins){
  const el=inp(); if(!el&&id!=='mode') return;
  if(id!=='rpu'&&id!=='rpd'){ replayIdx=-1; replayDraft=''; } /* any real action exits replay */
  if(id==='mode'){
    st().calcMode=(mode()==='deg')?'rad':'deg'; HUB.store.save();
    const mb=document.getElementById('calcModeBtn'), chip=document.querySelector('#calcRoot [data-ck="mode"]');
    const lbl=mode()==='deg'?t('calc.deg'):t('calc.rad');
    if(mb) mb.textContent=lbl;
    if(chip) chip.textContent=lbl;
    paint(); return;
  }
  if(id==='del'){ delChar(); return; }
  if(id==='ac'){ el.value=''; fresh=false; paint(); return; }
  if(id==='eq'){ commit(); return; }
  if(id==='adv'){ st().calcAdv=!st().calcAdv; HUB.store.save(); paintGrid(); return; }
  if(id==='set'){ openSettings(); return; }
  if(id==='lab-int'){ openLab('int'); return; }
  if(id==='lab-der'){ openLab('der'); return; }
  if(id==='lab-sum'){ openLab('sum'); return; }
  if(id==='lab-sol'){ openLab('sol'); return; }
  if(id==='lab-pol'){ openLab('pol'); return; }
  if(id==='lab-base'){ openLab('base'); return; }
  if(id==='rpu'){ replayNav(true); return; }
  if(id==='rpd'){ replayNav(false); return; }
  if(id==='ran'){
    if(fresh){ el.value=''; fresh=false; }
    insertAt(el,(Math.random()).toFixed(3)); paint(); return;
  }
  if(id==='mplus'||id==='mminus'){
    st().calcMem=memVal()+(id==='mplus'?curVal():-curVal()); HUB.store.save();
    flashMem(); return;
  }
  if(id==='mr'){
    if(fresh){ el.value=''; fresh=false; }
    insertAt(el,fmt(memVal())); paint(); return;
  }
  if(fresh){ if(isValueStart(ins)) el.value=''; fresh=false; }
  if(ins==='^'){
    const last=el.value[el.value.length-1];
    if(!el.value||'+-\u00D7\u00F7^(\u2212'.indexOf(last)>=0) return; /* dangling power */
  }
  insertAt(el,ins); paint();
}
/* every key path (tap, physical keyboard, DEL) goes through press: glow the display,
   flash the key, and play the original iPhone-feel click */
function press(id,ins){ pressKey(id,ins); pulseGlow(); flashKey(id); }

function copyText(s){
  const done=function(){ try{ ui().toast(t('calc.copied')); }catch(e){} };
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(s).then(done,function(){ fallbackCopy(s); done(); });
  }else{ fallbackCopy(s); done(); }
}
function fallbackCopy(s){
  try{
    const ta=document.createElement('textarea');
    ta.value=s; ta.style.position='fixed'; ta.style.opacity='0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
  }catch(e){}
}

function bindKeys(scope){
  const map={};
  /* map must cover the CURRENTLY RENDERED bank: the ADV bank's keys (sinh…mr)
     are not in rows(), so binding them against a rows()-only map passed
     ins=undefined into insertAt -> TypeError on every ADV function key tap. */
  (st().calcAdv?advRows():rows()).forEach(function(r){ r.forEach(function(k){ map[k.id]=k.ins; }); });
  scope.querySelectorAll('[data-ck]').forEach(function(b){
    const id=b.dataset.ck;
    /* volt glow the moment the finger lands; removed on release or timeout */
    b.addEventListener('pointerdown',function(){ b.classList.add('kglow'); });
    ['pointerup','pointerleave','pointercancel'].forEach(function(ev){
      b.addEventListener(ev,function(){ b.classList.remove('kglow'); });
    });
    if(id==='del'){ /* long-press DEL = clear all */
      let timer=0, longFired=false;
      b.addEventListener('pointerdown',function(){
        longFired=false;
        timer=setTimeout(function(){ longFired=true; press('ac'); },550);
      });
      ['pointerup','pointerleave','pointercancel'].forEach(function(ev){
        b.addEventListener(ev,function(){
          clearTimeout(timer);
          if(!longFired&&ev==='pointerup') press('del');
        });
      });
      b.addEventListener('contextmenu',function(e){ e.preventDefault(); });
      return;
    }
    b.addEventListener('click',function(){ press(id,map[id]); });
  });
}

function bind(el){
  const root=el.querySelector('#calcRoot'); if(!root) return;
  const grid=el.querySelector('#calcGrid'); if(grid) bindKeys(grid);
  const ab=el.querySelector('#calcAdvBtn'); /* ADV bank toggle */
  if(ab) ab.onclick=function(){ press('adv'); };
  syncAdv();
  const setb=el.querySelector('#calcSetBtn'); /* MODE/SETUP settings sheet */
  if(setb) setb.onclick=function(){ press('set'); };
  const rpu=el.querySelector('#calcRpUp'), rpd=el.querySelector('#calcRpDown');
  if(rpu) rpu.onclick=function(){ press('rpu'); };
  if(rpd) rpd.onclick=function(){ press('rpd'); };
  const vb=el.querySelector('#calcViewBtn'); /* icon-only Calc <-> Graph toggle */
  if(vb) vb.onclick=function(){ setView(st().calcView==='graph'?'calc':'graph'); };
  gBindPad(); /* in-app graph keypad (pre-rendered in cardHTML) */
  const zi=el.querySelector('#calcZoomIn'), zo=el.querySelector('#calcZoomOut'), zr=el.querySelector('#calcZoomReset');
  if(zi) zi.onclick=function(){ const g=gst(); g.ppu=clampPpu(g.ppu*1.45); gsave(); gRender(); };
  if(zo) zo.onclick=function(){ const g=gst(); g.ppu=clampPpu(g.ppu/1.45); gsave(); gRender(); };
  if(zr) zr.onclick=function(){ const g=gst(); g.cx=0; g.cy=0; g.ppu=34; gsave(); gTracePt=null; gRender(); };
  const mb=el.querySelector('#calcModeBtn');
  if(mb) mb.onclick=function(){ press('mode'); if(st().calcView==='graph') gValidateRender(); };
  const ch=el.querySelector('#calcClearHist');
  if(ch) ch.onclick=function(){ st().calcHist=[]; HUB.store.save(); paintHist(); };
  const dispExpr=el.querySelector('#calcExpr');
  if(dispExpr) dispExpr.addEventListener('click',function(){ /* tap-to-place: keep caret in view */
    const ta=dispExpr; setTimeout(function(){ revealCaret(ta); },30);
  });
  const rs=el.querySelector('#calcRes');
  if(rs) rs.onclick=function(){ /* tap-to-copy the live result */
    const txt=rs.textContent.replace(/^=\s*/, '');
    if(!txt||rs.classList.contains('calc-err')) return;
    copyText(txt);
  };
  paint(); paintHist();
  setView(st().calcView==='graph'?'graph':'calc'); /* restore last view; re-renders graph */
  /* physical keyboard: digits/operators/Enter/Backspace/Escape — cheap and student-friendly */
  if(!HUB.calc._kbd){
    HUB.calc._kbd=true;
    document.addEventListener('keydown',function(e){
      if(!document.getElementById('calcRoot')) return;
      if(st().calcView==='graph') return; /* graph function inputs are native text fields */
      const tag=(e.target&&e.target.tagName)||'';
      if(tag==='INPUT'||tag==='TEXTAREA'||(e.target&&e.target.isContentEditable)) return;
      const k=e.key; let id=null, ins=null;
      if(/^[0-9]$/.test(k)){ id='k'+k; ins=k; }
      else if(k==='.'){ id='dot'; ins='.'; }
      else if(k==='+'){ id='plus'; ins='+'; }
      else if(k==='-'){ id='kmin'; ins='\u2212'; }
      else if(k==='*'){ id='kmul'; ins='\u00D7'; }
      else if(k==='/'){ id='kdiv'; ins='\u00F7'; }
      else if(k==='^'){ id='kpow'; ins='^'; }
      else if(k==='x'||k==='X'){ id='kx'; ins='x'; }
      else if(k==='('){ id='lp'; ins='('; }
      else if(k===')'){ id='rp'; ins=')'; }
      else if(k==='%'){ id='pct'; ins='%'; }
      else if(k==='!'){ id='fact'; ins='!'; }
      else if(k==='Enter'||k==='='){ id='eq'; }
      else if(k==='Backspace'){ id='del'; }
      else if(k==='Escape'){ id='ac'; }
      else if(k==='ArrowUp'){ id='rpu'; } /* REPLAY: recall older */
      else if(k==='ArrowDown'){ id='rpd'; } /* REPLAY: recall newer */
      if(!id) return;
      e.preventDefault();
      press(id,ins);
    });
  }
}

/* ================= advanced function lab (sheet-based) =================
   Multi-argument operations open a small Onaro sheet with labeled fields —
   f(x), a, b in plain math notation (no translation needed). Results feed
   Ans so students can keep calculating. Trig follows the DEG/RAD mode. */
const LABDEF={
  int:{title:'\u222B f(x) dx', sub:'a \u2192 b',
    fields:[['f','f(x)','sin(x)'],['a','a','0'],['b','b','\u03C0/3']]},
  der:{title:'d/dx f(x)', sub:'at x',
    fields:[['f','f(x)','x^2'],['x','x','3']]},
  sum:{title:'\u03A3 f(x)', sub:'x = a..b',
    fields:[['f','f(x)','x'],['a','a','1'],['b','b','5']]},
  sol:{title:'f(x) = 0', sub:'find x',
    fields:[['f','f(x)','x^2-4']]},
  pol:{title:'Pol / Rec', sub:'', tabs:true,
    fields:[['p','x','3'],['q','y','4']]},
  base:{title:'BASE', sub:'integer', conv:true,
    fields:[['v','','255']]}
};
let labKind=null, labTab='pol';
function openLab(kind){ labKind=kind; labTab='pol'; renderLab(); }
function renderLab(){
  const U=ui(), d=LABDEF[labKind]; if(!d) return;
  let body='';
  if(d.tabs){
    body+='<div class="calc-seg" id="labTabs">'+
      '<button type="button" data-lt="pol" class="'+(labTab==='pol'?'on':'')+'">Pol</button>'+
      '<button type="button" data-lt="rec" class="'+(labTab==='rec'?'on':'')+'">Rec</button></div>';
  }
  let fields=d.fields;
  if(labKind==='pol') fields=(labTab==='pol')?[['p','x','3'],['q','y','4']]:[['p','r','5'],['q','\u03B8','53.13']];
  if(d.conv){
    body+='<label class="calc-fld"><input id="labV" inputmode="text" autocomplete="off" autocapitalize="off" spellcheck="false" value="'+U.esc(fields[0][2])+'"></label>'+
      '<div class="calc-seg" id="labBases">'+
      [['10','DEC'],['16','HEX'],['8','OCT'],['2','BIN']].map(function(p){
        return '<button type="button" data-lb="'+p[0]+'">'+p[1]+'</button>';
      }).join('')+'</div>';
  }else{
    body+=fields.map(function(f,i){
      return '<label class="calc-fld"><span>'+U.esc(f[1])+'</span>'+
        '<input id="labF'+i+'" inputmode="text" autocomplete="off" autocapitalize="off" spellcheck="false" value="'+U.esc(f[2])+'"></label>';
    }).join('');
  }
  const sub=(labKind==='pol')?('\u2220 '+(mode()==='deg'?'DEG':'RAD')):d.sub;
  ui().openSheet('<div class="calc-lab"><h3 class="calc-labtitle">'+U.esc(d.title)+'</h3>'+
    '<p class="calc-labsub">'+U.esc(sub)+'</p>'+body+
    (d.conv?'':'<button type="button" class="calc-key eq calc-labgo" id="labGo">=</button>')+
    '<div class="calc-labres" id="labRes" hidden></div></div>');
  bindLab();
}
function bindLab(){
  const U=ui();
  function labVal(i){ const el=document.getElementById('labF'+i); return el?el.value:''; }
  function showRes(html,isErr){
    const r=document.getElementById('labRes'); if(!r) return;
    r.hidden=false; r.innerHTML=html;
    r.classList.toggle('calc-laberr',!!isErr);
  }
  function numField(i){
    const r=evaluate(labVal(i));
    if(!r.ok) throw new CalcError(r.code);
    return r.value;
  }
  function fnField(i){
    const c=gCompile(labVal(i));
    if(!c.ok) throw new CalcError(c.code);
    return c.fn;
  }
  function copyBtn(pretty){
    return '<button type="button" class="chip calc-labcopy" id="labCopy" aria-label="Copy result">\uD83D\uDCCB</button>';
  }
  function wireCopy(pretty){
    const cp=document.getElementById('labCopy');
    if(cp) cp.onclick=function(){ copyText(pretty); };
  }
  const go=document.getElementById('labGo');
  if(go) go.onclick=function(){
    try{
      let out='', plain='';
      if(labKind==='int'){
        const v=numIntegrate(fnField(0),numField(1),numField(2));
        st().calcAns=v; HUB.store.save();
        plain=fmt(v); out='<div class="calc-labval">'+U.esc(plain)+'</div>';
      }else if(labKind==='der'){
        const v=numDeriv(fnField(0),numField(1));
        st().calcAns=v; HUB.store.save();
        plain=fmt(v); out='<div class="calc-labval">'+U.esc(plain)+'</div>';
      }else if(labKind==='sum'){
        const v=numSigma(fnField(0),numField(1),numField(2));
        st().calcAns=v; HUB.store.save();
        plain=fmt(v); out='<div class="calc-labval">'+U.esc(plain)+'</div>';
      }else if(labKind==='sol'){
        const rs=numSolve(fnField(0));
        if(!rs.length){ showRes(U.esc(t('calc.noSolution')),true); return; }
        st().calcAns=rs[0]; HUB.store.save();
        plain=rs.map(function(r){ return fmt(r); }).join(', ');
        out='<div class="calc-labval">'+rs.map(function(r,i){
          return '<div>x'+(rs.length>1?'<sub>'+(i+1)+'</sub>':'')+' = '+U.esc(fmt(r))+'</div>';
        }).join('')+'</div>';
      }else if(labKind==='pol'){
        const r=polRec(labTab,numField(0),numField(1));
        st().calcAns=r.a; HUB.store.save();
        const L1=labTab==='pol'?'r':'x', L2=labTab==='pol'?'\u03B8':'y';
        const unit=(labTab==='pol'&&mode()==='deg')?'\u00B0':'';
        plain=L1+' = '+fmt(r.a)+', '+L2+' = '+fmt(r.b)+unit;
        out='<div class="calc-labval">'+U.esc(L1)+' = '+U.esc(fmt(r.a))+'<br>'+
          U.esc(L2)+' = '+U.esc(fmt(r.b))+U.esc(unit)+'</div>';
      }
      showRes(out+copyBtn(),false); wireCopy(plain);
    }catch(e){
      showRes(U.esc(errText((e&&e.code)||'syntax')),true);
    }
  };
  const tabs=document.getElementById('labTabs');
  if(tabs) tabs.onclick=function(e){
    const b=e.target&&e.target.closest?e.target.closest('[data-lt]'):null;
    if(!b) return; labTab=b.dataset.lt; renderLab();
  };
  const bases=document.getElementById('labBases');
  if(bases) bases.onclick=function(e){
    const b=e.target&&e.target.closest?e.target.closest('[data-lb]'):null;
    if(!b) return;
    try{
      const inp=document.getElementById('labV');
      const base=+b.dataset.lb;
      const out=baseConvert(inp?inp.value:'',base);
      const pretty=base===16?'0x'+out:base===8?'0o'+out:base===2?'0b'+out:out;
      showRes('<div class="calc-labval">'+U.esc(pretty)+'</div>'+copyBtn(),false);
      wireCopy(pretty);
    }catch(err){ showRes(U.esc(errText((err&&err.code)||'syntax')),true); }
  };
}

/* ================= MODE/SETUP settings sheet =================
   Wordless where possible: ∠ for angle, 0.00 for format, π≈ preview for
   decimals. Only the title needs a translated string (calc.settings). */
function openSettings(){
  const U=ui();
  const f=st().calcFmt||'norm';
  let n=st().calcFixN; if(!(n>=0&&n<=9)) n=2;
  ui().openSheet('<div class="calc-set"><h3>'+U.esc(t('calc.settings'))+'</h3>'+
    '<div class="calc-setrow"><span class="calc-setcap" aria-hidden="true">\u2220</span>'+
      '<div class="calc-seg" id="setAng">'+
      '<button type="button" data-v="deg" class="'+(mode()==='deg'?'on':'')+'">'+U.esc(t('calc.deg'))+'</button>'+
      '<button type="button" data-v="rad" class="'+(mode()==='rad'?'on':'')+'">'+U.esc(t('calc.rad'))+'</button></div></div>'+
    '<div class="calc-setrow"><span class="calc-setcap" aria-hidden="true">0.00</span>'+
      '<div class="calc-seg" id="setFmt">'+
      '<button type="button" data-v="norm" class="'+(f==='norm'?'on':'')+'">NORM</button>'+
      '<button type="button" data-v="fix" class="'+(f==='fix'?'on':'')+'">FIX</button>'+
      '<button type="button" data-v="sci" class="'+(f==='sci'?'on':'')+'">SCI</button></div></div>'+
    '<div class="calc-setrow" id="setFixRow"'+(f==='fix'?'':' hidden')+'><span class="calc-setcap" aria-hidden="true">\u03C0 \u2248</span>'+
      '<button type="button" class="calc-stepbtn" id="setFixDn" aria-label="Fewer decimals">\u2212</button>'+
      '<b id="setFixN">'+n+'</b>'+
      '<button type="button" class="calc-stepbtn" id="setFixUp" aria-label="More decimals">+</button>'+
      '<span class="calc-setprev" id="setFixPrev">'+U.esc(fmt(Math.PI))+'</span></div>'+
    '</div>');
  function paintFix(){
    let m=st().calcFixN; if(!(m>=0&&m<=9)) m=2;
    const nn=document.getElementById('setFixN'), pv=document.getElementById('setFixPrev');
    if(nn) nn.textContent=m;
    if(pv) pv.textContent=fmt(Math.PI);
    const row=document.getElementById('setFixRow');
    if(row) row.hidden=(st().calcFmt||'norm')!=='fix';
    const seg=document.getElementById('setFmt');
    if(seg) seg.querySelectorAll('button').forEach(function(b){
      b.classList.toggle('on',b.dataset.v===(st().calcFmt||'norm'));
    });
  }
  function syncModeChips(){
    const mb=document.getElementById('calcModeBtn'), chip=document.querySelector('#calcRoot [data-ck="mode"]');
    const lbl=mode()==='deg'?t('calc.deg'):t('calc.rad');
    if(mb) mb.textContent=lbl; if(chip) chip.textContent=lbl;
  }
  const ang=document.getElementById('setAng');
  if(ang) ang.onclick=function(e){
    const b=e.target&&e.target.closest?e.target.closest('[data-v]'):null; if(!b) return;
    st().calcMode=b.dataset.v; HUB.store.save();
    ang.querySelectorAll('button').forEach(function(x){ x.classList.toggle('on',x===b); });
    syncModeChips(); paint();
    if(st().calcView==='graph') gValidateRender();
  };
  const fm=document.getElementById('setFmt');
  if(fm) fm.onclick=function(e){
    const b=e.target&&e.target.closest?e.target.closest('[data-v]'):null; if(!b) return;
    st().calcFmt=b.dataset.v; HUB.store.save(); paintFix(); paint();
  };
  const dn=document.getElementById('setFixDn'), up=document.getElementById('setFixUp');
  function step(d){
    let m=st().calcFixN; if(!(m>=0&&m<=9)) m=2;
    st().calcFixN=Math.max(0,Math.min(9,m+d)); HUB.store.save(); paintFix(); paint();
  }
  if(dn) dn.onclick=function(){ step(-1); };
  if(up) up.onclick=function(){ step(1); };
}

/* ================= graph mode =================
   Function plotter on a devicePixelRatio-aware canvas. Onaro crystal-glass
   styling, volt-first curve palette (never purple). Reuses the expression
   engine: 'x' tokenizes as a variable and parseAll evaluates with an {x}
   environment. Trig follows the current DEG/RAD mode. */
const GCOL_DARK=['#C6F135','#FF5C38','#35C6FF','#FFB800'];
const GCOL_LIGHT=['#4A7A00','#C22E1F','#0077B6','#B97A00'];
function gIsDark(){ return document.body.classList.contains('dark'); }
function gCols(){ var c=(gIsDark()?GCOL_DARK:GCOL_LIGHT).slice(); if(HUB.theme) c[0]=HUB.theme.accent(); return c; }
function gst(){
  let g=st().calcGraph;
  if(!g||typeof g!=='object'){ g={funcs:['sin(x)','x^2'],cx:0,cy:0,ppu:34}; st().calcGraph=g; }
  if(!Array.isArray(g.funcs)||!g.funcs.length) g.funcs=['sin(x)','x^2'];
  if(g.funcs.length>4) g.funcs=g.funcs.slice(0,4);
  if(typeof g.cx!=='number'||!isFinite(g.cx)) g.cx=0;
  if(typeof g.cy!=='number'||!isFinite(g.cy)) g.cy=0;
  if(typeof g.ppu!=='number'||!isFinite(g.ppu)||g.ppu<=0) g.ppu=34;
  if(typeof g.active!=='number'||g.active<0||g.active>=g.funcs.length) g.active=0;
  return g;
}
function gsave(){ try{ HUB.store.save(); }catch(e){} }
/* graph inputs are typed ASCII (iOS keyboard): map pretty symbols + 'pi' word */
function graphCanon(s){ return toCanon(String(s||'')).replace(/\bpi\b/gi,'\u03C0'); }
function gCompile(expr){
  try{
    const toks=tokenize(graphCanon(expr));
    const fn=function(xv){ return parseAll(toks,mode(),{x:xv}); };
    /* Tokenizing alone cannot catch parse-time errors ('2+*x' tokenizes fine):
       trial-evaluate at neutral points. Domain-ish failures at every trial point
       don't prove the function invalid ('1/x' at x=0, 'sqrt(x-3)' below 3), but
       syntax/paren/empty failures do. */
    const trials=[0.7,-1.3,2.1];
    for(let ti=0;ti<trials.length;ti++){
      try{ fn(trials[ti]); return {ok:1,fn:fn}; }
      catch(e){
        const code=(e&&e.code)||'syntax';
        if(code==='syntax'||code==='paren'||code==='empty') return {ok:0,code:code};
      }
    }
    return {ok:1,fn:fn}; /* valid somewhere, even if not at the trial points */
  }catch(e){ return {ok:0,code:(e&&e.code)||'syntax'}; }
}
function fmtTick(v){ const s=String(parseFloat(v.toPrecision(6))); return (s==='-0'||s==='NaN')?'0':s; }
function niceStep(ppu){
  const raw=56/ppu, mag=Math.pow(10,Math.floor(Math.log10(raw))), n=raw/mag;
  return (n<1.5?1:n<3.5?2:n<7.5?5:10)*mag;
}
function clampPpu(p){ return Math.min(3000,Math.max(3,p)); }

let gTracePt=null; /* {sx,sy,fi,xv,yv} — nearest curve point from a tap */

function gRenderRows(){
  const host=document.getElementById('calcFnRows'); if(!host) return;
  const g=gst(), cols=gCols(), U=ui();
  /* Rows are READONLY displays: tap selects the row as active (volt ring);
     the in-app keypad below the graph does all typing, so iOS never summons
     the system keyboard (readonly + inputmode="none", same as the main display). */
  host.innerHTML=g.funcs.map(function(expr,i){
    return '<div class="calc-fnrow'+(i===g.active?' act':'')+'" data-fi="'+i+'" style="--fnc:'+cols[i%4]+'">'+
      '<span class="calc-fndot" aria-hidden="true"></span>'+
      '<input class="calc-fnin" data-fi="'+i+'" value="'+U.esc(expr)+'" placeholder="f(x)" readonly '+
        'inputmode="none" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Function '+(i+1)+'">'+
      (g.funcs.length>1?'<button type="button" class="calc-fnx" data-fx="'+i+'" aria-label="Remove function '+(i+1)+'">\u00D7</button>':'<span></span>')+
      '<div class="calc-fnerr" data-fe="'+i+'"></div>'+
      '<div class="calc-fncaret" data-fc="'+i+'" aria-hidden="true" hidden></div>'+
    '</div>';
  }).join('')+
  (g.funcs.length<4?'<button type="button" class="calc-fnadd" id="calcFnAdd" aria-label="Add function">\uFF0B</button>':'');
  gValidateRender(); /* paint friendly errors for the fresh rows */
  gCaretUpdate(); /* show the custom caret on the active row */
}
function gValidateRender(){ /* no row rebuild: keeps focus while typing */
  const g=gst();
  g.funcs.forEach(function(expr,i){
    const errEl=document.querySelector('#calcFnRows [data-fe="'+i+'"]');
    const c=gCompile(expr);
    if(errEl) errEl.textContent=c.ok?'':errText(c.code);
  });
  gTracePt=null; const chip=document.getElementById('calcTrace'); if(chip) chip.hidden=true;
  gRender();
}
function gSetActive(i){
  const g=gst(); if(!g.funcs.length) return;
  g.active=Math.max(0,Math.min(i,g.funcs.length-1)); gsave();
  const host=document.getElementById('calcFnRows'); if(!host) return;
  host.querySelectorAll('.calc-fnrow').forEach(function(r){
    r.classList.toggle('act',+r.dataset.fi===g.active);
  });
  gCaretUpdate();
}
function gActiveEl(){
  const g=gst();
  const el=document.querySelector('#calcFnRows .calc-fnin[data-fi="'+g.active+'"]');
  return el||document.querySelector('#calcFnRows .calc-fnin');
}
let gDebT=0;
function gSoon(){ clearTimeout(gDebT); gDebT=setTimeout(gValidateRender,220); }
/* Keypad insert into the ACTIVE row at its cursor (readonly input: no iOS keyboard). */
function gPadIns(s){
  const el=gActiveEl(); if(!el) return;
  const a=(el.selectionStart==null)?el.value.length:el.selectionStart;
  const b=(el.selectionEnd==null)?a:el.selectionEnd;
  el.value=el.value.slice(0,a)+s+el.value.slice(b);
  const pos=a+s.length;
  try{ el.setSelectionRange(pos,pos); }catch(e){}
  try{ el.focus({preventScroll:true}); }catch(e){ try{el.focus();}catch(e2){} }
  const g=gst(); g.funcs[+el.dataset.fi]=el.value; gsave(); gSoon(); gCaretUpdate();
}
function gPadDel(){
  const el=gActiveEl(); if(!el) return;
  const a=(el.selectionStart==null)?el.value.length:el.selectionStart;
  const b=(el.selectionEnd==null)?a:el.selectionEnd;
  let v=el.value, na=a;
  if(b>a){ v=v.slice(0,a)+v.slice(b); }
  else if(a>0){ v=v.slice(0,a-1)+v.slice(a); na=a-1; }
  el.value=v;
  try{ el.setSelectionRange(na,na); }catch(e){}
  try{ el.focus({preventScroll:true}); }catch(e){ try{el.focus();}catch(e2){} }
  const g=gst(); g.funcs[+el.dataset.fi]=v; gsave(); gSoon(); gCaretUpdate();
}
/* Cursor keys: move the caret in the ACTIVE row. A selection collapses
   (left->start, right->end); at the ends the key is a no-op. Value is
   unchanged so no re-plot is triggered. */
function gPadMove(d){
  const el=gActiveEl(); if(!el) return;
  let a=(el.selectionStart==null)?el.value.length:el.selectionStart;
  const b=(el.selectionEnd==null)?a:el.selectionEnd;
  let pos=(b>a)?(d<0?a:b):a+d;
  pos=Math.max(0,Math.min(el.value.length,pos));
  try{ el.setSelectionRange(pos,pos); }catch(e){}
  try{ el.focus({preventScroll:true}); }catch(e){ try{el.focus();}catch(e2){} }
  gCaretUpdate();
}
let fnCaretCv=null;
function gCaretUpdate(){
  /* Custom blinking caret for the ACTIVE function row. iOS often refuses to
     render a native caret inside a readonly input, so we draw our own volt
     bar positioned at the text caret via canvas text measurement (the rows
     are single-line, so horizontal measurement is exact). It tracks typing,
     arrow moves, DEL and row switches, and hides on inactive rows. */
  const el=gActiveEl();
  const actRow=(el&&el.closest)?el.closest('.calc-fnrow'):null;
  document.querySelectorAll('#calcFnRows .calc-fncaret').forEach(function(cd){
    cd.hidden=!(actRow&&cd.parentNode===actRow);
  });
  if(!actRow||!el) return;
  const cd=actRow.querySelector('.calc-fncaret'); if(!cd) return;
  const a=(el.selectionStart==null)?el.value.length:el.selectionStart;
  if(!fnCaretCv) fnCaretCv=document.createElement('canvas').getContext('2d');
  const cs=getComputedStyle(el);
  fnCaretCv.font=cs.fontStyle+' '+cs.fontVariant+' '+cs.fontWeight+' '+
    cs.fontSize+'/'+cs.lineHeight+' '+cs.fontFamily;
  let w=fnCaretCv.measureText(el.value.slice(0,a)).width;
  const ls=parseFloat(cs.letterSpacing)||0;
  if(ls) w+=ls*a;
  /* keep the caret in view horizontally */
  const x=(parseFloat(cs.paddingLeft)||0)+w, vw=el.clientWidth;
  if(x-el.scrollLeft>vw-2) el.scrollLeft=Math.max(0,x-vw+10);
  else if(x-el.scrollLeft<0) el.scrollLeft=Math.max(0,x-10);
  cd.style.left=(el.offsetLeft+x-el.scrollLeft)+'px';
  /* vertical: center on the INPUT, not the row — the row grows taller when the
     friendly error line is showing, and top:50% of the row dropped the caret
     below the text (PraBin's iPhone report, 2026-09-22). */
  cd.style.top=(el.offsetTop+el.clientHeight/2)+'px';
}
function gBindRows(){
  const host=document.getElementById('calcFnRows'); if(!host||host._gb) return; host._gb=true;
  /* Tapping a row (or its input) makes it the active keypad target. */
  host.addEventListener('focusin',function(e){
    const inp=e.target&&e.target.closest?e.target.closest('.calc-fnin'):null;
    if(inp) gSetActive(+inp.dataset.fi);
  });
  /* Any caret move (tap-to-place, arrows, programmatic) re-syncs the custom bar. */
  document.addEventListener('selectionchange',function(){
    const ae=document.activeElement;
    if(ae&&ae.classList&&ae.classList.contains('calc-fnin')) gCaretUpdate();
  });
  host.addEventListener('click',function(e){
    const q=function(s){ return e.target&&e.target.closest?e.target.closest(s):null; };
    if(q('#calcFnAdd')){
      const g=gst(); if(g.funcs.length>=4) return;
      g.funcs.push(''); g.active=g.funcs.length-1; gsave(); gRenderRows();
      const inp=host.querySelector('.calc-fnin[data-fi="'+g.active+'"]');
      if(inp){ try{inp.setSelectionRange(inp.value.length,inp.value.length);}catch(e){} inp.focus({preventScroll:true}); }
      gCaretUpdate();
      return;
    }
    const x=q('[data-fx]');
    if(x){
      const g=gst(); g.funcs.splice(+x.dataset.fx,1);
      if(!g.funcs.length) g.funcs=[''];
      g.active=Math.min(g.active,g.funcs.length-1); gsave(); gTracePt=null; gRenderRows();
      const inp=host.querySelector('.calc-fnin[data-fi="'+g.active+'"]');
      if(inp){ try{inp.setSelectionRange(inp.value.length,inp.value.length);}catch(e){} inp.focus({preventScroll:true}); }
      gCaretUpdate();
      return;
    }
    const row=q('.calc-fnrow');
    if(row){
      const inp=row.querySelector('.calc-fnin');
      if(inp&&document.activeElement!==inp) inp.focus({preventScroll:true});
    }
  });
}
function gBindPad(){
  const pad=document.getElementById('calcGpad'); if(!pad||pad._gb) return; pad._gb=true;
  pad.addEventListener('click',function(e){
    const b=e.target&&e.target.closest?e.target.closest('[data-gk]'):null; if(!b) return;
    const gk=b.dataset.gk;
    if(gk==='DEL') gPadDel();
    else if(gk==='\u25C0') gPadMove(-1);
    else if(gk==='\u25B6') gPadMove(1);
    else gPadIns(gk);
  });
  /* same finger-down glow as the main keypad */
  pad.querySelectorAll('.calc-key').forEach(function(b){
    b.addEventListener('pointerdown',function(){ b.classList.add('kglow'); });
    const off=function(){ b.classList.remove('kglow'); };
    b.addEventListener('pointerup',off); b.addEventListener('pointerleave',off); b.addEventListener('pointercancel',off);
  });
}

function gRender(){
  const cv=document.getElementById('calcCanvas'); if(!cv) return;
  const dpr=window.devicePixelRatio||1;
  const W=cv.clientWidth, H=cv.clientHeight;
  if(!W||!H) return;
  const pw=Math.round(W*dpr), ph=Math.round(H*dpr);
  if(cv.width!==pw||cv.height!==ph){ cv.width=pw; cv.height=ph; }
  const ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,W,H);
  const g=gst(), cols=gCols(), dark=gIsDark();
  const gridC=dark?'rgba(255,255,255,0.08)':'rgba(20,30,10,0.08)';
  const axC=dark?'rgba(255,255,255,0.30)':'rgba(20,30,10,0.32)';
  const labC=dark?'rgba(255,255,255,0.50)':'rgba(20,30,10,0.55)';
  const step=niceStep(g.ppu);
  const x0=g.cx-(W/2)/g.ppu, x1=g.cx+(W/2)/g.ppu;
  const y0=g.cy-(H/2)/g.ppu, y1=g.cy+(H/2)/g.ppu;
  ctx.lineWidth=1; ctx.font='10px system-ui,-apple-system,sans-serif';
  /* vertical gridlines + x labels */
  ctx.textBaseline='top'; ctx.textAlign='left';
  for(let xv=Math.ceil(x0/step)*step; xv<=x1+1e-12; xv+=step){
    const sx=(xv-g.cx)*g.ppu+W/2, isAx=Math.abs(xv)<step*1e-9;
    ctx.strokeStyle=isAx?axC:gridC;
    ctx.beginPath(); ctx.moveTo(Math.round(sx)+0.5,0); ctx.lineTo(Math.round(sx)+0.5,H); ctx.stroke();
    if(!isAx&&sx>-30&&sx<W+30){ ctx.fillStyle=labC; ctx.fillText(fmtTick(xv),sx+4,H-15); }
  }
  /* horizontal gridlines + y labels */
  ctx.textBaseline='middle';
  for(let yv=Math.ceil(y0/step)*step; yv<=y1+1e-12; yv+=step){
    const sy=H/2-(yv-g.cy)*g.ppu, isAx=Math.abs(yv)<step*1e-9;
    ctx.strokeStyle=isAx?axC:gridC;
    ctx.beginPath(); ctx.moveTo(0,Math.round(sy)+0.5); ctx.lineTo(W,Math.round(sy)+0.5); ctx.stroke();
    if(!isAx&&sy>-10&&sy<H+10){ ctx.fillStyle=labC; ctx.fillText(fmtTick(yv),5,sy-8); }
  }
  /* curves: per-pixel sampling, path breaks on domain errors and asymptotes */
  const compiled=g.funcs.map(gCompile);
  ctx.lineWidth=2.4; ctx.lineJoin='round'; ctx.lineCap='round';
  compiled.forEach(function(c,fi){
    if(!c.ok) return;
    ctx.strokeStyle=cols[fi%4];
    ctx.beginPath();
    let pen=false, prevSy=0;
    for(let px=0;px<=W;px++){
      const xv=g.cx+(px-W/2)/g.ppu;
      let yv;
      try{ yv=c.fn(xv); }catch(e){ pen=false; continue; }
      if(typeof yv!=='number'||!isFinite(yv)){ pen=false; continue; }
      const sy=H/2-(yv-g.cy)*g.ppu;
      if(!pen){ ctx.moveTo(px,sy); pen=true; }
      else if(Math.abs(sy-prevSy)>H*1.5){ ctx.moveTo(px,sy); } /* asymptote: no vertical spike */
      else ctx.lineTo(px,sy);
      prevSy=sy;
    }
    ctx.stroke();
  });
  /* trace marker */
  if(gTracePt){
    const cols2=gCols(), m=gTracePt;
    ctx.beginPath(); ctx.arc(m.sx,m.sy,6,0,Math.PI*2);
    ctx.fillStyle='#fff'; ctx.fill();
    ctx.beginPath(); ctx.arc(m.sx,m.sy,4,0,Math.PI*2);
    ctx.fillStyle=cols2[m.fi%4]; ctx.fill();
  }
}

/* tap near a curve -> (x,y) readout chip. Each function is evaluated AT the
   tap's x, so the nearest point on that curve is (sx,py) and the tap picks the
   curve whose value is closest to the tap's y. */
function gTraceAt(sx,sy){
  const cv=document.getElementById('calcCanvas'); if(!cv) return null;
  const W=cv.clientWidth, H=cv.clientHeight, g=gst();
  const compiled=g.funcs.map(gCompile);
  let best=null;
  compiled.forEach(function(c,fi){
    if(!c.ok) return;
    const xv=g.cx+(sx-W/2)/g.ppu;
    let yv;
    try{ yv=c.fn(xv); }catch(e){ return; }
    if(typeof yv!=='number'||!isFinite(yv)) return;
    const py=H/2-(yv-g.cy)*g.ppu;
    if(py<-60||py>H+60) return;
    const d=Math.abs(py-sy);
    if(d<26&&(!best||d<best.d)) best={d:d,fi:fi,sx:sx,sy:py,xv:xv,yv:yv};
  });
  gTracePt=best;
  const chip=document.getElementById('calcTrace');
  if(chip){
    if(best){
      const cols=gCols();
      chip.hidden=false;
      chip.innerHTML='<span class="calc-trdot" style="background:'+cols[best.fi%4]+'"></span>'+
        '<b>f'+(best.fi+1)+'</b>&nbsp;('+fmtTick(best.xv)+', '+fmtTick(best.yv)+')';
      chip.style.left=Math.min(Math.max(best.sx+10,8),Math.max(8,W-180))+'px';
      chip.style.top=Math.min(Math.max(best.sy-38,8),Math.max(8,H-46))+'px';
    }else chip.hidden=true;
  }
  gRender();
  return best?{fi:best.fi,x:best.xv,y:best.yv}:null;
}

function gBindCanvas(){
  const cv=document.getElementById('calcCanvas'); if(!cv||cv._gb) return; cv._gb=true;
  if(!HUB.calc._grsz){
    HUB.calc._grsz=true;
    window.addEventListener('resize',function(){
      if(document.getElementById('calcCanvas')&&st().calcView==='graph') gRender();
    });
  }
  const ptrs=new Map();
  let downT=0, downX=0, downY=0, tapMoved=false;
  let panCx=0, panCy=0, pinchD0=0, pinchPpu=0, pinchCx=0, pinchCy=0, pinchMx=0, pinchMy=0;
  cv.addEventListener('pointerdown',function(e){
    try{ cv.setPointerCapture(e.pointerId); }catch(err){}
    ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});
    const g=gst();
    if(ptrs.size===1){
      downT=Date.now(); downX=e.clientX; downY=e.clientY; tapMoved=false;
      panCx=g.cx; panCy=g.cy;
    }else if(ptrs.size===2){
      const p=Array.from(ptrs.values());
      pinchD0=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)||1;
      pinchPpu=g.ppu;
      const rect=cv.getBoundingClientRect();
      pinchMx=(p[0].x+p[1].x)/2-rect.left; pinchMy=(p[0].y+p[1].y)/2-rect.top;
      pinchCx=g.cx+(pinchMx-cv.clientWidth/2)/g.ppu;  /* math coords under the midpoint */
      pinchCy=g.cy+(cv.clientHeight/2-pinchMy)/g.ppu;
      tapMoved=true;
    }
    e.preventDefault();
  });
  cv.addEventListener('pointermove',function(e){
    if(!ptrs.has(e.pointerId)) return;
    ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});
    const g=gst();
    if(ptrs.size===1){
      const dx=e.clientX-downX, dy=e.clientY-downY;
      if(Math.abs(dx)+Math.abs(dy)>6) tapMoved=true;
      if(tapMoved){ g.cx=panCx-dx/g.ppu; g.cy=panCy+dy/g.ppu; gsave(); gRender(); }
    }else if(ptrs.size===2){
      const p=Array.from(ptrs.values());
      const d=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)||1;
      g.ppu=clampPpu(pinchPpu*d/pinchD0);
      g.cx=pinchCx-(pinchMx-cv.clientWidth/2)/g.ppu;  /* midpoint stays fixed */
      g.cy=pinchCy-(cv.clientHeight/2-pinchMy)/g.ppu;
      gsave(); gRender();
    }
  });
  function endPtr(e){
    const wasTap=ptrs.size===1&&!tapMoved&&(Date.now()-downT)<500;
    ptrs.delete(e.pointerId);
    if(ptrs.size===0&&wasTap){
      const rect=cv.getBoundingClientRect();
      gTraceAt(e.clientX-rect.left,e.clientY-rect.top);
    }
  }
  cv.addEventListener('pointerup',endPtr);
  cv.addEventListener('pointercancel',function(e){ ptrs.delete(e.pointerId); });
}

function setView(v){
  st().calcView=(v==='graph')?'graph':'calc'; gsave();
  const n=document.getElementById('calcNormal'), gr=document.getElementById('calcGraph'),
        vb=document.getElementById('calcViewBtn');
  if(n) n.hidden=(v==='graph');
  if(gr) gr.hidden=(v!=='graph');
  if(vb){
    vb.innerHTML=calcViewIcon(v);
    vb.setAttribute('aria-pressed',(v==='graph')?'true':'false');
  }
  if(v==='graph'){
    gRenderRows(); gBindRows(); gBindCanvas();
    requestAnimationFrame(function(){ gRender(); });
  }else paint();
}

/* ---------------- Daily entry card + full-page overlay (2026-09-30) ----------------
   PraBin: an animated calculator entry card in the Daily tab ("daily life");
   tap opens a full page with ONLY the calculator. Reuses cardHTML()+bind();
   the Daily tab no longer embeds the calculator inline, so exactly one
   #calcRoot exists at a time (no duplicate-ID hazard for paint()/keyboard). */
function calcIconSVG(){
  var keys='', r, c, n=0;
  for(r=0;r<3;r++) for(c=0;c<3;c++){ n++;
    keys+='<rect x="'+(8+c*3)+'" y="'+(12.6+r*3.4)+'" width="2.4" height="2.4" rx="0.7" class="ce-k ce-k'+n+'"/>';
  }
  return '<svg class="ce-anim" viewBox="0 0 24 28" width="24" height="28" aria-hidden="true">'+
    '<rect x="5" y="2" width="14" height="24" rx="3.2" class="ce-body"/>'+
    '<rect x="8" y="5" width="8" height="4.8" rx="1.1" class="ce-disp"/>'+
    '<text x="12" y="8.9" text-anchor="middle" class="ce-d ce-d0">3</text>'+
    '<text x="12" y="8.9" text-anchor="middle" class="ce-d ce-d1">7</text>'+
    '<text x="12" y="8.9" text-anchor="middle" class="ce-d ce-d2">9</text>'+
    keys+
    '<rect x="8" y="23" width="8" height="2.2" rx="1.1" class="ce-eq"/></svg>';
}
function entryHTML(){
  const U=ui();
  const titleTx=U.esc(t('calc.title').replace(/^\uD83E\uDDEE\s*/, ''));
  return '<div class="hsec"><div class="hrow" id="homeCalcEntry" role="button" tabindex="0"'+
    ' aria-label="'+titleTx+'">'+
    '<span class="hrow-ico calc-entry-ico">'+calcIconSVG()+'</span>'+
    '<span class="grow"><span class="hrow-t">'+titleTx+'</span>'+
    '<span class="hrow-s">'+U.esc(t('calc.entrySub'))+'</span></span>'+
    '<span class="chev">›</span></div></div>';
}
function bindEntry(scope){
  const root=(scope&&scope.querySelector)?scope:document;
  const b=root.querySelector?root.querySelector('#homeCalcEntry'):document.getElementById('homeCalcEntry');
  if(!b) return;
  const go=function(){ openFull(); };
  b.onclick=go;
  b.onkeydown=function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
}
/* Overlay lifecycle — same mount pattern as degree/search/pulse: a .chatroot
   overlay removed from the DOM on close. Escape is captured (capture phase,
   before the calc's own keydown which maps Escape->AC, and before the app.js
   global handler): a sheet open above the overlay wins the first Escape; the
   overlay itself closes on the second. */
const CALC_OVL_ID='hubCalcRoot';
function ensureOvlClosed(){
  const old=document.getElementById(CALC_OVL_ID);
  if(old) old.remove();
  document.removeEventListener('keydown',onCalcOvlKey,true);
}
function closeFull(){ ensureOvlClosed(); }
function onCalcOvlKey(e){
  if(e.key!=='Escape') return;
  const sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden){ e.stopImmediatePropagation(); ui().closeSheet(); return; }
  e.stopImmediatePropagation(); e.preventDefault();
  closeFull();
}
function openFull(){
  ensureOvlClosed();
  ui().closeSheet();
  ['search','pulse','notifications'].forEach(function(k){ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  const U=ui();
  const titleTx=U.esc(t('calc.title').replace(/^\uD83E\uDDEE\s*/, ''));
  const app=document.getElementById('app')||document.body;
  const d=document.createElement('div');
  d.className='chatroot calcroot'; d.id=CALC_OVL_ID;
  d.innerHTML='<div class="calc-page">'+
    '<div class="calc-pagebar">'+
      '<button class="iconbtn" id="calcFullClose" aria-label="'+U.esc(t('common.close'))+'">✕</button>'+
      '<div class="calc-pagebar-t">'+titleTx+'</div>'+
      '<span class="calc-pagebar-sp"></span></div>'+
    '<div class="calc-pagebody" id="calcFullBody"></div></div>';
  app.appendChild(d);
  d.addEventListener('click',function(e){ if(e.target===d) closeFull(); });
  document.getElementById('calcFullClose').onclick=closeFull;
  document.addEventListener('keydown',onCalcOvlKey,true);
  const body=document.getElementById('calcFullBody');
  body.innerHTML=cardHTML();
  bind(body);
}

HUB.calc={
  cardHTML:cardHTML, bind:bind,
  entryHTML:entryHTML, bindEntry:bindEntry, openFull:openFull, closeFull:closeFull,
  /* QA + live-preview entry points (not user copy) */
  _eval:function(prettyExpr,md,env){ return evaluate(prettyExpr,md,env); },
  _fmt:fmt, _canon:toCanon, _press:press,
  _tokenize:function(s){ return tokenize(toCanon(s)); },
  _graph:{ state:gst, render:gRender, rows:gRenderRows, validate:gValidateRender, compile:gCompile,
    traceAt:gTraceAt, setView:setView, colors:gCols,
    pad:{ ins:gPadIns, del:gPadDel, move:gPadMove, active:gSetActive } },
  /* advanced-function QA hooks (throw plain Error on bad input) */
  _adv:{
    integ:function(f,a,b){ const c=gCompile(f); if(!c.ok) throw new Error(c.code); return numIntegrate(c.fn,a,b); },
    deriv:function(f,x){ const c=gCompile(f); if(!c.ok) throw new Error(c.code); return numDeriv(c.fn,x); },
    sigma:function(f,a,b){ const c=gCompile(f); if(!c.ok) throw new Error(c.code); return numSigma(c.fn,a,b); },
    solve:function(f){ const c=gCompile(f); if(!c.ok) throw new Error(c.code); return numSolve(c.fn); },
    polrec:polRec, base:baseConvert,
    mem:function(){ return memVal(); },
    replay:function(older){ replayNav(older); },
    lab:function(k){ openLab(k); }, settings:function(){ openSettings(); },
    advBank:function(){ return !!st().calcAdv; }
  }
};
})();
