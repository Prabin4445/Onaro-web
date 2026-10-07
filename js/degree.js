/* HUB Degree Plan Tracker (2026-09-29): official catalog degree plans with
   progress tracking. No bottom tab (standing rule) — opened from the Home tab
   "Degree plans" entry card as a full overlay (professors .chatroot pattern).
   Data: data/degrees/index.json + data/degrees/<slug>.json, built from official
   college catalogs (see data/degrees/PIPELINE.md). Every number comes from the
   JSON — no fake data, no invented majors.
   Progress: store.state.degree = {active, progress:{slug:{done:{slotId:{code,title,credits,ts}}, startYear, intake:{term,year}}}}.
   intake = the term/year the student started (fall|spring|summer + year).
   Semester labels rotate from the intake (Spring 2027 start -> Sem 1 =
   "Spring 2027", Sem 2 = "Fall 2027", ...); the course sequence itself never
   changes, only the term labels. Default intake = Fall of startYear, so
   existing users see zero change until they touch the selector.
   All completion feedback is VISUAL ONLY (glow burst + tile flip) — the app's
   sound policy leaves only the call ringtone audible.
   Classic IIFE. const t=function(k,v){return HUB.i18n.t(k,v);} — never shadow t. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const esc=function(s){ return HUB.ui.esc(s); };
/* Resilient fetch: retries + timeout (js/safeboot.js), plain-fetch fallback. */
const _fj=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){return fetch(u).then(function(r){if(!r.ok&&r.status!==0)throw new Error('http '+r.status);return r.json();});};
const store=function(){ return HUB.store; };
const ui=function(){ return HUB.ui; };

/* stylesheet injection (gpa.js pattern — keeps index.html edits to one line) */
(function(){
  if(document.querySelector('link[data-degree-css]')) return;
  const l=document.createElement('link');
  l.rel='stylesheet'; l.href='css/degree.css'; l.setAttribute('data-degree-css','1');
  document.head.appendChild(l);
})();

/* ---------------- data (promise-cached, professors.js pattern) ---------------- */
const DATA={idx:null,idxP:null,idxFailed:false,files:{},fileP:{}};
function degIndex(){
  if(DATA.idx) return Promise.resolve(DATA.idx);
  if(!DATA.idxP) DATA.idxP=Promise.resolve()
    /* Phase 1 backend (js/api.js): API first when configured, static fallback. */
    .then(function(){
      if(window.HUB&&HUB.api&&HUB.api.on()) return HUB.api.degreeIndex().catch(function(){ return null; });
      return null;
    })
    .then(function(apiIdx){ return apiIdx||_fj('data/degrees/index.json'); })
    .then(function(j){
      DATA.idx=(j&&Array.isArray(j.plans))?j:{plans:[],schools:[]};
      return DATA.idx;
    })
    .catch(function(){
      DATA.idxFailed=true;
      DATA.idx={plans:[],schools:[]};
      return DATA.idx;
    });
  return DATA.idxP;
}
function degFile(slug){
  if(DATA.files[slug]) return Promise.resolve(DATA.files[slug]);
  if(!DATA.fileP[slug]) DATA.fileP[slug]=Promise.resolve()
    .then(function(){
      if(window.HUB&&HUB.api&&HUB.api.on()) return HUB.api.degreeFile(slug).catch(function(){ return null; });
      return null;
    })
    .then(function(apiFile){ return apiFile||_fj('data/degrees/'+slug+'.json'); })
    .then(function(j){ DATA.files[slug]=j; return j; })
    .catch(function(){ DATA.files[slug]=null; return null; });
  return DATA.fileP[slug];
}

/* Campus data: official multi-campus structures (data/campuses.json).
   Keyed by institution slug. Promise-cached. */
const CAMPUSES={data:null,promise:null};
function campusData(){
  if(CAMPUSES.data) return Promise.resolve(CAMPUSES.data);
  if(!CAMPUSES.promise) CAMPUSES.promise=_fj('data/campuses.json')
    .then(function(j){ CAMPUSES.data=j||{}; return CAMPUSES.data; })
    .catch(function(){ CAMPUSES.data={}; return {}; });
  return CAMPUSES.promise;
}
/* Returns HTML for the campus list of a school slug, or '' if none. */
function campusHTML(slug){
  const entry=(CAMPUSES.data||{})[slug];
  if(!entry||!entry.campuses||!entry.campuses.length) return '';
  const sel=selectedCampus(slug);
  let h='<div class="deg-campuses"><div class="deg-campuses-hd">'+esc(entry.note||'Campuses')+'</div><div class="deg-campus-list">';
  entry.campuses.forEach(function(c,i){
    const isSel=sel===c.name;
    h+='<button class="deg-campus-chip'+(isSel?' sel':'')+'" data-campus="'+esc(c.name)+'" data-school="'+esc(slug)+'">'+esc(c.name)+
       '<span class="deg-campus-loc">'+esc(c.city)+', '+esc(c.state)+'</span>'+
       (c.note?'<span class="deg-campus-note">'+esc(c.note)+'</span>':'')+(isSel?'<span class="deg-campus-check">✓</span>':'')+'</button>';
  });
  return h+'</div></div>';
}
/* Selected campus per school, persisted in profile */
function selectedCampus(slug){
  try{
    const p=(store().state.profile||{});
    return (p.campuses||{})[slug]||'';
  }catch(e){ return ''; }
}
function setSelectedCampus(slug,name){
  const st=store().state;
  if(!st.profile) st.profile={};
  if(!st.profile.campuses) st.profile.campuses={};
  if(st.profile.campuses[slug]===name) delete st.profile.campuses[slug];
  else st.profile.campuses[slug]=name;
  store().save();
  /* Re-render to show the checkmark */
  if(typeof updatePickerResults==='function') updatePickerResults();
}

/* ---------------- game-like loading screen ----------------
   Makes API cold-start waits (30-60s) feel fun instead of broken.
   Shows animated planet, progress stages, time estimate, and tips. */
let degLoadStart=0;
let degLoadTipsTimer=null;
const DEG_LOAD_TIPS=[
  'tip1','tip2','tip3','tip4','tip5'
];
function degLoadingHTML(){
  degLoadStart=Date.now();
  return '<div class="deg-loading">'
    +'<div class="deg-load-planet"><div class="deg-load-ring"></div><div class="deg-load-core">🪐</div>'
    +'<div class="deg-load-orbit deg-load-o1">🎓</div>'
    +'<div class="deg-load-orbit deg-load-o2">📚</div>'
    +'<div class="deg-load-orbit deg-load-o3">✨</div></div>'
    +'<div class="deg-load-stage" id="degLoadStage">'+esc(t('deg.loadStage1'))+'</div>'
    +'<div class="deg-load-bar"><div class="deg-load-fill" id="degLoadFill"></div></div>'
    +'<div class="deg-load-time" id="degLoadTime"></div>'
    +'<div class="deg-load-tip"><span class="deg-load-tipicon">💡</span><span id="degLoadTip">'+esc(t('deg.loadTip1'))+'</span></div>'
    +'</div>';
}
/* premium polish (2026-10-07): shimmer skeleton rows shown while directory
   results load, so the list never flashes a bare "Loading…" line. */
function degSkelRows(n){
  let h='<div class="ps-skel-list" aria-hidden="true">';
  const count=n||6;
  for(let i=0;i<count;i++){
    h+='<div class="ps-skel-row" style="--i:'+i+'">'
      +'<div class="ps-skel ps-ava sm"></div>'
      +'<div class="grow"><div class="ps-skel ps-line lg"></div>'
      +'<div class="ps-skel ps-line short"></div></div></div>';
  }
  return h+'</div>';
}
function degLoadingStart(){
  const stage=document.getElementById('degLoadStage');
  const fill=document.getElementById('degLoadFill');
  const timeEl=document.getElementById('degLoadTime');
  const tipEl=document.getElementById('degLoadTip');
  if(!stage) return;
  degLoadStart=Date.now();
  /* Progress stages */
  const stages=[t('deg.loadStage1'),t('deg.loadStage2'),t('deg.loadStage3'),t('deg.loadStage4')];
  let stageIdx=0;
  const stageTimer=setInterval(function(){
    if(!document.getElementById('degLoadStage')){ clearInterval(stageTimer); return; }
    stageIdx=Math.min(stageIdx+1, stages.length-1);
    stage.textContent=stages[stageIdx];
    if(fill) fill.style.width=((stageIdx+1)/stages.length*100)+'%';
  }, 8000);
  /* Time estimate countdown */
  const timeTimer=setInterval(function(){
    if(!document.getElementById('degLoadTime')){ clearInterval(timeTimer); clearInterval(stageTimer); return; }
    const elapsed=Math.floor((Date.now()-degLoadStart)/1000);
    const estimate=Math.max(0, 45-elapsed);
    if(timeEl){
      if(estimate>0) timeEl.textContent=t('deg.loadEta',{s:estimate});
      else timeEl.textContent=t('deg.loadAlmost');
    }
  }, 1000);
  /* Rotating tips */
  let tipIdx=0;
  degLoadTipsTimer=setInterval(function(){
    if(!document.getElementById('degLoadTip')){ clearInterval(degLoadTipsTimer); return; }
    tipIdx=(tipIdx+1)%5;
    if(tipEl){
      tipEl.style.opacity='0';
      setTimeout(function(){
        tipEl.textContent=t('deg.loadTip'+(tipIdx+1));
        tipEl.style.opacity='1';
      }, 300);
    }
  }, 6000);
  /* Store timers for cleanup */
  degLoadingCleanup.timers=[stageTimer, timeTimer];
}
const degLoadingCleanup={timers:[]};
function degLoadingStop(){
  degLoadingCleanup.timers.forEach(function(t){ clearInterval(t); });
  if(degLoadTipsTimer) clearInterval(degLoadTipsTimer);
}
/* ---------------- progress state ---------------- */
function dstate(){
  const st=store().state;
  if(!st.degree||typeof st.degree!=='object') st.degree={active:null,progress:{}};
  if(!st.degree.progress||typeof st.degree.progress!=='object') st.degree.progress={};
  return st.degree;
}
function save(){ store().save(); }
function progFor(slug){
  const ds=dstate();
  let p=ds.progress[slug];
  if(!p||typeof p!=='object') p={done:{},startYear:new Date().getFullYear()};
  if(!p.done||typeof p.done!=='object') p.done={};
  if(!p.startYear) p.startYear=new Date().getFullYear();
  p.intake=normIntake(p.intake,p.startYear);
  ds.progress[slug]=p;
  return p;
}
/* Start-intake normalization. Defaults to Fall of the stamped startYear —
   the plan's original assumption — so existing users see zero change until
   they touch the selector. */
function normIntake(it,year){
  const y=Math.min(2100,Math.max(1990,Number(year)||new Date().getFullYear()));
  if(it&&typeof it==='object'){
    const term=(it.term==='spring'||it.term==='summer')?it.term:'fall';
    return {term:term,year:Math.min(2100,Math.max(1990,Number(it.year)||y))};
  }
  return {term:'fall',year:y};
}
function intakeOf(slug){ return progFor(slug).intake; }
function doneOf(slug){ return progFor(slug).done; }

/* ---------------- plan helpers ---------------- */
function semsOf(plan){ return (plan&&Array.isArray(plan.semesters))?plan.semesters:[]; }
function normCode(s){ return String(s||'').toUpperCase().replace(/\s+/g,' ').trim(); }
/* ---------------- occurrence identity ----------------
   Some collected plans reuse placeholder slot_ids ("s?-N") across many
   DIFFERENT courses, so a completion is identified by its OCCURRENCE:
   (semester index, course index) — never by bare slot_id alone. */
function slotOccs(plan){
  if(plan._occCache) return plan._occCache;
  const m={};
  semsOf(plan).forEach(function(sem,si){
    (sem.courses||[]).forEach(function(c,ci){
      (m[c.slot_id]=m[c.slot_id]||[]).push({si:si,ci:ci});
    });
  });
  plan._occCache=m;
  return m;
}
function occKey(si,ci){ return si+':'+ci; }
function parseAt(at){
  const m=/^(\d+):(\d+)$/.exec(String(at==null?'':at));
  return m?{si:parseInt(m[1],10),ci:parseInt(m[2],10)}:null;
}
/* done-map key for one tile occurrence. Unique slot_ids keep their legacy
   bare key; duplicated ids get an occurrence-qualified key so two different
   courses sharing "s?-N" can each be completed independently. */
function doneKey(plan,c,si,ci){
  const list=(slotOccs(plan)[c.slot_id]||[]);
  return list.length<=1?c.slot_id:(c.slot_id+'~~'+si+':'+ci);
}
/* the done record belonging to occurrence (si,ci), or null. Prefers the
   qualified key; falls back to a bare legacy record only when it carries a
   matching `at` stamp (or is unambiguous / best-effort matched). */
function occRec(done,plan,c,si,ci){
  let rec=done[c.slot_id+'~~'+si+':'+ci];
  if(rec) return rec;
  rec=done[c.slot_id];
  if(!rec) return null;
  if(rec.at!=null) return rec.at===occKey(si,ci)?rec:null;
  /* legacy unstamped record (pre-migration safety net; migration normally
     re-keys these before first render) */
  const list=(slotOccs(plan)[c.slot_id]||[]);
  if(list.length<=1) return rec;
  return legacyOccMatch(rec,c)?rec:null;
}
/* option code regardless of data shape: object {code} or plain code string */
function optCode(o){ return normCode((o&&typeof o==='object')?o.code:String(o==null?'':o)); }
function legacyOccMatch(rec,c){
  const rc=normCode(rec.code), cc=normCode(c.code);
  if(rc&&rc===cc) return true;
  if(c.choice){
    const opts=c.options||[];
    for(let i=0;i<opts.length;i++) if(optCode(opts[i])===rc&&rc) return true;
  }
  const rt=String(rec.title||'').trim().toLowerCase();
  const ct=String(c.title||'').trim().toLowerCase();
  return !!(rt&&rt===ct);
}
/* resolve the exact occurrence for a slot_id (+ optional "si:ci"), instead
   of blindly returning the first course with that id. */
function findCourse(plan,slotId,at){
  const sems=semsOf(plan), p=parseAt(at);
  if(p){
    const crs=(sems[p.si]||{}).courses||[];
    if(crs[p.ci]&&crs[p.ci].slot_id===slotId) return {c:crs[p.ci],si:p.si,ci:p.ci};
  }
  for(let si=0;si<sems.length;si++){
    const crs=sems[si].courses||[];
    for(let ci=0;ci<crs.length;ci++)
      if(crs[ci].slot_id===slotId) return {c:crs[ci],si:si,ci:ci};
  }
  return null;
}
/* One-time migration: legacy done records are keyed by bare slot_id, which
   is ambiguous when a plan reuses placeholder ids ("s?-N"). For each such
   record, find the best-matching occurrence by stored code/title (for choice
   slots the stored code is the user's pick — matched against the slot's
   options/slot code) and re-key it to that occurrence, stamping `at`.
   No confident match -> first occurrence, so the checkmark is never lost.
   Guarded: runs once per plan, never wipes user data. */
function migrateDoneOcc(slug,plan){
  const p=progFor(slug);
  if(p._occMig) return;
  p._occMig=1;
  const done=p.done, occs=slotOccs(plan), sems=semsOf(plan);
  let changed=false;
  Object.keys(done).forEach(function(key){
    if(key.indexOf('~~')!==-1) return;
    const rec=done[key];
    if(!rec||typeof rec!=='object') return;
    const list=occs[key]||[];
    if(list.length===1) return; /* unique id: the bare key is already correct */
    if(list.length>1){
      let best=list[0], bestScore=-1;
      for(let i=0;i<list.length;i++){
        const c=((sems[list[i].si]||{}).courses||[])[list[i].ci];
        if(!c) continue;
        const s=occScore(rec,c);
        if(s>bestScore){ bestScore=s; best=list[i]; }
      }
      rec.at=occKey(best.si,best.ci);
      done[key+'~~'+rec.at]=rec;
      delete done[key];
      changed=true;
      return;
    }
    /* ORPHAN KEY (NEW 2026-10-01): no course in the current plan uses this
       slot_id. The pipeline renumbered legacy placeholder ids (s?-N -> sK-N
       with real semester numbers), so pre-renumber checkmarks keyed by the
       old ids no longer match. Rescue in two passes:
       pass 1: exact code/option match or title match (occScore >= 2);
       pass 2 (choice slots only): the record's pick code appears in the
       slot's choice_note ("recommends HIST 202"), the catalog's own
       recommendation text. No confident match -> keep the orphan record
       untouched; user data is never deleted here. */
    let obest=null, obestScore=1;
    for(let si=0;si<sems.length;si++){
      const crs=(sems[si]||{}).courses||[];
      for(let ci=0;ci<crs.length;ci++){
        const s=occScore(rec,crs[ci]);
        if(s>obestScore){ obestScore=s; obest={si:si,ci:ci}; }
      }
    }
    if(!obest && rec.code){
      const want=String(rec.code).toLowerCase();
      const wantFlat=want.replace(/\s+/g,'');
      for(let si=0;si<sems.length && !obest;si++){
        const crs=(sems[si]||{}).courses||[];
        for(let ci=0;ci<crs.length;ci++){
          const c=crs[ci];
          if(!c.choice||!c.choice_note) continue;
          const note=String(c.choice_note).toLowerCase();
          if(note.indexOf(want)!==-1 ||
             (wantFlat.length>=6 && note.replace(/\s+/g,'').indexOf(wantFlat)!==-1)){
            obest={si:si,ci:ci}; break;
          }
        }
      }
    }
    if(!obest) return;
    const oc=((sems[obest.si]||{}).courses||[])[obest.ci];
    const nk=doneKey(plan,oc,obest.si,obest.ci);
    rec.at=occKey(obest.si,obest.ci);
    if(nk!==key){ done[nk]=rec; delete done[key]; }
    changed=true;
  });
  if(changed) save();
}
function occScore(rec,c){
  let s=0;
  const rc=normCode(rec.code), cc=normCode(c.code);
  if(rc&&rc===cc) s+=2;
  if(c.choice){
    const opts=c.options||[];
    for(let i=0;i<opts.length;i++) if(optCode(opts[i])===rc&&rc){ s+=2; break; }
  }
  const rt=String(rec.title||'').trim().toLowerCase();
  const ct=String(c.title||'').trim().toLowerCase();
  if(rt&&rt===ct) s+=1;
  return s;
}
/* Some collected plans have no semester `n` (placeholder builds); assign
   1-based numbers in catalog order so term labels and the collapse map stay
   unique. Idempotent — valid existing numbers are kept. */
function normSemNumbers(plan){
  const sems=semsOf(plan);
  for(let i=0;i<sems.length;i++){
    const n=Math.floor(Number(sems[i]&&sems[i].n));
    sems[i].n=(n>=1)?n:(i+1);
  }
}
/* find a plan course by local code or TCCNS number */
function slotByCode(plan,code){
  const nk=normCode(code);
  if(!nk) return null;
  const sems=semsOf(plan);
  for(let i=0;i<sems.length;i++){
    const crs=sems[i].courses||[];
    for(let k=0;k<crs.length;k++){
      const c=crs[k];
      if(normCode(c.code)===nk||normCode(c.tccns)===nk) return c;
    }
  }
  return null;
}
/* Parse "CODE — title" segments out of a choice_note, e.g.
   "Choose one: ARTS 1303 — Art History I; HUMA 1315 — Fine Arts Appreciation".
   Returns {NORMCODE: title}. */
function choiceNoteTitles(note){
  const out={};
  String(note||'').split(';').forEach(function(seg){
    const s=String(seg).replace(/^\s*choose one\s*:\s*/i,'').trim();
    const m=/^([A-Z]{2,5}\s?\d{3,4}[A-Z]?)\s*[—–-]\s*(.+)$/.exec(s);
    if(m) out[normCode(m[1])]=m[2].trim();
  });
  return out;
}
/* Normalize a choice slot's options to [{code,title,credits}] whether the
   plan stores option objects or plain code strings (1,833 string-option
   slots exist in the collected data — blank rows otherwise). Title for a
   string option resolves: same-plan course lookup, then choice_note, then
   '' (the code itself still renders, so a row is never blank). */
function normOptions(plan,c){
  const noteT=choiceNoteTitles(c.choice_note);
  return (c.options||[]).map(function(o){
    if(o&&typeof o==='object'){
      return {code:String(o.code==null?'':o.code).trim(),
        title:String(o.title==null?'':o.title).trim(),
        credits:(o.credits!=null?o.credits:c.credits)};
    }
    const code=String(o==null?'':o).trim();
    let title='';
    const hit=slotByCode(plan,code);
    if(hit&&hit.title) title=String(hit.title).trim();
    if(!title&&noteT[normCode(code)]) title=noteT[normCode(code)];
    return {code:code,title:title,credits:c.credits};
  });
}
function earnedCredits(plan,done){
  let sum=0;
  const sems=semsOf(plan);
  for(let i=0;i<sems.length;i++){
    const crs=sems[i].courses||[];
    for(let k=0;k<crs.length;k++){
      const c=crs[k], rec=occRec(done,plan,c,i,k);
      if(rec) sum+=(typeof rec.credits==='number'?rec.credits:(Number(c.credits)||0));
    }
  }
  return sum;
}
/* prereq check: is the course with this code completed in ANY occurrence?
   A done record's stored `code` is the actually-completed course (for choice
   slots, the user's pick), so it is matched first; then the plan course
   carrying that code, via occurrence identity. */
function prereqOk(plan,done,code){
  const nk=normCode(code);
  if(!nk) return false;
  const ids=Object.keys(done);
  for(let i=0;i<ids.length;i++){
    const r=done[ids[i]];
    if(r&&normCode(r.code)===nk) return true;
  }
  const sems=semsOf(plan);
  for(let si=0;si<sems.length;si++){
    const crs=sems[si].courses||[];
    for(let ci=0;ci<crs.length;ci++){
      const c=crs[ci];
      if((normCode(c.code)===nk||normCode(c.tccns)===nk)&&occRec(done,plan,c,si,ci)) return true;
    }
  }
  return false;
}
function extractCodes(raw){
  const m=String(raw||'').match(/[A-Z]{2,5}\s?\d{3,4}[A-Z]?/g);
  return m?m.map(function(s){ return s.replace(/\s+/g,' ').trim(); }):[];
}
/* Flatten a course's prereqs into checkable items:
   [{label, ok:true|false|null}] — ok:null means not auto-verifiable (info only). */
function prereqList(plan,course){
  const out=[], done=curDone();
  const items=course.prereq||[];
  for(let i=0;i<items.length;i++){
    const p=items[i];
    if(typeof p==='string'){
      const hit=slotByCode(plan,p);
      if(hit) out.push({label:p, ok:prereqOk(plan,done,p)});
      /* prereq not in the plan (e.g. a placement/TSI requirement): skip —
         we cannot verify it, so we don't warn about it. */
    }else if(p&&typeof p==='object'){
      if(Array.isArray(p.one_of)&&p.one_of.length){
        const opts=p.one_of.map(function(cd){
          return {code:cd, ok:prereqOk(plan,done,cd)};
        });
        out.push({label:opts.map(function(o){return o.code;}).join(' / '),
                  ok:opts.some(function(o){return o.ok;})});
      }else if(p.raw){
        const selfCodes=normCode(course.code+' '+course.tccns);
        const codes=extractCodes(p.raw).map(function(cd){
          const hit=slotByCode(plan,cd);
          return {code:cd, hit:hit, ok:!!(hit&&prereqOk(plan,done,cd))};
        }).filter(function(x){ return x.hit&&selfCodes.indexOf(normCode(x.code))===-1; });
        /* drop codes that are the course's own (e.g. "CSE 4303 / CSE 4305"
           choice slots whose note names their own options) */
        if(codes.length){
          out.push({label:p.raw, ok:codes.every(function(x){return x.ok;})});
        }else{
          out.push({label:p.raw, ok:null});
        }
      }
    }
  }
  return out;
}
function unmetWarn(plan,course){
  return prereqList(plan,course).filter(function(p){ return p.ok===false; });
}

/* ---------------- pace ---------------- */
/* Completed fall+spring terms since startYear (summers don't count).
   Fresh students (current term in progress) get expected=0 — never shaming. */
function completedTerms(startYear){
  const now=new Date(), m=now.getMonth(), y=now.getFullYear();
  let n;
  if(m>=8) n=(y-startYear)*2;          /* fall in progress */
  else if(m<=4) n=(y-startYear)*2-1;   /* spring in progress */
  else n=(y-startYear)*2;              /* summer: fall+spring done */
  return Math.max(0,n);
}
function paceOf(plan,earned,startYear,cap){
  const total=Number(plan.total_credits)||0;
  const per=cap||15;
  const expected=Math.min(completedTerms(startYear)*per,total);
  const onTrack=earned>=expected-3;
  return {expected:expected,earned:earned,onTrack:onTrack,behind:Math.max(0,expected-earned)};
}
/* Project the finishing term `need` fall/spring terms from now
   (summers don't count as terms, same as completedTerms). */
function termAfter(need){
  if(!(need>0)) return null;
  const now=new Date(), m=now.getMonth(), y=now.getFullYear();
  let season, yr;
  if(m>=8){ season='fall'; yr=y; }
  else if(m<=4){ season='spring'; yr=y; }
  else { season='fall'; yr=y; } /* summer -> next term is fall */
  for(let i=1;i<need;i++){
    if(season==='fall'){ season='spring'; yr++; }
    else { season='fall'; }
  }
  return t(season==='fall'?'deg.fall':'deg.spring')+' '+yr;
}
/* Project the finishing term at 15 credits/semester from now. */
function finishTerm(plan,earned){
  const total=Number(plan.total_credits)||0;
  return termAfter(Math.ceil((total-earned)/15));
}

/* ---------------- my pace ----------------
   "My pace": the student picks a credits-per-semester cap (9-18) and the
   plan re-flows to that pace. 0 = "as published" (full-time, the default —
   existing users see zero change until they touch the control).
   Persisted per plan alongside intake/startYear in progFor(). */
function paceCap(slug){
  const p=progFor(slug);
  const v=Math.floor(Number(p.pace)||0);
  return (v>=9&&v<=18)?v:0;
}
function setPaceCap(slug,v){
  if(!cur||cur.slug!==slug) return;
  const p=progFor(slug);
  const n=Math.floor(Number(v)||0);
  p.pace=(n>=9&&n<=18)?n:0;
  save(); renderTracker();
}
/* Flat course list in published order, each item keeping its published
   (si,ci) identity. Completion keys, tiles, findCourse() and occRec() all
   operate on published coordinates, so checkmarks survive any re-flow. */
function paceItems(plan){
  const out=[];
  semsOf(plan).forEach(function(sem,si){
    (sem.courses||[]).forEach(function(c,ci){ out.push({c:c,si:si,ci:ci}); });
  });
  return out;
}
/* Prereq constraints for item i, split by how the catalog itself schedules
   the dependency relative to the course:
   - strict: dep is published in an EARLIER semester -> the course must land
     in a strictly later view semester.
   - coreq: dep shares the course's published semester (corequisites like
     NURS 2360 + NURS 2390, scheduled together) -> the course may share the
     view semester but never land earlier than the dep.
   - A dep published LATER than the course is broken catalog data (130 cases
     in 13,112 plans); it gets no constraint so the published order is
     preserved rather than "repaired" into something the catalog never said.
   Conservative: a one_of group constrains against ALL its options, so the
   course always lands after whichever option the student actually takes. */
function paceDeps(flat,byCode,i){
  const seen={}, strict=[], coreq=[];
  const psi=flat[i].si;
  function add(cd){
    const h=byCode[normCode(cd)];
    if(h==null||h===i||seen[h]) return;
    seen[h]=1;
    const psd=flat[h].si;
    if(psd<psi) strict.push(h);
    else if(psd===psi) coreq.push(h);
  }
  const items=flat[i].c.prereq||[];
  for(let k=0;k<items.length;k++){
    const p=items[k];
    if(typeof p==='string') add(p);
    else if(p&&Array.isArray(p.one_of)) p.one_of.forEach(add);
    else if(p&&p.raw) extractCodes(p.raw).forEach(add);
  }
  return {strict:strict,coreq:coreq};
}
/* Re-flow a plan into semesters capped at `cap` credits.
   - Published relative order is ALWAYS preserved (the safe fallback for the
     ~89% of plans with no usable prereq data, and the task's requirement).
   - Where prereq data exists: a genuine prereq (published earlier) forces
     the course into a strictly later semester; a corequisite (same
     published semester) may share the semester but never precede it.
   - A single course over the cap gets its own semester — a course is never
     split, and overflow is honest rather than silently dropped.
   - Pathological catalog data (prereq published AFTER its dependent —
     130 cases in 13,112 plans) gets no constraint: the published order is
     preserved, never "repaired" into something the catalog never said.
   - A single greedy pass in published order is exact: strict deps are
     always published earlier (already placed); later-published coreq deps
     need no constraint because monotonicity lands them at-or-after. */
function reflowView(plan,cap){
  const flat=paceItems(plan), n=flat.length;
  const pubView=semsOf(plan).map(function(sem,si){
    return {n:si+1,term:sem.term,pub:true,semN:sem.n,
      items:(sem.courses||[]).map(function(c,ci){ return {c:c,si:si,ci:ci}; })};
  });
  if(!(cap>0)||!n) return pubView;
  const byCode0={};
  flat.forEach(function(it,i){
    [it.c.code,it.c.tccns].forEach(function(cd){
      const k=normCode(cd);
      if(k&&byCode0[k]==null) byCode0[k]=i;
    });
  });
  /* Within each published semester, stable topo-sort by corequisite edges so
     a same-semester prereq is always processed before its dependent (the
     catalog's prereq direction is honored even inside one semester).
     Only intra-semester coreq edges participate; strict deps (earlier
     semesters) and backward data are untouched. Cycles keep published order.
     Stable: non-constrained pairs keep their catalog listing order. */
  (function(){
    const bySem={};
    flat.forEach(function(it,i){ (bySem[it.si]=bySem[it.si]||[]).push(i); });
    const newOrder=[];
    Object.keys(bySem).forEach(function(sk){
      const members=bySem[sk], pos={};
      members.forEach(function(mi,k){ pos[mi]=k; });
      const succ=members.map(function(){ return []; });
      const indeg=members.map(function(){ return 0; });
      members.forEach(function(mi,k){
        paceDeps(flat,byCode0,mi).coreq.forEach(function(x){
          if(x===mi||pos[x]==null) return;
          succ[pos[x]].push(k); /* x before mi */
          indeg[k]++;
        });
      });
      const done=members.map(function(){ return false; });
      for(let t=0;t<members.length;t++){
        let pick=-1;
        for(let k=0;k<members.length;k++)
          if(!done[k]&&indeg[k]===0){ pick=k; break; }
        if(pick<0){ /* cycle: keep the rest in published order */
          for(let k=0;k<members.length;k++)
            if(!done[k]){ newOrder.push(members[k]); done[k]=true; }
          break;
        }
        done[pick]=true;
        newOrder.push(members[pick]);
        succ[pick].forEach(function(k){ indeg[k]--; });
      }
    });
    const sorted=newOrder.map(function(i){ return flat[i]; });
    flat.length=0;
    sorted.forEach(function(it){ flat.push(it); });
  })();
  const byCode={};
  flat.forEach(function(it,i){
    [it.c.code,it.c.tccns].forEach(function(cd){
      const k=normCode(cd);
      if(k&&byCode[k]==null) byCode[k]=i;
    });
  });
  const deps=flat.map(function(_,i){ return paceDeps(flat,byCode,i); });
  const cr=function(i){ return Math.max(0,Number(flat[i].c.credits)||0); };
  /* Single greedy pass in published order. This is exact (no fixpoint
     needed): a strict dep is always published earlier, hence already placed;
     a coreq dep published earlier is likewise placed; a coreq dep published
     later gets no constraint and monotonicity lands it at-or-after the
     course. Published order is therefore always preserved. */
  const placed=new Array(n), semCr=[];
  for(let i=0;i<n;i++){
    let m=-1, mc=-1;
    const ds=deps[i];
    for(let k=0;k<ds.strict.length;k++){ const v=placed[ds.strict[k]]; if(v!=null&&v>m) m=v; }
    for(let k=0;k<ds.coreq.length;k++){ const v=placed[ds.coreq[k]]; if(v!=null&&v>mc) mc=v; }
    let j=m+1;
    if(mc>j) j=mc;                        /* corequisite: never earlier */
    if(i>0&&placed[i-1]>j) j=placed[i-1]; /* published order preserved */
    const c=cr(i);
    for(;;j++){
      const used=semCr[j]||0;
      if(used===0||used+c<=cap) break;
    }
    placed[i]=j;
    semCr[j]=(semCr[j]||0)+c;
  }
  const groups=[];
  for(let i=0;i<n;i++){
    const j=placed[i];
    (groups[j]=groups[j]||[]).push(flat[i]);
  }
  return groups.map(function(g,j){ return {n:j+1,term:null,pub:false,items:g}; });
}
/* View semesters (at the student's pace) that still have incomplete courses.
   Used for the pace-aware graduation estimate. */
function remainingViewSems(plan,view,done){
  let need=0;
  view.forEach(function(vs){
    const allDone=vs.items.every(function(it){
      return !!occRec(done,plan,it.c,it.si,it.ci);
    });
    if(!allDone) need++;
  });
  return need;
}
/* ---------------- start-intake term labels ----------------
   Semester n (1-based) -> {term, year} rotated from the student's intake.
   Fall start:  Fall Y, Spring Y+1, Fall Y+1, ...
   Spring start: Spring Y, Fall Y, Spring Y+1, ...
   Summer start: Summer Y, then Fall Y, Spring Y+1, Fall Y+1, ...
   Only labels shift — the course sequence is untouched. */
function intakeTerm(n,it){
  n=Math.floor(Number(n));
  it=(it&&typeof it==='object')?it:{term:'fall',year:new Date().getFullYear()};
  if(!(n>=1)) return {term:'',year:NaN}; /* invalid n: the label falls back, never "NaN" */
  if(it.term==='summer'){
    if(n<=1) return {term:'summer',year:it.year};
    const m=n-1;
    return {term:(m%2===1?'fall':'spring'),year:it.year+Math.floor(m/2)};
  }
  const i=n-1;
  const cyc=it.term==='fall'?['fall','spring']:['spring','fall'];
  const term=cyc[i%2];
  const year=it.term==='fall'?it.year+Math.ceil(i/2):it.year+Math.floor(i/2);
  return {term:term,year:year};
}
function termNameKey(term){
  return term==='fall'?'deg.fall':term==='spring'?'deg.spring':'deg.summer';
}
/* "Spring 2027" — the visible semester label for semester n.
   `fallback` (the plan's own term string) is used if n is ever invalid, so a
   header can never render "NaN". */
function semTermLabel(n,it,fallback){
  const r=intakeTerm(n,it);
  if(r.term&&isFinite(r.year)) return t(termNameKey(r.term))+' '+r.year;
  const fb=String(fallback==null?'':fallback).trim();
  return fb||('Term '+n);
}
function tcBadge(conf){
  if(conf==='guaranteed_block') return '<span class="deg-tcbadge">🔀 '+esc(t('deg.block'))+'</span>';
  if(conf==='advisory') return '<span class="deg-tcbadge adv">'+esc(t('deg.checkAdvisor'))+'</span>';
  return '';
}
function catLabel(cat){
  if(cat==='core') return t('deg.catCore');
  if(cat==='major') return t('deg.catMajor');
  if(cat==='elective') return t('deg.catElective');
  return String(cat||'');
}

/* ---------------- overlay lifecycle ----------------
   Same mount pattern as professors/search/pulse: a .chatroot overlay removed
   from the DOM on close. Escape is captured (capture phase, before the app.js
   global handler): a sheet open above the overlay wins the first Escape; the
   overlay itself closes on the second. */
const ROOT_ID='hubDegRoot';
let cur=null;          /* {slug, plan(file), meta(index entry)} */
let xferMode=false;
let collapsed={};      /* sem n -> true */
let pickState={q:'',level:'all',pendingOpen:{}};
let lastPop=null;      /* slot_id that just completed -> burst animation */
let lastFloat=null;    /* {slot, text} floating credit chip */
let loadSeq=0;         /* guards async plan loads against back-navigation */
function curDone(){ return cur?doneOf(cur.slug):{}; }

function ensureClosed(){
  const old=document.getElementById(ROOT_ID);
  if(old) old.remove();
  document.removeEventListener('keydown',onKey,true);
}
function close(){ loadSeq++; /* invalidate any in-flight plan load */ ensureClosed(); cur=null; }
function onKey(e){
  if(e.key!=='Escape') return;
  const sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden){ e.stopImmediatePropagation(); ui().closeSheet(); return; }
  e.stopImmediatePropagation();
  close();
}
function open(slug){
  ensureClosed();
  ui().closeSheet();
  ['search','pulse','notifications'].forEach(function(k){ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  cur=null; xferMode=false; collapsed={}; lastPop=null; lastFloat=null;
  const app=document.getElementById('app')||document.body;
  const d=document.createElement('div');
  d.className='chatroot degroot'; d.id=ROOT_ID;
  d.innerHTML='<div class="chatpanel deg-panel">'+
    '<div class="deg-topbar">'+
      '<button class="iconbtn deg-back" id="degBack" aria-label="'+esc(t('common.back'))+'">‹</button>'+
      '<div class="deg-topbar-t" id="degTitle">'+esc(t('deg.entryTitle'))+'</div>'+
      '<button class="iconbtn" id="degClose" aria-label="'+esc(t('common.close'))+'">✕</button></div>'+
    '<div class="deg-body" id="degBody">'+degLoadingHTML()+'</div>'+
    '</div>';
  app.appendChild(d);
  d.addEventListener('click',function(e){ if(e.target===d) close(); });
  document.getElementById('degClose').onclick=close;
  document.getElementById('degBack').onclick=function(){
    if(cur) renderPicker(); else close();
  };
  document.addEventListener('keydown',onKey,true);
  if(slug) openPlan(slug);
  else { renderPicker(); degLoadingStart(); }
}
function openPlan(slug){
  const seq=++loadSeq;
  const body=document.getElementById('degBody');
  degIndex().then(function(idx){
    if(seq!==loadSeq) return;
    const meta=(idx.plans||[]).filter(function(p){ return p.slug===slug; })[0];
    if(!meta){ if(body) body.innerHTML='<div class="empty ps-empty"><div class="big">🎓</div><p>'+esc(t('deg.loadFail'))+'</p></div>'; return; }
    degFile(slug).then(function(file){
      if(seq!==loadSeq) return; /* user hit back while loading */
      if(!file||!file.plan){ if(body) body.innerHTML='<div class="empty ps-empty"><div class="big">🎓</div><p>'+esc(t('deg.loadFail'))+'</p></div>'; return; }
      cur={slug:slug,plan:file.plan,meta:meta};
      normSemNumbers(cur.plan); /* plans missing semester `n` get 1-based numbers */
      xferMode=false; collapsed={}; lastPop=null; lastFloat=null;
      progFor(slug); /* ensure startYear is stamped on first activation */
      migrateDoneOcc(slug,cur.plan); /* one-time: legacy done records gain occurrence identity */
      dstate().active=slug; save();
      const dt=document.getElementById('degTitle');
      if(dt) dt.textContent=meta.degree+' · '+meta.major;
      renderTracker();
    });
  });
}

/* ---------------- picker ---------------- */
function levelOfDegree(deg){
  /* catalog codes (AA/AS/AAS/AAT) and CIP-derived award levels */
  return /^(AA|AS|AAS|AAT|Associate)\b/i.test(String(deg||'').trim())?'associate':'bachelor';
}
function pickFilterOK(meta, prog){
  /* meta = index plan entry (collected) or pending program row */
  if(pickState.level==='all') return true;
  if(meta&&meta.level) return meta.level===pickState.level;
  return levelOfDegree(prog&&prog.degree)===pickState.level;
}
function pickQueryOK(){
  const q=pickState.q.trim().toLowerCase();
  return function(text){ return !q||String(text||'').toLowerCase().indexOf(q)!==-1; };
}
/* ---------------- picker: ONE unified search (2026-09-30) ----------------
   #degQ is the only search box: it filters the collected plans AND the
   national college directory. Typing re-renders ONLY the results containers
   (#degResults, #degBrowse) — the input is never rebuilt or refocused, so
   the screen doesn't shake/jump on iOS while typing. */
function renderPicker(){
  const body=document.getElementById('degBody');
  if(!body) return null;
  cur=null; xferMode=false;
  browseState.school=null;
  document.getElementById('degTitle').textContent=t('deg.entryTitle');
  body.innerHTML=
    '<div class="deg-search"><div class="field" style="margin:0"><input class="input" id="degQ" autocomplete="off" placeholder="'+esc(t('deg.searchPh'))+'" value="'+esc(pickState.q)+'"></div></div>'+
    '<div class="deg-chips" role="tablist">'+
      chipHTML('all',t('deg.all'))+chipHTML('associate',t('deg.associate'))+chipHTML('bachelor',t('deg.bachelor'))+'</div>'+
    '<div id="degResults"></div>'+
    '<div id="degBrowse"></div>';
  const q=document.getElementById('degQ');
  let deb=null;
  if(q) q.oninput=function(){
    clearTimeout(deb);
    deb=setTimeout(function(){ pickState.q=q.value; browseState.school=null; updatePickerResults(); },220);
  };
  body.querySelectorAll('.deg-chip').forEach(function(ch){
    ch.onclick=function(){
      pickState.level=ch.dataset.level;
      body.querySelectorAll('.deg-chip').forEach(function(c2){ c2.classList.toggle('on',c2===ch); });
      updatePickerResults();
    };
  });
  return updatePickerResults();
}
function updatePickerResults(){
  const seq=++loadSeq;
  if(!document.getElementById('degResults')) return null;
  /* Show game-like loading while fetching (cold starts take 30-60s) */
  const box0=document.getElementById('degResults');
  if(box0 && !box0.innerHTML.trim()){
    box0.innerHTML=degLoadingHTML();
    degLoadingStart();
  }
  return Promise.all([degIndex(), campusData()]).then(function(results){
    degLoadingStop();
    const idx=results[0];
    if(seq!==loadSeq) return;
    const box=document.getElementById('degResults');
    if(!box) return;
    const ok=pickQueryOK();
    const schools=idx.schools||[];
    const plansBySlug={};
    (idx.plans||[]).forEach(function(p){ plansBySlug[p.slug]=p; });
    /* Your university first: if the profile has a campus that matches a
       school in the index, pin it to the top (only when not searching). */
    let myUniSlug=null;
    try{
      const camp=String((store().state.profile||{}).campus||'').trim();
      if(camp && !pickState.q.trim()){
        const nc=camp.toLowerCase().replace(/^the\s+/,'').replace(/[^a-z0-9]/g,'');
        for(let i=0;i<schools.length;i++){
          const sn=String(schools[i].name||'').toLowerCase().replace(/^the\s+/,'').replace(/[^a-z0-9]/g,'');
          if(sn===nc){ myUniSlug=schools[i].slug||schools[i].name; break; }
        }
      }
    }catch(e){}
    const ordered=myUniSlug
      ? schools.slice().sort(function(a,b){
          const ka=(a.slug||a.name)===myUniSlug?-1:0, kb=(b.slug||b.name)===myUniSlug?-1:0;
          return ka-kb;
        })
      : schools;
    let h='';
    /* Preview-sample honesty badge: shows only when the bundled index holds
       fewer plans than the full catalog (slim preview builds). Self-hides
       the moment full data (or the backend) is present. */
    try{
      var _total=(idx.count||0), _have=(idx.plans||[]).length;
      if(_total>_have && _have>0){
        h+='<div class="deg-sample" style="margin:2px 0 10px;padding:8px 12px;border:1px dashed currentColor;border-radius:12px;font-size:12px;opacity:.8;text-align:center">📦 '+esc(t('deg.sampleNote',{n:_have,total:_total}))+'</div>';
      }
    }catch(e){}
    if(DATA.idxFailed){
      h+='<div class="empty ps-empty"><div class="big">📡</div><p>'+esc(t('deg.loadFail'))+'</p>'+
        '<button class="btn btn-line btn-sm" id="degRetry">'+esc(t('common.retry'))+'</button></div>';
    }else{
      let anySchool=false;
      ordered.forEach(function(sch){
        const progs=sch.programs||[];
        const collected=progs.filter(function(p){ return p.status==='collected'&&plansBySlug[p.plan_id]; });
        const pending=progs.filter(function(p){ return p.status!=='collected'; });
        const collRows=collected.filter(function(p){
          const pl=plansBySlug[p.plan_id];
          return pickFilterOK(pl,p)&&ok(sch.name+' '+pl.major+' '+pl.degree);
        });
        const pendRows=pending.filter(function(p){
          return pickFilterOK(null,p)&&ok(sch.name+' '+p.program+' '+p.degree);
        });
        if(!collRows.length&&!pendRows.length) return;
        anySchool=true;
        const moreComing=(sch.programs_collected||0)<(sch.programs_total||0);
        const isMine=myUniSlug&&(sch.slug||sch.name)===myUniSlug;
        h+='<div class="deg-school"><div class="deg-school-hd"><div class="grow"><h3>'+esc(sch.name)+
          (isMine?' <span class="deg-mine">'+esc(t('deg.yourUni'))+'</span>':'')+'</h3>'+
          '<div class="meta">'+esc(t('deg.ofPrograms',{a:sch.programs_collected||0,b:sch.programs_total||0}))+'</div>'+
          campusHTML(sch.slug||'')+'</div>'+
          (moreComing?'<span class="deg-more">'+esc(t('deg.moreComing'))+'</span>':'')+'</div>';
        collRows.forEach(function(p){
          const pl=plansBySlug[p.plan_id];
          h+='<button class="deg-planrow" data-slug="'+esc(pl.slug)+'">'+
            '<span class="deg-degree">'+esc(pl.degree)+'</span>'+
            '<span class="grow"><b>'+esc(pl.major)+'</b>'+
            '<span class="meta">'+esc(pl.credits+(pl.semesters?' · '+pl.semesters+' '+t('deg.semesters'):''))+'</span></span>'+
            tcBadge(pl.transfer_confidence)+'<span class="chev">›</span></button>';
        });
        if(pendRows.length){
          const openKey=sch.slug||sch.name;
          const isOpen=!!pickState.pendingOpen[openKey]||pickState.q.trim().length>0;
          h+='<button class="deg-pending-tgl" data-pend="'+esc(openKey)+'">'+
            esc(t('deg.pendingMore',{n:pendRows.length}))+' '+(isOpen?'▴':'▾')+'</button>';
          h+='<div class="deg-pending" data-pendbox="'+esc(openKey)+'"'+(isOpen?'':' hidden')+'>';
          pendRows.forEach(function(p){
            h+='<div class="deg-pending-row"><span class="deg-degree" style="opacity:.6">'+esc(p.degree)+'</span>'+
              '<span class="grow">'+esc(p.program)+'</span>'+
              '<span class="deg-soon">'+esc(t('deg.comingSoon'))+'</span></div>';
          });
          h+='</div>';
        }
        h+='</div>';
      });
      if(!anySchool) h+='<div class="empty ps-empty"><div class="big">🔍</div><p>'+esc(t('deg.noMatch'))+'</p></div>';
    }
    box.innerHTML=h;
    /* bindings: results only — the search input is never touched */
    box.querySelectorAll('.deg-planrow').forEach(function(row){
      row.onclick=function(){ openPlan(row.dataset.slug); };
    });
    box.querySelectorAll('.deg-pending-tgl').forEach(function(btn){
      btn.onclick=function(){
        const k=btn.dataset.pend;
        pickState.pendingOpen[k]=!pickState.pendingOpen[k];
        updatePickerResults();
      };
    });
    const rt=document.getElementById('degRetry');
    if(rt) rt.onclick=function(){ DATA.idxP=null; DATA.idx=null; DATA.idxFailed=false; updatePickerResults(); };
    /* Campus selection: tapping a campus chip saves it as "where I'm going" */
    const box2=document.getElementById('degResults');
    if(box2) box2.onclick=function(e){
      const cb=e.target.closest('[data-campus]');
      if(cb){
        e.stopPropagation();
        setSelectedCampus(cb.getAttribute('data-school'), cb.getAttribute('data-campus'));
        return;
      }
    };
    updateDirectory();
  });
}
function chipHTML(level,label){
  return '<button class="deg-chip'+(pickState.level===level?' on':'')+'" data-level="'+level+'">'+esc(label)+'</button>';
}

/* ---------------- national directory (Phase 1: IPEDS universe) ----------------
   dir.json: {schools:[[unitid,name,city,state,kind,pt,pc]]} — lazy-loaded once.
   p-<ST>.json: {unitid:[[title,degree,planId,status]]} — lazy-loaded per state.
   Program rows come from real IPEDS completions (CIP 2020 series); anything
   without a collected plan is an honest "coming soon" row. */
let browseState={school:null};
/* Unified directory search (2026-09-30): driven by the single #degQ box.
   No second search input — matching colleges render under the plan results;
   tapping one opens its programs in place. */
const NAT={dir:null,dirP:null,states:{},stateP:{}};
function natDir(){
  if(NAT.dir) return Promise.resolve(NAT.dir);
  if(!NAT.dirP) NAT.dirP=_fj('data/degrees/inventory/dir.json')
    .then(function(j){ NAT.dir=j; return j; })
    .catch(function(){ NAT.dir={schools:[]}; return NAT.dir; });
  return NAT.dirP;
}
function natState(st){
  if(NAT.states[st]) return Promise.resolve(NAT.states[st]);
  if(!NAT.stateP[st]) NAT.stateP[st]=_fj('data/degrees/inventory/p-'+st+'.json')
    .then(function(j){ NAT.states[st]=j; return j; })
    .catch(function(){ NAT.states[st]={}; return NAT.states[st]; });
  return NAT.stateP[st];
}
function natBadge(degree){
  /* Associate-level degrees (AA/AS/AAS/AAT/Associate) are 2-year.
     Matches levelOfDegree() so badges agree with the collected plans. */
  return /^(AA|AS|AAS|AAT|Associate)\b/i.test(String(degree||'').trim())?'2YR':'4YR';
}
function updateDirectory(){
  const host=document.getElementById('degBrowse');
  if(!host) return;
  if(browseState.school){
    host.innerHTML='<div class="deg-browse"><div style="margin:0 0 8px"><button class="btn btn-line btn-sm" id="degDirBack">'+
      esc(t('deg.backSchools'))+'</button></div><div id="degBResults"></div></div>';
    document.getElementById('degDirBack').onclick=function(){ browseState.school=null; updateDirectory(); };
    renderBrowseSchool(document.getElementById('degBResults'));
    return;
  }
  const q=pickState.q.trim().toLowerCase();
  if(q.length<2){
    const inv=(DATA.idx&&DATA.idx.inventory)||{};
    const n=inv.schools?Number(inv.schools).toLocaleString('en-US'):'';
    host.innerHTML='<div class="deg-dir-hint">'+esc(t('deg.browseSub',{n:n}))+' · '+esc(t('deg.browsePh'))+'</div>';
    return;
  }
  host.innerHTML='<div class="deg-browse"><div class="deg-dir-hd">'+esc(t('deg.browseAll'))+'</div>'+
    '<div id="degBResults">'+degSkelRows(6)+'</div></div>';
  natDir().then(function(d){
    const box=document.getElementById('degBResults');
    if(!box) return;
    /* re-read the live query: it may have changed while loading */
    const qq=pickState.q.trim().toLowerCase();
    if(browseState.school||qq.length<2){ updateDirectory(); return; }
    const rows=(d.schools||[]).filter(function(r){
      return (r[1]+' '+r[2]+' '+r[3]).toLowerCase().indexOf(qq)!==-1;
    }).slice(0,40);
    if(!rows.length){
      box.innerHTML='<div class="empty ps-empty"><div class="big">🔍</div><p>'+esc(t('deg.noSchools'))+'</p></div>';
      return;
    }
    let h='';
    rows.forEach(function(r){
      h+='<button class="deg-planrow" data-bunit="'+r[0]+'" data-bstate="'+esc(r[3])+'">'+
        '<span class="grow" style="text-align:left"><b>'+esc(r[1])+'</b>'+
        '<span class="meta">'+esc(r[2]+', '+r[3])+' · '+esc(t('deg.programsN',{n:r[5]}))+'</span></span>'+
        '<span class="chev">›</span></button>';
    });
    box.innerHTML=h;
    box.querySelectorAll('[data-bunit]').forEach(function(b){
      b.onclick=function(){
        browseState.school={u:b.dataset.bunit,st:b.dataset.bstate}; updateDirectory();
      };
    });
  });
}
function renderBrowseSchool(box){
  const s=browseState.school;
  box.innerHTML=degSkelRows(8);
  natDir().then(function(d){
    const row=(d.schools||[]).filter(function(r){ return String(r[0])===String(s.u); })[0]||[];
    const name=row[1]||'', loc=(row[2]||'')+', '+(row[3]||'');
    natState(s.st).then(function(st){
      if(!document.getElementById('degBResults')) return;
      const progs=st[String(s.u)]||[];
      let h='<div class="deg-school"><div class="deg-school-hd"><div class="grow"><h3>'+esc(name)+'</h3>'+
        '<div class="meta">'+esc(loc)+' · '+esc(t('deg.programsN',{n:progs.length}))+'</div></div></div>';
      progs.forEach(function(p){
        if(!pickFilterOK(null,{degree:p[1]})) return;
        if(p[3]==='collected'&&p[2]){
          h+='<button class="deg-planrow" data-slug="'+esc(p[2])+'">'+
            '<span class="deg-degree">'+esc(natBadge(p[1]))+'</span>'+
            '<span class="grow"><b>'+esc(p[0])+'</b>'+
            '<span class="meta">'+esc(p[1])+'</span></span><span class="chev">›</span></button>';
        }else{
          h+='<div class="deg-pending-row"><span class="deg-degree" style="opacity:.6">'+esc(natBadge(p[1]))+'</span>'+
            '<span class="grow">'+esc(p[0])+'<span class="meta">'+esc(p[1])+'</span></span>'+
            '<span class="deg-soon">'+esc(t('deg.comingSoon'))+'</span></div>';
        }
      });
      h+='</div>';
      box.innerHTML=h;
      box.querySelectorAll('.deg-planrow').forEach(function(r2){
        r2.onclick=function(){ openPlan(r2.dataset.slug); };
      });
    });
  });
}

/* ---------------- tracker ---------------- */
function renderTracker(){
  const body=document.getElementById('degBody');
  if(!body||!cur) return;
  const plan=cur.plan, meta=cur.meta, done=curDone();
  const earned=earnedCredits(plan,done);
  const total=Number(plan.total_credits)||0;
  const tabs='<div class="deg-tabs"><button class="deg-tab'+(xferMode?'':' on')+'" id="degTabPlan">'+esc(t('deg.tabPlan'))+'</button>'+
    '<button class="deg-tab'+(xferMode?' on':'')+'" id="degTabXfer">'+esc(t('deg.tabXfer'))+'</button></div>';
  let h=tabs;
  h+='<div style="text-align:center;margin:0 0 10px"><button class="btn btn-line btn-sm" id="degSwitch">'+esc(t('deg.switch'))+'</button></div>';
  if(!xferMode){
    const cap=paceCap(cur.slug);
    const view=reflowView(plan,cap);
    h+=headerHTML(plan,meta,done,earned,total,cap,view);
    h+=intakeHTML(cur.slug);
    h+=paceHTML(plan,done,cap,view);
    view.forEach(function(vs){ h+=semHTML(plan,done,vs); });
  }else{
    h+=xferHTML(plan,meta,done,earned,total);
  }
  body.innerHTML=h;
  bindTracker();
}
/* "I started in" selector: Fall / Spring / Summer + year stepper.
   One tap re-labels every semester instantly; progress is untouched. */
function intakeHTML(slug){
  const it=intakeOf(slug);
  const seg=['fall','spring','summer'].map(function(k){
    return '<button class="deg-intake-term'+(it.term===k?' on':'')+'" data-intake-term="'+k+'">'+
      esc(t(termNameKey(k)))+'</button>';
  }).join('');
  return '<div class="deg-intake" role="group" aria-label="'+esc(t('deg.intakeT'))+'">'+
    '<span class="deg-intake-lab">'+esc(t('deg.intakeT'))+'</span>'+
    '<div class="deg-intake-seg">'+seg+'</div>'+
    '<div class="deg-intake-yr"><button class="deg-yrbtn" data-intake-yr="-1" aria-label="‹">‹</button>'+
    '<span class="deg-yrval">'+it.year+'</span>'+
    '<button class="deg-yrbtn" data-intake-yr="1" aria-label="›">›</button></div></div>';
}
function setIntakeTerm(slug,term){
  if(!cur||cur.slug!==slug) return;
  const p=progFor(slug);
  p.intake.term=(term==='spring'||term==='summer')?term:'fall';
  save(); renderTracker();
}
function setIntakeYear(slug,delta){
  if(!cur||cur.slug!==slug) return;
  const p=progFor(slug);
  const y=Math.min(2100,Math.max(1990,p.intake.year+Number(delta)));
  p.intake.year=y;
  p.startYear=y; /* intake year IS the start year the pace calc uses */
  save(); renderTracker();
}
/* "My pace" control: credits-per-semester chips. 0 = as published.
   When a custom pace is active, a banner states the reshaped timeline and
   the graduation estimate at that pace. */
function paceHTML(plan,done,cap,view){
  const opts=[0,12,13,14,15,16];
  const chips=opts.map(function(v){
    const lab=v===0?t('deg.paceFull'):String(v);
    return '<button class="deg-pace-chip'+(cap===v?' on':'')+'" data-pace="'+v+'" aria-pressed="'+(cap===v)+'">'+
      esc(lab)+'</button>';
  }).join('');
  let h='<div class="deg-pace-ctl" role="group" aria-label="'+esc(t('deg.paceT'))+'">'+
    '<span class="deg-intake-lab">'+esc(t('deg.paceT'))+'</span>'+
    '<div class="deg-pace-chips">'+chips+'</div></div>';
  if(cap&&view&&view.length){
    const fin=termAfter(remainingViewSems(plan,view,done));
    h+='<div class="deg-pace-banner">'+esc(t('deg.paceBanner',{n:cap,s:view.length}))+
      (fin?' · '+esc(t('deg.paceFinish',{term:fin})):'')+'</div>';
  }
  return h;
}
function headerHTML(plan,meta,done,earned,total,cap,view){
  const startYear=progFor(cur.slug).startYear;
  const pace=paceOf(plan,earned,startYear,cap);
  const pct=total?Math.min(100,Math.round(earned/total*100)):0;
  const C=2*Math.PI*32, off=(C*(1-pct/100)).toFixed(1);
  const paceCls=pace.onTrack?'on':'off';
  const paceTxt=pace.onTrack?t('deg.onTrack'):t('deg.behind',{n:pace.behind});
  const fin=cap?termAfter(remainingViewSems(plan,view,done)):finishTerm(plan,earned);
  let h='<div class="deg-head"><div class="deg-ring">'+
    '<svg width="76" height="76" viewBox="0 0 76 76" aria-hidden="true">'+
    '<circle cx="38" cy="38" r="32" fill="none" stroke="var(--surface2)" stroke-width="8"/>'+
    '<circle cx="38" cy="38" r="32" fill="none" stroke="var(--volt)" stroke-width="8" stroke-linecap="round"'+
    ' stroke-dasharray="'+C.toFixed(1)+'" stroke-dashoffset="'+off+'"/></svg>'+
    '<div class="deg-ring-num">'+pct+'%</div></div>'+
    '<div class="deg-head-meta">'+
    '<div class="deg-planname">'+esc(meta.degree)+' · '+esc(meta.major)+'</div>'+
    '<div class="deg-schoolname">'+esc(meta.school)+'</div>'+
    '<div class="deg-pace '+paceCls+'">'+esc(paceTxt)+'</div>'+
    '<div class="deg-earned">'+esc(t('deg.earnedOf',{a:earned,b:total}))+'</div>'+
    '</div></div>';
  if(fin) h+='<div class="deg-finish">'+esc(t(cap?'deg.finishHintPace':'deg.finishHint',{n:cap,term:fin}))+'</div>';
  h+='<div class="deg-source">'+esc(t('deg.source',{school:meta.school,year:plan.catalog_year||''}))+
    ' · <a href="'+esc(plan.source_url||'#')+'" target="_blank" rel="noopener">'+esc(t('deg.viewCatalog'))+'</a></div>';
  if(plan.last_verified) h+='<div class="deg-verified">'+esc(t('deg.lastVerified',{date:plan.last_verified}))+'</div>';
  if(plan.transfer_confidence==='advisory')
    h+='<div class="deg-advisory">'+esc(t('deg.advisoryNote'))+'</div>';
  return h;
}
/* Render one semester section. `vw` is a pace-view semester:
   {n, term, pub, items:[{c,si,ci}]}. Published coordinates (si,ci) are
   preserved on every item, so completion keys, tiles and swipe handlers
   work identically in the re-flowed view. Collapse keys are namespaced so
   the "as published" and "my pace" views keep independent open state. */
function semHTML(plan,done,vw){
  const items=vw.items, n=vw.n;
  const ckey=vw.pub?vw.semN:('pace:'+n);
  let semCr=0, semEarn=0, allDone=true;
  items.forEach(function(it){
    const c=it.c;
    semCr+=Number(c.credits)||0;
    const rec=occRec(done,plan,c,it.si,it.ci);
    if(rec) semEarn+=Number(rec.credits!=null?rec.credits:c.credits)||0;
    else allDone=false;
  });
  const isOpen=collapsed[ckey]!==undefined?!collapsed[ckey]:!allDone;
  collapsed[ckey]=!isOpen;
  const pct=semCr?Math.round(semEarn/semCr*100):0;
  let h='<section class="deg-sem'+(isOpen?' open':'')+'" data-sem="'+esc(String(ckey))+'">'+
    '<button class="deg-sem-hd" data-semtgl="'+esc(String(ckey))+'"><span class="grow">'+
    '<span class="t">'+esc(semTermLabel(n,intakeOf(cur.slug),vw.term))+'</span>'+
    '<span class="s">'+esc(t('deg.semCredits',{n:semCr}))+
    (allDone?' · '+esc(t('deg.semDone')):'')+'</span>'+
    '<span class="deg-sem-bar"><i style="width:'+pct+'%"></i></span></span>'+
    (allDone?'<span class="deg-sem-done">✓</span>':'')+
    '<span class="deg-sem-chev">›</span></button>'+
    '<div class="deg-sem-body">';
  items.forEach(function(it){ h+=tileHTML(plan,it.c,done,it.si,it.ci); });
  h+='</div></section>';
  return h;
}
function tileHTML(plan,c,done,si,ci){
  const rec=occRec(done,plan,c,si,ci);
  const isDone=!!rec;
  const dk=doneKey(plan,c,si,ci);
  const dir=isDone?'right':'left'; /* undone: swipe LEFT completes; done: swipe RIGHT unmarks */
  const warn=unmetWarn(plan,c);
  let code=c.code, title=c.title;
  if(c.choice&&isDone){ code=rec.code||code; title=rec.title||title; }
  const xferCount=distinctXferSchools(c).length;
  let badges='<span class="deg-cat deg-cat-'+esc(c.category||'major')+'">'+esc(catLabel(c.category))+'</span>';
  if(c.choice) badges+='<span class="deg-choice-chip">'+esc(isDone?t('deg.yourChoice'):t('deg.choiceT'))+'</span>';
  if(warn.length) badges+='<span class="deg-warn" data-warn="'+esc(c.slot_id)+'" title="'+esc(warn[0].label)+'">'+esc(t('deg.prereqWarn',{code:warn[0].code||warn[0].label}))+'</span>';
  if(xferCount) badges+='<span class="deg-xfer">'+esc(t('deg.xferTo',{n:xferCount}))+'</span>';
  const pop=lastPop===dk?' deg-pop':'';
  const fl=(lastFloat&&lastFloat.slot===dk)?'<span class="deg-float">+'+lastFloat.text+'</span>':'';
  return '<div class="deg-tile'+(isDone?' done':'')+pop+'" data-slot="'+esc(c.slot_id)+'" data-at="'+si+':'+ci+'" data-dir="'+dir+'">'+fl+
    '<div class="deg-swipe-hint" aria-hidden="true">'+(dir==='left'?'✓':'↩')+'</div>'+
    '<div class="deg-tile-inner">'+
    '<button class="deg-check" data-check="'+esc(c.slot_id)+'" aria-label="'+esc(isDone?t('deg.markUndone'):t('deg.markDone'))+'">✓</button>'+
    '<div class="deg-tile-main" data-open="'+esc(c.slot_id)+'" role="button" tabindex="0" aria-label="'+esc(code+' — '+title)+'">'+
    '<div class="deg-code">'+esc(code)+'<span class="deg-cr">'+esc(String(c.credits))+' cr</span></div>'+
    '<div class="deg-title">'+esc(title)+'</div>'+
    '<div class="deg-badges">'+badges+'</div>'+
    '</div></div></div>';
}
function bindTracker(){
  const body=document.getElementById('degBody');
  if(!body||!cur) return;
  const plan=cur.plan;
  const tp=document.getElementById('degTabPlan');
  const tx=document.getElementById('degTabXfer');
  if(tp) tp.onclick=function(){ xferMode=false; renderTracker(); };
  if(tx) tx.onclick=function(){ xferMode=true; renderTracker(); };
  body.querySelectorAll('[data-semtgl]').forEach(function(btn){
    btn.onclick=function(){
      const key=btn.dataset.semtgl;
      collapsed[key]=!collapsed[key];
      const sec=body.querySelector('[data-sem="'+key+'"]');
      if(sec) sec.classList.toggle('open',!collapsed[key]);
      btn.querySelector('.deg-sem-chev').style.transform='';
    };
  });
  body.querySelectorAll('[data-pace]').forEach(function(btn){
    btn.onclick=function(){ setPaceCap(cur.slug,btn.dataset.pace); };
  });
  body.querySelectorAll('.deg-tile').forEach(function(tile){
    tileDrag(tile);
  });
  body.querySelectorAll('[data-check]').forEach(function(btn){
    btn.onclick=function(e){
      e.stopPropagation();
      const tile=btn.closest('.deg-tile');
      toggleSlot(tile?tile.dataset.slot:btn.dataset.check, tile?tile.dataset.at:null);
    };
  });
  body.querySelectorAll('[data-open]').forEach(function(main){
    const openIt=function(){
      const tile=main.closest('.deg-tile');
      const at=tile?tile.dataset.at:null;
      const occ=findCourse(cur.plan,main.dataset.open,at);
      if(!occ) return;
      const rec=occRec(curDone(),cur.plan,occ.c,occ.si,occ.ci);
      if(occ.c.choice&&!rec) openChoiceSheet(cur.plan,occ.c,at);
      else openDetailSheet(cur.plan,occ.c,at);
    };
    main.onclick=openIt;
    main.onkeydown=function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openIt(); } };
  });
  body.querySelectorAll('[data-warn]').forEach(function(w){
    w.onclick=function(e){
      e.stopPropagation();
      const tile=w.closest('.deg-tile');
      const at=tile?tile.dataset.at:null;
      const occ=findCourse(cur.plan,w.dataset.warn,at);
      if(occ) openDetailSheet(cur.plan,occ.c,at);
    };
  });
  const sw=document.getElementById('degSwitch');
  if(sw) sw.onclick=function(){ renderPicker(); };
  body.querySelectorAll('[data-intake-term]').forEach(function(btn){
    btn.onclick=function(){ setIntakeTerm(cur.slug,btn.dataset.intakeTerm); };
  });
  body.querySelectorAll('[data-intake-yr]').forEach(function(btn){
    btn.onclick=function(){ setIntakeYear(cur.slug,btn.dataset.intakeYr); };
  });
}
/* toggle a slot's completion; choice slots open the picker instead of
   marking done with a placeholder code. `at` ("si:ci") pins the exact tile
   occurrence — without it the first matching course is used. */
function toggleSlot(slotId,at){
  if(!cur) return; /* swipe fly-off may land after the overlay closed */
  const occ=findCourse(cur.plan,slotId,at);
  if(!occ) return;
  const plan=cur.plan, c=occ.c, done=curDone(), dk=doneKey(plan,c,occ.si,occ.ci);
  let rec=done[dk], rkey=dk;
  if(!rec&&done[c.slot_id]){
    /* legacy bare record that occRec matches to this occurrence */
    const lr=occRec(done,plan,c,occ.si,occ.ci);
    if(lr){ rec=lr; rkey=c.slot_id; }
  }
  if(rec){
    delete done[rkey];
    save();
    ui().toast(t('deg.undoneToast',{code:c.code}));
    lastPop=null; lastFloat=null;
    renderTracker();
    return;
  }
  if(c.choice){ openChoiceSheet(plan,c,occKey(occ.si,occ.ci)); return; }
  done[dk]={code:c.code,title:c.title,credits:Number(c.credits)||0,ts:Date.now(),at:occKey(occ.si,occ.ci)};
  save();
  ui().toast(t('deg.doneToast',{code:c.code}));
  try{ if(HUB.fx&&HUB.fx.haptic) HUB.fx.haptic('success'); }catch(e2){}
  lastPop=dk; lastFloat={slot:dk,text:(Number(c.credits)||0)};
  renderTracker();
  lastPop=null; lastFloat=null;
}
function completeChoice(plan,c,pick,at){
  const occ=findCourse(plan,c.slot_id,at);
  const si=occ?occ.si:0, ci=occ?occ.ci:0, dk=doneKey(plan,c,si,ci);
  const done=curDone();
  done[dk]={code:pick.code,title:pick.title||c.title,
    credits:(typeof pick.credits==='number'?pick.credits:(Number(c.credits)||0)),ts:Date.now(),at:occKey(si,ci)};
  save();
  ui().closeSheet();
  ui().toast(t('deg.doneToast',{code:pick.code}));
  try{ if(HUB.fx&&HUB.fx.haptic) HUB.fx.haptic('success'); }catch(e2){}
  lastPop=dk; lastFloat={slot:dk,text:done[dk].credits};
  renderTracker();
  lastPop=null; lastFloat=null;
}

/* ---------------- swipe-to-complete (pointer events unify touch + mouse) ----
   Tiles carry touch-action:pan-y so vertical scrolls stay native; horizontal
   drags are tracked here. One active drag at a time (module-level). The hint
   layer behind the tile shows ✓ (complete) or ↩ (unmark) during the drag.
   A ✓ button on every tile is the accessible toggle — swipe is enhancement.
   Silent: no sounds anywhere; completion is a scale/glow burst (see .deg-pop). */
let drag=null;
function tileDrag(tile){
  const inner=tile.querySelector('.deg-tile-inner');
  if(!inner) return;
  tile.addEventListener('pointerdown',function(e){
    if(drag||e.button>0||!cur) return;
    if(e.target.closest('button')) return; /* ✓ / badge taps own their clicks */
    const rtl=document.documentElement.dir==='rtl'?-1:1;
    const want=(tile.dataset.dir==='right'?1:-1)*rtl;
    drag={tile:tile,inner:inner,sx:e.clientX,sy:e.clientY,dx:0,mode:null,want:want};
    inner.style.transition='none';
  });
}
window.addEventListener('pointermove',function(e){
  if(!drag) return;
  const d=drag, ddx=e.clientX-d.sx, ddy=e.clientY-d.sy;
  if(d.mode===null){
    if(Math.abs(ddx)<10&&Math.abs(ddy)<10) return;
    d.mode=Math.abs(ddx)>Math.abs(ddy)?'x':'y';
    if(d.mode==='y'){ drag=null; d.inner.style.transition=''; d.inner.style.transform=''; return; }
  }
  if(d.mode!=='x') return;
  d.dx=ddx;
  /* rubber-band the wrong direction; the commit direction slides freely */
  const dd=(ddx*d.want<0)?ddx*0.22:ddx;
  d.inner.style.transform='translateX('+dd.toFixed(1)+'px) rotateY('+(dd*0.05).toFixed(2)+'deg)';
  d.tile.classList.toggle('deg-armed',Math.abs(ddx)>64&&ddx*d.want>0);
});
function dragReset(d){
  drag=null;
  d.inner.style.transition='';
  d.inner.style.transform='';
  d.tile.classList.remove('deg-armed');
}
window.addEventListener('pointerup',function(){
  if(!drag) return;
  const d=drag;
  if(d.mode!=='x'){ dragReset(d); return; }
  const go=Math.abs(d.dx)>64&&d.dx*d.want>0;
  drag=null;
  d.inner.style.transition='transform .3s var(--ease-spring),opacity .25s ease';
  if(go){
    /* fly-off, then commit on the 3D slide — the re-render plays the burst */
    d.inner.style.transform='translateX('+(d.want*160)+'px) rotateY('+(d.want*10)+'deg)';
    d.inner.style.opacity='0';
    const tile=d.tile;
    setTimeout(function(){
      tileDragCleanup(tile);
      toggleSlot(tile.dataset.slot, tile.dataset.at);
    },300);
  }else{
    d.inner.style.transform='';
    d.inner.style.opacity='';
    d.tile.classList.remove('deg-armed');
  }
});
window.addEventListener('pointercancel',function(){
  if(drag) dragReset(drag);
});
function tileDragCleanup(){ /* per-tile state lives on the drag object only */ }

/* ---------------- choice slot sheet ---------------- */
function openChoiceSheet(plan,c,at){
  const opts=normOptions(plan,c);
  let h='<h2>'+esc(t('deg.choiceT'))+'</h2>';
  if(c.choice_note) h+='<p class="sub" style="margin:4px 0 6px">'+esc(c.choice_note)+'</p>';
  h+='<p class="sub">'+esc(c.code)+' · '+esc(c.title)+' · '+esc(String(c.credits))+' cr</p>';
  if(opts.length){
    h+='<div class="deg-optlist">';
    opts.forEach(function(o,ix){
      h+='<button class="deg-opt" data-opt="'+ix+'"><span class="c">'+esc(o.code)+'</span> '+
        '<span class="cr2">'+esc(String(o.credits!=null?o.credits:(c.credits||'')))+' cr</span>'+
        '<span class="ti">'+esc(o.title||'')+'</span></button>';
    });
    h+='</div>';
  }else{
    h+='<div class="field"><label>'+esc(t('deg.choiceT'))+'</label>'+
      '<input class="input" id="degChoiceCode" autocomplete="off" placeholder="'+esc(t('deg.choiceCodePh'))+'"></div>'+
      '<div class="field"><input class="input" id="degChoiceTitle" autocomplete="off" placeholder="'+esc(t('deg.choiceTitlePh'))+'"></div>'+
      '<button class="btn btn-primary btn-block" id="degChoiceSave">'+esc(t('deg.choiceSave'))+'</button>';
  }
  ui().openSheet(h);
  const box=document.getElementById('sheetBox');
  if(!box) return;
  box.querySelectorAll('[data-opt]').forEach(function(btn){
    btn.onclick=function(){
      const o=opts[Number(btn.dataset.opt)];
      if(o) completeChoice(plan,c,{code:o.code,title:o.title,credits:(o.credits!=null?o.credits:Number(c.credits)||0)},at);
    };
  });
  const saveBtn=document.getElementById('degChoiceSave');
  if(saveBtn) saveBtn.onclick=function(){
    const codeEl=document.getElementById('degChoiceCode');
    const titleEl=document.getElementById('degChoiceTitle');
    const code=(codeEl.value||'').trim().toUpperCase();
    if(!code){ codeEl.focus(); ui().toast(t('deg.choiceNeed')); return; }
    completeChoice(plan,c,{code:code,title:(titleEl.value||'').trim(),credits:Number(c.credits)||0},at);
  };
}

/* ---------------- course detail sheet ---------------- */
function distinctXferSchools(c){
  const slugs=c.xfer||[];
  const seen={}, out=[];
  (DATA.idx&&DATA.idx.plans||[]).forEach(function(p){ seen[p.slug]=p.school; });
  slugs.forEach(function(sg){
    const nm=seen[sg];
    if(nm&&out.indexOf(nm)===-1) out.push(nm);
  });
  return out;
}
function openDetailSheet(plan,c,at){
  const occ=findCourse(plan,c.slot_id,at);
  const done=curDone(), rec=occ?occRec(done,plan,occ.c,occ.si,occ.ci):null;
  const reqs=prereqList(plan,c);
  const dests=distinctXferSchools(c);
  let h='<h2>'+esc(rec&&c.choice?rec.code:c.code)+'</h2>'+
    '<p class="sub">'+esc(rec&&c.choice?(rec.title||c.title):c.title)+'</p>';
  h+='<div class="deg-detail-row"><span class="k">'+esc(t('deg.detailT'))+'</span><span>'+
    '<span class="deg-cat deg-cat-'+esc(c.category||'major')+'">'+esc(catLabel(c.category))+'</span> · '+
    esc(String(c.credits))+' cr'+(c.core_area?' · '+esc(c.core_area):'')+'</span></div>';
  if(c.choice&&c.choice_note)
    h+='<div class="deg-detail-row"><span class="k">'+esc(t('deg.choiceT'))+'</span><span>'+esc(c.choice_note)+'</span></div>';
  /* Choice slots: offer the options right here so a completed pick can be
     SWAPPED for another without mark-undone -> re-pick. Tapping an option
     calls completeChoice, which overwrites the same occurrence key. */
  const dopts=c.choice?normOptions(plan,c):[];
  if(dopts.length){
    const curPick=normCode(rec&&rec.code);
    h+='<h3 style="margin:12px 0 4px;font-size:14px">'+esc(t('deg.choiceT'))+'</h3><div class="deg-optlist">';
    dopts.forEach(function(o,ix){
      const sel=!!(curPick&&normCode(o.code)===curPick);
      h+='<button class="deg-opt" data-dopt="'+ix+'"><span class="c">'+esc(o.code)+'</span> '+
        '<span class="cr2">'+esc(String(o.credits!=null?o.credits:(c.credits||'')))+' cr</span>'+
        '<span class="ti">'+esc(o.title||'')+'</span>'+
        (sel?' <span class="deg-choice-chip">'+esc(t('deg.yourChoice'))+'</span>':'')+'</button>';
    });
    h+='</div>';
  }
  if(reqs.length){
    h+='<h3 style="margin:12px 0 4px;font-size:14px">'+esc(t('deg.prereqT'))+'</h3>';
    reqs.forEach(function(r){
      const cls=r.ok===true?'ok':(r.ok===false?'no':'ok');
      const mark=r.ok===true?'✓':(r.ok===false?'!':'i');
      const st=r.ok===true?t('deg.prereqDone'):(r.ok===false?t('deg.prereqPending'):'');
      h+='<div class="deg-req"><span class="st '+cls+'">'+mark+'</span><span>'+esc(r.label)+
        (st?' <span style="color:var(--muted);font-size:12px">· '+esc(st)+'</span>':'')+'</span></div>';
    });
  }
  if(dests.length){
    h+='<h3 style="margin:12px 0 4px;font-size:14px">'+esc(t('deg.xferT'))+'</h3>';
    dests.forEach(function(nm){ h+='<div class="deg-req"><span class="st ok">🔀</span><span>'+esc(nm)+'</span></div>'; });
  }
  h+='<div style="margin-top:14px"><button class="btn '+(rec?'btn-line':'btn-primary')+' btn-block" id="degDetailToggle">'+
    esc(rec?t('deg.markUndone'):t('deg.markDone'))+'</button></div>';
  ui().openSheet(h);
  const box=document.getElementById('sheetBox');
  if(box) box.querySelectorAll('[data-dopt]').forEach(function(btn){
    btn.onclick=function(){
      const o=dopts[Number(btn.dataset.dopt)];
      if(o) completeChoice(plan,c,{code:o.code,title:o.title,
        credits:(o.credits!=null?o.credits:Number(c.credits)||0)},at);
    };
  });
  const tg=document.getElementById('degDetailToggle');
  if(tg) tg.onclick=function(){ ui().closeSheet(); toggleSlot(c.slot_id,at); };
}

/* ---------------- transfer view ---------------- */
function xferHTML(plan,meta,done,earned,total){
  const idxPlans=(DATA.idx&&DATA.idx.plans)||[];
  const bySlug={};
  idxPlans.forEach(function(p){ bySlug[p.slug]=p; });
  let h='<div class="deg-source">'+esc(t('deg.source',{school:meta.school,year:plan.catalog_year||''}))+
    ' · <a href="'+esc(plan.source_url||'#')+'" target="_blank" rel="noopener">'+esc(t('deg.viewCatalog'))+'</a></div>';
  if(plan.last_verified) h+='<div class="deg-verified">'+esc(t('deg.lastVerified',{date:plan.last_verified}))+'</div>';
  if(plan.transfer_confidence==='advisory')
    h+='<div class="deg-advisory">'+esc(t('deg.advisoryNote'))+'</div>';
  const perSchool={}; /* school -> {credits} */
  let rows='', anyX=false;
  semsOf(plan).forEach(function(sem){
    (sem.courses||[]).forEach(function(c){
      const dests=distinctXferSchools(c);
      if(!dests.length) return;
      anyX=true;
      const cr=Number(c.credits)||0;
      dests.forEach(function(nm){ perSchool[nm]=(perSchool[nm]||0)+cr; });
      rows+='<div class="deg-xrow"><div class="code">'+esc(c.code)+' <span class="deg-cr">'+esc(String(c.credits))+' cr</span></div>'+
        '<div class="title">'+esc(c.title)+'</div>'+
        '<div class="dests">🔀 '+esc(dests.join(' · '))+'</div></div>';
    });
  });
  if(!anyX){
    return h+'<div class="empty ps-empty"><div class="big">🔀</div><p><b>'+esc(t('deg.xferNone'))+'</b></p>'+
      '<p class="sub">'+esc(t('deg.xferNote'))+'</p></div>';
  }
  Object.keys(perSchool).sort().forEach(function(nm){
    h+='<div class="deg-xsummary">'+esc(t('deg.xferSummary',{a:perSchool[nm],b:total,school:nm}))+'</div>';
  });
  h+='<div class="deg-xnote">'+esc(t('deg.xferNote'))+'</div>'+rows;
  return h;
}

/* ---------------- Home tab entry card ----------------
   One managed row card near the Grade Calculator (home.js renders
   HUB.degree.entryHTML() and binds HUB.degree.bindEntry(el)), so it
   survives i18n re-renders like every other home card. */
/* ---------------- Home tab entry card ----------------
   Big glowing hero card (PraBin 2026-10-07): 3D graduation cap with volt
   halo, float animation, shimmer sweep — sized like the Appointments card
   to attract taps. home.js renders HUB.degree.entryHTML() and binds
   HUB.degree.bindEntry(el); #homeDegSub keeps receiving the live
   "{n} plans · {s} schools" counts. */
function entryHTML(){
  return '<div class="hsec"><div class="deg-hero" id="homeDegEntry" role="button" tabindex="0"'+
    ' aria-label="'+esc(t('deg.entryTitle'))+'">'+
    '<div class="deg-hero-cap" aria-hidden="true">'+
    '<svg viewBox="0 0 120 120" width="104" height="104">'+
    '<defs>'+
    '<radialGradient id="degHeroHalo" cx="50%" cy="50%" r="50%">'+
    '<stop offset="0%" stop-color="#C6F135" stop-opacity=".55"/>'+
    '<stop offset="60%" stop-color="#C6F135" stop-opacity=".12"/>'+
    '<stop offset="100%" stop-color="#C6F135" stop-opacity="0"/></radialGradient>'+
    '<linearGradient id="degHeroBoard" x1="0" y1="0" x2="1" y2="1">'+
    '<stop offset="0%" stop-color="#2b3440"/><stop offset="55%" stop-color="#171d26"/>'+
    '<stop offset="100%" stop-color="#0c0f14"/></linearGradient>'+
    '<linearGradient id="degHeroBand" x1="0" y1="0" x2="0" y2="1">'+
    '<stop offset="0%" stop-color="#232b37"/><stop offset="100%" stop-color="#10141b"/></linearGradient>'+
    '<filter id="degHeroDS" x="-40%" y="-40%" width="180%" height="180%">'+
    '<feDropShadow dx="0" dy="7" stdDeviation="7" flood-color="#000" flood-opacity=".55"/>'+
    '<feDropShadow dx="0" dy="0" stdDeviation="10" flood-color="#C6F135" flood-opacity=".28"/></filter>'+
    '</defs>'+
    '<circle cx="60" cy="60" r="46" fill="url(#degHeroHalo)"/>'+
    '<g filter="url(#degHeroDS)">'+
    '<path d="M38,54 L38,74 Q60,88 82,74 L82,54 Z" fill="url(#degHeroBand)"/>'+
    '<polygon points="60,20 106,43 60,66 14,43" fill="url(#degHeroBoard)" stroke="rgba(198,241,53,.45)" stroke-width="1.6" stroke-linejoin="round"/>'+
    '<polygon points="60,20 106,43 60,66 14,43" fill="none" stroke="rgba(255,255,255,.16)" stroke-width="1" stroke-linejoin="round" transform="translate(0,-2.5)"/>'+
    '<circle cx="60" cy="43" r="4.2" fill="#C6F135"/>'+
    '<g class="deg-hero-tassel"><path d="M60,43 C86,47 94,58 94,78" fill="none" stroke="#C6F135" stroke-width="2.4" stroke-linecap="round"/>'+
    '<rect x="88.5" y="76" width="11" height="17" rx="5.5" fill="#C6F135"/>'+
    '<path d="M91,85 L91,95 M94,85 L94,96 M97,85 L97,95" stroke="#9db82a" stroke-width="1.6" stroke-linecap="round"/></g>'+
    '</g>'+
    '<path class="deg-hero-spark1" d="M22,26 l1.6,4 4,1.6 -4,1.6 -1.6,4 -1.6,-4 -4,-1.6 4,-1.6 z" fill="#C6F135"/>'+
    '<path class="deg-hero-spark2" d="M98,88 l1.2,3 3,1.2 -3,1.2 -1.2,3 -1.2,-3 -3,-1.2 3,-1.2 z" fill="#fff"/>'+
    '</svg></div>'+
    '<div class="deg-hero-t">'+esc(t('deg.entryTitle'))+'</div>'+
    '<div class="deg-hero-pill"><span id="homeDegSub">'+esc(t('deg.entryHook'))+'</span></div>'+
    '<div class="deg-hero-cta">'+esc(t('deg.entryCta'))+'<span aria-hidden="true"> →</span></div>'+
    '</div></div>';
}
/* last rendered counts on #homeDegSub — the count-up only plays on first
   paint and when the values actually change, never on identical re-renders. */
var degCountsShown=null;
function bindEntry(scope){
  const root=(scope&&scope.querySelector)?scope:document;
  const b=root.querySelector?root.querySelector('#homeDegEntry'):document.getElementById('homeDegEntry');
  if(b){
    const go=function(){ open(dstate().active||null); };
    b.onclick=go;
    b.onkeydown=function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
  }
  /* honest live counts: complete plans + full national inventory
     ("7 plans · 3,898 schools"). If the API is still waking up (Render free
     tier sleeps), retry instead of showing "0 plans".
     The plans number count-ups (Stripe/Revolut pattern) on first paint and
     whenever the value actually changes — identical re-renders set the text
     directly with no animation. */
  function updateCounts(tries){
    degIndex().then(function(idx){
      const sub=root.querySelector?root.querySelector('#homeDegSub'):document.getElementById('homeDegSub');
      if(!sub) return;
      const nPlans=(idx.plans||[]).length;
      const nSchools=idx.national_schools||(idx.schools||[]).length;
      if(nPlans===0 && !DATA.idxFailed && (tries||0)<3){
        setTimeout(function(){ updateCounts((tries||0)+1); }, 8000);
        return;
      }
      const schoolsStr=Number(nSchools).toLocaleString('en-US');
      const prev=degCountsShown;
      degCountsShown={plans:nPlans, schools:nSchools};
      const fx=(window.HUB&&HUB.fx)||null;
      if(fx&&fx.countUp&&(!prev||prev.plans!==nPlans)){
        fx.countUp(sub, prev?prev.plans:0, nPlans, {dur:750, format:function(v){
          return t('deg.entrySub',{n:Math.round(v).toLocaleString('en-US'), s:schoolsStr});
        }});
      }else{
        sub.textContent=t('deg.entrySub',{n:Number(nPlans).toLocaleString('en-US'), s:schoolsStr});
      }
    });
  }
  updateCounts(0);
}

HUB.degree={open:open,close:close,entryHTML:entryHTML,bindEntry:bindEntry,_state:dstate};
})();
