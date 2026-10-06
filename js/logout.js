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
     cycle with zero CSS changes. Female read: LONG flowing hair with full
     crown coverage (no baldness), volt hair clip, feminine face (soft tapered
     jaw, eyelashes, fuller lips, blush), fitted maroon DRESS (bodice + flared
     skirt, rose theme — never purple), slim skin-tone legs below the hem;
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
    +'<linearGradient id="wxwDress" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#2c1219"/><stop offset="45%" stop-color="#6b2237"/>'
    +'<stop offset="100%" stop-color="#3d1a24"/></linearGradient>'
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

  /* ---- FAR LEG (behind): hip (22,52) -> knee (21,70) -> ankle (21,86).
        Slim skin-tone leg; thigh hides under the dress skirt. ---- */
  s+='<g transform="translate(22,52)"><g class="wx-thighF">'
    +'<line x1="0" y1="0" x2="-1" y2="18" stroke="url(#wxwSkin)" stroke-width="6" stroke-linecap="round"/>'
    +'<g transform="translate(-1,18)"><g class="wx-shinF">'
    +'<line x1="0" y1="0" x2="0" y2="16" stroke="url(#wxwSkin)" stroke-width="4.5" stroke-linecap="round"/>'
    +shoe('wx-footF',0,16)
    +'</g></g></g></g>';

  /* ---- FAR ARM (behind): shoulder (21,30) -> elbow (19,44) -> hand (18,56).
        Short maroon sleeve, skin forearm. ---- */
  s+='<g transform="translate(21,30)"><g class="wx-uarmF">'
    +'<line x1="0" y1="0" x2="-2" y2="14" stroke="url(#wxwDress)" stroke-width="5.5" stroke-linecap="round"/>'
    +'<g transform="translate(-2,14)"><g class="wx-farmF">'
    +'<line x1="0" y1="0" x2="-1" y2="12" stroke="url(#wxwSkin)" stroke-width="4" stroke-linecap="round"/>'
    +'<circle cx="-1" cy="13" r="2.8" fill="url(#wxwSkin)"/>'
    +'</g></g></g></g>';

  /* ---- NEAR LEG: hip (26,52) -> knee (27,70) -> ankle (27,86). ---- */
  s+='<g transform="translate(26,52)"><g class="wx-thighN">'
    +'<line x1="0" y1="0" x2="1" y2="18" stroke="url(#wxwSkin)" stroke-width="6" stroke-linecap="round"/>'
    +'<g transform="translate(1,18)"><g class="wx-shinN">'
    +'<line x1="0" y1="0" x2="0" y2="16" stroke="url(#wxwSkin)" stroke-width="4.5" stroke-linecap="round"/>'
    +shoe('wx-footN',0,16)
    +'</g></g></g></g>';

  /* ---- BACK HAIR MASS (behind torso & backpack): long hair flowing down
        her back. Drawn before the pack so straps sit over the hair. ---- */
  s+='<path d="M27,3 Q17,2 11.5,9 Q6,17 5,29 Q4.5,40 8,47.5 Q11,49.5 13.5,45.5 Q10.5,37 12.5,27 Q14.5,17 21,10 Q25,6.5 27,5 Z" fill="url(#wxwHair)"/>'
    +'<path d="M20,9 Q14,15 12,27 Q11,37 13,44" stroke="#0f0b07" stroke-width="1" fill="none" opacity=".45"/>'
    +'<ellipse cx="10" cy="22" rx="1.8" ry="7" fill="#fff" opacity=".08" transform="rotate(10 10 22)"/>';

  /* ---- BACKPACK (on her back, over the hair) ---- */
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

  /* ---- DRESS SKIRT (flared A-line): waist y~49 to hem y~66.
        Static piece drawn OVER both thighs — thighs swing beneath it,
        shins emerge below the hem. ---- */
  s+='<g>'
    +'<path d="M19.5,48.5 Q24,50.5 28.5,48.5 L35.5,65 Q24,69.5 12.5,65 Z" fill="url(#wxwDress)"/>'
    +'<path d="M19.5,48.5 Q24,50.5 28.5,48.5" stroke="#1c0d12" stroke-width="1.4" fill="none"/>'
    +'<path d="M22,52.5 Q21.2,58.5 20.2,63.5" stroke="#1c0d12" stroke-width="1" fill="none" opacity=".5"/>'
    +'<path d="M26,52.5 Q26.4,58.5 27,64" stroke="#1c0d12" stroke-width="1" fill="none" opacity=".5"/>'
    +'<path d="M14.5,63.2 Q24,67 33.8,63.2" stroke="#a05a6c" stroke-width="1.2" fill="none" opacity=".55"/>'
    +'<ellipse cx="17.5" cy="57" rx="2.4" ry="5" fill="#fff" opacity=".07" transform="rotate(10 17.5 57)"/>'
    +'</g>';

  /* ---- BODICE (fitted dress top, slight forward lean like his) ---- */
  s+='<g transform="rotate(3 24 40)">'
    +'<path d="M18.5,27 Q24,23.8 29.5,27 L28.5,49 Q24,51 19.5,49 Z" fill="url(#wxwDress)"/>'
    +'<path d="M21.5,28.5 Q24,30.5 26.5,28.5" stroke="#1c0d12" stroke-width="1.2" fill="none" opacity=".8"/>'
    +'<ellipse cx="27.5" cy="34" rx="1.4" ry="5" fill="#fff" opacity=".08"/>'
    +'</g>';

  /* ---- NECK ---- */
  s+='<rect x="22.8" y="18" width="4.6" height="10" rx="2" fill="url(#wxwSkin)"/>';

  /* ---- HEAD: feminine — softer tapered jaw, narrower chin.
        (Neck drawn first; head overlaps it. Hair cap below covers the crown
        fully — no skin shows on top.) ---- */
  s+='<path d="M18.3,10 Q18.8,5 25,4.4 Q31.2,5 32.2,10.5 Q32.4,14.5 30.8,17.8 Q29.4,20.6 27.2,21.6 Q25.4,22.3 23.6,21.6 Q21.4,20.6 20.2,17.8 Q18.6,14.5 18.3,10 Z" fill="url(#wxwSkin)"/>'
    +'<circle cx="29.3" cy="13.6" r="1.15" fill="#2b2118"/>'
    +'<path d="M30,12.4 L31.6,11.2" stroke="#2b2118" stroke-width="0.9" stroke-linecap="round"/>'
    +'<path d="M30.6,12.9 L32.3,12" stroke="#2b2118" stroke-width="0.9" stroke-linecap="round"/>'
    +'<path d="M27.3,11.3 Q29.3,10.3 31.4,11.4" stroke="#4a3220" stroke-width="1" fill="none" stroke-linecap="round"/>'
    +'<circle cx="30.8" cy="16.2" r="1.3" fill="#e8907a" opacity=".5"/>'
    +'<path d="M28.6,18.4 Q29.5,17.8 30.3,18.3 Q31.1,17.8 31.9,18.4 Q31.1,19 30.3,18.9 Q29.5,19 28.6,18.4 Z" fill="#b34a5e"/>'
    +'<path d="M29.1,19.1 Q30.3,20 31.5,19.1 Q30.3,19.5 29.1,19.1 Z" fill="#d4707f"/>'
    +'<ellipse cx="26.5" cy="14.8" rx="2" ry="1.2" fill="#fff" opacity=".10"/>';

  /* ---- HAIR CAP: fully opaque over the crown — NO baldness.
        Covers the entire top of the head; front hairline scallops sit
        above the brow. Merges into the back mass on the left. ---- */
  s+='<path d="M15.5,14.5 Q14,5 23,3 Q32,2.5 34,10.5 Q34.2,13 33.2,15.5 L32,15.5 Q32.5,12.5 31.5,11 Q30,10 28.6,11 Q27,10 25.5,11 Q23,10.2 21,11.2 Q18.5,11.5 17,13.5 Q16,14.2 15.5,14.5 Z" fill="url(#wxwHair)"/>'
    +'<path d="M32.6,10.5 Q33.4,15 32.4,20 Q31.8,22.5 30.7,21.8 Q31.9,17 31.9,13 Z" fill="url(#wxwHair)"/>'
    +'<ellipse cx="22" cy="6" rx="5" ry="2.2" fill="#fff" opacity=".12" transform="rotate(-15 22 6)"/>'
    +'<rect x="15.5" y="8.5" width="5" height="2.8" rx="1.4" fill="#c6f135" transform="rotate(-18 18 10)"/>';

  /* ---- NEAR ARM: shoulder (29,30) -> elbow (31,44) -> hand (32,56). ---- */
  s+='<g transform="translate(29,30)"><g class="wx-uarmN">'
    +'<line x1="0" y1="0" x2="2" y2="14" stroke="url(#wxwDress)" stroke-width="5.5" stroke-linecap="round"/>'
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
