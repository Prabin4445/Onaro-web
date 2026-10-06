/* HUB PEOPLE (Workstream D): same-institution / same-community people discovery.
   Students see "People at [Campus]"; community members see "People in [Community]".
   Renders as the "People" segment inside the Groups tab (HUB.views.groups delegates
   here when its sub is 'people'). Browser-local only; every sample person wears a
   Sample badge; the surface carries a demo note. No presence dots, no fake online
   state — nothing here claims a real person is online or reachable. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

/* clay avatar palette — same brand-safe set as ME, no purple */
const PPL_COLORS=['#1F7A4D','#2563EB','#C22E1F','#0F766E','#B45309','#C2410C','#1D4ED8','#131A00'];

let fSkill=null;    // active skill filter (lowercased), null = all
let fMutual=false;  // "shared households" filter
let fFollowing=false;// "people I follow" filter
let qName='';       // name search text

function myCampus(){ return store.state.profile.campus||''; }
function isStudent(){ return store.state.profile.audience==='student'; }
function peopleTitle(){ return isStudent() ? t('people.titleAt',{c:myCampus()}) : t('people.titleIn',{c:myCampus()}); }
function firstName(n){ return String(n||'').trim().split(/\s+/)[0]||t('people.there'); }
function avColor(p){ return PPL_COLORS[Math.abs(Number(p.avatarColor)||0)%PPL_COLORS.length]; }

/* ---- follow graph (local; production = server accounts) ---- */
function isFollowing(id){ return (store.state.following||[]).indexOf(id)>=0; }
function isFollower(id){ return (store.state.followers||[]).indexOf(id)>=0; }
function isMutual(id){ return isFollowing(id)&&isFollower(id); }
function setFollow(id,on){
  const f=store.state.following=store.state.following||[];
  const i=f.indexOf(id), p=store.find('people',id), nm=firstName(p&&p.name);
  if(on&&i<0){ f.push(id); ui.toast(t('people.followToast',{name:nm})); }
  if(!on&&i>=0){ f.splice(i,1); ui.toast(t('people.unfollowToast',{name:nm})); }
  store.save();
}
/* relationship chip for cards/profile — derived from real local state only */
function relBadge(p){
  if(isMutual(p.id)) return '<span class="badge b-verified">🤝 '+t('people.mutual')+'</span>';
  if(isFollower(p.id)) return '<span class="badge">'+t('people.followsYou')+'</span>';
  return '';
}
/* ---- the privacy core: only discoverable, unblocked, same-community,
      non-self people are ever listed ---- */
function visiblePeople(){
  const c=myCampus(), me=String(store.myName()||'').toLowerCase();
  const base=(store.state.people||[]).filter(p=>
    p&&p.discoverable!==false &&
    !ui.isBlocked(p.name) &&
    String(p.name||'').toLowerCase()!==me
  );
  const mine=base.filter(p=>String(p.campus||'')===c);
  if(mine.length) return mine;
  /* Demo fallback: nobody at this campus yet — show labeled samples so the
     surface is explorable. Real (non-sample) profiles always stay
     campus-strict; the "Sample profiles" note above the list says why. */
  const samples=base.filter(p=>p.sample);
  return samples.length?samples:mine;
}
function allSkills(list){
  const m=new Map();
  for(const p of list) for(const s of (p.skills||[])){
    const k=String(s).toLowerCase();
    if(!m.has(k)) m.set(k,s);
  }
  return [...m.values()].sort((a,b)=>String(a).localeCompare(String(b)));
}
function filteredPeople(){
  let list=visiblePeople();
  if(fMutual) list=list.filter(p=>(p.mutualGroups||[]).length>0);
  if(fFollowing) list=list.filter(p=>isFollowing(p.id));
  if(fSkill) list=list.filter(p=>(p.skills||[]).some(s=>String(s).toLowerCase()===fSkill));
  if(qName) list=list.filter(p=>String(p.name||'').toLowerCase().indexOf(qName)>=0);
  return list;
}
function contactExists(p){
  const nm=String(p.name||'').toLowerCase(), ph=String(p.phone||'').trim();
  return store.state.contacts.some(c=>{
    const cn=String(c.name||'').trim().toLowerCase();
    if(ph&&String(c.phone||'').trim()===ph) return true;
    return cn&&cn===nm;
  });
}
function skillLabel(p){ return (p.skills||[]).slice(0,3).map(s=>'<span class="ppl-skill">'+ui.esc(s)+'</span>').join('')
  +((p.skills||[]).length>3?'<span class="ppl-skill ppl-more">+'+((p.skills||[]).length-3)+'</span>':''); }

/* ================= person card ================= */
function cardHTML(p){
  const skills=skillLabel(p);
  const mutual=(p.mutualGroups||[]);
  return '<article class="card ppl-card">'
    +'<div class="row" style="align-items:flex-start">'
    +'<div class="ppl-avatar" style="--ppl-ac:'+avColor(p)+'">'+ui.esc(ui.initials(p.name))+'</div>'
    +'<div class="grow"><div class="row ppl-namerow"><h3>'+ui.esc(p.name)+'</h3>'+ui.sampleBadge(p.sample)+'</div>'
    +'<div class="ppl-badges">'
    +(p.verified?ui.verifiedBadge():'<span class="badge b-unverified">'+t('people.unverified')+'</span>')
    +relBadge(p)
    +'<span class="stars">'+ui.stars(Number(p.stars)||0)+'</span><span class="meta">'+(Number(p.stars)||0).toFixed(1)+'</span>'
    +'</div>'
    +(p.knownFor?'<div class="ppl-known">'+t('people.knownFor')+': '+ui.esc(p.knownFor)+'</div>':'')
    +'</div></div>'
    +(skills?'<div class="ppl-skills">'+skills+'</div>':'')
    +(mutual.length?'<div class="ppl-mutual">'+t('people.shares',{m:ui.esc(mutual.join(' · '))})+'</div>':'')
    +'<div class="ppl-stats"><span>🤝 '+(Number(p.jobsDone)||0)+' '+t('people.jobsDone')+'</span><span>🏷️ '+(Number(p.exchanges)||0)+' '+t('people.exchanges')+'</span></div>'
    +'<div class="ppl-actions">'
    +'<button class="btn btn-sm btn-ghost" data-act="view" data-pid="'+ui.esc(p.id)+'">'+t('people.view')+'</button>'
    +(isFollowing(p.id)
      ?'<button class="btn btn-sm btn-line" data-act="fol" data-pid="'+ui.esc(p.id)+'">✓ '+t('people.following')+'</button>'
      :'<button class="btn btn-sm btn-primary" data-act="fol" data-pid="'+ui.esc(p.id)+'">+ '+t('people.follow')+'</button>')
    +'<button class="btn btn-sm btn-ghost" data-act="msg" data-pid="'+ui.esc(p.id)+'">'+t('people.msg')+'</button>'
    +(contactExists(p)
      ?'<button class="btn btn-sm btn-line" data-act="add" data-pid="'+ui.esc(p.id)+'" disabled>'+t('people.inContacts')+'</button>'
      :'<button class="btn btn-sm btn-line" data-act="add" data-pid="'+ui.esc(p.id)+'">'+t('people.add')+'</button>')
    +'</div></article>';
}

/* ================= empty state ================= */
function emptyHTML(){
  const copy=isStudent()?t('people.emptyStudent'):t('people.emptyNeighbor');
  return '<div class="empty"><div class="big">👥</div><h3>'+t('people.emptyT')+'</h3>'
    +'<p class="sub">'+copy+'</p>'
    +'<button class="btn btn-primary" id="pplInvite">'+t('people.invite')+'</button></div>';
}

/* ================= profile sheet (mirrors the ME profile layout) ================= */
function openProfile(id){
  const p=store.find('people',id);
  if(!p){ ui.toast(t('people.notFound')); return; }
  const col=avColor(p), mutual=(p.mutualGroups||[]), added=contactExists(p);
  let html='<div class="ppl-prof">'
    +'<div class="ppl-hero">'
    +'<div class="ppl-avatar lg" style="--ppl-ac:'+col+'">'+ui.esc(ui.initials(p.name))+'</div>'
    +'<h1 class="ppl-name">'+ui.esc(p.name)+'</h1>'
    +'<div class="ppl-campus">'+ui.campusEmoji(p.campus||myCampus(),p.campusKind)+' '+ui.esc(p.campus||'')+'</div>'
    +'<div class="ppl-badgerow">'+ui.sampleBadge(p.sample)+' '
    +(p.verified?ui.verifiedBadge():'<span class="badge b-unverified">'+t('people.unverified')+'</span>')
    +relBadge(p)
    +(HUB.badges?HUB.badges.forPerson(p):'')
    +' <span class="stars">'+ui.stars(Number(p.stars)||0)+'</span></div>'
    +'<div class="ppl-ribbon" role="list" aria-label="'+t('people.knownFor')+'">'
    +'<span class="ppl-chip">'+(p.verified?ui.verifiedBadge():t('people.unverified'))+'</span>'
    +'<span class="ppl-chip">🤝 '+(Number(p.jobsDone)||0)+' '+t('people.jobsDone')+'</span>'
    +'<span class="ppl-chip">🏷️ '+(Number(p.exchanges)||0)+' '+t('people.exchanges')+'</span>'
    +'<span class="ppl-chip">'+t('people.rating',{n:(Number(p.stars)||0).toFixed(1)})+'</span>'
    +'</div></div>';
  if(p.knownFor) html+='<div class="ppl-sec"><h2>'+t('people.knownFor')+'</h2><div class="card tight"><p style="font-size:14.5px;line-height:1.55">'+ui.esc(p.knownFor)+'</p></div></div>';
  if((p.skills||[]).length) html+='<div class="ppl-sec"><h2>'+t('people.skills')+'</h2><div class="ppl-skills">'+(p.skills||[]).map(s=>'<span class="ppl-skill">'+ui.esc(s)+'</span>').join('')+'</div></div>';
  if(mutual.length) html+='<div class="ppl-sec"><h2>'+t('people.inCommon')+'</h2><div class="card tight"><p style="font-size:14px">'+t('people.shares',{m:'<strong>'+ui.esc(mutual.join(' · '))+'</strong>'})+'</p><p class="hint">'+t('people.plusAll',{c:ui.esc(p.campus||t('people.yourCommunity'))})+'</p></div></div>';
  html+='<div class="demo-note" style="margin-top:14px">'+t('people.sampleNote')+'</div>';
  html+='<div class="ppl-actions ppl-sheet-actions">'
    +'<button class="btn '+(isFollowing(p.id)?'btn-line':'btn-primary')+'" id="ppFol" style="flex:1">'
    +(isFollowing(p.id)?'✓ '+t('people.following'):'+ '+t('people.follow'))+'</button>'
    +'<button class="btn btn-ghost" id="ppMsg" style="flex:1">'+t('people.msg')+'</button>'
    +(added?'<button class="btn btn-line" disabled>'+t('people.inContacts')+'</button>'
           :'<button class="btn btn-line" id="ppAdd">'+t('people.addContact')+'</button>')
    +'</div></div>';
  ui.openSheet(html);
  document.getElementById('ppFol').onclick=()=>{ setFollow(p.id,!isFollowing(p.id)); openProfile(p.id); };
  document.getElementById('ppMsg').onclick=()=>messagePerson(p);
  const add=document.getElementById('ppAdd');
  if(add) add.onclick=()=>{ if(addContact(p)){ openProfile(p.id); } };
  const obb=document.querySelector('.ppl-badgerow .hp-badges');
  /* PraBin: close the profile card FIRST, then open the badge collection —
     never stack the two layers. */
  if(obb&&HUB.badges) obb.onclick=function(){ ui.closeSheet(); requestAnimationFrame(function(){ HUB.badges.openPersonShowcase(p); }); };
}

/* ================= contact + message actions ================= */
function addContact(p){
  if(contactExists(p)){ ui.toast(t('people.already')); return false; }
  store.add('contacts',{name:p.name,phone:p.phone||''});
  ui.toast(t('people.added'));
  return true;
}
/* Mutual-only messaging: a thread with a person opens only when you follow
   each other. Otherwise an honest gate sheet explains the rule. */
function gateSheet(p){
  const following=isFollowing(p.id), fn=firstName(p.name);
  ui.openSheet(
    '<h2>🔒 '+t('people.gateT')+'</h2>'+
    '<p class="sub" style="margin:6px 0 12px">'+t('people.gateD',{name:ui.esc(p.name)})+'</p>'+
    (following
      ?'<div class="demo-note">'+t('people.gateWaiting',{name:ui.esc(fn)})+'</div>'
      :'<button class="btn btn-primary btn-block" id="gateFol">+ '+t('people.follow')+' '+ui.esc(fn)+'</button>')+
    '<button class="btn btn-ghost btn-block" id="gateCancel" style="margin-top:8px">'+t('common.cancel')+'</button>'
  );
  document.getElementById('gateCancel').onclick=ui.closeSheet;
  const gf=document.getElementById('gateFol');
  if(gf) gf.onclick=()=>{ setFollow(p.id,true); gateSheet(p); };
}
/* Opens (or creates) a real local thread with this person — no fake replies,
   no presence. Uses openThread directly rather than openWith so the
   marketplace-only safety checklist isn't mislabeled for a person. */
function messagePerson(p){
  if(!isMutual(p.id)){ gateSheet(p); return; }
  const name=String(p.name||'').trim(), phone=String(p.phone||'').trim();
  if(!name){ ui.toast(t('people.noName')); return; }
  let c=null;
  if(phone) c=store.state.contacts.find(x=>String(x.phone||'').trim()===phone);
  if(!c) c=store.state.contacts.find(x=>String(x.name||'').trim().toLowerCase()===name.toLowerCase());
  if(!c){ store.add('contacts',{name,phone}); c=store.state.contacts[0]; }
  let th=store.state.threads.find(x=>x.contactId===c.id);
  if(!th){ store.add('threads',{contactId:c.id,listingId:null,title:c.name,messages:[],unread:0});
          th=store.state.threads.find(x=>x.contactId===c.id); }
  if(th&&(!th.messages||!th.messages.length)){
    th.messages=[{from:'me',text:t('people.hi',{first:firstName(name),campus:myCampus()}),at:Date.now()}];
    store.save();
  }
  if(HUB.chat&&HUB.chat.openThread) HUB.chat.openThread(th.id);
}

/* ================= friends: phone-contact sync + invites =================
   FRIENDS (2026-09-22). store.state.friends is a browser-local list of
   {name, phone, at}. Sync uses the Contact Picker API where the browser
   supports it (unavailable in iOS Safari — manual add is the iPhone path);
   permission denial and unsupported browsers open the manual sheet instead.
   The Onaro badge is an HONEST local heuristic: a contact counts as "on
   Onaro" when the name matches someone this device already knows (a person
   record, a household member, a community-group member/admin, or the local
   profile name). It means "known here", NOT verified online — name
   collisions are possible and real cross-device verification needs a
   backend identity service. */
let fMode='people'; /* 'people' | 'friends' */
function frAll(){
  if(!Array.isArray(store.state.friends)) store.state.friends=[];
  return store.state.friends;
}
function frIsAppUser(c){
  const nm=String(c.name||'').trim().toLowerCase();
  if(!nm) return false;
  const known=new Set();
  for(const p of (store.state.people||[])) if(p&&p.name) known.add(String(p.name).trim().toLowerCase());
  for(const h of (store.state.households||[])) for(const m of (h.members||[])) known.add(String(m).trim().toLowerCase());
  for(const g of (store.state.cgroups||[])){
    for(const m of (g.members||[])) known.add(String(m).trim().toLowerCase());
    if(g.admin) known.add(String(g.admin).trim().toLowerCase());
  }
  known.add(String(store.myName()||'').trim().toLowerCase());
  return known.has(nm);
}
function frFiltered(){
  const q=String(qName||'').trim().toLowerCase();
  return frAll().filter(c=>!q||String(c.name||'').toLowerCase().indexOf(q)>=0);
}
function frRowHTML(c,idx){
  const appUser=frIsAppUser(c);
  return '<div class="fr-row">'
    +'<div class="fr-avatar">'+ui.esc(ui.initials(c.name))+'</div>'
    +'<div class="grow" style="min-width:0"><h3 style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+ui.esc(c.name)+'</h3>'
    +(c.phone?'<div class="meta">'+ui.esc(c.phone)+'</div>':'')+'</div>'
    +(appUser
      ?'<span class="fr-onaro" title="'+ui.esc(t('friends.onApp'))+'">🪐 '+ui.esc(t('friends.onApp'))+'</span>'
      :'<button class="btn btn-sm btn-primary" data-fract="invite" data-fri="'+idx+'">'+t('friends.invite')+'</button>')
    +'<button class="linklike" data-fract="remove" data-fri="'+idx+'" aria-label="'+ui.esc(t('friends.remove'))+'">✕</button>'
    +'</div>';
}
function friendsListHTML(){
  const all=frAll(), list=frFiltered();
  let html='<div class="row between" style="margin-bottom:4px"><h2 style="margin:0">👥 '+ui.esc(t('friends.title'))+'</h2><span class="meta">'+list.length+'</span></div>';
  if(!all.length){
    html+='<div class="empty"><div class="big">📇</div><p>'+t('friends.none')+'</p><p class="sub">'+t('friends.noneSub')+'</p>'
      +'<div class="row" style="gap:8px;justify-content:center;margin-top:8px">'
      +'<button class="btn btn-primary btn-sm" id="frSync2">'+t('friends.sync')+'</button>'
      +'<button class="btn btn-line btn-sm" id="frMan2">'+t('friends.manual')+'</button></div></div>';
  }else if(!list.length){
    html+='<div class="empty"><div class="big">🔍</div><p>'+t('people.emptyT')+'</p></div>';
  }else{
    html+=list.map(function(c){ return frRowHTML(c,all.indexOf(c)); }).join('');
  }
  return html;
}
function frDup(name,phone){
  const nm=String(name||'').trim().toLowerCase(), ph=String(phone||'').trim();
  return frAll().some(function(x){
    if(ph&&String(x.phone||'').trim()===ph) return true;
    return String(x.name||'').trim().toLowerCase()===nm;
  });
}
function syncContacts(el){
  const api=(navigator.contacts&&navigator.contacts.select)?navigator.contacts:null;
  if(!api){ ui.toast(t('friends.unsupported')); manualSheet(el); return; }
  api.select(['name','tel'],{multiple:true}).then(function(picked){
    if(!picked||!picked.length){ ui.toast(t('friends.none')); return; }
    let added=0;
    for(const c of picked){
      const name=String((c.name&&c.name[0])||'').trim();
      if(!name) continue;
      const phone=String((c.tel&&c.tel[0])||'').trim();
      if(!frDup(name,phone)){ frAll().push({name:name,phone:phone,at:Date.now()}); added++; }
    }
    store.save(); ui.toast(t('friends.synced',{n:added})); paintList(el);
  },function(err){
    /* AbortError = user cancelled the picker: stay silent.
       NotAllowedError = permission denied: offer the manual sheet. */
    if(err&&err.name==='NotAllowedError'){ ui.toast(t('friends.denied')); manualSheet(el); }
  });
}
function manualSheet(el){
  ui.openSheet(
    '<h2>'+t('friends.manualT')+'</h2>'
    +'<div class="field"><label>'+t('friends.name')+'</label><input class="input" id="frName" maxlength="60" placeholder="'+ui.esc(t('friends.name'))+'"></div>'
    +'<div class="field"><label>'+t('friends.phone')+'</label><input class="input" id="frPhone" type="tel" inputmode="tel" placeholder="+1 555-000-0000"></div>'
    +'<button class="btn btn-primary btn-block" id="frSave">'+t('friends.add')+'</button>'
  );
  document.getElementById('frSave').onclick=()=>{
    const nm=document.getElementById('frName').value.trim();
    const ph=document.getElementById('frPhone').value.trim();
    if(!nm){ ui.toast(t('friends.needName')); return; }
    if(frDup(nm,ph)){ ui.toast(t('friends.dup')); return; }
    frAll().push({name:nm,phone:ph,at:Date.now()});
    store.save(); ui.closeSheet(); ui.toast(t('friends.added',{name:nm}));
    if(el) paintList(el);
  };
}
function frCopyText(str){
  const done=()=>ui.toast(t('friends.shared'));
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(str).then(done,()=>fallbackCopy(str,done));
  }else fallbackCopy(str,done);
}
function fallbackCopy(str,done){
  try{
    const ta=document.createElement('textarea');
    ta.value=str; ta.style.position='fixed'; ta.style.opacity='0';
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); done();
  }catch(e){ ui.toast(str); }
}
function frInvite(c){
  const base=(location.protocol.indexOf('http')===0&&location.origin&&location.origin!=='null')
    ?location.origin : 'https://hub-preview.surge.sh';
  const link=base+'/#invite';
  const text=t('friends.inviteText',{link:link});
  const done=()=>ui.toast(t('friends.shared'));
  if(navigator.share){
    try{
      navigator.share({title:t('friends.inviteTitle'),text:text,url:link}).then(done,function(err){
        if(err&&err.name!=='AbortError') frCopyText(link);
      });
    }catch(e){ frCopyText(link); }
  }else frCopyText(link);
}

/* ================= the surface ================= */
function segHTML(){
  return '<div class="seg"><button data-sub="clubs">'+t('cg.seg.groups')+'</button><button data-sub="households">'+t('groups.seg.hh')+'</button><button data-sub="campus">'+t('groups.seg.campus')+'</button><button class="on">'+t('groups.seg.people')+'</button></div>';
}
function chipsHTML(skills){
  return '<button class="chip'+((!fSkill&&!fMutual&&!fFollowing)?' on':'')+'" data-f="all">'+t('people.filterAll')+'</button>'
    +'<button class="chip'+(fFollowing?' on':'')+'" data-f="following">'+t('people.filterFollowing')+'</button>'
    +skills.map(s=>'<button class="chip'+(fSkill===String(s).toLowerCase()?' on':'')+'" data-f="skill" data-v="'+ui.esc(s)+'">'+ui.esc(s)+'</button>').join('')
    +'<button class="chip'+(fMutual?' on':'')+'" data-f="mutual">'+t('people.filterMutual')+'</button>';
}
function listHTML(){
  if(fMode==='friends') return friendsListHTML();
  const list=filteredPeople();
  return '<div class="row between" style="margin-bottom:4px"><h2 style="margin:0">👤 '+ui.esc(peopleTitle())+'</h2><span class="meta">'+t('people.shown',{n:list.length})+'</span></div>'
    +(list.length? list.map(cardHTML).join('') : emptyHTML());
}
/* repaints chips + list only, so the search input never loses focus */
function paintList(el){
  const vis=visiblePeople(), skills=allSkills(vis);
  const ch=el.querySelector('#pplChips'), ls=el.querySelector('#pplList');
  if(ch){ ch.innerHTML=chipsHTML(skills); ch.style.display=(fMode==='friends'?'none':''); }
  if(ls) ls.innerHTML=listHTML();
  bindChips(el); bindList(el);
}
function bindChips(el){
  el.querySelectorAll('#pplChips .chip').forEach(ch=>{
    ch.onclick=()=>{
      const f=ch.dataset.f;
      if(f==='all'){ fSkill=null; fMutual=false; fFollowing=false; }
      else if(f==='mutual'){ fMutual=!fMutual; if(fMutual){ fSkill=null; fFollowing=false; } }
      else if(f==='following'){ fFollowing=!fFollowing; if(fFollowing){ fSkill=null; fMutual=false; } }
      else if(f==='skill'){ const v=String(ch.dataset.v||'').toLowerCase(); fSkill=(fSkill===v?null:v); if(fSkill){ fMutual=false; fFollowing=false; } }
      paintList(el);
    };
  });
}
function bindList(el){
  const inv=el.querySelector('#pplInvite');
  if(inv) inv.onclick=()=>ui.toast(isStudent()?t('people.shareStudent'):t('people.shareNeighbor'));
  /* friends mode switch + contact sync */
  const fb=el.querySelector('#pplFriendsBtn');
  if(fb) fb.onclick=()=>{ fMode=(fMode==='friends'?'people':'friends'); renderSurface(el); };
  const sb=el.querySelector('#pplSyncBtn');
  if(sb) sb.onclick=()=>{ syncContacts(el); };
  const s2=el.querySelector('#frSync2');
  if(s2) s2.onclick=()=>{ syncContacts(el); };
  const m2=el.querySelector('#frMan2');
  if(m2) m2.onclick=()=>{ manualSheet(el); };
  el.querySelectorAll('#pplList [data-fract]').forEach(b=>{
    b.onclick=()=>{
      const c=frAll()[Number(b.dataset.fri)];
      if(!c) return;
      if(b.dataset.fract==='invite') frInvite(c);
      else if(b.dataset.fract==='remove'&&confirm(t('friends.removeC',{name:c.name}))){
        const i=frAll().indexOf(c);
        if(i>=0) frAll().splice(i,1);
        store.save(); ui.toast(t('friends.removed',{name:c.name})); paintList(el);
      }
    };
  });
  el.querySelectorAll('#pplList [data-act]').forEach(b=>{
    b.onclick=()=>{
      const p=store.find('people',b.dataset.pid);
      if(!p) return;
      const a=b.dataset.act;
      if(a==='view') openProfile(p.id);
      else if(a==='msg') messagePerson(p);
      else if(a==='fol'){ setFollow(p.id,!isFollowing(p.id)); paintList(el); }
      else if(a==='add'){ if(addContact(p)) paintList(el); }
    };
  });
}
function renderSurface(el){
  const vis=visiblePeople(), skills=allSkills(vis);
  el.innerHTML='<h1 class="greet">'+t('groups.title')+'</h1>'
    +'<p class="sub" style="margin:4px 0 12px">'+t('people.findAt',{where:isStudent()?t('people.atSchool'):t('people.inCommunity')})+'</p>'
    +segHTML()
    +'<div class="demo-note">'+t('people.demoNote')+'</div>'
    +'<div class="field" style="margin:10px 0 4px"><input class="input" id="pplSearch" placeholder="'+ui.esc(t(fMode==='friends'?'friends.searchPh':'people.searchPh'))+'" autocomplete="off" value="'+ui.esc(qName)+'"></div>'
    +'<div class="row" style="gap:8px;margin:0 0 8px">'
    +'<button class="btn btn-line btn-sm" id="pplFriendsBtn" style="flex:1">'+(fMode==='friends'?'← '+t('groups.seg.people'):'👥 '+ui.esc(t('friends.title'))+' ('+frAll().length+')')+'</button>'
    +'<button class="btn btn-ghost btn-sm" id="pplSyncBtn">'+ui.esc(t('friends.sync'))+'</button></div>'
    +'<div class="chips" id="pplChips"'+(fMode==='friends'?' style="display:none"':'')+'>'+chipsHTML(skills)+'</div>'
    +'<div id="pplList">'+listHTML()+'</div>';

  el.querySelectorAll('[data-sub]').forEach(b=>{ b.onclick=()=>HUB.views.groups.setSub(b.dataset.sub); });
  const si=el.querySelector('#pplSearch');
  if(si) si.oninput=()=>{ qName=si.value.trim().toLowerCase(); paintList(el); };
  bindChips(el); bindList(el);
}

/* ---- Home "People in {campus}" head row (2026-09-22, PraBin's ask) ----
   Stories-style circular head row on Home, below the Time Capsule pill.
   Demo profiles live in store.state.people with hpSeed:true and
   discoverable:false (so the Groups>People surface never lists them).
   Privacy core: ONLY profiles with public===true ever render. Private
   people are never shown — no exceptions. The user's own head appears
   only when they flip "Show my profile publicly" in ME > Edit profile
   (default OFF). Real cross-device discovery needs a backend; everything
   here is browser-local demo data (the row carries a demo-note caption). */
function hpSeeds(){
  /* v2 (2026-09-22, PraBin's ask): followers counts + one created group per
     public profile. Groups are conceptual ("Priya's Study Circle"); there is
     no backend, so the device user reviews join requests locally via the
     existing community-group machinery (see hpGroupEnsure). */
  const S=(name,major,year,bio,interests,pub,color,followers,group)=>({
    id:'hp'+Date.now().toString(36)+Math.random().toString(36).slice(2,6),
    name:name,campus:'',major:major,year:year,bio:bio,interests:interests,
    avatarColor:color,public:!!pub,followers:followers||0,group:group||null,
    discoverable:false,sample:true,hpSeed:true
  });
  const G=(emoji,name,desc,members)=>({emoji:emoji,name:name,desc:desc,members:members});
  return [
    S('Priya Nair','Computer Science','Senior','Building a study-buddy app for finals week. Always down for hackathons and boba runs.',['Coding','Hackathons','Boba'],true,1,214,
      G('📚',"Priya's Study Circle",'Finals-week study sessions, shared notes, and accountability buddies.',['Priya Nair','Emma Wilson','Omar Farouk','Aisha Bello'])),
    S('Diego Morales','Graphic Design','Junior','Poster artist for campus events. Looking for photographers to collab with this semester.',['Design','Photography','Posters'],true,2,89,
      G('🎨',"Diego's Design Crew",'Poster collabs, photo walks, and portfolio feedback nights.',['Diego Morales','Sofia Rossi','Grace Liu'])),
    S('Aisha Bello','Biology · Pre-Med','Sophomore','Future doctor. Runs a weekend tutoring circle for intro chem — all welcome.',['Tutoring','Medicine','Running'],true,0,156,
      G('🧪',"Aisha's Chem Tutoring",'Weekend intro-chem tutoring circle — all welcome, no question too small.',['Aisha Bello','Emma Wilson','Raj Sharma'])),
    S('Tom Becker','Mechanical Engineering','Senior','Capstone is a solar RC car. The workshop is open most evenings if you want to tinker.',['Robotics','3D printing','Cycling'],true,4,73,
      G('⚙️',"Tom's Workshop Nights",'Tinker evenings: 3D printing, RC builds, and capstone chaos.',['Tom Becker','Omar Farouk'])),
    S('Lena Fischer','Psychology','Junior','Research assistant in the sleep lab. Quiet coffee shop regular.',['Research','Coffee','Journaling'],false,3),
    S('Raj Sharma','Business Administration','Freshman','New here! Trying every food truck on campus and looking for intramural teammates.',['Startups','Food trucks','Soccer'],true,5,41,
      G('🌮',"Raj's Food Truck Tour",'Trying every food truck on campus, one lunch at a time.',['Raj Sharma','Grace Liu','Diego Morales','Sofia Rossi'])),
    S('Sofia Rossi','Architecture','Senior','Studio rat. Sketching the old library before they renovate it — join me sometime.',['Sketching','Models','Museums'],true,6,98,
      G('✏️',"Sofia's Sketch Club",'Urban sketching meetups around campus and the old library.',['Sofia Rossi','Grace Liu'])),
    S('Kenji Tanaka','Music Production','Junior','Bedroom producer. Always hunting for vocalists for my next track.',['Beats','Synths','Vinyl'],false,7),
    S('Emma Wilson','Nursing','Sophomore','Clinical rotations start next month. Coffee-fueled and always up for study groups.',['Study groups','Coffee','Hiking'],true,0,132,
      G('☕',"Emma's Study Groups",'Coffee-fueled study sessions before clinical rotations.',['Emma Wilson','Priya Nair','Aisha Bello'])),
    S('Omar Farouk','Data Science','Graduate','TA for stats. Happy to look over resumes or debug your Python at the library.',['Python','Stats','Chess'],true,2,187,
      G('📊',"Omar's Stats Help Desk",'Stats homework help and Python debugging at the library.',['Omar Farouk','Tom Becker','Raj Sharma'])),
    S('Grace Liu','Fine Arts','Freshman','Painting murals in my dorm (RA approved, promise). Looking for gallery buddies.',['Painting','Galleries','Film'],true,1,56,
      G('🖼️',"Grace's Gallery Buddies",'Gallery hops, film nights, and mural-painting weekends.',['Grace Liu','Sofia Rossi','Diego Morales'])),
    S('Chris Novak','Kinesiology','Junior','Training for a spring marathon. Early-morning track crew welcomes all paces.',['Running','Nutrition','Swimming'],false,5)
  ];
}
/* ---- demo groups for the public seeds ----
   Each public demo profile gets one created group, seeded as a REAL
   community-group record (store.state.cgroups) with sample:true so the
   existing sample-purge (store.clearSamples) removes it consistently.
   discoverable:false on the person keeps Groups>People clean; these groups
   live only in the glass sheet + the normal Groups surfaces, sample-badged
   like every other seed.
   mine:true + live:true activate the EXISTING request machinery untouched:
   the join request lands in g.requests, the existing Notifications row
   (g.mine && g.live) picks it up, and the existing approve/decline panel
   on the group page handles it. Demo honesty: there is no backend, so the
   device user reviews the request locally — the sheet copy says exactly
   that. admin keeps the demo person's name for the copy. */
function hpGroupEnsure(){
  const st=store.state;
  if(!Array.isArray(st.cgroups)) return;
  if(st.cgroups.some(function(g){ return g&&g.hpGroup; })) return; /* seeded once */
  let dirty=false;
  for(const p of (st.people||[])){
    if(!p||!p.hpSeed||p.public!==true||!p.group) continue;
    st.cgroups.push({
      id:'hpg-'+p.id, name:p.group.name, desc:p.group.desc, emoji:p.group.emoji||'👥', photo:'',
      admin:p.name, mine:true, members:(p.group.members||[]).slice(), requests:[],
      live:true, sample:true, hpGroup:true, createdAt:Date.now()
    });
    dirty=true;
  }
  if(dirty) store.save();
}
function hpGroupFor(p){
  if(!p||p.self) return null;
  return (store.state.cgroups||[]).find(function(g){ return g&&g.hpGroup&&g.id==='hpg-'+p.id; })||null;
}
function hpEnsure(){
  const st=store.state;
  if(!Array.isArray(st.people)) return;
  if(!st.people.some(p=>p&&p.hpSeed)){
    const c=myCampus()||'Riverside State';
    for(const p of hpSeeds()){ p.campus=c; st.people.push(p); }
    store.save();
  }else{
    /* v2 backfill: first-gen seeds (already on devices, e.g. PraBin's)
       get followers + group fields, matched by name. Follow state is kept
       because person ids are never regenerated. */
    const fresh={};
    for(const p of hpSeeds()) fresh[p.name]=p;
    let dirty=false;
    for(const p of st.people){
      if(!p||!p.hpSeed) continue;
      const f=fresh[p.name];
      if(f&&p.followers===undefined){ p.followers=f.followers; p.group=f.group||null; dirty=true; }
    }
    if(dirty) store.save();
  }
  hpGroupEnsure();
}
hpEnsure();
/* campus-sync + privacy filter: public seeds only, seed order.
   (Distances were removed from this surface on PraBin's order — no mile
   is rendered anywhere here; distanceMi no longer exists on hp seeds.) */
function hpList(){
  const c=myCampus(), out=[];
  let dirty=false;
  for(const p of (store.state.people||[])){
    if(!p||!p.hpSeed) continue;
    if(c&&p.campus!==c){ p.campus=c; dirty=true; } /* title stays honest */
    if(p.public===true) out.push(p);
  }
  if(dirty) store.save();
  return out;
}
function hpSelf(){
  const pr=store.state.profile;
  if(!pr||!pr.publicProfile) return null;
  return {id:'hp-self',name:pr.name||t('people.there'),campus:myCampus(),
    major:pr.major||'',year:pr.year||'',bio:pr.bio||'',
    interests:(pr.skills||[]).slice(),distanceMi:0,avatarColor:(pr.avatarColor||0),
    public:true,self:true,photo:pr.photo||null};
}
function hpHeadHTML(p,i,dup){
  const col=PPL_COLORS[Math.abs(Number(p.avatarColor)||0)%PPL_COLORS.length];
  const inner=p.photo
    ?'<img class="avimg" src="'+ui.esc(p.photo)+'" alt="">'
    :ui.esc(ui.initials(p.name));
  /* free-floating drift: each avatar sits in a .hp-drift wrapper that wanders it
     along a multi-waypoint path (hpDriftA/B/C) — real bubble movement, not a
     fixed bob. --dpd varies the drift period 4.2–6.6s; --dd is a NEGATIVE
     delay so every bubble is already mid-drift at load. Path + period + phase
     all differ per index, so neighbors never move in sync. */
  const ix=(typeof i==='number')?i:0;
  const ph='-'+((ix*0.55)%3.6).toFixed(2)+'s';
  const pd=(3.1+(ix%3)*0.5).toFixed(2)+'s';
  const dn='hpDrift'+'ABC'[ix%3];
  const dpdv=4.2+(ix%4)*0.8, dpd=dpdv.toFixed(2)+'s';
  const pdl='-'+((ix*1.37)%dpdv).toFixed(2)+'s';
  /* dup: the marquee's second (aria-hidden) copy — identical markup so the
     -50% loop point is seamless; tabindex -1 keeps it out of the tab order
     while taps still open the person's card. */
  const dupAttr=dup?' aria-hidden="true" tabindex="-1"':'';
  return '<button class="hp-head" data-hp="'+ui.esc(p.id)+'" style="--hd:'+ph+';--hpd:'+pd+'" aria-label="'+ui.esc(p.name)+'"'+dupAttr+'>'
    +'<span class="hp-drift" style="--dname:'+dn+';--dpd:'+dpd+';--dd:'+pdl+'"><span class="hp-av" style="--hp-ac:'+col+'">'+inner
    +(p.self?'<span class="hp-you">'+ui.esc(t('home.pplYou'))+'</span>':'')
    +'</span></span>'
    +'<span class="hp-name">'+ui.esc(String(p.name||'').split(/\s+/)[0])+'</span></button>';
}
function homeRowHTML(){
  hpEnsure();
  const list=hpList(), self=hpSelf();
  const heads=(self?[self]:[]).concat(list);
  if(!heads.length) return '';
  const c=myCampus();
  const title=c?t('people.titleIn',{c:c}):t('home.pplNear');
  /* infinite forward marquee: two identical head sets; the track translates
     0 -> -50% on a slow seamless loop so every person glides into view on
     their own. The second set is aria-hidden (tabindex -1) but taps still
     open that person's card. */
  const setA=heads.map(function(p,ix){return hpHeadHTML(p,ix,false)}).join('');
  const setB=heads.map(function(p,ix){return hpHeadHTML(p,ix,true)}).join('');
  return '<section class="hpsec hsec" id="homePplSec" aria-label="'+ui.esc(title)+'">'
    +'<div class="hsec-hd"><h2>'+ui.esc(title)+'</h2>'
    +'<span class="hsec-act" style="cursor:default">'+ui.esc(t('home.pplCount',{n:heads.length}))+'</span></div>'
    +'<div class="hp-row"><div class="hp-marquee" role="list">'+setA+setB+'</div></div>'
    +'<div class="demo-note hnote" style="margin-bottom:0">'+ui.esc(t('home.pplDemo'))+'</div>'
    +'</section>';
}
function bindHomeRow(scope){
  const sec=(scope||document).querySelector('#homePplSec');
  if(!sec) return;
  sec.querySelectorAll('[data-hp]').forEach(function(b){
    b.onclick=function(){ openGlass(b.dataset.hp); };
  });
  /* pause the auto-glide while the user's finger is on the row, resume ~2s
     after they lift it — the marquee never fights a manual swipe. */
  const trk=sec.querySelector('.hp-marquee');
  if(trk&&!trk.dataset.hpm){
    trk.dataset.hpm='1';
    let resume=null;
    const pause=function(){ trk.classList.add('hp-paused'); if(resume){clearTimeout(resume);resume=null;} };
    const go=function(){ if(resume) clearTimeout(resume); resume=setTimeout(function(){ trk.classList.remove('hp-paused'); resume=null; },2000); };
    trk.addEventListener('touchstart',pause,{passive:true});
    trk.addEventListener('touchend',go,{passive:true});
    trk.addEventListener('touchcancel',go,{passive:true});
    trk.addEventListener('pointerdown',pause);
    trk.addEventListener('pointerup',go);
    trk.addEventListener('pointercancel',go);
  }
}

/* ---- clear-glass 3D profile sheet ----
   Dedicated fixed overlay (same pattern as .incallroot): centered in the
   480px column, scrim tap / ✕ / Escape to close. The global Escape handler
   in app.js defers while .hpglass is open. */
let hpGlassMounted=false;
function hpMount(){
  if(hpGlassMounted) return; hpGlassMounted=true;
  const d=document.createElement('div');
  d.className='hpglass'; d.id='hpGlass'; d.hidden=true;
  d.innerHTML='<div class="hpglass-card" role="dialog" aria-modal="true" id="hpGlassCard"></div>';
  document.body.appendChild(d);
  d.addEventListener('click',function(e){ if(e.target===d) hpClose(); });
  document.addEventListener('keydown',function(e){
    const g=document.getElementById('hpGlass');
    if(e.key==='Escape'&&g&&!g.hidden) hpClose();
  });
}
function hpClose(){ const g=document.getElementById('hpGlass'); if(g) g.hidden=true; }
/* ---- the demo person's created group, inside the glass sheet ----
   Group name + member count + Request-to-join. The request uses the REAL
   community-group path (identical to the club page's cgReq handler):
   push {name, at} into g.requests, save, toast. The existing Notifications
   row then picks it up and the existing approve/decline panel on the group
   page handles it. States shown honestly: member / request pending / join. */
function hpGroupHTML(p){
  const g=hpGroupFor(p);
  if(!g) return '';
  const meL=String(store.myName()||'').toLowerCase();
  const members=g.members||[];
  const isMem=members.some(function(m){ return String(m||'').toLowerCase()===meL; });
  const reqSent=(g.requests||[]).some(function(r){ return String(r.name||'').toLowerCase()===meL; });
  const cta=isMem
    ?'<button class="btn btn-line btn-block" disabled>✓ '+ui.esc(t('cg.alreadyMember'))+'</button>'
    :reqSent
    ?'<button class="btn btn-line btn-block" disabled>'+ui.esc(t('cg.requested'))+'</button>'
    :'<button class="btn btn-primary btn-block" id="hpReqJoin">🙋 '+ui.esc(t('hp.joinGroup'))+'</button>';
  return '<div class="hpglass-sec"><h3>'+ui.esc(t('hp.groups'))+'</h3>'
    +'<div class="card tight" style="text-align:left">'
    +'<div class="row between" style="align-items:flex-start;gap:8px"><div class="grow" style="min-width:0">'
    +'<div style="font-weight:800;font-size:15.5px;line-height:1.35">'+ui.esc(g.emoji||'👥')+' '+ui.esc(g.name)+'</div>'
    +'<div class="meta" style="margin-top:3px">👥 '+ui.esc(t('cg.members',{n:members.length}))+'</div>'
    +(g.desc?'<div class="sub" style="margin-top:4px;line-height:1.5">'+ui.esc(g.desc)+'</div>':'')
    +'</div>'+ui.sampleBadge(g.sample)+'</div>'
    +'<div style="margin-top:10px">'+cta+'</div>'
    +'<p class="hint" style="margin:8px 0 0">'+ui.esc(t('hp.groupDemo',{name:firstName(p.name)}))+'</p>'
    +'</div></div>';
}
/* the real request path — mirrors the club page's cgReq handler exactly */
function hpRequestJoin(p){
  const g=hpGroupFor(p);
  if(!g) return;
  const me=store.myName(), meL=String(me||'').toLowerCase();
  g.requests=g.requests||[];
  if(!g.requests.some(function(r){ return String(r.name||'').toLowerCase()===meL; }))
    g.requests.push({name:me,at:Date.now()});
  store.save();
  ui.toast(t('cg.reqSent'));
  openGlass(p.id); /* re-render: the button becomes "Request sent ✓" */
}
function hpFollowCount(p){
  return (Number(p.followers)||0)+(isFollowing(p.id)?1:0);
}
function openGlass(id){
  hpMount();
  const p=id==='hp-self'?hpSelf():store.find('people',id);
  if(!p) return;
  const col=PPL_COLORS[Math.abs(Number(p.avatarColor)||0)%PPL_COLORS.length];
  const inner=p.photo
    ?'<img class="avimg" src="'+ui.esc(p.photo)+'" alt="">'
    :ui.esc(ui.initials(p.name));
  const meta=[p.year,p.campus].filter(Boolean).join(' · ');
  const chips=(p.interests||[]).map(s=>'<span class="ppl-skill">'+ui.esc(s)+'</span>').join('');
  const self=!!p.self, fol=isFollowing(p.id);
  document.getElementById('hpGlassCard').innerHTML=
    '<button class="hpglass-x" id="hpGlassX" aria-label="'+ui.esc(t('common.close'))+'">✕</button>'
    +'<div class="hpglass-av" style="--hp-ac:'+col+'">'+inner+'</div>'
    +'<div class="hpglass-namerow"><h2 class="hpglass-name">'+ui.esc(p.name)+'</h2>'
    +(HUB.badges?HUB.badges.forPerson(p):'')+'</div>'
    +(p.major?'<div class="hpglass-major">🎓 '+ui.esc(p.major)+'</div>':'')
    +(meta?'<div class="hpglass-meta">'+ui.esc(meta)+'</div>':'')
    +(self?'':'<div class="hpglass-folks">'+ui.esc(t('hp.followers',{n:hpFollowCount(p)}))+'</div>'
      +'<button class="btn '+(fol?'btn-line':'btn-primary')+' btn-block" id="hpFolBtn" style="margin-top:10px">'
      +(fol?'✓ '+t('people.following'):'+ '+t('people.follow'))+'</button>')
    +(p.bio?'<p class="hpglass-bio" style="margin-top:12px">'+ui.esc(p.bio)+'</p>':'')
    +(chips?'<div class="hpglass-sec"><h3>'+ui.esc(t('hp.interests'))+'</h3><div class="hpglass-chips">'+chips+'</div></div>':'')
    +(self?'':hpGroupHTML(p))
    +(self?'':'<div class="demo-note" style="margin:16px 0 0">'+ui.esc(t('hp.demoProf'))+'</div>');
  document.getElementById('hpGlass').hidden=false;
  const hbb=document.querySelector('#hpGlassCard .hp-badges');
  /* PraBin: close the glass card FIRST, then open the badge collection on the
     next frame — never stack the two layers. */
  if(hbb&&HUB.badges) hbb.onclick=function(){ hpClose(); requestAnimationFrame(function(){ HUB.badges.openPersonShowcase(p); }); };
  const x=document.getElementById('hpGlassX');
  if(x) x.onclick=hpClose;
  const fb=document.getElementById('hpFolBtn');
  if(fb) fb.onclick=function(){ setFollow(p.id,!isFollowing(p.id)); openGlass(p.id); };
  const rq=document.getElementById('hpReqJoin');
  if(rq) rq.onclick=function(){ hpRequestJoin(p); };
}

HUB.people={renderSurface,openProfile,addContact,messagePerson,visiblePeople,
  isFollowing,isFollower,isMutual,followPerson:setFollow,
  homeRowHTML,bindHomeRow,openGlass,closeGlass:hpClose,hpList,hpGroupFor,hpGroupEnsure};
})();
