/* HUB PEOPLE (Workstream D): same-institution / same-community people discovery.
   Students see "People at [Campus]"; community members see "People in [Community]".
   Renders as the "People" segment inside the Groups tab (HUB.views.groups delegates
   here when its sub is 'people'). Browser-local only; every sample person wears a
   Sample badge; the surface carries a demo note. No presence dots, no fake online
   state — nothing here claims a real person is online or reachable. */
(function(){
'use strict';
const {store,ui}=HUB;

/* clay avatar palette — same brand-safe set as ME, no purple */
const PPL_COLORS=['#1F7A4D','#2563EB','#C22E1F','#0F766E','#B45309','#C2410C','#1D4ED8','#131A00'];

let fSkill=null;    // active skill filter (lowercased), null = all
let fMutual=false;  // "shared households" filter

function myCampus(){ return store.state.profile.campus||''; }
function isStudent(){ return store.state.profile.audience==='student'; }
function peopleTitle(){ return isStudent() ? 'People at '+myCampus() : 'People in '+myCampus(); }
function firstName(n){ return String(n||'').trim().split(/\s+/)[0]||'there'; }
function avColor(p){ return PPL_COLORS[Math.abs(Number(p.avatarColor)||0)%PPL_COLORS.length]; }

/* ---- the privacy core: only discoverable, unblocked, same-community,
      non-self people are ever listed ---- */
function visiblePeople(){
  const c=myCampus(), me=String(store.myName()||'').toLowerCase();
  return (store.state.people||[]).filter(p=>
    p&&p.discoverable!==false &&
    String(p.campus||'')===c &&
    !ui.isBlocked(p.name) &&
    String(p.name||'').toLowerCase()!==me
  );
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
  if(fSkill) list=list.filter(p=>(p.skills||[]).some(s=>String(s).toLowerCase()===fSkill));
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
    +(p.verified?'<span class="badge b-verified">✓ Verified</span>':'<span class="badge b-unverified">Unverified</span>')
    +'<span class="stars">'+ui.stars(Number(p.stars)||0)+'</span><span class="meta">'+(Number(p.stars)||0).toFixed(1)+'</span>'
    +'</div>'
    +(p.knownFor?'<div class="ppl-known">💡 '+ui.esc(p.knownFor)+'</div>':'')
    +'</div></div>'
    +(skills?'<div class="ppl-skills">'+skills+'</div>':'')
    +(mutual.length?'<div class="ppl-mutual">🏠 Shares '+ui.esc(mutual.join(' · '))+' with you</div>':'')
    +'<div class="ppl-stats"><span>🤝 '+(Number(p.jobsDone)||0)+' jobs done</span><span>🏷️ '+(Number(p.exchanges)||0)+' exchanges</span></div>'
    +'<div class="ppl-actions">'
    +'<button class="btn btn-sm btn-ghost" data-act="view" data-pid="'+p.id+'">View profile</button>'
    +'<button class="btn btn-sm btn-primary" data-act="msg" data-pid="'+p.id+'">💬 Message</button>'
    +(contactExists(p)
      ?'<button class="btn btn-sm btn-line" data-act="add" data-pid="'+p.id+'" disabled>✓ In contacts</button>'
      :'<button class="btn btn-sm btn-line" data-act="add" data-pid="'+p.id+'">＋ Contact</button>')
    +'</div></article>';
}

/* ================= empty state ================= */
function emptyHTML(){
  const copy=isStudent()
    ?'Invite your classmates to join Orbit — once they\u2019re here, they\u2019ll show up in this list.'
    :'Invite your neighbors to join Orbit — once they\u2019re here, they\u2019ll show up in this list.';
  return '<div class="empty"><div class="big">👥</div><h3>No one here yet</h3>'
    +'<p class="sub">'+copy+'</p>'
    +'<button class="btn btn-primary" id="pplInvite">📨 Invite</button></div>';
}

/* ================= profile sheet (mirrors the ME profile layout) ================= */
function openProfile(id){
  const p=store.find('people',id);
  if(!p){ ui.toast('Profile not found'); return; }
  const col=avColor(p), mutual=(p.mutualGroups||[]), added=contactExists(p);
  let html='<div class="ppl-prof">'
    +'<div class="ppl-hero">'
    +'<div class="ppl-avatar lg" style="--ppl-ac:'+col+'">'+ui.esc(ui.initials(p.name))+'</div>'
    +'<h1 class="ppl-name">'+ui.esc(p.name)+'</h1>'
    +'<div class="ppl-campus">'+(isStudent()?'🎓':'🏘️')+' '+ui.esc(p.campus||'')+'</div>'
    +'<div class="ppl-badgerow">'+ui.sampleBadge(p.sample)+' '
    +(p.verified?'<span class="badge b-verified">✓ Verified</span>':'<span class="badge b-unverified">Unverified</span>')
    +' <span class="stars">'+ui.stars(Number(p.stars)||0)+'</span></div>'
    +'<div class="ppl-ribbon" role="list" aria-label="Reputation">'
    +'<span class="ppl-chip">'+(p.verified?'✓ Verified':'○ Unverified')+'</span>'
    +'<span class="ppl-chip">🤝 '+(Number(p.jobsDone)||0)+' jobs done</span>'
    +'<span class="ppl-chip">🏷️ '+(Number(p.exchanges)||0)+' exchanges</span>'
    +'<span class="ppl-chip">★ '+(Number(p.stars)||0).toFixed(1)+' rating</span>'
    +'</div></div>';
  if(p.knownFor) html+='<div class="ppl-sec"><h2>💡 Known for</h2><div class="card tight"><p style="font-size:14.5px;line-height:1.55">'+ui.esc(p.knownFor)+'</p></div></div>';
  if((p.skills||[]).length) html+='<div class="ppl-sec"><h2>🛠️ Skills</h2><div class="ppl-skills">'+(p.skills||[]).map(s=>'<span class="ppl-skill">'+ui.esc(s)+'</span>').join('')+'</div></div>';
  if(mutual.length) html+='<div class="ppl-sec"><h2>👥 In common</h2><div class="card tight"><p style="font-size:14px">🏠 Shares <strong>'+ui.esc(mutual.join(' · '))+'</strong> with you</p><p class="hint">Plus everyone here is at '+ui.esc(p.campus||'your community')+'.</p></div></div>';
  html+='<div class="demo-note" style="margin-top:14px"><strong>Sample profile.</strong> Real people appear when accounts go live with the production backend. Chatting here just opens a local thread in this browser.</div>';
  html+='<div class="ppl-actions ppl-sheet-actions">'
    +'<button class="btn btn-primary" id="ppMsg" style="flex:1">💬 Message</button>'
    +(added?'<button class="btn btn-line" disabled>✓ In contacts</button>'
           :'<button class="btn btn-line" id="ppAdd">＋ Add as contact</button>')
    +'</div></div>';
  ui.openSheet(html);
  document.getElementById('ppMsg').onclick=()=>messagePerson(p);
  const add=document.getElementById('ppAdd');
  if(add) add.onclick=()=>{ if(addContact(p)){ openProfile(p.id); } };
}

/* ================= contact + message actions ================= */
function addContact(p){
  if(contactExists(p)){ ui.toast('Already in your contacts'); return false; }
  store.add('contacts',{name:p.name,phone:p.phone||''});
  ui.toast('Added to contacts ✓');
  return true;
}
/* Opens (or creates) a real local thread with this person — no fake replies,
   no presence. Uses openThread directly rather than openWith so the
   marketplace-only safety checklist isn't mislabeled for a person. */
function messagePerson(p){
  const name=String(p.name||'').trim(), phone=String(p.phone||'').trim();
  if(!name){ ui.toast('No name on this profile'); return; }
  let c=null;
  if(phone) c=store.state.contacts.find(x=>String(x.phone||'').trim()===phone);
  if(!c) c=store.state.contacts.find(x=>String(x.name||'').trim().toLowerCase()===name.toLowerCase());
  if(!c){ store.add('contacts',{name,phone}); c=store.state.contacts[0]; }
  let t=store.state.threads.find(x=>x.contactId===c.id);
  if(!t){ store.add('threads',{contactId:c.id,listingId:null,title:c.name,messages:[],unread:0});
          t=store.state.threads.find(x=>x.contactId===c.id); }
  if(t&&(!t.messages||!t.messages.length)){
    t.messages=[{from:'me',text:'Hi '+firstName(name)+'! I found you in People at '+myCampus()+' on Orbit 👋',at:Date.now()}];
    store.save();
  }
  if(HUB.chat&&HUB.chat.openThread) HUB.chat.openThread(t.id);
}

/* ================= the surface ================= */
function segHTML(){
  return '<div class="seg"><button data-sub="households">🏠 Households</button><button data-sub="campus">🏘️ Communities</button><button class="on">👤 People</button></div>';
}
function renderSurface(el){
  const vis=visiblePeople(), list=filteredPeople(), skills=allSkills(vis);
  let html='<h1 class="greet">Groups</h1>'
    +'<p class="sub" style="margin:4px 0 12px">Find people '+(isStudent()?'at your school':'in your community')+' — message them or add them as contacts.</p>'
    +segHTML()
    +'<div class="demo-note">🧪 <b>Sample profiles</b> — real people appear when accounts go live with the production backend.</div>'
    +'<div class="row between" style="margin-bottom:4px"><h2 style="margin:0">👤 '+ui.esc(peopleTitle())+'</h2><span class="meta">'+list.length+' shown</span></div>'
    +'<div class="chips" id="pplChips">'
    +'<button class="chip'+((!fSkill&&!fMutual)?' on':'')+'" data-f="all">All</button>'
    +skills.map(s=>'<button class="chip'+(fSkill===String(s).toLowerCase()?' on':'')+'" data-f="skill" data-v="'+ui.esc(s)+'">'+ui.esc(s)+'</button>').join('')
    +'<button class="chip'+(fMutual?' on':'')+'" data-f="mutual">👥 Shared households</button>'
    +'</div>';
  html+=list.length? list.map(cardHTML).join('') : emptyHTML();
  el.innerHTML=html;

  el.querySelectorAll('[data-sub]').forEach(b=>{ b.onclick=()=>HUB.views.groups.setSub(b.dataset.sub); });
  el.querySelectorAll('#pplChips .chip').forEach(ch=>{
    ch.onclick=()=>{
      const f=ch.dataset.f;
      if(f==='all'){ fSkill=null; fMutual=false; }
      else if(f==='mutual'){ fMutual=!fMutual; if(fMutual) fSkill=null; }
      else if(f==='skill'){ const v=String(ch.dataset.v||'').toLowerCase(); fSkill=(fSkill===v?null:v); if(fSkill) fMutual=false; }
      renderSurface(el);
    };
  });
  const inv=document.getElementById('pplInvite');
  if(inv) inv.onclick=()=>ui.toast(isStudent()?'Share Orbit with your classmates 🤝':'Share Orbit with your neighbors 🤝');
  el.querySelectorAll('[data-act]').forEach(b=>{
    b.onclick=()=>{
      const p=store.find('people',b.dataset.pid);
      if(!p) return;
      const a=b.dataset.act;
      if(a==='view') openProfile(p.id);
      else if(a==='msg') messagePerson(p);
      else if(a==='add'){ if(addContact(p)) renderSurface(el); }
    };
  });
}

HUB.people={renderSurface,openProfile,addContact,messagePerson,visiblePeople};
})();
