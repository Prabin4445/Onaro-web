/* HUB store: localStorage-backed state, sample seeds, UI helpers.
   Everything user-created is REAL local data. Seeds are flagged sample:true. */
(function(){
'use strict';
const KEY='hub_v1';
const uid=()=> 'id'+Date.now().toString(36)+Math.random().toString(36).slice(2,7);
/* Resilient fetch: retries + timeout (js/safeboot.js), plain-fetch fallback. */
const _fj=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){return fetch(u).then(function(r){if(!r.ok&&r.status!==0)throw new Error('http '+r.status);return r.json();});};
/* ---- people-discovery seeds (Workstream D) ----
   Sample people discoverable at their community. Schema:
   {id,name,phone,campus,skills[],stars,verified,jobsDone,exchanges,
    knownFor,mutualGroups[],avatarColor,discoverable,sample} */
function seedPeople(){
  const P=(name,phone,campus,skills,stars,verified,jobsDone,exchanges,knownFor,mutualGroups,avatarColor,bdays,brevs)=>({
    id:uid(),name,phone,campus,skills,stars,verified,jobsDone,exchanges,knownFor,
    mutualGroups:mutualGroups||[],avatarColor:avatarColor||0,discoverable:true,sample:true,
    loginDays:bdays||0,profReviews:brevs||0 /* badge seeds: real tier data per seed person */
  });
  return [
    P('Maya Chen','+1 555-902-1173','Riverside State',['Photography','Poster design','Video editing'],4.9,true,12,8,'Campus event photos & poster design',['Apartment 204'],1,200,12),
    P('Alex Rivera','+1 555-014-2288','Riverside State',['Moving help','Furniture assembly','Driving'],4.5,true,7,5,'Fast moves & IKEA builds',['Apartment 204'],0,45,0),
    P('Jordan Lee','+1 555-773-9041','Riverside State',['Math tutoring','Physics','Study guides'],5.0,false,4,3,'MATH 201 cram sessions',[],6,400,150),
    P('Sam Ortiz','+1 555-331-8870','Riverside State',['Bike repair','Cooking','Gardening'],4.2,false,9,11,'Flat fixes & Sunday curry nights',[],4,120,3),
    P('Casey Kim','+1 555-210-4471','Riverside State',['Web design','Coding','Logo design'],4.7,true,6,4,'Landing pages in a weekend',[],2,95,101),
    P('Riley Patel','+1 555-220-4816','Riverside State',['Dog sitting','Plant care','House cleaning'],4.8,false,5,9,'Plant rescues & puppy walks',[],3,20,0),
    P('Nora Feld','+1 555-410-2290','Maplewood Apartments',['Gardening','Compost','Seed swaps'],4.6,true,3,7,'Balcony gardens & seed swaps',[],0,500,0),
    P('Omar Haddad','+1 555-410-8834','Maplewood Apartments',['Grilling','Carpentry','Tool lending'],4.9,false,8,6,'Courtyard BBQs & shelf builds',[],5,10,0),
  ];
}
/* ---- class-reminder seeds (Workstream H1) ----
   Schema: {id,subject,room,days[0=Sun..6=Sat],start:'HH:MM',end:'HH:MM',sample} */
function seedClasses(){
  return [
    {id:uid(),subject:'Biology',room:'204',days:[1,3,5],start:'10:00',end:'11:00',sample:true,createdAt:Date.now()},
    {id:uid(),subject:'Math 201',room:'118',days:[2,4],start:'14:00',end:'15:30',sample:true,createdAt:Date.now()},
  ];
}
/* ---- community-group seeds (Groups feature, 2026-09-22) ----
   Interest groups with admin / live-draft / join-request flow.
   Schema: {id,name,desc,emoji,photo,admin,mine,members[],requests[{name,at}],
            live,lat,lng,sample,createdAt}
   mine=true marks groups the local user administers (admin name renders as
   the user's own name). Coordinates scatter within ~50 mi of the demo
   default location (Dallas, 32.8674,-96.9885); discovery filters by radius. */
var CG_HOME={lat:32.8674,lng:-96.9885};
function seedCGroups(){
  const now=Date.now(), H=3600e3;
  /* demo chat threads (2026-09-22): sample-flagged like the rest of the
     preview. Real multi-device messaging needs a backend. */
  const M=(from,ago,kind,body)=>Object.assign(
    {id:uid(),from:from,at:now-ago,kind:kind,sample:true},body||{});
  const mathChat=[
    M('Jordan Lee',6*H,'text',{text:'Problem set 4 is brutal. Anyone free Thursday? 😅'}),
    M('Priya Nair',5*H,'text',{text:'Thursday works — I will bring snacks 🍿'}),
    M('Jordan Lee',4.6*H,'image',{data:'chat/memes/seed-photo.jpg',name:'battle-station.jpg'}),
    M('Priya Nair',4*H,'meme',{data:'chat/memes/meme-whiteboard.png',name:'5th time'})
  ];
  const pubgChat=[
    M('Alex Rivera',5*H,'text',{text:'Squad up at 9 tonight? 🎮'}),
    M('Sam Ortiz',4*H,'text',{text:'In. New drop spot — trust me 🪂 https://example.com/drop-map'}),
    M('Alex Rivera',3*H,'gif',{data:'chat/memes/gif-hype.png',name:'Hype'})
  ];
  const G=(name,desc,emoji,admin,members,lat,lng,live,extra)=>Object.assign({
    id:uid(),name:name,desc:desc,emoji:emoji||'👥',photo:'',admin:admin,mine:false,
    members:members||[admin],requests:[],live:!!live,lat:lat,lng:lng,
    sample:true,createdAt:now,chat:[]
  },extra||{});
  return [
    G('Math Study Group','MATH 201 cram sessions — problem sets every Tue/Thu. All levels welcome.','📐',
      'Jordan Lee',['Jordan Lee','Priya Nair'],32.9124,-96.9885,true,{chat:mathChat}),
    G('PUBG Squad','Squad up nightly after 9 PM. Mic required, no rage-quitters.','🎮',
      'Alex Rivera',['Alex Rivera','Sam Ortiz'],32.8000,-96.9500,true,{chat:pubgChat}),
    G('Morning Runners','Easy 5K loops at dawn, coffee after. Beginners welcome!','🏃',
      'Sam Ortiz',['Sam Ortiz'],32.8674,-96.7500,false),
    G('Guitar Jammers','Acoustic jams on Thursdays. Bring your own axe — beginners welcome.','🎸',
      'Maya Chen',['Maya Chen','Riley Patel'],32.7000,-97.1000,true),
    /* user-administered seed: demonstrates the admin/approve flow.
       admin/members resolve to the local user's name via helpers (mine=true). */
    G('Weekend Hikers','Day hikes within an hour of the city. Carpool from downtown.','🥾',
      '',[],32.8674,-97.0500,true,
      {mine:true,requests:[{name:'Riley Patel',at:now-3*H}]}),
  ];
}
const esc=s=> String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/* Workstream F: currency-aware price formatting. Symbol follows the device's
   selected country (HUB.i18n.currencySymbol); symbol-only, not full locale
   money formatting (production-backend work — see the workstream E note). */
const fmt$=n=>{ let sym='$'; try{ if(HUB.i18n&&HUB.i18n.currencySymbol) sym=HUB.i18n.currencySymbol(); }catch(e){} return sym+Number(n).toFixed(2).replace(/\.00$/,''); };
const timeAgo=ts=>{const _t=HUB.i18n.t,s=(Date.now()-ts)/1e3;if(s<60)return _t('time.justNow');if(s<3600)return _t('time.mAgo',{n:Math.floor(s/60)});if(s<86400)return _t('time.hAgo',{n:Math.floor(s/3600)});return _t('time.dAgo',{n:Math.floor(s/86400)});};
const todayStr=()=> new Date().toISOString().slice(0,10);

function seeds(){
  const now=Date.now();
  /* Production: no sample/demo/fake data. All collections start empty.
     Real data comes from the backend API and user actions. */
  return {
    profile:{name:'',email:'',phone:'',campus:'',audience:'',avatarColor:0,verified:false,stars:0,jobsDone:0,createdAt:now,sample:false,discoverable:true},
    prefs:{},
    people:[],
    listings:[],
    jobs:[],
    threads:[],
    campuses:[],
    classes:[],
    classFires:[],
    cgroups:[],
    tasks:[],
    notes:[],
  };
}

let state;
/* Self-healing state load (js/safeboot.js): corrupt JSON is backed up before
   replacement, and missing top-level keys are backfilled from fresh seeds —
   a partial/legacy state can never crash the app again (e.g. the old
   state.households undefined crash in householdOwed). */
if(window.HUB&&HUB.safe&&HUB.safe.loadState){
  state=HUB.safe.loadState(KEY,seeds); save();
}else{
  try{ state=JSON.parse(localStorage.getItem(KEY))||null; }catch(e){ state=null; }
  if(!state||typeof state!=='object'||Array.isArray(state)){ state=seeds(); save(); }
}
if(!state.prefs||typeof state.prefs!=='object') state.prefs={};
if(!state.reports) state.reports=[];
if(!state.blocked) state.blocked=[];
if(state.prefs.privacyCampus==null) state.prefs.privacyCampus=true;
if(state.prefs.privacyLocation==null) state.prefs.privacyLocation=false;
/* Workstream D: people-discovery seeds + the discoverability privacy flag.
   Legacy saved profiles default to discoverable so the demo surface is alive. */
if(!Array.isArray(state.people)) state.people=seedPeople();
if(state.profile&&state.profile.discoverable==null) state.profile.discoverable=true;
    /* Workstream H migrations: class schedule on legacy saved state */
if(!Array.isArray(state.classes)) state.classes=seedClasses();
/* Groups feature (2026-09-22): community groups live under state.cgroups.
   Legacy saved states predate the feature, so seed once. */
if(!Array.isArray(state.cgroups)) state.cgroups=seedCGroups();
else{
  /* Group chat (2026-09-22) arrived after the groups seed: backfill chat
     arrays onto groups that predate it, matched by seed name. */
  try{
    const byName={};
    seedCGroups().forEach(function(g){ if(g.chat&&g.chat.length) byName[g.name]=g.chat; });
    state.cgroups.forEach(function(g){ if(!Array.isArray(g.chat)) g.chat=byName[g.name]||[]; });
  }catch(e){}
}
/* Stories removed 2026-09-22: drop any legacy story state. */
delete state.stories; delete state.storyBin; delete state.highlights;
if(state.prefs) delete state.prefs.storyBlocks;
if(!Array.isArray(state.classFires)) state.classFires=[];
/* Daily tab migrations */
if(!Array.isArray(state.tasks)) state.tasks=[];
if(!Array.isArray(state.notes)) state.notes=[];
if(!Array.isArray(state.capsules)) state.capsules=[];
/* Social: follow graph. Sample-backed in this build (production = server accounts).
   followers seeds: two sample people follow you so the mutual-follow flow is demonstrable. */
if(!Array.isArray(state.following)) state.following=[];
if(!Array.isArray(state.followers)){
  state.followers=[];
  const byName={};
  for(const p of (state.people||[])) if(p&&p.name) byName[p.name]=p.id;
  for(const n of ['Maya Chen','Alex Rivera']) if(byName[n]) state.followers.push(byName[n]);
}
/* Follow-event log: timestamped "X followed you" entries so the notification
   center can surface follow alerts with a profile deep-link. Backfilled once
   for pre-existing seeds (production = server push). */
if(!Array.isArray(state.followerEvents)) state.followerEvents=[];
if(state.followers.length&&!state.followerEvents.length){
  const nowEv=Date.now();
  state.followerEvents=state.followers.map((id,i)=>({id:id,ts:nowEv-i*36e5}));
}
function save(){ if(window.HUB&&HUB.safe&&HUB.safe.saveState){ HUB.safe.saveState(KEY,state); return; } try{ localStorage.setItem(KEY,JSON.stringify(state)); }catch(e){} }

/* ---- derived helpers ---- */
function myName(){ return state.profile.name||'you'; }
function householdOwed(){ // {owedToMe, billDue}
  let owedToMe=0, billDue=null, earliest='';
  for(const h of (state.households||[])){
    const n=h.members.length||1, me=myName();
    for(const b of h.bills){
      const share=b.amount/n;
      if(b.paidBy===me) owedToMe+=(b.amount-share);
    }
    for(const b of h.bills){ if(!billDue||String(b.due)<earliest){billDue=b;earliest=String(b.due);} }
  }
  return {owedToMe:Math.max(0,Math.round(owedToMe*100)/100),billDue};
}
function unreadCount(){ return state.threads.reduce((a,t)=>a+(t.unread||0),0); }
function isBlocked(name){ return !!name && state.blocked.some(b=>b.toLowerCase()===String(name).toLowerCase()); }
function clearSamples(){
  for(const k of ['listings','jobs','events','campusPosts','memory','contacts','threads','people','classes','cgroups']) state[k]=state[k].filter(x=>!x.sample);
  state.households=state.households.filter(h=>!h.sample);
  save();
}

/* ---- ui helpers ---- */
/* Toast: snappy single-toast. A new toast replaces the old one immediately
   (no stacking — 3 quick taps used to queue 8+ seconds of toasts), visible
   1.2s + 0.25s fade. Cleared on tab switch via clearToasts(). */
function clearToasts(){ try{ document.getElementById('toastHost').innerHTML=''; }catch(e){} }
function toast(msg, silent){
  const h=document.getElementById('toastHost'); if(!h) return;
  h.innerHTML='';
  const d=document.createElement('div'); d.className='toast'; d.textContent=msg; h.appendChild(d);
  setTimeout(function(){ d.style.opacity='0'; d.style.transition='opacity .25s'; setTimeout(function(){ d.remove(); },260); },1200);
}
  /* 2026-09-29: all in-app sound effects removed on PraBin's order —
     toasts (incl. profile/gender saves) are now completely silent.
     Only the call ringtone remains audible anywhere in the app. */
function openSheet(html){ const host=document.getElementById('sheetHost'),box=document.getElementById('sheetBox');
  /* Universal ✕: every bottom sheet gets a dismiss button unless it already
     ships its own close control (astro calendar
     [data-close]). The global [data-close] delegation in app.js handles taps. */
  const hasOwn=html.indexOf('data-close')!==-1;
  box.innerHTML=(hasOwn?'':'<button class="sheetx" data-close aria-label="Close">✕</button>')+html;
  host.hidden=false; box.scrollTop=0;
  host.onclick=e=>{ if(e.target===host) closeSheet(); }; }
function closeSheet(){ document.getElementById('sheetHost').hidden=true; }
function stars(n){ const f=Math.round(n); return '★'.repeat(f)+'☆'.repeat(5-f); }
function sampleBadge(s){ return s?'<span class="badge sample">'+HUB.i18n.t('honesty.sample')+'</span>':''; }
function initials(name){ return (name||'?').trim().split(/\s+/).map(w=>w[0]).join('').slice(0,2).toUpperCase(); }

/* ---- user avatar (profile editing) — one source of truth ----
   profile.photo is a downscaled JPEG dataURL kept in localStorage
   (browser-only, set from ME > Edit profile). avatarFor(name) returns an
   <img> when the name is the user's and a photo exists, else initials text.
   Call sites (me hero, market sellers/comments) use this
   so a photo change propagates everywhere instantly. */
function mePhoto(){ return (state.profile&&state.profile.photo)||null; }
function isMe(name){ return String(name||'').trim().toLowerCase()===String(myName()||'').trim().toLowerCase(); }
function avatarFor(name){
  if(isMe(name)&&mePhoto()) return '<img class="avimg" src="'+esc(mePhoto())+'" alt="">';
  return esc(initials(name));
}

/* ---- verified badge (PraBin's design): blue tick on top, small "Verified"
      caption underneath. The single source of truth used everywhere a
      verified identity is shown: ME hero, people cards, chat headers.
      Unverified keeps the existing pill. */
function verifiedBadge(){
  return '<span class="vbadge"><span class="vbadge-tick" aria-hidden="true">✓</span>'+
    '<span class="vbadge-cap">'+esc(HUB.i18n.t('vbadge.verified'))+'</span></span>';
}
function greeting(){ const h=new Date().getHours(),_t=HUB.i18n.t; return h<12?_t('time.greetMorning'):h<17?_t('time.greetAfternoon'):_t('time.greetEvening'); }

/* ---- Communities picker (Workstream C: Campus → Communities reframe) ----
   state.campuses keeps its storage key for legacy localStorage compatibility.
   Seeds mix sample campuses + sample neighborhoods/areas; the picker groups
   them and labels each group as sample. Orphaned values (e.g. from older
   seeds) are appended so a stored choice never silently unselects. */
const CAMPUS_NAMES=['Riverside State','City College','Northlake University','Westfield Tech'];
function isCampusCommunity(name){ return CAMPUS_NAMES.indexOf(name)!==-1; }
function communityOptions(selected){
  const list=state.campuses||[];
  const opt=c=>'<option value="'+esc(c)+'"'+(c===selected?' selected':'')+'>'+esc(c)+'</option>';
  const campuses=list.filter(isCampusCommunity), areas=list.filter(c=>!isCampusCommunity(c));
  let html='';
  if(campuses.length) html+='<optgroup label="'+HUB.i18n.t('ob.campusesSample')+'">'+campuses.map(opt).join('')+'</optgroup>';
  if(areas.length) html+='<optgroup label="'+HUB.i18n.t('ob.areasSample')+'">'+areas.map(opt).join('')+'</optgroup>';
  if(selected&&list.indexOf(selected)===-1) html+='<option value="'+esc(selected)+'" selected>'+esc(selected)+'</option>';
  return html;
}

/* ================= ONARO-INTL (Workstream F) =================
   World institution directory: data/colleges.json holds compact
   [name, country, city, lat, lng] arrays built from Wikidata (CC0)
   plus a US Dept of Education College Scorecard supplement; data/schools_us.json
   holds the official NCES K-12 directory (CCD 2024-25 public schools with EDGE
   2023-24 geocodes + PSS 2023-24 private schools, built by data/build_schools_us.py).
   Both load LAZILY on first picker open (memory cache + best-effort
   localStorage so it works offline once fetched; the merged file can exceed
   localStorage quota, in which case it simply re-fetches next session).
   No API keys, no live lookups — the picker labels it a bundled directory,
   never "live". School rows missing coordinates keep lat/lng null and stay
   searchable; only map/near-me math may skip them. */
const COLLS_KEY='orbit_colleges_v3';
let collegesPromise=null, collegesCache=null, collegesFailed=false;
/* country code <-> English country name helpers (records carry names only) */
function countryEnByCode(cc){
  try{ const c=HUB.i18n.countryByCode(cc); return c?(c.en||'') : ''; }catch(e){ return ''; }
}
let _ccRev=null;
function codeByCountryEn(name){
  if(!_ccRev){
    _ccRev={};
    try{
      for(const c of (HUB.i18n.COUNTRIES||[])) if(c&&c.en&&c.c&&!_ccRev[c.en]) _ccRev[c.en]=c.c;
    }catch(e){}
  }
  return _ccRev[name]||'';
}
function loadColleges(){
  if(collegesCache) return Promise.resolve(collegesCache);
  if(collegesPromise) return collegesPromise;
  const pickRows=j=>Array.isArray(j&&j.data)?j.data:(Array.isArray(j&&j.records)?j.records:(Array.isArray(j)?j:null));
  try{
    const raw=localStorage.getItem(COLLS_KEY);
    if(raw){
      const rows=pickRows(JSON.parse(raw));
      if(rows&&rows.length){ collegesCache=rows; return Promise.resolve(rows); }
    }
  }catch(e){}
  collegesPromise=Promise.all([_fj('data/colleges.json'),_fj('data/schools_us.json')])
    .then(js=>{
      const rows=[];
      for(const j of js){ const part=pickRows(j)||[]; for(let k=0;k<part.length;k++) rows.push(part[k]); }
      collegesCache=rows;
      try{ localStorage.setItem(COLLS_KEY, JSON.stringify({v:1,data:rows})); }catch(e){}
      return rows;
    })
    .catch(e=>{ collegesFailed=true; collegesPromise=null; throw e; });
  return collegesPromise;
}
/* fast client-side search: prefix matches on name/city first, then
   substring matches (name/city/country). cc=null searches all countries;
   a country code is matched against the record's English country name. */
function searchColleges(q, cc, limit){
  const rows=collegesCache||[];
  limit=limit||60;
  const needle=String(q||'').trim().toLowerCase();
  const wantCountry=cc?countryEnByCode(cc):'';
  const out=[], sub=[];
  for(let i=0;i<rows.length;i++){
    const r=rows[i];
    if(wantCountry&&r[1]!==wantCountry) continue;
    if(!needle){ out.push(r); if(out.length>=limit) break; continue; }
    const nm=String(r[0]).toLowerCase(), cy=String(r[2]).toLowerCase();
    const nn=needle.replace(/\s+/g,''), nmn=nm.replace(/\s+/g,''), cyn=cy.replace(/\s+/g,'');
    if(nm.indexOf(needle)===0||cy.indexOf(needle)===0||nmn.indexOf(nn)===0||cyn.indexOf(nn)===0) out.push(r);
    else if(nm.indexOf(needle)!==-1||cy.indexOf(needle)!==-1||String(r[1]).toLowerCase().indexOf(needle)!==-1||nmn.indexOf(nn)!==-1||cyn.indexOf(nn)!==-1){
      if(sub.length<limit) sub.push(r);
    }
    if(out.length>=limit) break;
  }
  return out.concat(sub).slice(0,limit);
}
function collegeCountries(){
  const seen={}, rows=collegesCache||[];
  for(const r of rows){ if(r[1]&&!seen[r[1]]) seen[r[1]]=codeByCountryEn(r[1]); }
  return Object.keys(seen).map(name=>({iso:seen[name],name:name}))
    .sort((a,b)=>a.name<b.name?-1:(a.name>b.name?1:0));
}
function collegesMeta(){ return {count:(collegesCache||[]).length, countries:collegeCountries().length, failed:collegesFailed}; }

/* icon follows what the user actually picked: 🎓 for schools/colleges,
   🏘️ for neighborhoods/communities. Older profiles without a stored kind
   fall back to a name heuristic. */
const SCHOOL_WORDS=/college|universit|school|institute|academy|polytechnic|campus|colegio|escuela|universidad|instituto|école|université|schule|hochschule|università|scuola|istituto|大学|学校|学院|대학교|학교|جامعة|مدرسة|कलेज|विश्वविद्यालय|विद्यालय|महाविद्यालय|कॉलेज|पाठशाला/i;
function campusEmoji(name, kind){
  if(kind==='school') return '🎓';
  if(kind==='community') return '🏘️';
  return SCHOOL_WORDS.test(String(name||''))?'🎓':'🏘️';
}

/* Searchable, country-grouped institution picker (bottom sheet).
   opts: {mode:'student'|'community', onPick(rec)}.
   rec for directory picks: {name,country,city,lat,lng,iso,sample:false,kind:'school'};
   for sample picks: {name,sample:true,kind:'school'|'community'};
   for manual picks: {name,city,country,iso,sample:false,custom:true,kind:'school'|'community'}.
   kind follows the picker mode so the icon matches what was picked. */
function openInstitutionPicker(opts){
  opts=opts||{};
  const onPick=opts.onPick||function(){};
  const mode=opts.mode==='community'?'community':'student';
  const tr=HUB.i18n.t, i18n=HUB.i18n;
  const lang=i18n.getLang();
  const userCC=i18n.getCountry()||i18n.guessCountry();
  let q='', countrySel='__user__', flat=[], loading=true, failed=false, deb=null, booted=false;

  const effIso=()=> countrySel==='__all__'?null:(countrySel==='__user__'?userCC:countrySel);
  const hasUserCC=()=> collegeCountries().some(c=>c.iso===userCC);

  function countryOptions(){
    const u=i18n.countryByCode(userCC);
    const ulab=u?(u.f+' '+tr('intl.yourCountry')+': '+i18n.countryName(u,lang)):tr('intl.yourCountry');
    let h='<option value="__user__">'+esc(ulab)+'</option>';
    h+='<option value="__all__">'+esc(tr('intl.allCountries'))+'</option>';
    for(const c of collegeCountries()) h+='<option value="'+esc(c.iso)+'">'+esc(c.name)+'</option>';
    return h;
  }
  function rowHTML(r, idx){
    const meta=[r[2],r[1]].filter(Boolean).join(', ');
    return '<div class="item intl-row"><div class="grow"><h3>'+esc(r[0])+'</h3>'+
      '<div class="meta">'+esc(meta)+'</div></div>'+
      '<button class="btn btn-sm btn-primary intl-pick" data-i="'+idx+'">'+esc(tr('intl.dirPick'))+'</button></div>';
  }
  function pickInstitution(r){
    const rec={name:r[0],country:r[1],city:r[2],lat:r[3],lng:r[4],iso:codeByCountryEn(r[1]),sample:false,kind:'school'}; /* directory = institutions only */
    closeSheet(); onPick(rec);
  }
  function pickSample(name){
    closeSheet(); onPick({name:name,sample:true,kind:mode==='student'?'school':'community'});
  }
  function pickCustom(name, city){
    const iso=effIso()||userCC||'';
    closeSheet();
    onPick({name:name,country:countryEnByCode(iso),city:city||'',lat:null,lng:null,iso:iso,sample:false,custom:true,kind:mode==='student'?'school':'community'});
  }
  let manualMode=false;
  function showManualForm(){
    manualMode=true;
    const host=document.getElementById('intlResults'); if(!host) return;
    host.innerHTML=
      '<div class="field"><label>'+esc(tr('intl.dirYourSchool'))+'</label>'+
      '<input class="input" id="intlCustomName" autocomplete="off" placeholder="'+esc(tr('intl.dirYourSchool'))+'"></div>'+
      '<div class="field"><label>'+esc(tr('intl.dirYourCity'))+'</label>'+
      '<input class="input" id="intlCustomCity" autocomplete="off" placeholder="'+esc(tr('intl.dirYourCity'))+'"></div>'+
      '<button class="btn btn-primary btn-block" id="intlCustomAdd">'+esc(tr('intl.dirAddSchool'))+'</button>'+
      '<button class="btn btn-line btn-block" id="intlCustomCancel" style="margin-top:8px">'+esc(tr('common.cancel'))+'</button>';
    document.getElementById('intlCustomCancel').onclick=()=>{ manualMode=false; draw(); };
    document.getElementById('intlCustomAdd').onclick=()=>{
      const nm=(document.getElementById('intlCustomName').value||'').trim();
      if(!nm){ document.getElementById('intlCustomName').focus(); return; }
      const cy=(document.getElementById('intlCustomCity').value||'').trim();
      pickCustom(nm, cy);
    };
    setTimeout(()=>{ const i=document.getElementById('intlCustomName'); if(i) i.focus(); },60);
  }
  function draw(){
    const host=document.getElementById('intlResults'); if(!host) return;
    if(manualMode) return;
    if(loading){
      host.innerHTML='<div class="empty"><div class="big">🌍</div><p>'+esc(tr('intl.dirLoading'))+'</p></div>';
      return;
    }
    if(failed){
      host.innerHTML='<div class="empty"><div class="big">📡</div><p>'+esc(tr('intl.dirFail'))+'</p>'+
        '<button class="btn btn-line btn-sm" id="intlRetry">'+esc(tr('intl.dirRetry'))+'</button></div>';
      document.getElementById('intlRetry').onclick=()=>{ failed=false; loading=true; draw(); loadColleges().then(ok).catch(bad); };
      return;
    }
    const rows=searchColleges(q, effIso(), 120);
    flat=[]; let h='';
    if(!rows.length){
      h='<div class="empty"><div class="big">🔍</div><p>'+esc(tr(q?'intl.dirEmpty':'intl.dirEmptyCountry'))+'</p></div>';
    }else if(!q){
      /* country-grouped browsing: headers per country, 8 rows each */
      const groups={}, order=[];
      for(const r of rows){
        const k=r[1];
        if(!groups[k]){ groups[k]=[]; order.push(k); }
        if(groups[k].length<8) groups[k].push(r);
      }
      for(const k of order.slice(0,10)){
        const g=groups[k];
        h+='<div class="intl-chead">'+esc(g[0][1])+' · '+esc(tr('intl.dirCount',{n:g.length}))+'</div>';
        for(const r of g){ flat.push(r); h+=rowHTML(r, flat.length-1); }
      }
    }else{
      for(const r of rows.slice(0,60)){ flat.push(r); h+=rowHTML(r, flat.length-1); }
    }
    /* sample communities stay, clearly badged, beside the real directory */
    const samples=(state.campuses||[]).filter(c=>mode==='student'?isCampusCommunity(c):!isCampusCommunity(c));
    if(samples.length){
      h+='<div class="intl-chead">'+esc(tr('intl.samplesTitle'))+'</div>';
      for(const s of samples){
        h+='<div class="item intl-row"><div class="grow"><h3>'+esc(s)+'</h3></div>'+sampleBadge(true)+
          '<button class="btn btn-sm btn-line intl-spick" data-name="'+esc(s)+'">'+esc(tr('intl.dirPick'))+'</button></div>';
      }
    }
    host.innerHTML=h;
    host.querySelectorAll('.intl-pick').forEach(b=>{ b.onclick=()=>{ const r=flat[Number(b.dataset.i)]; if(r) pickInstitution(r); }; });
    host.querySelectorAll('.intl-spick').forEach(b=>{ b.onclick=()=>pickSample(b.dataset.name); });
    const addRow=document.createElement('div');
    addRow.className='empty'; addRow.style.marginTop='14px';
    addRow.innerHTML='<p>'+esc(tr('intl.dirAddMissing'))+'</p>'+
      '<button class="btn btn-line btn-sm" id="intlAddManual">'+esc(tr('intl.dirAddManually'))+'</button>';
    host.appendChild(addRow);
    document.getElementById('intlAddManual').onclick=showManualForm;
  }
  function ok(){
    loading=false; failed=false;
    if(!booted){
      booted=true;
      const sel=document.getElementById('intlCountry');
      if(sel){
        sel.innerHTML=countryOptions();
        if(!hasUserCC()){ countrySel='__all__'; sel.value='__all__'; }
      }
    }
    draw();
  }
  function bad(){ loading=false; failed=true; draw(); }

  openSheet(
    '<h2>'+esc(tr('intl.dirTitle'))+'</h2>'+
    '<div style="margin:6px 0 10px"><span class="badge sample">'+esc(tr('intl.bundledDir'))+'</span></div>'+
    '<p class="sub" style="margin-bottom:12px">'+esc(tr('intl.dirSub'))+'</p>'+
    '<div class="field"><input class="input" id="intlSearch" placeholder="'+esc(tr('intl.dirSearch'))+'" autocomplete="off"></div>'+
    '<div class="field"><label>'+esc(tr('welcome.countryLabel'))+'</label><select class="input" id="intlCountry"><option>'+esc(tr('intl.dirLoading'))+'</option></select></div>'+
    '<div id="intlResults" class="intl-results"></div>'+
    '<p class="hint" style="margin-top:10px">'+esc(tr('intl.dirNote'))+'</p>'
  );
  draw();
  document.getElementById('intlSearch').oninput=e=>{ q=e.target.value; clearTimeout(deb); deb=setTimeout(draw,180); };
  document.getElementById('intlCountry').onchange=e=>{ countrySel=e.target.value; draw(); };
  loadColleges().then(ok).catch(bad);
}

/* Keyboard dodge (2026-09-22): when the iOS/Android keyboard opens, the message
   list must stay visible above a docked composer, like iPhone Messages.
   The viewport meta carries interactive-widget=resizes-content so modern iOS
   shrinks the layout viewport (pure CSS then fixes the thread: the fixed
   .chatroot shrinks, .chatpanel{height:92%} follows, the composer docks above
   the keyboard, the flex:1 message list stays scrollable). This visualViewport
   fallback covers older iOS / odd webviews where the layout viewport does NOT
   shrink: while a chat composer is open and the visual viewport is much shorter
   than the layout viewport, the panel is sized to the visual height explicitly.
   Idempotent; safe to call from any thread view; no new strings. */
let kbVvBound=false;
function kbSnap(){
  /* iMessage-like: if the reader is already near the latest messages, keep the
     latest visible when the keyboard opens or the field is focused; never yank
     someone who scrolled up to read history. */
  ['gcScroll','chatScroll'].forEach(function(id){
    try{
      const sc=document.getElementById(id);
      if(sc&&sc.scrollHeight-sc.scrollTop-sc.clientHeight<140) sc.scrollTop=sc.scrollHeight;
    }catch(e){}
  });
}
/* QA hook: pass a forced visual height (e.g. 500) to simulate the keyboard;
   call with no arg for the live reading. Returns 'dodged'|'restored'|'skip'. */
function kbVvApply(forcedH,forcedOff){
  try{
    const rootEl=document.getElementById('chatRoot');
    const panelEl=document.getElementById('chatPanel');
    if(!rootEl||rootEl.hidden||!panelEl) return 'skip';
    if(!panelEl.querySelector('#gcText,#chatText')) return 'skip'; /* thread list: untouched */
    const lh=window.innerHeight||0;
    const vv=window.visualViewport;
    const vh=(typeof forcedH==='number')?forcedH:(vv?vv.height:lh);
    const vo=(typeof forcedOff==='number')?forcedOff:(vv?(vv.offsetTop||0):0);
    if(vh<lh-100){
      /* remember who was pinned to the latest message BEFORE the shrink:
         shrinking the panel inflates the distance-from-bottom, which would
         otherwise fool kbSnap's reading-history guard */
      const pins=[false,false];
      ['gcScroll','chatScroll'].forEach(function(id,i){
        try{
          const sc=document.getElementById(id);
          pins[i]=!!(sc&&sc.scrollHeight-sc.scrollTop-sc.clientHeight<140);
        }catch(e){}
      });
      const px=Math.max(240,Math.round(vh*0.92))+'px';
      panelEl.style.height=px; panelEl.style.maxHeight=px;
      /* old-iOS geometry: the layout viewport stays full-height, so the
         bottom-anchored panel must be lifted by the keyboard height to sit
         inside the visible area. Modern iOS shrinks the layout viewport
         (interactive-widget=resizes-content), in which case lift is 0. */
      const lift=Math.max(0,Math.round(lh-vh-vo));
      panelEl.style.transform=lift>0?('translateY('+(-lift)+'px)'):'';
      ['gcScroll','chatScroll'].forEach(function(id,i){
        try{
          const sc=document.getElementById(id);
          if(sc&&pins[i]) sc.scrollTop=sc.scrollHeight; /* stay pinned to latest */
        }catch(e){}
      });
      kbSnap();
      return 'dodged';
    }
    panelEl.style.height=''; panelEl.style.maxHeight=''; panelEl.style.transform='';
    return 'restored';
  }catch(e){ return 'error'; }
}
function dodgeKeyboard(){
  if(!window.visualViewport) return kbVvApply;
  if(!kbVvBound){
    kbVvBound=true;
    window.visualViewport.addEventListener('resize',function(){ kbVvApply(); });
  }
  return kbVvApply;
}

/* ================= HUB.fx — feel-polish helpers =================
   countUp(el, from, to, opts): Stripe/Revolut-style digit morph for hero
   numbers. ~700ms ease-out cubic; tabular-nums so digits never jitter;
   reduced-motion -> final value instantly, no animation. Only animates
   when from!==to; a re-triggered tween cancels the stale one via a token
   on the element. opts is a duration number OR {dur, decimals, format},
   where format(v) maps the raw tween value to display text (thousand
   separators, %, etc.).
   haptic(kind): Android-only vibration vocabulary. iOS Safari does NOT
   implement navigator.vibrate, so everything is feature-guarded and a
   no-op where unsupported. Kinds: light (button press), select (picker
   change), medium (send / sheet dismiss), success (action completed),
   celebrate (milestone). Never fire on scroll, page load, or typing —
   call sites own that discipline. */
function fxReduced(){ return !!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches); }
var _fxToken=0;
function countUp(el, from, to, opts){
  try{
    if(!el) return;
    var o=(typeof opts==='number')?{dur:opts}:(opts||{});
    var durMs=Math.max(0, o.dur!=null?o.dur:700);
    var dec=(o.decimals!=null)?o.decimals:0;
    var fmt=o.format||function(v){ return dec>0?Number(v).toFixed(dec):String(Math.round(v)); };
    from=Number(from); to=Number(to);
    if(!isFinite(from)) from=0; if(!isFinite(to)) to=0;
    try{ el.style.fontVariantNumeric='tabular-nums'; }catch(e2){} /* no layout shift mid-tween */
    if(from===to||fxReduced()){ el.textContent=fmt(to); return; }
    var token=++_fxToken; el._fxCountToken=token;
    var t0=performance.now();
    (function frame(now){
      try{
        if(el._fxCountToken!==token) return; /* superseded by a newer tween */
        var ms=(typeof now==='number')?now:performance.now();
        /* clamp p to [0,1]: a stale rAF timestamp (seen in headless
           Chromium) would otherwise drive the cubic ease far outside
           [from,to] and flash a bogus number. */
        var p=Math.min(1,Math.max(0,(ms-t0)/Math.max(1,durMs)));
        var e=1-Math.pow(1-p,3); /* ease-out cubic */
        el.textContent=fmt(from+(to-from)*e);
        if(p<1) requestAnimationFrame(frame);
        else el.textContent=fmt(to); /* land exactly on the target */
      }catch(e3){}
    })();
  }catch(e){}
}
var FX_HAPTIC={light:10, select:15, medium:50, success:[15,30,15], celebrate:[50,30,50]};
function haptic(kind){
  try{
    if(!navigator.vibrate) return; /* iOS Safari / desktop: no-op */
    navigator.vibrate(FX_HAPTIC[kind]||FX_HAPTIC.light);
  }catch(e){}
}

window.HUB=Object.assign(window.HUB||{},{
  intl:{loadColleges,searchColleges,collegeCountries,collegesMeta},
  fx:{countUp:countUp,haptic:haptic},
  store:{get state(){return state;},save,uid,clearSamples,householdOwed,unreadCount,myName,todayStr,cgHome:CG_HOME,
    add(k,obj){state[k].unshift(Object.assign({id:uid(),createdAt:Date.now(),sample:false},obj));save();},
    remove(k,id){state[k]=state[k].filter(x=>x.id!==id);save();},
    find(k,id){return state[k].find(x=>x.id===id);},
  },
  ui:{toast,clearToasts,openSheet,closeSheet,esc,fmt$,timeAgo,stars,sampleBadge,initials,greeting,isBlocked,communityOptions,isCampusCommunity,openInstitutionPicker,campusEmoji,mePhoto,isMe,avatarFor,verifiedBadge,dodgeKeyboard,kbSnap,_kbApply:kbVvApply},
});
})();
