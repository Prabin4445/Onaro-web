/* HUB STYLE CLOSET (2026-10-01): digital closet + personal stylist + outfit
   planner in the Daily tab. 100% offline-first: localStorage (hub_style_v1)
   for data, IndexedDB (hub_style) for item photos. Suggestions are built ONLY
   from clothes the user owns. Mounts as a .chatroot full overlay (degree.js
   pattern). Honest boundary: no fake AI recognition — manual entry with smart
   defaults; cloud enhancement later. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const ui=function(){ return HUB.ui; };
const esc=function(s){ return ui().esc(s==null?'':String(s)); };

/* ================= constants ================= */
const CATS=[
  ['tops','👕'],['bottoms','👖'],['dresses','👗'],['jackets','🧥'],
  ['sweaters','🧶'],['shoes','👟'],['bags','👜'],['jewelry','💍'],
  ['accessories','🧢'],['swimwear','🩱'],['basics','🧦'],['activewear','👚'],
  ['sleepwear','💤'],['seasonal','🧣']
];
/* color: [key, hex, neutral?] */
const COLORS=[
  ['black','#232323',1],['white','#f4f4f4',1],['gray','#9aa0a6',1],
  ['beige','#d9c7a7',1],['cream','#f1e8d2',1],['navy','#27436b',1],
  ['brown','#7a4a2b',1],['olive','#6b7a3f',0],['denim','#4a6fa5',0],
  ['red','#d43d3d',0],['pink','#f0a3c0',0],['blue','#3d7dd4',0],
  ['green','#3da35d',0],['yellow','#eec93f',0],['orange','#e07b39',0],
  ['gold','#c9a227',0],['silver','#c6c9cf',0],['multicolor','linear-gradient(135deg,#d43d3d,#eec93f,#3da35d,#3d7dd4)',0]
];
const NEUTRALS={}; COLORS.forEach(function(c){ if(c[2]) NEUTRALS[c[0]]=1; });
const OCCASIONS=['class','coffee','interview','dinner','party','gym','airport','vacation','wedding','birthday','casual','work'];
const VIBES=['minimal','feminine','edgy','clean','soft','bold','casual','professional','streetwear','comfortable'];
const FEELS=['comfortable','confident','cute','elegant','relaxed','professional'];
const SEASONS=['spring','summer','fall','winter'];
const STATUSES=['available','laundry','drycleaning','packed','borrowed'];
const WXBANDS=['hot','warm','cool','cold','rainy'];
const OCC_EMOJI={class:'🎓',coffee:'☕',interview:'💼',dinner:'🍽️',party:'💃',gym:'🏋️',airport:'✈️',vacation:'🏖️',wedding:'👰',birthday:'🎉',casual:'🏠',work:'💼'};
const VIBE_EMOJI={minimal:'✨',feminine:'🎀',edgy:'🖤',clean:'🤍',soft:'🌸',bold:'🔥',casual:'👟',professional:'💼',streetwear:'🏙️',comfortable:'🌿'};
const WX_EMOJI={hot:'☀️',warm:'🌤️',cool:'🍂',cold:'🥶',rainy:'🌧️'};
const STATUS_EMOJI={available:'✅',laundry:'🧺',drycleaning:'🧼',packed:'🧳',borrowed:'🤝'};
/* Clay 3D status icons — visual twin of STATUS_EMOJI, swapped in everywhere a status shows. */
const STATUS_ICON={available:'st-check',laundry:'st-laundry',drycleaning:'st-hanger',packed:'st-packing',borrowed:'st-borrowed'};
function statusIcon(s){ return clayIcon(STATUS_ICON[s]||'st-check',STATUS_EMOJI[s]||'📌'); }
/* Clay 3D twins for occasions, weather, vibes and feels — emoji survive only as fallback. */
const OCC_ICON={class:'st-occ-class',coffee:'st-occ-coffee',interview:'st-occ-interview',dinner:'st-occ-dinner',party:'st-occ-party',gym:'st-occ-gym',airport:'st-occ-airport',vacation:'st-occ-vacation',wedding:'st-occ-wedding',birthday:'st-occ-birthday',casual:'st-occ-casual',work:'st-occ-work'};
const VIBE_ICON={minimal:'st-vibe-minimal',feminine:'st-vibe-feminine',edgy:'st-vibe-edgy',clean:'st-vibe-clean',soft:'st-vibe-soft',bold:'st-vibe-bold',casual:'st-vibe-casual',professional:'st-vibe-professional',streetwear:'st-vibe-streetwear',comfortable:'st-vibe-comfortable'};
const WX_ICON={hot:'st-wx-hot',warm:'st-wx-warm',cool:'st-wx-cool',cold:'st-wx-cold',rainy:'st-wx-rainy'};
const FEEL_ICON={comfortable:'st-vibe-comfortable',confident:'st-feel-confident',cute:'st-feel-cute',elegant:'st-feel-elegant',relaxed:'st-feel-relaxed',professional:'st-vibe-professional'};
function occIcon(s){ return clayIcon(OCC_ICON[s]||'st-closet',OCC_EMOJI[s]||'👗'); }
function vibeIcon(v){ return clayIcon(VIBE_ICON[v]||'st-styleme',VIBE_EMOJI[v]||'✨'); }
function wxIcon(b){ return clayIcon(WX_ICON[b]||'st-wx-auto',WX_EMOJI[b]||'☀️'); }
function wxAutoIcon(){ return clayIcon('st-wx-auto','🤖'); }
function feelIcon(f){ return clayIcon(FEEL_ICON[f]||'st-feel-cute','💛'); }
/* Chip with a clay icon + label (icons are safe HTML from clayIcon; label is escaped). */
function icChip(cls,attrs,iconHTML,label){
  return '<button class="'+cls+'" '+attrs+'><span class="sty-clay">'+iconHTML+'</span><span>'+esc(label)+'</span></button>';
}
/* occasion -> categories to prioritize (score boost), categories to avoid */
const OCC_RULES={
  interview:{boost:['tops','bottoms','shoes','bags'],avoid:['activewear','swimwear','sleepwear'],vibe:['professional','clean','minimal']},
  gym:{boost:['activewear','shoes'],avoid:['dresses','jackets','jewelry','bags','swimwear','sleepwear'],vibe:['casual','comfortable']},
  wedding:{boost:['dresses','jewelry','shoes','bags'],avoid:['activewear','swimwear','sleepwear','basics'],vibe:['elegant','feminine','bold']},
  dinner:{boost:['dresses','tops','jewelry','shoes'],avoid:['activewear','swimwear','sleepwear'],vibe:['elegant','feminine','clean']},
  party:{boost:['dresses','tops','jewelry','shoes'],avoid:['activewear','swimwear','sleepwear'],vibe:['bold','feminine','edgy']},
  work:{boost:['tops','bottoms','shoes','bags','jackets'],avoid:['activewear','swimwear','sleepwear'],vibe:['professional','clean','minimal']},
  class:{boost:['tops','bottoms','shoes','basics'],avoid:['swimwear','sleepwear'],vibe:['casual','comfortable','minimal']},
  coffee:{boost:['tops','bottoms','dresses','shoes'],avoid:['activewear','swimwear','sleepwear'],vibe:['casual','soft','cute']},
  airport:{boost:['tops','bottoms','shoes','jackets'],avoid:['dresses','swimwear','sleepwear','jewelry'],vibe:['comfortable','casual','minimal']},
  vacation:{boost:['dresses','swimwear','tops','shoes','bags'],avoid:['sleepwear'],vibe:['casual','bold','soft']},
  birthday:{boost:['dresses','tops','jewelry','shoes'],avoid:['activewear','swimwear','sleepwear'],vibe:['feminine','bold','cute']},
  casual:{boost:['tops','bottoms','shoes'],avoid:['swimwear','sleepwear'],vibe:['casual','comfortable','minimal']}
};
/* weather band -> {preferCats, avoidCats, preferSeasons} */
const WX_RULES={
  hot:{prefer:['tops','bottoms','dresses','shoes','swimwear'],avoid:['jackets','sweaters','seasonal'],seasons:['summer','spring']},
  warm:{prefer:['tops','bottoms','dresses','shoes'],avoid:['sweaters','seasonal'],seasons:['spring','summer','fall']},
  cool:{prefer:['jackets','sweaters','tops','bottoms','shoes'],avoid:['swimwear'],seasons:['fall','spring']},
  cold:{prefer:['jackets','sweaters','seasonal','shoes','bottoms'],avoid:['swimwear','dresses'],seasons:['winter','fall']},
  rainy:{prefer:['jackets','shoes','bags'],avoid:['swimwear'],seasons:['fall','spring','winter']}
};
/* simple hue families for harmony: color -> family */
const HUE_FAM={black:'n',white:'n',gray:'n',beige:'n',cream:'n',navy:'n',brown:'n',
  olive:'g',denim:'b',red:'r',pink:'r',blue:'b',green:'g',yellow:'y',orange:'o',gold:'y',silver:'n',multicolor:'m'};
const COMPLEMENT={r:'g',g:'r',b:'o',o:'b',y:'r'};

/* ================= storage ================= */
const LS_KEY='hub_style_v1';
function blank(){ return {items:[],outfits:[],cal:{},settings:{dontRepeat:7,wxMode:'auto'},cats:[]}; }
function load(){
  try{
    const raw=localStorage.getItem(LS_KEY);
    if(!raw) return blank();
    const d=Object.assign(blank(),JSON.parse(raw));
    if(!Array.isArray(d.items)) d.items=[];
    if(!Array.isArray(d.outfits)) d.outfits=[];
    if(!d.cal||typeof d.cal!=='object') d.cal={};
    d.settings=Object.assign(blank().settings,d.settings||{});
    return d;
  }catch(e){ return blank(); }
}
let DB=load();
function save(){ try{ localStorage.setItem(LS_KEY,JSON.stringify(DB)); }catch(e){} }
function uid(p){ return (p||'id')+'_'+Date.now().toString(36)+Math.floor(Math.random()*1e6).toString(36); }
function todayISO(){
  const d=new Date();
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function daysAgoISO(n){
  const d=new Date(); d.setDate(d.getDate()-n);
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function itemById(id){ return DB.items.filter(function(x){ return x.id===id; })[0]||null; }
function outfitById(id){ return DB.outfits.filter(function(x){ return x.id===id; })[0]||null; }
function allCats(){
  const base=CATS.map(function(c){ return c[0]; });
  (DB.cats||[]).forEach(function(c){ if(base.indexOf(c)<0) base.push(c); });
  return base;
}
function catEmoji(cat){
  for(let i=0;i<CATS.length;i++) if(CATS[i][0]===cat) return CATS[i][1];
  return '👗';
}
function catName(cat){ return t('style.cat.'+cat)!=='style.cat.'+cat?t('style.cat.'+cat):cat; }

/* ---------- IndexedDB photos ---------- */
let _idbP=null;
function idb(){
  if(_idbP) return _idbP;
  _idbP=new Promise(function(res,rej){
    try{
      const r=indexedDB.open('hub_style',1);
      r.onupgradeneeded=function(){ try{ r.result.createObjectStore('photos'); }catch(e){} };
      r.onsuccess=function(){ res(r.result); };
      r.onerror=function(){ rej(r.error); };
    }catch(e){ rej(e); }
  });
  return _idbP;
}
function photoPut(id,dataUrl){
  return idb().then(function(db){
    return new Promise(function(res,rej){
      try{
        const tx=db.transaction('photos','readwrite');
        tx.objectStore('photos').put(dataUrl,id);
        tx.oncomplete=function(){ res(true); }; tx.onerror=function(){ rej(tx.error); };
      }catch(e){ rej(e); }
    });
  }).catch(function(){ return false; });
}
function photoGet(id){
  return idb().then(function(db){
    return new Promise(function(res){
      try{
        const tx=db.transaction('photos','readonly');
        const q=tx.objectStore('photos').get(id);
        q.onsuccess=function(){ res(q.result||null); };
        q.onerror=function(){ res(null); };
      }catch(e){ res(null); }
    });
  }).catch(function(){ return null; });
}
function photoDel(id){
  idb().then(function(db){
    try{ const tx=db.transaction('photos','readwrite'); tx.objectStore('photos').delete(id); }catch(e){}
  }).catch(function(){});
}
/* downscale an image File -> dataURL (max 800px, jpeg) */
function fileToPhoto(file){
  return new Promise(function(res){
    const url=URL.createObjectURL(file);
    const img=new Image();
    img.onload=function(){
      try{
        const max=800, sc=Math.min(1,max/Math.max(img.width,img.height));
        const w=Math.max(1,Math.round(img.width*sc)), h=Math.max(1,Math.round(img.height*sc));
        const cv=document.createElement('canvas'); cv.width=w; cv.height=h;
        cv.getContext('2d').drawImage(img,0,0,w,h);
        URL.revokeObjectURL(url);
        res(cv.toDataURL('image/jpeg',0.82));
      }catch(e){ URL.revokeObjectURL(url); res(null); }
    };
    img.onerror=function(){ URL.revokeObjectURL(url); res(null); };
    img.src=url;
  });
}

/* ================= weather ================= */
function wxBand(){
  /* manual override wins; otherwise cached Open-Meteo data; fallback warm */
  const m=DB.settings.wxMode;
  if(m&&m!=='auto'&&WXBANDS.indexOf(m)>=0) return m;
  try{
    const d=HUB.wx&&HUB.wx.data?HUB.wx.data():null;
    if(d&&d.current){
      const unit=HUB.wx.unit?HUB.wx.unit():'f';
      let tmp=+d.current.temperature_2m;
      if(unit!=='f') tmp=tmp*9/5+32;
      const code=+d.current.weather_code||0;
      if(code>=51&&code<=67||code>=80&&code<=82||code>=95) return 'rainy';
      if(code>=71&&code<=77) return 'cold';
      if(tmp>=80) return 'hot';
      if(tmp>=65) return 'warm';
      if(tmp>=50) return 'cool';
      return 'cold';
    }
  }catch(e){}
  return 'warm';
}
function wxLabel(){
  const b=wxBand(), m=DB.settings.wxMode;
  const ic='<span class="sty-clay xs">'+wxIcon(b)+'</span> ';
  try{
    const d=HUB.wx&&HUB.wx.data?HUB.wx.data():null;
    if((!m||m==='auto')&&d&&d.current){
      const unit=HUB.wx.unit?HUB.wx.unit():'f';
      let tmp=Math.round(+d.current.temperature_2m);
      return ic+tmp+'°'+(unit==='f'?'F':'C');
    }
  }catch(e){}
  return ic+esc(t('style.wx.'+b));
}

/* ================= overlay lifecycle (degree.js pattern) ================= */
const ROOT_ID='hubStyleRoot';
let viewStack=[];
function ensureClosed(){
  const old=document.getElementById(ROOT_ID);
  if(old) old.remove();
  document.removeEventListener('keydown',onKey,true);
}
function close(){ ensureClosed(); viewStack=[]; }
function onKey(e){
  if(e.key!=='Escape') return;
  const sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden){ e.stopImmediatePropagation(); ui().closeSheet(); return; }
  e.stopImmediatePropagation();
  if(viewStack.length>1){ viewStack.pop(); paint(); }
  else close();
}
function genderCls(){
  try{ return (HUB.store.state.profile||{}).gender==='female'?' sty-female':''; }catch(e){ return ''; }
}
function open(v){
  /* PERF 2026-10-02: optional initial view — open('styleme') paints once instead
     of open();go('styleme') painting twice. */
  ensureClosed();
  ui().closeSheet();
  ['search','pulse','notifications'].forEach(function(k){ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  viewStack=[{v:(v||'home')}];
  const app=document.getElementById('app')||document.body;
  const d=document.createElement('div');
  d.className='chatroot styroot'+genderCls(); d.id=ROOT_ID;
  d.innerHTML='<div class="chatpanel sty-panel">'+
    '<div class="sty-topbar">'+
    '<button class="iconbtn" data-sty="back" aria-label="'+esc(t('common.back'))+'">‹</button>'+
    '<div class="sty-topbar-t"><span class="sty-clay" style="width:26px;height:26px;vertical-align:-6px;margin-right:6px">'+clayIcon('st-closet','👗')+'</span>'+esc(t('style.title'))+'</div>'+
    '<button class="iconbtn" data-sty="close" aria-label="'+esc(t('common.close'))+'">✕</button></div>'+
    '<div class="sty-body" id="styBody"></div></div>';
  app.appendChild(d);
  d.addEventListener('click',function(e){ if(e.target===d) close(); });
  /* buttery motion: ink ripple on pressable CTAs (delegated, transform-only) */
  d.addEventListener('pointerdown',function(e){
    const btn=e.target.closest&&e.target.closest('.sty-cta,.sty-qbtn.primary,.btn-dark');
    if(!btn||btn.querySelector('.sty-ink')) return;
    try{
      const r=btn.getBoundingClientRect();
      const s=document.createElement('span'); s.className='sty-ink';
      const sz=Math.max(r.width,r.height)*2.2;
      s.style.width=s.style.height=sz+'px';
      s.style.left=(e.clientX-r.left-sz/2)+'px';
      s.style.top=(e.clientY-r.top-sz/2)+'px';
      btn.appendChild(s);
      setTimeout(function(){ if(s.parentNode) s.parentNode.removeChild(s); },650);
    }catch(err){}
  });
  /* pop-on-tap for chips: re-trigger the transform-only tap animation */
  d.addEventListener('click',function(e){
    const ch=e.target.closest&&e.target.closest('.sty-chips .chip:not(.static)');
    if(ch&&!ch.classList.contains('sty-tap')){
      ch.classList.add('sty-tap');
      ch.addEventListener('animationend',function h(){ ch.classList.remove('sty-tap'); ch.removeEventListener('animationend',h); });
    }
  });
  d.querySelector('[data-sty="close"]').onclick=close;
  d.querySelector('[data-sty="back"]').onclick=function(){
    if(viewStack.length>1){ viewStack.pop(); paint(); } else close();
  };
  document.addEventListener('keydown',onKey,true);
  paint();
}
function go(v,params){ viewStack.push(Object.assign({v:v},params||{})); paint(); }
function cur(){ return viewStack[viewStack.length-1]||{v:'home'}; }
function paint(){
  const body=document.getElementById('styBody');
  if(!body){ return; }
  const c=cur();
  const fn=VIEWS[c.v]||VIEWS.home;
  const changed=(paint._lastV||'')!==c.v;
  paint._lastV=c.v;
  body.innerHTML='';
  try{ fn(body,c); }catch(e){ body.innerHTML='<div class="empty"><div class="big">👗</div><p>'+esc(String(e&&e.message||e))+'</p></div>'; }
  body.scrollTop=0;
  /* springy view entrance, only on real view changes (not soft repaints) */
  if(changed){
    body.classList.remove('sty-view-in');
    void body.offsetWidth;
    body.classList.add('sty-view-in');
  }
}

/* ================= shared bits ================= */
function greetKey(){
  const h=new Date().getHours();
  return h<12?'style.gm':(h<18?'style.ga':'style.ge');
}
/* countUp(root) — rAF number tween for [data-count]; textContent-only, respects reduced motion. */
function countUp(root){
  try{
    const reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
    root.querySelectorAll('[data-count],[data-ringpct]').forEach(function(el){
      const target=+(el.getAttribute('data-count')||el.getAttribute('data-ringpct'))||0;
      const suffix=el.hasAttribute('data-ringpct')?'%':'';
      if(reduce||!target){ el.textContent=String(target)+suffix; return; }
      const t0=performance.now(), dur=750;
      const step=function(now){
        const p=Math.min(1,(now-t0)/dur), e=1-Math.pow(1-p,3);
        el.textContent=String(Math.round(target*e))+suffix;
        if(p<1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }catch(e){}
}
function photoTileHTML(it,cls){
  /* async photo fill: tile renders clay category icon now, swaps in photo when loaded.
     .sty-ph-loading shows a shimmer sweep until the lookup resolves (photo or not). */
  return '<div class="sty-tile '+(cls||'')+' sty-ph-loading" data-photo-for="'+esc(it.id)+'" data-emoji="'+esc(catEmoji(it.category))+'">'+
    catIcon(it.category)+'</div>';
}
function hydratePhotos(root){
  const tiles=root.querySelectorAll('[data-photo-for]');
  tiles.forEach(function(el){
    if(el._phDone) return; /* already resolved by an earlier pass */
    el._phDone=true;
    const id=el.getAttribute('data-photo-for');
    photoGet(id).then(function(url){
      if(!el.isConnected) return;
      el.classList.remove('sty-ph-loading');
      if(!url) return;
      el.classList.add('has-photo');
      el.innerHTML='<img src="'+esc(url)+'" alt="">';
    });
  });
}
function favCount(){ return DB.items.filter(function(x){ return x.favorite; }).length; }
/* item card for grids + builder pick lists (data-pick for builder, data-item for closet) */
function itemCardHTML(it,pickMode){
  return '<button class="sty-item" '+(pickMode?'data-pick="'+esc(it.id)+'"':'data-item="'+esc(it.id)+'"')+'>'+
    photoTileHTML(it)+
    '<span class="sty-item-n">'+esc(it.name||catName(it.category))+'</span>'+
    '<span class="sty-item-m">'+esc(catName(it.category))+(it.colors&&it.colors.length?' · '+esc(t('style.color.'+it.colors[0])):'')+'</span>'+
    (it.favorite?'<span class="sty-fav">❤️</span>':'')+
    (it.status&&it.status!=='available'?'<span class="sty-st">'+statusIcon(it.status)+'</span>':'')+
    '</button>';
}
function chipRow(opts,sel,attr){
  return '<div class="sty-chips">'+opts.map(function(o){
    return '<button class="chip'+(sel===o[0]?' on':'')+'" data-'+attr+'="'+esc(o[0])+'">'+
      (o[2]?'<span>'+esc(o[2])+'</span> ':'')+esc(o[1])+'</button>';
  }).join('')+'</div>';
}
function multiChips(opts,selArr,attr){
  return '<div class="sty-chips">'+opts.map(function(o){
    const on=selArr.indexOf(o[0])>=0;
    return '<button class="chip'+(on?' on':'')+'" data-'+attr+'="'+esc(o[0])+'">'+
      (o[2]?'<span>'+esc(o[2])+'</span> ':'')+esc(o[1])+'</button>';
  }).join('')+'</div>';
}
function colorDots(colors){
  return '<span class="sty-cdots">'+colors.map(function(c){
    const def=COLORS.filter(function(x){ return x[0]===c; })[0];
    const bg=def?def[1]:'#999';
    return '<i style="background:'+esc(bg)+'"></i>';
  }).join('')+'</span>';
}

/* ================= VIEWS ================= */
const VIEWS={};

/* ---------- home ---------- */
VIEWS.home=function(body){
  const n=DB.items.length, no=DB.outfits.length, nf=favCount();
  const band=wxBand();
  body.innerHTML=
    '<div class="sty-hero"><div class="sty-greet">'+esc(t(greetKey()))+'</div>'+
    '<div class="sty-ask">'+esc(t('style.ask'))+'</div>'+
    '<button class="sty-cta" data-go="styleme"><span class="sty-clay">'+clayIcon('st-styleme','✨')+'</span> '+esc(t('style.styleMe'))+'</button>'+
    '<button class="sty-cta2" data-go="quick"><span class="sty-clay xs">'+clayIcon('st-styleme','⚡')+'</span> '+esc(t('style.whatWear'))+'</button>'+
    '<div class="sty-wxline">'+wxLabel()+' · '+esc(t('style.wx.'+band))+'</div></div>'+

    '<div class="sty-counts">'+
    '<div class="sty-count"><b data-count="'+n+'">0</b><span>'+esc(t('style.items'))+'</span></div>'+
    '<div class="sty-count"><b data-count="'+no+'">0</b><span>'+esc(t('style.outfits'))+'</span></div>'+
    '<div class="sty-count"><b data-count="'+nf+'">0</b><span>'+esc(t('style.favs'))+'</span></div></div>'+

    '<div class="sty-grid">'+
    menuCard('closet','st-closet','👗','style.myCloset','style.myClosetSub')+
    menuCard('runway','st-styleme','✨','style.rw.title','style.rw.sub')+
    menuCard('builder','st-builder','🧩','style.createLook','style.createLookSub')+
    menuCard('calendar','st-calendar','📅','style.calendar','style.calendarSub')+
    menuCard('laundry','st-laundry','🧺','style.laundry','style.laundrySub')+
    menuCard('insights','st-insights','📊','style.insights','style.insightsSub')+
    menuCard('packing','st-packing','🧳','style.packing','style.packingSub')+
    menuCard('settings','st-gear','⚙️','style.settings','style.settingsSub')+
    '</div>'+
    '<p class="hint" style="text-align:center">'+clayIcon('st-lock','🔒')+' '+esc(t('style.offline'))+'</p>';
  body.querySelectorAll('[data-go]').forEach(function(b){
    b.onclick=function(){ go(b.getAttribute('data-go')); };
  });
  /* PERF 2026-10-02: number tweens start after the entrance (~200ms) so they
     never compete with the slide-in for main-thread frames. */
  setTimeout(function(){ if(body.isConnected) countUp(body); },200);
};
function menuCard(v,icon,fb,titleK,subK){
  return '<button class="sty-menu" data-go="'+v+'"><span class="sty-clay">'+(icon?clayIcon(icon,fb):'<span class="sty-menu-em">'+esc(fb)+'</span>')+'</span>'+
    '<span class="sty-menu-t">'+esc(t(titleK))+'</span>'+
    '<span class="sty-menu-s">'+esc(t(subK))+'</span></button>';
}

/* ---------- closet ---------- */
let closetFilter={cat:'all',q:'',fav:false};
/* PERF 2026-10-02: grid renders the first 18 tiles synchronously; the rest
   stream in via rAF after first paint so a huge wardrobe never blocks open. */
const STY_GRID_FIRST=18, STY_GRID_CHUNK=36;
let styGridToken=0;
function itemTileHTML(it){
  const st=it.status&&it.status!=='available'?'<span class="sty-st" title="'+esc(t('style.st.'+it.status))+'">'+statusIcon(it.status)+'</span>':'';
  return '<button class="sty-item" data-item="'+esc(it.id)+'">'+photoTileHTML(it)+
    '<span class="sty-item-n">'+esc(it.name||catName(it.category))+'</span>'+
    '<span class="sty-item-m">'+colorDots(it.colors||[])+esc((it.colors||[]).join(' · '))+'</span>'+
    (it.favorite?'<span class="sty-fav">❤️</span>':'')+st+'</button>';
}
function streamGridItems(grid,items,from){
  const token=++styGridToken;
  function chunk(){
    if(token!==styGridToken||!grid.isConnected) return;
    const slice=items.slice(from,from+STY_GRID_CHUNK);
    if(!slice.length) return;
    const tmp=document.createElement('div');
    tmp.innerHTML=slice.map(itemTileHTML).join('');
    /* static snapshot: tmp.children is live and shrinks as we appendChild */
    const btns=Array.prototype.slice.call(tmp.children);
    btns.forEach(function(b){
      b.onclick=function(){ openItemSheet(b.getAttribute('data-item')); };
      grid.appendChild(b);
    });
    hydratePhotos(grid);
    from+=slice.length;
    if(from<items.length) requestAnimationFrame(chunk);
  }
  requestAnimationFrame(chunk);
}
VIEWS.closet=function(body){
  const cats=allCats();
  const f=closetFilter;
  let items=DB.items.slice();
  if(f.cat!=='all') items=items.filter(function(x){ return x.category===f.cat; });
  if(f.fav) items=items.filter(function(x){ return x.favorite; });
  if(f.q){
    const q=f.q.toLowerCase();
    items=items.filter(function(x){
      return (x.name||'').toLowerCase().indexOf(q)>=0||
        (x.tags||[]).join(' ').toLowerCase().indexOf(q)>=0||
        (x.colors||[]).join(' ').toLowerCase().indexOf(q)>=0||
        catName(x.category).toLowerCase().indexOf(q)>=0;
    });
  }
  items.sort(function(a,b){ return (b.favorite?1:0)-(a.favorite?1:0)||String(a.name).localeCompare(String(b.name)); });
  body.innerHTML=
    '<div class="sty-toolbar"><div class="field" style="margin:0;flex:1"><input class="input" id="styQ" placeholder="🔍 '+esc(t('style.searchPh'))+'" value="'+esc(f.q)+'"></div>'+
    '<button class="chip'+(f.fav?' on':'')+'" data-favtog>❤️</button></div>'+
    '<div class="sty-chips sty-cats">'+
    '<button class="chip'+(f.cat==='all'?' on':'')+'" data-cat="all">'+esc(t('style.all'))+'</button>'+
    cats.map(function(c){
      const n=DB.items.filter(function(x){ return x.category===c; }).length;
      return '<button class="chip'+(f.cat===c?' on':'')+'" data-cat="'+esc(c)+'">'+catIcon(c)+'<span>'+esc(catName(c))+'</span> <span class="chip-n">'+n+'</span></button>';
    }).join('')+'</div>'+
    (items.length?
      '<div class="sty-items" id="styItems">'+items.slice(0,STY_GRID_FIRST).map(itemTileHTML).join('')+'</div>'
    :'<div class="empty"><div class="big">'+clayIcon('st-closet','👗')+'</div><p>'+esc(t('style.empty'))+'</p>'+
      '<button class="btn btn-dark" data-go="add">'+clayIcon('st-hanger','➕')+' '+esc(t('style.add'))+'</button></div>')+
    '<button class="fab" data-go="add" aria-label="'+esc(t('style.add'))+'">＋</button>';
  hydratePhotos(body);
  const q=document.getElementById('styQ');
  if(q) q.addEventListener('input',function(){ f.q=q.value; paintSoft(); });
  body.querySelectorAll('[data-cat]').forEach(function(b){
    b.onclick=function(){ f.cat=b.getAttribute('data-cat'); paint(); };
  });
  const ft=body.querySelector('[data-favtog]');
  if(ft) ft.onclick=function(){ f.fav=!f.fav; paint(); };
  body.querySelectorAll('[data-go]').forEach(function(b){
    b.onclick=function(){ go(b.getAttribute('data-go')); };
  });
  body.querySelectorAll('[data-item]').forEach(function(b){
    b.onclick=function(){ openItemSheet(b.getAttribute('data-item')); };
  });
  const grid=document.getElementById('styItems');
  if(grid&&items.length>STY_GRID_FIRST) streamGridItems(grid,items,STY_GRID_FIRST);
};
let paintSoftT=null;
function paintSoft(){
  /* re-render closet grid without losing search focus */
  clearTimeout(paintSoftT);
  paintSoftT=setTimeout(function(){
    const body=document.getElementById('styBody');
    const qv=(document.getElementById('styQ')||{}).value||'';
    closetFilter.q=qv;
    const pos=qv.length;
    paint();
    const nq=document.getElementById('styQ');
    if(nq){ nq.focus(); try{ nq.setSelectionRange(pos,pos); }catch(e){} }
  },350);
}

/* ---------- item detail sheet ---------- */
function openItemSheet(id){
  const it=itemById(id); if(!it) return;
  const U=ui();
  U.openSheet(
    '<div class="sty-sheet-head"><div class="sty-sheet-photo" id="stySheetPhoto">'+photoTileHTML(it,'big')+'</div>'+
    '<div style="flex:1"><h2 style="margin:0 0 4px">'+esc(it.name||catName(it.category))+'</h2>'+
    '<div class="meta">'+catIcon(it.category)+' '+esc(catName(it.category))+'</div>'+
    '<div style="margin-top:6px">'+colorDots(it.colors||[])+' <span class="meta">'+esc((it.colors||[]).map(function(c){ return t('style.color.'+c); }).join(' · '))+'</span></div></div>'+
    '<button class="iconbtn" data-styfav>'+(it.favorite?'❤️':'🤍')+'</button></div>'+
    metaRow('style.seasons',(it.seasons||[]).map(function(s){ return t('style.season.'+s); }).join(' · ')||'—')+
    '<div class="kv"><span>'+esc(t('style.occasions'))+'</span><b>'+((it.occasions||[]).map(function(s){ return '<span class="sty-clay xs">'+occIcon(s)+'</span> '+esc(t('style.occ.'+s)); }).join(' · ')||'—')+'</b></div>'+
    ((it.tags||[]).length?'<div class="sty-chips">'+it.tags.map(function(g){ return '<span class="chip static">#'+esc(g)+'</span>'; }).join('')+'</div>':'')+
    '<div class="kv"><span>'+t('style.status')+'</span><b>'+statusIcon(it.status||'available')+' '+esc(t('style.st.'+(it.status||'available')))+'</b></div>'+
    (it.price?'<div class="kv"><span>'+clayIcon('st-pricetag','🏷️')+' '+t('style.price')+'</span><b>$'+esc(String(it.price))+'</b></div>':'')+
    '<div class="kv"><span>'+t('style.wornCount')+'</span><b>'+(it.wearCount||0)+'×'+(it.lastWorn?' · '+esc(fmtD(it.lastWorn)):'')+'</b></div>'+
    '<div class="field"><label>'+esc(t('style.status'))+'</label><div class="sty-chips" id="styStChips">'+
      STATUSES.map(function(s){ return '<button class="chip'+((it.status||'available')===s?' on':'')+'" data-st="'+s+'">'+statusIcon(s)+' '+esc(t('style.st.'+s))+'</button>'; }).join('')+'</div></div>'+
    '<div class="row" style="gap:8px;margin-top:12px">'+
    '<button class="btn btn-ghost btn-sm" data-styedit style="flex:1">✏️ '+esc(t('style.edit'))+'</button>'+
    '<button class="btn btn-ghost btn-sm" data-stydel style="flex:1;color:#F87171">🗑 '+esc(t('style.delete'))+'</button></div>'+
    ((it.status||'available')!=='available'?'<p class="hint">'+esc(t('style.laundryNote'))+'</p>':'')
  );
  hydratePhotos(document.getElementById('sheetHost')||document);
  document.querySelector('[data-styfav]').onclick=function(){
    it.favorite=!it.favorite; save(); U.closeSheet(); paint(); openItemSheet(id);
  };
  document.querySelectorAll('#styStChips [data-st]').forEach(function(b){
    b.onclick=function(){ it.status=b.getAttribute('data-st'); save(); U.closeSheet(); paint(); openItemSheet(id); };
  });
  document.querySelector('[data-styedit]').onclick=function(){ U.closeSheet(); openItemForm(id); };
  document.querySelector('[data-stydel]').onclick=function(){
    if(!confirm(t('style.confirmDel'))) return;
    DB.items=DB.items.filter(function(x){ return x.id!==id; });
    photoDel(id); save(); U.closeSheet(); paint(); U.toast('🗑 '+t('style.deleted'));
  };
}
function metaRow(k,v){
  return '<div class="kv"><span>'+esc(t(k))+'</span><b>'+esc(v)+'</b></div>';
}
function fmtD(iso){
  try{ return new Date(iso+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric'}); }
  catch(e){ return iso; }
}

/* ---------- add / edit item ---------- */
let pendingPhoto=null; /* dataURL waiting for save */
function openItemForm(id){
  const it=id?itemById(id):null;
  const U=ui();
  const cats=allCats();
  const sel={
    cat:it?it.category:'tops',
    colors:it?(it.colors||[]).slice():[],
    seasons:it?(it.seasons||[]).slice():[],
    occasions:it?(it.occasions||[]).slice():[]
  };
  pendingPhoto=null;
  U.openSheet(
    '<h2>'+(it?'✏️ ':'➕ ')+esc(t(it?'style.editItem':'style.addTitle'))+'</h2>'+
    '<div class="sty-photo-pick"><div class="sty-sheet-photo" id="styFormPhoto"><span class="sty-tile-em sty-clay">'+clayIcon('st-camera','📸')+'</span></div>'+
    '<div><button class="btn btn-ghost btn-sm" id="styTake">'+clayIcon('st-camera','📷')+' '+esc(t('style.takePhoto'))+'</button> '+
    '<button class="btn btn-ghost btn-sm" id="styUpload"><span class="sty-clay xs">'+clayIcon('st-photo','🖼️')+'</span> '+esc(t('style.uploadPhoto'))+'</button>'+
    '<p class="hint">'+esc(t('style.photoNote'))+'</p></div></div>'+
    '<input type="file" id="styFileCam" accept="image/*" capture="environment" style="display:none">'+
    '<input type="file" id="styFileUp" accept="image/*" style="display:none">'+
    '<div class="field"><label>'+esc(t('style.name'))+'</label>'+
    '<input class="input" id="styFName" maxlength="60" value="'+esc(it?(it.name||''):'')+'" placeholder="'+esc(t('style.namePh'))+'"></div>'+
    '<div class="field"><label>'+esc(t('style.category'))+'</label><div class="sty-chips" id="styFCats">'+
    cats.map(function(c){ return '<button class="chip'+(sel.cat===c?' on':'')+'" data-c="'+esc(c)+'">'+catIcon(c)+'<span>'+esc(catName(c))+'</span></button>'; }).join('')+'</div></div>'+
    '<div class="field"><label>'+esc(t('style.colors'))+'</label><div class="sty-chips" id="styFColors">'+
    COLORS.map(function(c){
      return '<button class="chip sty-colorchip'+(sel.colors.indexOf(c[0])>=0?' on':'')+'" data-c="'+c[0]+'">'+
        '<i style="background:'+c[1]+'"></i>'+esc(t('style.color.'+c[0]))+'</button>';
    }).join('')+'</div></div>'+
    '<div class="field"><label>'+esc(t('style.seasons'))+'</label><div class="sty-chips" id="styFSeasons">'+
    SEASONS.map(function(s){ return '<button class="chip'+(sel.seasons.indexOf(s)>=0?' on':'')+'" data-c="'+s+'">'+esc(t('style.season.'+s))+'</button>'; }).join('')+'</div></div>'+
    '<div class="field"><label>'+esc(t('style.occasions'))+'</label><div class="sty-chips" id="styFOcc">'+
    OCCASIONS.map(function(s){ return icChip('chip sty-icchip'+(sel.occasions.indexOf(s)>=0?' on':''),'data-c="'+s+'"',occIcon(s),t('style.occ.'+s)); }).join('')+'</div></div>'+
    '<div class="field"><label>'+esc(t('style.tags'))+'</label>'+
    '<input class="input" id="styFTags" maxlength="120" value="'+esc(it?(it.tags||[]).join(', '):'')+'" placeholder="'+esc(t('style.tagsPh'))+'"></div>'+
    '<div class="field"><label>'+esc(t('style.price'))+' ('+esc(t('style.optional'))+')</label>'+
    '<input class="input" id="styFPrice" inputmode="decimal" maxlength="12" value="'+esc(it&&it.price?String(it.price):'')+'" placeholder="'+esc(t('style.pricePh'))+'"></div>'+
    '<button class="btn btn-dark" id="styFSave" style="width:100%;margin-top:8px">💾 '+esc(t('style.save'))+'</button>'+
    '<p class="hint">🔒 '+esc(t('style.privateNote'))+'</p>'
  );
  if(it&&it.id) photoGet(it.id).then(function(url){
    const ph=document.getElementById('styFormPhoto');
    if(url&&ph) ph.innerHTML='<img src="'+esc(url)+'" alt="">';
  });
  const single=function(rootId,attr){
    document.querySelectorAll('#'+rootId+' [data-c]').forEach(function(b){
      b.onclick=function(){
        document.querySelectorAll('#'+rootId+' [data-c]').forEach(function(x){ x.classList.remove('on'); });
        b.classList.add('on'); sel[attr]=b.getAttribute('data-c');
      };
    });
  };
  const multi=function(rootId,attr){
    document.querySelectorAll('#'+rootId+' [data-c]').forEach(function(b){
      b.onclick=function(){
        const v=b.getAttribute('data-c'), arr=sel[attr], i=arr.indexOf(v);
        if(i>=0){ arr.splice(i,1); b.classList.remove('on'); }
        else{ arr.push(v); b.classList.add('on'); }
      };
    });
  };
  single('styFCats','cat'); multi('styFColors','colors'); multi('styFSeasons','seasons'); multi('styFOcc','occasions');
  const fc=document.getElementById('styFileCam'), fu=document.getElementById('styFileUp');
  /* iOS: input.click() must fire synchronously inside the tap handler */
  document.getElementById('styTake').onclick=function(){ if(HUB.perms) HUB.perms.nudge('camera'); fc.click(); };
  document.getElementById('styUpload').onclick=function(){ if(HUB.perms) HUB.perms.nudge('photos'); fu.click(); };
  const onFile=function(files){
    if(!files||!files.length) return;
    fileToPhoto(files[0]).then(function(url){
      if(!url){ U.toast(t('style.photoFail')); return; }
      pendingPhoto=url;
      const ph=document.getElementById('styFormPhoto');
      if(ph) ph.innerHTML='<img src="'+esc(url)+'" alt="">';
    });
  };
  fc.onchange=function(){ onFile(fc.files); fc.value=''; };
  fu.onchange=function(){ onFile(fu.files); fu.value=''; };
  document.getElementById('styFSave').onclick=function(){
    const name=document.getElementById('styFName').value.trim();
    const tags=document.getElementById('styFTags').value.split(',').map(function(s){ return s.trim(); }).filter(Boolean).slice(0,8);
    const priceRaw=document.getElementById('styFPrice').value.trim().replace(/[^0-9.]/g,'');
    const price=priceRaw?parseFloat(priceRaw):null;
    if(!name){ U.toast(t('style.needName')); return; }
    const finalize=function(photoId){
      if(it){
        it.name=name; it.category=sel.cat; it.colors=sel.colors; it.seasons=sel.seasons;
        it.occasions=sel.occasions; it.tags=tags; it.price=price;
      }else{
        DB.items.push({id:photoId||uid('it'),name:name,category:sel.cat,colors:sel.colors,
          seasons:sel.seasons,occasions:sel.occasions,tags:tags,status:'available',
          price:price,favorite:false,wearCount:0,lastWorn:null});
      }
      save(); U.closeSheet();
      if(it){ go('item',{id:it.id}); }else{ go('closet'); }
      U.toast('👗 '+t('style.saved'));
    };
    if(pendingPhoto){
      const pid=it?it.id:uid('it');
      photoPut(pid,pendingPhoto).then(function(){ finalize(it?null:pid); });
    }else finalize(null);
  };
}
VIEWS.add=function(body){ /* add opens the sheet right away over closet */
  body.innerHTML='<div class="empty"><div class="big">➕</div><p>'+esc(t('style.addTitle'))+'</p></div>';
  openItemForm(null);
};

/* ================= Style Me engine ================= */
/* vibe -> preferred colors / categories (soft boosts, never hard rules) */
const VIBE_MAP={
  minimal:{colors:['black','white','gray','beige','cream'],cats:['tops','bottoms']},
  feminine:{colors:['pink','red','cream','gold'],cats:['dresses','jewelry']},
  edgy:{colors:['black','silver','red'],cats:['jackets','shoes']},
  clean:{colors:['white','cream','navy'],cats:['tops']},
  soft:{colors:['pink','cream','beige','white'],cats:['sweaters','dresses']},
  bold:{colors:['red','yellow','orange','pink'],cats:['dresses','tops']},
  casual:{colors:[],cats:['basics','activewear','tops','bottoms']},
  professional:{colors:['navy','black','white','gray'],cats:['jackets','tops','bottoms']},
  streetwear:{colors:['black','white','denim','olive'],cats:['activewear','shoes','accessories']},
  comfortable:{colors:['gray','beige','cream','white'],cats:['sweaters','basics','activewear']}
};
const FEEL_MAP={
  comfortable:{colors:['gray','beige','cream'],cats:['sweaters','basics']},
  confident:{colors:['red','black','navy'],cats:['jackets','dresses']},
  cute:{colors:['pink','cream','yellow'],cats:['dresses','tops']},
  elegant:{colors:['black','navy','gold','silver'],cats:['dresses','jewelry']},
  relaxed:{colors:['gray','white','beige'],cats:['basics','sweaters']},
  professional:{colors:['navy','black','white'],cats:['tops','bottoms','jackets']}
};
function scoreItem(it,o){
  o=o||{};
  if(!it||it.archived) return -1;
  if(it.status!=='available') return -1; /* laundry/drycleaning/packed/borrowed excluded */
  if(o.excludeIds&&o.excludeIds.indexOf(it.id)>=0) return -1;
  let s=50;
  if(o.occasion){
    if((it.occasions||[]).indexOf(o.occasion)>=0) s+=30;
    else{
      const rule=OCC_RULES[o.occasion];
      if(rule){
        if(rule.avoid&&rule.avoid.indexOf(it.category)>=0) s-=30;
        if(rule.boost&&rule.boost.indexOf(it.category)>=0) s+=10;
      }
    }
  }
  if(o.wx&&o.wx!=='auto'){
    const wr=WX_RULES[o.wx];
    if(wr){
      if(wr.avoid&&wr.avoid.indexOf(it.category)>=0) s-=22;
      if(wr.prefer&&wr.prefer.indexOf(it.category)>=0) s+=8;
      if(wr.seasons&&it.seasons){
        if(it.seasons.some(function(x){ return wr.seasons.indexOf(x)>=0; })) s+=8;
        else s-=6;
      }
    }
  }
  const softBoost=function(map,key){
    const m=map[key]; if(!m) return;
    if(m.cats.indexOf(it.category)>=0) s+=6;
    if(it.colors&&it.colors.some(function(c){ return m.colors.indexOf(c)>=0; })) s+=6;
  };
  if(o.vibe) softBoost(VIBE_MAP,o.vibe);
  if(o.feel) softBoost(FEEL_MAP,o.feel);
  if(it.favorite) s+=5;
  /* recency: gently push down recently worn, don't hard-block small closets */
  if(it.lastWorn){
    const days=(Date.now()-new Date(it.lastWorn+'T12:00:00').getTime())/864e5;
    const dr=(DB.settings&&DB.settings.dontRepeat)||7;
    if(days<dr) s-=Math.round(30*(1-days/dr));
  }
  return s;
}
/* harmony of a color set, 0..100. 3-color rule, complementary accents, analogous ease */
const WHEEL=['r','o','y','g','b'];
function colorHarmony(colors){
  const fams=(colors||[]).map(function(c){ return HUE_FAM[c]||'n'; });
  const counts={};
  fams.forEach(function(f){ counts[f]=(counts[f]||0)+1; });
  if(counts.m) counts.m=0; /* multicolor handled as its own statement */
  const nonN=Object.keys(counts).filter(function(f){ return f!=='n'&&f!=='m'&&counts[f]>0; });
  let score=100;
  if(nonN.length>3) score-=(nonN.length-3)*25;
  /* complementary pair where one side is an accent (count 1) */
  nonN.forEach(function(f){
    const c=COMPLEMENT[f];
    if(c&&counts[c]>0&&(counts[f]===1||counts[c]===1)) score+=10;
  });
  /* analogous neighbors */
  for(let i=0;i<nonN.length;i++) for(let j=i+1;j<nonN.length;j++){
    const a=WHEEL.indexOf(nonN[i]), b=WHEEL.indexOf(nonN[j]);
    if(a>=0&&b>=0&&Math.abs(a-b)===1) score+=5;
  }
  return Math.max(0,Math.min(100,score));
}
/* slot fill order for a complete look */
const SLOT_CATS={
  core:[['dresses'],['tops'],['bottoms']],
  layer:[['jackets'],['sweaters']],
  shoes:[['shoes']],
  bag:[['bags']],
  extras:[['jewelry'],['accessories'],['seasonal']]
};
function styleMe(o){
  o=o||{};
  const pool=DB.items.filter(function(x){ return !x.archived&&x.status==='available'; });
  const scored=pool.map(function(it){ return {it:it,s:scoreItem(it,o)}; })
    .filter(function(x){ return x.s>0; })
    .sort(function(a,b){ return b.s-a.s; });
  if(!scored.length) return [];
  const chosen=[], chosenColors=[];
  const jitter=o.jitter? (Math.random()*8) : 0;
  const pickBest=function(cats){
    let best=null,bestScore=-1e9;
    scored.forEach(function(x){
      if(chosen.indexOf(x.it)>=0) return;
      if(cats.indexOf(x.it.category)<0) return;
      const before=colorHarmony(chosenColors);
      const after=colorHarmony(chosenColors.concat(x.it.colors||[]));
      const sc=x.s+(after-before)*0.8+Math.random()*jitter;
      if(sc>bestScore){ bestScore=sc; best=x.it; }
    });
    return best;
  };
  /* core: dress alone, or top+bottom */
  const dress=pickBest(['dresses']);
  const top=pickBest(['tops']), bottom=pickBest(['bottoms']);
  if(dress&&(!top||!bottom||(scoreItem(dress,o)>scoreItem(top,o)+scoreItem(bottom,o)-70))){
    chosen.push(dress); Array.prototype.push.apply(chosenColors,dress.colors||[]);
  }else{
    if(top){ chosen.push(top); Array.prototype.push.apply(chosenColors,top.colors||[]); }
    if(bottom){ chosen.push(bottom); Array.prototype.push.apply(chosenColors,bottom.colors||[]); }
  }
  /* layer only when it adds (cool/cold/rainy, or strong score) */
  const band=o.wx==='auto'?wxBand():o.wx;
  if(band==='cool'||band==='cold'||band==='rainy'){
    const layer=pickBest(['jackets','sweaters','seasonal']);
    if(layer){ chosen.push(layer); Array.prototype.push.apply(chosenColors,layer.colors||[]); }
  }
  ['shoes','bag','extras'].forEach(function(slot){
    const cats=slot==='extras'?['jewelry','accessories','seasonal']:(slot==='bag'?['bags']:['shoes']);
    const p=pickBest(cats);
    if(p){ chosen.push(p); Array.prototype.push.apply(chosenColors,p.colors||[]); }
  });
  const maxN=o.count||6;
  return buildOutfit(chosen.slice(0,maxN));
}
const SLOT_ORDER=['dresses','tops','bottoms','jackets','sweaters','shoes','bags','jewelry','accessories','seasonal','basics','activewear','swimwear','sleepwear'];
function buildOutfit(items){
  return (items||[]).slice().sort(function(a,b){
    return SLOT_ORDER.indexOf(a.category)-SLOT_ORDER.indexOf(b.category);
  });
}

/* ---------- shared result view ---------- */
function outfitResultHTML(items,ctx){
  ctx=ctx||{};
  const missing=ctx.missing||[];
  return '<div class="sty-hero"><div class="sty-greet">'+esc(t(greetKey()))+'</div>'+
    '<div class="sty-ask"><span class="sty-clay" style="width:24px;height:24px;vertical-align:-5px">'+clayIcon('st-styleme','✨')+'</span> '+esc(t('style.yourLook'))+'</div></div>'+
    (items.length?lookCardHTML(items,{big:true})
      :'<div class="empty"><div class="big">'+clayIcon('st-closet','👗')+'</div><p>'+esc(t('style.errNeedItems'))+'</p></div>')+
    (items.length?'<p class="hint" style="text-align:center">✨ '+esc(t('style.ownAll'))+'</p>':'')+
    missing.map(function(c){ return needSomethingHTML(c); }).join('')+
    (items.length?'<button class="btn btn-dark sty-cta celebrate" data-r="wear" style="width:100%"><span class="sty-clay" style="width:24px;height:24px;vertical-align:-5px">'+clayIcon('st-hanger','👗')+'</span> '+esc(t('style.wearThis'))+'</button>':'')+
    (items.length?'<button class="btn btn-ghost" data-r="runway" style="width:100%;margin-top:8px"><span class="sty-clay" style="width:22px;height:22px;vertical-align:-5px">'+clayIcon('st-styleme','✨')+'</span> '+esc(t('style.rw.viewBtn'))+'</button>':'')+
    '<button class="btn btn-ghost" data-r="another" style="width:100%;margin-top:8px">🔀 '+esc(t('style.tryAnother'))+'</button>'+
    '<button class="btn btn-ghost" data-r="save" style="width:100%;margin-top:8px">💾 '+esc(t('style.save'))+'</button>';
}
function bindOutfitResult(body,items,ctx){
  ctx=ctx||{};
  hydratePhotos(body); bindNeed(body);
  const again=body.querySelector('[data-r="another"]');
  if(again) again.onclick=function(){
    const ids=items.map(function(x){ return x.id; });
    const r=styleMe(Object.assign({},ctx.opts,{excludeIds:ids,jitter:12}));
    const useList=r.length?r:items;
    body.innerHTML=outfitResultHTML(useList,ctx);
    bindOutfitResult(body,useList,ctx);
  };
  const rwy=body.querySelector('[data-r="runway"]');
  if(rwy) rwy.onclick=function(){ go('runway',{opts:ctx.opts||{}}); };
  const wear=body.querySelector('[data-r="wear"]');
  if(wear) wear.onclick=function(ev){
    celebrate(ev);
    wearNow(items.map(function(x){ return x.id; }),ctx.name||t('style.todayName'));
    ui().toast('✨ '+t('style.logWorn'));
    setTimeout(function(){ go('calendar'); },700);
  };
  const save=body.querySelector('[data-r="save"]');
  if(save) save.onclick=function(){
    const o={id:uid('of'),name:ctx.name||t('style.todayName'),itemIds:items.map(function(x){ return x.id; }),
      occasion:ctx.opts?ctx.opts.occasion:'',vibe:ctx.opts?ctx.opts.vibe:'',favorite:false,created:Date.now()};
    DB.outfits.push(o); save();
    checkUnlock();
    ui().toast('💾 '+t('style.saved'));
  };
}
function openOutfitResult(items,opts){
  go('result',{items:items,opts:opts||{}});
}
VIEWS.result=function(body,params){
  const items=buildOutfit((params.items||[]).map(function(x){ return typeof x==='string'?itemById(x):x; }).filter(Boolean));
  const ctx={opts:params.opts||{},name:params.name};
  /* detect missing core slots for the market bridge */
  const cats=items.map(function(x){ return x.category; });
  const missing=[];
  if(cats.indexOf('dresses')<0&&(cats.indexOf('tops')<0||cats.indexOf('bottoms')<0)){
    if(cats.indexOf('tops')<0&&cats.indexOf('dresses')<0) missing.push('tops');
    else if(cats.indexOf('bottoms')<0&&cats.indexOf('dresses')<0) missing.push('bottoms');
  }
  if(cats.indexOf('shoes')<0) missing.push('shoes');
  body.innerHTML=outfitResultHTML(items,{opts:ctx.opts,name:ctx.name,missing:missing.slice(0,1)});
  bindOutfitResult(body,items,{opts:ctx.opts,name:ctx.name});
};

/* ---------- Style Me stepped flow ---------- */
let smState=null;
VIEWS.styleme=function(body){
  if(!smState) smState={step:0,occasion:null,vibe:null,feel:null,wx:'auto'};
  const sm=smState;
  const steps=[
    {k:'where',key:'occasion',opts:OCCASIONS,icon:function(o){return occIcon(o);}},
    {k:'whatVibe',key:'vibe',opts:VIBES,icon:function(o){return vibeIcon(o);}},
    {k:'howFeel',key:'feel',opts:FEELS,icon:function(o){return feelIcon(o);}},
    {k:'weatherQ',key:'wx',opts:['auto'].concat(WXBANDS),icon:function(v){return v==='auto'?wxAutoIcon():wxIcon(v);},label:function(v){return v==='auto'?t('style.set.weatherAuto'):t('style.wx.'+v);}}
  ];
  if(sm.step<4){
    const st=steps[sm.step];
    body.innerHTML=
      '<div class="sty-hero"><div class="sty-greet">'+esc(t(greetKey()))+'</div>'+
      '<div class="sty-ask">'+esc(t('style.'+st.k))+'</div>'+
      '<div class="sub" style="text-align:center">'+(sm.step+1)+' / 4 · '+esc(t('style.styleMe'))+'</div></div>'+
      '<div class="sty-chips" style="justify-content:center">'+
      st.opts.map(function(o){
        const lab=st.label?st.label(o):(st.key==='occasion'?t('style.occ.'+o):(st.key==='vibe'?t('style.vibe.'+o):t('style.feel.'+o)));
        return icChip('chip sty-bigchip sty-icchip','data-v="'+esc(o)+'"',st.icon(o),lab);
      }).join('')+'</div>';
    body.querySelectorAll('[data-v]').forEach(function(b){
      b.onclick=function(){
        sm[st.key]=b.getAttribute('data-v');
        if(sm.step<3){ sm.step++; paint(); }
        else{
          const r=styleMe({occasion:sm.occasion,vibe:sm.vibe,feel:sm.feel,wx:sm.wx,count:6});
          smState=null;
          openOutfitResult(r,{occasion:sm.occasion,vibe:sm.vibe,feel:sm.feel,wx:sm.wx});
        }
      };
    });
    return;
  }
};
/* ---------- What Should I Wear: 3 taps ---------- */
let qwState=null;
VIEWS.quick=function(body){
  if(!qwState) qwState={step:0,occasion:null,wx:'auto'};
  const q=qwState;
  if(q.step===0){
    body.innerHTML='<div class="sty-hero"><div class="sty-greet">'+esc(t(greetKey()))+'</div>'+
      '<div class="sty-ask"><span class="sty-clay xs">'+clayIcon('st-styleme','⚡')+'</span> '+esc(t('style.where'))+'</div></div>'+
      '<div class="sty-chips" style="justify-content:center">'+
      OCCASIONS.map(function(o){
        return icChip('chip sty-bigchip sty-icchip','data-v="'+esc(o)+'"',occIcon(o),t('style.occ.'+o));
      }).join('')+'</div>';
    body.querySelectorAll('[data-v]').forEach(function(b){
      b.onclick=function(){ q.occasion=b.getAttribute('data-v'); q.step=1; paint(); };
    });
    return;
  }
  body.innerHTML='<div class="sty-hero"><div class="sty-greet">'+esc(t(greetKey()))+'</div>'+
    '<div class="sty-ask"><span class="sty-clay xs">'+clayIcon('st-styleme','⚡')+'</span> '+esc(t('style.weatherQ'))+'</div></div>'+
    '<div class="sty-chips" style="justify-content:center">'+
    ['auto'].concat(WXBANDS).map(function(w){
      return icChip('chip sty-bigchip sty-icchip','data-v="'+esc(w)+'"',(w==='auto'?wxAutoIcon():wxIcon(w)),(w==='auto'?t('style.set.weatherAuto'):t('style.wx.'+w)));
    }).join('')+'</div>';
  body.querySelectorAll('[data-v]').forEach(function(b){
    b.onclick=function(){
      q.wx=b.getAttribute('data-v'); qwState=null;
      const r=styleMe({occasion:q.occasion,vibe:null,feel:null,wx:q.wx,count:5});
      openOutfitResult(r,{occasion:q.occasion,wx:q.wx});
    };
  });
};
/* ---------- outfit builder ---------- */
let bdState=null;
const BD_SLOTS=['tops','bottoms','dresses','jackets','sweaters','shoes','bags','jewelry','accessories'];
VIEWS.builder=function(body){
  if(!bdState) bdState={slots:{},pick:null};
  const bd=bdState;
  if(bd.pick){
    const cat=bd.pick;
    const items=DB.items.filter(function(x){ return !x.archived&&x.category===cat; });
    body.innerHTML='<div class="row" style="margin-bottom:10px"><button class="iconbtn" data-b="back">‹</button>'+
      '<h2 style="margin:0;flex:1;display:flex;align-items:center;gap:8px">'+catIcon(cat)+'<span>'+esc(catName(cat))+'</span></h2></div>'+
      (items.length?'<div class="sty-items">'+items.map(function(x){ return itemCardHTML(x,true); }).join('')+'</div>'
        :'<div class="empty"><div class="big">'+catIcon(cat)+'</div><p>'+esc(t('style.empty'))+'</p>'+
        '<button class="btn btn-dark" data-b="add">➕ '+esc(t('style.add'))+'</button></div>');
    hydratePhotos(body);
    body.querySelector('[data-b="back"]').onclick=function(){ bd.pick=null; paint(); };
    const addB=body.querySelector('[data-b="add"]');
    if(addB) addB.onclick=function(){ go('add'); };
    body.querySelectorAll('[data-pick]').forEach(function(b){
      b.onclick=function(){
        bd.slots[cat]=b.getAttribute('data-pick');
        bd.pick=null; paint();
      };
    });
    return;
  }
  body.innerHTML=
    '<div class="sty-hero"><div class="sty-ask"><span class="sty-clay" style="width:26px;height:26px;vertical-align:-6px">'+clayIcon('st-builder','🧩')+'</span> '+esc(t('style.createLook'))+'</div>'+
    '<div class="sub" style="text-align:center">'+esc(t('style.createLookSub'))+'</div></div>'+
    BD_SLOTS.map(function(cat){
      const it=bd.slots[cat]?itemById(bd.slots[cat]):null;
      return '<button class="sty-slot'+(it?' filled':'')+'" data-slot="'+esc(cat)+'">'+
        (it?photoTileHTML(it,'sm'):'<span class="sty-tile sm">'+catIcon(cat)+'</span>')+
        '<span class="grow"><b>'+esc(catName(cat))+'</b><br><span class="meta">'+esc(it?(it.name||''):'—')+'</span></span>'+
        '<span>›</span></button>';
    }).join('')+
    '<div class="field"><label>'+esc(t('style.name'))+'</label>'+
    '<input class="input" id="styOfName" maxlength="40" placeholder="'+esc(t('style.todayName'))+'"></div>'+
    '<button class="btn btn-dark sty-cta" id="styOfSave" style="width:100%">💾 '+esc(t('style.save'))+'</button>';
  body.querySelectorAll('[data-slot]').forEach(function(b){
    b.onclick=function(){ bd.pick=b.getAttribute('data-slot'); paint(); };
  });
  document.getElementById('styOfSave').onclick=function(){
    const ids=Object.keys(bd.slots).map(function(k){ return bd.slots[k]; }).filter(Boolean);
    if(!ids.length){ ui().toast('👗 '+t('style.errNeedItems')); return; }
    const name=document.getElementById('styOfName').value.trim()||t('style.todayName');
    const o={id:uid('of'),name:name,itemIds:ids,occasion:'',vibe:'',favorite:false,created:Date.now()};
    DB.outfits.push(o); save(); bdState=null;
    checkUnlock();
    ui().toast('💾 '+t('style.saved'));
    go('closet');
  };
};

/* ================= engagement: streaks, today's look, unlocks ================= */
function streak(){
  let n=0, d=new Date();
  for(;;){
    const iso=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
    if(DB.cal[iso]) n++; else break;
    d.setDate(d.getDate()-1);
    if(n>365) break;
  }
  return n;
}
/* auto occasion guess for Today's Look */
function guessOccasion(){
  const d=new Date(), day=d.getDay(), h=d.getHours();
  if(day===0||day===6) return h>=18?'dinner':'casual';
  if(h<9) return 'class';
  if(h<17) return 'work';
  if(h<20) return 'coffee';
  return 'dinner';
}
/* today's look: logged outfit wins; else auto-style from owned items */
function todayLook(){
  const iso=todayISO();
  const logged=DB.cal[iso];
  if(logged){
    const o=outfitById(logged);
    if(o) return {outfit:o,items:o.itemIds.map(itemById).filter(Boolean),logged:true};
  }
  const sug=styleMe({occasion:guessOccasion(),vibe:null,feel:null,wx:wxBand(),count:3});
  if(sug&&sug.length) return {outfit:null,items:sug,logged:false,occasion:guessOccasion()};
  return null;
}
const UNLOCK_AT=[1,5,10,25,50,100];
function checkUnlock(){
  const n=DB.outfits.length;
  if(UNLOCK_AT.indexOf(n)>=0){
    ui().toast('🎉 '+t('style.unlockN',{n:n}));
    return true;
  }
  return false;
}
/* log an outfit as worn today: wear counts, calendar, streak-safe */
function wearNow(itemIds,name){
  const iso=todayISO();
  let o=null;
  if(name){
    o={id:uid('of'),name:name,itemIds:itemIds.slice(),occasion:'',vibe:'',favorite:false,created:Date.now()};
    DB.outfits.push(o);
    checkUnlock();
  }
  itemIds.forEach(function(id){
    const it=itemById(id);
    if(it){ it.wearCount=(it.wearCount||0)+1; it.lastWorn=iso; }
  });
  if(o) DB.cal[iso]=o.id;
  save();
  return o;
}

/* ---------- outfit row / look card ---------- */
function lookCardHTML(items,opts){
  opts=opts||{};
  return '<div class="sty-look'+(opts.big?' big':'')+'">'+
    items.map(function(it){
      return '<div class="sty-look-it">'+photoTileHTML(it)+
        '<span>'+esc(it.name||catName(it.category))+'</span></div>';
    }).join('')+'</div>';
}

/* ---------- calendar ---------- */
let calCursor=null; /* {y,m} */
VIEWS.calendar=function(body){
  if(!calCursor){ const d=new Date(); calCursor={y:d.getFullYear(),m:d.getMonth()}; }
  const y=calCursor.y, m=calCursor.m;
  const first=new Date(y,m,1), startDay=first.getDay();
  const dim=new Date(y,m+1,0).getDate();
  const mName=first.toLocaleDateString(undefined,{month:'long',year:'numeric'});
  let cells='';
  for(let i=0;i<startDay;i++) cells+='<span class="sty-cal-d empty"></span>';
  for(let d=1;d<=dim;d++){
    const iso=y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');
    const oid=DB.cal[iso], o=oid?outfitById(oid):null;
    cells+='<button class="sty-cal-d'+(iso===todayISO()?' today':'')+(o?' has':'')+'" data-day="'+iso+'">'+
      '<span class="sty-cal-n">'+d+'</span>'+
      (o?'<span class="sty-cal-o">'+esc(lookEmoji(o))+'</span>':'')+'</button>';
  }
  const recent=Object.keys(DB.cal).sort().reverse().slice(0,8);
  body.innerHTML=
    '<div class="row between" style="margin-bottom:10px"><button class="iconbtn" data-calnav="-1">‹</button>'+
    '<h2 style="margin:0">'+esc(mName)+'</h2><button class="iconbtn" data-calnav="1">›</button></div>'+
    '<div class="sty-cal-head">'+['S','M','T','W','T','F','S'].map(function(d){ return '<span>'+d+'</span>'; }).join('')+'</div>'+
    '<div class="sty-cal">'+cells+'</div>'+
    '<h3 style="margin:16px 0 8px">🕘 '+esc(t('style.recentlyWorn'))+'</h3>'+
    (recent.length?recent.map(function(iso){
      const o=outfitById(DB.cal[iso]);
      if(!o) return '';
      return '<button class="item tight" data-rewear="'+esc(o.id)+'"><span style="font-size:22px">'+esc(lookEmoji(o))+'</span>'+
        '<div class="grow"><h3>'+esc(o.name)+'</h3><div class="meta">'+esc(fmtD(iso))+'</div></div>'+
        '<span class="meta">↻</span></button>';
    }).join(''):'<p class="sub">'+esc(t('style.noWornYet'))+'</p>');
  body.querySelectorAll('[data-calnav]').forEach(function(b){
    b.onclick=function(){
      let nm=calCursor.m+(+b.getAttribute('data-calnav'));
      calCursor={y:calCursor.y+Math.floor(nm/12),m:((nm%12)+12)%12};
      paint();
    };
  });
  body.querySelectorAll('[data-day]').forEach(function(b){
    b.onclick=function(){ openDaySheet(b.getAttribute('data-day')); };
  });
  body.querySelectorAll('[data-rewear]').forEach(function(b){
    b.onclick=function(){
      const o=outfitById(b.getAttribute('data-rewear'));
      if(o) openOutfitResult(o.itemIds.map(itemById).filter(Boolean),{name:o.name,rewear:true});
    };
  });
};
function lookEmoji(o){
  const first=itemById((o.itemIds||[])[0]);
  return first?catEmoji(first.category):'👗';
}
function openDaySheet(iso){
  const U=ui(), oid=DB.cal[iso], o=oid?outfitById(oid):null;
  U.openSheet(
    '<h2><span class="sty-clay" style="width:26px;height:26px;vertical-align:-6px">'+clayIcon('st-calendar','📅')+'</span> '+esc(fmtD(iso))+'</h2>'+
    (o?'<div class="card" style="margin-bottom:10px"><h3 style="margin:0 0 8px">'+esc(o.name)+'</h3>'+lookCardHTML(o.itemIds.map(itemById).filter(Boolean))+'</div>'
      :'<p class="sub">'+esc(t('style.noOutfitDay'))+'</p>')+
    '<div class="field"><label>'+esc(t('style.pickOutfit'))+'</label><div class="sty-chips" id="styDayPick">'+
    DB.outfits.map(function(x){ return '<button class="chip'+(oid===x.id?' on':'')+'" data-o="'+esc(x.id)+'">'+clayIcon('st-hanger','👗')+' '+esc(x.name)+'</button>'; }).join('')+
    (DB.outfits.length?'':'<span class="hint">'+esc(t('style.noOutfits'))+'</span>')+'</div></div>'+
    (o?'<button class="btn btn-ghost btn-sm" id="styDayClear" style="width:100%">🗑 '+esc(t('style.clearDay'))+'</button>':'')
  );
  document.querySelectorAll('#styDayPick [data-o]').forEach(function(b){
    b.onclick=function(){
      DB.cal[iso]=b.getAttribute('data-o');
      const of=outfitById(DB.cal[iso]);
      if(of) of.itemIds.map(itemById).filter(Boolean).forEach(function(it){ it.wearCount=(it.wearCount||0)+1; it.lastWorn=iso; });
      save(); U.closeSheet(); paint(); U.toast('📅 '+esc(t('style.daySaved')));
    };
  });
  const cl=document.getElementById('styDayClear');
  if(cl) cl.onclick=function(){ delete DB.cal[iso]; save(); U.closeSheet(); paint(); };
}

/* ---------- insights ---------- */
VIEWS.insights=function(body){
  const items=DB.items.filter(function(x){ return !x.archived; });
  const byCat={};
  items.forEach(function(x){ byCat[x.category]=(byCat[x.category]||0)+1; });
  const colorN={};
  items.forEach(function(x){ (x.colors||[]).forEach(function(c){ colorN[c]=(colorN[c]||0)+1; }); });
  const topColor=Object.keys(colorN).sort(function(a,b){ return colorN[b]-colorN[a]; })[0];
  const mostWorn=items.slice().sort(function(a,b){ return (b.wearCount||0)-(a.wearCount||0); })[0];
  const cutoff=daysAgoISO(90);
  const neverWorn=items.filter(function(x){ return !(x.wearCount>0)&&!(x.lastWorn&&x.lastWorn>=cutoff); });
  const priced=items.filter(function(x){ return x.price>0; });
  const origVal=priced.reduce(function(s,x){ return s+(+x.price||0); },0);
  /* animated progress ring: worn vs total */
  const wornN=items.filter(function(x){ return (x.wearCount||0)>0; }).length;
  const pct=items.length?Math.round(wornN/items.length*100):0;
  const circ=2*Math.PI*34;
  body.innerHTML=
    '<h2 style="margin-top:0"><span class="sty-clay">'+clayIcon('st-insights','📊')+'</span> '+esc(t('style.insights'))+'</h2>'+
    '<div class="sty-ins-top"><div class="sty-ring" style="--p:'+pct+';--c:'+circ+'">'+
    '<svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="34"/><circle class="fg" cx="40" cy="40" r="34"/></svg>'+
    '<b data-ringpct="'+pct+'">0%</b><span>'+esc(t('style.ins.worn'))+'</span></div>'+
    '<div class="sty-ins-facts">'+
    '<div><b data-count="'+items.length+'">0</b><span>'+esc(t('style.items'))+'</span></div>'+
    '<div><b>'+(topColor?t('style.color.'+topColor):'—')+'</b><span>'+esc(t('style.ins.topColor'))+'</span></div>'+
    '<div><b>'+esc(mostWorn?(mostWorn.name||''):'—')+'</b><span>'+esc(t('style.ins.mostWorn'))+'</span></div></div></div>'+
    '<h3>'+esc(t('style.ins.byCat'))+'</h3><div class="sty-ins-cats">'+
    Object.keys(byCat).sort(function(a,b){ return byCat[b]-byCat[a]; }).map(function(c){
      return '<div class="sty-ins-cat"><span class="sty-clay">'+clayIcon('st-'+c,catEmoji(c))+'</span>'+
        '<b>'+byCat[c]+'</b><span>'+esc(catName(c))+'</span></div>';
    }).join('')+'</div>'+
    (priced.length?'<div class="card" style="margin:14px 0"><h3 style="margin:0 0 6px"><span class="sty-clay" style="width:24px;height:24px;vertical-align:-5px">'+clayIcon('st-pricetag','💰')+'</span> '+esc(t('style.ins.value'))+'</h3>'+
      '<div class="kv"><span>'+esc(t('style.ins.origValue'))+'</span><b>$'+origVal.toLocaleString()+'</b></div>'+
      '<p class="hint">'+esc(t('style.ins.valueNote'))+'</p></div>':'')+
    '<h3><span class="sty-clay" style="width:24px;height:24px;vertical-align:-5px">'+clayIcon('st-hanger','😴')+'</span> '+esc(t('style.ins.neverWorn'))+' ('+neverWorn.length+')</h3>'+
    '<p class="sub">'+esc(t('style.ins.neverWornSub'))+'</p>'+
    '<div id="styNever">'+neverWorn.slice(0,20).map(function(x){
      return '<div class="item tight" data-never="'+esc(x.id)+'">'+photoTileHTML(x,'sm')+
        '<div class="grow"><h3>'+esc(x.name||catName(x.category))+'</h3><div class="meta">'+esc(catName(x.category))+'</div></div>'+
        '<button class="linklike" data-nact="keep" data-id="'+esc(x.id)+'">'+esc(t('style.ins.keep'))+'</button>'+
        '<button class="linklike" data-nact="sell" data-id="'+esc(x.id)+'">'+esc(t('style.ins.sell'))+'</button>'+
        '<button class="linklike" data-nact="donate" data-id="'+esc(x.id)+'">'+esc(t('style.ins.donate'))+'</button>'+
        '<button class="linklike" data-nact="archive" data-id="'+esc(x.id)+'">'+esc(t('style.ins.archive'))+'</button></div>';
    }).join('')+'</div>';
  hydratePhotos(body);
  body.querySelectorAll('[data-nact]').forEach(function(b){
    b.onclick=function(e){
      e.stopPropagation();
      const it=itemById(b.getAttribute('data-id')), act=b.getAttribute('data-nact');
      if(!it) return;
      if(act==='archive'){ it.archived=true; save(); paint(); ui().toast('📦 '+t('style.ins.archived')); }
      else if(act==='sell'){ close(); marketSearch(it.name+' '+catName(it.category)); ui().toast('🛍️ '+t('style.ins.sellNote')); }
      else if(act==='donate'){ ui().toast('💝 '+t('style.ins.donateNote')); const row=b.closest('[data-never]'); if(row) row.remove(); }
      else { const row=b.closest('[data-never]'); if(row) row.remove(); }
    };
  });
};
function clayIcon(name,fb){
  try{ if(HUB.icons&&HUB.icons.icon) return HUB.icons.icon(name,'sty-ico'); }catch(e){}
  return '<span class="sty-ico-fb">'+esc(fb||'👗')+'</span>';
}
/* category -> clay 3D icon with emoji fallback (no emoji-only category tiles) */
function catIcon(cat){ return clayIcon('st-'+cat, catEmoji(cat)); }

/* ---------- packing ---------- */
let packState={days:5,vibe:'casual',result:null};
VIEWS.packing=function(body){
  const ps=packState;
  body.innerHTML=
    '<h2 style="margin-top:0"><span class="sty-clay">'+clayIcon('st-packing','🧳')+'</span> '+esc(t('style.pack.title'))+'</h2>'+
    '<div class="field"><label>'+esc(t('style.pack.days'))+'</label>'+
    '<input class="input" id="styPackDays" inputmode="numeric" maxlength="2" value="'+ps.days+'" style="width:90px"></div>'+
    '<div class="field"><label>'+esc(t('style.pack.vibeT'))+'</label>'+
    '<div class="sty-chips">'+[['beach','st-occ-vacation',t('style.pack.beach')],['city','st-trip-city',t('style.pack.city')],['mountain','st-trip-mountain',t('style.pack.mountain')],['business','st-occ-interview',t('style.pack.business')]].map(function(o){
      return icChip('chip sty-icchip'+(ps.vibe===o[0]?' on':''),'data-pvibe="'+esc(o[0])+'"',clayIcon(o[1],'✈️'),o[2]);
    }).join('')+'</div></div>'+
    '<button class="btn btn-dark sty-cta" id="styPackGo" style="width:100%">🧳 '+esc(t('style.pack.make'))+'</button>'+
    '<div id="styPackOut" style="margin-top:14px">'+(ps.result?packResultHTML(ps.result):'')+'</div>';
  body.querySelectorAll('[data-pvibe]').forEach(function(b){
    b.onclick=function(){
      ps.vibe=b.getAttribute('data-pvibe');
      body.querySelectorAll('[data-pvibe]').forEach(function(x){ x.classList.toggle('on',x===b); });
    };
  });
  document.getElementById('styPackGo').onclick=function(){
    const d=Math.max(1,Math.min(30,parseInt(document.getElementById('styPackDays').value,10)||5));
    ps.days=d; ps.result=makePack(d,ps.vibe);
    document.getElementById('styPackOut').innerHTML=packResultHTML(ps.result);
  };
};
function makePack(days,vibe){
  const occMap={beach:'vacation',city:'casual',mountain:'casual',business:'work'};
  const occ=occMap[vibe]||'casual';
  const used=[], plan=[];
  for(let d=0;d<days;d++){
    const sug=styleMe({occasion:d===0||d===days-1?'airport':occ,vibe:null,feel:null,wx:vibe==='beach'?'hot':(vibe==='mountain'?'cool':wxBand()),exclude:used,count:5});
    const ids=(sug||[]).map(function(x){ return x.id; });
    ids.forEach(function(id){ if(used.indexOf(id)<0) used.push(id); });
    plan.push({day:d+1,travel:(d===0||d===days-1),occasion:d===0||d===days-1?'airport':occ,items:(sug||[])});
  }
  const counts={};
  used.forEach(function(id){ const it=itemById(id); if(it) counts[it.category]=(counts[it.category]||0)+1; });
  return {days:days,vibe:vibe,plan:plan,counts:counts,used:used};
}
function packResultHTML(r){
  return '<h3><span class="sty-clay xs">'+clayIcon('st-occ-airport','✈️')+'</span> '+esc(t('style.pack.plan'))+'</h3>'+
    r.plan.map(function(p){
      return '<div class="card" style="margin-bottom:10px"><div class="row between"><h3 style="margin:0">'+esc(t('style.pack.day')+' '+p.day)+(p.travel?' ✈️':'')+'</h3>'+
        '<span class="meta"><span class="sty-clay xs">'+occIcon(p.occasion)+'</span> '+esc(t('style.occ.'+p.occasion))+'</span></div>'+
        (p.items.length?lookCardHTML(p.items):'<p class="sub">'+esc(t('style.errNeedItems'))+'</p>')+'</div>';
    }).join('')+
    '<h3><span class="sty-clay">'+clayIcon('st-packing','🎒')+'</span> '+esc(t('style.pack.list'))+'</h3><div class="sty-chips">'+
    Object.keys(r.counts).map(function(c){
      return '<span class="chip static">'+catIcon(c)+'<span>'+esc(r.counts[c]+' × '+catName(c))+'</span></span>';
    }).join('')+'</div>';
}

/* ================= THE RUNWAY: 3D outfit card stack =================
   Full-screen outfit picker. Scored outfits (same styleMe engine, offline) are
   dealt as a 3D card stack with spring physics: swipe/drag with momentum or use
   the arrows to glide between looks. Each card shows the outfit's pieces on
   clay-icon tiles plus honest score chips (occasion / weather / color harmony).
   "Wear today" logs the look exactly like the result view does. */
let rwState=null;
function rwBuildLooks(opts){
  /* up to 6 looks, each forced onto fresh items via excludeIds so every
     card in the stack is a genuinely different outfit (best first) */
  const looks=[], used=[];
  for(let attempt=0;attempt<6&&looks.length<6;attempt++){
    const r=styleMe(Object.assign({},opts,{excludeIds:used,jitter:16,count:6}));
    if(!r||!r.length) break;
    looks.push(r);
    r.forEach(function(x){ used.push(x.id); });
  }
  return looks;
}
function rwScoreChips(items,opts){
  const occ=(opts&&opts.occasion)||'';
  const nOcc=occ?items.filter(function(x){ return (x.occasions||[]).indexOf(occ)>=0; }).length:0;
  const harm=colorHarmony(items.reduce(function(a,x){ return a.concat(x.colors||[]); },[]));
  const chips=[];
  if(occ) chips.push('<span class="chip static">'+esc(t('style.occ.'+occ))+' · '+nOcc+'/'+items.length+'</span>');
  chips.push('<span class="chip static">'+esc(t('style.wx.'+wxBand()))+'</span>');
  chips.push('<span class="chip static">'+esc(t('style.rw.harmony'))+' '+harm+'%</span>');
  return chips.join('');
}
function rwCardHTML(items,i,n,opts){
  return '<div class="rw-card rw-deal" data-i="'+i+'" aria-label="'+esc(t('style.rw.look'))+' '+(i+1)+'">'+
    '<div class="rw-num">'+esc(t('style.rw.look'))+' '+(i+1)+' / '+n+'</div>'+
    '<div class="rw-items">'+items.map(function(it){
      return '<div class="rw-it">'+photoTileHTML(it,'sm')+'<span>'+esc(it.name||catName(it.category))+'</span></div>';
    }).join('')+'</div>'+
    '<div class="rw-chips">'+rwScoreChips(items,opts)+'</div>'+
    '<button class="sty-cta rw-wear" data-rw-wear="'+i+'"><span class="sty-clay" style="width:24px;height:24px;vertical-align:-5px">'+clayIcon('st-hanger','👗')+'</span> '+esc(t('style.wearThis'))+'</button>'+
  '</div>';
}
/* rwLayout: 3D fan — transform-only, so it stays on the compositor at 60fps */
function rwLayout(stage,pos,animate){
  stage.classList.toggle('rw-anim',!!animate);
  const cards=stage.querySelectorAll('.rw-card');
  cards.forEach(function(cd){
    const i=+cd.getAttribute('data-i'), off=i-pos, a=Math.abs(off);
    cd.style.zIndex=String(100-Math.round(a*10));
    cd.style.visibility=a>2.4?'hidden':'visible';
    cd.style.opacity=a>2.4?'0':String(Math.max(0.05,1-a*0.3));
    const tx=Math.round(off*86), sc=1-Math.min(a,2.4)*0.09, tz=-Math.min(a,2.4)*130, ry=off*-6;
    cd.style.transform='translateX(calc(-50% + '+tx+'px)) translateZ('+tz+'px) rotateY('+ry+'deg) scale('+sc+')';
  });
  const dots=document.getElementById('styRwDots');
  if(dots) dots.querySelectorAll('i').forEach(function(d,k){ d.classList.toggle('on',Math.round(pos)===k); });
}
function rwBind(stage){
  const n=rwState.looks.length;
  const setPos=function(p,animate){
    rwState.pos=Math.max(0,Math.min(n-1,p));
    rwLayout(stage,rwState.pos,animate);
  };
  let drag=null, suppressClick=false;
  stage.addEventListener('pointerdown',function(e){
    if(e.target.closest&&e.target.closest('button')) return;
    drag={x0:e.clientX,p0:rwState.pos,moved:false,vx:0,lx:e.clientX,lt:performance.now()};
    stage.classList.add('rw-drag');
    try{ stage.setPointerCapture(e.pointerId); }catch(err){}
  });
  stage.addEventListener('pointermove',function(e){
    if(!drag) return;
    const dx=e.clientX-drag.x0;
    if(Math.abs(dx)>10) drag.moved=true;
    const now=performance.now();
    drag.vx=0.8*drag.vx+0.2*((e.clientX-drag.lx)/Math.max(1,now-drag.lt));
    drag.lx=e.clientX; drag.lt=now;
    const w=stage.clientWidth||320;
    setPos(drag.p0-dx/w,false);
  });
  const endDrag=function(e){
    if(!drag) return;
    const dgd=drag; drag=null;
    stage.classList.remove('rw-drag');
    if(!dgd.moved) return;
    suppressClick=true;
    setTimeout(function(){ suppressClick=false; },80);
    /* momentum: project position by release velocity, then spring to nearest card
       (pos-velocity is -vx/w: dragging left advances the stack) */
    const w=stage.clientWidth||320;
    const proj=dgd.p0-(e.clientX-dgd.x0)/w-dgd.vx*350/w;
    setPos(Math.round(proj),true);
  };
  stage.addEventListener('pointerup',endDrag);
  stage.addEventListener('pointercancel',function(){
    if(!drag) return;
    const p=drag.p0; drag=null;
    stage.classList.remove('rw-drag');
    setPos(p,true);
  });
  stage.addEventListener('click',function(e){
    if(suppressClick){ e.stopPropagation(); e.preventDefault(); }
  },true);
  const prev=document.getElementById('styRwPrev'), next=document.getElementById('styRwNext');
  if(prev) prev.onclick=function(){ setPos(Math.round(rwState.pos)-1,true); };
  if(next) next.onclick=function(){ setPos(Math.round(rwState.pos)+1,true); };
  const dots=document.getElementById('styRwDots');
  if(dots) dots.querySelectorAll('i').forEach(function(d){
    d.onclick=function(){ setPos(+d.getAttribute('data-d'),true); };
  });
  stage.querySelectorAll('[data-rw-wear]').forEach(function(b){
    b.onclick=function(ev){
      const items=rwState.looks[+b.getAttribute('data-rw-wear')]||[];
      celebrate(ev);
      wearNow(items.map(function(x){ return x.id; }),t('style.todayName'));
      ui().toast('✨ '+t('style.logWorn'));
      setTimeout(function(){ go('calendar'); },700);
    };
  });
}
VIEWS.runway=function(body,params){
  const opts=Object.assign({occasion:guessOccasion(),vibe:null,feel:null,wx:'auto'},(params&&params.opts)||{});
  const looks=rwBuildLooks(opts);
  rwState={looks:looks,opts:opts,pos:0};
  if(!looks.length){
    body.innerHTML='<div class="empty"><div class="big">'+clayIcon('st-styleme','✨')+'</div><p>'+esc(t('style.rw.empty'))+'</p>'+
      '<button class="btn btn-dark" data-go="add">'+clayIcon('st-hanger','➕')+' '+esc(t('style.add'))+'</button></div>';
    body.querySelector('[data-go]').onclick=function(){ go('add'); };
    return;
  }
  body.innerHTML=
    '<div class="sty-rw-head"><div><h2 style="margin:0;display:flex;align-items:center;gap:8px"><span class="sty-clay" style="width:30px;height:30px">'+clayIcon('st-styleme','✨')+'</span>'+esc(t('style.rw.title'))+'</h2>'+
    '<div class="sub">'+esc(t('style.rw.sub'))+'</div></div>'+
    '<button class="iconbtn" id="styRwShuffle" aria-label="'+esc(t('style.rw.shuffle'))+'"><span class="sty-clay" style="width:22px;height:22px">'+clayIcon('st-shuffle','🔀')+'</span></button></div>'+
    '<div class="sty-rw-stage" id="styRwStage" aria-roledescription="carousel">'+
    looks.map(function(){
      return '<div class="rw-skel"><div class="rw-skel-tiles"><i></i><i></i><i></i></div><div class="rw-skel-bar"></div><div class="rw-skel-bar short"></div></div>';
    }).join('')+'</div>'+
    '<div class="sty-rw-nav"><button class="iconbtn" id="styRwPrev" aria-label="‹">‹</button>'+
    '<div class="rw-dots" id="styRwDots">'+looks.map(function(_,i){ return '<i data-d="'+i+'"'+(i===0?' class="on"':'')+'></i>'; }).join('')+'</div>'+
    '<button class="iconbtn" id="styRwNext" aria-label="›">›</button></div>';
  const stage=document.getElementById('styRwStage');
  document.getElementById('styRwShuffle').onclick=function(){ paint(); };
  /* deal the stack: skeleton shimmer covers scoring, then cards spring in staggered */
  const reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  setTimeout(function(){
    if(!stage.isConnected||!rwState) return;
    stage.innerHTML=looks.map(function(items,i){ return rwCardHTML(items,i,looks.length,opts); }).join('');
    hydratePhotos(stage);
    rwBind(stage);
    const cards=stage.querySelectorAll('.rw-card');
    if(reduce){ cards.forEach(function(cd){ cd.classList.remove('rw-deal'); }); }
    else cards.forEach(function(cd,k){ cd.style.animationDelay=(k*0.09)+'s'; });
    rwLayout(stage,0,false);
  },reduce?60:420);
};

/* ---------- laundry mode ---------- */
const LAU_GROUPS=['laundry','drycleaning','borrowed','packed'];
VIEWS.laundry=function(body){
  const groups=LAU_GROUPS.map(function(s){
    return {st:s,items:DB.items.filter(function(x){ return (x.status||'available')===s&&!x.archived; })};
  });
  const total=groups.reduce(function(n,g){ return n+g.items.length; },0);
  body.innerHTML=
    '<h2 style="margin-top:0"><span class="sty-clay">'+clayIcon('st-laundry','🧺')+'</span> '+esc(t('style.laundry'))+'</h2>'+
    (total===0?'<p class="sub"><span class="sty-clay" style="width:22px;height:22px;vertical-align:-5px">'+clayIcon('st-laundry','🧺')+'</span> '+esc(t('style.lau.empty'))+'</p>':
      groups.filter(function(g){ return g.items.length; }).map(function(g){
        return '<h3 class="sty-laugrp">'+statusIcon(g.st)+' '+esc(t('style.st.'+g.st))+' <span class="meta">· '+g.items.length+'</span></h3>'+
          g.items.map(function(it){
            return '<div class="item tight sty-lrow">'+photoTileHTML(it,'sm')+
              '<div class="grow"><h3>'+esc(it.name||catName(it.category))+'</h3>'+
              '<div class="meta">'+catIcon(it.category)+' '+esc(catName(it.category))+'</div></div>'+
              '<button class="btn btn-ghost btn-sm" data-lau="'+esc(it.id)+'">'+clayIcon('st-check','✅')+' '+esc(t('style.lau.back'))+'</button></div>';
          }).join('');
      }).join(''));
  body.querySelectorAll('[data-lau]').forEach(function(b){
    b.onclick=function(){
      const it=itemById(b.getAttribute('data-lau'));
      if(it){ it.status='available'; save(); ui().toast('✅ '+t('style.lau.done')); paint(); }
    };
  });
  hydratePhotos(body);
};

/* ---------- settings ---------- */
VIEWS.settings=function(body){
  const s=DB.settings;
  body.innerHTML=
    '<h2 style="margin-top:0"><span class="sty-clay">'+clayIcon('st-gear','⚙️')+'</span> '+esc(t('style.settings'))+'</h2>'+
    '<div class="field"><label>'+esc(t('style.set.dontRepeat'))+'</label><div class="sty-chips" id="styDR">'+
    [3,7,14,30].map(function(d){ return '<button class="chip'+(s.dontRepeat===d?' on':'')+'" data-dr="'+d+'">'+esc(t('style.set.daysN',{n:d}))+'</button>'; }).join('')+'</div></div>'+
    '<div class="field"><label>'+esc(t('style.set.weather'))+'</label><div class="sty-chips" id="styWX">'+
    [['auto',wxAutoIcon(),t('style.set.weatherAuto')]].concat(WXBANDS.map(function(b){ return [b,wxIcon(b),t('style.wx.'+b)]; })).map(function(o){
      return '<button class="chip sty-icchip'+(s.wxMode===o[0]?' on':'')+'" data-wx="'+o[0]+'"><span class="sty-clay">'+o[1]+'</span><span>'+esc(o[2])+'</span></button>';
    }).join('')+'</div></div>'+
    '<div class="field"><label>'+esc(t('style.set.cats'))+'</label><div class="sty-chips">'+
    allCats().map(function(c){ return '<span class="chip static">'+catIcon(c)+'<span>'+esc(catName(c))+'</span></span>'; }).join('')+'</div>'+
    '<div class="row" style="gap:8px;margin-top:8px"><input class="input" id="styNewCat" maxlength="24" placeholder="'+esc(t('style.set.catPh'))+'" style="flex:1">'+
    '<button class="btn btn-ghost btn-sm" id="styAddCat">➕</button></div></div>'+
    '<div class="card" style="margin:14px 0"><h3 style="margin:0 0 6px"><span class="sty-clay" style="width:24px;height:24px;vertical-align:-5px">'+clayIcon('st-lock','🔒')+'</span> '+esc(t('style.set.privacy'))+'</h3>'+
    '<p class="sub" style="margin:0">'+esc(t('style.set.privacyNote'))+'</p></div>'+
    '<div class="card" style="margin:14px 0"><h3 style="margin:0 0 8px">🚧 '+esc(t('style.set.coming'))+'</h3>'+
    '<div class="sty-soon"><span>💬</span><span>'+esc(t('style.set.soonAsk'))+'</span><span class="meta">⏳</span></div>'+
    '<div class="sty-soon"><span class="sty-clay" style="width:22px;height:22px">'+clayIcon('st-camera','📸')+'</span><span>'+esc(t('style.set.soonShow'))+'</span><span class="meta">⏳</span></div>'+
    '<div class="sty-soon"><span>👥</span><span>'+esc(t('style.set.soonShare'))+'</span><span class="meta">⏳</span></div>'+
    '<p class="sub" style="margin:10px 0 0">'+esc(t('style.set.soonNote'))+'</p></div>'+
    '<div class="row" style="gap:8px"><button class="btn btn-ghost btn-sm" id="styExport" style="flex:1">📤 '+esc(t('style.set.export'))+'</button>'+
    '<button class="btn btn-ghost btn-sm" id="styReset" style="flex:1;color:#F87171">🗑 '+esc(t('style.set.reset'))+'</button></div>'+
    '<p class="hint">📵 '+esc(t('style.offline'))+'</p>';
  body.querySelectorAll('#styDR [data-dr]').forEach(function(b){
    b.onclick=function(){ s.dontRepeat=+b.getAttribute('data-dr'); save(); paint(); };
  });
  body.querySelectorAll('#styWX [data-wx]').forEach(function(b){
    b.onclick=function(){ s.wxMode=b.getAttribute('data-wx'); save(); paint(); };
  });
  document.getElementById('styAddCat').onclick=function(){
    const v=document.getElementById('styNewCat').value.trim().toLowerCase().replace(/[^a-z0-9-]/g,'').slice(0,24);
    if(!v) return;
    if(allCats().indexOf(v)<0){ DB.cats.push(v); save(); }
    paint(); ui().toast('➕ '+esc(v));
  };
  document.getElementById('styExport').onclick=function(){
    const blob=new Blob([JSON.stringify(DB,null,1)],{type:'application/json'});
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob); a.download='style-closet-backup.json'; a.click();
    setTimeout(function(){ URL.revokeObjectURL(a.href); },4000);
    ui().toast('📤 '+t('style.set.exported'));
  };
  document.getElementById('styReset').onclick=function(){
    if(!confirm(t('style.set.resetConfirm'))) return;
    DB=blank(); save(); close();
    ui().toast('🗑 '+t('style.set.resetDone'));
  };
}

/* ================= market bridge ================= */
function marketSearch(q){
  try{ HUB.showTab('market'); }catch(e){ return; }
  setTimeout(function(){
    const s=document.getElementById('mkSearch');
    if(s){ s.value=q; s.dispatchEvent(new Event('input',{bubbles:true})); try{ s.focus(); }catch(e){} }
  },600);
}
function needSomethingHTML(missingCat){
  return '<button class="btn btn-ghost btn-sm" data-need="'+esc(missingCat)+'" style="width:100%;margin-top:10px">🛍️ '+
    esc(t('style.need.title')+': '+catName(missingCat))+'</button>';
}
function bindNeed(root){
  root.querySelectorAll('[data-need]').forEach(function(b){
    b.onclick=function(){
      const c=b.getAttribute('data-need');
      close(); marketSearch(catName(c));
    };
  });
}

/* ================= Daily entry card ================= */
function cardHTML(){
  const n=DB.items.filter(function(x){ return !x.archived; }).length;
  const no=DB.outfits.length, st=streak();
  const look=todayLook();
  return '<section class="card sty-card" data-style-card>'+
    '<div class="sty-cardhead"><span class="sty-clay lg">'+clayIcon('st-closet','👗')+'</span>'+
    '<div style="flex:1"><div class="sty-cardtitle">'+esc(t('style.title'))+'</div>'+
    '<div class="sty-cardsub">'+esc(t('style.tagline'))+'</div></div>'+
    (st>1?'<div class="sty-streak" title="'+esc(t('style.streak'))+'"><span class="sty-clay xs">'+clayIcon('st-vibe-bold','🔥')+'</span> '+st+'</div>':'')+'</div>'+
    '<div class="sty-counts sm"><div class="sty-count"><b data-count="'+n+'">0</b><span>'+esc(t('style.items'))+'</span></div>'+
    '<div class="sty-count"><b data-count="'+no+'">0</b><span>'+esc(t('style.outfits'))+'</span></div>'+
    '<div class="sty-count"><b data-count="'+favCount()+'">0</b><span>'+esc(t('style.favs'))+'</span></div></div>'+
    (look&&look.items.length?
      '<button class="sty-today" data-act="today"><span class="sty-today-l">'+esc(t(look.logged?'style.todayLogged':'style.todayPick'))+'</span>'+
      '<span class="sty-today-items">'+look.items.slice(0,3).map(function(it){
        return '<span class="sty-today-it">'+catIcon(it.category)+' '+esc(it.name||catName(it.category))+'</span>';
      }).join('')+'</span><span class="sty-today-go">→</span></button>'
    :'')+
    '<div class="sty-quick">'+
    '<button class="sty-qbtn primary" data-act="styleme"><span class="sty-clay">'+clayIcon('st-styleme','✨')+'</span><span>'+esc(t('style.styleMe'))+'</span></button>'+
    '<button class="sty-qbtn" data-act="add"><span class="sty-clay">'+clayIcon('st-hanger','➕')+'</span><span>'+esc(t('style.add'))+'</span></button>'+
    '<button class="sty-qbtn" data-act="open"><span class="sty-clay">'+clayIcon('st-closet','👗')+'</span><span>'+esc(t('style.open'))+'</span></button>'+
    '</div></section>';
}
function bindCard(root){
  const card=root.querySelector('[data-style-card]');
  if(!card) return;
  countUp(card);
  card.querySelectorAll('[data-act]').forEach(function(b){
    b.onclick=function(){
      const a=b.getAttribute('data-act');
      if(a==='add') open('add');
      else if(a==='styleme') open('styleme');
      else if(a==='today') open('today');
      else open();
    };
  });
}
/* "today" view: full Today's Look with Wear This */
VIEWS.today=function(body){
  const look=todayLook();
  if(!look||!look.items.length){
    body.innerHTML='<div class="empty"><div class="big">'+clayIcon('st-hanger','👗')+'</div><p>'+esc(t('style.errNeedItems'))+'</p>'+
      '<button class="btn btn-dark" data-go="add">'+clayIcon('st-hanger','➕')+' '+esc(t('style.add'))+'</button></div>';
    body.querySelector('[data-go]').onclick=function(){ go('add'); };
    return;
  }
  body.innerHTML=
    '<div class="sty-hero"><div class="sty-greet">'+esc(t(greetKey()))+'</div>'+
    '<div class="sty-ask">'+esc(t(look.logged?'style.todayLogged':'style.todayPick'))+'</div>'+
    '<div class="sty-wxline">'+wxLabel()+'</div></div>'+
    lookCardHTML(look.items,{big:true})+
    '<p class="hint" style="text-align:center">✨ '+esc(t('style.ownAll'))+'</p>'+
    '<button class="btn btn-dark sty-cta celebrate" id="styWearToday" style="width:100%"><span class="sty-clay" style="width:24px;height:24px;vertical-align:-5px">'+clayIcon('st-hanger','👗')+'</span> '+esc(t('style.wearThis'))+'</button>'+
    '<button class="btn btn-ghost" id="styAnotherToday" style="width:100%;margin-top:8px">🔀 '+esc(t('style.tryAnother'))+'</button>';
  document.getElementById('styWearToday').onclick=function(ev){
    celebrate(ev);
    wearNow(look.items.map(function(x){ return x.id; }),look.outfit?null:t('style.todayName'));
    ui().toast('✨ '+t('style.logWorn'));
    setTimeout(paint,700);
  };
  document.getElementById('styAnotherToday').onclick=function(){ go('styleme'); };
};
/* satisfying completion burst on log buttons */
function celebrate(ev){
  try{
    const host=document.getElementById(ROOT_ID);
    if(!host) return;
    const r=(ev&&ev.currentTarget&&ev.currentTarget.getBoundingClientRect())||{left:innerWidth/2,top:innerHeight/2,width:0};
    for(let i=0;i<14;i++){
      const s=document.createElement('span');
      s.className='sty-pop';
      s.textContent=['✨','💫','🌟','💖'][i%4];
      s.style.left=(r.left+r.width/2+(Math.random()*120-60))+'px';
      s.style.top=(r.top+(Math.random()*40-20))+'px';
      host.appendChild(s);
      setTimeout(function(){ s.remove(); },1100);
    }
  }catch(e){}
}

/* ================= public API ================= */
HUB.style={
  cardHTML:cardHTML, bind:bindCard, open:open, close:close,
  todayLook:todayLook, streak:streak, wearNow:wearNow,
  _t:{
    load:load, blank:blank, styleMe:styleMe, buildOutfit:buildOutfit,
    colorHarmony:colorHarmony, wxBand:wxBand, guessOccasion:guessOccasion,
    get DB(){ return DB; }, setDB:function(d){ DB=d; save(); },
    scoreItem:scoreItem, catName:catName
  }
};
})();
