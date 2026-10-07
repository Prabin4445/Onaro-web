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
const t=function(k,v){ return HUB.i18n.t(k,v); };
/* HUB.icons loads after this file (see index.html) — resolve lazily. */
function icons(name,cls){ return (HUB.icons&&HUB.icons.icon)?HUB.icons.icon(name,cls):''; }
HUB.views=HUB.views||{};

const blobUrls={};       // id -> objectURL, in-session only
let searchQ='';
let pendingFile=null;      // chosen-but-unsaved upload; survives search re-renders
let rec=null, recChunks=[];

const KIND_ORDER=['receipt','document','photo','voice','note'];

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
  if(d<0) return '<div class="meta" style="color:var(--danger);font-weight:700">'+t('me.vault.expired',{d:Math.abs(d)})+'</div>';
  if(d<=60) return '<div class="meta" style="color:var(--amber);font-weight:700">'+t('me.vault.expiresIn',{d,n:d})+'</div>';
  return '<div class="meta">'+t('me.vault.expiresInN',{d})+'</div>';
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

/* community emoji: follows what was actually picked — 🎓 for schools,
   🏘️ for communities. Profiles saved before kinds existed fall back to the
   audience, then to a name heuristic inside ui.campusEmoji. */
function comEmoji(p){
  if(p.campusKind) return ui.campusEmoji(p.campus, p.campusKind);
  if(ui.campusEmoji(p.campus,'')==='🎓') return '🎓'; /* legacy: school-like name beats the audience tag */
  return ui.campusEmoji(p.campus, p.audience==='student'?'school':(p.audience==='community'?'community':''));
}

/* ---- SAFETY SCORE: computed ONLY from real local data (never invented) ----
   Formula: 50 base · +20 if profile.verified · +2 per completed deal (capped +20),
   where a "deal" = profile.jobsDone + my non-sample listings (same as the 🤝 chip) ·
   +1 per FULL star above 3 in profile.stars (capped +10) · total capped at 100. */
function safetyScore(p,s){
  const parts=[];
  let score=50;
  parts.push({label:t('me.score.base'), detail:t('me.score.baseD'), pts:50});
  const vPts=p.verified?20:0;
  score+=vPts;
  parts.push({label:t('me.score.verified'), detail:p.verified?t('me.score.verifiedY'):t('me.score.verifiedN'), pts:vPts});
  const dPts=Math.min(20,2*(s.deals||0));
  score+=dPts;
  parts.push({label:t('me.score.deals'), detail:t('me.score.dealsD',{n:(s.deals||0),d:t('me.score.dealU',{n:(s.deals||0)}),p:dPts}), pts:dPts});
  const starsAbove=Math.max(0,Math.floor((p.stars||0)-3));
  const rPts=Math.min(10,starsAbove);
  score+=rPts;
  parts.push({label:t('me.score.ratings'), detail:t('me.score.ratingsD',{s:(p.stars||0),n:starsAbove,st:t('me.score.starU',{n:starsAbove}),p:rPts}), pts:rPts});
  score=Math.min(100,score);
  return {score:score,parts:parts};
}

/* ================= MEMORY VAULT (kept from previous build) ================= */
function renderVault(){
  const items=store.state.memory;
  const q=searchQ.trim().toLowerCase();
  const filtered=items.filter(m=>!q||(m.title+' '+(m.note||'')).toLowerCase().includes(q));

  let html='<div class="card"><div class="row between"><h2>'+t('me.vault.title')+'</h2><span class="badge b-BORROW">'+t('me.vault.demo')+'</span></div>'
    +'<p class="sub" style="margin:6px 0 10px">'+t('me.vault.sub')+'</p>'
    +'<div class="field"><label>'+t('me.vault.upload')+'</label><label class="btn btn-line btn-block" style="cursor:pointer">'+t('me.vault.choose')+'<input type="file" class="hiddenfile" id="memFile"></label>'
    +'<p class="hint" id="memFileName">'+t('me.vault.any')+'</p></div>'
    +'<div class="field"><label>'+t('me.vault.titleL')+'</label><input class="input" id="memTitle" placeholder="'+ui.esc(t('me.vault.titlePh'))+'"></div>'
    +'<div class="field"><label>'+t('me.vault.noteL')+'</label><textarea class="textarea" id="memNote" placeholder="'+ui.esc(t('me.vault.notePh'))+'"></textarea></div>'
    +'<div class="grid2"><div class="field"><label>'+t('me.vault.kindL')+'</label><select class="input" id="memKind">'
    +KIND_ORDER.map(k=>'<option value="'+k+'">'+t('me.vault.kind.'+k)+'</option>').join('')+'</select></div>'
    +'<div class="field"><label>'+t('me.vault.expL')+'</label><input class="input" id="memExp" type="date"></div></div>'
    +'<button class="btn btn-primary btn-block" id="memSave">'+t('me.vault.save')+'</button>';

  /* voice recorder */
  if(window.MediaRecorder) html+='<button class="btn btn-ghost btn-block" id="memRec" style="margin-top:8px">'+t('me.vault.rec')+'</button>';
  else html+='<p class="hint" style="margin-top:8px">'+t('me.vault.noRec')+'</p>';

  html+='<div class="divider"></div>'
    +'<div class="field"><input class="input" id="memSearch" placeholder="'+ui.esc(t('me.vault.searchPh'))+'" value="'+ui.esc(searchQ)+'"></div>';

  /* reminders: expiry within 60 days */
  const soon=items.filter(m=>m.expiry&&daysLeft(m.expiry)<=60).sort((a,b)=>a.expiry-b.expiry);
  if(soon.length){
    html+='<h3 style="margin-bottom:8px">'+t('me.vault.reminders')+'</h3>';
    for(const m of soon){
      html+='<div class="item tight" style="padding:10px 12px;margin-bottom:8px"><div class="grow"><h3>'+ui.esc(m.title)+'</h3>'+expiryLine(m)+'</div><button class="btn btn-sm btn-line memDel" data-mid="'+m.id+'">✕</button></div>';
    }
    html+='<div class="divider"></div>';
  }

  /* grouped by kind */
  if(!filtered.length) html+='<div class="empty"><div class="big">🧠</div><p>'+t('me.vault.empty')+'</p></div>';
  for(const k of KIND_ORDER){
    const group=filtered.filter(m=>m.kind===k).sort((a,b)=>(b.createdAt||0)-(a.createdAt||0));
    if(!group.length) continue;
    html+='<h3 style="margin:12px 0 8px">'+t('me.vault.kind.'+k)+' <span class="meta">'+group.length+'</span></h3>';
    for(const m of group){
      const url=blobUrls[m.id];
      const thumb=url?(m.kind==='photo'?'<img class="thumb" src="'+url+'" alt="">':'<div class="avatar" style="background:var(--surface2);color:var(--ink)">'+(m.kind==='voice'?'🎙️':'📎')+'</div>'):'<div class="avatar" style="background:var(--surface2);color:var(--ink)">'+ui.initials(m.title)+'</div>';
      html+='<div class="item">'+thumb+'<div class="grow"><h3>'+ui.esc(m.title)+'</h3>'
        +'<div class="meta">'+t('me.vault.kind.'+(m.kind||'note'))+(m.fileName?' · '+ui.esc(m.fileName):'')+(m.createdAt?' · '+ui.timeAgo(m.createdAt):'')+'</div>'
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
  if(pendingFile&&nameHint){ nameHint.textContent=t('me.vault.file',{name:pendingFile.name,kb:Math.round(pendingFile.size/1024)}); kindSel.value=kindFromFile(pendingFile); }
  if(fileInput){
    fileInput.onchange=()=>{
      pendingFile=fileInput.files&&fileInput.files[0]||null;
      if(pendingFile){
        nameHint.textContent=t('me.vault.file',{name:pendingFile.name,kb:Math.round(pendingFile.size/1024)});
        kindSel.value=kindFromFile(pendingFile);
        const title=el.querySelector('#memTitle');
        if(!title.value.trim()) title.value=pendingFile.name.replace(/\.[^.]+$/,'');
      }else{ nameHint.textContent=t('me.vault.any'); }
    };
  }
  el.querySelector('#memSave').onclick=()=>{
    const title=el.querySelector('#memTitle').value.trim();
    if(!title){ui.toast(t('me.vault.needTitle'));return;}
    const expStr=el.querySelector('#memExp').value;
    const m={id:store.uid(),kind:kindSel.value,title,note:el.querySelector('#memNote').value.trim(),createdAt:Date.now(),sample:false};
    if(pendingFile){ m.fileName=pendingFile.name; blobUrls[m.id]=URL.createObjectURL(pendingFile); }
    if(expStr){ const exp=new Date(expStr+'T12:00:00').getTime(); if(!isNaN(exp)) m.expiry=exp; }
    store.state.memory.unshift(m); store.save();
    pendingFile=null;
    rerender(); ui.toast(t('me.vault.saved'));
  };

  /* search */
  const sIn=el.querySelector('#memSearch');
  if(sIn){ sIn.oninput=()=>{ searchQ=sIn.value; const pos=sIn.selectionStart; rerender(); const el2=document.getElementById('view-me'); const n2=el2&&el2.querySelector('#memSearch'); if(n2){n2.focus();n2.setSelectionRange(pos,pos);} }; }

  /* delete */
  el.querySelectorAll('.memDel').forEach(b=>{ b.onclick=()=>{ const id=b.dataset.mid; if(blobUrls[id]){URL.revokeObjectURL(blobUrls[id]);delete blobUrls[id];} store.remove('memory',id); rerender(); ui.toast(t('me.vault.deleted')); }; });

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
          stream.getTracks().forEach(tr=>tr.stop());
          const blob=new Blob(recChunks,{type:rec.mimeType||'audio/webm'});
          const m={id:store.uid(),kind:'voice',title:t('me.vault.voiceTitle',{d:new Date().toLocaleString()}),note:'',createdAt:Date.now(),sample:false};
          blobUrls[m.id]=URL.createObjectURL(blob);
          store.state.memory.unshift(m); store.save();
          rec=null; rerender(); ui.toast(t('me.vault.voiceSaved'));
        };
        rec.start();
        recBtn.textContent='⏹️ Stop recording…';
        recBtn.onclick=()=>{ if(rec) rec.stop(); };
      }catch(e){ ui.toast(t('me.vault.noMic')); rec=null; }
    };
  }
}

/* ================= VERIFY SHEET (honest demo — kept) ================= */
function verifySheet(){
  const p=store.state.profile;
  ui.openSheet(
    '<h2>'+t('me.verify.title')+'</h2>'
    +'<div class="demo-note">'+t('me.verify.demo')+'</div>'
    +'<h3 style="margin:12px 0 8px">'+t('me.verify.opt1')+'</h3>'
    +'<div class="field"><label>'+t('me.verify.email')+'</label><input class="input" id="vEmail" type="email" placeholder="you@school.edu" value="'+ui.esc(p.email||'')+'"></div>'
    +'<button class="btn btn-line btn-block" id="vEmailGo" disabled>'+t('me.verify.sendCode')+'</button>'
    +'<h3 style="margin:16px 0 8px">'+t('me.verify.opt2')+'</h3>'
    +'<div class="field"><label>'+t('me.verify.phone')+'</label><input class="input" id="vPhone" type="tel" placeholder="+1 555-000-0000" value="'+ui.esc(p.phone||'')+'"></div>'
    +'<button class="btn btn-line btn-block" id="vSmsGo" disabled>'+t('me.verify.sendCode')+'</button>'
    +'<p class="hint" style="margin-top:12px">'+t('me.verify.disabled')+'</p>'
    +'<button class="btn btn-primary btn-block" id="vSave" style="margin-top:10px">'+t('me.verify.save')+'</button>'
    +(p.verified?'':'<button class="btn btn-line btn-block" id="vInstant" style="margin-top:10px">'+t('me.verify.instant')+'</button>')
  );
  document.getElementById('vSave').onclick=()=>{
    p.email=document.getElementById('vEmail').value.trim();
    p.phone=document.getElementById('vPhone').value.trim();
    store.save(); ui.closeSheet(); rerender();
    ui.toast(t('me.verify.saved'));
  };
  var vInst=document.getElementById('vInstant');
  if(vInst) vInst.onclick=()=>{
    p.verified=true; store.save(); ui.closeSheet(); rerender();
    ui.toast(t('me.verify.instantDone'));
  };
}

/* ================= REPORT SHEET (local, honest) ================= */
function reportSheet(){
  ui.openSheet(
    '<h2>'+t('me.report.title')+'</h2>'
    +'<p class="sub" style="margin-bottom:12px">'+t('me.report.sub')+'</p>'
    +'<div class="field"><label>'+t('me.report.kind')+'</label><select class="input" id="rpKind">'
    +['listing','job','user','post','other'].map(k=>'<option value="'+k+'">'+t('me.report.k.'+k)+'</option>').join('')+'</select></div>'
    +'<div class="field"><label>'+t('me.report.what')+'</label><input class="input" id="rpTitle" placeholder="'+ui.esc(t('me.report.whatPh'))+'" maxlength="80"></div>'
    +'<div class="field"><label>'+t('me.report.happened')+'</label><textarea class="textarea" id="rpReason" placeholder="'+ui.esc(t('me.report.happenedPh'))+'"></textarea></div>'
    +'<button class="btn btn-primary btn-block" id="rpSave">'+t('me.report.save')+'</button>'
  );
  document.getElementById('rpSave').onclick=()=>{
    const title=document.getElementById('rpTitle').value.trim();
    if(!title){ui.toast(t('me.report.need'));return;}
    store.state.reports.unshift({id:store.uid(),kind:document.getElementById('rpKind').value,title,
      reason:document.getElementById('rpReason').value.trim(),at:Date.now(),resolved:false,sample:false});
    store.save(); ui.closeSheet(); rerender();
    ui.toast(t('me.report.saved'));
  };
}

/* ================= SECTION BUILDERS ================= */
function secHead(iconName,emoji,title){
  const ic=icons(iconName);
  return '<div class="me-sec"><span class="me-secico">'+(ic||ui.esc(emoji))+'</span><h2>'+ui.esc(title)+'</h2></div>';
}

function renderHero(p,s){
  const av=AV_COLORS[Math.abs(p.avatarColor||0)%AV_COLORS.length];
  const badge=p.verified?ui.verifiedBadge():'<span class="badge b-unverified">'+t('me.unverified')+'</span>';
  const dealN=s.deals, comN=s.communities;
  const chips=
    '<div class="me-chip '+(p.verified?'me-chip-ok':'me-chip-warn')+'">'+(p.verified?ui.verifiedBadge():t('me.chip.unverified'))+'</div>'
    +'<div class="me-chip">🤝 '+t('me.deals',{n:dealN})+'</div>'
    +'<div class="me-chip">👥 '+t('me.communities',{n:comN})+'</div>'
    +'<div class="me-chip">'+(s.stars>0?t('me.stars',{n:s.stars}):t('me.noRatings'))+'</div>';
  const photoHtml=p.photo?'<img class="avimg" src="'+ui.esc(p.photo)+'" alt="">':ui.initials(p.name||'?');
  /* tier badges: gaming-style profile badges, tap to open the showcase. */
  const bdgHtml=(HUB.badges&&HUB.badges.headerHTML)?HUB.badges.headerHTML(p):'';
  return '<div class="card me-hero">'
    +'<button class="btn btn-line btn-sm me-editbtn" id="meEditBtn">✎ '+t('pedit.edit')+'</button>'
    +'<div class="me-avatar" style="--me-ac:'+av+'">'+photoHtml+'</div>'
    +'<div class="me-namerow"><h1 class="me-name">'+ui.esc(p.name||t('me.noName'))+'</h1>'+bdgHtml+'</div>'
    +'<div class="me-campus">'+comEmoji(p)+' '+ui.esc(p.campus||t('me.noCommunity'))+'</div>'
    +(p.bio?'<p class="me-bio">'+ui.esc(p.bio)+'</p>':'')
    +'<div class="me-badgerow">'+badge+' <span class="stars">'+ui.stars(s.stars)+'</span></div>'
    +'<div class="me-ribbon" role="list" aria-label="'+ui.esc(t('me.rep.title'))+'">'+chips+'</div>'
    +scoreStrip(p,s)
    +'</div>';
}

/* tappable safety-score strip (lives just under the ribbon, inside the hero) */
function scoreStrip(p,s){
  const sc=safetyScore(p,s);
  const band=sc.score>=75?'me-score-high':(sc.score>=50?'me-score-mid':'me-score-low');
  return '<button class="me-score '+band+'" id="meScoreStrip" aria-label="'+ui.esc(t('me.score.aria',{n:sc.score}))+'">'
    +'<span class="me-score-num" aria-hidden="true">'+sc.score+'</span>'
    +'<span class="me-score-body">'
    +'<span class="me-score-label">'+t('me.score.label')+'</span>'
    +'<span class="me-score-bar" aria-hidden="true"><span style="width:'+sc.score+'%"></span></span>'
    +'<span class="me-score-note">'+t('me.score.note')+'</span>'
    +'</span>'
    +'<span class="me-score-chev" aria-hidden="true">›</span>'
    +'</button>';
}

/* ================= PROFILE EDITING =================
   "Edit profile" sheet (PraBin's ask): photo (downscaled dataURL, kept in
   localStorage — browser-only, honest note in the sheet), name, bio,
   school/community (the existing world institution picker), skills.
   Verification state is NEVER touched here; the honest "needs the production
   backend" verification note stays exactly as it is. */
let pedit={photo:null,photoTouched:false,campusRec:null};

function applyCampusRec(p,rec){
  p.campus=rec.name; p.campusSample=!!rec.sample; p.campusKind=rec.kind||'';
  if(!rec.sample&&rec.lat!=null&&rec.lng!=null&&isFinite(rec.lat)&&isFinite(rec.lng)){ p.campusCoords=[rec.lat,rec.lng]; p.campusIso=rec.iso||''; p.campusCity=rec.city||''; }
  else { delete p.campusCoords; delete p.campusIso; delete p.campusCity; }
}

function downscalePhoto(file,cb){
  const url=URL.createObjectURL(file);
  const img=new Image();
  img.onload=()=>{
    URL.revokeObjectURL(url);
    const mx=512, sc=Math.min(1,mx/Math.max(img.width||1,img.height||1));
    const w=Math.max(1,Math.round(img.width*sc)), h=Math.max(1,Math.round(img.height*sc));
    const cv=document.createElement('canvas'); cv.width=w; cv.height=h;
    cv.getContext('2d').drawImage(img,0,0,w,h);
    try{ cb(cv.toDataURL('image/jpeg',0.85)); }catch(e){ ui.toast(t('pedit.photoErr')); }
  };
  img.onerror=()=>{ URL.revokeObjectURL(url); ui.toast(t('pedit.photoErr')); };
  img.src=url;
}

function editSheet(){
  const p=store.state.profile;
  /* fresh from profile on every open — EXCEPT the campus-picker reopen, which
     must keep the pending toggle flip */
  if(!pedit._keepPub) pedit.pubOn=!!p.publicProfile;
  pedit._keepPub=false;
  /* gender: pending selection survives the campus-picker sheet reopen */
  if(!pedit._keepGender) pedit.gender=p.gender||'';
  pedit._keepGender=false;
  const curPhoto=pedit.photoTouched?pedit.photo:(p.photo||null);
  const campusName=pedit.campusRec?pedit.campusRec.name:(p.campus||'');
  const avc=AV_COLORS[Math.abs(p.avatarColor||0)%AV_COLORS.length];
  const prevInner=curPhoto?'<img class="avimg" src="'+ui.esc(curPhoto)+'" alt="">':ui.initials((document.getElementById('peditName')||{}).value||p.name||'?');
  ui.openSheet(
    '<h2>'+t('pedit.title')+'</h2>'
    +'<div class="demo-note" style="margin-top:8px">'+t('pedit.browserNote')+'</div>'
    +'<div class="pedit-photo"><div class="me-avatar" id="peditPrev" style="--me-ac:'+avc+'">'+prevInner+'</div>'
    +'<div><label class="btn btn-line btn-sm" style="cursor:pointer">'+t('pedit.choosePhoto')+'<input type="file" class="hiddenfile" id="peditFile" accept="image/*"></label>'
    +(curPhoto?' <button class="btn btn-ghost btn-sm" id="peditRemove">'+t('pedit.removePhoto')+'</button>':'')+'</div></div>'
    +'<div class="field"><label>'+t('pedit.name')+'</label><input class="input" id="peditName" maxlength="60" value="'+ui.esc(p.name||'')+'"></div>'
    +'<div class="field"><label>'+t('pedit.gender')+'</label><div class="seg" id="peditGender" role="radiogroup">'+genderSegHTML(pedit.gender||'')+'</div></div>'
    +'<div class="field"><label>'+t('pedit.bio')+'</label><textarea class="textarea" id="peditBio" maxlength="160" placeholder="'+ui.esc(t('pedit.bioPh'))+'">'+ui.esc(p.bio||'')+'</textarea></div>'
    +'<div class="field"><label>'+t(p.audience==='community'?'pedit.community':'pedit.school')+'</label>'
    +'<button class="btn btn-line btn-block" id="peditCampus" style="justify-content:flex-start;text-align:left"><span class="grow">'+ui.esc(campusName||t('pedit.pick'))+'</span><span aria-hidden="true">›</span></button></div>'
    +'<div class="field"><label>'+t('pedit.skills')+'</label><input class="input" id="peditSkills" maxlength="200" placeholder="'+ui.esc(t('pedit.skillsPh'))+'" value="'+ui.esc((p.skills||[]).join(', '))+'"></div>'
    +'<div class="field"><label>'+t('pedit.major')+'</label><input class="input" id="peditMajor" maxlength="60" placeholder="'+ui.esc(t('pedit.majorPh'))+'" value="'+ui.esc(p.major||'')+'"></div>'
    +'<div class="field"><label>'+t('pedit.year')+'</label><input class="input" id="peditYear" maxlength="30" placeholder="'+ui.esc(t('pedit.yearPh'))+'" value="'+ui.esc(p.year||'')+'"></div>'
    +'<div class="kv" style="margin-top:2px"><span><strong>'+t('pedit.pubProf')+'</strong><br><span class="meta">'+t('pedit.pubHint')+'</span></span>'
    +'<div class="toggle'+(pedit.pubOn?' on':'')+'" id="peditPub" role="switch" aria-checked="'+(!!pedit.pubOn)+'" tabindex="0" aria-label="'+ui.esc(t('pedit.pubProf'))+'"></div></div>'
    +'<div class="field"><label>'+t('pedit.dob')+'</label><input class="input" type="date" id="peditDob" value="'+ui.esc(p.dob||'')+'" max="2016-12-31"><div class="hint">'+ui.esc(t('pedit.dobHint'))+'</div></div>'
    +'<div class="row" style="gap:8px;margin-top:14px"><button class="btn btn-ghost grow" id="peditCancel">'+t('common.cancel')+'</button>'
    +'<button class="btn btn-primary grow" id="peditSave">'+t('common.save')+'</button></div>'
  );
  const prev=document.getElementById('peditPrev');
  document.getElementById('peditFile').onchange=e=>{
    const f=e.target.files&&e.target.files[0]; if(!f) return;
    downscalePhoto(f,url=>{ pedit.photo=url; pedit.photoTouched=true; prev.innerHTML='<img class="avimg" src="'+ui.esc(url)+'" alt="">'; });
  };
  const rm=document.getElementById('peditRemove');
  if(rm) rm.onclick=()=>{ pedit.photo=null; pedit.photoTouched=true; prev.innerHTML=ui.initials(document.getElementById('peditName').value||p.name||'?'); };
  document.getElementById('peditCampus').onclick=()=>{
    /* the institution picker closes this sheet; reopen it with pending state kept */
    ui.openInstitutionPicker({mode:p.audience==='community'?'community':'student',onPick:rec=>{ pedit.campusRec=rec; pedit._keepPub=true; pedit._keepGender=true; editSheet(); }});
  };
  const gdRoot=document.getElementById('peditGender');
  if(gdRoot) gdRoot.querySelectorAll('button').forEach(b=>{ b.onclick=()=>{ pedit.gender=b.dataset.g;
    gdRoot.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b)); }; });
  document.getElementById('peditCancel').onclick=()=>ui.closeSheet();
  /* public-profile toggle: default OFF; only ON shows the user's head in the Home people row */
  const pubT=document.getElementById('peditPub');
  const flipPub=()=>{ pedit.pubOn=!pedit.pubOn; pubT.classList.toggle('on',pedit.pubOn); pubT.setAttribute('aria-checked',String(pedit.pubOn)); };
  if(pubT){ pubT.onclick=flipPub; pubT.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flipPub(); } }; }
  document.getElementById('peditSave').onclick=()=>{
    const nameEl=document.getElementById('peditName');
    const name=nameEl.value.trim();
    if(!name){ ui.toast(t('pedit.nameNeed')); nameEl.focus(); return; }
    const oldName=store.myName();
    p.name=name;
    p.bio=document.getElementById('peditBio').value.trim().slice(0,160);
    const dobEl=document.getElementById('peditDob');
    const dob=dobEl?dobEl.value:'';
    if(dob) p.dob=dob; else delete p.dob; // drives zodiac + daily horoscope
    if(pedit.photoTouched){ if(pedit.photo) p.photo=pedit.photo; else delete p.photo; }
    if(pedit.campusRec) applyCampusRec(p,pedit.campusRec);
    const seen={}; p.skills=[];
    document.getElementById('peditSkills').value.split(',').forEach(s=>{
      s=s.trim().slice(0,40); const k=s.toLowerCase();
      if(s&&!seen[k]){ seen[k]=1; p.skills.push(s); }
    });
    p.major=document.getElementById('peditMajor').value.trim().slice(0,60);
    p.year=document.getElementById('peditYear').value.trim().slice(0,30);
    if(pedit.gender) p.gender=pedit.gender; /* drives the ME tab icon */
    p.publicProfile=!!pedit.pubOn; /* default OFF: own head stays out of the Home people row */
    /* keep the user's own content consistent when the display name changes */
    if(oldName&&oldName!==name){
      store.state.listings.forEach(l=>{ if(l.seller===oldName) l.seller=name; });
      (store.state.listings||[]).forEach(l=>{ (l.comments||[]).forEach(c=>{ if(c.author===oldName) c.author=name; }); });
      store.state.jobs.forEach(j=>{ if(j.poster===oldName) j.poster=name; if(j.acceptedBy===oldName) j.acceptedBy=name; });
    }
    store.save(); ui.closeSheet(); rerender();
    if(HUB.paintChrome) HUB.paintChrome(); /* gender may have changed the ME tab icon */
    if(HUB.theme) HUB.theme.apply(true); /* gender may have flipped volt<->rose: water-flow transition */
    ui.toast(t('pedit.saved'));
  };
}

/* explainer sheet: the exact formula, with this user's real numbers plugged in */
function scoreSheet(){
  const p=store.state.profile, s=stats(); s.me=store.myName();
  const sc=safetyScore(p,s);
  ui.openSheet(
    '<h2>'+t('me.scoreSheet.title')+'</h2>'
    +'<div class="demo-note" style="margin-top:8px">'+t('me.scoreSheet.demo')+'</div>'
    +'<h3 style="margin:14px 0 4px">'+t('me.scoreSheet.formula')+'</h3>'
    +'<p class="sub" style="margin-bottom:10px">'+t('me.scoreSheet.formulaT')+'</p>'
    +'<p class="sub" style="margin-bottom:8px">'+t('me.scoreSheet.dealDef')+'</p>'
    +sc.parts.map(pt=>'<div class="kv"><span>'+ui.esc(pt.label)+'<br><span class="meta">'+ui.esc(pt.detail)+'</span></span><strong>'+(pt.pts>0?'+':'')+pt.pts+'</strong></div>').join('')
    +'<div class="kv"><span><strong>'+t('me.score.yours')+'</strong></span><strong>'+t('me.score.outOf',{n:sc.score})+'</strong></div>'
    +'<div class="divider"></div>'
    +'<p class="sub">'+t('me.score.raise')+'</p>'
  );
}

function renderRepGrid(s){
  const card=(iconName,emoji,num,label,hint)=>'<div class="me-repcard"><span class="me-repico">'+(icons(iconName)||ui.esc(emoji))+'</span>'
    +'<div class="me-repnum">'+num+'</div><div class="me-replabel">'+ui.esc(label)+'</div>'
    +(hint?'<div class="me-rephint">'+ui.esc(hint)+'</div>':'')+'</div>';
  const ratings=s.stars>0?t('me.stars',{n:s.stars}):t('me.rep.noRatings');
  return secHead('stat-money','💰',t('me.rep.title'))
    +'<div class="me-repgrid">'
    +card('act-job','💼',(store.state.profile.jobsDone||0),t('me.rep.jobs'),'')
    +card('act-sell','🏷️',s.myRealListings.length,t('me.rep.exchanges'),t('me.rep.exchangesH'))
    +card('nav-groups','👥',s.communities,t('me.rep.communities'),t('me.rep.communitiesH'))
    +card('','★',ratings,t('me.rep.ratings'),s.stars>0?t('me.rep.ratingsH'):t('me.rep.noRatingsH'))
    +'</div>';
}

function renderSkills(p){
  const skills=p.skills||[];
  let body;
  if(!skills.length){
    body='<p class="sub me-skills-empty">'+t('me.skills.empty')+'</p>';
  }else{
    body='<div class="me-skills">'+skills.map((sk,i)=>'<span class="me-skill">'+ui.esc(sk)+'<button class="me-skill-x" data-skill="'+i+'" aria-label="'+ui.esc(t('me.skills.remove',{s:sk}))+'">✕</button></span>').join('')+'</div>';
  }
  return secHead('act-task','📋',t('me.skills.title'))
    +'<div class="card">'+body
    +'<div class="me-skill-add"><input class="input" id="meSkillInput" placeholder="'+ui.esc(t('me.skills.ph'))+'" maxlength="40"><button class="btn btn-primary" id="meSkillAdd">'+t('me.skills.add')+'</button></div>'
    +'</div>';
}

function renderCommunities(p){
  const hs=store.state.households||[];
  let hh=hs.length? hs.map(h=>{
    const mems=(h.members||[]);
    return '<div class="me-comrow"><div class="me-comicon">🏠</div><div class="grow"><h3>'+ui.esc(h.name||t('me.com.householdFallback'))+ui.sampleBadge(h.sample)+'</h3>'
      +'<div class="meta">'+t('me.com.members',{n:mems.length})+(mems.length?' · '+ui.esc(mems.slice(0,4).join(', '))+(mems.length>4?'…':''):'')+'</div></div></div>';
  }).join('')
    :'<p class="sub">'+t('me.com.noHh')+'</p>';
  return secHead('nav-groups','👥',t('me.com.title'))
    +'<div class="card">'
    +'<div class="me-comrow"><div class="me-comicon">'+comEmoji(p)+'</div><div class="grow"><h3>'+t('me.com.h')+'</h3><div class="meta">'+t('me.com.hD')+'</div></div>'
    +'<button class="btn btn-line btn-sm" id="meCampusBtn" style="max-width:170px" aria-label="'+ui.esc(t('me.com.change'))+'">'+ui.esc(p.campus||t('me.com.change'))+'</button></div>'
    +'<p class="hint" style="margin:8px 0 0">'+t('me.com.sampleNote')+'</p>'
    +'<div class="divider"></div>'
    +'<h3 style="margin-bottom:8px">'+t('me.com.hh',{n:hs.length})+'</h3>'+hh
    +'</div>';
}

function renderActivity(s){
  const items=[];
  const me=s.me;
  for(const l of store.state.listings) if(l.seller===me)
    items.push({ic:'act-sell',fb:'🏷️',t:t('me.act.listed',{t:l.title}),m:((l.type||'').toLowerCase()||t('me.tx.chip.listing'))+' · '+ui.timeAgo(l.createdAt||Date.now()),at:l.createdAt||0,sample:l.sample});
  for(const j of store.state.jobs){
    if(j.poster===me) items.push({ic:'act-job',fb:'💼',t:t('me.act.postedJob',{t:j.title}),m:(j.status||'open')+' · '+ui.fmt$(j.pay||0)+' · '+ui.timeAgo(j.createdAt||Date.now()),at:j.createdAt||0,sample:j.sample});
    else if(j.acceptedBy===me) items.push({ic:'act-job',fb:'💼',t:t('me.act.acceptedJob',{t:j.title}),m:(j.status||'open')+' · '+ui.fmt$(j.pay||0)+' · '+ui.timeAgo(j.createdAt||Date.now()),at:j.createdAt||0,sample:j.sample});
  }
  for(const m of store.state.memory)
    items.push({ic:'act-memory',fb:'🧠',t:t('me.act.vault',{t:m.title}),m:t('me.vault.kind.'+(m.kind||'note'))+' · '+ui.timeAgo(m.createdAt||Date.now()),at:m.createdAt||0,sample:m.sample});
  for(const c of (store.state.campusPosts||[])) if(c.author===me)
    items.push({ic:'act-post',fb:'📣',t:t('me.act.postedCommunity'),m:ui.timeAgo(c.at||Date.now()),at:c.at||0,sample:c.sample});
  items.sort((a,b)=>b.at-a.at);
  const top=items.slice(0,10);

  let body;
  if(!top.length){
    body='<div class="empty"><div class="big">🕰️</div><p>'+t('me.act.empty')+'</p></div>'
      +'<div class="me-act-cta"><button class="btn btn-line" id="meGoMarket">'+t('me.act.market')+'</button><button class="btn btn-line" id="meGoWork">'+t('me.act.work')+'</button></div>';
  }else{
    body=top.map(a=>'<div class="me-act"><span class="me-acticon">'+(icons(a.ic)||ui.esc(a.fb))+'</span>'
      +'<div class="grow"><h3>'+ui.esc(a.t)+'</h3><div class="meta">'+ui.esc(a.m)+'</div></div>'
      +ui.sampleBadge(a.sample)+'</div>').join('');
  }
  return secHead('ic-pulse','⚡',t('me.act.title'))+'<div class="card">'+body+'</div>';
}

/* ---- TRANSACTION / EXCHANGE HISTORY: real local activity only ----
   My listings (posted), jobs I've posted or accepted, completed exchanges.
   Each row: icon, title, type chip (Listing/Job), time-ago, status. Sample
   items carry Sample badges. Honest empty state with redirect. */
function renderTransactions(s){
  const me=s.me;
  const items=[];
  for(const l of store.state.listings) if(l.seller===me)
    items.push({ic:'act-sell',fb:'🏷️',t:l.title||t('me.tx.chip.listing'),chip:t('me.tx.chip.listing'),chipCls:'b-SELL',
      m:t('me.tx.listed',{ago:ui.timeAgo(l.createdAt||Date.now()),price:l.price?' · '+ui.fmt$(l.price):''}),
      at:l.createdAt||0,sample:l.sample});
  for(const j of store.state.jobs){
    const jm=' · '+ui.fmt$(j.pay||0)+' · '+(j.status||'open')+' · '+ui.timeAgo(j.createdAt||Date.now());
    if(j.poster===me) items.push({ic:'act-job',fb:'💼',t:j.title||t('me.tx.chip.job'),chip:t('me.tx.chip.job'),chipCls:'b-job',
      m:t('me.tx.posted',{rest:jm}),at:j.createdAt||0,sample:j.sample});
    else if(j.acceptedBy===me) items.push({ic:'act-job',fb:'💼',t:j.title||t('me.tx.chip.job'),chip:t('me.tx.chip.job'),chipCls:'b-job',
      m:t('me.tx.accepted',{rest:jm}),at:j.createdAt||0,sample:j.sample});
  }
  items.sort((a,b)=>b.at-a.at);

  let body;
  if(!items.length){
    body='<div class="empty"><div class="big">🧾</div><p>'+t('me.tx.empty')+'</p></div>'
      +'<div class="me-act-cta"><button class="btn btn-primary" id="meGoList">'+t('me.tx.first')+'</button><button class="btn btn-line" id="meGoWork2">'+t('me.act.work')+'</button></div>';
  }else{
    body=items.map(a=>'<div class="me-act"><span class="me-acticon">'+(icons(a.ic)||ui.esc(a.fb))+'</span>'
      +'<div class="grow"><h3>'+ui.esc(a.t)+'</h3><div class="meta">'+ui.esc(a.m)+'</div></div>'
      +ui.sampleBadge(a.sample)+'<span class="badge '+a.chipCls+'">'+a.chip+'</span></div>').join('');
  }
  return secHead('act-expense','🧾',t('me.tx.title'))+'<div class="card">'+body+'</div>';
}

function renderVerification(p){
  const row=(label,val)=>'<div class="kv"><span>'+label+'</span><span class="meta">'+(val?ui.esc(val):t('me.verify.notSet'))+'</span></div>';
  return secHead('wl-shield','✅',t('me.verify.secTitle'))
    +'<div class="card">'
    +row(t('me.verify.rowEmail'),p.email)+row(t('me.verify.rowPhone'),p.phone)
    +'<button class="btn btn-primary btn-block" id="verifyBtn" style="margin-top:10px">'+(p.verified?t('me.verify.manage'):t('me.verify.title'))+'</button>'
    +(p.verified?'':'<p class="hint" style="margin-top:8px">'+t('me.verify.hint')+'</p>')
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
  const discRow='<div class="divider"></div><h3 style="margin-bottom:6px">'+t('me.safety.disc')+'</h3>'
    +'<div class="item" style="cursor:default">'
    +'<div class="grow"><h3>'+t('me.safety.discT',{scope:student?t('me.safety.scopeSchool'):t('me.safety.scopeCommunity')})+'</h3>'
    +'<div class="meta">'+t('me.safety.discD',{at:p.campus?t('me.safety.discAt',{c:p.campus}):''})+'</div></div>'
    +'<div class="toggle'+(discOn?' on':'')+'" id="discToggle" role="switch" aria-checked="'+(discOn?'true':'false')+'" tabindex="0" aria-label="'+ui.esc(t('me.safety.discAria'))+'"></div>'
    +'</div>'
    +'<p class="hint" style="margin-top:8px">'+t('me.safety.discH')+'</p>';
  return secHead('wl-shield','🛡️',t('me.safety.title'))
    +'<div class="card">'
    +'<div class="kv"><span>'+t('me.safety.report')+'</span><button class="btn btn-sm btn-line" id="meReport">'+t('me.safety.reportBtn')+'</button></div>'
    +'<div class="kv"><span>'+t('me.safety.modq')+'</span><button class="btn btn-sm btn-line" id="meModQ">'+t('me.safety.review')+(openReports?' '+t('me.safety.openN',{n:openReports}):'')+'</button></div>'
    +'<div class="kv"><span>'+t('me.safety.blocked')+'</span><button class="btn btn-sm btn-line" id="meBlocked">'+t('me.safety.manage',{n:nBlocked})+'</button></div>'
    +(HUB.trust?'<div class="divider"></div><h3 style="margin-bottom:6px">'+t('me.safety.privacy')+'</h3>'+HUB.trust.privacySettingsHTML():'')
    +discRow
    +'</div>';
}

function renderSettings(){
  const i18n=HUB.i18n;
  const cc=i18n.countryByCode(i18n.getCountry()||i18n.guessCountry()||'US');
  const cname=i18n.countryName(cc,i18n.getLang())||'US';
  const lname=(i18n.LOCALES[i18n.getLang()]||i18n.LOCALES.en).native;
  /* glossy grouped settings (redesign): row labels reuse the existing me.set.*
     keys; the leading emoji is stripped because each row now carries a 3D
     clay icon tile instead. */
  const noEm=s=>{ s=String(s); return /^[^ -~]/.test(s)?s.replace(/^[^\s]+\s/,''):s; };
  const sic=(n,fb)=>'<span class="me-setico">'+(icons(n)||ui.esc(fb))+'</span>';
  const trow=(id,icon,fb,label,on)=>'<div class="kv"><span class="me-setlab">'+sic(icon,fb)+'<span class="me-settx">'+label+'</span></span>'
    +'<div class="toggle'+(on?' on':'')+'" id="'+id+'" role="switch" aria-checked="'+(!!on)+'" tabindex="0" aria-label="'+ui.esc(label)+'"></div></div>';
  const brow=(icon,fb,label,btn)=>'<div class="kv"><span class="me-setlab">'+sic(icon,fb)+'<span class="me-settx">'+label+'</span></span>'+btn+'</div>';
  const grp=k=>'<div class="me-setgroup">'+t(k)+'</div>';
  return secHead('calc-set','⚙️',t('me.set.title'))
    +'<div class="card me-setcard">'+grp('me.set.gAppearance')
    +trow('soundToggle','calc-snd-on','🔊',t('me.set.sound'),store.state.prefs.soundOn!==false)
    +'<div class="kv me-setring"><span class="me-setlab">'+sic('wl-sparkle','✨')+'<span class="me-settx">'+t('me.set.ringtone')+'</span></span><div id="ringList" style="flex:1;min-width:0;display:flex;flex-direction:column;gap:6px"></div></div>'
    +'<p class="hint">'+t('me.set.soundNote')+'</p>'
    +brow('subj-language','🌐',noEm(t('me.set.language')),'<button class="btn btn-sm btn-line" id="meLangBtn">'+ui.esc(lname)+'</button>')
    +brow('nav-discover','📍',noEm(t('me.set.country')),'<button class="btn btn-sm btn-line" id="meCountryBtn">'+ui.esc(cname)+'</button>')
    +'<p class="hint">'+t('me.set.countryNote')+'</p>'
    +'</div>'
    +'<div class="card me-setcard">'+grp('me.set.gNotify')
    +trow('pushToggle','wl-bell','🔔',t('push.title'),!!store.state.prefs.pushOn)
    +'<p class="hint">'+t('push.sub')+'</p>'
    +'</div>'
    +'<div class="card me-setcard">'+grp('me.set.gData')
    +brow('stat-docs','📄',t('me.set.clear'),'<button class="btn btn-sm btn-line" id="clearSamples">'+t('me.set.clearBtn')+'</button>')
    +'</div>';
}

/* ================= ringtone picker (preview + custom file) ================= */
let ringPrevKey=null;        /* which ringtone is previewing right now (me.js mirror) */
let ringCustomName=null;     /* filename of the stored custom ringtone, null if none */
let ringCustomReady=false;   /* IndexedDB check finished */
let ringEndHooked=false;

function ringRowHtml(key,label,sub,sel){
  const checked=sel===key;
  const playing=ringPrevKey===key;
  return '<div class="ringrow" data-ring="'+key+'" role="radio" tabindex="0" aria-checked="'+(checked?'true':'false')+'" aria-label="'+ui.esc(label)+'">'
    +'<span class="ringdot" aria-hidden="true"></span>'
    +'<span class="ringname">'+ui.esc(label)+(sub?'<span class="ringfile">'+ui.esc(sub)+'</span>':'')+'</span>'
    +'<button class="ringpv'+(playing?' playing':'')+'" data-pv="1" aria-label="'+ui.esc((playing?t('me.set.ringStop'):t('me.set.ringPreview'))+' '+label)+'">'+(playing?'⏹':'▶')+'</button>'
    +'</div>';
}
function renderRingList(){
  const host=document.getElementById('ringList');
  if(!host||!HUB.sound) return;
  const sel=HUB.sound.getRingtone();
  let html=ringRowHtml('aurora',t('me.set.ringAurora'),null,sel)
    +ringRowHtml('breeze',t('me.set.ringBreeze'),null,sel)
    +ringRowHtml('phone','Classic Phone',null,sel);
  if(ringCustomReady&&ringCustomName){
    html+=ringRowHtml('custom',t('me.set.ringMy'),ringCustomName,sel)
      +'<div style="display:flex;gap:8px;flex-wrap:wrap">'
      +'<button class="btn btn-sm btn-line" id="ringReplaceBtn" style="min-height:44px">'+ui.esc(t('me.set.ringReplace'))+'</button>'
      +'<button class="btn btn-sm btn-line" id="ringRemoveBtn" style="min-height:44px">'+ui.esc(t('me.set.ringRemove'))+'</button>'
      +'</div>';
  }else if(ringCustomReady){
    html+='<button class="btn btn-sm btn-line" id="ringAddBtn" style="align-self:flex-start;min-height:44px">+ '+ui.esc(t('me.set.ringAdd'))+'</button>';
  }
  html+='<p class="hint" style="margin:2px 0 0">'+t('me.set.ringFilesNote')+'</p>';
  host.innerHTML=html;
  host.querySelectorAll('[data-ring]').forEach(function(row){
    const key=row.getAttribute('data-ring');
    row.onclick=function(){ selectRing(key); };
    row.onkeydown=function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); selectRing(key); } };
    const pv=row.querySelector('[data-pv]');
    if(pv) pv.onclick=function(ev){ ev.stopPropagation(); togglePreview(key); };
  });
  const add=host.querySelector('#ringAddBtn');
  if(add) add.onclick=function(){ openRingFile(); };
  const rep=host.querySelector('#ringReplaceBtn');
  if(rep) rep.onclick=function(ev){ ev.stopPropagation(); openRingFile(); };
  const rm=host.querySelector('#ringRemoveBtn');
  if(rm) rm.onclick=function(ev){ ev.stopPropagation(); removeCustomRing(); };
}
function selectRing(key){
  if(!HUB.sound) return;
  if(HUB.sound.previewing()) HUB.sound.stopPreview();
  ringPrevKey=null;
  HUB.sound.setRingtone(key);
  renderRingList();
}
function togglePreview(key){
  if(!HUB.sound) return;
  const st=HUB.sound.preview(key); /* sound.js toasts honestly when sound is off */
  ringPrevKey=(st==='playing')?key:null;
  renderRingList();
}
function openRingFile(){
  let inp=document.getElementById('ringFileInp');
  if(!inp){
    inp=document.createElement('input');
    inp.type='file'; inp.id='ringFileInp'; inp.accept='audio/*'; inp.hidden=true;
    inp.onchange=function(){
      const f=inp.files&&inp.files[0];
      inp.value='';
      if(!f||!HUB.sound) return;
      HUB.sound.setCustom(f).then(function(){
        ringCustomName=HUB.sound.customName();
        ui.toast(t('me.set.ringSaved'));
        HUB.sound.setRingtone('custom');
        renderRingList();
      }).catch(function(err){
        ui.toast(err&&err.tooBig?t('me.set.ringTooBig'):t('me.set.ringBadFile'));
      });
    };
    document.body.appendChild(inp);
  }
  inp.click();
}
function removeCustomRing(){
  if(!HUB.sound) return;
  HUB.sound.removeCustom().then(function(){
    ringCustomName=null;
    if(HUB.sound.previewing()==='custom'){ HUB.sound.stopPreview(); ringPrevKey=null; }
    ui.toast(t('me.set.ringRemoved'));
    renderRingList();
  });
}
function ringInit(){
  if(!HUB.sound) return;
  if(!ringEndHooked){
    ringEndHooked=true;
    HUB.sound.onPreviewEnd(function(){ ringPrevKey=null; renderRingList(); });
  }
  ringCustomReady=false; ringCustomName=null;
  renderRingList();
  HUB.sound.hasCustom().then(function(ok){
    ringCustomReady=true;
    ringCustomName=ok?HUB.sound.customName():null;
    renderRingList();
  }).catch(function(){ ringCustomReady=true; renderRingList(); });
}

/* ================= VIEW ================= */
/* Gender-aware ME tab icon (PraBin's ask): female->girl bust, other->3D rainbow,
   na (prefer not to say)->ninja boy; male/unset legacy profiles keep the boy. */
function tabIconName(){
  const g=store.state.profile&&store.state.profile.gender;
  return g==='female'?'nav-me-girl':g==='other'?'nav-me-rainbow':g==='na'?'nav-me-ninja':'nav-me';
}
function genderSegHTML(cur){
  const opts=[['male','me.gender.male'],['female','me.gender.female'],['other','me.gender.other'],['na','me.gender.na']];
  return opts.map(o=>'<button type="button" data-g="'+o[0]+'" class="'+(cur===o[0]?'on':'')+'">'+t(o[1])+'</button>').join('');
}
HUB.me={tabIconName:tabIconName};
HUB.views.me={ render(el){
  const p=store.state.profile;
  if(!Array.isArray(p.skills)) p.skills=[];
  const s=stats(); s.me=store.myName();

  let html=renderHero(p,s)
    +(HUB.auth?HUB.auth.accountCardHTML():'')
    +renderRepGrid(s)
    +renderSkills(p)
    +renderCommunities(p)
    +renderActivity(s)
    +renderTransactions(s)
    +'<div id="vaultHost">'+renderVault()+'</div>'
    +renderVerification(p)
    +renderSafety()
    +renderSettings()
    +'<div class="demo-note">'+t('me.demoNote')+'<br><span style="opacity:.75">'+t('me.tagline')+'</span></div>'
    +'<div class="card" style="border-color:var(--danger)"><h2 style="margin-bottom:10px;color:var(--danger)">'+t('me.danger')+'</h2>'
    +'<button class="btn btn-block" id="resetAll" style="background:var(--danger);color:#fff">'+t('me.reset')+'</button>'
    +'<p class="hint">'+t('me.resetHint')+'</p></div>';

  el.innerHTML=html;

  document.getElementById('verifyBtn').onclick=verifySheet;
  wireVault(el);
  /* auth account card (login / signup / logout / Face ID) */
  if(HUB.auth) HUB.auth.wireAccountCard();

  /* profile editing */
  document.getElementById('meEditBtn').onclick=()=>{ pedit={photo:null,photoTouched:false,campusRec:null}; editSheet(); };
  /* tier badges -> showcase sheet */
  const mbBtn=document.getElementById('meBadges');
  if(mbBtn&&HUB.badges) mbBtn.onclick=()=>{ HUB.badges.openShowcase(); };

  /* skills */
  const addSkill=()=>{
    const inp=document.getElementById('meSkillInput');
    const v=inp.value.trim();
    if(!v){ui.toast(t('me.skills.need'));return;}
    if(p.skills.some(sk=>sk.toLowerCase()===v.toLowerCase())){ui.toast(t('me.skills.dup'));return;}
    p.skills.push(v.slice(0,40)); store.save(); rerender(); ui.toast(t('me.skills.added'));
  };
  document.getElementById('meSkillAdd').onclick=addSkill;
  document.getElementById('meSkillInput').onkeydown=e=>{ if(e.key==='Enter') addSkill(); };
  el.querySelectorAll('[data-skill]').forEach(b=>{ b.onclick=()=>{ p.skills.splice(Number(b.dataset.skill),1); store.save(); rerender(); }; });

  /* community + households */
  document.getElementById('meCampusBtn').onclick=()=>{
    ui.openInstitutionPicker({mode:ui.isCampusCommunity(p.campus)?'student':'community',onPick:rec=>{
      applyCampusRec(p,rec);
      store.save(); rerender(); ui.toast(t('intl.mapCenterSet',{name:rec.name}));
    }});
  };

  /* safety score explainer */
  const mss=document.getElementById('meScoreStrip');
  if(mss){ mss.onclick=scoreSheet; mss.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); scoreSheet(); } }; }

  /* activity + transaction-history empty-state redirects */
  const gm=document.getElementById('meGoMarket'); if(gm) gm.onclick=()=>HUB.showTab('market');
  const gw=document.getElementById('meGoWork'); if(gw) gw.onclick=()=>HUB.showTab('work');
  const mgl=document.getElementById('meGoList'); if(mgl) mgl.onclick=()=>HUB.showTab('market');
  const mgw2=document.getElementById('meGoWork2'); if(mgw2) mgw2.onclick=()=>HUB.showTab('work');

  /* settings */
  const mlb=document.getElementById('meLangBtn');
  if(mlb) mlb.onclick=()=>HUB.i18n.openLanguagePicker();
  const mcb=document.getElementById('meCountryBtn');
  if(mcb) mcb.onclick=()=>HUB.i18n.openCountryPicker(()=>rerender());
  /* sound on/off (Workstream: original Onaro ringtone + notification chime) */
  const st=document.getElementById('soundToggle');
  if(st){
    const flipSound=()=>{ const v=!st.classList.contains('on'); st.classList.toggle('on',v); st.setAttribute('aria-checked',String(v)); if(HUB.sound) HUB.sound.setOn(v); };
    st.onclick=flipSound;
    st.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flipSound(); } };
  }
  /* call notifications (Web Push groundwork): needs home-screen install +
     notification permission + the signaling worker — degrades honestly */
  const pt=document.getElementById('pushToggle');
  if(pt){
    const flipPush=()=>{ const want=!pt.classList.contains('on');
      const apply=v=>{ pt.classList.toggle('on',v); pt.setAttribute('aria-checked',String(v)); };
      if(HUB.push&&HUB.push.setOn){ HUB.push.setOn(want).then(r=>{ apply(!!(r&&r.ok)); }); }
      else apply(false);
    };
    pt.onclick=flipPush;
    pt.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flipPush(); } };
  }
  /* ringtone picker: built-in ringtones + preview + custom file (2026-09-22) */
  ringInit();
  document.getElementById('clearSamples').onclick=()=>{ store.clearSamples(); rerender(); ui.toast(t('me.set.cleared')); };
  document.getElementById('resetAll').onclick=()=>{ if(confirm(t('me.resetConfirm'))){ localStorage.removeItem('hub_v1'); location.reload(); } };

  /* trust & safety */
  document.getElementById('meReport').onclick=reportSheet;
  document.getElementById('meModQ').onclick=()=>{ if(HUB.trust&&HUB.trust.moderationQueue) HUB.trust.moderationQueue(); else ui.toast(t('me.trustNotReady')); };
  /* discoverability toggle (Workstream D): one tap, flips profile.discoverable */
  const dts=document.getElementById('discToggle');
  if(dts){
    const flipDisc=()=>{
      const pr=store.state.profile;
      pr.discoverable=!(pr.discoverable!==false);
      store.save();
      dts.classList.toggle('on',!!pr.discoverable);
      dts.setAttribute('aria-checked',pr.discoverable?'true':'false');
      ui.toast(pr.discoverable?t('me.safety.discOn'):t('me.safety.discOff'));
    };
    dts.onclick=flipDisc;
    dts.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flipDisc(); } };
  }
  document.getElementById('meModQ').onclick=()=>{ if(HUB.trust&&HUB.trust.moderationQueue) HUB.trust.moderationQueue(); else ui.toast(t('me.trustNotReady')); };
  document.getElementById('meBlocked').onclick=()=>{
    const blocked=(store.state.blocked||[]).map(b=>typeof b==='string'?b:(b&&b.name)||'').filter(Boolean);
    ui.openSheet('<h2>'+t('me.blocked.title')+'</h2><p class="sub" style="margin-bottom:12px">'+t('me.blocked.sub')+'</p>'+
      (blocked.length? blocked.map(b=>'<div class="item"><div class="avatar" style="background:var(--surface2)">⛔</div><div class="grow"><h3>'+ui.esc(b)+'</h3></div><button class="btn btn-sm btn-line" data-unblock="'+ui.esc(b)+'">'+t('me.blocked.unblock')+'</button></div>').join('')
        : '<p class="sub">'+t('me.blocked.none')+'</p>'));
    document.querySelectorAll('[data-unblock]').forEach(x=>{ x.onclick=()=>{ store.state.blocked=(store.state.blocked||[]).filter(n=>String(typeof n==='string'?n:(n&&n.name)||'')!==x.dataset.unblock); store.save(); ui.closeSheet(); rerender(); ui.toast(t('me.blocked.done')); }; });
  };
}};
})();
