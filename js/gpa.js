/* HUB GPA calculator (2026-09-22): semester GPA card on Home, rendered between
   the classes card and the appointments card (home.js inserts HUB.gpa.cardHTML()).
   Courses persist browser-locally in store.state.gpaCourses. Classic IIFE. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

/* stylesheet injection — keeps the index.html edit surface to one script line */
(function(){
  if(document.querySelector('link[data-gpa-css]')) return;
  const l=document.createElement('link');
  l.rel='stylesheet'; l.href='css/gpa.css'; l.setAttribute('data-gpa-css','1');
  document.head.appendChild(l);
})();

const GP={A:4,B:3,C:2,D:1,F:0};
const GRADES=['A','B','C','D','F'];
/* polish pass (2026-09-22): live grade-reactive tint + animated GPA number.
   gpaFrom = previous on-screen GPA (for count-up); freshId = course just
   added (for entrance animation). band() maps GPA to a color band. */
let gpaFrom=null, freshId=null;
function band(r){
  if(!r.count) return 0;
  const g=r.gpa;
  if(g>=3.5) return 5;
  if(g>=3) return 4;
  if(g>=2) return 3;
  if(g>=1) return 2;
  return 1;
}

function courses(){
  if(!Array.isArray(store.state.gpaCourses)) store.state.gpaCourses=[];
  return store.state.gpaCourses;
}
function calc(){
  let pts=0, cr=0;
  for(const c of courses()){
    const p=GP[c.grade];
    const h=Number(c.credits)||0;
    if(p===undefined||!(h>0)) continue;
    pts+=p*h; cr+=h;
  }
  return {gpa: cr>0? pts/cr : 0, credits: Math.round(cr*100)/100, count: courses().length};
}
function refresh(){
  try{
    const old=document.querySelector('#gpaCard .gpa-num');
    if(old) gpaFrom=parseFloat(old.textContent)||0;
    const el=document.getElementById('view-home');
    if(el&&HUB.views&&HUB.views.home&&!el.hidden) HUB.views.home.render(el);
  }catch(e){}
  animateNum();
}
/* Count-up the big GPA numeral + a soft glow pulse so the number feels alive.
   Reads the pre-render value captured in refresh(); no-ops on first paint. */
function animateNum(){
  const el=document.querySelector('#gpaCard .gpa-num');
  if(!el) return;
  const to=calc().gpa, from=(gpaFrom==null)?to:gpaFrom;
  gpaFrom=null;
  el.textContent=to.toFixed(2);
  if(Math.abs(to-from)<0.005) return;
  const hero=el.closest('.gpa-hero');
  if(hero){ hero.classList.remove('gpa-pulse'); void hero.offsetWidth; hero.classList.add('gpa-pulse'); }
  const t0=performance.now(), dur=650;
  (function frame(now){
    const ms=(typeof now==='number')?now:performance.now();
    /* clamp p to [0,1]: a rAF timestamp older than t0 (stale compositor clock,
       seen in headless) would otherwise make p negative and the cubic ease
       overshoot far above `from` (e.g. GPA flashing 5.67). */
    const p=Math.min(1,Math.max(0,(ms-t0)/dur)), e=1-Math.pow(1-p,3);
    el.textContent=(from+(to-from)*e).toFixed(2);
    if(p<1) requestAnimationFrame(frame);
  })();
}

/* ---------------- Home card ---------------- */
function cardHTML(){
  const r=calc(), rb=band(r);
  let html='<div class="hsec"><div class="hsec-hd"><h2>'+ui.esc(t('gpa.title'))+'</h2>'
    +'<button class="hsec-act" data-gpa-add>'+ui.esc(t('gpa.add'))+'</button></div>'
    +'<div class="gpa-card gb'+rb+'" id="gpaCard">'
    +'<div class="gpa-hero gb'+rb+'"><div class="gpa-num">'+r.gpa.toFixed(2)+'</div>'
    +'<div class="gpa-sub">'+ui.esc(t('gpa.gpa'))+'</div>'
    +'<div class="gpa-meta"><span class="gpa-chip">'+ui.esc(t('gpa.credits',{n:r.credits}))+'</span>'
    +'<span class="gpa-chip">'+ui.esc(t('gpa.courses',{n:r.count}))+'</span></div></div>';
  const list=courses();
  if(!list.length){
    html+='<div class="gpa-empty"><div class="big">📝</div><div>'+ui.esc(t('gpa.empty'))+'</div></div>';
  }else{
    for(const c of list){
      const g=GP[c.grade]!==undefined?c.grade:'F';
      const isNew=freshId&&String(c.id)===String(freshId);
      const gid=ui.esc(String(c.id));
      /* swipe wrapper (mirrors household bill rows): swipe the inner row left
         to reveal Edit/Delete; the ⋯ button is the non-gesture fallback. */
      html+='<div class="gpa-swipe" data-gswipe="'+gid+'">'
        +'<div class="gpa-swactions">'
        +'<button class="gsw-edit" data-gpa-edit="'+gid+'">✏️ '+ui.esc(t('common.edit'))+'</button>'
        +'<button class="gsw-del" data-gpa-del="'+gid+'">🗑️ '+ui.esc(t('common.delete'))+'</button></div>'
        +'<div class="gpa-inner'+(isNew?' gpa-new':'')+'">'
        +'<span class="gp-pill gp-'+g+'">'+g+'</span>'
        +'<div class="grow"><div class="gpa-subj">'+ui.esc(c.subject||'—')+'</div>'
        +'<div class="gpa-cr">'+ui.esc(t('gpa.credits',{n:Number(c.credits)||0}))+'</div></div>'
        +'<button class="gpa-more" data-gpa-more="'+gid+'" aria-label="'+ui.esc(t('common.edit'))+'">⋯</button></div></div>';
    }
    html+='<div class="gpa-foot"><button class="btn btn-line btn-sm" data-gpa-clear>'+ui.esc(t('gpa.clear'))+'</button></div>';
  }
  freshId=null;
  return html+'</div></div>';
}

/* ---------------- add/edit course sheet ----------------
   Shared form: add (editId null) or edit (prefilled; the grade-reactive
   background opens on the course's grade). */
let pickGrade='A';
function courseSheet(editId){
  const isEdit=!!editId;
  const ec=isEdit?courses().find(function(x){ return String(x.id)===String(editId); }):null;
  if(isEdit&&!ec) return;
  pickGrade=isEdit&&GP[ec.grade]!==undefined?ec.grade:'A';
  ui.openSheet(
    '<div class="gpa-form gg-'+pickGrade+'">'
    +'<h2>🎓 '+ui.esc(t(isEdit?'gpa.editT':'gpa.formT'))+'</h2>'
    +'<div class="field"><label>'+ui.esc(t('gpa.subject'))+'</label>'
    +'<input class="input" id="gpaSubj" maxlength="60" placeholder="'+ui.esc(t('gpa.subjectPh'))+'" value="'+ui.esc(isEdit?ec.subject:'')+'"></div>'
    +'<div class="field"><label>'+ui.esc(t('gpa.creditsL'))+'</label>'
    +'<input class="input" id="gpaCr" type="number" min="0.5" max="12" step="0.5" inputmode="decimal" placeholder="3" value="'+(isEdit?ec.credits:'')+'"></div>'
    +'<div class="field"><label>'+ui.esc(t('gpa.grade'))+'</label><div class="gpa-seg">'
    +GRADES.map(function(g){ return '<button class="gpa-segbtn'+(g===pickGrade?' on':'')+'" data-ggrade="'+g+'">'+g+'</button>'; }).join('')
    +'</div></div>'
    +'<button class="btn btn-primary btn-block" id="gpaSave">'+ui.esc(t(isEdit?'common.save':'gpa.add'))+'</button></div>'
  );
  document.querySelectorAll('[data-ggrade]').forEach(function(b){
    b.onclick=function(){
      pickGrade=b.dataset.ggrade;
      document.querySelectorAll('[data-ggrade]').forEach(function(x){ x.classList.toggle('on',x===b); });
      const form=document.querySelector('.gpa-form');
      if(form) form.className='gpa-form gg-'+pickGrade; /* live grade-reactive background */
    };
  });
  document.getElementById('gpaSave').onclick=function(){
    const subj=document.getElementById('gpaSubj').value.trim();
    const cr=parseFloat(document.getElementById('gpaCr').value);
    if(!subj){ ui.toast(t('gpa.needSubject')); return; }
    if(!(cr>0)){ ui.toast(t('gpa.needCredits')); return; }
    if(isEdit){
      ec.subject=subj; ec.credits=Math.round(cr*100)/100; ec.grade=pickGrade;
      freshId=ec.id; store.save(); ui.closeSheet(); refresh();
      ui.toast(t('gpa.updated',{subject:subj}));
    }else{
      const nid=store.uid();
      courses().push({id:nid,subject:subj,credits:Math.round(cr*100)/100,grade:pickGrade});
      freshId=nid;
      store.save(); ui.closeSheet(); refresh();
      ui.toast(t('gpa.added',{subject:subj}));
    }
  };
}
function addSheet(){ courseSheet(null); }

/* ---------------- clear-all confirm ---------------- */
function clearSheet(){
  ui.openSheet(
    '<h2>'+ui.esc(t('gpa.clearT'))+'</h2>'
    +'<p class="sub" style="margin:6px 0 14px">'+ui.esc(t('gpa.clearD'))+'</p>'
    +'<button class="btn btn-block" id="cfGo" style="background:#ef4444;color:#fff;font-weight:800">'+ui.esc(t('gpa.clearGo'))+'</button>'
    +'<button class="btn btn-ghost btn-block" id="cfNo" style="margin-top:8px">'+ui.esc(t('common.cancel'))+'</button>'
  );
  document.getElementById('cfNo').onclick=ui.closeSheet;
  document.getElementById('cfGo').onclick=function(){
    store.state.gpaCourses=[]; store.save(); ui.closeSheet(); refresh();
    ui.toast(t('gpa.cleared'));
  };
}

/* ---------------- swipe-to-edit/delete (mirrors household bill swipe) ----------------
   iOS hardening (2026-09-22): the tray appears ONLY after a real horizontal
   swipe (>=24px, horizontal-dominant). A plain tap never reveals it — it only
   snaps an already-open tray shut. The tray is opacity:0 + visibility:hidden
   by default, so even an iOS-mis-sized tray can never bleed through. */
const GPA_SWIPE_W=148; /* two 74px action buttons */
const GPA_SWIPE_ARM=24; /* min horizontal px before a drag counts as a swipe */
function closeOthersSwipes(except){
  document.querySelectorAll('#gpaCard .gpa-swipe.gpa-open').forEach(function(r){
    if(r===except) return;
    r.classList.remove('gpa-open','gpa-drag');
    const ir=r.querySelector('.gpa-inner');
    if(ir){ ir.style.transition='transform .18s ease'; ir.style.transform='translateX(0px)'; }
  });
}
function bindGpaSwipe(row){
  if(row.dataset.sbound) return; row.dataset.sbound='1';
  const inner=row.querySelector('.gpa-inner');
  if(!inner) return;
  let sx=0, sy=0, dx=0, dy=0, armed=false, swiped=false, pid=null;
  const setX=function(x){ inner.style.transform='translateX('+x+'px)'; };
  const openRow=function(){
    inner.style.transition='transform .18s ease';
    setX(-GPA_SWIPE_W);
    row.classList.add('gpa-open'); row.classList.remove('gpa-drag');
    setTimeout(function(){ inner.style.transition=''; },220);
  };
  const closeRow=function(){
    inner.style.transition='transform .18s ease';
    setX(0);
    row.classList.remove('gpa-open','gpa-drag');
    setTimeout(function(){ inner.style.transition=''; },220);
  };
  const onDown=function(x,y,id){
    closeOthersSwipes(row);
    sx=x; sy=y; dx=0; dy=0; armed=false; swiped=false; pid=id;
    inner.style.transition='';
    /* tray stays fully hidden until the swipe threshold is crossed */
  };
  const onMove=function(x,y,id){
    if(pid!==null&&id!==pid) return;
    dx=x-sx; dy=y-sy;
    if(!armed){
      if(Math.abs(dx)>=GPA_SWIPE_ARM&&Math.abs(dx)>Math.abs(dy)*1.2){
        armed=true; row.classList.add('gpa-drag'); /* tray fades in only now */
      }
      return;
    }
    setX(dx<0?Math.max(-GPA_SWIPE_W,dx):0);
  };
  const onUp=function(id,target){
    if(pid!==null&&id!==pid) return;
    pid=null;
    if(!armed){
      /* plain tap: never opens; snaps an open tray shut — UNLESS the tap
         landed on a tray action button (Edit/Delete). Closing the tray here
         strips pointer-events from the tray BEFORE iOS Safari dispatches the
         synthesized click, so WebKit hit-tests the click onto the row beneath
         and the button's tap silently does nothing. Leave the tray open and
         hit-testable; the button's own click (closeOpenSwipes) shuts it right
         after. */
      if(target&&target.closest&&target.closest('.gpa-swactions')) return;
      if(row.classList.contains('gpa-open')) closeRow();
      return;
    }
    armed=false; swiped=true;
    if(dx<-GPA_SWIPE_W*0.45) openRow(); else closeRow();
    setTimeout(function(){ swiped=false; },350);
  };
  const onCancel=function(){
    pid=null; armed=false; swiped=false;
    row.classList.remove('gpa-open','gpa-drag');
    inner.style.transition=''; setX(0);
  };
  if(window.PointerEvent){
    row.addEventListener('pointerdown',function(e){ onDown(e.clientX,e.clientY,e.pointerId); },{passive:true});
    row.addEventListener('pointermove',function(e){ onMove(e.clientX,e.clientY,e.pointerId); },{passive:true});
    row.addEventListener('pointerup',function(e){ onUp(e.pointerId,e.target); });
    row.addEventListener('pointercancel',onCancel);
  }else{ /* touch fallback for browsers without Pointer Events */
    row.addEventListener('touchstart',function(e){ const tc=e.touches[0]; onDown(tc.clientX,tc.clientY,0); },{passive:true});
    row.addEventListener('touchmove',function(e){ const tc=e.touches[0]; onMove(tc.clientX,tc.clientY,0); },{passive:true});
    row.addEventListener('touchend',function(e){ onUp(0,e.target); });
    row.addEventListener('touchcancel',onCancel);
  }
  /* tap on the row body snaps a revealed tray shut; the click landing right
     after a real swipe is suppressed so the tray stays open */
  inner.addEventListener('click',function(e){
    if(swiped){ e.stopPropagation(); e.preventDefault(); return; }
    if(row.classList.contains('gpa-open')) closeRow();
  });
}
function closeOpenSwipes(){
  document.querySelectorAll('#gpaCard .gpa-swipe').forEach(function(row){
    row.classList.remove('gpa-open','gpa-drag');
    const inner=row.querySelector('.gpa-inner');
    if(inner){ inner.style.transition=''; inner.style.transform='translateX(0px)'; }
  });
}
function bindGpaRows(){
  document.querySelectorAll('#gpaCard [data-gswipe]').forEach(bindGpaSwipe);
}
/* home re-renders the card on every refresh(): observe so new rows get bound */
new MutationObserver(function(){ bindGpaRows(); }).observe(document.documentElement,{childList:true,subtree:true});
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bindGpaRows);
else bindGpaRows();

/* ---------------- ⋯ fallback sheet (non-touch/desktop) ---------------- */
function moreSheet(id){
  const c=courses().find(function(x){ return String(x.id)===String(id); });
  if(!c) return;
  ui.openSheet('<h2>🎓 '+ui.esc(c.subject||'—')+'</h2>'
    +'<p class="sub" style="margin:0 0 12px">'+ui.esc(t('gpa.credits',{n:Number(c.credits)||0}))+' · '+ui.esc(c.grade||'—')+'</p>'
    +'<div class="row" style="gap:8px">'
    +'<button class="btn btn-line" id="gmEdit" style="flex:1">✏️ '+ui.esc(t('common.edit'))+'</button>'
    +'<button class="btn" id="gmDel" style="flex:1;background:#e5484d;color:#fff;border:0">🗑️ '+ui.esc(t('common.delete'))+'</button></div>');
  document.getElementById('gmEdit').onclick=function(){ ui.closeSheet(); courseSheet(id); };
  document.getElementById('gmDel').onclick=function(){ ui.closeSheet(); delCourse(id); };
}

/* ---------------- delete (confirm, then slide-away) ---------------- */
function delCourse(id){
  const c=courses().find(function(x){ return String(x.id)===String(id); });
  if(!c) return;
  if(!confirm(t('gpa.delC',{subject:c.subject||'—'}))) return;
  const row=document.querySelector('#gpaCard [data-gswipe="'+id+'"] .gpa-inner');
  const go=function(){
    const list=courses();
    const ix=list.findIndex(function(x){ return String(x.id)===String(id); });
    if(ix>=0){
      const nm=list[ix].subject;
      list.splice(ix,1); store.save(); refresh(); /* GPA, chips, band re-calc live */
      ui.toast(t('gpa.deleted',{subject:nm}));
    }
  };
  if(row){ row.classList.add('gpa-leave'); setTimeout(go,200); } /* quick slide-away, then remove */
  else go();
}

/* Delegated clicks (card buttons survive home re-renders). */
document.addEventListener('click',function(e){
  const add=e.target.closest('[data-gpa-add]');
  if(add){ courseSheet(null); return; }
  const more=e.target.closest('[data-gpa-more]');
  if(more){ moreSheet(more.dataset.gpaMore); return; }
  const edt=e.target.closest('[data-gpa-edit]');
  if(edt){ closeOpenSwipes(); courseSheet(edt.dataset.gpaEdit); return; }
  const del=e.target.closest('[data-gpa-del]');
  if(del){ delCourse(del.dataset.gpaDel); return; }
  const clr=e.target.closest('[data-gpa-clear]');
  if(clr){ clearSheet(); return; }
});

HUB.gpa={cardHTML:cardHTML,calc:calc,courses:courses,addSheet:addSheet,courseSheet:courseSheet,delCourse:delCourse};
})();
