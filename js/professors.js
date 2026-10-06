/* HUB Professors — RateMyProfessor-style professor ratings, Onaro edition.
   Opened from the Professors entry card on the HOME tab (directly below the
   classes card) as a full-screen overlay — the tab bar stays untouched.
   College-scoped (profile.campus): the directory seed below holds REAL public
   faculty info (names + departments verified on the universities' own sites;
   sources in data/ATTRIBUTION.txt). ALL ratings, comments, courses and votes
   are user-generated in this browser and START EMPTY — never invent a rating.
   Ratings/comments are ANONYMOUS (no author name is ever shown) and every
   comment is auto-scanned for cursing/abusive words: blocked attempts earn
   strikes, 3 strikes = a one-month rating ban.
   Storage: state.prof = {reviews:{profId:[...]}, votes:{reviewId:1|-1},
   custom:[...]} — browser-local for now; the data-layer functions are shaped
   so a backend can replace them later (honest copy in the UI says so).
   Screens: list (search name/course) -> detail (stats + reviews + rate CTA)
   -> rate sheet / add-professor sheet. Water 3D crystal UI. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const ui=()=>HUB.ui, st=()=>HUB.store.state;
/* Resilient fetch: retries + timeout (js/safeboot.js), plain-fetch fallback. */
const _fj=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){return fetch(u).then(function(r){if(!r.ok&&r.status!==0)throw new Error('http '+r.status);return r.json();});};

/* ---------- directory seed (real public faculty data) ----------
   campus strings match data/colleges.json record names exactly so they line
   up with profile.campus from the institution picker. courses: [] — courses
   are added honestly from student reviews, never invented. */
const SEED=[
 /* The University of Texas at Dallas — Computer Science (cs.utdallas.edu) */
 {id:'p-utd-khan',src:'https://news.utdallas.edu/faculty-staff/aaas-fellow-2025/',campus:'The University of Texas at Dallas',name:'Latifur Khan',title:'Professor',dept:'Computer Science',courses:[]},
 {id:'p-utd-hamlen',src:'https://cs.utdallas.edu/25302/dean-cybersecurity-researchers-recognized-in-ut-dallas-investiture-ceremony/',campus:'The University of Texas at Dallas',name:'Kevin Hamlen',title:'Professor',dept:'Computer Science',courses:[]},
 {id:'p-utd-thuraisingham',src:'https://cs.utdallas.edu/30713/elevating-education-a-conversation-with-bhavani-thuraisingham-taylor-l-booth-education-award-winner-2/',campus:'The University of Texas at Dallas',name:'Bhavani Thuraisingham',title:'Founders Chair Professor',dept:'Computer Science',courses:[]},
 {id:'p-utd-marcus',src:'https://cs.utdallas.edu/10412/drs-andrian-marcus-and-vincent-ng-create-automated-system-for-improving-computer-bug-reports/',campus:'The University of Texas at Dallas',name:'Andrian Marcus',title:'Professor',dept:'Computer Science',courses:[]},
 {id:'p-utd-liu',src:'https://profiles.utdallas.edu/cong',campus:'The University of Texas at Dallas',name:'Cong Liu',title:'Associate Professor',dept:'Computer Science',courses:[]},
 {id:'p-utd-salifullah',src:'https://cs.utdallas.edu/34033/introducing-new-faculty-members-to-computer-science-department/',campus:'The University of Texas at Dallas',name:'Abusayeed Salifullah',title:'Associate Professor',dept:'Computer Science',courses:[]},
 {id:'p-utd-zhang',src:'https://cs.utdallas.edu/34033/introducing-new-faculty-members-to-computer-science-department/',campus:'The University of Texas at Dallas',name:'Congyi Zhang',title:'Assistant Professor',dept:'Computer Science',courses:[]},
 {id:'p-utd-jaffal',src:'https://cs.utdallas.edu/34033/introducing-new-faculty-members-to-computer-science-department/',campus:'The University of Texas at Dallas',name:'Wafa Jaffal',title:'Assistant Professor of Instruction',dept:'Computer Science',courses:[]},
 /* Southern Methodist University — Cox School of Business (smu.edu) */
 {id:'p-smu-bowles',src:'https://www.smu.edu/cox/academics/faculty/trey-bowles',campus:'Southern Methodist University',name:'Trey Bowles',title:'Adjunct Professor',dept:'Caruth Institute for Entrepreneurship',courses:[]},
 {id:'p-smu-braun',src:'https://smu.edu/cox/our-people-and-community/faculty/',campus:'Southern Methodist University',name:'Michael Braun',title:'Associate Professor',dept:'Marketing',courses:[]},
 {id:'p-smu-butts',src:'https://smu.edu/cox/our-people-and-community/faculty/',campus:'Southern Methodist University',name:'Marcus Butts',title:'Professor',dept:'Management, Strategy, and Entrepreneurship',courses:[]},
 {id:'p-smu-choi',src:'http://www.smu.edu/cox/academics/faculty/emily-choi',campus:'Southern Methodist University',name:'Emily Choi',title:'Professor of Practice',dept:'Management, Strategy, and Entrepreneurship',courses:[]},
 {id:'p-smu-cambre',src:'https://smu.edu/cox/our-people-and-community/faculty/',campus:'Southern Methodist University',name:'Aren Cambre',title:'Clinical Professor',dept:'Information Technology and Operations Management',courses:[]},
 {id:'p-smu-chambers',src:'https://smu.edu/cox/our-people-and-community/faculty/',campus:'Southern Methodist University',name:'Chester Chambers',title:'Clinical Professor',dept:'Information Technology and Operations Management',courses:[]},
 /* Dallas College (dallascollege.edu) */
 {id:'p-dc-shepard',src:'https://www.dallascollege.edu/employee-directory/faculty/sshepard/',campus:'Dallas College',name:'Michael Shepard',title:'Faculty',dept:'English',courses:[]},
 {id:'p-dc-abedin',src:'https://www.dallascollege.edu/employee-directory/faculty/habedin/',campus:'Dallas College',name:'Haven Abedin',title:'Faculty',dept:'English',courses:[]},
 {id:'p-dc-baggett',src:'https://www.dallascollege.edu/resources/career-services/spotlights/',campus:'Dallas College',name:'Jennifer Baggett',title:'Faculty',dept:'Biology',courses:[]},
 {id:'p-dc-pleimann',src:'https://www.dallascollege.edu/resources/career-services/spotlights/',campus:'Dallas College',name:'Natalie Pleimann',title:'Faculty',dept:'English',courses:[]},
 {id:'p-dc-park',src:'http://blog.dallascollege.edu/2024/10/breast-cancer-awareness-month-cards/',campus:'Dallas College',name:'Minjung Park',title:'Professor',dept:'ESOL',courses:[]},
 {id:'p-dc-grimes',src:'http://blog.dallascollege.edu/2023/05/importance-of-magic/',campus:'Dallas College',name:'Geoffrey Grimes',title:'Professor',dept:'English',courses:[]}
];

/* ---------- data layer (backend-ready shape) ---------- */
function pstate(){
  const s=st();
  if(!s.prof||typeof s.prof!=='object') s.prof={reviews:{},votes:{},custom:[]};
  const p=s.prof;
  if(!p.reviews||typeof p.reviews!=='object') p.reviews={};
  if(!p.votes||typeof p.votes!=='object') p.votes={};
  if(!Array.isArray(p.custom)) p.custom=[];
  if(!p.mod||typeof p.mod!=='object') p.mod={strikes:0,bannedUntil:0}; /* auto-moderation */
  return p;
}
/* ---------- anonymity + auto-moderation (PraBin) ----------
   Every rating/comment is anonymous: the author's name is never rendered.
   authorId stays internal (self-vote guard + SPECIALIST badge) but no name
   ever reaches the DOM.
   Every comment/course text is scanned for cursing/abusive words BEFORE it
   posts. A blocked attempt = 1 strike (user is warned and can re-comment
   clean). 3 strikes = the account is flagged and cannot rate or comment
   for one month. Preview-local; the production backend will enforce
   server-side. */
const BADWORDS=['fuck','fucking','fucker','fucked','fucks','shit','shits','shitty','shat',
'bitch','bitches','bitchy','bastard','bastards','asshole','assholes','dick','dicks','dickhead',
'cock','cocks','cunt','cunts','pussy','whore','whores','slut','sluts','slutty','motherfucker',
'motherfuckers','faggot','faggots','nigga','nigger','niggers','retard','retards','retarded',
'douchebag','douchebags','jackass','jackasses','prick','pricks','dipshit','bullshit','tit','tits'];
/* substring-evasion sweep: bad words of 4+ letters matched inside the fully
   joined string, so f.u.c.k / f-u-c-k / f_u_c_k still trip. 'ass' and 'tit'
   stay whole-word-only — they live inside innocent words like "class" and
   "title" that students type constantly. */
const BADWORD_SUB=BADWORDS.filter(function(w){ return w.length>=4&&w!=='ass'&&w!=='tit'; });
function profanityNorm(s){
  return String(s||'').toLowerCase()
    .replace(/[@4]/g,'a').replace(/[0]/g,'o').replace(/[1!|]/g,'i').replace(/[3]/g,'e')
    .replace(/[5$]/g,'s').replace(/[7]/g,'t').replace(/[+]/g,'t')
    .replace(/(.)\1\1+/g,'$1'); /* shiiit -> shit */
}
function hasProfanity(s){
  const norm=profanityNorm(s);
  const words=norm.replace(/[^a-z]+/g,' ').split(' ');
  for(let i=0;i<words.length;i++){ if(words[i]&&BADWORDS.indexOf(words[i])>=0) return true; }
  const joined=norm.replace(/[^a-z]/g,'');
  for(let i=0;i<BADWORD_SUB.length;i++){ if(joined.indexOf(BADWORD_SUB[i])>=0) return true; }
  return false;
}
const MOD_MAX_STRIKES=3, MOD_BAN_MS=30*24*3600*1000; /* one month */
function modState(){ return pstate().mod; }
function modBannedUntil(){
  const m=modState();
  if(m.bannedUntil&&Date.now()>=m.bannedUntil){ m.strikes=0; m.bannedUntil=0; HUB.store.save(); }
  return (m.bannedUntil&&Date.now()<m.bannedUntil)?m.bannedUntil:0;
}
/* ---------- faculty directory lazy-load (data/faculty/*.json) ----------
   Public university faculty directories collected by the data pipeline
   (see data/faculty/PIPELINE.md). index.json maps campus -> slug file;
   the file loads on demand when the user opens Professors. Ratings still
   start empty — this is directory data only. */
const FAC={idx:null,idxP:null,files:{},fileP:{},byId:{}};
function normCamp(s){ return String(s||'').toLowerCase().replace(/^the\s+/,'').replace(/[^a-z0-9]/g,''); }
/* duplicate-proof name match: strip honorifics ("Dr.", "Prof.") so
   "Dr. Jane Doe" matches an existing "Jane Doe" listing. */
function normProfName(s){ return normCamp(String(s||'').replace(/^(dr|prof|professor|mr|mrs|ms)\.?\s+/i,'')); }
function facIndex(){
  if(FAC.idx) return Promise.resolve(FAC.idx);
  if(!FAC.idxP) FAC.idxP=Promise.resolve()
    /* Phase 1 backend (js/api.js): API first when configured, static fallback. */
    .then(function(){
      if(window.HUB&&HUB.api&&HUB.api.on()) return HUB.api.facultyIndex().catch(function(){ return null; });
      return null;
    })
    .then(function(apiIdx){ return apiIdx||_fj('data/faculty/index.json'); })
    .then(function(j){ FAC.idx=(j&&Array.isArray(j.colleges))?j:{colleges:[]}; return FAC.idx; })
    .catch(function(){ FAC.idx={colleges:[]}; return FAC.idx; });
  return FAC.idxP;
}
function facultySlugFor(cp){
  if(!FAC.idx) return null;
  const n=normCamp(cp);
  const cols=FAC.idx.colleges;
  for(let i=0;i<cols.length;i++){
    const names=[cols[i].name].concat(cols[i].match||[]);
    for(let k=0;k<names.length;k++){ if(normCamp(names[k])===n) return cols[i].slug; }
  }
  return null;
}
function facFile(slug){
  if(FAC.files[slug]) return Promise.resolve(FAC.files[slug]);
  if(!FAC.fileP[slug]) FAC.fileP[slug]=Promise.resolve()
    /* Phase 1 backend (js/api.js): API first when configured, static fallback. */
    .then(function(){
      if(window.HUB&&HUB.api&&HUB.api.on()) return HUB.api.facultyFile(slug).catch(function(){ return null; });
      return null;
    })
    .then(function(apiFile){ return apiFile||_fj('data/faculty/'+slug+'.json'); })
    .then(function(j){ FAC.files[slug]=j; return j; })
    .catch(function(){ FAC.files[slug]={professors:[]}; return FAC.files[slug]; });
  return FAC.fileP[slug];
}
function ensureFaculty(cp){
  return facIndex().then(function(){
    const s=facultySlugFor(cp);
    return s?facFile(s).then(function(){ return true; }):false;
  });
}
function facultyProfs(cp){
  const slug=facultySlugFor(cp), f=slug&&FAC.files[slug];
  if(!f||!Array.isArray(f.professors)) return [];
  const seen={}, out=[];
  f.professors.forEach(function(p,i){
    const nm=String(p.name||'').trim();
    if(!nm) return;
    const k=normCamp(nm);
    if(seen[k]) return;
    seen[k]=1;
    const rec={id:'f-'+slug+'-'+i,name:nm,title:p.title||'',dept:p.dept||'',campus:cp,dir:true,courses:Array.isArray(p.courses)?p.courses:[]};
    FAC.byId[rec.id]=rec;
    out.push(rec);
  });
  return out;
}
function allProfs(campus){
  const customs=pstate().custom.filter(c=>c.campus===campus).map(c=>({id:c.id,name:c.name,title:c.title||'',dept:c.dept||'',campus:c.campus,custom:true,courses:Array.isArray(c.courses)?c.courses:[]}));
  const dirs=facultyProfs(campus);
  const seen={};
  dirs.forEach(function(p){ seen[normCamp(p.name)]=1; });
  const seeds=SEED.filter(function(p){ return p.campus===campus&&!seen[normCamp(p.name)]; });
  return dirs.concat(seeds).concat(customs);
}
function profById(pid){
  const s=SEED.find(p=>p.id===pid);
  if(s) return s;
  if(pid&&FAC.byId[pid]) return FAC.byId[pid];
  const c=pstate().custom.find(x=>x.id===pid);
  return c?{id:c.id,name:c.name,title:c.title||'',dept:c.dept||'',campus:c.campus,custom:true,courses:Array.isArray(c.courses)?c.courses:[]}:null;
}
function reviewsOf(pid){ return (pstate().reviews[pid]||[]).slice().sort((a,b)=>b.ts-a.ts); }
function statsOf(pid){
  const rs=reviewsOf(pid), n=rs.length;
  /* a professor's own declared courses (e.g. from Add Professor) count too */
  const prec=profById(pid), declared=(prec&&Array.isArray(prec.courses))?prec.courses.slice():[];
  const cs=declared.filter(function(c,i){ return c&&declared.indexOf(c)===i; });
  if(!n) return {n:0,avgQ:0,avgD:0,againPct:0,courses:cs.sort()};
  let q=0,d=0,ag=0,agN=0;
  rs.forEach(r=>{ q+=r.q; d+=(r.d||3);
    if(r.again===1){ag++;agN++;} else if(r.again===0){agN++;}
    if(r.course&&cs.indexOf(r.course)<0) cs.push(r.course);
  });
  return {n:n,avgQ:q/n,avgD:d/n,againPct:agN?Math.round(100*ag/agN):0,courses:cs.sort()};
}
function addReview(pid,rv){
  const p=pstate();
  if(!p.reviews[pid]) p.reviews[pid]=[];
  const prof=st().profile||{};
  if(!prof.aid) prof.aid=HUB.store.uid(); /* stable per-device author id */
  const clean=Object.assign({},rv); delete clean.author; /* anonymous: a name is never stored */
  p.reviews[pid].unshift(Object.assign({id:HUB.store.uid(),ts:Date.now(),likes:0,dislikes:0,authorId:prof.aid},clean));
  HUB.store.save();
  /* badge hook: a new professor review may earn SPECIALIST. */
  try{ if(HUB.badges&&HUB.badges.onReview) HUB.badges.onReview(); }catch(e){}
}
/* Fix 1 (PraBin): a user can never vote on their OWN comment. authorId match
   is authoritative; legacy reviews without authorId fall back to name match. */
function isOwnReview(r){
  if(!r) return false;
  const p=st().profile||{};
  if(r.authorId&&p.aid) return r.authorId===p.aid;
  const nm=HUB.store.myName()||'';
  return !!(nm&&r.author&&r.author===nm);
}
function findReview(rid){
  const p=pstate();
  for(const pid of Object.keys(p.reviews)){
    const r=p.reviews[pid].find(x=>x.id===rid);
    if(r) return r;
  }
  return null;
}
/* like/dislike: one vote per review per device; tap again to undo, tap the
   other side to switch. */
function vote(rid,dir){
  const p=pstate(), r=findReview(rid);
  if(!r) return false;
  if(isOwnReview(r)) return false; /* belt-and-braces: no self-voting, even via _vote */
  const cur=p.votes[rid]||0;
  if(cur===dir){ /* undo */
    if(dir===1) r.likes=Math.max(0,r.likes-1); else r.dislikes=Math.max(0,r.dislikes-1);
    delete p.votes[rid];
  }else{
    if(cur===1) r.likes=Math.max(0,r.likes-1);
    if(cur===-1) r.dislikes=Math.max(0,r.dislikes-1);
    if(dir===1) r.likes++; else r.dislikes++;
    p.votes[rid]=dir;
  }
  HUB.store.save();
  return true;
}
function searchProfs(q,campus){
  const needle=String(q||'').trim().toLowerCase();
  const list=allProfs(campus);
  if(!needle) return list;
  return list.filter(p=>{
    if((p.name+' '+p.dept+' '+(p.title||'')).toLowerCase().indexOf(needle)>=0) return true;
    const sts=statsOf(p.id).courses;
    return sts.some(c=>c.toLowerCase().indexOf(needle)>=0);
  });
}

/* ---------- view state ---------- */
let cur=null, query='', sortMode='top';
function campus(){ return (st().profile&&st().profile.campus)||''; }
function hueFor(name){ let h=0; const s=String(name||'?'); for(let i=0;i<s.length;i++) h=(h*31+s.charCodeAt(i))>>>0; return h%360; }
function avaHTML(name,cls){
  const U=ui();
  return '<span class="prof-ava '+(cls||'')+'" style="--h:'+hueFor(name)+'">'+U.esc(U.initials(name))+'</span>';
}
function ratingLine(pid){
  const U=ui(), s=statsOf(pid);
  if(!s.n) return '<span class="prof-norate">'+U.esc(t('prof.noRatings'))+'</span>';
  const cnt=s.n===1?t('prof.rating1'):t('prof.ratingsN',{n:s.n});
  return '<span class="prof-stars">'+U.esc(U.stars(s.avgQ))+'</span>'+
    ' <b>'+s.avgQ.toFixed(1)+'</b><span class="meta"> · '+U.esc(cnt)+
    ' · '+U.esc(t('prof.againPct',{p:s.againPct}))+'</span>';
}
function sortedList(list){
  const arr=list.slice();
  if(sortMode==='most') arr.sort((a,b)=>statsOf(b.id).n-statsOf(a.id).n||statsOf(b.id).avgQ-statsOf(a.id).avgQ);
  else arr.sort((a,b)=>{
    const sa=statsOf(a.id), sb=statsOf(b.id);
    if(!sa.n&&!sb.n) return a.name.localeCompare(b.name);
    if(!sa.n) return 1; if(!sb.n) return -1;
    return sb.avgQ-sa.avgQ||sb.n-sa.n;
  });
  return arr;
}

/* ---------- list screen ---------- */
function cardHTML(p){
  const U=ui(), s=statsOf(p.id);
  const line=s.n
    ? '<span class="prof-stars">'+U.esc(U.stars(s.avgQ))+'</span> <b>'+s.avgQ.toFixed(1)+'</b>'+
      '<span class="meta"> · '+(s.n===1?U.esc(t('prof.rating1')):U.esc(t('prof.ratingsN',{n:s.n})))+'</span>'
    : '<span class="prof-norate">'+U.esc(t('prof.noRatings'))+'</span>';
  return '<button class="prof-card" data-pid="'+U.esc(p.id)+'">'+avaHTML(p.name)+
    '<span class="grow"><b>'+U.esc(p.name)+'</b>'+
    '<span class="meta">'+U.esc(p.title?p.title+' · ':'')+U.esc(p.dept)+'</span>'+
    '<span class="meta prof-campus">🎓 '+U.esc(p.campus)+'</span>'+
    '<span class="prof-line">'+line+'</span></span>'+
    '<span class="prof-chev" aria-hidden="true">›</span></button>';
}
function paintList(){
  const U=ui(), box=document.getElementById('profList');
  if(!box) return;
  const list=sortedList(searchProfs(query,campus()));
  if(!list.length){
    box.innerHTML='<div class="empty"><div class="big">🔍</div><p>'+
      (query?U.esc(t('prof.noResults',{q:query})):U.esc(t('prof.noProfs',{campus:campus()})))+'</p>'+
      '<p class="hint">➕ '+U.esc(t('prof.addMissing'))+'</p>'+
      '<button class="btn btn-dark btn-sm" id="profAddEmpty">＋ '+U.esc(t('prof.addProf'))+'</button></div>';
  }else{
    box.innerHTML=list.map(cardHTML).join('');
  }
  box.querySelectorAll('[data-pid]').forEach(b=>{ b.onclick=()=>openProf(b.dataset.pid); });
  const ae=document.getElementById('profAddEmpty');
  if(ae) ae.onclick=openAddSheet;
}
function renderList(el){
  const U=ui(), cp=campus();
  let h='<div class="prof-wrap">';
  h+='<div class="prof-hero"><span class="prof-hero-ico">'+HUB.icons.icon('nav-prof')+'</span>'+
    '<div><h1>'+U.esc(t('prof.title'))+'</h1>'+
    '<p class="sub">'+U.esc(t('prof.sub',{campus:cp}))+'</p></div></div>';
  h+='<div class="prof-swrap"><input class="input" id="profQ" enterkeyhint="search" autocomplete="off"'+
    ' placeholder="'+U.esc(t('prof.searchPh'))+'" value="'+U.esc(query)+'" aria-label="'+U.esc(t('prof.searchPh'))+'">'+
    '<button class="prof-clear" id="profClear" hidden aria-label="'+U.esc(t('prof.searchClear'))+'">✕</button></div>';
  h+='<div class="prof-tools"><div class="chips">'+
    '<button class="chip'+(sortMode==='top'?' on':'')+'" data-sort="top">'+U.esc(t('prof.sortTop'))+'</button>'+
    '<button class="chip'+(sortMode==='most'?' on':'')+'" data-sort="most">'+U.esc(t('prof.sortMost'))+'</button></div>'+
    '<button class="btn btn-line btn-sm" id="profAdd">＋ '+U.esc(t('prof.addProf'))+'</button></div>';
  /* reviewer points banner: tap opens the badge showcase */
  (function(){
    let pts=0, sp=false, goal=1000;
    try{ if(HUB.badges){ pts=HUB.badges.myPoints(); sp=HUB.badges.isSpecialist(); goal=HUB.badges.ptsGoal(); } }catch(e){}
    h+='<button class="prof-pts" id="profPts">⭐ <b>'+pts+'</b> '+U.esc(t('prof.myPoints'))+
      ' · '+(sp?U.esc(t('prof.specEarned')):U.esc(t('prof.ptsToSpec',{n:Math.max(0,goal-pts)})))+'</button>';
  })();
  h+='<div id="profList"></div>';
  h+='<p class="hint">➕ '+U.esc(t('prof.addMissing'))+'</p>';
  h+='<p class="hint">🎓 '+U.esc(t('prof.dirNote'))+'</p>';
  h+='<p class="hint">🔒 '+U.esc(t('prof.localNote'))+'</p></div>';
  el.innerHTML=h;
  const q=document.getElementById('profQ');
  const qc=document.getElementById('profClear');
  const syncClear=()=>{ if(qc) qc.hidden=!q.value; };
  q.addEventListener('input',()=>{ query=q.value; syncClear(); paintList(); });
  if(qc) qc.onclick=()=>{ q.value=''; query=''; syncClear(); paintList(); try{q.focus();}catch(e){} };
  syncClear();
  el.querySelectorAll('[data-sort]').forEach(b=>{ b.onclick=()=>{
    sortMode=b.dataset.sort;
    el.querySelectorAll('[data-sort]').forEach(x=>x.classList.toggle('on',x===b));
    paintList();
  };});
  document.getElementById('profAdd').onclick=openAddSheet;
  const pp=document.getElementById('profPts');
  if(pp) pp.onclick=()=>{ try{ HUB.badges.openShowcase(); }catch(e){} };
  paintList();
  ensureFaculty(cp).then(function(ok){ if(ok) paintList(); });
}
function renderNoCampus(el){
  const U=ui();
  el.innerHTML='<div class="prof-wrap"><div class="empty prof-empty">'+
    '<div class="big">🎓</div><h2>'+U.esc(t('prof.title'))+'</h2>'+
    '<p>'+U.esc(t('prof.noCampus'))+'</p>'+
    '<button class="btn btn-dark" id="profPickCampus">'+U.esc(t('prof.noCampusCta'))+'</button>'+
    '<p class="hint">🔒 '+U.esc(t('prof.localNote'))+'</p></div></div>';
  document.getElementById('profPickCampus').onclick=()=>{
    ui().openInstitutionPicker({mode:'student',onPick:rec=>{
      const p=st().profile;
      p.campus=rec.name; p.campusSample=!!rec.sample; p.campusKind=rec.kind||'';
      if(!rec.sample&&rec.lat!=null&&rec.lng!=null&&isFinite(rec.lat)&&isFinite(rec.lng)){ p.campusCoords=[rec.lat,rec.lng]; p.campusIso=rec.iso||''; p.campusCity=rec.city||''; }
      else { delete p.campusCoords; delete p.campusIso; delete p.campusCity; }
      HUB.store.save();
      renderBody();
    }});
  };
}

/* ---------- detail screen ---------- */
/* 3D glowing heart (like) + red thumbs-down (dislike). Original SVG art. */
const HEART_D='M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z';
const HEART_SVG='<svg class="prof-heart" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><defs><linearGradient id="profHeartG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FF8FAB"/><stop offset="1" stop-color="#E0245E"/></linearGradient></defs><path d="'+HEART_D+'" fill="url(#profHeartG)"/></svg>';
const THUMB_SVG='<svg class="prof-thumb" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><g transform="rotate(180 12 12)"><path d="M7 11v9H4.5A1.5 1.5 0 0 1 3 18.5v-6A1.5 1.5 0 0 1 4.5 11H7zm2.4 9H17a2 2 0 0 0 2-1.6l1.3-5.2a2 2 0 0 0-2-2.4h-4.9l.7-3.4c.2-.8-.2-1.6-1-2-.7-.4-1.6-.3-2.2.3L9.4 7.6V20z" fill="#E5484D"/></g></svg>';
function reviewHTML(pid,r){
  const U=ui(), mine=pstate().votes[r.id]||0, own=isOwnReview(r);
  /* own comment: buttons rendered disabled (aria-disabled keeps the tap
     alive so we can explain WHY with a toast instead of dead silence) */
  const dis=own?' aria-disabled="true"':'';
  let h='<div class="prof-rev" data-rev="'+U.esc(r.id)+'"><div class="prof-rev-head"><span class="prof-stars">'+U.esc(U.stars(r.q))+'</span>';
  if(r.course) h+='<span class="chip sm">'+U.esc(r.course)+'</span>';
  h+='<span class="meta">'+U.esc(U.timeAgo(r.ts))+'</span></div>';
  if(r.comment) h+='<p class="prof-rev-txt">'+U.esc(r.comment)+'</p>';
  h+='<div class="prof-rev-foot"><span class="meta">🕵️ '+U.esc(t('prof.anon'))+'</span>'+
    '<span class="grow"></span>'+
    '<button class="prof-vote'+(mine===1?' on':'')+(own?' is-own':'')+'" data-vote="1" data-rid="'+U.esc(r.id)+'"'+dis+' aria-pressed="'+(mine===1)+'" aria-label="'+U.esc(t('prof.like'))+'">'+HEART_SVG+'<b>'+r.likes+'</b></button>'+
    '<button class="prof-vote'+(mine===-1?' on':'')+(own?' is-own':'')+'" data-vote="-1" data-rid="'+U.esc(r.id)+'"'+dis+' aria-pressed="'+(mine===-1)+'" aria-label="'+U.esc(t('prof.dislike'))+'">'+THUMB_SVG+'<b>'+r.dislikes+'</b></button></div></div>';
  return h;
}
function renderDetail(el,pid){
  const U=ui(), p=profById(pid);
  if(!p){ cur=null; renderBody(); return; }
  const s=statsOf(pid), rs=reviewsOf(pid);
  let h='<div class="prof-wrap">';
  h+='<button class="linklike prof-back" id="profBack">‹ '+U.esc(t('common.back'))+'</button>';
  h+='<div class="prof-hero prof-hero-detail"><span class="prof-orb o1"></span><span class="prof-orb o2"></span>'+
    avaHTML(p.name,'xl')+
    '<h1>'+U.esc(p.name)+'</h1>'+
    '<p class="sub">'+U.esc(p.title?p.title+' · ':'')+U.esc(p.dept)+'</p>'+
    '<div class="chips prof-idchips">'+
    (p.custom?'<span class="chip sm">📝 '+U.esc(t('prof.customTag'))+'</span>':'')+
    (p.dept?'<span class="chip sm">📚 '+U.esc(p.dept)+'</span>':'')+
    '<span class="chip sm">🎓 '+U.esc(p.campus)+'</span></div>';
  if(s.n){
    h+='<div class="prof-score"><span class="prof-bignum">'+s.avgQ.toFixed(1)+'</span><span class="meta">/5</span>'+
      '<span class="prof-stars big">'+U.esc(U.stars(s.avgQ))+'</span></div>'+
      '<div class="prof-statrow">'+
      '<span class="prof-stat"><b>'+(s.n===1?t('prof.rating1'):t('prof.ratingsN',{n:s.n}))+'</b></span>'+
      '<span class="prof-stat">'+U.esc(t('prof.difficulty'))+' <b>'+s.avgD.toFixed(1)+'/5</b></span>'+
      '<span class="prof-stat">'+U.esc(t('prof.againPct',{p:s.againPct}))+'</span></div>';
  }else{
    h+='<p class="prof-norate" style="margin:10px 0">'+U.esc(t('prof.noRatings'))+'</p>';
  }
  h+='<button class="btn btn-dark" id="profRate" style="margin-top:10px">★ '+U.esc(t('prof.rate'))+'</button></div>';
  /* courses */
  h+='<h3 class="prof-h">'+U.esc(t('prof.courses'))+'</h3>';
  if(s.courses.length) h+='<div class="chips">'+s.courses.map(c=>'<span class="chip">'+U.esc(c)+'</span>').join('')+'</div>';
  else h+='<p class="sub">'+U.esc(t('prof.coursesPending'))+'</p>';
  /* reviews */
  h+='<h3 class="prof-h">'+U.esc(t('prof.comment'))+'s · '+s.n+'</h3>';
  h+='<div id="profRevs">'+(rs.length?rs.map(r=>reviewHTML(pid,r)).join('')
    :'<div class="empty"><div class="big">💬</div><p>'+U.esc(t('prof.noRatings'))+'</p></div>')+'</div>';
  if(rs.length) h+='<button class="prof-scroll" id="profGoDown" aria-label="↓">↓</button>'+
    '<button class="prof-scroll up" id="profGoUp" aria-label="↑" hidden>↑</button>';
  h+='<p class="hint">🔒 '+U.esc(t('prof.localNote'))+'</p></div>';
  el.innerHTML=h;
  document.getElementById('profBack').onclick=()=>{ cur=null; renderBody(); };
  document.getElementById('profRate').onclick=()=>openRateSheet(pid);
  el.querySelectorAll('[data-vote]').forEach(b=>{ b.onclick=()=>{
    if(isOwnReview(findReview(b.dataset.rid))){ U.toast(t('prof.voteSelf')); return; }
    if(!vote(b.dataset.rid, +b.dataset.vote)) return;
    /* in-place repaint: counts + pressed state, no scroll jump */
    const r=findReview(b.dataset.rid);
    const foot=b.closest('.prof-rev-foot')||b.parentElement;
    foot.querySelectorAll('[data-vote]').forEach(x=>{
      const dir=+x.dataset.vote, on=(pstate().votes[r.id]||0)===dir;
      x.classList.toggle('on',on);
      x.setAttribute('aria-pressed',on?'true':'false');
      const cnt=x.querySelector('b');
      if(cnt) cnt.textContent=(dir===1?r.likes:r.dislikes);
    });
    b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop');
  };});
  /* smooth comment navigation: down/up floaters track .prof-body scroll */
  const dn=document.getElementById('profGoDown'), up=document.getElementById('profGoUp');
  if(dn&&up){
    const sc=el; /* .prof-body is the scroll container; it persists across renders */
    const sync=()=>{
      const d2=document.getElementById('profGoDown'), u2=document.getElementById('profGoUp');
      if(!d2||!u2) return;
      u2.hidden=sc.scrollTop<80;
      d2.hidden=(sc.scrollHeight-sc.scrollTop-sc.clientHeight)<80;
    };
    if(!sc._profSyncWired){ sc.addEventListener('scroll',sync,{passive:true}); sc._profSyncWired=true; }
    sync();
    const step=()=>Math.round(sc.clientHeight*0.85);
    dn.onclick=()=>sc.scrollBy({top:step(),behavior:'smooth'});
    up.onclick=()=>sc.scrollBy({top:-step(),behavior:'smooth'});
  }
}

/* ---------- rate sheet ---------- */
const rate={q:0,d:0,again:null};
function isVerified(){ const p=st().profile; return !!(p&&p.verified); }
function openVerifyGate(){
  const U=ui();
  U.openSheet(
    '<h2>🎓 '+U.esc(t('prof.verifyOnly'))+'</h2>'+
    '<p class="sub">'+U.esc(t('prof.verifyOnlySub'))+'</p>'+
    '<button class="btn btn-dark btn-block" id="profVerifyGo">'+U.esc(t('prof.verifyCta'))+'</button>'
  );
  document.getElementById('profVerifyGo').onclick=()=>{
    U.closeSheet(); close(); /* leave Professors, land on ME verification */
    try{ HUB.showTab('me'); }catch(e){}
    setTimeout(()=>{ const vb=document.getElementById('verifyBtn'); if(vb) vb.click(); },400);
  };
}
function openBannedGate(until){
  const U=ui();
  U.openSheet(
    '<h2>🚫 '+U.esc(t('prof.bannedTitle'))+'</h2>'+
    '<p class="sub">'+U.esc(t('prof.banned',{date:new Date(until).toLocaleDateString()}))+'</p>'+
    '<button class="btn btn-dark btn-block" data-close>'+U.esc(t('common.ok')||'OK')+'</button>'
  );
}
function starBtns(curN){
  let h='';
  for(let i=1;i<=5;i++) h+='<button class="prof-star'+(i<=curN?' on':'')+'" data-star="'+i+'" aria-label="'+i+' / 5">★</button>';
  return h;
}
function openRateSheet(pid){
  const U=ui(), p=profById(pid);
  if(!p) return;
  if(!isVerified()){ openVerifyGate(); return; } /* verified students only */
  const ban=modBannedUntil();
  if(ban){ openBannedGate(ban); return; } /* flagged accounts cannot rate */
  rate.q=0; rate.d=0; rate.again=null;
  U.openSheet(
    '<h2>★ '+U.esc(t('prof.rateTitle',{name:p.name}))+'</h2>'+
    '<p class="hint">🕵️ '+U.esc(t('prof.anonNote'))+'</p>'+
    '<p class="hint">🚫 '+U.esc(t('prof.cleanRule'))+'</p>'+
    '<div class="field"><label>'+U.esc(t('prof.quality'))+'</label><div class="prof-stars input" id="rateStars" style="font-size:30px">'+starBtns(0)+'</div></div>'+
    '<div class="field"><label>'+U.esc(t('prof.difficulty'))+' <span class="meta">1–5</span></label><div class="chips" id="rateDiff">'+
      [1,2,3,4,5].map(n=>'<button class="chip" data-diff="'+n+'">'+n+'</button>').join('')+'</div></div>'+
    '<div class="field"><label>'+U.esc(t('prof.again'))+'</label><div class="seg" id="rateAgain">'+
      '<button data-ag="1">'+U.esc(t('common.yes'))+'</button><button data-ag="0">'+U.esc(t('common.no'))+'</button></div></div>'+
    '<div class="field"><label>'+U.esc(t('prof.course'))+'</label><input class="input" id="rateCourse" maxlength="40" placeholder="'+U.esc(t('prof.coursePh'))+'"></div>'+
    '<div class="field"><label>'+U.esc(t('prof.comment'))+'</label><textarea class="input" id="rateComment" rows="3" maxlength="500" placeholder="'+U.esc(t('prof.commentPh'))+'"></textarea></div>'+
    '<button class="btn btn-dark btn-block" id="rateGo">'+U.esc(t('prof.submit'))+'</button>'+
    '<p class="hint">🔒 '+U.esc(t('prof.localNote'))+'</p>'
  );
  const paintStars=()=>{ document.getElementById('rateStars').innerHTML=starBtns(rate.q);
    document.querySelectorAll('#rateStars [data-star]').forEach(b=>{ b.onclick=()=>{ rate.q=+b.dataset.star; paintStars(); }; }); };
  paintStars();
  document.querySelectorAll('#rateDiff [data-diff]').forEach(b=>{ b.onclick=()=>{
    rate.d=+b.dataset.diff;
    document.querySelectorAll('#rateDiff [data-diff]').forEach(x=>x.classList.toggle('on',x===b));
  };});
  document.querySelectorAll('#rateAgain [data-ag]').forEach(b=>{ b.onclick=()=>{
    rate.again=+(b.dataset.ag);
    document.querySelectorAll('#rateAgain [data-ag]').forEach(x=>x.classList.toggle('on',x===b));
  };});
  document.getElementById('rateGo').onclick=()=>{
    if(!isVerified()){ U.toast(t('prof.verifyOnly')); U.closeSheet(); return; } /* never trust the client alone */
    if(modBannedUntil()){ U.closeSheet(); openBannedGate(modBannedUntil()); return; }
    if(!rate.q){ U.toast(t('prof.needQuality')); return; }
    const course=document.getElementById('rateCourse').value.trim();
    const comment=document.getElementById('rateComment').value.trim();
    /* auto-moderation: scan BEFORE anything posts */
    if(hasProfanity(comment)||hasProfanity(course)){
      const m=modState(); m.strikes=(m.strikes||0)+1;
      if(m.strikes>=MOD_MAX_STRIKES){
        m.bannedUntil=Date.now()+MOD_BAN_MS; HUB.store.save();
        U.closeSheet(); openBannedGate(m.bannedUntil);
      }else{
        HUB.store.save();
        U.toast(t('prof.curseWarn',{n:m.strikes}));
        const box=document.getElementById('rateComment');
        if(box){ box.classList.add('prof-curse-flag'); box.focus(); }
      }
      return; /* the offending comment is never posted */
    }
    addReview(pid,{q:rate.q,d:rate.d||3,again:rate.again,course:course,comment:comment});
    U.closeSheet(); renderBody(); U.toast('★ '+t('prof.thanks')+' · +10 '+t('prof.pts'));
  };
}

/* ---------- add-professor sheet ---------- */
function openAddSheet(){
  const U=ui(), cp=campus();
  const ban0=modBannedUntil();
  if(ban0){ openBannedGate(ban0); return; } /* flagged accounts cannot add either */
  U.openSheet(
    '<h2>🎓 '+U.esc(t('prof.addProf'))+'</h2>'+
    '<p class="sub">'+U.esc(t('prof.addProfSub'))+'</p>'+
    '<p class="hint">🎓 '+U.esc(cp)+'</p>'+
    '<div class="field"><label>'+U.esc(t('prof.fName'))+'</label><input class="input" id="apName" maxlength="60" placeholder="Jane Doe"></div>'+
    '<div class="field"><label>'+U.esc(t('prof.fTitle'))+'</label><input class="input" id="apTitle" maxlength="40" placeholder="'+U.esc(t('prof.fTitlePh'))+'"></div>'+
    '<div class="field"><label>'+U.esc(t('prof.fDept'))+'</label><input class="input" id="apDept" maxlength="60" placeholder="Computer Science"></div>'+
    '<div class="field"><label>'+U.esc(t('prof.fCourses'))+'</label><input class="input" id="apCourses" maxlength="120" placeholder="'+U.esc(t('prof.fCoursesPh'))+'"></div>'+
    '<p class="hint">🚫 '+U.esc(t('prof.cleanRule'))+'</p>'+
    '<button class="btn btn-dark btn-block" id="apGo">'+U.esc(t('common.add'))+'</button>'
  );
  document.getElementById('apGo').onclick=()=>{
    const name=document.getElementById('apName').value.trim();
    if(!name){ const box=document.getElementById('apName'); if(box){ box.classList.add('prof-curse-flag'); box.focus(); } U.toast(t('prof.nameNeed')); return; }
    const title=document.getElementById('apTitle').value.trim();
    const dept=document.getElementById('apDept').value.trim();
    const courses=document.getElementById('apCourses').value.split(',').map(function(s){ return s.trim(); }).filter(Boolean).slice(0,12);
    /* auto-moderation applies to additions too — nothing abusive gets listed */
    if(hasProfanity(name)||hasProfanity(title)||hasProfanity(dept)||courses.some(hasProfanity)){
      const m=modState(); m.strikes=(m.strikes||0)+1;
      if(m.strikes>=MOD_MAX_STRIKES){
        m.bannedUntil=Date.now()+MOD_BAN_MS; HUB.store.save();
        U.closeSheet(); openBannedGate(m.bannedUntil);
      }else{
        HUB.store.save();
        U.toast(t('prof.curseWarnAdd',{n:m.strikes}));
      }
      return;
    }
    /* duplicate prevention: match within this campus against the directory,
       seed list, and student-added professors. Duplicates are not saved and
       earn no points — an honest mistake, not abuse, so no strike. */
    const nk=normProfName(name);
    const dup=allProfs(cp).some(function(p){ return normProfName(p.name)===nk; });
    if(dup){ U.toast('⚠️ '+t('prof.dupProf')); return; }
    const p=pstate(), id='c'+HUB.store.uid();
    p.custom.unshift({id:id,name:name,title:title,dept:dept,courses:courses,campus:cp,ts:Date.now()});
    HUB.store.save();
    try{ if(HUB.badges&&HUB.badges.onAddProfessor) HUB.badges.onAddProfessor(); }catch(e){}
    U.closeSheet(); U.toast('🎓 '+t('prof.added')+' · +25 '+t('prof.pts'));
    openProf(id);
  };
}

/* ---------- overlay entry (from the Home tab entry card) ----------
   Same mount pattern as notifications/search/pulse: a .chatroot overlay
   removed from the DOM on close. Escape closes the overlay, but a sheet
   open above it wins (the global sheet handler runs its own dismissal). */
const ROOT_ID='hubProfRoot';
function ensureClosed(){
  const old=document.getElementById(ROOT_ID);
  if(old) old.remove();
  document.removeEventListener('keydown',onKey);
}
function close(){ ensureClosed(); }
function onKey(e){
  if(e.key!=='Escape') return;
  const sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden) return; /* sheet above us handles this Escape */
  close();
}
function renderBody(){
  const body=document.getElementById('profBody');
  if(!body) return;
  if(!campus()){ renderNoCampus(body); return; }
  if(cur&&profById(cur)) renderDetail(body,cur);
  else { cur=null; renderList(body); }
}
function openProf(pid){
  ensureClosed();
  ui().closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  cur=pid||null;
  const app=document.getElementById('app')||document.body;
  const d=document.createElement('div');
  d.className='chatroot profroot'; d.id=ROOT_ID;
  d.innerHTML='<div class="chatpanel prof-panel">'+
    '<div class="prof-topbar"><span class="prof-topbar-t">'+ui().esc(t('prof.title'))+'</span>'+
    '<button class="iconbtn" id="profClose" aria-label="'+ui().esc(t('common.close'))+'">✕</button></div>'+
    '<div class="prof-body" id="profBody"></div></div>';
  app.appendChild(d);
  d.addEventListener('click',e=>{ if(e.target===d) close(); });
  document.getElementById('profClose').onclick=close;
  document.addEventListener('keydown',onKey);
  renderBody();
}
/* ---------- Home tab entry card (directly below the classes card) ----------
   Blackboard scene: original SVG artwork — a small chalkboard with an
   original teacher figure writing glowing chalk stars on a loop. Pure
   CSS/SVG animation (transform + opacity + stroke-dashoffset only). */
const BB_STAR_D='M0,-7 L2.1,-2.3 L7,-2.3 L3,1.1 L4.5,5.7 L0,2.9 L-4.5,5.7 L-3,1.1 L-7,-2.3 L-2.1,-2.3 Z';
function bbStars(){
  const xs=[24,40,56,72,88];
  let h='';
  for(let i=0;i<xs.length;i++){
    h+='<path class="prof-star-draw" pathLength="100" transform="translate('+xs[i]+',30) scale(0.85)" d="'+BB_STAR_D+'" style="animation-delay:-'+(i*0.9)+'s"/>';
  }
  return h;
}
const BB_SVG='<svg class="prof-bb-svg" viewBox="0 0 132 104" aria-hidden="true" focusable="false">'+
 '<rect x="4" y="6" width="124" height="80" rx="8" fill="#6E4A2A"/>'+
 '<rect x="11" y="13" width="110" height="66" rx="3" fill="#1F2E28"/>'+
 '<rect x="11" y="13" width="110" height="16" rx="3" fill="#FFFFFF" opacity="0.04"/>'+
 '<g fill="none" stroke="#F4F1E4" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+bbStars()+'</g>'+
 '<text class="prof-chalk-aplus" x="36" y="64" text-anchor="middle" font-size="17" font-style="italic" font-family="\'Segoe Print\',\'Comic Sans MS\',cursive" fill="none" stroke="#F4F1E4" stroke-width="1.3">A+</text>'+
 '<g class="prof-teacher">'+
  '<circle cx="104" cy="44" r="6.5" fill="#EFC39B"/>'+
  '<path d="M97.5,42.5 a6.5,6.5 0 0 1 13,0 l0,-1.5 a6.5,6.5 0 0 0 -13,0 Z" fill="#4A3226"/>'+
  '<path d="M96,52 q8,-5 16,0 l3,24 q-11,5 -22,0 Z" fill="#4368B0"/>'+
  '<rect x="99" y="74" width="4.4" height="7" rx="2" fill="#2B3550"/>'+
  '<rect x="106" y="74" width="4.4" height="7" rx="2" fill="#2B3550"/>'+
  '<g class="prof-arm">'+
   '<rect x="99.6" y="54" width="5" height="18" rx="2.5" fill="#4368B0"/>'+
   '<circle cx="102.1" cy="73" r="2.8" fill="#EFC39B"/>'+
   '<rect x="100.7" y="74.6" width="2.8" height="6.4" rx="1.2" fill="#F7F3E6"/>'+
  '</g>'+
 '</g>'+
 '<g fill="#F7F3E6" class="prof-dust"><circle cx="98" cy="70" r="1.1"/><circle cx="106" cy="66" r="0.9"/><circle cx="101" cy="62" r="0.8"/></g>'+
 '<rect x="48" y="86" width="36" height="5" rx="2.5" fill="#54371E"/>'+
 '<rect x="57" y="84.4" width="11" height="3" rx="1.5" fill="#F7F3E6"/>'+
'</svg>';
function entryHTML(){
  const U=ui();
  /* Restored 2026-09-29: PraBin rejected the slim managed row ("I want old
     style") — the 2026-09-23 blackboard-scene banner is back: chalkboard +
     teacher SVG (6s chalk-draw loop) beside eyebrow + hook + sub. */
  return '<div class="prof-entry" id="homeProfEntry" role="button" tabindex="0" aria-label="'+U.esc(t('prof.entryTitle'))+' — '+U.esc(t('prof.entryHook'))+'">'+
    '<span class="prof-bb">'+BB_SVG+'</span>'+
    '<span class="grow">'+
      '<span class="prof-entry-eyebrow">'+U.esc(t('prof.entryTitle'))+'</span>'+
      '<span class="prof-entry-hook">'+U.esc(t('prof.entryHook'))+'</span>'+
      '<span class="prof-entry-s">'+U.esc(t('prof.entryHookSub'))+'</span>'+
    '</span></div>';
}
function bindEntry(scope){
  const root=scope||document;
  const b=root.querySelector?root.querySelector('#homeProfEntry'):document.getElementById('homeProfEntry');
  if(!b) return;
  const go=()=>openProf(null);
  b.onclick=go;
  b.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
}
HUB.professors={open:openProf,close:close,entryHTML:entryHTML,bindEntry:bindEntry,
  _reset:function(){ cur=null; query=''; sortMode='top'; },
  _state:pstate,_stats:statsOf,_all:allProfs,_byId:profById,
  _add:addReview,_vote:vote,_search:searchProfs,_reviews:reviewsOf,_hasProfanity:hasProfanity,
  _faculty:{ensure:ensureFaculty,slugFor:facultySlugFor,dirs:facultyProfs,reset:function(){FAC.idx=null;FAC.idxP=null;FAC.files={};FAC.fileP={};FAC.byId={};}}};
})();
