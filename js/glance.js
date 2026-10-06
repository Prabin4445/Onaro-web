/* HUB HOME: "Today at a glance" — an auto-rotating water-glass stat carousel.
   Sits directly above the "Your classes" card. Tile numbers live-update from
   store state: repainted on every Home render plus a debounced hook on
   store.save, so adding a bill / reading a message / logging an event
   updates the tiles without leaving Home.
   Auto-rotation advances ~every 4s, pauses the moment the finger touches the
   strip, and resumes after 10s idle (never fights the swipe). Tap-vs-swipe is
   disambiguated by pointer distance (10px), same convention as the rest of
   Home. Tapping a tile opens its detail sheet (or the relevant view).
   Numbers are browser-local demo data until the user adds their own —
   the honest sample line stays under the carousel. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
function esc(s){ return ui.esc(s); }

/* stylesheet injection — keeps the index.html edit surface to script lines */
(function(){
  if(document.querySelector('link[data-glance-css]')) return;
  const l=document.createElement('link');
  l.rel='stylesheet'; l.href='css/glance.css'; l.setAttribute('data-glance-css','1');
  document.head.appendChild(l);
})();

const DAY=86400e3;
function docsNeedingAttention(){
  const now=Date.now();
  return (store.state.memory||[]).filter(function(m){ return m.expiry && (m.expiry-now)<=45*DAY; });
}

/* ---- data snapshot behind the tiles ---- */
function snapshot(){
  const st=store.state, owed=store.householdOwed();
  const unread=store.unreadCount();
  const openJobs=(st.jobs||[]).filter(function(j){ return j.status==='open'; });
  const docs=docsNeedingAttention();
  const events=st.events||[];
  const nowD=new Date();
  const dayStart=new Date(nowD.getFullYear(),nowD.getMonth(),nowD.getDate()).getTime();
  const monthStart=new Date(nowD.getFullYear(),nowD.getMonth(),1).getTime();
  let spentToday=0, spentMonth=0;
  for(const hh of (st.households||[])) for(const b of (hh.bills||[])){
    const amt=Number(b.amount)||0, at=Number(b.at)||0;
    if(amt<=0||!at) continue;
    if(at>=dayStart) spentToday+=amt;
    if(at>=monthStart) spentMonth+=amt;
  }
  const sampleBits=[openJobs,events,docs].flat();
  return {owed:owed,unread:unread,openJobs:openJobs,docs:docs,events:events,
    spentToday:spentToday,spentMonth:spentMonth,
    allSample:sampleBits.length>0 && sampleBits.every(function(x){ return x.sample; })};
}

/* ---- tile definitions (static parts) ---- */
var TILES=[
  {k:'owed',   icon:'stat-money',    label:'home.owedToYou'},
  {k:'unread', icon:'stat-messages', label:'home.unreadMsgs'},
  {k:'jobs',   icon:'stat-jobs',     label:'home.jobsNearYou'},
  {k:'bill',   icon:'stat-bill',     label:'home.billDue'},
  {k:'events', icon:'stat-events',   label:'home.todaysEvents'},
  {k:'docs',   icon:'stat-docs',     label:'home.docsAttention'},
  {k:'spend',  emoji:'💸',           label:'home.spendTitle'}
];
function tileVal(kw,d){
  switch(kw){
    case 'owed':   return {v:ui.fmt$(d.owed.owedToMe)};
    case 'unread': return {v:String(d.unread)};
    case 'jobs':   return {v:String(d.openJobs.length)};
    case 'bill':   return {v:d.owed.billDue?ui.fmt$(d.owed.billDue.amount):'—',
                           s:d.owed.billDue?String(d.owed.billDue.item||''):''};
    case 'events': return {v:String(d.events.length)};
    case 'docs':   return {v:String(d.docs.length)};
    case 'spend':  return {v:ui.fmt$(Math.round(d.spentToday*100)/100),
                           s:t('home.spendMonth')+': '+ui.fmt$(Math.round(d.spentMonth*100)/100)};
  }
  return {v:'—'};
}

/* ---- markup ---- */
function tileHTML(def,d){
  const vv=tileVal(def.k,d);
  const ico=def.icon
    ? (HUB.icons?HUB.icons.icon(def.icon):'')
    : '<span class="gltile-emoji">'+esc(def.emoji)+'</span>';
  return '<button class="gltile" data-gl="'+def.k+'" aria-label="'+esc(t(def.label))+': '+esc(vv.v)+'">'+
    '<span class="gltile-ico">'+ico+'</span>'+
    '<span class="gltile-v" data-glv="'+def.k+'">'+esc(vv.v)+'</span>'+
    '<span class="gltile-l">'+esc(t(def.label))+'</span>'+
    '<span class="gltile-s" data-gls="'+def.k+'">'+esc(vv.s||'')+'</span>'+
  '</button>';
}
function sectionHTML(){
  const d=snapshot();
  return '<div class="hsec"><div class="hsec-hd"><h2>'+esc(t('home.glance'))+'</h2></div>'+
    '<div class="glwrap" id="glanceWrap">'+
      '<div class="glflow" id="glanceFlow" role="region" aria-label="'+esc(t('home.glance'))+'">'+
        TILES.map(function(def){ return tileHTML(def,d); }).join('')+
      '</div>'+
      '<div class="gldots" id="glanceDots" aria-hidden="true">'+
        TILES.map(function(def,i){ return '<span class="'+(i===0?'on':'')+'"></span>'; }).join('')+
      '</div>'+
    '</div>'+
    (d.allSample?'<p class="hnote">'+esc(t('home.sampleHint'))+'</p>':'')+'</div>';
}

/* ---- live repaint: update values in place (scroll position preserved) ---- */
function paint(){
  const f=document.getElementById('glanceFlow');
  if(!f) return;
  const d=snapshot();
  TILES.forEach(function(def){
    const vv=tileVal(def.k,d);
    const vEl=f.querySelector('[data-glv="'+def.k+'"]');
    const sEl=f.querySelector('[data-gls="'+def.k+'"]');
    if(vEl) vEl.textContent=vv.v;
    if(sEl) sEl.textContent=vv.s||'';
  });
}

/* ---- auto-rotation: advance ~every 4s; pauses the moment the user's finger
   touches the strip and resumes after 10s idle — never fights the swipe.
   Programmatic rotation steps set progScroll so they don't count as user
   activity (otherwise the scroll listener would cancel the very step it
   started). Dots track the strip position either way. */
let rotTimer=null, rotOn=true, resumeT=null, progScroll=false;
const reducedMotion=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
function stopRot(){ rotOn=false; if(rotTimer){ clearInterval(rotTimer); rotTimer=null; } }
function userHold(){
  stopRot();
  if(resumeT) clearTimeout(resumeT);
  resumeT=setTimeout(function(){ resumeT=null; if(!document.hidden) startRot(); },10000);
}
function setDots(i){
  const dots=document.getElementById('glanceDots');
  if(!dots) return;
  const sp=dots.children;
  for(let j=0;j<sp.length;j++) sp[j].classList.toggle('on', j===i);
}
function curIndex(f){
  const tiles=f.children;
  if(!tiles.length) return 0;
  const w=tiles[0].offsetWidth+12; /* tile + gap */
  return Math.min(tiles.length-1, Math.max(0, Math.round(f.scrollLeft/w)));
}
function startRot(){
  stopRot(); rotOn=true;
  if(reducedMotion) return;
  rotTimer=setInterval(function(){
    if(!rotOn) return;
    if(document.hidden) return;
    const f=document.getElementById('glanceFlow');
    if(!f||!document.body.contains(f)){ stopRot(); return; }
    const n=f.children.length;
    if(!n) return;
    const next=(curIndex(f)+1)%n;
    const w=f.children[0].offsetWidth+12;
    progScroll=true;
    try{ f.scrollTo({left:next*w,behavior:'smooth'}); }catch(e){ f.scrollLeft=next*w; }
    setDots(next);
    setTimeout(function(){ progScroll=false; },900);
  },4000);
}

/* ---- tap a tile -> its detail ---- */
function openDetail(kw){
  switch(kw){
    case 'unread': if(HUB.chat) HUB.chat.openList(); return;
    case 'jobs': HUB.showTab('work'); return;
    case 'owed': owedSheet(); return;
    case 'bill': billSheet(); return;
    case 'events': eventsSheet(); return;
    case 'docs': docsSheet(); return;
    case 'spend': spendSheet(); return;
  }
}
function hintHTML(){ return snapshot().allSample?'<p class="hint" style="margin-top:10px">'+esc(t('home.sampleHint'))+'</p>':''; }

function owedSheet(){
  const me=store.myName(); let rows='', total=0;
  for(const h of (store.state.households||[])){
    const n=(h.members||[]).length||1;
    for(const b of (h.bills||[])){
      if(b.paidBy!==me) continue;
      const amt=Number(b.amount)||0, back=amt-amt/n;
      if(back<=0) continue;
      total+=back;
      rows+='<div class="row between" style="padding:8px 2px;border-top:1px solid var(--line)">'+
        '<span><b>'+esc(String(b.item||''))+'</b><br><span class="sub">'+esc(h.name||'')+
        ' · '+esc(t('glance.paidBy'))+': '+esc(String(b.paidBy||''))+'</span></span>'+
        '<span><b>'+ui.fmt$(Math.round(back*100)/100)+'</b></span></div>';
    }
  }
  ui.openSheet('<h2>'+esc(t('home.owedToYou'))+'</h2>'+
    '<div class="row between" style="margin:8px 0"><span class="sub">'+esc(t('glance.total'))+'</span>'+
    '<span class="money" style="font-size:22px">'+ui.fmt$(Math.round(total*100)/100)+'</span></div>'+
    (rows||'<p class="sub">'+esc(t('glance.empty'))+'</p>')+hintHTML());
}
function billSheet(){
  const d=snapshot(), b=d.owed.billDue;
  let body;
  if(b){
    let hhName='';
    for(const h of (store.state.households||[])) if((h.bills||[]).indexOf(b)>=0) hhName=h.name||'';
    body='<div class="card" style="margin:10px 0;padding:14px">'+
      '<h3 style="margin:0 0 4px">🧾 '+esc(String(b.item||''))+'</h3>'+
      '<div class="money" style="font-size:26px;margin:6px 0">'+ui.fmt$(Number(b.amount)||0)+'</div>'+
      '<div class="sub">'+esc(t('glance.household'))+': '+esc(hhName||'—')+'</div>'+
      '<div class="sub">'+esc(t('glance.paidBy'))+': '+esc(String(b.paidBy||'—'))+'</div>'+
      '<div class="sub">'+esc(t('glance.due'))+': '+esc(String(b.due||'—'))+'</div></div>'+
      '<button class="btn btn-dark btn-block" id="glBillGo">'+esc(t('home.spendSub'))+' →</button>';
  } else {
    body='<p class="sub" style="padding:12px 0">'+esc(t('glance.empty'))+'</p>';
  }
  ui.openSheet('<h2>'+esc(t('home.billDue'))+'</h2>'+body+hintHTML());
  const go=document.getElementById('glBillGo');
  if(go) go.onclick=function(){ ui.closeSheet(); HUB.showTab('groups'); };
}
function eventsSheet(){
  const evs=store.state.events||[];
  const rows=evs.map(function(e){
    return '<button class="item tight" data-gev="'+esc(e.id)+'"><div class="grow"><h3>'+esc(e.title||'')+'</h3>'+
      '<div class="meta">🕐 '+esc(e.time||'—')+' · 📍 '+esc(e.where||'—')+'</div></div>'+
      '<span style="color:var(--faint)">›</span></button>';
  }).join('');
  ui.openSheet('<h2>'+esc(t('home.todaysEvents'))+'</h2><div style="margin-top:8px">'+
    (rows||'<p class="sub">'+esc(t('glance.empty'))+'</p>')+'</div>'+hintHTML());
  document.querySelectorAll('[data-gev]').forEach(function(btn){
    btn.onclick=function(){
      ui.closeSheet();
      if(HUB.views.daily&&HUB.views.daily.openEventSheet) HUB.views.daily.openEventSheet(btn.dataset.gev);
    };
  });
}
function docsSheet(){
  const docs=docsNeedingAttention();
  const rows=docs.map(function(m){
    let exp='';
    try{ exp=new Date(m.expiry).toLocaleDateString(); }catch(e){}
    return '<div class="item tight"><div class="grow"><h3>'+esc(m.title||m.note||'')+'</h3>'+
      '<div class="meta">'+esc(t('glance.expires'))+': '+esc(exp)+'</div></div></div>';
  }).join('');
  ui.openSheet('<h2>'+esc(t('home.docsAttention'))+'</h2><div style="margin-top:8px">'+
    (rows||'<p class="sub">'+esc(t('glance.empty'))+'</p>')+'</div>'+hintHTML());
}
function spendSheet(){
  const nowD=new Date();
  const dayStart=new Date(nowD.getFullYear(),nowD.getMonth(),nowD.getDate()).getTime();
  const monthStart=new Date(nowD.getFullYear(),nowD.getMonth(),1).getTime();
  let rows='', tT=0, tM=0;
  for(const hh of (store.state.households||[])){
    let dD=0, mM=0;
    for(const b of (hh.bills||[])){
      const amt=Number(b.amount)||0, at=Number(b.at)||0;
      if(amt<=0||!at) continue;
      if(at>=dayStart) dD+=amt;
      if(at>=monthStart) mM+=amt;
    }
    if(!dD&&!mM) continue;
    tT+=dD; tM+=mM;
    rows+='<div class="row between" style="padding:8px 2px;border-top:1px solid var(--line)">'+
      '<span><b>'+esc(hh.name||'')+'</b></span>'+
      '<span class="sub">'+esc(t('home.spendToday'))+': <b>'+ui.fmt$(Math.round(dD*100)/100)+'</b> · '+
      esc(t('home.spendMonth'))+': <b>'+ui.fmt$(Math.round(mM*100)/100)+'</b></span></div>';
  }
  ui.openSheet('<h2>💸 '+esc(t('home.spendTitle'))+' <span class="meta">· '+esc(t('home.spendSub'))+'</span></h2>'+
    '<div class="grid2" style="margin:10px 0"><div><div class="sub">'+esc(t('home.spendToday'))+'</div>'+
    '<div class="money" style="font-size:22px">'+ui.fmt$(Math.round(tT*100)/100)+'</div></div>'+
    '<div><div class="sub">'+esc(t('home.spendMonth'))+'</div>'+
    '<div class="money" style="font-size:22px">'+ui.fmt$(Math.round(tM*100)/100)+'</div></div></div>'+
    (rows||'<p class="sub">'+esc(t('glance.empty'))+'</p>'));
}

/* ---- bindings: delegation survives repaint; any touch pauses rotation (idle resumes it) ---- */
function bind(){
  const wrap=document.getElementById('glanceWrap');
  if(!wrap||wrap.dataset.gbound) return;
  wrap.dataset.gbound='1';
  const f=wrap.querySelector('#glanceFlow');
  const pause=function(){ userHold(); };
  f.addEventListener('pointerdown',pause,{passive:true});
  f.addEventListener('wheel',pause,{passive:true});
  f.addEventListener('touchstart',pause,{passive:true});
  f.addEventListener('scroll',function(){ setDots(curIndex(f)); if(!progScroll) userHold(); },{passive:true});
  let sx=0, sy=0;
  wrap.addEventListener('pointerdown',function(e){ sx=e.clientX; sy=e.clientY; },{passive:true});
  wrap.addEventListener('click',function(e){
    const tile=e.target.closest?e.target.closest('[data-gl]'):null;
    if(!tile) return;
    if(Math.hypot((e.clientX||0)-sx,(e.clientY||0)-sy)>10) return; /* it was a swipe */
    userHold(); /* a tap also pauses rotation (resumes after idle) */
    openDetail(tile.dataset.gl);
  });
  wrap.addEventListener('keydown',function(e){
    const tile=e.target.closest?e.target.closest('[data-gl]'):null;
    if(tile&&(e.key==='Enter'||e.key===' ')){ e.preventDefault(); userHold(); openDetail(tile.dataset.gl); }
  });
  startRot();
}

/* ---- live updates: debounced repaint after any store mutation ---- */
let saveT=null;
(function(){
  if(store.__glanceWrapped) return;
  store.__glanceWrapped=true;
  const orig=store.save;
  store.save=function(){
    orig();
    if(saveT) return;
    saveT=setTimeout(function(){ saveT=null; try{ paint(); }catch(e){} },350);
  };
})();

HUB.glance={sectionHTML:sectionHTML,paint:paint,bind:bind,openDetail:openDetail,
  /* QA hook: pause auto-rotation like a real touch would (resumes after idle) */
  _hold:userHold};
})();
