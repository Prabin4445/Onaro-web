/* HUB MARKET tab: community marketplace (sell / buy / swap / borrow / free).
   Static build — photos are object URLs (don't survive reload, known limitation).
   Seeds are flagged sample:true and show "Sample" badges. Never invent users. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
/* Workstream F: currency symbol for the device's selected country. */
function curSym(){ try{ return (HUB.i18n.currencySymbol?HUB.i18n.currencySymbol():'$').trim()||'$'; }catch(e){ return '$'; } }

let filter='ALL', query='';
let radius=20; // search radius in miles; 'city' = City-wide. Default: 20 mi.

const TYPES=['SELL','BUY','SWAP','BORROW','FREE'];
/* glossy-redesign: clay intent icon per type filter chip (icon() carries an
   emoji fallback, so nothing ever renders blank) */
const TYPE_ICON={ALL:'hm-mod-market',SELL:'intent-sell',BUY:'intent-buy',SWAP:'intent-swap',BORROW:'intent-borrow',FREE:'intent-free'};
const RADII=[1,5,10,20,25,'city'];
const RADIUS_LABEL={1:'market.radius.1',5:'market.radius.5',10:'market.radius.10',20:'market.radius.20',25:'market.radius.25',city:'market.radius.city'};
/* Condition is stored as a stable key; older seeds may carry English labels. */
const COND_KEY={new:'new',likenew:'likenew',good:'good',fair:'fair',New:'new','Like new':'likenew',Good:'good',Fair:'fair'};
function condLabel(c){ const k=COND_KEY[c]; return k?t('market.p.cond.'+k):String(c||''); }

/* Neutral commerce glyphs (2026-09-22 real-commerce restyle): monochrome inline
   SVGs replace the clay 3D intent icons on tiles and in the photo flow. */
const PH_SVG='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="M4.5 17.5 10 12l3.5 3.5L17 12l2.5 2.5"/></svg>';
const ZOOM_SVG='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M16.5 16.5 21 21"/></svg>';
/* Neutral commerce badge: type label from i18n (market.type.X), not the raw key.
   SELL gets the volt brand accent; photo overlays stay top-left. */
function typeBadge(ty){
  return '<span class="mkbadge'+(ty==='SELL'?' mkbadge-volt':'')+'">'+ui.esc(t('market.type.'+ty)||ty)+'</span>';
}

/* Seller photos: up to 4 per listing, downscaled client-side to ~1000px JPEG.
   Session-local (memory-only photoBlobs) — the honest label in the form says so. */
const MAX_PHOTOS=4;
function readFileURL(file){
  return new Promise(function(res,rej){ const r=new FileReader(); r.onload=function(){res(r.result);}; r.onerror=rej; r.readAsDataURL(file); });
}
function downscalePhoto(file,maxDim){
  return readFileURL(file).then(function(raw){
    return new Promise(function(res){
      const img=new Image();
      img.onload=function(){
        try{
          let w=img.width,h=img.height;
          const k=Math.min(1,maxDim/Math.max(w,h));
          w=Math.max(1,Math.round(w*k)); h=Math.max(1,Math.round(h*k));
          const c=document.createElement('canvas'); c.width=w; c.height=h;
          c.getContext('2d').drawImage(img,0,0,w,h);
          res(c.toDataURL('image/jpeg',0.82));
        }catch(e){ res(raw); }
      };
      img.onerror=function(){ res(raw); };
      img.src=raw;
    });
  });
}
const photoBlobs={};
function photosOf(l){ return photoBlobs[l.id]||l.photos||[]; }
function revokePhotos(id){ (photoBlobs[id]||[]).forEach(u=>{try{URL.revokeObjectURL(u)}catch(e){}}); delete photoBlobs[id]; }

/* distance: real field on user-posted listings; deterministic illustrative
   distances for legacy seeds (their Sample badge discloses this). */
function hashStr(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
function distOf(l){
  if(typeof l.dist==='number'&&isFinite(l.dist)) return l.dist;
  return Math.round((0.2+(hashStr(String(l.id||l.title||'x'))%280)/100)*10)/10; // 0.2–3.0
}
function areaOf(l){ return l.area||l.campus||''; }
function fmtDist(l){ const d=distOf(l); return d<0.15?t('market.nearYou'):t('market.miAway',{d:(Math.round(d*10)/10)}); }

function priceLine(l){
  switch(l.type){
    case 'SELL': return ui.fmt$(l.price||0);
    case 'BUY':  return l.price? t('market.price.wantBuy',{p:ui.fmt$(l.price)}) : t('market.price.lookingBuy');
    case 'SWAP': return l.swapFor? t('market.price.swapFor',{x:ui.esc(l.swapFor)}) : t('market.price.swap');
    case 'BORROW': return t('market.price.borrow',{x:ui.esc(l.borrowFor||t('market.price.askme'))});
    case 'FREE': return t('market.price.free');
    default: return '';
  }
}

function filtered(){
  const q=query.trim().toLowerCase();
  return store.state.listings
    .filter(l=>!ui.isBlocked(l.seller))
    .filter(l=>filter==='ALL'||l.type===filter)
    .filter(l=>!q || (l.title+' '+(l.desc||'')).toLowerCase().includes(q))
    .filter(l=>radius==='city'||distOf(l)<=radius)
    .slice().sort((a,b)=>(distOf(a)-distOf(b))||((b.createdAt||0)-(a.createdAt||0)));
}

/* chip counts are computed over the search+radius-filtered set (before the
   type filter) so counts stay stable while switching between type chips. */
function countsBase(){
  const q=query.trim().toLowerCase();
  return store.state.listings
    .filter(l=>!ui.isBlocked(l.seller))
    .filter(l=>!q || (l.title+' '+(l.desc||'')).toLowerCase().includes(q))
    .filter(l=>radius==='city'||distOf(l)<=radius);
}

/* Overlay hygiene: bottom sheets and chatroot overlays (search/pulse/
   notifications/chat) are mutually exclusive — opening one closes the
   others so they never visually stack. */
function closeOverlays(){
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
}

function render(el){
  const list=filtered();
  const base=countsBase();
  const countFor=function(ty){ return ty==='ALL'?base.length:base.filter(l=>l.type===ty).length; };
  const radiusSeg=RADII.map(r=>'<button data-r="'+r+'" class="'+(radius===r?'on':'')+'">'+t(RADIUS_LABEL[r])+'</button>').join('');
  /* glossy filter chips: clay intent icon + label + live count */
  const chips=['ALL'].concat(TYPES).map(ty=>
    '<button class="mk-chip'+(filter===ty?' on':'')+'" data-f="'+ty+'">'+
    HUB.icons.icon(TYPE_ICON[ty])+
    '<span>'+(ty==='ALL' ? t('market.all') : t('market.type.'+ty))+'</span>'+
    ' <span class="chip-n">'+countFor(ty)+'</span></button>'
  ).join('');
  const scopeLabel=radius==='city'?t('market.radius.city'):t('market.scopeMi',{r:radius});
  const demoNote=list.some(l=>l.sample)?'<div class="mkdemonote">'+t('market.demoNote')+'</div>':'';

  el.innerHTML =
    '<div class="mk-hero pop"><div class="mk-hero-row">'+
      '<span class="mk-hero-ico">'+HUB.icons.icon('hm-mod-market')+'</span>'+
      '<div><h1>'+t('market.title')+'</h1>'+
      '<p class="mk-hero-sub">'+t('mkt.heroSub')+'</p></div>'+
    '</div>'+
    '<div class="mk-hero-cta"><button class="mk-hero-post" id="mkHeroPost">+ '+ui.esc(t('market.emptyPost'))+'</button></div>'+
    '<div class="mk-hero-count" style="position:relative;z-index:1;margin-top:8px">'+ui.esc(t('market.scopePill',{scope:scopeLabel}))+'</div></div>'+
    '<div class="seg seg-compact" id="mkRadius" role="group" aria-label="'+ui.esc(t('market.searchRadius'))+'">'+radiusSeg+'</div>'+
    '<div class="mk-search-wrap"><span class="mk-search-ico">'+HUB.icons.icon('ic-search')+'</span><input class="input" id="mkSearch" placeholder="'+t('market.searchPh')+'" value="'+ui.esc(query)+'"></div>'+
    '<div class="chips">'+chips+'</div>'+
    demoNote+
    '<div class="mkgrid" id="mkList">'+
    (list.length? adInterleavedHTML(list) : emptyHtml())+
    '</div>'+
    '<button class="fab" id="mkPostBtn" aria-label="'+t('market.postAria')+'">'+t('market.postShort')+'</button>';

  // search
  const s=document.getElementById('mkSearch');
  s.addEventListener('input',()=>{ query=s.value; render(el); keepFocus(); });
  function keepFocus(){ const n=document.getElementById('mkSearch'); n.focus(); n.setSelectionRange(n.value.length,n.value.length); }

  // chips
  el.querySelectorAll('.mk-chip').forEach(c=>{ c.onclick=()=>{ filter=c.dataset.f; render(el); }; });

  // radius control — live-updates the list
  el.querySelectorAll('#mkRadius button').forEach(b=>{ b.onclick=()=>{ radius=b.dataset.r==='city'?'city':+b.dataset.r; render(el); }; });

  // empty-state widen action
  const w=document.getElementById('mkWiden'); if(w) w.onclick=()=>{ radius='city'; render(el); };

  // cards -> detail
  el.querySelectorAll('[data-listing]').forEach(card=>{
    card.style.cursor='pointer';
    card.onclick=()=>openDetail(card.dataset.listing);
    card.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openDetail(card.dataset.listing); } });
  });

  // sponsored cards -> demo honesty sheet
  if(HUB.ads&&HUB.ads.bind) HUB.ads.bind(el);

  // post flow
  document.getElementById('mkPostBtn').onclick=openPost;
  document.getElementById('mkHeroPost').onclick=openPost;
  const ep=document.getElementById('mkEmptyPost'); if(ep) ep.onclick=openPost;
}

/* sponsored interleave: organic cards every 5th position get a Sponsored card.
   Demo inventory only — every ad card carries Sponsored + Demo ad labels. */
function adInterleavedHTML(list){
  const cards=list.map((l,i)=>tileHtml(l,Math.min(i,8)*45));
  if(HUB.ads&&HUB.ads.interleaveFeed) return HUB.ads.interleaveFeed(cards);
  return cards.join('');
}

function emptyHtml(){
  const label=radius==='city'?t('market.radius.city'):t('market.emptyWithin',{r:radius});
  return '<div class="mk-empty"><span class="mk-empty-ico">'+HUB.icons.icon('hm-mod-market')+'</span>'+
    '<h3>'+t('market.emptyTitle',{label:ui.esc(label)})+'</h3>'+
    '<p class="sub">'+t('market.emptySub')+'</p>'+
    '<div class="mk-empty-actions">'+
    (radius!=='city'?'<button class="btn btn-ghost btn-sm" id="mkWiden">'+t('market.widen')+'</button>':'')+
    '<button class="btn btn-primary btn-sm" id="mkEmptyPost">'+t('market.emptyPost')+'</button></div></div>';
}

/* glossy commerce card: photo (type pill overlay) → volt price → 2-line
   title → area·distance meta → seller row (avatar + name + distance).
   Real metadata only — condition stays detail-only, per real apps. */
function tileHtml(l,delay){
  const ph=photosOf(l), url=ph&&ph[0];
  const media=url
    ? '<img src="'+ui.esc(url)+'" alt="" loading="lazy">'
    : '<div class="mktile-ico">'+PH_SVG+'</div>';
  return '<div class="mktile pop" data-listing="'+l.id+'"'+(delay?' style="animation-delay:'+delay+'ms"':'')+' role="button" tabindex="0" aria-label="'+ui.esc(l.title)+'">'+
    '<div class="mktile-media">'+media+typeBadge(l.type)+'</div>'+
    '<div class="mktile-body">'+
      '<div class="money">'+priceLine(l)+'</div>'+
      '<h3>'+ui.esc(l.title)+'</h3>'+
      '<div class="meta"><span class="meta-main">'+ui.esc(areaOf(l))+' · '+fmtDist(l)+'</span>'+(l.sample?'<span class="mksample-inline">'+ui.esc(t('honesty.sample'))+'</span>':'')+'</div>'+
      '<div class="mkseller-row"><span class="avatar">'+ui.avatarFor(l.seller)+'</span>'+
        '<span class="who">'+ui.esc(l.seller)+'</span>'+
        '<span class="dist">'+fmtDist(l)+'</span></div>'+
    '</div></div>';
}

/* ---------- detail sheet ---------- */
/* demo-honest meetup spot suggestions — labeled as samples, not real data */
const MEETUP_SPOTS=['market.spot.1','market.spot.2','market.spot.3','market.spot.4','market.spot.5'];
function meetupSpotsHTML(){
  return '<h3>'+HUB.icons.icon('nav-discover')+' '+t('market.d.meetupTitle')+'</h3>'+
    MEETUP_SPOTS.map(sp=>'<div class="spot">'+ui.esc(t(sp))+'</div>').join('')+
    '<p class="hint">'+t('market.d.meetupHint')+'</p>';
}

/* Detail sheet (real-commerce layout): badges → photo carousel (counter +
   taller media) → 22px price → 17px title → 2-col specs grid → seller card
   (REAL listing count from the store; no invented ratings) → description →
   safety → comments → "you may also like" → sticky Message-seller CTA. */
function openDetail(id){
  closeOverlays();
  const l=store.find('listings',id); if(!l) return;
  const photos=photosOf(l).filter(Boolean);
  const comments=l.comments||[];
  const mine=l.seller===store.myName();
  const sellerCount=store.state.listings.filter(function(x){ return x.seller===l.seller; }).length;
  const typeWord=t('market.p.typeLabel').replace(/\s*\*+\s*$/,'');
  const postedWord=t('market.d.posted').replace(/\s*\{ago\}\s*/,'');

  let html='<div style="display:flex;gap:6px;align-items:center;margin-bottom:10px;flex-wrap:wrap">'+typeBadge(l.type)+ui.sampleBadge(!!l.sample)+'</div>'+
    (photos.length? '<div class="mkflowwrap" style="margin-bottom:6px">'+photoFlowHTML(photos)+'</div>' : '')+
    '<div class="mkd-price">'+priceLine(l)+'</div>'+
    '<h2 class="mkd-title">'+ui.esc(l.title)+'</h2>'+
    '<div class="mkspecs">'+
      (l.condition? '<div class="mkspec"><div class="k">'+t('market.d.condition')+'</div><div class="v">'+ui.esc(condLabel(l.condition))+'</div></div>':'')+
      '<div class="mkspec"><div class="k">'+ui.esc(typeWord)+'</div><div class="v">'+ui.esc(t('market.type.'+l.type))+'</div></div>'+
      '<div class="mkspec"><div class="k">'+ui.esc(postedWord)+'</div><div class="v">'+ui.timeAgo(l.createdAt||Date.now())+'</div></div>'+
      '<div class="mkspec"><div class="k">'+t('market.d.distance')+'</div><div class="v">'+fmtDist(l)+'</div></div>'+
    '</div>'+
    '<div class="mkseller"><div class="avatar">'+ui.avatarFor(l.seller)+'</div>'+
      '<div class="grow"><strong>'+ui.esc(l.seller)+'</strong><div class="sub">'+t('market.d.listings',{n:sellerCount})+' · '+t('market.d.posted',{ago:ui.timeAgo(l.createdAt||Date.now())})+'</div></div></div>'+
    (l.desc? '<p class="mkd-desc">'+ui.esc(l.desc)+'</p>':'')+
    '<div class="divider"></div>'+
    '<button class="btn btn-line btn-block" id="mkShowPhone" style="margin-bottom:10px">'+t('market.d.showPhone')+'</button>'+
    '<div class="row" style="flex-wrap:wrap;margin-bottom:6px"><button class="btn btn-ghost btn-sm" id="mkReport">'+t('market.d.report')+'</button><button class="btn btn-ghost btn-sm" id="mkBlock">'+t('market.d.block')+'</button>'+
    (mine?'<button class="btn btn-ghost btn-sm" id="mkDelete">'+t('market.d.delete')+'</button>':'')+'</div>'+
    '<div class="divider"></div>'+
    meetupSpotsHTML()+
    '<div class="divider"></div>'+
    (HUB.trust? HUB.trust.safeMeetupHTML(): '')+
    '<h3 style="margin-bottom:10px">'+t('market.d.comments',{n:comments.length})+'</h3>'+
    '<div id="mkComments">'+
      (comments.length? comments.map(c=>
        '<div class="row" style="align-items:flex-start;margin-bottom:10px"><div class="avatar" style="width:34px;height:34px;font-size:14px">'+ui.avatarFor(c.author)+'</div>'+
        '<div class="grow" style="background:var(--surface2);border-radius:12px;padding:9px 12px"><strong style="font-size:13px">'+ui.esc(c.author)+'</strong><div style="font-size:13px">'+ui.esc(c.text)+'</div><div class="sub" style="font-size:11px;margin-top:2px">'+ui.timeAgo(c.at)+'</div></div></div>'
      ).join('') : '<p class="sub" style="margin-bottom:10px">'+t('market.d.noComments')+'</p>')+
    '</div>'+
    '<div class="askbox"><input class="input" id="mkCommentInput" placeholder="'+t('market.d.commentPh')+'" maxlength="300"><button class="btn btn-primary btn-sm" id="mkCommentSend">'+t('common.send')+'</button></div>'+
    similarHTML(l)+
    '<div class="mkcta"><button class="btn btn-primary btn-block" id="mkMsg">'+t('market.d.msgSeller')+'</button></div>';

  ui.openSheet(html);

  /* water-crystal 3D flow carousel for listing photos: shared tilt/drift
     from the groups carousel; tap (not drag) opens the pinch-zoom lightbox */
  try{ if(HUB.cgroups&&HUB.cgroups.bindCarousels) HUB.cgroups.bindCarousels(document.getElementById('sheetBox')); }catch(e){}
  bindPhotoTaps(photos);
  bindPhotoCounter(photos.length);
  document.querySelectorAll('#sheetBox [data-sim]').forEach(function(el){
    el.addEventListener('click',function(){ openDetail(el.dataset.sim); });
  });

  document.getElementById('mkShowPhone').onclick=e=>{
    e.target.outerHTML='<div class="card tight" style="text-align:center;font-weight:800;font-size:19px;margin-bottom:10px">'+ui.esc(l.phone||t('market.d.noNumber'))+'</div>';
  };
  document.getElementById('mkMsg').onclick=()=>{
    if(HUB.chat&&HUB.chat.openWith) HUB.chat.openWith({name:l.seller,phone:l.phone},'Hi! I saw your listing "'+l.title+'" on Onaro…');
    else ui.toast(t('market.d.chatNotReady'));
  };
  document.getElementById('mkReport').onclick=()=>{
    if(HUB.trust&&HUB.trust.reportSheet) HUB.trust.reportSheet('listing',l.id,l.title);
    else ui.toast(t('market.d.trustNotReady'));
  };
  document.getElementById('mkBlock').onclick=()=>{
    if(HUB.trust&&HUB.trust.blockUser) HUB.trust.blockUser(l.seller);
    else ui.toast(t('market.d.trustNotReady'));
  };

  // Delete: only the user's own listings get the button (two-tap confirm).
  // Revokes session photo blobs, removes from the store, closes the sheet,
  // and re-renders the market list so no stale state lingers.
  const delBtn=document.getElementById('mkDelete');
  if(delBtn) delBtn.onclick=()=>{
    if(delBtn.dataset.armed){
      revokePhotos(l.id);
      store.remove('listings',l.id);
      ui.closeSheet();
      ui.toast(t('market.d.deleted'));
      render(document.getElementById('view-market'));
      return;
    }
    delBtn.dataset.armed='1';
    delBtn.innerHTML=t('market.d.confirmDelete');
    delBtn.style.color='var(--danger)';
    setTimeout(()=>{ if(document.body.contains(delBtn)){ delete delBtn.dataset.armed; delBtn.innerHTML=t('market.d.delete'); delBtn.style.color=''; } },3500);
  };

  const addComment=()=>{
    const inp=document.getElementById('mkCommentInput');
    const text=inp.value.trim(); if(!text) return;
    l.comments=(l.comments||[]).concat([{author:store.myName(),text,at:Date.now()}]);
    store.save();
    openDetail(id); // re-render sheet with the new comment
    render(document.getElementById('view-market')); // refresh card comment count
  };
  document.getElementById('mkCommentSend').onclick=addComment;
  document.getElementById('mkCommentInput').addEventListener('keydown',e=>{ if(e.key==='Enter') addComment(); });
}

/* ---------- listing photo carousel + pinch-zoom lightbox ---------- */
function photoFlowHTML(photos){
  const cards=photos.map(function(u,i){
    return '<article class="gcard mkphoto" data-photo="'+i+'" tabindex="0" role="button" aria-label="'+ui.esc(t('market.d.photoOf',{i:i+1,n:photos.length}))+'">'+
      '<div class="gcard-media mkphoto-media"><img src="'+ui.esc(u)+'" alt="" loading="lazy" draggable="false"></div>'+
      '<div class="gcard-body"><div class="gcard-meta"><span class="gdist">'+(i+1)+' / '+photos.length+'</span></div></div></article>';
  }).join('');
  return '<div class="flowwrap"><div class="flow" id="mkPhotoFlow">'+cards+'</div></div>'+
    '<div class="mkphoto-count" id="mkPhotoCount">1 / '+photos.length+'</div>'+
    '<div class="mkphoto-zoomhint" aria-hidden="true">'+ZOOM_SVG+'</div>';
}
/* floating "1 / 4" badge over the photo flow: tracks the scroll-snapped card */
function bindPhotoCounter(n){
  const flow=document.getElementById('mkPhotoFlow'), badge=document.getElementById('mkPhotoCount');
  if(!flow||!badge) return;
  if(n<2){ badge.style.display='none'; return; }
  const upd=function(){
    const max=flow.scrollWidth-flow.clientWidth;
    const i=max>0?Math.round(flow.scrollLeft/max*(n-1)):0;
    badge.textContent=(i+1)+' / '+n;
  };
  flow.addEventListener('scroll',upd,{passive:true});
  upd();
}
/* "You may also like": up to 6 same-type listings (excluding self), compact
   tiles reusing the new card grammar. Tapping one opens its detail sheet. */
function similarHTML(l){
  const sims=store.state.listings
    .filter(function(x){ return x.id!==l.id&&x.type===l.type&&!ui.isBlocked(x.seller); })
    .slice(0,6);
  if(!sims.length) return '';
  return '<div class="divider"></div><h3 style="margin-bottom:8px">'+t('market.d.similar')+'</h3>'+
    '<div class="mksim">'+sims.map(function(x){
      const ph=photosOf(x), url=ph&&ph[0];
      return '<button class="mksim-card" data-sim="'+x.id+'" aria-label="'+ui.esc(x.title)+'">'+
        '<div class="mksim-media">'+(url?'<img src="'+ui.esc(url)+'" alt="" loading="lazy">':'<div class="mktile-ico">'+PH_SVG+'</div>')+typeBadge(x.type)+'</div>'+
        '<div class="money">'+priceLine(x)+'</div>'+
        '<div class="t">'+ui.esc(x.title)+'</div></button>';
    }).join('')+'</div>';
}
function bindPhotoTaps(photos){
  document.querySelectorAll('#mkPhotoFlow [data-photo]').forEach(function(card){
    let px=0,py=0;
    card.addEventListener('pointerdown',function(e){ px=e.clientX; py=e.clientY; },{passive:true});
    const go=function(e){
      if(e&&Math.hypot((e.clientX||0)-px,(e.clientY||0)-py)>10) return; /* it was a drag */
      openLightbox(photos[+card.dataset.photo],{keepSheet:true});
    };
    card.addEventListener('click',go);
    card.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openLightbox(photos[+card.dataset.photo],{keepSheet:true}); } });
  });
}
/* Fullscreen lightbox: pinch-to-zoom (two-finger pointer events), double-tap
   to zoom, drag to pan when zoomed, wheel zoom on desktop. Dismisses with
   the same standard as all overlays: ✕ button, backdrop tap, Escape. */
function openLightbox(src,opts){
  if(!opts||!opts.keepSheet) closeOverlays();
  const ov=document.createElement('div');
  ov.className='mkzoom'; ov.setAttribute('role','dialog'); ov.setAttribute('aria-modal','true');
  ov.setAttribute('aria-label',t('market.d.closePhoto'));
  ov.innerHTML='<button class="sheetx mkzoom-x" aria-label="'+ui.esc(t('market.d.closePhoto'))+'">✕</button>'+
    '<div class="mkzoom-stage"><img src="'+ui.esc(src)+'" alt="" draggable="false"></div>';
  document.body.appendChild(ov);
  const img=ov.querySelector('img'), stage=ov.querySelector('.mkzoom-stage');
  let scale=1, tx=0, ty=0;
  const apply=function(){ img.style.transform='translate(calc(-50% + '+tx+'px),calc(-50% + '+ty+'px)) scale('+scale+')'; };
  const clampS=function(s){ return Math.min(4,Math.max(1,s)); };
  const pts=new Map();
  let pinch0=0, scale0=1;
  img.addEventListener('pointerdown',function(e){
    try{ img.setPointerCapture(e.pointerId); }catch(err){}
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(pts.size===2){ const p=Array.from(pts.values()); pinch0=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)||0; scale0=scale; }
  });
  img.addEventListener('pointermove',function(e){
    if(!pts.has(e.pointerId)) return;
    const prev=pts.get(e.pointerId);
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(pts.size===1&&scale>1){ tx+=e.clientX-prev.x; ty+=e.clientY-prev.y; apply(); }
    else if(pts.size===2&&pinch0>0){
      const p=Array.from(pts.values());
      const d=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);
      scale=clampS(scale0*d/pinch0); apply();
    }
  });
  const endP=function(e){
    pts.delete(e.pointerId);
    if(pts.size<2) pinch0=0;
    if(scale<=1.05){ scale=1; tx=0; ty=0; apply(); }
  };
  img.addEventListener('pointerup',endP);
  img.addEventListener('pointercancel',endP);
  stage.addEventListener('wheel',function(e){
    e.preventDefault();
    scale=clampS(scale*(e.deltaY<0?1.18:0.85)); apply();
  },{passive:false});
  let lastTap=0;
  img.addEventListener('click',function(){
    const now=Date.now();
    if(now-lastTap<320){ scale=scale>1?1:2.5; tx=0; ty=0; apply(); lastTap=0; }
    else lastTap=now;
  });
  const close=function(){ ov.remove(); document.removeEventListener('keydown',onKey); };
  ov.querySelector('.mkzoom-x').addEventListener('click',close);
  stage.addEventListener('click',function(e){ if(e.target===stage) close(); });
  function onKey(e){ if(e.key==='Escape') close(); }
  document.addEventListener('keydown',onKey);
}

/* ---------- post flow ---------- */
function openPost(){
  closeOverlays();
  const p=store.state.profile;
  const campuses=ui.communityOptions(p.campus);
  let selType='', photoURLs=[];

  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-sell')+' '+t('market.p.title')+'</h2>'+
    '<div class="field"><label>'+t('market.p.titleLabel')+'</label><input class="input" id="mkTitle" placeholder="'+ui.esc(t('market.p.titlePh'))+'" maxlength="80"></div>'+
    '<div class="field"><label>'+t('market.p.typeLabel')+'</label><div class="chips" id="mkTypeChips">'+
      TYPES.map(ty=>'<button class="chip" data-t="'+ty+'">'+t('market.type.'+ty)+'</button>').join('')+
    '</div></div>'+
    '<div class="field" id="mkPriceField" hidden><label>'+t('market.p.priceLabel',{sym:curSym()})+'</label><input class="input" id="mkPrice" type="number" min="0" step="1" placeholder="'+ui.esc(t('market.p.pricePh'))+'"></div>'+
    '<div class="field" id="mkSwapField" hidden><label>'+t('market.p.swapLabel')+'</label><input class="input" id="mkSwapFor" placeholder="'+ui.esc(t('market.p.swapPh'))+'" maxlength="60"></div>'+
    '<div class="field" id="mkBorrowField" hidden><label>'+t('market.p.borrowLabel')+'</label><input class="input" id="mkBorrowFor" placeholder="'+ui.esc(t('market.p.borrowPh'))+'" maxlength="40"></div>'+
    '<div class="field"><label>'+t('market.p.condLabel')+'</label><select class="input" id="mkCond"><option value="">'+t('market.p.condChoose')+'</option>'+
      [['new','market.p.cond.new'],['likenew','market.p.cond.likenew'],['good','market.p.cond.good'],['fair','market.p.cond.fair']].map(function(vk){return '<option value="'+vk[0]+'">'+ui.esc(t(vk[1]))+'</option>';}).join('')+'</select></div>'+
    '<div class="field"><label>'+t('market.p.descLabel')+'</label><textarea class="textarea" id="mkDesc" placeholder="'+ui.esc(t('market.p.descPh'))+'" maxlength="500" style="min-height:110px"></textarea>'+
    '<p class="hint" style="text-align:right"><span id="mkDescCount">0</span>/500</p></div>'+
    '<div class="field"><label>'+t('market.p.areaLabel')+'</label><select class="input" id="mkCampus">'+campuses+'</select><p class="hint">'+t('market.p.areaHint')+'</p></div>'+
    '<div class="field"><label>'+t('market.p.photosLabel')+'</label><div><label for="mkPhotoInput" class="btn btn-ghost btn-sm">'+ui.esc(t('market.p.addPhotos'))+'</label>'+
    '<input type="file" class="hiddenfile" id="mkPhotoInput" accept="image/*" multiple></div>'+
    '<div class="photo-prev" id="mkPhotoPrev"></div><p class="hint">'+t('market.p.photosHint')+'</p></div>'+
    '<div class="field"><label>'+t('market.p.phoneLabel')+'</label><input class="input" id="mkPhone" type="tel" value="'+ui.esc(p.phone||'')+'" placeholder="'+ui.esc(t('market.p.phonePh'))+'"></div>'+
    '<button class="btn btn-primary btn-block" id="mkPublish">'+t('market.p.publish')+'</button>'
  );

  // type chips
  document.querySelectorAll('#mkTypeChips .chip').forEach(c=>{
    c.onclick=()=>{
      document.querySelectorAll('#mkTypeChips .chip').forEach(x=>x.classList.remove('on'));
      c.classList.add('on'); selType=c.dataset.t;
      document.getElementById('mkPriceField').hidden=selType!=='SELL'&&selType!=='BUY';
      document.getElementById('mkSwapField').hidden=selType!=='SWAP';
      document.getElementById('mkBorrowField').hidden=selType!=='BORROW';
    };
  });

  // photo previews — multi-photo strip with per-photo remove + "n of 4" counter
  const renderPhotoPrev=()=>{
    const prev=document.getElementById('mkPhotoPrev');
    prev.innerHTML=photoURLs.map((p,i)=>
      '<span class="ph-thumb"><img src="'+ui.esc(p.url)+'" alt=""><button class="ph-x" data-i="'+i+'" aria-label="'+ui.esc(t('market.p.removePhoto'))+'">✕</button></span>'
    ).join('')+
    '<div class="sub" style="width:100%">'+ui.esc(t('market.p.photosCount',{n:photoURLs.length}))+'</div>';
    prev.querySelectorAll('.ph-x').forEach(b=>{
      b.onclick=()=>{ photoURLs.splice(+b.dataset.i,1); renderPhotoPrev(); };
    });
  };
  document.getElementById('mkPhotoInput').addEventListener('change',function(e){
    const files=Array.prototype.slice.call(e.target.files||[]);
    e.target.value=''; // allow re-adding the same file
    const room=MAX_PHOTOS-photoURLs.length;
    if(room<=0){ ui.toast(t('market.p.maxPhotos')); return; }
    if(files.length>room) ui.toast(t('market.p.maxPhotos'));
    files.slice(0,room).forEach(function(f){
      downscalePhoto(f,1000).then(function(url){
        if(photoURLs.length>=MAX_PHOTOS){ ui.toast(t('market.p.maxPhotos')); return; }
        photoURLs.push({url:url,name:f.name||'photo.jpg'});
        renderPhotoPrev();
      });
    });
  });

  // description character count
  const mkDesc=document.getElementById('mkDesc'), mkCount=document.getElementById('mkDescCount');
  mkDesc.addEventListener('input',()=>{ mkCount.textContent=String(mkDesc.value.length); });

  document.getElementById('mkPublish').onclick=()=>{
    const title=document.getElementById('mkTitle').value.trim();
    if(!title){ ui.toast(t('market.p.needTitle')); return; }
    if(!selType){ ui.toast(t('market.p.needType')); return; }
    const price=Number(document.getElementById('mkPrice').value)||0;
    const campus=document.getElementById('mkCampus').value;
    const id=store.uid();
    photoBlobs[id]=photoURLs.map(p=>p.url); // session-local blob map; revoked if removed above
    const obj={
      id, type:selType, title,
      condition:document.getElementById('mkCond').value,
      price, swapFor:document.getElementById('mkSwapFor').value.trim(),
      borrowFor:document.getElementById('mkBorrowFor').value.trim(),
      desc:document.getElementById('mkDesc').value.trim(),
      area:campus, campus, dist:0.1, // user's own listing: "near you"
      seller:store.myName(),
      phone:document.getElementById('mkPhone').value.trim(),
      photos:[], comments:[],
    };
    // persist phone on profile for next time
    if(obj.phone&&obj.phone!==p.phone){ p.phone=obj.phone; }
    store.add('listings',obj);
    ui.closeSheet();
    ui.toast(t('market.p.posted'));
    render(document.getElementById('view-market'));
  };
}

HUB.views.market={render};
/* Post FAB gets out of the way while scrolling (mirrors the Ask pill's
   hide-on-scroll-down / return-on-scroll-up-or-idle in app.js), so it never
   covers listing cards mid-scroll. Attached once at module level. */
(function(){
  let lastY=0, idleT=null;
  const onScroll=function(){
    const fab=document.getElementById('mkPostBtn');
    if(!fab) return;
    const views=document.querySelector('.views');
    const y=Math.max(window.scrollY||0, views?views.scrollTop:0);
    if(y>lastY+6) fab.classList.add('hide');
    else if(y<lastY-4) fab.classList.remove('hide');
    lastY=y;
    clearTimeout(idleT);
    idleT=setTimeout(function(){ const f=document.getElementById('mkPostBtn'); if(f) f.classList.remove('hide'); },1400);
  };
  window.addEventListener('scroll',onScroll,{passive:true});
  const views=document.querySelector('.views');
  if(views) views.addEventListener('scroll',onScroll,{passive:true});
})();
HUB.mkZoom=HUB.mkZoom||{};
HUB.mkZoom.open=openLightbox;
})();
