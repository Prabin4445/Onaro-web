/* Onaro Gym Fuel — body math, fuel targets, meals, supplements, weekly progress.
   All formulas are standard, labeled as estimates: Mifflin-St Jeor (BMR),
   activity multipliers (TDEE), US Navy tape method (body fat). No medical
   claims — the app says to check with a coach/doctor. Everything stored
   only on this device. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const ui=function(){ return HUB.ui; };
const st=function(){ return HUB.store.state; };

const LB=2.20462, IN=2.54;
const ACTS=[['sedentary',1.2],['light',1.375],['moderate',1.55],['very',1.725]];
const GOALS={lose:{adj:-500,prot:2.2},maintain:{adj:0,prot:1.8},gain:{adj:300,prot:2.0}};

/* ---------- state ---------- */
function gym(){ return st().gym||null; }
function gunit(){ return (gym()&&gym().unit)||'imp'; }
function prof(){ const g=gym(); return g&&g.profile?g.profile:null; }
function saveG(g){ st().gym=g; HUB.store.save(); }
function dayStr(d){ d=d||new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }

/* ---------- display ---------- */
function dW(kg){ return gunit()==='imp'?Math.round(kg*LB)+' lb':(Math.round(kg*10)/10)+' kg'; }
function dH(cm){
  if(gunit()==='imp'){ const tin=Math.round(cm/IN); return Math.floor(tin/12)+"'"+(tin%12)+'"'; }
  return Math.round(cm)+' cm';
}
function inW(v){ return gunit()==='imp'?v/LB:v; }   /* display -> kg */
function inH(v){ return v; }                        /* height handled separately */

/* ---------- math (estimates, labeled as such) ---------- */
function bmr(p){
  const s=p.sex==='f'?-161:5;
  return 10*p.wKg+6.25*p.hCm-5*p.age+s;
}
function tdee(p){
  const m=(ACTS.find(a=>a[0]===p.act)||ACTS[1])[1];
  return bmr(p)*m;
}
function targetCal(p){ return Math.round(tdee(p)+GOALS[p.goal].adj); }
function macros(p){
  const cal=targetCal(p);
  const prot=Math.round(GOALS[p.goal].prot*p.wKg);
  const fat=Math.round(cal*0.25/9);
  const carbs=Math.max(0,Math.round((cal-prot*4-fat*9)/4));
  return {cal:cal,prot:prot,fat:fat,carbs:carbs};
}
function bmi(p){ return p.wKg/Math.pow(p.hCm/100,2); }
function bmiCat(v){
  if(v<18.5) return t('gym.bmiUnder');
  if(v<25) return t('gym.bmiOk');
  if(v<30) return t('gym.bmiOver');
  return t('gym.bmiObese');
}
function bodyFat(p){
  if(!(p.neckCm>0&&p.waistCm>0)) return null;
  if(p.sex==='f'&&!(p.hipsCm>0)) return null;
  const l10=function(x){ return Math.log(x)/Math.LN10; };
  try{
    let d;
    if(p.sex==='f') d=495/(1.29579-0.35004*l10(p.waistCm+p.hipsCm-p.neckCm)+0.22100*l10(p.hCm))-450;
    else d=495/(1.0324-0.19077*l10(p.waistCm-p.neckCm)+0.15456*l10(p.hCm))-450;
    if(!(d>2&&d<60)) return null;
    return d;
  }catch(e){ return null; }
}
/* kg per week via least squares */
function trend(logs){
  if(logs.length<2) return 0;
  const t0=new Date(logs[0].d).getTime();
  let sx=0,sy=0,sxx=0,sxy=0; const n=logs.length;
  logs.forEach(L=>{
    const x=(new Date(L.d).getTime()-t0)/864e5, y=L.w;
    sx+=x; sy+=y; sxx+=x*x; sxy+=x*y;
  });
  const den=n*sxx-sx*sx;
  if(!den) return 0;
  return (n*sxy-sx*sy)/den*7;
}
function logs(){
  const g=gym(); if(!g||!g.logs) return [];
  return g.logs.slice().sort((a,b)=>a.d<b.d?-1:1);
}

/* ---------- report ---------- */
function report(){
  const p=prof(), L=logs();
  if(!p) return {state:'noprofile'};
  if(L.length<2) return {state:'nodata'};
  const days=(new Date(L[L.length-1].d)-new Date(L[0].d))/864e5;
  if(days<6) return {state:'nodata'};
  const pw=trend(L); /* kg/week, negative = losing */
  const goal=p.goal;
  let verdict, cls;
  if(goal==='lose'){
    if(pw<=-0.3){ verdict=t('gym.onPace'); cls='good'; }
    else if(pw<0){ verdict=t('gym.slow'); cls='warn'; }
    else { verdict=t('gym.stalled'); cls='bad'; }
  }else if(goal==='gain'){
    if(pw>=0.15&&pw<=0.5){ verdict=t('gym.onPace'); cls='good'; }
    else if(pw>0.5){ verdict=t('gym.tooFast'); cls='warn'; }
    else { verdict=t('gym.wrongWay'); cls='bad'; }
  }else{
    if(Math.abs(pw)<=0.2){ verdict=t('gym.steady'); cls='good'; }
    else { verdict=t('gym.drift'); cls='warn'; }
  }
  const focus=[];
  const lastLog=L[L.length-1];
  const daysSince=(Date.now()-new Date(lastLog.d+'T12:00:00').getTime())/864e5;
  if(daysSince>10) focus.push(t('gym.tipWeigh'));
  if(!L.some(x=>x.waist>0)) focus.push(t('gym.tipWaist'));
  const toGo=p.targetKg-p.wKg;
  if(goal==='lose'&&toGo<-0.5) focus.push(t('gym.tipCut'));
  if(goal==='gain'&&toGo>0.5) focus.push(t('gym.tipBulk'));
  if(goal==='maintain'&&cls==='good') focus.push(t('gym.tipHold'));
  return {state:'ok',pw:pw,verdict:verdict,cls:cls,focus:focus,toGo:toGo,n:L.length};
}

/* ---------- weekly report: what got logged, pace vs goal, coach's orders ---------- */
var wkOff=0;
function wkBounds(off){
  const now=new Date(); now.setHours(12,0,0,0);
  const dow=(now.getDay()+6)%7; /* Monday=0 */
  const mon=new Date(now); mon.setDate(now.getDate()-dow-off*7); mon.setHours(0,0,0,0);
  const sun=new Date(mon); sun.setDate(mon.getDate()+6); sun.setHours(23,59,59,999);
  return {mon:mon,sun:sun};
}
function wkLabel(off){
  const b=wkBounds(off), f=function(d){ return d.toLocaleDateString(undefined,{month:'short',day:'numeric'}); };
  if(off===0) return t('gym.wkThis');
  if(off===1) return t('gym.wkLast');
  return f(b.mon)+' – '+f(b.sun);
}
function wkMaxOff(){
  const L=logs(); if(!L.length) return 0;
  const first=new Date(L[0].d+'T12:00:00');
  const fdow=(first.getDay()+6)%7;
  const firstMon=new Date(first); firstMon.setDate(first.getDate()-fdow); firstMon.setHours(0,0,0,0);
  const now=new Date();
  const dow=(now.getDay()+6)%7;
  const thisMon=new Date(now); thisMon.setDate(now.getDate()-dow); thisMon.setHours(0,0,0,0);
  return Math.max(0,Math.round((thisMon-firstMon)/6048e5));
}
function weekReport(off){
  const p=prof(); if(!p) return null;
  const b=wkBounds(off), imp=gunit()==='imp';
  const L=logs().filter(function(x){ const d=new Date(x.d+'T12:00:00'); return d>=b.mon&&d<=b.sun; });
  const fmtD=function(kg){ const s=(kg>=0?'+':''); return s+(imp?(kg*LB).toFixed(1)+' lb':kg.toFixed(2)+' kg'); };
  const base={label:wkLabel(off),n:L.length,off:off,maxOff:wkMaxOff(),imp:imp};
  if(!L.length) return Object.assign(base,{state:'empty'});
  const first=L[0], last=L[L.length-1], delta=last.w-first.w, sw=first.w;
  /* pace target as % of bodyweight — personalized, honest */
  let cls, ck;
  if(delta===0){ cls='warn'; ck='flat'; }
  else if(p.goal==='lose'){
    if(delta<=-0.003*sw&&delta>=-0.015*sw){ cls='good'; ck='pace'; }
    else if(delta<-0.015*sw){ cls='warn'; ck='toofast'; }
    else if(delta<0){ cls='warn'; ck='slow'; }
    else { cls='bad'; ck='wrong'; }
  }else if(p.goal==='gain'){
    if(delta>=0.0015*sw&&delta<=0.006*sw){ cls='good'; ck='pace'; }
    else if(delta>0.006*sw){ cls='warn'; ck='gainfast'; }
    else if(delta>0){ cls='warn'; ck='slow'; }
    else { cls='bad'; ck='wrong'; }
  }else{
    if(Math.abs(delta)<=0.0025*sw){ cls='good'; ck='pace'; }
    else { cls='warn'; ck='drift'; }
  }
  const paceTxt=p.goal==='lose'
    ? '−'+(imp?(0.005*sw*LB).toFixed(1)+'–'+(0.01*sw*LB).toFixed(1)+' lb':(0.005*sw).toFixed(2)+'–'+(0.01*sw).toFixed(2)+' kg')
    : p.goal==='gain'
    ? '+'+(imp?(0.002*sw*LB).toFixed(1)+'–'+(0.005*sw*LB).toFixed(1)+' lb':(0.002*sw).toFixed(2)+'–'+(0.005*sw).toFixed(2)+' kg')
    : '±'+(imp?(0.0025*sw*LB).toFixed(1)+' lb':(0.0025*sw).toFixed(2)+' kg');
  const coach=[];
  if(ck==='flat'){ coach.push(L.length===1?t('gym.cFewData'):t('gym.cFlat')); }
  else{
    if(L.length===1) coach.push(t('gym.cFewData'));
    if(ck==='toofast') coach.push(t('gym.cTooFast'));
    else if(ck==='slow') coach.push(t('gym.cStalled'));
    else if(ck==='wrong') coach.push(t('gym.cWrongWay'));
    else if(ck==='gainfast') coach.push(t('gym.cGainFast'));
    else if(ck==='drift') coach.push(t('gym.cDrift'));
    else coach.push(t('gym.cOnPace'));
  }
  if(!L.some(function(x){ return x.waist>0; })) coach.push(t('gym.cWaist'));
  /* ETA to goal at this week's pace */
  const toGo=p.targetKg-last.w;
  let eta=null, done=false;
  if(Math.abs(toGo)<0.3) done=true;
  else if(Math.abs(delta)>=0.1&&((p.goal==='lose'&&delta<0&&toGo<0)||(p.goal==='gain'&&delta>0&&toGo>0))){
    eta=Math.max(1,Math.ceil(Math.abs(toGo)/Math.abs(delta)));
  }
  return Object.assign(base,{state:'ok',delta:delta,fmtDelta:fmtD(delta),pace:paceTxt,cls:cls,coach:coach,eta:eta,done:done,
    w0:imp?Math.round(first.w*LB*10)/10:Math.round(first.w*10)/10,
    w1:imp?Math.round(last.w*LB*10)/10:Math.round(last.w*10)/10, unit:imp?'lb':'kg'});
}
function wkHTML(){
  const U=ui(), r=weekReport(wkOff);
  if(!r) return '';
  const cls=r.cls==='good'?'gy-good':r.cls==='warn'?'gy-warn':'gy-bad';
  let h='<div class="gy-wk"><h3 style="margin:0">'+U.esc(t('gym.wkReport'))+'</h3>'+
    '<div class="gy-wknav"><button class="chip" id="gWkPrev" '+(r.off>=r.maxOff?'disabled style="opacity:.35"':'')+' aria-label="previous">‹</button>'+
    '<b>'+U.esc(r.label)+'</b>'+
    '<button class="chip" id="gWkNext" '+(r.off<=0?'disabled style="opacity:.35"':'')+' aria-label="next">›</button></div>';
  if(r.state==='empty'){
    h+='<div class="gy-nodata"><span class="empty-ico">📋</span><p class="sub">'+U.esc(t('gym.wkNone'))+'</p>'+
      '<p class="hint">'+U.esc(t('gym.wkNoneHint'))+'</p></div>'+
      '<ul class="gy-focus"><li>🎯 '+U.esc(t('gym.cNoData'))+'</li></ul>';
  }else{
    h+='<div class="gy-wkrow"><span class="sub">'+U.esc(r.n===1?t('gym.wkLogged1'):t('gym.wkLogged',{n:r.n}))+'</span><b>'+U.esc(r.w0+' → '+r.w1+' '+r.unit)+'</b></div>'+
      '<div class="gy-wkrow"><span class="sub">'+U.esc(t('gym.wkChange'))+'</span><b>'+U.esc(r.fmtDelta)+'</b></div>'+
      '<div class="gy-wkrow"><span class="sub">'+U.esc(t('gym.wkPace'))+'</span><b>'+U.esc(r.pace)+'</b></div>'+
      '<div class="gy-verdict '+cls+'" style="margin-top:10px"><b>'+U.esc(r.fmtDelta)+' / '+U.esc(r.label)+'</b></div>';
    if(r.done) h+='<p class="sub" style="margin:8px 0">🎉 '+U.esc(t('gym.wkEtaDone'))+'</p>';
    else if(r.eta) h+='<p class="sub" style="margin:8px 0">🎯 '+U.esc(t('gym.wkEta',{n:r.eta}))+'</p>';
    h+='<h4 style="margin:12px 0 6px">'+U.esc(t('gym.coach'))+'</h4><ul class="gy-focus">'+
      r.coach.map(function(c){ return '<li>🎯 '+U.esc(c)+'</li>'; }).join('')+'</ul>';
  }
  return h+'</div>';
}
function bindWk(){
  const pv=document.getElementById('gWkPrev'), nx=document.getElementById('gWkNext');
  const go=function(d){ wkOff=Math.max(0,Math.min(wkMaxOff(),wkOff+d)); const el=document.getElementById('gReport'); if(el){ el.innerHTML=reportHTML(); bindWk(); } };
  if(pv) pv.onclick=function(){ go(1); };
  if(nx) nx.onclick=function(){ go(-1); };
}

/* ---------- main card ---------- */
function infoBtn(key){
  return '<button class="gy-info" data-info="'+key+'" aria-label="info">i</button>';
}
/* ---------- treadmill runner animation (replaces the emoji) ---------- */
function runnerSVG(big){
  return '<svg class="gy-run'+(big?' big':'')+'" viewBox="0 0 120 74" aria-hidden="true">'+
  '<rect x="8" y="60" width="104" height="8" rx="4" class="rn-base"/>'+
  '<line x1="14" y1="60" x2="106" y2="60" class="rn-belt"/>'+
  '<ellipse cx="58" cy="62" rx="17" ry="2.6" class="rn-shadow"/>'+
  '<g class="rn-dust"><circle cx="64" cy="58" r="2.4"/><circle cx="61" cy="58" r="1.8"/></g>'+
  '<line x1="100" y1="60" x2="94" y2="32" class="rn-post"/>'+
  '<rect x="82" y="22" width="26" height="11" rx="5.5" class="rn-console"/>'+
  '<circle cx="87.5" cy="27.5" r="2.2" class="rn-dot"/>'+
  '<g class="rn-speed"><line x1="18" y1="26" x2="32" y2="26"/><line x1="12" y1="36" x2="28" y2="36"/><line x1="20" y1="46" x2="32" y2="46"/></g>'+
  '<g class="rn-bob">'+
    '<g class="rn-sw-lb" style="transform-origin:59px 25px">'+
      '<line x1="59" y1="25" x2="50" y2="32" class="rn-limb dim"/>'+
      '<g class="rn-elb" style="transform-origin:50px 32px"><line x1="50" y1="32" x2="43" y2="28" class="rn-limb dim"/></g>'+
    '</g>'+
    '<g class="rn-th-lb" style="transform-origin:54px 39px">'+
      '<line x1="54" y1="39" x2="54" y2="50" class="rn-limb dim"/>'+
      '<g class="rn-sh-lb" style="transform-origin:54px 50px"><line x1="54" y1="50" x2="54" y2="60" class="rn-limb dim"/></g>'+
    '</g>'+
    '<line x1="61" y1="22" x2="57" y2="39" class="rn-limb"/>'+
    '<circle cx="63" cy="15" r="6" class="rn-head"/>'+
    '<g class="rn-th-rf" style="transform-origin:57px 39px">'+
      '<line x1="57" y1="39" x2="57" y2="50" class="rn-limb"/>'+
      '<g class="rn-sh-rf" style="transform-origin:57px 50px"><line x1="57" y1="50" x2="57" y2="60" class="rn-limb"/></g>'+
    '</g>'+
    '<g class="rn-sw-rf" style="transform-origin:60px 25px">'+
      '<line x1="60" y1="25" x2="69" y2="31" class="rn-limb"/>'+
      '<g class="rn-elb" style="transform-origin:69px 31px"><line x1="69" y1="31" x2="76" y2="27" class="rn-limb"/></g>'+
    '</g>'+
  '</g></svg>';
}
/* ---------- main card (draft-aware: live preview behind the setup drawer) ---------- */
function draft(){ return HUB.gym._draft||null; }
function draftValid(d){ return d&&d.age>=13&&d.age<=100&&d.wKg>20&&d.wKg<400&&d.hCm>100&&d.hCm<265&&d.targetKg>20&&d.targetKg<400; }
function draftComp(d){ let n=0; if(d.age>=13&&d.age<=100)n++; if(d.wKg>20)n++; if(d.hCm>100)n++; if(d.targetKg>20)n++; return n/4; }
function cardHTML(){
  const U=ui(), dr=draft(), p=dr||prof(), isDr=!!dr, vd=!isDr||draftValid(dr);
  let h='<div class="card gy-hero" style="margin-bottom:14px"><div class="row between"><h3 class="gy-title">'+runnerSVG()+"<span>"+t('gym.title')+'</span></h3>'+
    '<span class="row" style="gap:8px;flex-wrap:nowrap">'+
    (p?'<button class="chip" id="gyReset" style="min-height:34px;padding:6px 12px;color:#F87171" aria-label="'+U.esc(t('gym.resetT'))+'">↺ '+U.esc(t('gym.reset'))+'</button>':'')+
    '<button class="chip'+(gunit()==='met'?' on':'')+'" id="gyUnit" style="min-height:34px;padding:6px 12px">lb ⇄ kg</button></span></div>';
  if(!p){
    h+='<div class="empty" style="padding:18px 8px">'+runnerSVG(true)+
      '<p class="sub">'+U.esc(t('gym.setupSub'))+'</p>'+
      '<button class="btn btn-dark" id="gySetup">'+U.esc(t('gym.setup'))+'</button></div></div>';
    return h;
  }
  const M=macros(p), bf=bodyFat(p), b=bmi(p);
  const goalLbl=p.goal==='lose'?t('gym.toLose'):p.goal==='gain'?t('gym.toGain'):t('gym.toMaintain');
  const C=2*Math.PI*52, ringOff=vd?'0':(C*(1-(isDr?draftComp(dr):0))).toFixed(1);
  const dash=function(v){ return vd?' data-count="'+v+'"':''; };
  const num0=function(){ return vd?'0':'—'; };
  h+=
  '<div class="gy-ringwrap"><div class="gy-glow"></div>'+
    '<svg class="gy-ring" viewBox="0 0 120 120" role="img" aria-label="'+U.esc(t('gym.calTarget'))+'">'+
      '<circle cx="60" cy="60" r="52" class="gy-track"/>'+
      '<circle cx="60" cy="60" r="52" class="gy-fill" data-gy="ring" stroke-dasharray="'+C.toFixed(1)+'" stroke-dashoffset="'+ringOff+'"/>'+
      '<circle cx="60" cy="60" r="52" class="gy-sheen" stroke-dasharray="42 285" stroke-dashoffset="0"/>'+
    '</svg>'+
    '<div class="gy-ringc"><div class="gy-kcal" data-gy="kcal"'+dash(M.cal)+'>'+num0()+'</div><div class="sub">kcal / '+U.esc(t('gym.day'))+'</div>'+
    '<div class="gy-goal" data-gy="goal">'+U.esc(goalLbl)+'</div>'+(isDr?'<span class="gy-live">'+U.esc(t('gym.live'))+'</span>':'')+'</div>'+
  '</div>'+
  '<div class="gy-macros">'+
    [['gym.protein','prot',M.prot,'g','var(--volt,#C6F135)'],['gym.carbs','carbs',M.carbs,'g','#7DD3FC'],['gym.fat','fat',M.fat,'g','#F0ABFC']].map(function(mrow){
      const pct=Math.min(100,Math.round(mrow[2]/Math.max(1,M.prot+M.carbs+M.fat)*100*2.2));
      return '<div class="gy-macro"><div class="row between"><span>'+U.esc(t(mrow[0]))+'</span><b data-gy="'+mrow[1]+'"'+dash(mrow[2])+'>'+num0()+'</b><span class="sub">'+mrow[3]+'</span></div>'+
        '<div class="gy-bar"><div class="gy-barfill" data-gy="bar-'+mrow[1]+'" data-bar="'+pct+'" style="background:'+mrow[4]+'"></div></div></div>';
    }).join('')+
  '</div>'+
  '<div class="gy-stats">'+
    '<div class="gy-stat"><span class="sub">'+U.esc(t('gym.weight'))+'</span><b data-gy="weight">'+U.esc(vd?dW(p.wKg):'—')+'</b></div>'+
    '<div class="gy-stat"><span class="sub">BMI '+infoBtn('bmi')+'</span><b data-gy="bmi">'+(vd?b.toFixed(1):'—')+'</b><span class="gy-cat" data-gy="bmicat">'+U.esc(vd?bmiCat(b):'')+'</span></div>'+
    '<div class="gy-stat"><span class="sub">'+U.esc(t('gym.bodyFat'))+' '+infoBtn('bf')+'</span><b data-gy="bf">'+(bf==null?'—':bf.toFixed(1)+'%')+'</b>'+
      (bf==null?'<button class="gy-link" id="gyMeas">'+U.esc(t('gym.addMeas'))+'</button>':'')+'</div>'+
  '</div>'+
  '<div class="row" style="gap:8px;margin-top:12px;flex-wrap:wrap">'+
    '<button class="btn btn-ghost btn-sm" id="gyMeals">🍽️ '+U.esc(t('gym.meals'))+'</button>'+
    '<button class="btn btn-ghost btn-sm" id="gySupp">💊 '+U.esc(t('gym.supp'))+'</button>'+
    '<button class="btn btn-ghost btn-sm" id="gyProg">📈 '+U.esc(t('gym.progress'))+'</button>'+
    '<button class="btn btn-ghost btn-sm" id="gyEdit">✏️ '+U.esc(t('gym.edit'))+'</button>'+
  '</div>'+
  '<p class="hint" style="margin-top:10px">'+U.esc(t('gym.estNote'))+' '+infoBtn('cal')+'</p></div>';
  return h;
}
/* ---------- setup sheet ---------- */
function chipRow(name, opts, cur){
  return '<div class="row" style="gap:8px;flex-wrap:wrap;margin:6px 0 12px">'+opts.map(function(o){
    return '<button class="chip'+(o[0]===cur?' on':'')+'" data-f="'+name+'" data-v="'+o[0]+'">'+U0esc(o[1])+'</button>';
  }).join('')+'</div>';
}
function U0esc(s){ return HUB.ui.esc(s); }
/* ---------- setup: transparent right drawer, numbers update live behind it ---------- */
function tweenNum(el,to,fmt){
  if(!el) return;
  const cur=parseFloat(String(el.textContent).replace(/[^0-9.\-]/g,''));
  const from=isFinite(cur)?cur:0;
  if(el._tw) cancelAnimationFrame(el._tw);
  const t0=performance.now(), dur=450;
  const step=function(now){
    const k=Math.min(1,Math.max(0,(now-t0)/dur)), e=1-Math.pow(1-k,3);
    el.textContent=fmt(from+(to-from)*e);
    if(k<1) el._tw=requestAnimationFrame(step);
  };
  el._tw=requestAnimationFrame(step);
}
function liveUpdate(){
  const d=draft(), card=document.querySelector('.gy-hero'); if(!d||!card) return;
  const C=2*Math.PI*52;
  const q=function(nm){ return card.querySelector('[data-gy="'+nm+'"]'); };
  const ring=q('ring');
  if(draftValid(d)){
    const M=macros(d), b=bmi(d), bf=bodyFat(d);
    if(ring){ ring.style.strokeDashoffset='0'; ring.classList.remove('gy-pulse'); void ring.getBoundingClientRect(); ring.classList.add('gy-pulse'); }
    tweenNum(q('kcal'),M.cal,function(v){ return Math.round(v).toLocaleString(); });
    tweenNum(q('prot'),M.prot,function(v){ return String(Math.round(v)); });
    tweenNum(q('carbs'),M.carbs,function(v){ return String(Math.round(v)); });
    tweenNum(q('fat'),M.fat,function(v){ return String(Math.round(v)); });
    tweenNum(q('bmi'),b,function(v){ return v.toFixed(1); });
    const bfe=q('bf');
    if(bf==null){ if(bfe) bfe.textContent='—'; } else tweenNum(bfe,bf,function(v){ return v.toFixed(1)+'%'; });
    const we=q('weight'); if(we) we.textContent=dW(d.wKg);
    const cat=q('bmicat'); if(cat) cat.textContent=bmiCat(b);
    const gl=q('goal'); if(gl) gl.textContent=d.goal==='lose'?t('gym.toLose'):d.goal==='gain'?t('gym.toGain'):t('gym.toMaintain');
    const tot=Math.max(1,M.prot+M.carbs+M.fat);
    [['prot',M.prot],['carbs',M.carbs],['fat',M.fat]].forEach(function(pr){
      const be=card.querySelector('[data-gy="bar-'+pr[0]+'"]');
      if(be) be.style.width=Math.min(100,Math.round(pr[1]/tot*100*2.2))+'%';
    });
  } else {
    if(ring) ring.style.strokeDashoffset=(C*(1-draftComp(d))).toFixed(1);
    ['kcal','prot','carbs','fat','bmi','bf'].forEach(function(nm){ const e=q(nm); if(e) e.textContent='—'; });
    const cat=q('bmicat'); if(cat) cat.textContent='';
  }
}
var drawerEscH=null;
function closeDrawer(){
  HUB.gym._draft=null;
  if(drawerEscH){ document.removeEventListener('keydown',drawerEscH); drawerEscH=null; }
  ['gyBd','gyDrawer'].forEach(function(id){ const e=document.getElementById(id); if(e) e.remove(); });
}
function openSetup(){
  const U=ui(), p=prof(), imp=gunit()==='imp';
  closeDrawer();
  HUB.gym._draft=p?Object.assign({},p):{sex:'m',age:0,hCm:0,wKg:0,act:'moderate',goal:'gain',targetKg:0,neckCm:0,waistCm:0,hipsCm:0,diet:'all'};
  const d=HUB.gym._draft;
  if(!HUB.gym._tabWrapped&&HUB.showTab){
    const orig=HUB.showTab;
    HUB.showTab=function(){ closeDrawer(); return orig.apply(HUB,arguments); };
    HUB.gym._tabWrapped=true;
  }
  const dispW=function(kg){ return imp?Math.round(kg*LB*10)/10:Math.round(kg*10)/10; };
  const dispL=function(cm){ return imp?Math.round(cm/IN*10)/10:Math.round(cm*10)/10; };
  let hgtH;
  if(imp){
    let fo='', io=''; const tin=Math.round(d.hCm/IN), noH=!(d.hCm>0);
    fo='<option value=""'+(noH?' selected':'')+'>–</option>';
    for(let f=4;f<=7;f++) fo+='<option value="'+f+'"'+(!noH&&Math.floor(tin/12)===f?' selected':'')+'>'+f+'</option>';
    for(let i=0;i<12;i++) io+='<option value="'+i+'"'+(tin%12===i?' selected':'')+'>'+i+'</option>';
    hgtH='<div class="row" style="gap:8px"><div class="field grow"><label>'+U.esc(t('gym.ft'))+'</label><select class="input" id="fFt">'+fo+'</select></div>'+
         '<div class="field grow"><label>'+U.esc(t('gym.in'))+'</label><select class="input" id="fIn">'+io+'</select></div></div>';
  }else{
    hgtH='<div class="field"><label>'+U.esc(t('gym.height'))+' (cm)</label><input class="input" id="fHcm" type="number" min="120" max="230" inputmode="decimal" value="'+(d.hCm>0?Math.round(d.hCm):'')+'"></div>';
  }
  const dr=document.createElement('aside'); dr.className='gy-drawer'; dr.id='gyDrawer';
  dr.innerHTML=
    '<div class="row between" style="margin-bottom:2px"><h2 class="gy-title">'+runnerSVG()+"<span>"+U.esc(t('gym.setup'))+'</span></h2><button class="gy-x" id="gyX" aria-label="close">✕</button></div>'+
    '<p class="hint" style="margin-bottom:12px">'+U.esc(t('gym.draftHint'))+'</p>'+
    '<div class="field"><label>'+U.esc(t('gym.sex'))+'</label></div>'+
    chipRow('sex',[[ 'm',t('gym.male')],['f',t('gym.female')]],d.sex)+
    '<div class="row" style="gap:8px">'+
      '<div class="field grow"><label>'+U.esc(t('gym.age'))+'</label><input class="input" id="fAge" type="number" min="13" max="100" inputmode="numeric" value="'+(d.age>0?d.age:'')+'"></div>'+
      '<div class="field grow"><label>'+U.esc(t('gym.weight'))+' ('+(imp?'lb':'kg')+')</label><input class="input" id="fW" type="number" min="20" max="400" inputmode="decimal" value="'+(d.wKg>0?dispW(d.wKg):'')+'"></div>'+
    '</div>'+hgtH+
    '<div class="field"><label>'+U.esc(t('gym.activity'))+'</label></div>'+
    chipRow('act',[[ 'sedentary',t('gym.act1')],['light',t('gym.act2')],['moderate',t('gym.act3')],['very',t('gym.act4')]],d.act)+
    '<div class="field"><label>'+U.esc(t('gym.goal'))+'</label></div>'+
    chipRow('goal',[[ 'lose',t('gym.goalLose')],['maintain',t('gym.goalMaintain')],['gain',t('gym.goalGain')]],d.goal)+
    '<div class="field"><label>'+U.esc(t('gym.diet'))+'</label></div>'+
    chipRow('diet',[[ 'all',t('gym.dietAll')],['nobeefpork',t('gym.dietNoBP')],['veg',t('gym.dietVeg')],['vegan',t('gym.dietVegan')]],d.diet||'all')+
    '<div class="field"><label>'+U.esc(t('gym.target'))+' ('+(imp?'lb':'kg')+')</label><input class="input" id="fT" type="number" min="20" max="400" inputmode="decimal" value="'+(d.targetKg>0?dispW(d.targetKg):'')+'"></div>'+
    '<div class="field"><label>'+U.esc(t('gym.measOpt'))+'</label></div>'+
    '<div class="row" style="gap:8px">'+
      '<div class="field grow"><label>'+U.esc(t('gym.neck'))+' ('+(imp?'in':'cm')+')</label><input class="input" id="fNeck" type="number" min="10" max="80" inputmode="decimal" value="'+(d.neckCm>0?dispL(d.neckCm):'')+'"></div>'+
      '<div class="field grow"><label>'+U.esc(t('gym.waist'))+' ('+(imp?'in':'cm')+')</label><input class="input" id="fWaist" type="number" min="20" max="200" inputmode="decimal" value="'+(d.waistCm>0?dispL(d.waistCm):'')+'"></div>'+
    '</div>'+
    '<button class="btn btn-dark" id="fSave" style="width:100%;margin:12px 0 6px">'+U.esc(t('gym.savePlan'))+'</button>';
  const bd=document.createElement('div'); bd.className='gy-bd'; bd.id='gyBd';
  document.body.appendChild(bd); document.body.appendChild(dr);
  if(drawerEscH) document.removeEventListener('keydown',drawerEscH);
  drawerEscH=function(e){ if(e.key==='Escape') closeDrawer(); };
  document.addEventListener('keydown',drawerEscH);
  requestAnimationFrame(function(){ requestAnimationFrame(function(){ bd.classList.add('show'); dr.classList.add('show'); }); });
  rerender();
  setTimeout(function(){ const c=document.querySelector('.gy-hero'); if(c) c.scrollIntoView({block:'center'}); },150);
  let deb=null;
  const live=function(){ if(deb) clearTimeout(deb); deb=setTimeout(liveUpdate,160); };
  const num=function(id){ const e=document.getElementById(id); const v=e?parseFloat(e.value):NaN; return isNaN(v)?0:v; };
  const readAll=function(){
    d.age=Math.round(num('fAge')); d.wKg=inW(num('fW')); d.targetKg=inW(num('fT'));
    if(imp){ const ft=num('fFt'); d.hCm=ft>0?(ft*12+num('fIn'))*IN:0; } else d.hCm=num('fHcm');
    const nIn=num('fNeck'), wIn=num('fWaist');
    d.neckCm=nIn>0?(imp?nIn*IN:nIn):0; d.waistCm=wIn>0?(imp?wIn*IN:wIn):0;
  };
  dr.querySelectorAll('input,select').forEach(function(e){
    e.addEventListener('input',function(){ readAll(); live(); });
    e.addEventListener('change',function(){ readAll(); live(); });
  });
  dr.querySelectorAll('[data-f]').forEach(function(b){
    b.onclick=function(){
      d[b.dataset.f]=b.dataset.v;
      b.parentElement.querySelectorAll('.chip').forEach(function(x){ x.classList.toggle('on',x===b); });
      liveUpdate();
    };
  });
  const done=function(saved){
    closeDrawer(); rerender();
    if(saved) ui().toast(t('gym.planSaved'));
  };
  document.getElementById('gyX').onclick=function(){ done(false); };
  bd.onclick=function(){ done(false); };
  document.getElementById('fSave').onclick=function(){
    readAll();
    if(!draftValid(d)){ ui().toast(t('gym.needAll')); return; }
    const g=gym()||{}; g.unit=gunit(); g.profile=Object.assign({},d);
    if(!g.logs) g.logs=[];
    saveG(g); done(true);
  };
}
function rerender(){
  const v=document.getElementById('view-daily');
  if(v&&HUB.views&&HUB.views.daily) HUB.views.daily.render(v);
}

/* ---------- info sheets ---------- */
const INFOS={bmr:['gym.iBmr','gym.iBmrT'],tdee:['gym.iTdee','gym.iTdeeT'],cal:['gym.iCal','gym.iCalT'],bmi:['gym.iBmi','gym.iBmiT'],bf:['gym.iBf','gym.iBfT'],protein:['gym.iProtein','gym.iProteinT']};
function openInfo(key){
  const U=ui(), pair=INFOS[key]; if(!pair) return;
  U.openSheet('<h2>'+U.esc(t(pair[0]))+'</h2><p style="margin-top:10px;line-height:1.55">'+U.esc(t(pair[1]))+'</p>');
}
/* ---------- reset: wipe setup + measurements + progress, return to setup ---------- */
function openResetConfirm(){
  const U=ui();
  U.openSheet('<h2>↺ '+U.esc(t('gym.resetT'))+'</h2>'+
    '<p class="sub" style="margin:10px 0 16px;line-height:1.55">'+U.esc(t('gym.resetC'))+'</p>'+
    '<div class="row" style="gap:8px">'+
    '<button class="btn btn-dark" id="gyResetGo" style="flex:1;background:#DC2626;border-color:#DC2626">↺ '+U.esc(t('gym.reset'))+'</button>'+
    '<button class="btn btn-ghost" id="gyResetNo" style="flex:1">'+U.esc(t('common.cancel'))+'</button></div>');
  document.getElementById('gyResetGo').onclick=function(){
    const unit=gunit();
    HUB.gym._draft=null;
    saveG({unit:unit}); /* keep the lb/kg display pref; setup, measurements and logs wiped */
    U.closeSheet(); rerender();
  };
  document.getElementById('gyResetNo').onclick=function(){ U.closeSheet(); };
}

/* ---------- smart day-plan generator (on-device, from your targets) ----------
   Foods carry a cuisine tag: 'all' = universal, 'us' = American staples,
   'in' = Indian staples. The plan filters by the user's selected country so
   US users see American dishes, IN/NP/PK/BD/LK users see Indian dishes,
   and everyone else sees the full list. */
function foodCui(){
  const cc=((HUB.i18n.getCountry()||HUB.i18n.guessCountry()||'US')+'').toUpperCase();
  if(cc==='US') return 'us';
  if(cc==='IN'||cc==='NP'||cc==='PK'||cc==='BD'||cc==='LK') return 'in';
  return null;
}
const FOODS=[
 {n:'gym.fd1', kcal:420, prot:32, diets:['all','nobeefpork','veg'], slots:['B'], cui:'all'},
 {n:'gym.fd2', kcal:380, prot:24, diets:['all','nobeefpork','veg','vegan'], slots:['B'], cui:'all'},
 {n:'gym.fd3', kcal:400, prot:28, diets:['all','nobeefpork','veg'], slots:['B'], cui:'all'},
 {n:'gym.fd4', kcal:410, prot:26, diets:['all','nobeefpork','veg'], slots:['B'], cui:'in'},
 {n:'gym.fd5', kcal:650, prot:50, diets:['all','nobeefpork'], slots:['L'], cui:'all'},
 {n:'gym.fd6', kcal:600, prot:24, diets:['all','nobeefpork','veg','vegan'], slots:['L'], cui:'in'},
 {n:'gym.fd7', kcal:620, prot:32, diets:['all','nobeefpork','veg'], slots:['L'], cui:'in'},
 {n:'gym.fd8', kcal:580, prot:45, diets:['all','nobeefpork'], slots:['L'], cui:'all'},
 {n:'gym.fd9', kcal:640, prot:44, diets:['all'], slots:['L'], cui:'all'},
 {n:'gym.fd10',kcal:300, prot:27, diets:['all','nobeefpork','veg'], slots:['P'], cui:'all'},
 {n:'gym.fd11',kcal:280, prot:10, diets:['all','nobeefpork','veg','vegan'], slots:['P'], cui:'all'},
 {n:'gym.fd12',kcal:220, prot:4,  diets:['all','nobeefpork','veg','vegan'], slots:['P'], cui:'all'},
 {n:'gym.fd13',kcal:520, prot:48, diets:['all','nobeefpork'], slots:['D'], cui:'all'},
 {n:'gym.fd14',kcal:560, prot:42, diets:['all','nobeefpork'], slots:['D'], cui:'all'},
 {n:'gym.fd15',kcal:480, prot:22, diets:['all','nobeefpork','veg','vegan'], slots:['D'], cui:'all'},
 {n:'gym.fd16',kcal:540, prot:30, diets:['all','nobeefpork','veg'], slots:['D'], cui:'in'},
 {n:'gym.fd17',kcal:220, prot:26, diets:['all','nobeefpork','veg'], slots:['E'], cui:'all'},
 {n:'gym.fd18',kcal:250, prot:14, diets:['all','nobeefpork','veg','vegan'], slots:['E'], cui:'all'},
 {n:'gym.fd19',kcal:200, prot:20, diets:['all','nobeefpork','veg'], slots:['E'], cui:'all'},
 {n:'gym.fd20',kcal:380, prot:28, diets:['all','nobeefpork','veg'], slots:['B'], cui:'us'},
 {n:'gym.fd21',kcal:450, prot:30, diets:['all','nobeefpork','veg'], slots:['B'], cui:'us'},
 {n:'gym.fd22',kcal:640, prot:48, diets:['all','nobeefpork'], slots:['L'], cui:'us'},
 {n:'gym.fd23',kcal:600, prot:42, diets:['all','nobeefpork'], slots:['L'], cui:'us'},
 {n:'gym.fd24',kcal:560, prot:44, diets:['all','nobeefpork'], slots:['D'], cui:'us'},
 {n:'gym.fd25',kcal:520, prot:40, diets:['all','nobeefpork'], slots:['D'], cui:'us'}
];
function dietName(d){ return t(d==='vegan'?'gym.dietVegan':d==='veg'?'gym.dietVeg':d==='nobeefpork'?'gym.dietNoBP':'gym.dietAll'); }
function genPlan(){
  const p=prof(), M=macros(p), diet=p.diet||'all', cui=foodCui();
  const budget={B:.25,L:.30,P:.10,D:.25,E:.10};
  const plan={};
  ['B','L','P','D','E'].forEach(function(s){
    let cands=FOODS.filter(function(f){ return f.slots.indexOf(s)>=0&&f.diets.indexOf(diet)>=0; });
    if(cui) cands=cands.filter(function(f){ return f.cui==='all'||f.cui===cui; });
    if(!cands.length) cands=FOODS.filter(function(f){ return f.slots.indexOf(s)>=0&&f.diets.indexOf(diet)>=0; });
    const c=cands.slice().sort(function(){ return Math.random()-.5; });
    const items=[]; let k=0; const target=M.cal*budget[s];
    for(let i=0;i<c.length&&items.length<3;i++){
      if(k>=target*0.9) break;
      items.push(c[i]); k+=c[i].kcal;
    }
    if(!items.length&&c.length) items.push(c[0]);
    plan[s]=items;
  });
  return plan;
}
function planHTML(plan){
  const U=ui(), p=prof(), M=macros(p);
  const slotNames={B:t('gym.breakfast'),L:t('gym.lunch'),P:t('gym.prework'),D:t('gym.dinner'),E:t('gym.evening')};
  let tk=0, tp=0, h='';
  ['B','L','P','D','E'].forEach(function(s){
    const items=plan[s]||[];
    const sk=items.reduce(function(a,f){ return a+f.kcal; },0), sp=items.reduce(function(a,f){ return a+f.prot; },0);
    tk+=sk; tp+=sp;
    h+='<div class="gy-meal"><div class="row between"><span class="sub">'+U.esc(slotNames[s])+'</span><span class="sub">≈'+sk+' kcal · '+sp+'g '+U.esc(t('gym.protein'))+'</span></div>'+
      items.map(function(f){ return '<div class="gy-food">🍽️ '+U.esc(t(f.n))+' <span class="sub">≈'+f.kcal+' kcal · '+f.prot+'g</span></div>'; }).join('')+'</div>';
  });
  const kd=Math.round((tk-M.cal)/M.cal*100), pd=Math.round(tp-M.prot);
  h+='<div class="gy-totals"><b>'+U.esc(t('gym.dayTot'))+'</b><span>≈'+tk.toLocaleString()+' / '+M.cal.toLocaleString()+' kcal ('+(kd>=0?'+':'')+kd+'%)</span>'+
    '<span>'+tp+'g / '+M.prot+'g '+U.esc(t('gym.protein'))+' ('+(pd>=0?'+':'')+pd+'g)</span></div>';
  h+='<p class="hint">'+U.esc(t('gym.genNote'))+'</p>';
  return h;
}
/* ---------- meals ---------- */
function mealKey(slot){ return 'gym.m'+prof().goal[0].toUpperCase()+prof().goal.slice(1)+slot; }
function openMeals(){
  const U=ui(), p=prof(); if(!p) return;
  const goalName=p.goal==='lose'?t('gym.goalLose'):p.goal==='gain'?t('gym.goalGain'):t('gym.goalMaintain');
  const slots=['B','L','P','D','E'];
  const slotNames={B:t('gym.breakfast'),L:t('gym.lunch'),P:t('gym.prework'),D:t('gym.dinner'),E:t('gym.evening')};
  let h='<h2>🍽️ '+U.esc(t('gym.mealsT',{g:goalName}))+'</h2><p class="sub" style="margin:6px 0 12px">'+U.esc(t('gym.mealsSub'))+'</p>';
  h+='<div class="gy-gen"><div class="row between" style="margin-bottom:8px"><b>✨ '+U.esc(t('gym.genT'))+'</b><span class="chip on">'+U.esc(dietName(p.diet||'all'))+'</span></div>'+
    '<div id="gyPlan"></div>'+
    '<div class="row" style="gap:8px;margin-top:8px"><button class="btn btn-dark btn-sm" id="gyGenBtn" style="flex:1">'+U.esc(t('gym.genBtn'))+'</button>'+
    '<button class="btn btn-ghost btn-sm" id="gyShuffle" style="display:none">🔀 '+U.esc(t('gym.shuffle'))+'</button></div></div>';
  h+=slots.map(function(s){
    return '<div class="gy-meal"><div class="sub">'+U.esc(slotNames[s])+'</div><b>'+U.esc(t(mealKey(s)))+'</b></div>';
  }).join('');
  h+='<h3 style="margin:16px 0 8px">👨‍🍳 '+U.esc(t('gym.recipes'))+'</h3>';
  /* US users get the American chili recipe instead of dal; everyone else keeps dal. */
  const rIdx=foodCui()==='us'?[1,2,5,4]:[1,2,3,4];
  h+=rIdx.map(function(i){
    return '<div class="gy-recipe"><div class="row between"><b>'+U.esc(t('gym.r'+i+'t'))+'</b><span class="sub">≈ '+U.esc(t('gym.r'+i+'n'))+'</span></div>'+
      '<div class="sub" style="margin:6px 0"><b>'+U.esc(t('gym.ing'))+':</b> '+U.esc(t('gym.r'+i+'i'))+'</div>'+
      '<div class="sub">'+U.esc(t('gym.r'+i+'s'))+'</div></div>';
  }).join('');
  U.openSheet(h);
  const renderPlan=function(){ document.getElementById('gyPlan').innerHTML=planHTML(genPlan()); };
  document.getElementById('gyGenBtn').onclick=function(){ renderPlan(); document.getElementById('gyShuffle').style.display=''; };
  document.getElementById('gyShuffle').onclick=renderPlan;
}

/* ---------- supplements ---------- */
/* evidence: evStrong = strong human evidence, evMod = moderate, evLim = limited */
const SUPP_SECS=[
 ['gym.supSecPerf',['creatine','caffeine','betaalanine','citrulline']],
 ['gym.supSecDaily',['whey','vitd','mag','zinc','omega3']],
 ['gym.supSecSkin',['collagen','vitc','hyal']]
];
const SUPP_EV={creatine:'evStrong',caffeine:'evStrong',betaalanine:'evMod',citrulline:'evMod',whey:'evStrong',vitd:'evStrong',mag:'evMod',zinc:'evStrong',omega3:'evMod',collagen:'evMod',vitc:'evStrong',hyal:'evLim'};
function suppName(id){ return id==='creatine'?t('gym.creatine'):id==='whey'?t('gym.whey'):t('gym.su_'+id); }
function suppText(id){ return id==='creatine'?t('gym.creatineT'):id==='whey'?t('gym.wheyT'):t('gym.su_'+id+'t'); }
function openSupp(){
  const U=ui();
  let h='<h2>💊 '+U.esc(t('gym.supp'))+'</h2><p class="hint" style="margin:8px 0 12px">'+U.esc(t('gym.suppNote'))+'</p>';
  SUPP_SECS.forEach(function(sec){
    h+='<h3 style="margin:16px 0 8px">'+U.esc(t(sec[0]))+'</h3>';
    sec[1].forEach(function(id){
      const ev=SUPP_EV[id]||'evMod';
      h+='<div class="gy-supp"><div class="row between"><b>'+U.esc(suppName(id))+'</b>'+
        '<span class="row" style="gap:6px"><span class="gy-ev gy-'+ev+'">'+U.esc(t('gym.'+ev))+'</span>'+infoBtn(id)+'</span></div>'+
        '<p class="sub" style="margin-top:6px;line-height:1.55">'+U.esc(suppText(id))+'</p></div>';
    });
  });
  U.openSheet(h);
}
const SUPP_INFO={creatine:['gym.creatine','gym.creatineT'],whey:['gym.whey','gym.wheyT'],
 caffeine:['gym.su_caffeine','gym.su_caffeinet'],betaalanine:['gym.su_betaalanine','gym.su_betaalaninet'],
 citrulline:['gym.su_citrulline','gym.su_citrullinet'],vitd:['gym.su_vitd','gym.su_vitdt'],
 mag:['gym.su_mag','gym.su_magt'],zinc:['gym.su_zinc','gym.su_zinct'],omega3:['gym.su_omega3','gym.su_omega3t'],
 collagen:['gym.su_collagen','gym.su_collagent'],vitc:['gym.su_vitc','gym.su_vitct'],hyal:['gym.su_hyal','gym.su_hyalt']};

/* ---------- progress ---------- */
function openProgress(){
  const U=ui(), p=prof(); if(!p) return;
  const L=logs(), imp=gunit()==='imp';
  const last=L.length?L[L.length-1]:null;
  U.openSheet('<h2>📈 '+U.esc(t('gym.progress'))+'</h2>'+
    '<div class="row" style="gap:8px;margin:12px 0">'+
      '<div class="field grow"><label>'+U.esc(t('gym.logW'))+' ('+(imp?'lb':'kg')+')</label><input class="input" id="gW" type="number" inputmode="decimal" value="'+(last?(imp?Math.round(last.w*LB*10)/10:Math.round(last.w*10)/10):(imp?Math.round(p.wKg*LB*10)/10:Math.round(p.wKg*10)/10))+'"></div>'+
      '<div class="field grow"><label>'+U.esc(t('gym.logWaist'))+' ('+(imp?'in':'cm')+', '+U.esc(t('gym.opt'))+')</label><input class="input" id="gWaist" type="number" inputmode="decimal" value="'+(last&&last.waist?(imp?Math.round(last.waist/IN*10)/10:Math.round(last.waist*10)/10):'')+'"></div>'+
    '</div>'+
    '<button class="btn btn-dark" id="gSaveLog" style="width:100%">'+U.esc(t('gym.logSave'))+'</button>'+
    '<div id="gReport" style="margin-top:14px">'+reportHTML()+'</div>'
  );
  bindWk();
  document.getElementById('gSaveLog').onclick=function(){
    const U2=ui();
    const wEl=document.getElementById('gW'), wsEl=document.getElementById('gWaist');
    const w=parseFloat(wEl.value), ws=parseFloat(wsEl.value);
    if(!(w>0)){ U2.toast(t('gym.needAll')); return; }
    const g=gym(); const entry={d:dayStr(),w:inW(w),waist:(ws>0?(imp?ws*IN:ws):0)};
    const ix=g.logs.findIndex(function(x){ return x.d===entry.d; });
    if(ix>=0) g.logs[ix]=entry; else g.logs.push(entry);
    saveG(g); U2.closeSheet(); openProgress(); rerender(); U2.toast('📈 '+t('gym.logSaved'));
  };
}
function reportHTML(){
  const U=ui(), r=report(), p=prof();
  if(r.state==='noprofile') return '';
  if(r.state!=='ok'){
    return '<div class="gy-nodata"><span class="empty-ico">📊</span><p class="sub">'+U.esc(t('gym.noData'))+'</p>'+
      '<p class="hint">'+U.esc(t('gym.noDataHint'))+'</p></div>'+wkHTML();
  }
  const L=logs().slice(-12);
  const ws=L.map(function(x){ return x.w; });
  const mn=Math.min.apply(null,ws), mx=Math.max.apply(null,ws), pad=Math.max(0.5,(mx-mn)*0.3);
  const W=320, H=120;
  const pts=L.map(function(x,i){
    const px=8+i*(W-16)/Math.max(1,L.length-1);
    const py=H-10-((x.w-(mn-pad))/((mx+pad)-(mn-pad)))*(H-20);
    return [px.toFixed(1),py.toFixed(1)];
  });
  const line=pts.map(function(q){ return q.join(','); }).join(' ');
  const area=line+' '+(W-8)+','+(H-6)+' 8,'+(H-6);
  const cls=r.cls==='good'?'gy-good':r.cls==='warn'?'gy-warn':'gy-bad';
  let h='<div class="gy-chart"><svg viewBox="0 0 '+W+' '+H+'" style="width:100%">'+
    '<polygon points="'+area+'" class="gy-area"/>'+
    '<polyline points="'+line+'" class="gy-line gy-draw"/></svg>'+
    '<div class="row between"><span class="sub">'+U.esc(dW(mn))+'</span><span class="sub">'+U.esc(dW(mx))+'</span></div></div>';
  const rateStr=(r.pw>=0?'+':'')+(gunit()==='imp'?(r.pw*LB).toFixed(1)+' lb':r.pw.toFixed(2)+' kg')+'/'+t('gym.wk');
  h+='<div class="gy-verdict '+cls+'"><b>'+U.esc(r.verdict)+'</b><span class="sub"> · '+U.esc(rateStr)+'</span></div>';
  const toGoTxt=r.toGo===0?'':(p.goal==='lose'?t('gym.toGo',{x:dW(-r.toGo)}):p.goal==='gain'?t('gym.toGo',{x:dW(r.toGo)}):'');
  if(toGoTxt) h+='<p class="sub" style="margin:8px 0">🎯 '+U.esc(toGoTxt)+'</p>';
  if(r.focus.length){
    h+='<h3 style="margin:12px 0 6px">🔧 '+U.esc(t('gym.focus'))+'</h3><ul class="gy-focus">'+
      r.focus.map(function(f){ return '<li>'+U.esc(f)+'</li>'; }).join('')+'</ul>';
  }
  h+='<p class="hint" style="margin-top:8px">'+U.esc(t('gym.nEntries',{n:r.n}))+'</p>';
  h+=wkHTML();
  return h;
}

/* ---------- animations + bindings ---------- */
function animateNums(el){
  el.querySelectorAll('[data-count]').forEach(function(n){
    const to=parseFloat(n.dataset.count), t0=performance.now(), dur=900;
    const step=function(now){
      const k=Math.min(1,Math.max(0,(now-t0)/dur)), e=1-Math.pow(1-k,3);
      n.textContent=Math.round(to*e).toLocaleString();
      if(k<1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
  el.querySelectorAll('[data-bar]').forEach(function(b){
    requestAnimationFrame(function(){ requestAnimationFrame(function(){ b.style.width=b.dataset.bar+'%'; }); });
  });
  el.querySelectorAll('[data-gy="ring"]').forEach(function(r){
    const C=parseFloat(r.getAttribute('stroke-dasharray'));
    const d=draft(), off=(d&&!draftValid(d))?(C*(1-draftComp(d))).toFixed(1):'0';
    requestAnimationFrame(function(){ requestAnimationFrame(function(){ r.style.strokeDashoffset=off; }); });
  });
}
function bind(el){
  const U=ui();
  animateNums(el);
  const un=document.getElementById('gyUnit');
  if(un) un.onclick=function(){ const g=gym()||{}; g.unit=gunit()==='imp'?'met':'imp'; saveG(g); rerender(); };
  const rs=document.getElementById('gyReset'); if(rs) rs.onclick=openResetConfirm;
  const su=document.getElementById('gySetup'); if(su) su.onclick=openSetup;
  const ed=document.getElementById('gyEdit'); if(ed) ed.onclick=openSetup;
  const me=document.getElementById('gyMeas'); if(me) me.onclick=openSetup;
  const ml=document.getElementById('gyMeals'); if(ml) ml.onclick=openMeals;
  const sp=document.getElementById('gySupp'); if(sp) sp.onclick=openSupp;
  const pr=document.getElementById('gyProg'); if(pr) pr.onclick=openProgress;
  el.querySelectorAll('[data-info]').forEach(function(b){
    b.onclick=function(){
      const k=b.dataset.info;
      if(SUPP_INFO[k]){ const U2=ui(); U2.openSheet('<h2>'+U2.esc(t(SUPP_INFO[k][0]))+'</h2><p style="margin-top:10px;line-height:1.55">'+U2.esc(t(SUPP_INFO[k][1]))+'</p>'); }
      else openInfo(k);
    };
  });
}

HUB.gym={cardHTML:cardHTML,bind:bind,openSetup:openSetup};

/* tap the runner: sprint burst for ~1.4s (pure delight, no data involved) */
document.addEventListener('click',function(e){
  const s=e.target&&e.target.closest?e.target.closest('.gy-run'):null;
  if(!s) return;
  s.classList.add('sprinting');
  clearTimeout(s._sprintT);
  s._sprintT=setTimeout(function(){ s.classList.remove('sprinting'); },1400);
});
})();
