/* HUB MARKET tab: community marketplace (sell / buy / swap / borrow / free).
   Static build — photos are object URLs (don't survive reload, known limitation).
   Seeds are flagged sample:true and show "Sample" badges. Never invent users. */
(function(){
'use strict';
const {store,ui}=HUB;

let filter='ALL', query='';
let radius=5; // search radius in miles; 'city' = City-wide. Default: nearby-only.

const TYPES=['SELL','BUY','SWAP','BORROW','FREE'];
const TYPE_ICON={SELL:'intent-sell',BUY:'intent-buy',SWAP:'intent-swap',BORROW:'intent-borrow',FREE:'intent-free'};
const RADII=[1,5,10,25,'city'];
const RADIUS_LABEL={1:'1 mi',5:'5 mi',10:'10 mi',25:'25 mi',city:'City-wide'};

/* session-local photo blobs keyed by listing id (memory-vault pattern).
   Object URLs die on reload — the honest label in the form says so. */
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
function fmtDist(l){ const d=distOf(l); return d<0.15?'near you':(Math.round(d*10)/10)+' mi away'; }

function priceLine(l){
  switch(l.type){
    case 'SELL': return ui.fmt$(l.price||0);
    case 'BUY':  return l.price? 'Wants to buy · '+ui.fmt$(l.price) : 'Looking to buy';
    case 'SWAP': return 'Swap for '+ui.esc(l.swapFor||'anything');
    case 'BORROW': return 'Borrow · '+ui.esc(l.borrowFor||'ask me');
    case 'FREE': return 'Free';
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

function thumbHtml(l){
  const ph=photosOf(l), url=ph&&ph[0];
  return url
    ? '<img class="thumb" src="'+ui.esc(url)+'" alt="">'
    : '<div class="thumb thumb-ico" style="display:grid;place-items:center">'+HUB.icons.icon(TYPE_ICON[l.type]||'intent-sell')+'</div>';
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
  const radiusSeg=RADII.map(r=>'<button data-r="'+r+'" class="'+(radius===r?'on':'')+'">'+RADIUS_LABEL[r]+'</button>').join('');
  const chips=['ALL'].concat(TYPES).map(t=>
    '<button class="chip'+(filter===t?' on':'')+'" data-f="'+t+'">'+
    (t==='ALL' ? 'All' : HUB.icons.icon(TYPE_ICON[t])+(t.charAt(0)+t.slice(1).toLowerCase()))+
    '</button>'
  ).join('');
  const scopeLabel=radius==='city'?'City-wide':'Within '+radius+' mi';

  el.innerHTML =
    '<h1>Marketplace</h1>'+
    '<p class="sub" style="margin:4px 0 12px">Buy, sell, swap &amp; borrow with people near you.</p>'+
    '<div class="sub" style="font-weight:700;margin:0 2px 6px">Search radius</div>'+
    '<div class="seg seg-compact" id="mkRadius">'+radiusSeg+'</div>'+
    '<div class="field"><input class="input" id="mkSearch" placeholder="🔍 Search listings…" value="'+ui.esc(query)+'"></div>'+
    '<div class="chips">'+chips+'</div>'+
    '<div><span class="scope-pill" id="mkScopePill">📍 '+ui.esc(scopeLabel)+' · sorted by distance</span></div>'+
    '<div id="mkList">'+
    (list.length? list.map((l,i)=>cardHtml(l,Math.min(i,8)*45)).join('') : emptyHtml())+
    '</div>'+
    '<button class="fab" id="mkPostBtn" style="width:auto;border-radius:999px;padding:0 22px;font-size:16px;font-weight:800" aria-label="Post a listing">＋ Post</button>';

  // search
  const s=document.getElementById('mkSearch');
  s.addEventListener('input',()=>{ query=s.value; render(el); keepFocus(); });
  function keepFocus(){ const n=document.getElementById('mkSearch'); n.focus(); n.setSelectionRange(n.value.length,n.value.length); }

  // chips
  el.querySelectorAll('.chip').forEach(c=>{ c.onclick=()=>{ filter=c.dataset.f; render(el); }; });

  // radius control — live-updates the list
  el.querySelectorAll('#mkRadius button').forEach(b=>{ b.onclick=()=>{ radius=b.dataset.r==='city'?'city':+b.dataset.r; render(el); }; });

  // empty-state widen action
  const w=document.getElementById('mkWiden'); if(w) w.onclick=()=>{ radius='city'; render(el); };

  // cards -> detail
  el.querySelectorAll('[data-listing]').forEach(card=>{
    card.style.cursor='pointer';
    card.onclick=()=>openDetail(card.dataset.listing);
  });

  // post flow
  document.getElementById('mkPostBtn').onclick=openPost;
  const ep=document.getElementById('mkEmptyPost'); if(ep) ep.onclick=openPost;
}

function emptyHtml(){
  const label=radius==='city'?'City-wide':('within '+radius+' mi');
  return '<div class="empty"><span class="empty-ico">'+HUB.icons.icon('intent-free')+'</span>'+
    '<h3>Nothing '+ui.esc(label)+' yet</h3>'+
    '<p class="sub">Try a wider radius — or be the first to post here.</p>'+
    '<div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">'+
    (radius!=='city'?'<button class="btn btn-ghost btn-sm" id="mkWiden">Expand to City-wide</button>':'')+
    '<button class="btn btn-primary btn-sm" id="mkEmptyPost">＋ Post a listing</button></div></div>';
}

/* trust-first card: photo area, price, title + ONE honest trust chip
   (real metadata only — community and time-ago. Never invent seller stats.) */
function cardHtml(l,delay){
  return '<div class="item pop" data-listing="'+l.id+'"'+(delay?' style="animation-delay:'+delay+'ms"':'')+'>'+
    thumbHtml(l)+
    '<div class="grow">'+
      '<div style="display:flex;gap:6px;align-items:center;margin-bottom:5px;flex-wrap:wrap"><span class="badge b-'+l.type+'">'+l.type+'</span>'+ui.sampleBadge(!!l.sample)+'</div>'+
      '<div class="money" style="font-size:17px;margin-bottom:1px">'+priceLine(l)+'</div>'+
      '<h3>'+ui.esc(l.title)+'</h3>'+
      '<div style="margin-top:7px"><span class="trustchip">'+ui.esc(areaOf(l))+' · '+fmtDist(l)+' · '+ui.timeAgo(l.createdAt||Date.now())+'</span></div>'+
    '</div></div>';
}

/* ---------- detail sheet ---------- */
/* demo-honest meetup spot suggestions — labeled as samples, not real data */
const MEETUP_SPOTS=['Student Union lobby','Library main entrance','Police station lobby','Rec center front desk','Community center lobby'];
function meetupSpotsHTML(){
  return '<h3>'+HUB.icons.icon('nav-discover')+' Safe meetup spots</h3>'+
    MEETUP_SPOTS.map(sp=>'<div class="spot"><span style="font-size:18px">📍</span><span>'+ui.esc(sp)+'</span></div>').join('')+
    '<p class="hint">Sample suggestions — real verified spots arrive with the backend. Always meet in public, daytime areas.</p>';
}

function openDetail(id){
  closeOverlays();
  const l=store.find('listings',id); if(!l) return;
  const photos=photosOf(l).filter(Boolean);
  const comments=l.comments||[];
  const mine=l.seller===store.myName();

  let html='<h2>'+ui.esc(l.title)+'</h2>'+
    '<div style="display:flex;gap:6px;align-items:center;margin-bottom:10px"><span class="badge b-'+l.type+'">'+l.type+'</span>'+ui.sampleBadge(!!l.sample)+'</div>'+
    (photos.length
      ? '<div style="margin-bottom:10px"><img class="gal-main" id="mkGalMain" src="'+ui.esc(photos[0])+'" alt="">'+
        (photos.length>1? '<div class="gal-thumbs">'+photos.map((u,i)=>'<img src="'+ui.esc(u)+'" alt="" data-i="'+i+'" class="'+(i===0?'on':'')+'">').join('')+'</div>':'')+'</div>'
      : '')+
    '<div class="money" style="margin-bottom:8px">'+priceLine(l)+'</div>'+
    (l.desc? '<p class="sub" style="margin-bottom:12px;white-space:pre-wrap">'+ui.esc(l.desc)+'</p>':'')+
    '<div class="kv"><span class="sub">Location</span><strong>'+ui.esc(areaOf(l)||'—')+'</strong></div>'+
    '<div class="kv"><span class="sub">Distance</span><strong>'+fmtDist(l)+'</strong></div>'+
    (l.condition? '<div class="kv"><span class="sub">Condition</span><strong>'+ui.esc(l.condition)+'</strong></div>':'')+
    '<div class="divider"></div>'+
    '<div class="row"><div class="avatar">'+ui.esc(ui.initials(l.seller))+'</div>'+
      '<div class="grow"><strong>'+ui.esc(l.seller)+'</strong><div class="sub">Posted '+ui.timeAgo(l.createdAt||Date.now())+'</div></div></div>'+
    '<div class="divider"></div>'+
    '<button class="btn btn-line btn-block" id="mkShowPhone" style="margin-bottom:10px">📞 Show seller\'s number</button>'+
    '<button class="btn btn-primary btn-block" id="mkMsg">💬 Message seller</button>'+
    '<div class="row" style="margin-top:10px;flex-wrap:wrap"><button class="btn btn-ghost btn-sm" id="mkReport">🚩 Report listing</button><button class="btn btn-ghost btn-sm" id="mkBlock">⛔ Block seller</button>'+
    (mine?'<button class="btn btn-ghost btn-sm" id="mkDelete">🗑 Delete listing</button>':'')+'</div>'+
    '<div class="divider"></div>'+
    meetupSpotsHTML()+
    '<div class="divider"></div>'+
    (HUB.trust? HUB.trust.safeMeetupHTML(): '')+
    '<h3 style="margin-bottom:10px">Comments ('+comments.length+')</h3>'+
    '<div id="mkComments">'+
      (comments.length? comments.map(c=>
        '<div class="row" style="align-items:flex-start;margin-bottom:10px"><div class="avatar" style="width:34px;height:34px;font-size:14px">'+ui.esc(ui.initials(c.author))+'</div>'+
        '<div class="grow" style="background:var(--surface2);border-radius:12px;padding:9px 12px"><strong style="font-size:13px">'+ui.esc(c.author)+'</strong><div style="font-size:13px">'+ui.esc(c.text)+'</div><div class="sub" style="font-size:11px;margin-top:2px">'+ui.timeAgo(c.at)+'</div></div></div>'
      ).join('') : '<p class="sub" style="margin-bottom:10px">No comments yet — ask a question!</p>')+
    '</div>'+
    '<div class="askbox"><input class="input" id="mkCommentInput" placeholder="Write a comment…" maxlength="300"><button class="btn btn-primary btn-sm" id="mkCommentSend">Send</button></div>';

  ui.openSheet(html);

  const gm=document.getElementById('mkGalMain');
  if(gm){
    const thumbs=gm.parentElement.querySelectorAll('.gal-thumbs img');
    thumbs.forEach(t=>{ t.onclick=()=>{ gm.src=t.src; thumbs.forEach(x=>x.classList.remove('on')); t.classList.add('on'); }; });
  }

  document.getElementById('mkShowPhone').onclick=e=>{
    e.target.outerHTML='<div class="card tight" style="text-align:center;font-weight:800;font-size:19px;margin-bottom:10px">📞 '+ui.esc(l.phone||'No number provided')+'</div>';
  };
  document.getElementById('mkMsg').onclick=()=>{
    if(HUB.chat&&HUB.chat.openWith) HUB.chat.openWith({name:l.seller,phone:l.phone},'Hi! I saw your listing "'+l.title+'" on Orbit…');
    else ui.toast('Chat is not ready yet');
  };
  document.getElementById('mkReport').onclick=()=>{
    if(HUB.trust&&HUB.trust.reportSheet) HUB.trust.reportSheet('listing',l.id,l.title);
    else ui.toast('Trust tools are not ready yet');
  };
  document.getElementById('mkBlock').onclick=()=>{
    if(HUB.trust&&HUB.trust.blockUser) HUB.trust.blockUser(l.seller);
    else ui.toast('Trust tools are not ready yet');
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
      ui.toast('Listing deleted');
      render(document.getElementById('view-market'));
      return;
    }
    delBtn.dataset.armed='1';
    delBtn.innerHTML='Tap again to confirm delete';
    delBtn.style.color='var(--danger)';
    setTimeout(()=>{ if(document.body.contains(delBtn)){ delete delBtn.dataset.armed; delBtn.innerHTML='🗑 Delete listing'; delBtn.style.color=''; } },3500);
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

/* ---------- post flow ---------- */
function openPost(){
  closeOverlays();
  const p=store.state.profile;
  const campuses=ui.communityOptions(p.campus);
  let selType='', photoURLs=[];

  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-sell')+' Post a listing</h2>'+
    '<div class="field"><label>Title *</label><input class="input" id="mkTitle" placeholder="e.g. Mini fridge — like new" maxlength="80"></div>'+
    '<div class="field"><label>Type *</label><div class="chips" id="mkTypeChips">'+
      TYPES.map(t=>'<button class="chip" data-t="'+t+'">'+HUB.icons.icon(TYPE_ICON[t])+(t.charAt(0)+t.slice(1).toLowerCase())+'</button>').join('')+
    '</div></div>'+
    '<div class="field" id="mkPriceField" hidden><label>Price ($) — SELL only</label><input class="input" id="mkPrice" type="number" min="0" step="1" placeholder="e.g. 25"></div>'+
    '<div class="field" id="mkSwapField" hidden><label>Swap for…</label><input class="input" id="mkSwapFor" placeholder="e.g. a mechanical keyboard" maxlength="60"></div>'+
    '<div class="field" id="mkBorrowField" hidden><label>Borrow duration</label><input class="input" id="mkBorrowFor" placeholder="e.g. 2 weeks" maxlength="40"></div>'+
    '<div class="field"><label>Condition</label><select class="input" id="mkCond"><option value="">Choose…</option>'+
      ['New','Like new','Good','Fair'].map(c=>'<option>'+c+'</option>').join('')+'</select></div>'+
    '<div class="field"><label>Description</label><textarea class="textarea" id="mkDesc" placeholder="Details, pickup info, anything useful…" maxlength="500" style="min-height:110px"></textarea>'+
    '<p class="hint" style="text-align:right"><span id="mkDescCount">0</span>/500</p></div>'+
    '<div class="field"><label>Location (area)</label><select class="input" id="mkCampus">'+campuses+'</select><p class="hint">Your listing shows as “near you” to nearby browsers.</p></div>'+
    '<div class="field"><label>Photos</label><div><label for="mkPhotoInput" class="btn btn-ghost btn-sm">📷 Add photos</label>'+
    '<input type="file" class="hiddenfile" id="mkPhotoInput" accept="image/*" multiple></div>'+
    '<div class="photo-prev" id="mkPhotoPrev"></div><p class="hint">Photos are kept for this session only — they won\'t survive a page reload.</p></div>'+
    '<div class="field"><label>Phone number</label><input class="input" id="mkPhone" type="tel" value="'+ui.esc(p.phone||'')+'" placeholder="So buyers can reach you"></div>'+
    '<button class="btn btn-primary btn-block" id="mkPublish">Post listing</button>'
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

  // photo previews — multi-photo strip with per-photo remove
  const renderPhotoPrev=()=>{
    const prev=document.getElementById('mkPhotoPrev');
    prev.innerHTML=photoURLs.map((p,i)=>
      '<span class="ph-thumb"><img src="'+p.url+'" alt=""><button class="ph-x" data-i="'+i+'" aria-label="Remove photo">✕</button></span>'
    ).join('');
    prev.querySelectorAll('.ph-x').forEach(b=>{
      b.onclick=()=>{
        const gone=photoURLs.splice(+b.dataset.i,1)[0];
        try{ if(gone) URL.revokeObjectURL(gone.url); }catch(e){}
        renderPhotoPrev();
      };
    });
  };
  document.getElementById('mkPhotoInput').addEventListener('change',e=>{
    for(const f of e.target.files) photoURLs.push({url:URL.createObjectURL(f),name:f.name||'photo'});
    e.target.value=''; // allow re-adding the same file
    renderPhotoPrev();
  });

  // description character count
  const mkDesc=document.getElementById('mkDesc'), mkCount=document.getElementById('mkDescCount');
  mkDesc.addEventListener('input',()=>{ mkCount.textContent=String(mkDesc.value.length); });

  document.getElementById('mkPublish').onclick=()=>{
    const title=document.getElementById('mkTitle').value.trim();
    if(!title){ ui.toast('Please add a title'); return; }
    if(!selType){ ui.toast('Please pick a type'); return; }
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
    ui.toast('Listing posted 🎉');
    render(document.getElementById('view-market'));
  };
}

HUB.views.market={render};
})();
