/* HUB ME tab: real-identity profile with the REPUTATION RIBBON hero.
   Sections: hero + reputation ribbon, reputation breakdown, skills,
   community & households, activity history, MEMORY vault, verification
   (honest demo), trust & safety, settings, danger zone.
   Module keeps in-session blob URLs (they do not survive reload);
   metadata always persists in store.state.memory.
   All styles live in profile.css, scoped under #view-me / .me-*. */
(function(){
'use strict';
const {store,ui}=HUB;
/* HUB.icons loads after this file (see index.html) — resolve lazily. */
function icons(name,cls){ return (HUB.icons&&HUB.icons.icon)?HUB.icons.icon(name,cls):''; }
HUB.views=HUB.views||{};

const blobUrls={};       // id -> objectURL, in-session only
let searchQ='';
let pendingFile=null;      // chosen-but-unsaved upload; survives search re-renders
let rec=null, recChunks=[];

const KIND_ORDER=['receipt','document','photo','voice','note'];
const KIND_BADGE={receipt:'🧾 Receipt',document:'📄 Document',photo:'🖼️ Photo',voice:'🎙️ Voice',note:'📝 Note'};

/* orbit avatar palette (avatarColor indexes into it) — all AA-safe under white initials, no purple */
const AV_COLORS=['#1F7A4D','#2563EB','#C22E1F','#0F766E','#B45309','#C2410C','#1D4ED8','#131A00'];

function kindFromFile(f){
  if(!f) return 'note';
  if(f.type.startsWith('image/')) return 'photo';
  if(f.type.startsWith('audio/')) return 'voice';
  if(f.type==='application/pdf'||f.type.startsWith('text/')||/word|msword|officedocument/.test(f.type)) return 'document';
  return 'document';
}
function daysLeft(exp){ return Math.ceil((exp-Date.now())/86400000); }
function expiryLine(m){
  if(!m.expiry) return '';
  const d=daysLeft(m.expiry);
  if(d<0) return '<div class="meta" style="color:var(--danger);font-weight:700">❌ expired '+Math.abs(d)+'d ago</div>';
  if(d<=60) return '<div class="meta" style="color:var(--amber);font-weight:700">⚠️ expires in '+d+' day'+(d===1?'':'s')+'</div>';
  return '<div class="meta">expires in '+d+' days</div>';
}

function rerender(){ const el=document.getElementById('view-me'); if(el) HUB.views.me.render(el); }

/* ---- derived profile stats (all from store.state, never invented) ---- */
function stats(){
  const p=store.state.profile, me=store.myName();
  const myListings=store.state.listings.filter(l=>l.seller===me);
  const myRealListings=myListings.filter(l=>!l.sample);
  const myJobsPosted=store.state.jobs.filter(j=>j.poster===me);
  const myJobsTaken=store.state.jobs.filter(j=>j.acceptedBy===me);
  return {
    me:myListings,myRealListings:myRealListings,myJobsPosted:myJobsPosted,myJobsTaken:myJobsTaken,
    deals:(p.jobsDone||0)+myRealListings.length,
    communities:(store.state.households||[]).length+(p.campus?1:0),
    stars:p.stars||0,
  };
}

/* community emoji (Workstream C): students see 🎓, community members 🏘️.
   Profiles saved before the reframe have no audience — infer from the name. */
function comEmoji(p){
  if(p.audience==='student') return '🎓';
  if(p.audience==='community') return '🏘️';
  return ui.isCampusCommunity(p.campus)?'🎓':'🏘️';
}

/* ---- SAFETY SCORE: computed ONLY from real local data (never invented) ----
   Formula: 50 base · +20 if profile.verified · +2 per completed deal (capped +20),
   where a "deal" = profile.jobsDone + my non-sample listings (same as the 🤝 chip) ·
   +1 per FULL star above 3 in profile.stars (capped +10) · total capped at 100. */
function safetyScore(p,s){
  const parts=[];
  let score=50;
  parts.push({label:'Base score', detail:'Everyone starts here', pts:50});
  const vPts=p.verified?20:0;
  score+=vPts;
  parts.push({label:'Verified account', detail:p.verified?'+20 — your account is verified':'+0 — verify your account to earn +20', pts:vPts});
  const dPts=Math.min(20,2*(s.deals||0));
  score+=dPts;
  parts.push({label:'Completed deals', detail:(s.deals||0)+' deal'+((s.deals||0)===1?'':'s')+' × 2 = +'+dPts+' (capped at +20)', pts:dPts});
  const starsAbove=Math.max(0,Math.floor((p.stars||0)-3));
  const rPts=Math.min(10,starsAbove);
  score+=rPts;
  parts.push({label:'Ratings', detail:(p.stars||0)+'★ → '+starsAbove+' full star'+(starsAbove===1?'':'s')+' above 3 = +'+rPts+' (capped at +10)', pts:rPts});
  score=Math.min(100,score);
  return {score:score,parts:parts};
}

/* ================= MEMORY VAULT (kept from previous build) ================= */
function renderVault(){
  const items=store.state.memory;
  const q=searchQ.trim().toLowerCase();
  const filtered=items.filter(m=>!q||(m.title+' '+(m.note||'')).toLowerCase().includes(q));

  let html='<div class="card"><div class="row between"><h2>🧠 MEMORY vault</h2><span class="badge b-BORROW">demo local</span></div>'
    +'<p class="sub" style="margin:6px 0 10px">“Remember it for me” — receipts, docs, photos, voice notes. Stored in this browser only.</p>'
    +'<div class="field"><label>Upload file</label><label class="btn btn-line btn-block" style="cursor:pointer">📎 Choose file<input type="file" class="hiddenfile" id="memFile"></label>'
    +'<p class="hint" id="memFileName">images, pdf, audio, anything</p></div>'
    +'<div class="field"><label>Title</label><input class="input" id="memTitle" placeholder="e.g. Laptop receipt"></div>'
    +'<div class="field"><label>Note</label><textarea class="textarea" id="memNote" placeholder="Serial number, where it is, anything…"></textarea></div>'
    +'<div class="grid2"><div class="field"><label>Kind (auto)</label><select class="input" id="memKind">'
    +KIND_ORDER.map(k=>'<option value="'+k+'">'+KIND_BADGE[k]+'</option>').join('')+'</select></div>'
    +'<div class="field"><label>Warranty expiry (optional)</label><input class="input" id="memExp" type="date"></div></div>'
    +'<button class="btn btn-primary btn-block" id="memSave">Save to vault</button>';

  /* voice recorder */
  if(window.MediaRecorder) html+='<button class="btn btn-ghost btn-block" id="memRec" style="margin-top:8px">🎤 Record voice note</button>';
  else html+='<p class="hint" style="margin-top:8px">🎤 Voice recording not supported here — voice upload via file.</p>';

  html+='<div class="divider"></div>'
    +'<div class="field"><input class="input" id="memSearch" placeholder="🔍 search the vault…" value="'+ui.esc(searchQ)+'"></div>';

  /* reminders: expiry within 60 days */
  const soon=items.filter(m=>m.expiry&&daysLeft(m.expiry)<=60).sort((a,b)=>a.expiry-b.expiry);
  if(soon.length){
    html+='<h3 style="margin-bottom:8px">⏰ Reminders</h3>';
    for(const m of soon){
      html+='<div class="item tight" style="padding:10px 12px;margin-bottom:8px"><div class="grow"><h3>'+ui.esc(m.title)+'</h3>'+expiryLine(m)+'</div><button class="btn btn-sm btn-line memDel" data-mid="'+m.id+'">✕</button></div>';
    }
    html+='<div class="divider"></div>';
  }

  /* grouped by kind */
  if(!filtered.length) html+='<div class="empty"><div class="big">🧠</div><p>Vault is empty — save your first memory above.</p></div>';
  for(const k of KIND_ORDER){
    const group=filtered.filter(m=>m.kind===k).sort((a,b)=>(b.createdAt||0)-(a.createdAt||0));
    if(!group.length) continue;
    html+='<h3 style="margin:12px 0 8px">'+KIND_BADGE[k]+' <span class="meta">'+group.length+'</span></h3>';
    for(const m of group){
      const url=blobUrls[m.id];
      const thumb=url?(m.kind==='photo'?'<img class="thumb" src="'+url+'" alt="">':'<div class="avatar" style="background:var(--surface2);color:var(--ink)">'+(m.kind==='voice'?'🎙️':'📎')+'</div>'):'<div class="avatar" style="background:var(--surface2);color:var(--ink)">'+ui.initials(m.title)+'</div>';
      html+='<div class="item">'+thumb+'<div class="grow"><h3>'+ui.esc(m.title)+'</h3>'
        +'<div class="meta">'+KIND_BADGE[m.kind||'note']+(m.fileName?' · '+ui.esc(m.fileName):'')+(m.createdAt?' · '+ui.timeAgo(m.createdAt):'')+'</div>'
        +(m.note?'<div style="font-size:13.5px;margin-top:4px;line-height:1.45">'+ui.esc(m.note)+'</div>':'')
        +expiryLine(m)
        +(url&&m.kind==='voice'?'<audio controls src="'+url+'" style="width:100%;margin-top:6px"></audio>':'')
        +'</div>'
        +'<button class="btn btn-sm btn-line memDel" data-mid="'+m.id+'">✕</button></div>';
    }
  }
  html+='</div>';
  return html;
}

function wireVault(el){
  const fileInput=el.querySelector('#memFile');
  const kindSel=el.querySelector('#memKind');
  const nameHint=el.querySelector('#memFileName');
  if(pendingFile&&nameHint){ nameHint.textContent='📎 '+pendingFile.name+' ('+Math.round(pendingFile.size/1024)+' KB)'; kindSel.value=kindFromFile(pendingFile); }
  if(fileInput){
    fileInput.onchange=()=>{
      pendingFile=fileInput.files&&fileInput.files[0]||null;
      if(pendingFile){
        nameHint.textContent='📎 '+pendingFile.name+' ('+Math.round(pendingFile.size/1024)+' KB)';
        kindSel.value=kindFromFile(pendingFile);
        const title=el.querySelector('#memTitle');
        if(!title.value.trim()) title.value=pendingFile.name.replace(/\.[^.]+$/,'');
      }else{ nameHint.textContent='images, pdf, audio, anything'; }
    };
  }
  el.querySelector('#memSave').onclick=()=>{
    const title=el.querySelector('#memTitle').value.trim();
    if(!title){ui.toast('Give it a title');return;}
    const expStr=el.querySelector('#memExp').value;
    const m={id:store.uid(),kind:kindSel.value,title,note:el.querySelector('#memNote').value.trim(),createdAt:Date.now(),sample:false};
    if(pendingFile){ m.fileName=pendingFile.name; blobUrls[m.id]=URL.createObjectURL(pendingFile); }
    if(expStr){ const t=new Date(expStr+'T12:00:00').getTime(); if(!isNaN(t)) m.expiry=t; }
    store.state.memory.unshift(m); store.save();
    pendingFile=null;
    rerender(); ui.toast('Saved to vault 🧠');
  };

  /* search */
  const sIn=el.querySelector('#memSearch');
  if(sIn){ sIn.oninput=()=>{ searchQ=sIn.value; const pos=sIn.selectionStart; rerender(); const el2=document.getElementById('view-me'); const n2=el2&&el2.querySelector('#memSearch'); if(n2){n2.focus();n2.setSelectionRange(pos,pos);} }; }

  /* delete */
  el.querySelectorAll('.memDel').forEach(b=>{ b.onclick=()=>{ const id=b.dataset.mid; if(blobUrls[id]){URL.revokeObjectURL(blobUrls[id]);delete blobUrls[id];} store.remove('memory',id); rerender(); ui.toast('Deleted'); }; });

  /* voice recorder */
  const recBtn=el.querySelector('#memRec');
  if(recBtn&&window.MediaRecorder){
    recBtn.onclick=async()=>{
      if(rec){
        rec.stop(); return;
      }
      try{
        const stream=await navigator.mediaDevices.getUserMedia({audio:true});
        recChunks=[];
        rec=new MediaRecorder(stream);
        rec.ondataavailable=e=>{ if(e.data.size) recChunks.push(e.data); };
        rec.onstop=()=>{
          stream.getTracks().forEach(t=>t.stop());
          const blob=new Blob(recChunks,{type:rec.mimeType||'audio/webm'});
          const m={id:store.uid(),kind:'voice',title:'Voice note · '+new Date().toLocaleString(),note:'',createdAt:Date.now(),sample:false};
          blobUrls[m.id]=URL.createObjectURL(blob);
          store.state.memory.unshift(m); store.save();
          rec=null; rerender(); ui.toast('Voice note saved 🎙️');
        };
        rec.start();
        recBtn.textContent='⏹️ Stop recording…';
        recBtn.onclick=()=>{ if(rec) rec.stop(); };
      }catch(e){ ui.toast('Microphone not available'); rec=null; }
    };
  }
}

/* ================= VERIFY SHEET (honest demo — kept) ================= */
function verifySheet(){
  const p=store.state.profile;
  ui.openSheet(
    '<h2>Verify my account</h2>'
    +'<div class="demo-note"><strong>Demo preview.</strong> Verification needs the production backend — your account works in demo mode for now. Nothing here is actually sent or verified.</div>'
    +'<h3 style="margin:12px 0 8px">Option 1 — Email code</h3>'
    +'<div class="field"><label>Email</label><input class="input" id="vEmail" type="email" placeholder="you@school.edu" value="'+ui.esc(p.email||'')+'"></div>'
    +'<button class="btn btn-line btn-block" id="vEmailGo" disabled>Send code (needs backend)</button>'
    +'<h3 style="margin:16px 0 8px">Option 2 — SMS code</h3>'
    +'<div class="field"><label>Phone</label><input class="input" id="vPhone" type="tel" placeholder="+1 555-000-0000" value="'+ui.esc(p.phone||'')+'"></div>'
    +'<button class="btn btn-line btn-block" id="vSmsGo" disabled>Send code (needs backend)</button>'
    +'<p class="hint" style="margin-top:12px">Code-sending buttons are disabled until the backend exists. Posting, groups and everything else work in demo mode regardless.</p>'
    +'<button class="btn btn-primary btn-block" id="vSave" style="margin-top:10px">Save my details</button>'
  );
  document.getElementById('vSave').onclick=()=>{
    p.email=document.getElementById('vEmail').value.trim();
    p.phone=document.getElementById('vPhone').value.trim();
    store.save(); ui.closeSheet(); rerender();
    ui.toast('Details saved — verification arrives with the backend');
  };
}

/* ================= REPORT SHEET (local, honest) ================= */
function reportSheet(){
  ui.openSheet(
    '<h2>🚩 Report a problem</h2>'
    +'<p class="sub" style="margin-bottom:12px">Reports are stored on this device in the demo preview — nothing is sent anywhere. Review them in the moderation queue.</p>'
    +'<div class="field"><label>Kind</label><select class="input" id="rpKind"><option>Listing</option><option>Job</option><option>User</option><option>Post</option><option>Other</option></select></div>'
    +'<div class="field"><label>What is this about? *</label><input class="input" id="rpTitle" placeholder="e.g. Suspicious listing" maxlength="80"></div>'
    +'<div class="field"><label>What happened?</label><textarea class="textarea" id="rpReason" placeholder="Describe what happened…"></textarea></div>'
    +'<button class="btn btn-primary btn-block" id="rpSave">Save report</button>'
  );
  document.getElementById('rpSave').onclick=()=>{
    const title=document.getElementById('rpTitle').value.trim();
    if(!title){ui.toast('Say what this is about');return;}
    store.state.reports.unshift({id:store.uid(),kind:document.getElementById('rpKind').value,title,
      reason:document.getElementById('rpReason').value.trim(),at:Date.now(),resolved:false,sample:false});
    store.save(); ui.closeSheet(); rerender();
    ui.toast('Report saved — find it in the moderation queue');
  };
}

/* ================= SECTION BUILDERS ================= */
function secHead(iconName,emoji,title){
  const ic=icons(iconName);
  return '<div class="me-sec"><span class="me-secico">'+(ic||ui.esc(emoji))+'</span><h2>'+ui.esc(title)+'</h2></div>';
}

function renderHero(p,s){
  const av=AV_COLORS[Math.abs(p.avatarColor||0)%AV_COLORS.length];
  const badge=p.verified?'<span class="badge b-verified">✓ Verified</span>':'<span class="badge b-unverified">Unverified</span>';
  const dealN=s.deals, comN=s.communities;
  const chips=
    '<div class="me-chip '+(p.verified?'me-chip-ok':'me-chip-warn')+'">'+(p.verified?'✓ Verified':'○ Unverified')+'</div>'
    +'<div class="me-chip">🤝 '+dealN+' deal'+(dealN===1?'':'s')+'</div>'
    +'<div class="me-chip">👥 '+comN+' communit'+(comN===1?'y':'ies')+'</div>'
    +'<div class="me-chip">'+(s.stars>0?'★ '+s.stars:'★ No ratings yet')+'</div>';
  return '<div class="card me-hero">'
    +'<div class="me-avatar" style="--me-ac:'+av+'">'+ui.initials(p.name||'?')+'</div>'
    +'<h1 class="me-name">'+ui.esc(p.name||'—')+'</h1>'
    +'<div class="me-campus">'+comEmoji(p)+' '+ui.esc(p.campus||'No community set')+'</div>'
    +'<div class="me-badgerow">'+badge+' <span class="stars">'+ui.stars(s.stars)+'</span></div>'
    +'<div class="me-ribbon" role="list" aria-label="Reputation">'+chips+'</div>'
    +scoreStrip(p,s)
    +'</div>';
}

/* tappable safety-score strip (lives just under the ribbon, inside the hero) */
function scoreStrip(p,s){
  const sc=safetyScore(p,s);
  const band=sc.score>=75?'me-score-high':(sc.score>=50?'me-score-mid':'me-score-low');
  return '<button class="me-score '+band+'" id="meScoreStrip" aria-label="Safety score '+sc.score+' out of 100. Show how it is derived.">'
    +'<span class="me-score-num" aria-hidden="true">'+sc.score+'</span>'
    +'<span class="me-score-body">'
    +'<span class="me-score-label">🛡️ Safety score</span>'
    +'<span class="me-score-bar" aria-hidden="true"><span style="width:'+sc.score+'%"></span></span>'
    +'<span class="me-score-note">Demo score · computed on this device · How is this derived? ⓘ</span>'
    +'</span>'
    +'<span class="me-score-chev" aria-hidden="true">›</span>'
    +'</button>';
}

/* explainer sheet: the exact formula, with this user's real numbers plugged in */
function scoreSheet(){
  const p=store.state.profile, s=stats(); s.me=store.myName();
  const sc=safetyScore(p,s);
  ui.openSheet(
    '<h2>🛡️ How is this derived?</h2>'
    +'<div class="demo-note" style="margin-top:8px"><strong>Demo safety score — computed on this device from your local data.</strong> Nothing is sent, checked, or verified against any server.</div>'
    +'<h3 style="margin:14px 0 4px">Exact formula</h3>'
    +'<p class="sub" style="margin-bottom:10px">Start at <strong>50</strong> · <strong>+20</strong> if your account is verified · <strong>+2</strong> per completed deal, up to +20 · <strong>+1</strong> per full star above 3 in your ratings, up to +10 · total capped at 100.</p>'
    +'<p class="sub" style="margin-bottom:8px">A “deal” = completed jobs (your jobsDone) + non-sample marketplace listings you posted — the same number as the 🤝 chip in your ribbon above.</p>'
    +sc.parts.map(pt=>'<div class="kv"><span>'+ui.esc(pt.label)+'<br><span class="meta">'+ui.esc(pt.detail)+'</span></span><strong>'+(pt.pts>0?'+':'')+pt.pts+'</strong></div>').join('')
    +'<div class="kv"><span><strong>Your safety score</strong></span><strong>'+sc.score+' / 100</strong></div>'
    +'<div class="divider"></div>'
    +'<p class="sub">Raise it by verifying your account, completing exchanges, and earning good ratings. Real ID/phone verification, escrow and human review are planned for the production backend — until then this score only sees what\u2019s stored on this device.</p>'
  );
}

function renderRepGrid(s){
  const card=(iconName,emoji,num,label,hint)=>'<div class="me-repcard"><span class="me-repico">'+(icons(iconName)||ui.esc(emoji))+'</span>'
    +'<div class="me-repnum">'+num+'</div><div class="me-replabel">'+ui.esc(label)+'</div>'
    +(hint?'<div class="me-rephint">'+ui.esc(hint)+'</div>':'')+'</div>';
  const ratings=s.stars>0?'★ '+s.stars:'No ratings yet';
  return secHead('stat-money','💰','Reputation')
    +'<div class="me-repgrid">'
    +card('act-job','💼',(store.state.profile.jobsDone||0),'Jobs completed','')
    +card('act-sell','🏷️',s.myRealListings.length,'Marketplace exchanges','listings you posted')
    +card('nav-groups','👥',s.communities,'Communities','households + community')
    +card('','★',ratings,'Ratings received',s.stars>0?'from your profile':'nobody has rated you yet')
    +'</div>';
}

function renderSkills(p){
  const skills=p.skills||[];
  let body;
  if(!skills.length){
    body='<p class="sub me-skills-empty">Add what you\u2019re good at — design, photography, tutoring… People will see these on your profile.</p>';
  }else{
    body='<div class="me-skills">'+skills.map((sk,i)=>'<span class="me-skill">'+ui.esc(sk)+'<button class="me-skill-x" data-skill="'+i+'" aria-label="Remove '+ui.esc(sk)+'">✕</button></span>').join('')+'</div>';
  }
  return secHead('act-task','📋','Skills')
    +'<div class="card">'+body
    +'<div class="me-skill-add"><input class="input" id="meSkillInput" placeholder="Add a skill — e.g. photography" maxlength="40"><button class="btn btn-primary" id="meSkillAdd">Add</button></div>'
    +'</div>';
}

function renderCommunities(p){
  const campOpts=ui.communityOptions(p.campus);
  const hs=store.state.households||[];
  let hh=hs.length? hs.map(h=>{
    const mems=(h.members||[]);
    return '<div class="me-comrow"><div class="me-comicon">🏠</div><div class="grow"><h3>'+ui.esc(h.name||'Household')+ui.sampleBadge(h.sample)+'</h3>'
      +'<div class="meta">'+mems.length+' member'+(mems.length===1?'':'s')+(mems.length?' · '+ui.esc(mems.slice(0,4).join(', '))+(mems.length>4?'…':''):'')+'</div></div></div>';
  }).join('')
    :'<p class="sub">No households yet — create one in Groups to split bills and chores.</p>';
  return secHead('nav-groups','👥','Community & households')
    +'<div class="card">'
    +'<div class="me-comrow"><div class="me-comicon">'+comEmoji(p)+'</div><div class="grow"><h3>Community</h3><div class="meta">Shown on your listings and profile.</div></div>'
    +'<select class="input" id="meCampus" style="width:auto;max-width:170px" aria-label="Change community">'+campOpts+'</select></div>'
    +'<p class="hint" style="margin:8px 0 0">Sample communities — real communities go live with the production backend. You can switch anytime here.</p>'
    +'<div class="divider"></div>'
    +'<h3 style="margin-bottom:8px">Households ('+hs.length+')</h3>'+hh
    +'</div>';
}

function renderActivity(s){
  const items=[];
  const me=s.me;
  for(const l of store.state.listings) if(l.seller===me)
    items.push({ic:'act-sell',fb:'🏷️',t:'Listed: '+l.title,m:((l.type||'').toLowerCase()||'listing')+' · '+ui.timeAgo(l.createdAt||Date.now()),at:l.createdAt||0,sample:l.sample});
  for(const j of store.state.jobs){
    if(j.poster===me) items.push({ic:'act-job',fb:'💼',t:'Posted job: '+j.title,m:(j.status||'open')+' · '+ui.fmt$(j.pay||0)+' · '+ui.timeAgo(j.createdAt||Date.now()),at:j.createdAt||0,sample:j.sample});
    else if(j.acceptedBy===me) items.push({ic:'act-job',fb:'💼',t:'Accepted job: '+j.title,m:(j.status||'open')+' · '+ui.fmt$(j.pay||0)+' · '+ui.timeAgo(j.createdAt||Date.now()),at:j.createdAt||0,sample:j.sample});
  }
  for(const m of store.state.memory)
    items.push({ic:'act-memory',fb:'🧠',t:'Saved to vault: '+m.title,m:(m.kind||'note')+' · '+ui.timeAgo(m.createdAt||Date.now()),at:m.createdAt||0,sample:m.sample});
  for(const c of (store.state.campusPosts||[])) if(c.author===me)
    items.push({ic:'act-post',fb:'📣',t:'Posted to community',m:ui.timeAgo(c.at||Date.now()),at:c.at||0,sample:c.sample});
  items.sort((a,b)=>b.at-a.at);
  const top=items.slice(0,10);

  let body;
  if(!top.length){
    body='<div class="empty"><div class="big">🕰️</div><p>Nothing here yet. Your listings, jobs, posts and vault saves will show up here.</p></div>'
      +'<div class="me-act-cta"><button class="btn btn-line" id="meGoMarket">Browse marketplace</button><button class="btn btn-line" id="meGoWork">Find micro-jobs</button></div>';
  }else{
    body=top.map(a=>'<div class="me-act"><span class="me-acticon">'+(icons(a.ic)||ui.esc(a.fb))+'</span>'
      +'<div class="grow"><h3>'+ui.esc(a.t)+'</h3><div class="meta">'+ui.esc(a.m)+'</div></div>'
      +ui.sampleBadge(a.sample)+'</div>').join('');
  }
  return secHead('ic-pulse','⚡','Recent activity')+'<div class="card">'+body+'</div>';
}

/* ---- TRANSACTION / EXCHANGE HISTORY: real local activity only ----
   My listings (posted), jobs I've posted or accepted, completed exchanges.
   Each row: icon, title, type chip (Listing/Job), time-ago, status. Sample
   items carry Sample badges. Honest empty state with redirect. */
function renderTransactions(s){
  const me=s.me;
  const items=[];
  for(const l of store.state.listings) if(l.seller===me)
    items.push({ic:'act-sell',fb:'🏷️',t:l.title||'Listing',chip:'Listing',chipCls:'b-SELL',
      m:'Listed · '+ui.timeAgo(l.createdAt||Date.now())+(l.price?' · '+ui.fmt$(l.price):''),
      at:l.createdAt||0,sample:l.sample});
  for(const j of store.state.jobs){
    const jm=' · '+ui.fmt$(j.pay||0)+' · '+(j.status||'open')+' · '+ui.timeAgo(j.createdAt||Date.now());
    if(j.poster===me) items.push({ic:'act-job',fb:'💼',t:j.title||'Job',chip:'Job',chipCls:'b-job',
      m:'Posted'+jm,at:j.createdAt||0,sample:j.sample});
    else if(j.acceptedBy===me) items.push({ic:'act-job',fb:'💼',t:j.title||'Job',chip:'Job',chipCls:'b-job',
      m:'Accepted'+jm,at:j.createdAt||0,sample:j.sample});
  }
  items.sort((a,b)=>b.at-a.at);

  let body;
  if(!items.length){
    body='<div class="empty"><div class="big">🧾</div><p>No exchanges yet — when you post a listing or take a job, it will show up here.</p></div>'
      +'<div class="me-act-cta"><button class="btn btn-primary" id="meGoList">Post your first listing</button><button class="btn btn-line" id="meGoWork2">Find micro-jobs</button></div>';
  }else{
    body=items.map(a=>'<div class="me-act"><span class="me-acticon">'+(icons(a.ic)||ui.esc(a.fb))+'</span>'
      +'<div class="grow"><h3>'+ui.esc(a.t)+'</h3><div class="meta">'+ui.esc(a.m)+'</div></div>'
      +ui.sampleBadge(a.sample)+'<span class="badge '+a.chipCls+'">'+a.chip+'</span></div>').join('');
  }
  return secHead('act-expense','🧾','Transaction history')+'<div class="card">'+body+'</div>';
}

function renderVerification(p){
  const row=(label,val)=>'<div class="kv"><span>'+label+'</span><span class="meta">'+(val?ui.esc(val):'Not set')+'</span></div>';
  return secHead('','✅','Verification')
    +'<div class="card">'
    +row('📧 Email',p.email)+row('📱 Phone',p.phone)
    +'<button class="btn btn-primary btn-block" id="verifyBtn" style="margin-top:10px">'+(p.verified?'Manage verification':'Verify my account')+'</button>'
    +(p.verified?'':'<p class="hint" style="margin-top:8px">Verified accounts get the ✓ badge on their profile and listings.</p>')
    +'</div>';
}

function renderSafety(){
  const p=store.state.profile;
  const openReports=(store.state.reports||[]).filter(r=>!r.resolved).length;
  const nBlocked=(store.state.blocked||[]).length;
  /* Discoverability (Workstream D): one-tap opt-out of the People surface.
     Defaults ON for the demo profile (migrated in store.js); people with
     this OFF never appear in anyone's people list. */
  const student=p.audience==='student';
  const discOn=p.discoverable!==false;
  const discRow='<div class="divider"></div><h3 style="margin-bottom:6px">👀 Discoverability</h3>'
    +'<div class="item" style="cursor:default">'
    +'<div class="grow"><h3>Discoverable by people '+(student?'at my school':'in my community')+'</h3>'
    +'<div class="meta">You appear in the People list'+(p.campus?' at '+p.campus:'')+'. People you already know can still message you.</div></div>'
    +'<div class="toggle'+(discOn?' on':'')+'" id="discToggle" role="switch" aria-checked="'+(discOn?'true':'false')+'" tabindex="0" aria-label="Discoverable by people at my community"></div>'
    +'</div>'
    +'<p class="hint" style="margin-top:8px">Turn this off and your profile disappears from everyone\u2019s People list.</p>';
  return secHead('','🛡️','Trust & safety')
    +'<div class="card">'
    +'<div class="kv"><span>🚩 Report a problem</span><button class="btn btn-sm btn-line" id="meReport">Report</button></div>'
    +'<div class="kv"><span>🔎 Moderation queue</span><button class="btn btn-sm btn-line" id="meModQ">Review'+(openReports?' ('+openReports+' open)':'')+'</button></div>'
    +'<div class="kv"><span>⛔ Blocked users</span><button class="btn btn-sm btn-line" id="meBlocked">Manage ('+nBlocked+')</button></div>'
    +(HUB.trust?'<div class="divider"></div><h3 style="margin-bottom:6px">🔒 Privacy</h3>'+HUB.trust.privacySettingsHTML():'')
    +discRow
    +'</div>';
}

function renderSettings(){
  return secHead('','⚙️','Settings')
    +'<div class="card">'
    +'<div class="kv"><span>🌙 Dark mode</span><div class="toggle'+(store.state.prefs.dark?' on':'')+'" id="darkToggle" role="switch" aria-checked="'+(!!store.state.prefs.dark)+'" tabindex="0" aria-label="Dark mode"></div></div>'
    +'<div class="kv"><span>Clear sample data</span><button class="btn btn-sm btn-line" id="clearSamples">Clear</button></div>'
    +'</div>';
}

/* ================= VIEW ================= */
HUB.views.me={ render(el){
  const p=store.state.profile;
  if(!Array.isArray(p.skills)) p.skills=[];
  const s=stats(); s.me=store.myName();

  let html=renderHero(p,s)
    +renderRepGrid(s)
    +renderSkills(p)
    +renderCommunities(p)
    +renderActivity(s)
    +renderTransactions(s)
    +'<div id="vaultHost">'+renderVault()+'</div>'
    +renderVerification(p)
    +renderSafety()
    +renderSettings()
    +'<div class="demo-note">Orbit demo preview — everything stays in this browser. No servers, no accounts yet.<br><span style="opacity:.75">Everything in your orbit.</span></div>'
    +'<div class="card" style="border-color:var(--danger)"><h2 style="margin-bottom:10px;color:var(--danger)">☢️ Danger zone</h2>'
    +'<button class="btn btn-block" id="resetAll" style="background:var(--danger);color:#fff">Reset all data</button>'
    +'<p class="hint">Wipes everything (including your posts) and restarts Orbit fresh.</p></div>';

  el.innerHTML=html;

  document.getElementById('verifyBtn').onclick=verifySheet;
  wireVault(el);

  /* skills */
  const addSkill=()=>{
    const inp=document.getElementById('meSkillInput');
    const v=inp.value.trim();
    if(!v){ui.toast('Type a skill first');return;}
    if(p.skills.some(sk=>sk.toLowerCase()===v.toLowerCase())){ui.toast('Already on your list');return;}
    p.skills.push(v.slice(0,40)); store.save(); rerender(); ui.toast('Skill added ✨');
  };
  document.getElementById('meSkillAdd').onclick=addSkill;
  document.getElementById('meSkillInput').onkeydown=e=>{ if(e.key==='Enter') addSkill(); };
  el.querySelectorAll('[data-skill]').forEach(b=>{ b.onclick=()=>{ p.skills.splice(Number(b.dataset.skill),1); store.save(); rerender(); }; });

  /* community + households */
  document.getElementById('meCampus').onchange=e=>{ p.campus=e.target.value; store.save(); rerender(); ui.toast('Community updated 🏘️'); };

  /* safety score explainer */
  const mss=document.getElementById('meScoreStrip');
  if(mss){ mss.onclick=scoreSheet; mss.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); scoreSheet(); } }; }

  /* activity + transaction-history empty-state redirects */
  const gm=document.getElementById('meGoMarket'); if(gm) gm.onclick=()=>HUB.showTab('market');
  const gw=document.getElementById('meGoWork'); if(gw) gw.onclick=()=>HUB.showTab('work');
  const mgl=document.getElementById('meGoList'); if(mgl) mgl.onclick=()=>HUB.showTab('market');
  const mgw2=document.getElementById('meGoWork2'); if(mgw2) mgw2.onclick=()=>HUB.showTab('work');

  /* settings */
  const dt=document.getElementById('darkToggle');
  const flipDark=()=>{ dt.classList.toggle('on'); store.state.prefs.dark=dt.classList.contains('on'); dt.setAttribute('aria-checked',String(store.state.prefs.dark)); store.save(); HUB.applyTheme(); };
  dt.onclick=flipDark;
  dt.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flipDark(); } };
  document.getElementById('clearSamples').onclick=()=>{ store.clearSamples(); rerender(); ui.toast('Sample data cleared'); };
  document.getElementById('resetAll').onclick=()=>{ if(confirm('Reset ALL Orbit data? This cannot be undone.')){ localStorage.removeItem('hub_v1'); location.reload(); } };

  /* trust & safety */
  document.getElementById('meReport').onclick=reportSheet;
  document.getElementById('meModQ').onclick=()=>{ if(HUB.trust&&HUB.trust.moderationQueue) HUB.trust.moderationQueue(); else ui.toast('Trust tools are not ready yet'); };
  /* discoverability toggle (Workstream D): one tap, flips profile.discoverable */
  const dts=document.getElementById('discToggle');
  if(dts){
    const flipDisc=()=>{
      const pr=store.state.profile;
      pr.discoverable=!(pr.discoverable!==false);
      store.save();
      dts.classList.toggle('on',!!pr.discoverable);
      dts.setAttribute('aria-checked',pr.discoverable?'true':'false');
      ui.toast(pr.discoverable?'You\u2019re discoverable in People ✓':'Hidden from the People list 👻');
    };
    dts.onclick=flipDisc;
    dts.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flipDisc(); } };
  }
  document.getElementById('meModQ').onclick=()=>{ if(HUB.trust&&HUB.trust.moderationQueue) HUB.trust.moderationQueue(); else ui.toast('Trust tools are not ready yet'); };
  document.getElementById('meBlocked').onclick=()=>{
    const blocked=(store.state.blocked||[]).map(b=>typeof b==='string'?b:(b&&b.name)||'').filter(Boolean);
    ui.openSheet('<h2>⛔ Blocked users</h2><p class="sub" style="margin-bottom:12px">You won\'t see listings, jobs, posts or pins from these people.</p>'+
      (blocked.length? blocked.map(b=>'<div class="item"><div class="avatar" style="background:var(--surface2)">⛔</div><div class="grow"><h3>'+ui.esc(b)+'</h3></div><button class="btn btn-sm btn-line" data-unblock="'+ui.esc(b)+'">Unblock</button></div>').join('')
        : '<p class="sub">Nobody blocked. 🎉</p>'));
    document.querySelectorAll('[data-unblock]').forEach(x=>{ x.onclick=()=>{ store.state.blocked=(store.state.blocked||[]).filter(n=>String(typeof n==='string'?n:(n&&n.name)||'')!==x.dataset.unblock); store.save(); ui.closeSheet(); rerender(); ui.toast('Unblocked'); }; });
  };
}};
})();
