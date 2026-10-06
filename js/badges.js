/* HUB profile badges: gaming-style tier badges, Onaro-branded.
   Tier is earned by QUALIFYING LOGIN DAYS (one per calendar day, only after
   60s of foreground presence) — never calendar months. SPECIALIST stacks on
   top at 100+ professor reviews/ratings/comments authored in the app.
   All art is hand-built inline SVG (crisp at 24px and 120px, zero purple):
   metallic bevels, layered gradients, gloss highlights, feathered wings,
   and a looping shine sweep (.bdg-shineg, CSS-driven so prefers-reduced-motion
   can freeze it). Earn moment = celebratory showcase sheet + reason why +
   what's-next card + notification-center entry + toast.
   Counts are device-local (hub_v1); real cross-device badges arrive with the
   production backend. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/* ---- tier ladder ---- */
var TIERS=[
  {id:'new', days:0},
  {id:'silver', days:90},
  {id:'gold', days:180},
  {id:'legend', days:365}
];
var RANK={new:0,silver:1,gold:2,legend:3};
var SPEC_GOAL=100; /* legacy review-count goal; kept for other-people demo display only */
/* ---- reviewer points: the road to SPECIALIST ----
   Writing a review earns PTS_REVIEW, adding a missing professor earns
   PTS_ADDPROF, and the SPECIALIST badge unlocks at PTS_GOAL. Points are
   seeded from existing reviews on first run so nobody loses progress. */
var PTS_GOAL=1000, PTS_REVIEW=10, PTS_ADDPROF=25;
var uidN=0;

function prof(){
  const st=HUB.store.state;
  if(!st.profile||typeof st.profile!=='object') st.profile={};
  return st.profile;
}
function tierOf(days){ const d=Number(days)||0; if(d>=365) return 'legend'; if(d>=180) return 'gold'; if(d>=90) return 'silver'; return 'new'; }
function nextTier(id){ const r=RANK[id]; return r>=3?null:TIERS[r+1].id; }

/* ---- professor contributions: reviews authored by this device ---- */
var dbgReviewCount=null; /* QA override; never user-visible */
function myReviewCount(){
  if(dbgReviewCount!=null) return dbgReviewCount;
  try{
    const p=prof(), aid=p.aid, nm=String(p.name||'').trim().toLowerCase();
    const pr=(HUB.store.state.prof&&HUB.store.state.prof.reviews)||{};
    let n=0;
    Object.keys(pr).forEach(function(pid){
      (pr[pid]||[]).forEach(function(r){
        if(r.authorId&&aid){ if(r.authorId===aid) n++; }
        else if(nm&&String(r.author||'').trim().toLowerCase()===nm) n++;
      });
    });
    return n;
  }catch(e){ return 0; }
}
function isSpecialist(){ return myPoints()>=PTS_GOAL; }
/* Reviewer points for the signed-in device. Seeded once from the reviews
   already written so the move from review-count to points loses nothing. */
function myPoints(){
  const p=prof();
  if(p.reviewPts==null||!isFinite(Number(p.reviewPts))){
    p.reviewPts=myReviewCount()*PTS_REVIEW;
    try{ HUB.store.save(); }catch(e){}
  }
  return Math.max(0,Math.floor(Number(p.reviewPts)||0));
}
function addPoints(n){
  const p=prof(), cur=myPoints();
  p.reviewPts=cur+Math.max(0,Math.floor(Number(n)||0));
  try{ HUB.store.save(); }catch(e){}
  return p.reviewPts;
}

/* ================= BADGE ART (inline SVG, viewBox 120) ================= */
function star5(cx,cy,R,r,fill,extra){
  const pts=[];
  for(let i=0;i<10;i++){
    const rad=i%2===0?R:r, a=-Math.PI/2+i*Math.PI/5;
    pts.push((cx+rad*Math.cos(a)).toFixed(2)+','+(cy+rad*Math.sin(a)).toFixed(2));
  }
  return '<polygon points="'+pts.join(' ')+'" fill="'+fill+'"'+(extra?' '+extra:'')+'/>';
}
function spark4(cx,cy,s,fill){
  return '<path d="M'+cx+','+(cy-s)+' C'+(cx+s*0.15)+','+(cy-s*0.15)+' '+(cx+s*0.15)+','+(cy-s*0.15)+' '+(cx+s)+','+cy
    +' C'+(cx+s*0.15)+','+(cy+s*0.15)+' '+(cx+s*0.15)+','+(cy+s*0.15)+' '+cx+','+(cy+s)
    +' C'+(cx-s*0.15)+','+(cy+s*0.15)+' '+(cx-s*0.15)+','+(cy+s*0.15)+' '+(cx-s)+','+cy
    +' C'+(cx-s*0.15)+','+(cy-s*0.15)+' '+(cx-s*0.15)+','+(cy-s*0.15)+' '+cx+','+(cy-s)+' Z" fill="'+fill+'"/>';
}
/* diagonal shine streak shared by every badge; the .bdg-shineg group is
   translated across the badge by CSS (bdgshine keyframes) and frozen under
   prefers-reduced-motion. */
function shineDefs(p){
  return '<linearGradient id="'+p+'sh" x1="0" y1="0" x2="1" y2="0">'
    +'<stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>'
    +'<stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.55"/>'
    +'<stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>';
}
function shineG(p,clipId,shape){
  return '<clipPath id="'+p+clipId+'">'+shape+'</clipPath>'
    +'<g class="bdg-shineg" clip-path="url(#'+p+clipId+')">'
    +'<rect x="-70" y="-40" width="46" height="200" fill="url(#'+p+'sh)" transform="skewX(-18)"/></g>';
}

var ART={
new:function(p){
  return '<svg viewBox="0 0 120 120" role="img" aria-hidden="true">'
  +'<defs>'
  +'<radialGradient id="'+p+'nbg" cx="50%" cy="35%" r="80%"><stop offset="0%" stop-color="#2E8B4E"/><stop offset="55%" stop-color="#16482A"/><stop offset="100%" stop-color="#081F12"/></radialGradient>'
  +'<linearGradient id="'+p+'nleaf" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#C4F7D2"/><stop offset="45%" stop-color="#4ADE80"/><stop offset="100%" stop-color="#15803D"/></linearGradient>'
  +'<linearGradient id="'+p+'nring" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#F2FF8A"/><stop offset="35%" stop-color="#C6F135"/><stop offset="60%" stop-color="#7FA321"/><stop offset="100%" stop-color="#D4F75A"/></linearGradient>'
  +'<radialGradient id="'+p+'ngloss" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.5"/><stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
  +shineDefs(p)
  +'</defs>'
  +'<circle cx="60" cy="60" r="56" fill="none" stroke="url(#'+p+'nring)" stroke-width="8"/>'
  +'<path d="M15,34 A52,52 0 0 1 86,15" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" opacity="0.55"/>'
  +'<circle cx="60" cy="60" r="51" fill="url(#'+p+'nbg)"/>'
  +'<ellipse cx="44" cy="34" rx="28" ry="15" fill="url(#'+p+'ngloss)" opacity="0.55"/>'
  +'<ellipse cx="60" cy="93" rx="33" ry="9" fill="#04120A" opacity="0.55"/>'
  +'<ellipse cx="60" cy="90" rx="29" ry="8.5" fill="#0A2E18"/>'
  +'<path d="M33,88 A29,8.5 0 0 1 87,88" fill="none" stroke="#3DDC74" stroke-width="1.6" opacity="0.7"/>'
  +'<path d="M60,90 C60,76 60,68 60,56" stroke="#3DDC74" stroke-width="8" stroke-linecap="round" fill="none"/>'
  +'<path d="M58,88 C58,76 58,68 58,58" stroke="#B9F5C9" stroke-width="2.4" stroke-linecap="round" fill="none" opacity="0.85"/>'
  +'<path d="M60,68 C46,66 36,58 33,44 C48,46 58,56 60,68 Z" fill="url(#'+p+'nleaf)" stroke="#0E5A2E" stroke-width="1.2"/>'
  +'<path d="M60,58 C74,56 84,48 87,34 C72,36 62,46 60,58 Z" fill="url(#'+p+'nleaf)" stroke="#0E5A2E" stroke-width="1.2"/>'
  +'<path d="M59,66 C50,62 43,56 39,49" stroke="#E7FBEF" stroke-width="1.8" fill="none" opacity="0.8"/>'
  +'<path d="M61,56 C70,52 77,46 81,39" stroke="#E7FBEF" stroke-width="1.8" fill="none" opacity="0.8"/>'
  +'<path d="M60,56 C58,49 58,43 61,37" stroke="#D8F9E2" stroke-width="5" stroke-linecap="round" fill="none"/>'
  +spark4(33,30,7,'#C6F135')+'<circle cx="89" cy="82" r="3.2" fill="#C6F135"/><circle cx="30" cy="84" r="2.6" fill="#8FF0A4"/>'
  +shineG(p,'c','<circle cx="60" cy="60" r="56"/>')
  +'</svg>';
},
silver:function(p){
  const sh='M60,12 C76,20 90,24 104,26 L104,58 C104,86 84,101 60,109 C36,101 16,86 16,58 L16,26 C30,24 44,20 60,12 Z';
  const sh2='M60,24 C72,30 82,33 92,35 L92,58 C92,78 78,89 60,96 C42,89 28,78 28,58 L28,35 C38,33 48,30 60,24 Z';
  const WL=['M21,50 C13,46 7,38 5,28 C13,32 19,34 23,36 C19,40 18,45 19,50 Z',
            'M21,60 C14,57 9,51 7,43 C14,46 19,48 23,49 C20,52 19,56 20,60 Z',
            'M23,70 C17,68 12,63 10,56 C16,59 20,60 24,61 C21,64 21,67 22,70 Z'];
  let wings='';
  WL.forEach(function(d){ wings+='<path d="'+d+'" fill="url(#'+p+'ssteel)" stroke="#46536A" stroke-width="1.2"/>'; });
  wings='<g>'+wings+'</g><g transform="translate(120,0) scale(-1,1)">'+wings+'</g>';
  return '<svg viewBox="0 0 120 120" role="img" aria-hidden="true">'
  +'<defs>'
  +'<linearGradient id="'+p+'smet" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#FFFFFF"/><stop offset="30%" stop-color="#D7DEE8"/><stop offset="55%" stop-color="#94A3B8"/><stop offset="80%" stop-color="#E8EDF3"/><stop offset="100%" stop-color="#8FA0B5"/></linearGradient>'
  +'<radialGradient id="'+p+'span" cx="50%" cy="35%" r="80%"><stop offset="0%" stop-color="#27364F"/><stop offset="60%" stop-color="#101A2C"/><stop offset="100%" stop-color="#060B14"/></radialGradient>'
  +'<linearGradient id="'+p+'srim" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#F2FF8A"/><stop offset="100%" stop-color="#9DBE2A"/></linearGradient>'
  +'<linearGradient id="'+p+'ssteel" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#E8EDF3"/><stop offset="100%" stop-color="#7E8FA6"/></linearGradient>'
  +shineDefs(p)
  +'</defs>'
  +wings
  +'<path d="'+sh+'" fill="url(#'+p+'smet)" stroke="#46536A" stroke-width="3"/>'
  +'<path d="M28,31 C40,28 50,24 60,20 C70,24 80,28 92,31" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity="0.6"/>'
  +'<path d="'+sh2+'" fill="url(#'+p+'span)" stroke="url(#'+p+'srim)" stroke-width="2.5"/>'
  +'<ellipse cx="60" cy="44" rx="24" ry="10" fill="#FFFFFF" opacity="0.08"/>'
  +'<circle cx="30" cy="33" r="3" fill="url(#'+p+'smet)" stroke="#46536A" stroke-width="1"/>'
  +'<circle cx="90" cy="33" r="3" fill="url(#'+p+'smet)" stroke="#46536A" stroke-width="1"/>'
  +'<circle cx="60" cy="58" r="21" fill="#C6F135" opacity="0.16"/>'
  +star5(60,58,17,7.2,'#C6F135')
  +star5(60,58,17,7.2,'none','stroke="#8FA31F" stroke-width="1" opacity="0.8"')
  +star5(60,58,10.5,4.5,'#EDFB8A','opacity="0.9"')
  +spark4(38,32,5,'#FFFFFF')+'<circle cx="84" cy="80" r="2.4" fill="#CBD5E1"/>'
  +shineG(p,'c','<path d="'+sh+'"/>')
  +'</svg>';
},
gold:function(p){
  const sh='M60,12 C76,20 90,24 104,26 L104,58 C104,86 84,101 60,109 C36,101 16,86 16,58 L16,26 C30,24 44,20 60,12 Z';
  const sh2='M60,24 C72,30 82,33 92,35 L92,58 C92,78 78,89 60,96 C42,89 28,78 28,58 L28,35 C38,33 48,30 60,24 Z';
  const WL=['M21,50 C13,46 7,38 5,28 C13,32 19,34 23,36 C19,40 18,45 19,50 Z',
            'M21,60 C14,57 9,51 7,43 C14,46 19,48 23,49 C20,52 19,56 20,60 Z',
            'M23,70 C17,68 12,63 10,56 C16,59 20,60 24,61 C21,64 21,67 22,70 Z'];
  let wings='';
  WL.forEach(function(d){ wings+='<path d="'+d+'" fill="url(#'+p+'gwing)" stroke="#7A4E08" stroke-width="1.2"/>'; });
  wings='<g>'+wings+'</g><g transform="translate(120,0) scale(-1,1)">'+wings+'</g>';
  return '<svg viewBox="0 0 120 120" role="img" aria-hidden="true">'
  +'<defs>'
  +'<linearGradient id="'+p+'gmet" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#FFFBEA"/><stop offset="30%" stop-color="#FDE68A"/><stop offset="55%" stop-color="#F59E0B"/><stop offset="80%" stop-color="#FDE68A"/><stop offset="100%" stop-color="#B45309"/></linearGradient>'
  +'<radialGradient id="'+p+'gpan" cx="50%" cy="35%" r="80%"><stop offset="0%" stop-color="#6B4210"/><stop offset="60%" stop-color="#3A2408"/><stop offset="100%" stop-color="#1C1204"/></radialGradient>'
  +'<linearGradient id="'+p+'gwing" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#FDE68A"/><stop offset="100%" stop-color="#B45309"/></linearGradient>'
  +shineDefs(p)
  +'</defs>'
  +wings
  +'<path d="'+sh+'" fill="url(#'+p+'gmet)" stroke="#7A4E08" stroke-width="3"/>'
  +'<path d="M28,31 C40,28 50,24 60,20 C70,24 80,28 92,31" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity="0.7"/>'
  +'<path d="'+sh2+'" fill="url(#'+p+'gpan)" stroke="#F2FF8A" stroke-width="2"/>'
  +'<ellipse cx="60" cy="44" rx="24" ry="10" fill="#FFFFFF" opacity="0.1"/>'
  +'<circle cx="30" cy="33" r="3" fill="url(#'+p+'gmet)" stroke="#7A4E08" stroke-width="1"/>'
  +'<circle cx="90" cy="33" r="3" fill="url(#'+p+'gmet)" stroke="#7A4E08" stroke-width="1"/>'
  +'<circle cx="60" cy="58" r="22" fill="#F59E0B" opacity="0.3"/>'
  +star5(60,58,17,7.2,'#FFE9A8')
  +star5(60,58,17,7.2,'none','stroke="#B45309" stroke-width="1" opacity="0.85"')
  +star5(60,58,10.5,4.5,'#FFFBEA','opacity="0.95"')
  +spark4(36,30,6,'#FFF3C4')+spark4(86,32,4.5,'#FFF3C4')+'<circle cx="86" cy="82" r="2.6" fill="#FDE68A"/>'
  +shineG(p,'c','<path d="'+sh+'"/>')
  +'</svg>';
},
legend:function(p){
  /* proper feathered wings: primary vanes (dark, behind) + covert vanes
     (light, in front), each with shaft line and inner-vane highlight,
     fanning up-and-out from behind the orb. No purple anywhere. */
  function feather(x,y,len,wid,rot,gA,gB){
    const hw=wid/2, L=len;
    const r2=function(n){ return Math.round(n*10)/10; };
    const vane='M'+r2(x)+','+r2(y)
      +' C'+r2(x-hw)+','+r2(y+L*0.3)+' '+r2(x-hw*0.75)+','+r2(y+L*0.75)+' '+r2(x)+','+r2(y+L)
      +' C'+r2(x+hw*0.75)+','+r2(y+L*0.75)+' '+r2(x+hw)+','+r2(y+L*0.3)+' '+r2(x)+','+r2(y)+' Z';
    const inner='M'+r2(x)+','+r2(y+L*0.08)
      +' C'+r2(x-hw*0.45)+','+r2(y+L*0.4)+' '+r2(x-hw*0.32)+','+r2(y+L*0.72)+' '+r2(x)+','+r2(y+L*0.9)
      +' C'+r2(x+hw*0.32)+','+r2(y+L*0.72)+' '+r2(x+hw*0.45)+','+r2(y+L*0.4)+' '+r2(x)+','+r2(y+L*0.08)+' Z';
    return '<g transform="rotate('+rot+' '+r2(x)+' '+r2(y)+')">'
      +'<path d="'+vane+'" fill="url(#'+p+gA+')" stroke="#8A5A0B" stroke-width="1.4"/>'
      +'<path d="'+inner+'" fill="url(#'+p+gB+')" opacity="0.6"/>'
      +'<line x1="'+r2(x)+'" y1="'+r2(y+3)+'" x2="'+r2(x)+'" y2="'+r2(y+L*0.88)+'" stroke="#8A5A0B" stroke-width="1" opacity="0.55"/>'
      +'</g>';
  }
  const PRIM=[
    {x:38,y:56,len:36,wid:13,rot:112},{x:35,y:62,len:40,wid:14,rot:122},
    {x:33,y:69,len:42,wid:14,rot:132},{x:33,y:76,len:40,wid:13,rot:143},
    {x:36,y:83,len:36,wid:12,rot:154},{x:41,y:88,len:30,wid:11,rot:165},
    {x:47,y:91,len:24,wid:10,rot:176}];
  const COV=[
    {x:38,y:62,len:22,wid:11,rot:116},{x:36,y:70,len:24,wid:11,rot:130},
    {x:37,y:78,len:22,wid:10,rot:144},{x:41,y:85,len:18,wid:10,rot:158}];
  let wings='', coverts='';
  PRIM.forEach(function(f){ wings+=feather(f.x,f.y,f.len,f.wid,f.rot,'lgf2','lgf3'); });
  PRIM.forEach(function(f){ wings+=feather(120-f.x,f.y,f.len,f.wid,-f.rot,'lgf2','lgf3'); });
  COV.forEach(function(f){ coverts+=feather(f.x,f.y,f.len,f.wid,f.rot,'lgf1','lgf2'); });
  COV.forEach(function(f){ coverts+=feather(120-f.x,f.y,f.len,f.wid,-f.rot,'lgf1','lgf2'); });
  let rays='';
  for(let i=0;i<12;i++){
    const a=i*Math.PI/6, dx=Math.cos(a), dy=Math.sin(a);
    if(dy<-0.4&&Math.abs(dx)<0.7) continue; /* no antenna ray poking up between the wings */
    const x1=60+31*dx, y1=60+31*dy, x2=60+40*dx, y2=60+40*dy;
    rays+='<line x1="'+x1.toFixed(1)+'" y1="'+y1.toFixed(1)+'" x2="'+x2.toFixed(1)+'" y2="'+y2.toFixed(1)
      +'" stroke="'+(i%2?'#F59E0B':'#C6F135')+'" stroke-width="2" stroke-linecap="round" opacity="'+(i%2?0.45:0.8)+'"/>';
  }
  return '<svg viewBox="0 0 120 120" role="img" aria-hidden="true">'
  +'<defs>'
  +'<radialGradient id="'+p+'lghalo" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#FCD34D" stop-opacity="0.35"/><stop offset="100%" stop-color="#FCD34D" stop-opacity="0"/></radialGradient>'
  +'<radialGradient id="'+p+'lgorb" cx="42%" cy="36%" r="75%"><stop offset="0%" stop-color="#FFFDEA"/><stop offset="40%" stop-color="#FCD34D"/><stop offset="75%" stop-color="#F59E0B"/><stop offset="100%" stop-color="#B45309"/></radialGradient>'
  +'<linearGradient id="'+p+'lgf1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#FEF3C7"/><stop offset="100%" stop-color="#FBBF24"/></linearGradient>'
  +'<linearGradient id="'+p+'lgf2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#FCD34D"/><stop offset="100%" stop-color="#D97706"/></linearGradient>'
  +'<linearGradient id="'+p+'lgf3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#F59E0B"/><stop offset="100%" stop-color="#92400E"/></linearGradient>'
  +'<linearGradient id="'+p+'lgring" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#F2FF8A"/><stop offset="50%" stop-color="#C6F135"/><stop offset="100%" stop-color="#9DBE2A"/></linearGradient>'
  +'<radialGradient id="'+p+'lggloss" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.55"/><stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
  +'<clipPath id="'+p+'lgoc"><circle cx="60" cy="60" r="27"/></clipPath>'
  +shineDefs(p)
  +'</defs>'
  +'<circle cx="60" cy="60" r="58" fill="url(#'+p+'lghalo)"/>'
  +rays+wings+coverts
  +'<circle cx="60" cy="60" r="27" fill="url(#'+p+'lgorb)"/>'
  +'<g clip-path="url(#'+p+'lgoc)">'
  +'<ellipse cx="60" cy="80" rx="17" ry="7" fill="#92400E" opacity="0.35"/>'
  +'<ellipse cx="50" cy="48" rx="12" ry="8" fill="url(#'+p+'lggloss)" opacity="0.7"/>'
  +'</g>'
  +'<circle cx="60" cy="60" r="27" fill="none" stroke="url(#'+p+'lgring)" stroke-width="4"/>'
  +'<path d="M40,46 A24,24 0 0 1 80,46" fill="none" stroke="#FFFFFF" stroke-width="1.6" opacity="0.6"/>'
  +'<ellipse cx="51" cy="49" rx="8.5" ry="6" fill="#FFFFFF" opacity="0.85"/>'
  +'<ellipse cx="51" cy="49" rx="3.6" ry="2.6" fill="#FFFFFF" opacity="0.95"/>'
  +star5(60,60,13,5.6,'#FFFBEA')
  +star5(60,60,13,5.6,'none','stroke="#F59E0B" stroke-width="1" opacity="0.7"')
  +spark4(24,22,6,'#F2FF8A')+spark4(98,26,5,'#F2FF8A')+'<circle cx="96" cy="92" r="3" fill="#FCD34D"/><circle cx="24" cy="94" r="2.6" fill="#FCD34D"/>'
  +shineG(p,'c','<circle cx="60" cy="60" r="58"/>')
  +'</svg>';
},
specialist:function(p){
  const SH=['M28,40 L8,26 L16,42 L6,50 L26,48 Z',
            'M28,52 L10,48 L20,58 L12,66 L28,62 Z',
            'M30,64 L16,66 L26,72 L20,80 L32,74 Z'];
  let wings='';
  SH.forEach(function(d){ wings+='<path d="'+d+'" fill="url(#'+p+'cch)" stroke="#BAE6FD" stroke-width="1.1"/>'; });
  wings='<g>'+wings+'</g><g transform="translate(120,0) scale(-1,1)">'+wings+'</g>';
  return '<svg viewBox="0 0 120 120" role="img" aria-hidden="true">'
  +'<defs>'
  +'<radialGradient id="'+p+'cbg" cx="50%" cy="35%" r="80%"><stop offset="0%" stop-color="#143A6E"/><stop offset="60%" stop-color="#0A1F42"/><stop offset="100%" stop-color="#040B1C"/></radialGradient>'
  +'<linearGradient id="'+p+'cch" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#D6F1FF"/><stop offset="35%" stop-color="#38BDF8"/><stop offset="75%" stop-color="#1D4ED8"/><stop offset="100%" stop-color="#1E3A8A"/></linearGradient>'
  +'<linearGradient id="'+p+'csteel" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#E8F6FF"/><stop offset="35%" stop-color="#38BDF8"/><stop offset="65%" stop-color="#1D4ED8"/><stop offset="100%" stop-color="#0B1B3A"/></linearGradient>'
  +'<radialGradient id="'+p+'cgloss" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.5"/><stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
  +shineDefs(p)
  +'</defs>'
  +wings
  +'<circle cx="60" cy="60" r="56" fill="none" stroke="url(#'+p+'csteel)" stroke-width="7"/>'
  +'<path d="M15,34 A52,52 0 0 1 86,15" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" opacity="0.55"/>'
  +'<circle cx="60" cy="60" r="51" fill="url(#'+p+'cbg)"/>'
  +'<circle cx="60" cy="60" r="51" fill="none" stroke="#C6F135" stroke-width="1.6" opacity="0.85"/>'
  +'<ellipse cx="45" cy="36" rx="26" ry="14" fill="url(#'+p+'cgloss)" opacity="0.5"/>'
  +'<path d="M30,48 L60,82 L90,48" fill="none" stroke="#050D20" stroke-width="19" stroke-linecap="round" stroke-linejoin="round" transform="translate(0,3)" opacity="0.85"/>'
  +'<path d="M30,48 L60,82 L90,48" fill="none" stroke="url(#'+p+'cch)" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/>'
  +'<path d="M34,45 L60,74 L86,45" fill="none" stroke="#D6F1FF" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" opacity="0.65"/>'
  +'<circle cx="60" cy="28" r="11" fill="#C6F135" opacity="0.22"/>'
  +'<path d="M60,18 l6.5,9 -6.5,9 -6.5,-9 Z" fill="#C6F135" stroke="#8FA31F" stroke-width="1"/>'
  +'<path d="M60,21 l3.5,6 -3.5,6 -3.5,-6 Z" fill="#F2FF8A" opacity="0.9"/>'
  +spark4(36,86,4.5,'#7DD3FC')+'<circle cx="86" cy="86" r="2.6" fill="#7DD3FC"/>'
  +shineG(p,'c','<circle cx="60" cy="60" r="56"/>')
  +'</svg>';
}
};

function svg(name,size){
  const idp='bdg'+(++uidN)+'_';
  const art=(ART[name]||ART.new)(idp);
  const px=Math.max(16,Math.min(240,Number(size)||32));
  return '<span class="bdg bdg-t-'+name+'" style="width:'+px+'px;height:'+px+'px" aria-hidden="true">'+art+'</span>';
}

/* ================= tracking ================= */
function todayStr(){ return new Date().toISOString().slice(0,10); }
var fgSec=0, counted=false, sessDay=todayStr(), timer=null;

function awardDay(force){
  const p=prof(), td=todayStr();
  if(p.lastLoginDay===td&&!force) return false;
  p.lastLoginDay=td;
  p.loginDays=(Number(p.loginDays)||0)+1;
  try{ HUB.store.save(); }catch(e){}
  checkUnlocks(true);
  return true;
}
function tickOnce(){
  if(document.hidden) return;
  const td=todayStr();
  if(td!==sessDay){ sessDay=td; fgSec=0; counted=false; } /* crossed midnight */
  fgSec++;
  if(fgSec>=60&&!counted){ counted=true; awardDay(false); }
}
/* honest unlock log — feeds the notification center (last 30 days) */
function logUnlock(id){
  const p=prof();
  if(!Array.isArray(p.badgeFeed)) p.badgeFeed=[];
  if(!p.badgeFeed.some(function(u){ return u&&u.id===id; })){
    p.badgeFeed.push({id:id,ts:Date.now()});
    if(p.badgeFeed.length>20) p.badgeFeed=p.badgeFeed.slice(-20);
  }
}
function checkUnlocks(celebrate){
  const p=prof();
  if(!p.badgesSeen||typeof p.badgesSeen!=='object') p.badgesSeen={};
  const seen=p.badgesSeen, tr=tierOf(p.loginDays), sp=isSpecialist();
  const newly=[];
  if(seen.tier!==tr){
    if(seen.tier&&RANK[tr]>RANK[seen.tier]) newly.push(tr);
    seen.tier=tr;
  }
  if(sp&&!seen.specialist){ seen.specialist=true; newly.push('specialist'); }
  if(newly.length) newly.forEach(logUnlock);
  try{ HUB.store.save(); }catch(e){}
  if(celebrate&&newly.length){
    try{ if(HUB.ui&&HUB.ui.toast) HUB.ui.toast(t('bdg.earnT')+' '+newly.map(function(n){ return t('bdg.'+n); }).join(' + ')); }catch(e){}
    earnSheet(newly);
  }
  return newly;
}
function start(){
  const p=prof();
  if(!p.createdAt){ p.createdAt=Date.now(); try{HUB.store.save();}catch(e){} }
  checkUnlocks(false); /* seed seen-state; no celebration for history */
  if(timer) return;
  timer=setInterval(tickOnce,1000);
}

/* ================= UI ================= */
function headerHTML(p){
  p=p||prof();
  const tr=tierOf(p.loginDays);
  let h='<button class="me-badges" id="meBadges" aria-label="'+esc(t('bdg.title'))+'">'
    +'<span class="me-badges-ic">'+svg(tr,30)+'</span>'
    +'<span class="me-badges-name">'+esc(t('bdg.'+tr))+'</span>';
  if((p.profReviews||0)>=SPEC_GOAL||(p===prof()&&isSpecialist()))
    h+='<span class="me-badges-ic">'+svg('specialist',30)+'</span>';
  return h+'</button>';
}
/* badges for any person record.
   DEMO-ONLY data derivation: sample/demo person records carry no login
   history, so a deterministic hash of the record id yields a stable,
   plausible tier per person (same person -> same badge, every launch).
   Stored loginDays/profReviews ALWAYS win when present (the real-data
   path), and hp-self (my own glass profile) uses my real counts. */
function hashN(s){ s=String(s==null?'':s); let h=2166136261;
  for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); }
  return h>>>0; }
function personDays(p){
  if(p&&p.self) return Number(prof().loginDays)||0;
  const d=Number(p&&p.loginDays);
  if(isFinite(d)&&d>=0) return d;
  return hashN(p&&p.id)%430; /* DEMO: stable per-record, spans all tiers */
}
function personReviews(p){
  if(p&&p.self) return myReviewCount();
  const r=Number(p&&p.profReviews);
  if(isFinite(r)&&r>=0) return r;
  return hashN('rev:'+(p&&p.id))%140; /* DEMO: stable per-record */
}
function personTier(p){ return tierOf(personDays(p)); }
function personSpec(p){ if(p&&p.self) return isSpecialist(); return personReviews(p)>=SPEC_GOAL; }
/* Tappable: the tier badge (+ SPECIALIST when earned) shown next to another
   person's name. Tapping opens their read-only badge showcase. */
function forPerson(p){
  p=p||{};
  const tr=personTier(p), sp=personSpec(p);
  let h='<button class="hp-badges" data-pid="'+esc(String(p.id||''))+'" aria-label="'
    +esc(String(p.name||''))+' — '+esc(t('bdg.title'))+'">'
    +'<span class="me-badges-ic" title="'+esc(t('bdg.'+tr))+'">'+svg(tr,26)+'</span>';
  if(sp) h+='<span class="me-badges-ic" title="'+esc(t('bdg.specialist'))+'">'+svg('specialist',26)+'</span>';
  return h+'</button>';
}
/* Read-only showcase for another person: their earned badges shine, locked
   ones stay dimmed. No progress bars or "what's next" tips for others —
   just the badges and what each one means. */
function personShowcaseHTML(p){
  const tr=personTier(p), sp=personSpec(p);
  let cards='';
  TIERS.forEach(function(x){
    const unlocked=RANK[tr]>=RANK[x.id];
    cards+='<div class="bdg-card'+(unlocked?'':' bdg-islocked')+'">'
      +'<div class="bdg-art">'+svg(x.id,84)+(unlocked?'':'<span class="bdg-lock" aria-hidden="true">🔒</span>')+'</div>'
      +'<div class="bdg-name">'+esc(t('bdg.'+x.id))+'</div>'
      +'<div class="bdg-desc">'+esc(t('bdg.'+x.id+'D'))+'</div></div>';
  });
  cards+='<div class="bdg-card'+(sp?'':' bdg-islocked')+'">'
    +'<div class="bdg-art">'+svg('specialist',84)+(sp?'':'<span class="bdg-lock" aria-hidden="true">🔒</span>')+'</div>'
    +'<div class="bdg-name">'+esc(t('bdg.specialist'))+'</div>'
    +'<div class="bdg-desc">'+esc(t('bdg.specialistD'))+'</div></div>';
  return '<div class="bdg-show">'
    +'<h2>'+esc(p.name||'')+'</h2>'
    +'<p class="sub">'+esc(t('bdg.title'))+'</p>'
    +'<div class="bdg-grid">'+cards+'</div>'
    +'<p class="hint">'+esc(t('bdg.note'))+'</p>'
    +'<p class="hint">'+esc(t('hp.demoProf'))+'</p>'
    +'</div>';
}
function openPersonShowcase(pidOrP){
  let p=(pidOrP&&typeof pidOrP==='object')?pidOrP:null;
  if(!p&&pidOrP&&HUB.store) p=HUB.store.find('people',pidOrP);
  if(!p||!HUB.ui||!HUB.ui.openSheet) return;
  HUB.ui.openSheet(personShowcaseHTML(p));
}
function showcaseHTML(){
  const p=prof(), days=Number(p.loginDays)||0, tr=tierOf(days), nx=nextTier(tr);
  const revs=myPoints(), sp=isSpecialist();
  let cards='';
  TIERS.forEach(function(x){
    const unlocked=RANK[tr]>=RANK[x.id];
    let prog='';
    if(x.id===tr&&nx) prog='<div class="bdg-prog">'+esc(t('bdg.nextTier',{n:days,goal:TIERS[RANK[x.id]+1].days,next:t('bdg.'+nx)}))+'</div>';
    else if(x.id===tr&&!nx) prog='<div class="bdg-prog bdg-prog-max">'+esc(t('bdg.maxTier'))+'</div>';
    cards+='<div class="bdg-card'+(unlocked?'':' bdg-islocked')+'">'
      +'<div class="bdg-art">'+svg(x.id,84)+(unlocked?'':'<span class="bdg-lock" aria-hidden="true">🔒</span>')+'</div>'
      +'<div class="bdg-name">'+esc(t('bdg.'+x.id))+'</div>'
      +'<div class="bdg-desc">'+esc(t('bdg.'+x.id+'D'))+'</div>'+prog+'</div>';
  });
  const specProg=sp
    ?'<div class="bdg-prog bdg-prog-max">'+esc(t('bdg.specDone'))+'</div>'
    :'<div class="bdg-prog">'+esc(t('bdg.specNeed',{n:Math.min(revs,PTS_GOAL),goal:PTS_GOAL}))+'</div>';
  cards+='<div class="bdg-card'+(sp?'':' bdg-islocked')+'">'
    +'<div class="bdg-art">'+svg('specialist',84)+(sp?'':'<span class="bdg-lock" aria-hidden="true">🔒</span>')+'</div>'
    +'<div class="bdg-name">'+esc(t('bdg.specialist'))+'</div>'
    +'<div class="bdg-desc">'+esc(t('bdg.specialistD'))+'</div>'+specProg+'</div>';
  return '<div class="bdg-show">'
    +'<h2>'+esc(t('bdg.title'))+'</h2>'
    +'<p class="sub">'+esc(t('bdg.sub'))+'</p>'
    +'<div class="bdg-grid">'+cards+'</div>'
    +'<p class="hint">'+esc(t('bdg.note'))+'</p>'
    +'</div>';
}
function openShowcase(){ HUB.ui.openSheet(showcaseHTML()); }
/* Earn-moment celebration: hero badge(s) large + animated, the exact reason
   why, every other badge (locked ones dimmed), and a what's-next card with
   accurate remaining counts + a concrete tip. */
function earnSheet(names){
  const p=prof(), days=Number(p.loginDays)||0, revs=myPoints();
  const tr=tierOf(days), nx=nextTier(tr), sp=isSpecialist();
  const whyFor=function(n){
    return n==='specialist'?t('bdg.whySpec'):t('bdg.whyTier',{n:TIERS[RANK[n]].days});
  };
  const cards=names.map(function(n){
    return '<div class="bdg-earncard"><div class="bdg-earnart">'+svg(n,120)+'</div>'
      +'<h2>'+esc(t('bdg.'+n))+'</h2><p class="bdg-why">'+esc(whyFor(n))+'</p></div>';
  }).join('');
  const earnedSet={};
  TIERS.forEach(function(x){ if(RANK[x.id]<=RANK[tr]) earnedSet[x.id]=1; });
  if(sp) earnedSet.specialist=1;
  const others=['new','silver','gold','legend','specialist'].filter(function(id){ return names.indexOf(id)<0; }).map(function(id){
    return '<span class="bdg-oth'+(earnedSet[id]?' bdg-oth-earned':'')+'" title="'+esc(t('bdg.'+id))+'">'+svg(id,44)+'</span>';
  }).join('');
  const rows=[];
  if(nx){
    rows.push('<div class="bdg-nextrow"><span class="bdg-nextic">'+svg(nx,40)+'</span><span class="grow">'
      +'<div class="bdg-nextneed">'+esc(t('bdg.nextTierNeed',{n:TIERS[RANK[tr]+1].days-days,next:t('bdg.'+nx)}))+'</div>'
      +'<div class="bdg-nexttip">'+esc(t('bdg.tipLogin'))+'</div></span></div>');
  }
  if(!sp){
    rows.push('<div class="bdg-nextrow"><span class="bdg-nextic">'+svg('specialist',40)+'</span><span class="grow">'
      +'<div class="bdg-nextneed">'+esc(t('bdg.nextSpecNeed',{n:Math.max(0,PTS_GOAL-revs)}))+'</div>'
      +'<div class="bdg-nexttip">'+esc(t('bdg.tipReview'))+'</div></span></div>');
  }
  const nextHtml='<div class="bdg-next"><h3>'+esc(t('bdg.nextT'))+'</h3>'
    +(rows.length?rows.join(''):'<div class="bdg-nexttip">'+esc(t('bdg.maxTier'))+' '+esc(t('bdg.specDone'))+'</div>')
    +'</div>';
  HUB.ui.openSheet('<div class="bdg-earn">'
    +'<div class="bdg-earnburst" aria-hidden="true"></div>'
    +'<h1>'+esc(t('bdg.earnT'))+' 🎉</h1>'
    +'<div class="bdg-earncards">'+cards+'</div>'
    +'<div class="bdg-others" aria-hidden="true">'+others+'</div>'
    +nextHtml
    +'<button class="btn btn-primary btn-block" id="bdgViewAll" style="margin-top:14px">'+esc(t('bdg.viewAll'))+'</button>'
    +'</div>');
  const b=document.getElementById('bdgViewAll');
  if(b) b.onclick=function(){ openShowcase(); };
}

/* ---- public API ---- */
HUB.badges={
  tierOf:tierOf, myTier:function(){ return tierOf(prof().loginDays); },
  myReviewCount:myReviewCount, isSpecialist:isSpecialist,
  svg:svg, headerHTML:headerHTML, forPerson:forPerson,
  openPersonShowcase:openPersonShowcase, personTier:personTier,
  openShowcase:openShowcase, start:start,
  onReview:function(){ addPoints(PTS_REVIEW); checkUnlocks(true); },
  onAddProfessor:function(){ addPoints(PTS_ADDPROF); checkUnlocks(true); },
  myPoints:myPoints, ptsGoal:function(){ return PTS_GOAL; },
  ptsFor:{review:PTS_REVIEW,addProfessor:PTS_ADDPROF},
  _tick:tickOnce,
  _debug:{
    status:function(){ const p=prof(); return {loginDays:Number(p.loginDays)||0,lastLoginDay:p.lastLoginDay||null,tier:tierOf(p.loginDays),reviews:myReviewCount(),points:myPoints(),specialist:isSpecialist(),fgSec:fgSec,seen:p.badgesSeen||{}}; },
    setLoginDays:function(n){ prof().loginDays=n; try{HUB.store.save();}catch(e){} return checkUnlocks(true); },
    setLastDay:function(s){ prof().lastLoginDay=s; try{HUB.store.save();}catch(e){} },
    setReviews:function(n){ dbgReviewCount=n; prof().reviewPts=null; /* re-seed points from the new count */ try{HUB.store.save();}catch(e){} return checkUnlocks(true); },
    setPoints:function(n){ prof().reviewPts=Math.max(0,Math.floor(Number(n)||0)); try{HUB.store.save();}catch(e){} return checkUnlocks(true); },
    simulateMinute:function(){ counted=false; fgSec=59; sessDay=todayStr(); tickOnce(); return HUB.badges._debug.status(); },
    forceAward:function(){ return awardDay(true); },
    reset:function(){ const p=prof(); delete p.loginDays; delete p.lastLoginDay; delete p.badgeFeed; delete p.reviewPts; p.badgesSeen={}; dbgReviewCount=null; try{HUB.store.save();}catch(e){} }
  }
};
})();
