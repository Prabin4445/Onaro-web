/* HUB HOME tab — glossy 3D redesign (2026-10-05, PraBin's mockup language).
   Top to bottom: hero banner (greeting + date + astro art + motivation quote),
   4 module cards (Daily / Memory / Market / Work), People nearby (existing
   People store surface), Ask Onaro banner, Groups near you (existing cgroups
   surface), Quick Access, then ALL existing Home features below, untouched in
   behavior (capsule, glance, classes, professors, GPA, degree, appts, weather,
   ads, astro, events). Visual overhaul only — nothing removed, nothing broken. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
HUB.views=HUB.views||{};

/* ---- "What's happening" events as a 3D water-flow carousel ----
   Same treatment as the groups carousel: .flow/.gcard classes get the
   cover-flow tilt + auto-drift from HUB.cgroups.bindCarousels (already
   called for the home view). Cards keep icon/title/time/location +
   Sample badge; tap opens the event detail sheet (daily module). */
/* Shared 3D water-flow events carousel (used by Home and Daily).
   flowId defaults to homeEvFlow; opts.chev adds the row-style chevron. */
function eventsCarouselHTML(evs,flowId,opts){
  const fid=flowId||'homeEvFlow', chev=opts&&opts.chev;
  const cards=evs.map(function(e){
    return '<article class="gcard" data-ev="'+ui.esc(e.id)+'" tabindex="0" role="button" aria-label="'+ui.esc(e.title)+'">'
      +'<div class="gcard-media"><span class="gcard-emoji">'+ui.esc(e.emoji||'🎉')+'</span>'+(chev?'<span class="gcard-chev" aria-hidden="true">›</span>':'')+'</div>'
      +'<div class="gcard-body"><h3>'+ui.esc(e.title)+'</h3>'
      +'<p>🕐 '+ui.esc(e.time||'—')+'</p>'
      +'<p>📍 '+ui.esc(e.where||'—')+'</p>'
      +ui.sampleBadge(e.sample)
      +'</div></article>';
  }).join('');
  return '<div class="flowwrap"><div class="flow" id="'+fid+'">'+cards+'</div></div>';
}
function bindEventCards(scope,rootSel){
  scope.querySelectorAll((rootSel||'#homeEvents')+' [data-ev]').forEach(function(card){
    if(card.dataset.ebound) return; card.dataset.ebound='1';
    let px=0, py=0;
    card.addEventListener('pointerdown',function(e){ px=e.clientX; py=e.clientY; },{passive:true});
    const go=function(e){
      if(e&&Math.hypot((e.clientX||0)-px,(e.clientY||0)-py)>10) return; /* it was a drag */
      if(HUB.views.daily&&HUB.views.daily.openEventSheet) HUB.views.daily.openEventSheet(card.dataset.ev);
    };
    card.addEventListener('click',go);
    card.addEventListener('keydown',function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); }
    });
  });
}

/* ---- Time Capsule detail sheet (the (i) button) ----
   Explains what the capsule is and how it works; a CTA goes to the tab. */
function capsuleInfoSheet(){
  ui.openSheet(
    '<h2>⏳ '+ui.esc(t('daily.capsule'))+'</h2>'+
    '<p class="sub" style="margin:8px 0">'+ui.esc(t('home.capInfoLede'))+'</p>'+
    '<p class="capmanifestline">'+ui.esc(t('capsule.manifestInfo'))+'</p>'+
    '<ol class="capsteps"><li>'+ui.esc(t('home.capInfo1'))+'</li><li>'+ui.esc(t('home.capInfo2'))+'</li>'+
    '<li>'+ui.esc(t('home.capInfo3'))+'</li><li>'+ui.esc(t('home.capInfo4'))+'</li></ol>'+
    '<p class="hint">'+ui.esc(t('home.capInfoNote'))+'</p>'+
    '<button class="btn btn-dark" id="capInfoOpen" style="width:100%;margin-top:10px">⏳ '+ui.esc(t('home.capInfoOpen'))+'</button>'
  );
  const go=document.getElementById('capInfoOpen');
  if(go) go.onclick=()=>{ ui.closeSheet(); HUB.showTab('daily'); };
}

/* ---- Time Capsule row (one managed row card under the hero) ----
   Soonest locked capsule ticks live ("3d 03:02:02") via the shared 1s
   ticker in classes.js; tap -> Daily tab. Empty state is a one-tap row
   that opens the Daily tab with the capsule setup sheet open. The (i)
   button opens the detail sheet. */
function capsuleRowHTML(){
  const nowD=new Date();
  const today=nowD.getFullYear()+'-'+String(nowD.getMonth()+1).padStart(2,'0')+'-'+String(nowD.getDate()).padStart(2,'0');
  const locked=(store.state.capsules||[]).filter(c=>c&&c.unlock&&String(c.unlock)>today)
    .sort((a,b)=>String(a.unlock).localeCompare(String(b.unlock)));
  const infoBtn='<button class="capinfo" id="homeCapInfo" aria-label="'+ui.esc(t('home.capInfoAria'))+'">i</button>';
  if(locked.length){
    const c=locked[0];
    const ts=new Date(c.unlock+'T00:00:00').getTime();
    const p=(HUB.classes&&HUB.classes.fmtDHMS)?HUB.classes.fmtDHMS(Math.max(0,ts-Date.now())):{d:'0',h:'00',m:'00',s:'00'};
    const more=locked.length>1?' · +'+(locked.length-1):'';
    return '<div class="hrow" id="homeCapCard" role="button" tabindex="0" aria-label="'+ui.esc(t('daily.capsule'))+'">'+
      '<span class="hrow-ico">⏳</span>'+
      '<span class="grow"><span class="hrow-t">'+ui.esc(t('daily.capsule'))+'</span>'+
      '<span class="hrow-s"><b data-capcd-ts="'+ts+'">'+p.d+'d '+p.h+':'+p.m+':'+p.s+'</b>'+ui.esc(more)+' · '+ui.esc(t('capsule.manifest'))+'</span></span>'+
      infoBtn+'<span class="chev">›</span></div>';
  }
  return '<div class="hrow" id="homeCapNew" role="button" tabindex="0">'+
    '<span class="hrow-ico">⏳</span>'+
    '<span class="grow"><span class="hrow-t">'+ui.esc(t('home.capCreate'))+'</span>'+
    '<span class="hrow-s">'+ui.esc(t('capsule.manifest'))+'</span></span>'+
    '<span class="chev">›</span></div>';
}

/* ============ new glossy sections (2026-10-05) ============ */

/* Hero banner: time-aware greeting + date line, astro art right, and the
   EXISTING 120-quote daily rotation inside a "TODAY'S MOTIVATION" card.
   Quote markup is untouched (same ids) so quote.bindQuoteCard keeps working. */
function heroHTML(dateStr,me){
  return '<section class="hm-hero">'
    +'<div class="hm-hero-top"><div class="hm-hero-txt">'
    +'<div class="hm-greet">'+ui.esc(ui.greeting())+', <span class="hm-hl">'+ui.esc(me)+'</span></div>'
    +'<div class="hm-date">'+ui.esc(dateStr)+' · '+ui.esc(t('home.worldToday'))+'</div>'
    +'</div><div class="hm-hero-art">'+HUB.icons.icon('hm-hero-astro','hm-art')+'</div></div>'
    +((HUB.quote&&HUB.quote.cardHTML)?'<div class="hm-quote">'+HUB.quote.cardHTML()+'</div>':'')
    +'</section>';
}

/* 4 module cards: rose Daily / green Memory / orange Market / blue Work.
   Memory opens the EXISTING global search overlay (not a new tab). */
const HM_MODS=[
  {k:'daily', icon:'hm-mod-daily', tk:'hm.daily', sk:'hm.dailySub',
   go:function(){ HUB.showTab('daily'); }},
  {k:'memory',icon:'hm-mod-memory',tk:'hm.memory',sk:'hm.memorySub',
   go:function(){ if(HUB.search) HUB.search.open(); }},
  {k:'market',icon:'hm-mod-market',tk:'hm.market',sk:'hm.marketSub',
   go:function(){ HUB.showTab('market'); }},
  {k:'work',  icon:'hm-mod-work',  tk:'hm.work',  sk:'hm.workSub',
   go:function(){ HUB.showTab('work'); }}
];
function modulesHTML(){
  return '<div class="hm-mods" role="list">'+HM_MODS.map(function(m){
    return '<button class="hm-mod hm-mod-'+m.k+'" data-hmod="'+m.k+'" role="listitem" aria-label="'+ui.esc(t(m.tk))+'">'
      +'<span class="hm-mod-ico">'+HUB.icons.icon(m.icon)+'</span>'
      +'<span class="hm-mod-t">'+ui.esc(t(m.tk))+'</span>'
      +'<span class="hm-mod-s">'+ui.esc(t(m.sk))+'</span>'
      +'<span class="hm-mod-go" aria-hidden="true">→</span></button>';
  }).join('')+'</div>';
}

/* People nearby: the EXISTING People store surface (Groups → People contacts).
   Honest empty state when there is nobody — no invented people, ever. */
function peopleEmptyHTML(){
  return '<div class="hsec"><div class="hsec-hd hm-hd"><h2><span class="hm-glyph" aria-hidden="true">👥</span>'
    +ui.esc(t('home.pplNear'))+'</h2>'
    +'<button class="hsec-act" data-hmppl="1">'+ui.esc(t('common.seeAll'))+'</button></div>'
    +'<div class="hm-empty"><span class="hm-empty-ico" aria-hidden="true">👥</span>'
    +'<p><b>'+ui.esc(t('hm.pplEmpty'))+'</b><br><span class="sub">'+ui.esc(t('hm.pplEmptySub'))+'</span></p></div></div>';
}
function openPeople(){
  try{ if(HUB.views.groups&&HUB.views.groups.setSub) HUB.views.groups.setSub('people'); }catch(e){}
  HUB.showTab('groups');
}

/* Ask Onaro banner: gradient border, bulb glyph, robot art right -> Ask sheet. */
function askBannerHTML(){
  return '<div class="hsec"><div class="hm-ask" id="hmAsk" role="button" tabindex="0" aria-label="'+ui.esc(t('ask.title'))+'">'
    +'<div class="hm-ask-in"><div class="hm-ask-main">'
    +'<span class="hm-ask-bulb" aria-hidden="true">💡</span>'
    +'<span class="hm-ask-txt"><span class="hm-ask-t">'+ui.esc(t('ask.title'))+'</span>'
    +'<span class="hm-ask-s">'+ui.esc(t('hm.askSub'))+'</span></span>'
    +'<span class="hm-ask-go" aria-hidden="true">→</span></div>'
    +'<span class="hm-ask-art">'+HUB.icons.icon('hm-ask-robot','hm-robot')+'</span>'
    +'</div></div></div>';
}

/* Quick Access: Style Closet (style overlay), central big volt + (create
   composer), Groups (groups tab). Beauty Hub / Room & Decor / Travel /
   Safety have NO feature code in the codebase — their icons are excluded
   rather than invented (verified 2026-10-05). */
function quickAccessHTML(){
  return '<div class="hsec"><div class="hsec-hd hm-hd"><h2><span class="hm-glyph" aria-hidden="true">⚡</span>'
    +ui.esc(t('hm.quick'))+'</h2></div>'
    +'<div class="hm-qa">'
    +'<button class="hm-qa-item" id="hmQaCloset"><span class="hm-qa-c">'+HUB.icons.icon('qa-closet')+'</span>'
    +'<span class="hm-qa-l">'+ui.esc(t('style.title'))+'</span></button>'
    +'<button class="hm-qa-item" id="hmQaScan"><span class="hm-qa-c">'+HUB.icons.icon('scan-doc')+'</span>'
    +'<span class="hm-qa-l">'+ui.esc(t('scan.title'))+'</span></button>'
    +'<button class="hm-qa-plus" id="hmQaCreate" aria-label="'+ui.esc(t('create.aria'))+'"><span aria-hidden="true">+</span></button>'
    +'<button class="hm-qa-item" id="hmQaGroups"><span class="hm-qa-c">'+HUB.icons.icon('qa-groups')+'</span>'
    +'<span class="hm-qa-l">'+ui.esc(t('groups.title'))+'</span></button>'
    +'</div></div>';
}

HUB.views.home={
  render(el){
    const st=store.state, me=store.myName();
    const events=st.events;
    const langTag={en:'en-US',es:'es',ne:'ne-NP',hi:'hi-IN'}[HUB.i18n.getLang()]||'en-US';
    let dateStr='';
    try{ dateStr=new Date().toLocaleDateString(langTag,{weekday:'long',month:'short',day:'numeric'}); }catch(e){ dateStr=new Date().toDateString(); }

    /* people surface from the existing People store; honest empty state */
    const pplHTML=(HUB.people&&HUB.people.homeRowHTML)?HUB.people.homeRowHTML():'';

    el.innerHTML =
      // 1. hero: greeting + date + astro art + motivation quote card
      heroHTML(dateStr,me)+

      // 2. module cards: Daily / Memory / Market / Work
      modulesHTML()+

      // 3. people nearby (existing store surface, or honest empty state)
      (pplHTML||peopleEmptyHTML())+

      // 4. Ask Onaro banner
      askBannerHTML()+

      // 5. quick access
      quickAccessHTML()+

      // ---- 7. existing Home features below, behavior untouched ----
      // time capsule row
      '<div class="hsec">'+capsuleRowHTML()+'</div>'+
      // today at a glance — auto-rotating water-glass stat carousel
      ((HUB.glance&&HUB.glance.sectionHTML)?HUB.glance.sectionHTML():'')+
      // next-class card
      HUB.classes.cardHTML()+
      // Professors entry — the original blackboard-scene banner
      ((HUB.professors&&HUB.professors.entryHTML)?HUB.professors.entryHTML():'')+
      // GPA calculator
      ((HUB.gpa&&HUB.gpa.cardHTML)?HUB.gpa.cardHTML():'')+
      // Degree plans entry (tracker opens as a full overlay — no bottom tab)
      ((HUB.degree&&HUB.degree.entryHTML)?HUB.degree.entryHTML():'')+
      ((HUB.appts&&HUB.appts.cardHTML)?HUB.appts.cardHTML():'')+
      // weather card (Today + Tomorrow; tap -> glass detail)
      ((HUB.wxhome&&HUB.wxhome.stripHTML)?'<div class="hsec">'+HUB.wxhome.stripHTML()+'</div>':'')+
      // sponsored side-by-side carousel (demo inventory, labeled)
      ((HUB.ads&&HUB.ads.carouselHTML)?'<div class="hsec" id="adCarouselHost">'+HUB.ads.carouselHTML()+'</div>':'')+
      // horoscope + calendar (tap: full horoscope / calendar sheet)
      ((HUB.astro&&HUB.astro.homeCardHTML)?'<div class="hsec">'+HUB.astro.homeCardHTML()+'</div>':'')+
      // groups near you — directly below horoscope, 3D water-flow carousel ≤50 mi
      '<div class="hsec" id="homeCg">'+((HUB.cgroups&&HUB.cgroups.homeSectionHTML)?HUB.cgroups.homeSectionHTML():'')+'</div>'+
      // events preview — 3D water-flow carousel
      '<div class="hsec"><div class="hsec-hd"><h2><span class="hm-glyph" aria-hidden="true">🎉</span>'+t('home.happening')+'</h2><button class="hsec-act" data-goto="daily">'+t('common.seeAll')+'</button></div>'+
      '<div id="homeEvents">'+
        (events.length? eventsCarouselHTML(events.slice(0,8))
         : '<div class="empty"><span class="empty-ico">'+HUB.icons.icon('stat-events')+'</span><h3>'+t('home.noEvents')+'</h3><p class="sub">'+t('home.noEventsSub')+'</p><button class="btn btn-ghost btn-sm" id="homeEventsEmpty">'+t('daily.title')+' →</button></div>')+
      '</div></div>';

    // ---- bindings (after innerHTML) ----
    /* Workstream H: start the class countdown ticker + reminder scheduler. */
    try{ HUB.classes.startTicker(); }catch(e){}
    /* module cards */
    el.querySelectorAll('[data-hmod]').forEach(function(b){
      const m=HM_MODS.find(function(x){ return x.k===b.dataset.hmod; });
      if(!m) return;
      b.addEventListener('click',m.go);
    });
    /* people "See all →": existing store surface header gets one injected;
       the honest empty state carries its own (data-hmppl). */
    const pplHd=el.querySelector('#homePplSec .hsec-hd');
    if(pplHd&&!pplHd.querySelector('[data-hmppl]')){
      const b=document.createElement('button');
      b.className='hsec-act'; b.setAttribute('data-hmppl','1'); b.textContent=t('common.seeAll');
      b.addEventListener('click',openPeople);
      pplHd.appendChild(b);
    }
    el.querySelectorAll('[data-hmppl]').forEach(function(b){
      if(b.dataset.hmpplBound) return; b.dataset.hmpplBound='1';
      b.addEventListener('click',openPeople);
    });
    try{ if(HUB.people&&HUB.people.bindHomeRow) HUB.people.bindHomeRow(el); }catch(e){}
    /* Ask Onaro banner -> the full Ask sheet (same as the global pill) */
    const hmAsk=document.getElementById('hmAsk');
    if(hmAsk){
      const openAsk=()=>{ if(HUB.askHUB) HUB.askHUB.open(''); };
      hmAsk.addEventListener('click',openAsk);
      hmAsk.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openAsk(); } });
    }
    /* quick access */
    const qc=document.getElementById('hmQaCloset');
    if(qc) qc.onclick=()=>{ if(HUB.style) HUB.style.open(); };
    const qs=document.getElementById('hmQaScan');
    if(qs) qs.onclick=()=>{ if(HUB.scan) HUB.scan.studio(); };
    const qg=document.getElementById('hmQaGroups');
    if(qg) qg.onclick=()=>HUB.showTab('groups');
    const qp=document.getElementById('hmQaCreate');
    if(qp) qp.onclick=()=>{ if(HUB.create) HUB.create.open(); };
    /* time capsule row: tap -> Daily; setup row opens Daily + capsule sheet */
    const hcc=document.getElementById('homeCapCard');
    if(hcc){
      hcc.addEventListener('click',()=>HUB.showTab('daily'));
      hcc.addEventListener('keydown',e=>{ if(e.target.closest('#homeCapInfo')) return; if(e.key==='Enter'||e.key===' '){ e.preventDefault(); HUB.showTab('daily'); } });
    }
    const hcn=document.getElementById('homeCapNew');
    if(hcn){
      const openCap=()=>{
        HUB.showTab('daily');
        setTimeout(()=>{ try{ if(HUB.views.daily&&HUB.views.daily.openCapsuleSheet) HUB.views.daily.openCapsuleSheet(); }catch(err){} },400);
      };
      hcn.addEventListener('click',openCap);
      hcn.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openCap(); } });
    }
    /* (i) -> detail sheet about the capsule */
    const hci=document.getElementById('homeCapInfo');
    if(hci) hci.addEventListener('click',e=>{ e.stopPropagation(); capsuleInfoSheet(); });
    /* astro: horoscope snippet fetch + card/calendar taps */
    try{ if(HUB.astro&&HUB.astro.bindHomeCard) HUB.astro.bindHomeCard(); }catch(e){}
    /* home weather strip: paint from cache, refresh live, tap -> detail */
    try{ if(HUB.wxhome){ HUB.wxhome.bind(el); HUB.wxhome.refresh(); } }catch(e){}
    /* daily motivation quote */
    try{ if(HUB.quote&&HUB.quote.bindQuoteCard) HUB.quote.bindQuoteCard(); }catch(e){}
    /* sponsored carousel taps -> demo honesty sheet */
    try{ if(HUB.ads&&HUB.ads.bind) HUB.ads.bind(el); }catch(e){}
    const hee=document.getElementById('homeEventsEmpty');
    if(hee) hee.onclick=()=>HUB.showTab('daily');

    HUB.ai.bindGotos(el); // generic [data-goto] navigation

    // "today at a glance" carousel: tap-vs-swipe, auto-rotation, live repaint
    try{ if(HUB.glance) HUB.glance.bind(); }catch(e){}

    // Professors entry card -> full directory overlay
    try{ if(HUB.professors&&HUB.professors.bindEntry) HUB.professors.bindEntry(el); }catch(e){}

    // Degree plans entry card -> full tracker overlay
    try{ if(HUB.degree&&HUB.degree.bindEntry) HUB.degree.bindEntry(el); }catch(e){}

    /* groups near you: 3D carousel tilt/drift + "see all" -> Groups tab */
    try{
      if(HUB.cgroups){
        HUB.cgroups.bindCarousels(el);
        const cgAll=document.getElementById('homeCgAll');
        if(cgAll) cgAll.onclick=()=>HUB.showTab('groups');
      }
    }catch(e){}
    /* events water-flow carousel: bindCarousels above already gave #homeEvFlow
       its tilt/drift; cards tap through to the event detail sheet */
    try{ bindEventCards(el); }catch(e){}

  }
};
/* shared with the Daily tab: same 3D water-flow events carousel */
HUB.evCarousel={html:eventsCarouselHTML,bind:bindEventCards};
})();
