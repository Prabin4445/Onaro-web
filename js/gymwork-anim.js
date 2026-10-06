/* HUB.gymworkAnim — video-based exercise demos.
   Each exercise plays a short AI-generated video of a real human performing
   the lift with textbook form (videos/gym/<id>.mp4, poster <id>-poster.jpg).
   Public API is unchanged: EXERCISES, render(container, id, {mode}),
   destroy(container), _register(id, def).
   (private QA: window.__GWA_QA=true before load attaches _pose(container,frac).) */
(function(){
'use strict';

var EXERCISES = ['bench-press','overhead-press','incline-db-press','lateral-raise',
  'tricep-pushdown','dips','push-up','deadlift','pull-up','barbell-row','lat-pulldown',
  'face-pull','barbell-curl','hammer-curl','back-squat','romanian-deadlift',
  'leg-press','lying-leg-curl','calf-raise','walking-lunge','goblet-squat',
  'warmup-jumping-jacks','warmup-leg-swings',
  'warmup-bodyweight-squat','warmup-high-knees',
  'abs-crunch','abs-plank','abs-leg-raise','abs-bicycle','abs-mountain-climber',
  'abs-russian-twist','abs-dead-bug',
  'pilates-hundred','pilates-roll-up','pilates-single-leg-stretch',
  'pilates-glute-bridge','pilates-side-leg-lift','pilates-bird-dog',
  'zumba-salsa-basic','zumba-merengue','zumba-cumbia','zumba-reggaeton',
  'zumba-cooldown',
  'db-floor-press',
  'machine-chest-press',
  'db-shoulder-press',
  'bench-dips',
  'pec-deck',
  'pike-push-up',
  'cable-crossover',
  'close-grip-bench-press',
  'seated-cable-row',
  'db-single-arm-row',
  'assisted-pull-up',
  'preacher-curl',
  'db-shrugs',
  'straight-arm-pulldown',
  'concentration-curl',
  'reverse-curl',
  'leg-extension',
  'step-up',
  'hip-thrust',
  'bulgarian-split-squat',
  'seated-calf-raise',
  'sumo-deadlift',
  'glute-kickback',
  'hip-abduction-machine',
  'torso-twists',
  'hip-circles',
  'shoulder-rolls',
  'inchworm',
  'cat-cow',
  'glute-bridge',
  'reverse-crunch',
  'flutter-kicks',
  'heel-taps',
  'plank-shoulder-taps',
  'side-plank',
  'hollow-hold',
  'ab-wheel-rollout',
  'leg-circles',
  'double-leg-stretch',
  'spine-twist',
  'swan-prep',
  'mermaid-stretch',
  'teaser-prep',
  'bachata-basic',
  'samba-step',
  'hiphop-groove',
  'soca-bounce',
  'belly-shimmy',
  'neck-stretch',
  'cross-shoulder-stretch',
  'overhead-tricep-stretch',
  'standing-quad-stretch',
  'hamstring-fold',
  'hip-flexor-stretch',
  'childs-pose',
  'cobra-stretch'];

var BASE = 'videos/gym/';
var REDUCED = false;
try{ REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }catch(e){}

function urls(id){
  return { mp4: BASE+id+'.mp4', poster: BASE+id+'-poster.jpg' };
}
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;'); }

function posterIMG(u){
  return '<img src="'+esc(u.poster)+'" alt="" loading="lazy" decoding="async" '+
    'style="width:100%;height:100%;object-fit:cover;display:block" draggable="false">';
}

/* ================= render / destroy ================= */
function render(container, exerciseId, opts){
  var el = (typeof container==='string') ? document.querySelector(container) : container;
  if(!el) return;
  destroy(el);
  opts = opts || {};
  var mode = opts.mode || 'full';
  var u = urls(exerciseId);

  /* thumbnails and reduced-motion: static poster frame only */
  if(mode==='thumb' || REDUCED){
    el.innerHTML = posterIMG(u);
    el._gwa = { mode:'img' };
    return;
  }

  var v = document.createElement('video');
  v.muted = true;
  v.loop = true;
  v.playsInline = true;
  v.preload = 'none';
  v.poster = u.poster;
  v.src = u.mp4;
  v.setAttribute('aria-hidden','true');
  v.setAttribute('disablepictureinpicture','');
  v.style.cssText = 'width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;'+
    'display:block;border-radius:12px;background:#0b0d10';
  /* if the video file fails, fall back to the poster frame */
  v.addEventListener('error', function(){
    if(el._gwa && el._gwa.mode==='video'){ el.innerHTML = posterIMG(u); el._gwa = {mode:'img'}; }
  });
  el.appendChild(v);

  var st = { mode:'video', v:v, io:null };
  el._gwa = st;

  function play(){
    try{ var p = v.play(); if(p && p.catch) p.catch(function(){}); }catch(e){}
  }
  if('IntersectionObserver' in window){
    st.io = new IntersectionObserver(function(entries){
      if(!el._gwa || el._gwa!==st) return;
      if(entries[0] && entries[0].isIntersecting) play(); else v.pause();
    }, { threshold: 0.15 });
    st.io.observe(el);
  }else{
    play();
  }
}

function destroy(container){
  var el = (typeof container==='string') ? document.querySelector(container) : container;
  if(!el || !el._gwa) return;
  var st = el._gwa;
  if(st.io){ try{ st.io.disconnect(); }catch(e){} }
  if(st.v){ try{ st.v.pause(); st.v.removeAttribute('src'); st.v.load(); }catch(e){} }
  el.innerHTML = '';
  delete el._gwa;
}

/* QA helper: freeze a static frame at frac (0..1) of the clip. */
function _pose(container, frac){
  var el = (typeof container==='string') ? document.querySelector(container) : container;
  if(!el || !el._gwa || !el._gwa.v) return;
  var v = el._gwa.v;
  if(el._gwa.io){ try{ el._gwa.io.disconnect(); }catch(e){} el._gwa.io = null; }
  v.pause();
  function seek(){
    try{
      if(v.duration && isFinite(v.duration)) v.currentTime = Math.min(Math.max(frac||0,0),1)*v.duration;
    }catch(e){}
  }
  if(v.readyState >= 1){ v.preload='auto'; seek(); }
  else{
    v.preload = 'auto';
    v.addEventListener('loadedmetadata', seek, { once:true });
    try{ v.load(); }catch(e){}
  }
}

/* ================= registration & public API ================= */
function _register(id, def){ /* kept for API compatibility; videos need no pose defs */ }

window.HUB = window.HUB || {};
HUB.gymworkAnim = {
  EXERCISES: EXERCISES,
  render: render,
  destroy: destroy,
  _register: _register
};
/* private QA hook: deterministic static frames. Only attached when the page
   opts in BEFORE this script loads (window.__GWA_QA=true). */
if(window.__GWA_QA === true) HUB.gymworkAnim._pose = _pose;

})();
