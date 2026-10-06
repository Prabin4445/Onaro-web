/* HUB DAILY tab: everyday essentials — a Time Capsule (encrypted letters to
   your future self), Gym Fuel, and the happening-events list (no map).
   Weather moved to the Home car-dashboard strip (js/wxhome.js) backed by the
   shared HUB.wx layer (js/wx.js); capsules stay in this browser.
   2026-10-05 redesign: glossy-3D chrome (hero + gradient-border section
   frames, css/daily.css). Chrome-only — every feature's cardHTML/bind
   behavior is untouched; the frames wrap the module cards as-is. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const ui=()=>HUB.ui, st=()=>HUB.store.state;
let hostEl=null;
/* ---------- glossy chrome (2026-10-05) ----------
   frame(): wraps a module's cardHTML in the gradient-border glossy card
   with a floating 3D clay icon badge. No header — the module's own card
   keeps its title/subtitle, so nothing is duplicated and no module code
   is touched.
   sectionCard(): for Daily-owned sections (capsule, happening) — glossy
   frame + header row (3D icon, title, optional sub, action slot). */
function frame(accent,iconName,inner){
  return '<section class="dly-card" style="--dly-ac:'+accent+'"><div class="dly-card-in">'+
    '<span class="dly-badge" aria-hidden="true">'+HUB.icons.icon(iconName)+'</span>'+
    '<div class="dly-cbody">'+inner+'</div></div></section>';
}
function sectionCard(accent,headIcon,title,sub,action,body){
  return '<section class="dly-card" style="--dly-ac:'+accent+'"><div class="dly-card-in">'+
    '<div class="dly-chead"><span class="dly-chead-ico" aria-hidden="true">'+headIcon+'</span>'+
    '<div class="dly-chead-tx"><div class="dly-chead-t">'+title+'</div>'+
    (sub?'<div class="dly-chead-s">'+sub+'</div>':'')+'</div>'+
    (action?'<div class="dly-chead-act">'+action+'</div>':'')+'</div>'+
    '<div class="dly-cbody">'+body+'</div></div></section>';
}
function heroHTML(){
  const U=ui();
  const langTag={en:'en-US',es:'es',ne:'ne-NP',hi:'hi-IN'}[HUB.i18n.getLang()]||'en-US';
  let dateStr='';
  try{ dateStr=new Date().toLocaleDateString(langTag,{weekday:'long',month:'long',day:'numeric'}); }
  catch(e){ dateStr=new Date().toDateString(); }
  return '<div class="dly-hero"><div class="dly-hero-ico" aria-hidden="true">'+HUB.icons.icon('hm-mod-daily')+'</div>'+
    '<div class="dly-hero-tx"><div class="dly-hero-t">'+U.esc(t('daily.title'))+'</div>'+
    '<div class="dly-hero-s">'+U.esc(t('dly.heroSub',{date:dateStr}))+'</div></div></div>';
}
/* Weather moved to the shared HUB.wx layer (js/wx.js);
   the Home car-dashboard strip (js/wxhome.js) renders it now. */
/* ---------- time capsule ---------- */
function todayStr(){
  const d=new Date();
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function fmtD(iso){
  try{ return new Date(iso+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}); }
  catch(e){ return iso; }
}
function capOpen(c){ return String(c.unlock||'')<=todayStr(); }
function capDaysLeft(c){
  const ms=new Date(c.unlock+'T00:00:00')-new Date(todayStr()+'T00:00:00');
  return Math.round(ms/86400000);
}
async function capsulesHTML(){
  const U=ui(), arr=(st().capsules||[]).slice().sort((a,b)=>b.createdAt-a.createdAt);
  let h='<p class="sub" style="margin:0 0 10px">'+U.esc(t('daily.capSub'))+'</p>';
  h+='<button class="btn btn-dark btn-sm" id="dyCapNew" style="margin-bottom:10px">⏳ '+U.esc(t('daily.capNew'))+'</button>';
  if(!arr.length) h+='<p class="sub" style="padding:6px 2px">'+U.esc(t('daily.capEmpty'))+'</p>';
  for(const c of arr){
    const title=U.esc(c.title||t('daily.capUntitled'));
    if(capOpen(c)){
      const txt=await HUB.crypto.textOf(c);
      h+='<div class="card" style="margin-bottom:10px;border:1px dashed var(--line)"><div class="row between"><h3>💌 '+title+'</h3>'+
        '<button class="linklike" data-cdel="'+U.esc(c.id)+'" aria-label="'+U.esc(t('daily.del'))+'">✕</button></div>'+
        '<p style="margin:8px 0;white-space:pre-wrap">'+U.esc(txt)+'</p>'+
        '<div class="sub">✨ '+U.esc(t('daily.capOpened',{d:fmtD(c.unlock)}))+'</div></div>';
    }else{
      const n=capDaysLeft(c);
      const when=n<=0?fmtD(c.unlock):(n===1?t('daily.capIn1'):t('daily.capInN',{n:n}));
      h+='<div class="item tight"><span style="font-size:24px">🔒</span><div class="grow"><h3>'+title+'</h3>'+
        '<div class="meta">'+U.esc(t('daily.capUnlocks')+' '+when)+'</div></div>'+
        '<button class="linklike" data-cdel="'+U.esc(c.id)+'" aria-label="'+U.esc(t('daily.del'))+'">✕</button></div>';
    }
  }
  h+='<p class="hint">'+U.esc(t('daily.capNote'))+'</p>';
  return h;
}
function openCapsuleSheet(){
  const U=ui(), min=todayStr();
  const chips=[[30,'daily.cap1mo'],[182,'daily.cap6mo'],[365,'daily.cap1yr']];
  U.openSheet(
    '<h2>⏳ '+U.esc(t('daily.capNew'))+'</h2>'+
    '<p class="sub">'+U.esc(t('daily.capFormSub'))+'</p>'+
    '<div class="field"><label>'+U.esc(t('daily.capTitle'))+'</label><input class="input" id="cpTitle" maxlength="60" placeholder="'+U.esc(t('daily.capTitlePh'))+'"></div>'+
    '<div class="field"><label>'+U.esc(t('daily.capMsg'))+'</label><textarea class="input" id="cpMsg" rows="4" placeholder="'+U.esc(t('daily.capMsgPh'))+'"></textarea></div>'+
    '<div class="field"><label>'+U.esc(t('daily.capUnlock'))+'</label><input class="input" id="cpDate" type="date" min="'+min+'"></div>'+
    '<div class="row" style="gap:8px;margin:10px 0">'+chips.map(ch=>'<button class="chip" data-cpdays="'+ch[0]+'">'+U.esc(t(ch[1]))+'</button>').join('')+'</div>'+
    '<button class="btn btn-dark" id="cpSeal" style="width:100%">🔒 '+U.esc(t('daily.capSeal'))+'</button>'+
    '<p class="hint">'+U.esc(t('daily.capSealNote'))+'</p>'
  );
  document.querySelectorAll('[data-cpdays]').forEach(b=>{ b.onclick=()=>{
    const d=new Date(); d.setDate(d.getDate()+(+b.dataset.cpdays));
    document.getElementById('cpDate').value=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  };});
  document.getElementById('cpSeal').onclick=async()=>{
    const msg=document.getElementById('cpMsg').value.trim();
    const unlock=document.getElementById('cpDate').value;
    if(!msg){ U.toast(t('daily.capNeedMsg')); return; }
    if(!unlock||unlock<=min){ U.toast(t('daily.capNeedDate')); return; }
    const enc=await HUB.crypto.encryptText(msg);
    /* WebCrypto unavailable -> enc is null and the message is kept as
       top-level plaintext (the shape HUB.crypto.textOf reads); storing it
       under enc:{text} would render as an empty letter on unlock day. */
    HUB.store.add('capsules',{title:document.getElementById('cpTitle').value.trim(),text:enc?'':msg,enc:enc||null,unlock:unlock});
    U.closeSheet(); render(hostEl); U.toast('⏳ '+t('daily.capSealed'));
  };
}

/* ---------- happening (events, no map): 3D water-flow carousel ----------
   Same shared treatment as Home/Groups (HUB.evCarousel from js/home.js).
   Falls back to the old vertical list if the shared export is missing. */
function eventsListHTML(){
  const U=ui(), evs=st().events||[];
  return evs.map(e=>'<div class="item tight" data-ev="'+U.esc(e.id)+'" role="button" tabindex="0">'+
    '<div class="evthumb">'+HUB.icons.eventIcon(e.emoji)+'</div>'+
    '<div class="grow"><h3>'+U.esc(e.title)+'</h3><div class="meta">'+U.esc((e.time||'')+(e.where?' · '+e.where:''))+'</div></div>'+
    U.sampleBadge(e.sample)+'<span style="font-size:20px;color:var(--faint)">›</span></div>').join('');
}
function eventsHTML(){
  const U=ui(), evs=st().events||[];
  if(!evs.length) return '<p class="sub">'+U.esc(t('daily.noEvents'))+'</p>';
  if(HUB.evCarousel&&HUB.evCarousel.html)
    return '<div id="dyEvWrap">'+HUB.evCarousel.html(evs,'dyEvFlow',{chev:true})+'</div>';
  return '<div id="dyEvWrap">'+eventsListHTML()+'</div>';
}
/* Event detail: full info (title, when, where, category, description) plus
   optional links (tappable) and a photo strip (tap -> pinch-zoom lightbox).
   Events carry optional links:[{label,url}] and photos:[] — rendered only
   when present, so older events without them are unaffected. */
function evHost(url){
  try{ return new URL(url).hostname.replace(/^www\./,''); }catch(e){ return url; }
}
function openEventSheet(id){
  const U=ui(), e=HUB.store.find('events',id);
  if(!e) return;
  const links=(e.links||[]).filter(function(l){ return l&&l.url; });
  const photos=(e.photos||[]).filter(Boolean);
  U.openSheet(
    '<div style="font-size:46px;margin-bottom:6px">'+U.esc(e.emoji||'🎉')+'</div>'+
    '<h2>'+U.esc(e.title)+'</h2>'+
    '<div class="kv"><span>'+t('daily.evWhen')+'</span><b>'+U.esc(e.time||'—')+'</b></div>'+
    '<div class="kv"><span>'+t('daily.evWhere')+'</span><b>'+U.esc(e.where||'—')+'</b></div>'+
    (e.cat?'<div class="kv"><span>'+t('daily.evCat')+'</span><b>'+U.esc(e.cat)+'</b></div>':'')+
    (e.desc?'<p class="sub" style="margin:10px 0;white-space:pre-wrap">'+U.esc(e.desc)+'</p>':'')+
    (photos.length?'<h3 style="margin:12px 0 8px">'+U.esc(t('daily.evPhotos'))+'</h3>'+
      '<div class="evphotostrip">'+photos.map(function(p,i){
        return '<img src="'+U.esc(p)+'" alt="" loading="lazy" data-evph="'+i+'">';
      }).join('')+'</div>':'')+
    (links.length?'<h3 style="margin:12px 0 8px">'+U.esc(t('daily.evLinks'))+'</h3>'+
      links.map(function(l){
        return '<a class="item tight evlink" href="'+U.esc(l.url)+'" target="_blank" rel="noopener">'+
          '<span style="font-size:20px">🔗</span><div class="grow"><h3>'+U.esc(l.label||l.url)+'</h3>'+
          '<div class="meta">'+U.esc(evHost(l.url))+'</div></div><span style="color:var(--faint)">↗</span></a>';
      }).join(''):'')+
    '<div style="margin-top:12px">'+U.sampleBadge(e.sample)+'</div>'+
    (!e.sample?'<div class="row" style="gap:8px;margin-top:14px">'+
      '<button class="btn btn-ghost btn-sm" id="evEditBtn" style="flex:1">✏️ '+U.esc(t('daily.evEdit'))+'</button>'+
      '<button class="btn btn-ghost btn-sm" id="evDelBtn" style="flex:1;color:#F87171">🗑 '+U.esc(t('daily.evDel'))+'</button></div>':'')
  );
  /* photo strip -> fullscreen pinch-zoom lightbox (keeps the sheet behind) */
  document.querySelectorAll('#sheetBox [data-evph]').forEach(function(img){
    img.style.cursor='zoom-in';
    img.onclick=function(){ if(HUB.mkZoom&&HUB.mkZoom.open) HUB.mkZoom.open(photos[+img.dataset.evph],{keepSheet:true}); };
  });
  /* owner actions on user-created events (samples are read-only) */
  var eb=document.getElementById('evEditBtn');
  if(eb) eb.onclick=function(){ openEventFormSheet(e.id); };
  var db=document.getElementById('evDelBtn');
  if(db) db.onclick=function(){
    HUB.store.remove('events',e.id);
    U.closeSheet(); render(hostEl); U.toast('🗑 '+t('daily.evDeleted'));
  };
}

/* ---------- happening: add / edit event form ---------- */
function openEventFormSheet(id){
  const U=ui(), e=id?HUB.store.find('events',id):null;
  if(id&&!e) return;
  U.openSheet(
    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'+
    '<h2 style="margin:0;flex:1">'+U.esc(t(e?'daily.evEdit':'daily.evNew'))+'</h2>'+
    '<button class="btn ghost" data-close style="font-size:12px;padding:6px 10px">✕</button></div>'+
    '<div class="field"><label>'+U.esc(t('daily.evEmoji'))+'</label>'+
    '<input class="input" id="efEmoji" maxlength="4" style="width:80px" value="'+U.esc(e?(e.emoji||''):'')+'" placeholder="🎉"></div>'+
    '<div class="field"><label>'+U.esc(t('daily.evTitleL'))+'</label>'+
    '<input class="input" id="efTitle" maxlength="80" value="'+U.esc(e?(e.title||''):'')+'"></div>'+
    '<div class="field"><label>'+U.esc(t('daily.evWhenL'))+'</label>'+
    '<input class="input" id="efTime" maxlength="60" value="'+U.esc(e?(e.time||''):'')+'" placeholder="Sat · 6:00 PM"></div>'+
    '<div class="field"><label>'+U.esc(t('daily.evWhereL'))+'</label>'+
    '<input class="input" id="efWhere" maxlength="80" value="'+U.esc(e?(e.where||''):'')+'"></div>'+
    '<div class="field"><label>'+U.esc(t('daily.evCatL'))+'</label>'+
    '<input class="input" id="efCat" maxlength="40" value="'+U.esc(e?(e.cat||''):'')+'"></div>'+
    '<div class="field"><label>'+U.esc(t('daily.evDescL'))+'</label>'+
    '<textarea class="input" id="efDesc" rows="3" maxlength="500">'+U.esc(e?(e.desc||''):'')+'</textarea></div>'+
    '<button class="btn btn-dark" id="efSave" style="width:100%;margin-top:10px">'+U.esc(t('daily.evSave'))+'</button>'
  );
  document.getElementById('efSave').onclick=function(){
    const o={
      emoji:document.getElementById('efEmoji').value.trim()||'🎉',
      title:document.getElementById('efTitle').value.trim(),
      time:document.getElementById('efTime').value.trim(),
      where:document.getElementById('efWhere').value.trim(),
      cat:document.getElementById('efCat').value.trim(),
      desc:document.getElementById('efDesc').value.trim()
    };
    if(!o.title||!o.time){ U.toast(t('daily.evNeed')); return; }
    if(e){ Object.assign(e,o); HUB.store.save(); U.toast(t('daily.evUpdated')); }
    else{ HUB.store.add('events',o); U.toast('🎉 '+t('daily.evSaved')); }
    U.closeSheet(); render(hostEl);
  };
}

/* ---------- render ---------- */
async function render(el){
  hostEl=el;
  const U=ui();
  const capH=await capsulesHTML(), lockH=await HUB.crypto.lockHTML();
  el.innerHTML=
    heroHTML()+

    /* time capsule: Daily-owned section -> glossy header card (lock indicator
       keeps its header action slot; the capsule list/buttons are untouched) */
    sectionCard('#FBBF24','<span class="dly-emoji">⏳</span>',
      U.esc(t('daily.capsule')),'',lockH,
      '<div id="dyCaps">'+capH+'</div>')+

    /* calculator entry card (2026-09-30): animated icon near the top; tap opens
       the full-page calculator overlay. The calculator no longer embeds inline. */
    (HUB.calc&&HUB.calc.entryHTML?frame('#7DD3FC','calc-title',HUB.calc.entryHTML()):'')+

    /* period & wellness card (2026-09-30): gender-gated INSIDE cardHTML —
       the gating logic is untouched; this frame is chrome only. */
    (HUB.wellness?frame('#FB7185','wl-heart',HUB.wellness.cardHTML()):'')+

    /* student scanner card (2026-09-30): directly above Gym Fuel per PraBin's order. */
    (HUB.scan?frame('#5EEAD4','scan-doc',HUB.scan.cardHTML()):'')+

    /* style closet card (2026-10-01): directly above Gym Fuel per PraBin's order. */
    (HUB.style?frame('#FB923C','st-closet',HUB.style.cardHTML()):'')+

    /* gym fuel + workout plans */
    (HUB.gym?frame('#C6F135','st-occ-gym',HUB.gym.cardHTML()):'')+

    /* happening: Daily-owned section -> glossy header card with the Add
       button in the header action slot */
    sectionCard('#F87171',HUB.icons.icon('act-event'),
      U.esc(t('daily.happening')),U.esc(t('dly.evSub')),
      '<button class="btn btn-ghost btn-sm" data-ev-add>'+U.esc(t('daily.evAddBtn'))+'</button>',
      '<div id="dyEvents">'+eventsHTML()+'</div>');

  /* capsule bindings */
  const capNew=document.getElementById('dyCapNew');
  if(capNew) capNew.onclick=openCapsuleSheet;
  el.querySelectorAll('[data-cdel]').forEach(b=>{ b.onclick=()=>{
    const arr=st().capsules, i=arr.findIndex(x=>x.id===b.dataset.cdel);
    if(i>=0){ arr.splice(i,1); HUB.store.save(); render(hostEl); }
  };});

  /* events bindings: 3D water-flow carousel (shared with Home) */
  const evAdd=el.querySelector('[data-ev-add]');
  if(evAdd) evAdd.onclick=function(){ openEventFormSheet(null); };
  if(HUB.evCarousel&&HUB.evCarousel.bind){
    try{ if(HUB.cgroups) HUB.cgroups.bindCarousels(el); }catch(e){}
    try{ HUB.evCarousel.bind(el,'#dyEvents'); }catch(e){}
  }else{
    el.querySelectorAll('#dyEvents [data-ev]').forEach(row=>{
      const open=()=>openEventSheet(row.dataset.ev);
      row.onclick=open;
      row.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); open(); } };
    });
  }

  /* gym bindings */
  if(HUB.gym) HUB.gym.bind(el);

  /* calculator entry card binding (full-page overlay; no inline calculator) */
  if(HUB.calc&&HUB.calc.bindEntry) HUB.calc.bindEntry(el);

  /* period & wellness card bindings */
  if(HUB.wellness) HUB.wellness.bind(el);

  /* style closet card bindings */
  if(HUB.style) HUB.style.bind(el);

  /* student scanner card bindings */
  if(HUB.scan) HUB.scan.bind(el);
}

HUB.views=HUB.views||{};
HUB.views.daily={render:render,openCapsuleSheet:openCapsuleSheet,openEventSheet:openEventSheet,openEventFormSheet:openEventFormSheet};
})();
