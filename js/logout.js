/* HUB logout farewell: everything happens inside the top bar.
   The 6th appbar control is a little 3D door with "Logout" written on it.
   On click, a compact stage opens in the top bar (no fullscreen, no new page):
   a 3D wax-style character with a backpack WALKS in along the bar with a
   proper walk cycle (feet plant on the ground, knees bend, arms counter-swing),
   the door swings open on a real 3D hinge with warm light, he walks into the
   light and dissolves, the door shuts behind him — then the real sign-out
   runs and the login page opens.
   - Review-only safe: never touches session until the timeline finishes.
   - Tap the stage to skip. Honors prefers-reduced-motion (skips instantly).
   - All motion is transform/opacity-only (iOS-safe), matching auth.js rules. */
(function(){
'use strict';
var STRIP_ID='loStrip';
var DURATION=2000; /* ms — matches the css/logout.css timeline (door shut ~1.6s) */
var busy=false, timer=null;

function t(k){ try{ return HUB.i18n.t(k); }catch(e){ return 'Log out'; } }
function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }

function manSVG(){
  /* 3D wax-figure walker with backpack, side profile facing the door (right).
     Built like a puppet: every limb is a nested <g> translated to its joint,
     so rotating a thigh swings the shin+foot with it — joints can never
     detach. The walk cycle (css/logout.css) follows real 8-phase gait
     biomechanics: heel-strike -> loading (knee flexes) -> mid-stance ->
     heel-rise -> toe-off -> swing (knee folds, ankle dorsiflexes) ->
     late swing -> heel-strike. Feet articulate at the ankle (toe-up at
     strike, flat, heel-up at push-off). Arms counter-swing the same-side leg.
     Wax look: cylindrical gradients on limbs, spherical shading on the head,
     rim light from the doorway side (right). */
  var s='';
  s+='<svg viewBox="0 0 48 96" aria-hidden="true">';
  s+='<defs>'
    +'<radialGradient id="wxSkin" cx="38%" cy="30%" r="80%">'
    +'<stop offset="0%" stop-color="#f8d9b3"/><stop offset="55%" stop-color="#eec39b"/>'
    +'<stop offset="100%" stop-color="#c99a68"/></radialGradient>'
    +'<linearGradient id="wxHood" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#1c212b"/><stop offset="45%" stop-color="#333b49"/>'
    +'<stop offset="100%" stop-color="#232936"/></linearGradient>'
    +'<linearGradient id="wxPants" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#161b24"/><stop offset="45%" stop-color="#2a3140"/>'
    +'<stop offset="100%" stop-color="#1a1f29"/></linearGradient>'
    +'<linearGradient id="wxPack" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#232a38"/><stop offset="50%" stop-color="#3d4659"/>'
    +'<stop offset="100%" stop-color="#2a3140"/></linearGradient>'
    +'<linearGradient id="wxCap" x1="0" y1="0" x2="0" y2="1">'
    +'<stop offset="0%" stop-color="#2e3542"/><stop offset="100%" stop-color="#141821"/></linearGradient>'
    +'<linearGradient id="wxShoe" x1="0" y1="0" x2="0" y2="1">'
    +'<stop offset="0%" stop-color="#3a4354"/><stop offset="70%" stop-color="#232a38"/>'
    +'<stop offset="100%" stop-color="#141821"/></linearGradient>'
    +'</defs>';

  function shoe(cls,ax,ay){
    /* chunky sneaker, ankle pivot at (ax,ay): heel x=-4, toe x=+11,
       thick light sole so it reads clearly at small size */
    return '<g transform="translate('+ax+','+ay+')"><g class="'+cls+'">'
      +'<path d="M-4,-2 Q-4,-5 -1,-5 L4,-5 Q8,-5 10.5,-2.5 Q11.5,-1 11,1 L10.5,3 Q10,4.5 8,4.5 L-2,4.5 Q-4,4.5 -4,2.5 Z" fill="url(#wxShoe)"/>'
      +'<path d="M6.5,-5 Q9,-5 10.5,-2.5 L8.5,-2 Q7.5,-3.8 5.5,-4 Z" fill="#0e1218" opacity=".55"/>'
      +'<rect x="-4" y="2.8" width="15" height="2.6" rx="1.3" fill="#eef1f6"/>'
      +'<rect x="-4" y="4.4" width="15" height="1" rx=".5" fill="#b9c1cf"/>'
      +'</g></g>';
  }

  /* ---- FAR LEG (darker, behind): hip (22,52) -> knee (21,70) -> ankle (21,86) ---- */
  s+='<g transform="translate(22,52)"><g class="wx-thighF">'
    +'<line x1="0" y1="0" x2="-1" y2="18" stroke="url(#wxPants)" stroke-width="7" stroke-linecap="round"/>'
    +'<g transform="translate(-1,18)"><g class="wx-shinF">'
    +'<line x1="0" y1="0" x2="0" y2="16" stroke="url(#wxPants)" stroke-width="5.5" stroke-linecap="round"/>'
    +shoe('wx-footF',0,16)
    +'</g></g></g></g>';

  /* ---- FAR ARM (behind): shoulder (21,30) -> elbow (19,44) -> hand (18,56) ---- */
  s+='<g transform="translate(21,30)"><g class="wx-uarmF">'
    +'<line x1="0" y1="0" x2="-2" y2="14" stroke="url(#wxHood)" stroke-width="6" stroke-linecap="round"/>'
    +'<g transform="translate(-2,14)"><g class="wx-farmF">'
    +'<line x1="0" y1="0" x2="-1" y2="12" stroke="url(#wxSkin)" stroke-width="4.5" stroke-linecap="round"/>'
    +'<circle cx="-1" cy="13" r="3" fill="url(#wxSkin)"/>'
    +'</g></g></g></g>';

  /* ---- BACKPACK (on his back, left side) ---- */
  s+='<g>'
    +'<rect x="7" y="28" width="13" height="24" rx="6.5" fill="url(#wxPack)"/>'
    +'<rect x="7" y="28" width="13" height="24" rx="6.5" fill="none" stroke="#12161d" stroke-width="1" opacity=".6"/>'
    +'<rect x="9.5" y="39" width="8" height="10" rx="3.5" fill="#1b2130"/>'
    +'<line x1="13.5" y1="39" x2="13.5" y2="49" stroke="#c6f135" stroke-width="1.6"/>'
    +'<circle cx="13.5" cy="41" r="1.1" fill="#c6f135"/>'
    +'<path d="M17,30 Q21,27 24,31" stroke="#1a1f29" stroke-width="3.2" fill="none" stroke-linecap="round"/>'
    +'<path d="M17,34 Q20,32 22,35" stroke="#1a1f29" stroke-width="2.4" fill="none" stroke-linecap="round" opacity=".7"/>'
    +'<ellipse cx="11" cy="33" rx="2.2" ry="4" fill="#fff" opacity=".10"/>'
    +'</g>';

  /* ---- TORSO (hoodie, slight forward lean) ---- */
  s+='<g transform="rotate(3 24 40)">'
    +'<path d="M17,27 Q24,23.5 31,27 L29.5,52 Q24,54.5 18.5,52 Z" fill="url(#wxHood)"/>'
    +'<line x1="24.5" y1="27" x2="24.5" y2="52" stroke="#c6f135" stroke-width="1.8"/>'
    +'<path d="M20,28 Q24,26 28,28" stroke="#12161d" stroke-width="1.4" fill="none" opacity=".7"/>'
    +'<ellipse cx="28.5" cy="34" rx="1.6" ry="6" fill="#fff" opacity=".08"/>'
    +'</g>';

  /* ---- HEAD + CAP ---- */
  s+='<circle cx="25" cy="14" r="8" fill="url(#wxSkin)"/>'
    +'<path d="M17.5,13 Q18,5 25,4.5 Q32,5 32.5,13 Q32.5,10.5 25,10 Q17.5,10.5 17.5,13 Z" fill="url(#wxCap)"/>'
    +'<ellipse cx="25" cy="6.5" rx="7.5" ry="2.6" fill="url(#wxCap)"/>'
    +'<ellipse cx="37" cy="11.5" rx="6.5" ry="2.2" fill="url(#wxCap)"/>'
    +'<circle cx="25" cy="3.8" r="1.4" fill="#c6f135"/>'
    +'<circle cx="29.5" cy="14" r="1.1" fill="#2b2118"/>'
    +'<path d="M30,18.5 Q31.5,19.5 33,18.5" stroke="#b3855a" stroke-width="1" fill="none" stroke-linecap="round"/>';

  /* ---- NEAR LEG: hip (26,52) -> knee (27,70) -> ankle (27,86) ---- */
  s+='<g transform="translate(26,52)"><g class="wx-thighN">'
    +'<line x1="0" y1="0" x2="1" y2="18" stroke="url(#wxPants)" stroke-width="7" stroke-linecap="round"/>'
    +'<g transform="translate(1,18)"><g class="wx-shinN">'
    +'<line x1="0" y1="0" x2="0" y2="16" stroke="url(#wxPants)" stroke-width="5.5" stroke-linecap="round"/>'
    +shoe('wx-footN',0,16)
    +'</g></g></g></g>';

  /* ---- NEAR ARM: shoulder (29,30) -> elbow (31,44) -> hand (32,56) ---- */
  s+='<g transform="translate(29,30)"><g class="wx-uarmN">'
    +'<line x1="0" y1="0" x2="2" y2="14" stroke="url(#wxHood)" stroke-width="6" stroke-linecap="round"/>'
    +'<g transform="translate(2,14)"><g class="wx-farmN">'
    +'<line x1="0" y1="0" x2="1" y2="12" stroke="url(#wxSkin)" stroke-width="4.5" stroke-linecap="round"/>'
    +'<circle cx="1" cy="13" r="3.2" fill="url(#wxSkin)"/>'
    +'</g></g></g></g>';

  /* rim light from the doorway (right side) */
  s+='<line x1="32.5" y1="30" x2="31" y2="50" stroke="#ffedbe" stroke-width="1" opacity=".35" stroke-linecap="round"/>';

  return s+'</svg>';
}

function womanSVG(){
  /* 3D wax-figure walker — FEMALE variant with backpack, side profile facing
     the door (right). Puppet hierarchy, joint pivots and CSS class names are
     IDENTICAL to manSVG() so css/logout.css drives the same 8-phase walk
     cycle with zero CSS changes. Female read: long ponytail with volt tie,
     narrower shoulders, fitted maroon jacket (rose theme), slimmer limbs;
     same wax materials, same backpack, same rim light from the doorway. */
  var s='';
  s+='<svg viewBox="0 0 48 96" aria-hidden="true">';
  s+='<defs>'
    +'<radialGradient id="wxwSkin" cx="38%" cy="30%" r="80%">'
    +'<stop offset="0%" stop-color="#f8d9b3"/><stop offset="55%" stop-color="#eec39b"/>'
    +'<stop offset="100%" stop-color="#c99a68"/></radialGradient>'
    +'<linearGradient id="wxwHair" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#1d140d"/><stop offset="45%" stop-color="#4a3421"/>'
    +'<stop offset="100%" stop-color="#241a10"/></linearGradient>'
    +'<linearGradient id="wxwTop" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#2c161d"/><stop offset="45%" stop-color="#572b37"/>'
    +'<stop offset="100%" stop-color="#331a21"/></linearGradient>'
    +'<linearGradient id="wxwPants" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#161b24"/><stop offset="45%" stop-color="#2a3140"/>'
    +'<stop offset="100%" stop-color="#1a1f29"/></linearGradient>'
    +'<linearGradient id="wxwPack" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#232a38"/><stop offset="50%" stop-color="#3d4659"/>'
    +'<stop offset="100%" stop-color="#2a3140"/></linearGradient>'
    +'<linearGradient id="wxwShoe" x1="0" y1="0" x2="0" y2="1">'
    +'<stop offset="0%" stop-color="#3a4354"/><stop offset="70%" stop-color="#232a38"/>'
    +'<stop offset="100%" stop-color="#141821"/></linearGradient>'
    +'</defs>';

  function shoe(cls,ax,ay){
    /* chunky sneaker, ankle pivot at (ax,ay) — same geometry as man's shoe */
    return '<g transform="translate('+ax+','+ay+')"><g class="'+cls+'">'
      +'<path d="M-4,-2 Q-4,-5 -1,-5 L4,-5 Q8,-5 10.5,-2.5 Q11.5,-1 11,1 L10.5,3 Q10,4.5 8,4.5 L-2,4.5 Q-4,4.5 -4,2.5 Z" fill="url(#wxwShoe)"/>'
      +'<path d="M6.5,-5 Q9,-5 10.5,-2.5 L8.5,-2 Q7.5,-3.8 5.5,-4 Z" fill="#0e1218" opacity=".55"/>'
      +'<rect x="-4" y="2.8" width="15" height="2.6" rx="1.3" fill="#eef1f6"/>'
      +'<rect x="-4" y="4.4" width="15" height="1" rx=".5" fill="#b9c1cf"/>'
      +'</g></g>';
  }

  /* ---- FAR LEG (darker, behind): hip (22,52) -> knee (21,70) -> ankle (21,86) ---- */
  s+='<g transform="translate(22,52)"><g class="wx-thighF">'
    +'<line x1="0" y1="0" x2="-1" y2="18" stroke="url(#wxwPants)" stroke-width="6.5" stroke-linecap="round"/>'
    +'<g transform="translate(-1,18)"><g class="wx-shinF">'
    +'<line x1="0" y1="0" x2="0" y2="16" stroke="url(#wxwPants)" stroke-width="5" stroke-linecap="round"/>'
    +shoe('wx-footF',0,16)
    +'</g></g></g></g>';

  /* ---- FAR ARM (behind): shoulder (21,30) -> elbow (19,44) -> hand (18,56) ---- */
  s+='<g transform="translate(21,30)"><g class="wx-uarmF">'
    +'<line x1="0" y1="0" x2="-2" y2="14" stroke="url(#wxwTop)" stroke-width="5.5" stroke-linecap="round"/>'
    +'<g transform="translate(-2,14)"><g class="wx-farmF">'
    +'<line x1="0" y1="0" x2="-1" y2="12" stroke="url(#wxwSkin)" stroke-width="4" stroke-linecap="round"/>'
    +'<circle cx="-1" cy="13" r="2.8" fill="url(#wxwSkin)"/>'
    +'</g></g></g></g>';

  /* ---- BACKPACK (on her back, left side) ---- */
  s+='<g>'
    +'<rect x="7" y="28" width="13" height="24" rx="6.5" fill="url(#wxwPack)"/>'
    +'<rect x="7" y="28" width="13" height="24" rx="6.5" fill="none" stroke="#12161d" stroke-width="1" opacity=".6"/>'
    +'<rect x="9.5" y="39" width="8" height="10" rx="3.5" fill="#1b2130"/>'
    +'<line x1="13.5" y1="39" x2="13.5" y2="49" stroke="#c6f135" stroke-width="1.6"/>'
    +'<circle cx="13.5" cy="41" r="1.1" fill="#c6f135"/>'
    +'<path d="M17,30 Q21,27 24,31" stroke="#1a1f29" stroke-width="3.2" fill="none" stroke-linecap="round"/>'
    +'<path d="M17,34 Q20,32 22,35" stroke="#1a1f29" stroke-width="2.4" fill="none" stroke-linecap="round" opacity=".7"/>'
    +'<ellipse cx="11" cy="33" rx="2.2" ry="4" fill="#fff" opacity=".10"/>'
    +'</g>';

  /* ---- TORSO (fitted jacket, narrower shoulders, slight forward lean) ---- */
  s+='<g transform="rotate(3 24 40)">'
    +'<path d="M18.5,27 Q24,23.8 29.5,27 L28.5,52 Q24,54.2 19.5,52 Z" fill="url(#wxwTop)"/>'
    +'<line x1="24" y1="27" x2="24" y2="52" stroke="#c6f135" stroke-width="1.6"/>'
    +'<path d="M21,28 Q24,26.5 27,28" stroke="#0f0a0c" stroke-width="1.2" fill="none" opacity=".7"/>'
    +'<ellipse cx="27.5" cy="34" rx="1.4" ry="5" fill="#fff" opacity=".08"/>'
    +'</g>';

  /* ---- HAIR: back mass + ponytail flowing left, volt tie ---- */
  s+='<ellipse cx="16.5" cy="17" rx="7" ry="13" fill="url(#wxwHair)" transform="rotate(12 16.5 17)"/>'
    +'<path d="M13,11 Q8,19 4.5,29 Q3.5,32 6,31.5 Q10.5,25.5 14.5,15 Z" fill="url(#wxwHair)"/>'
    +'<rect x="10.5" y="11.5" width="4.5" height="3.2" rx="1.6" fill="#c6f135" transform="rotate(-28 12.7 13.1)"/>'
    +'<ellipse cx="12" cy="20" rx="1.6" ry="5" fill="#fff" opacity=".10" transform="rotate(18 12 20)"/>';

  /* ---- HEAD ---- */
  s+='<circle cx="25" cy="14" r="8" fill="url(#wxwSkin)"/>'
    +'<path d="M17,13 Q17.5,5 25,4 Q32.5,5 33,13 Q31,8.8 25,8.3 Q19,8.8 17,13 Z" fill="url(#wxwHair)"/>'
    +'<ellipse cx="21.5" cy="6.8" rx="3.6" ry="1.4" fill="#fff" opacity=".12" transform="rotate(-16 21.5 6.8)"/>'
    +'<circle cx="29.5" cy="14" r="1.1" fill="#2b2118"/>'
    +'<circle cx="31.6" cy="16.6" r="1.2" fill="#e8907a" opacity=".45"/>'
    +'<path d="M30,18.5 Q31.5,19.5 33,18.5" stroke="#b3855a" stroke-width="1" fill="none" stroke-linecap="round"/>';

  /* ---- NEAR LEG: hip (26,52) -> knee (27,70) -> ankle (27,86) ---- */
  s+='<g transform="translate(26,52)"><g class="wx-thighN">'
    +'<line x1="0" y1="0" x2="1" y2="18" stroke="url(#wxwPants)" stroke-width="6.5" stroke-linecap="round"/>'
    +'<g transform="translate(1,18)"><g class="wx-shinN">'
    +'<line x1="0" y1="0" x2="0" y2="16" stroke="url(#wxwPants)" stroke-width="5" stroke-linecap="round"/>'
    +shoe('wx-footN',0,16)
    +'</g></g></g></g>';

  /* ---- NEAR ARM: shoulder (29,30) -> elbow (31,44) -> hand (32,56) ---- */
  s+='<g transform="translate(29,30)"><g class="wx-uarmN">'
    +'<line x1="0" y1="0" x2="2" y2="14" stroke="url(#wxwTop)" stroke-width="5.5" stroke-linecap="round"/>'
    +'<g transform="translate(2,14)"><g class="wx-farmN">'
    +'<line x1="0" y1="0" x2="1" y2="12" stroke="url(#wxwSkin)" stroke-width="4" stroke-linecap="round"/>'
    +'<circle cx="1" cy="13" r="3" fill="url(#wxwSkin)"/>'
    +'</g></g></g></g>';

  /* rim light from the doorway (right side) */
  s+='<line x1="32.5" y1="30" x2="31" y2="50" stroke="#ffedbe" stroke-width="1" opacity=".35" stroke-linecap="round"/>';

  return s+'</svg>';
}

function pickWalkerSVG(){
  /* Female profile -> womanSVG(); anything else (male/other/unset) -> manSVG(). */
  var g='';
  try{ g=String((HUB.store&&HUB.store.state&&HUB.store.state.profile&&HUB.store.state.profile.gender)||'').toLowerCase(); }catch(e){}
  return g==='female'?womanSVG():manSVG();
}

function buildStrip(){
  var bar=document.querySelector('.appbar');
  if(!bar) return false;
  var s=document.createElement('div');
  s.className='lo-strip'; s.id=STRIP_ID;
  s.setAttribute('role','alert');
  s.setAttribute('aria-label',esc(t('auth.logout')));
  s.innerHTML='<div class="lo-track">'
    +'<div class="lo-doorway"><div class="lo-glow"></div><div class="lo-frame"></div>'
    +'<div class="lo-door"><span class="lo-door-label">'+esc(t('auth.logout'))+'</span></div></div>'
    +'<div class="lo-manshadow"></div>'
    +'<div class="lo-man">'+pickWalkerSVG()+'</div>'
    +'</div>';
  s.addEventListener('click',function(){ finish(); });
  bar.appendChild(s);
  return true;
}

function doSignOut(){
  try{ HUB.auth._doSignOut(); }catch(e){}
}

function finish(){
  if(timer){ clearTimeout(timer); timer=null; }
  var s=document.getElementById(STRIP_ID);
  if(s&&s.parentNode) s.parentNode.removeChild(s);
  busy=false;
  doSignOut();
}

function play(){
  if(busy) return;
  var loggedIn=false;
  try{ loggedIn=!!(HUB.auth&&HUB.auth.currentUser&&HUB.auth.currentUser()); }catch(e){}
  if(!loggedIn){ try{ HUB.auth.openLogin(); }catch(e){} return; }
  var reduce=false;
  try{ reduce=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches); }catch(e){}
  if(reduce){ doSignOut(); return; }
  busy=true;
  if(!buildStrip()){ busy=false; doSignOut(); return; }
  timer=setTimeout(finish,DURATION);
}

HUB.logout=HUB.logout||{};
HUB.logout.play=play;
HUB.logout._finish=finish; /* QA hook: run the real end-of-timeline path on demand */
})();
