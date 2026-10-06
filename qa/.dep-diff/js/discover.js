/* HUB Discover tab: "What's happening around me?" — a discovery layer over
   listings, jobs and events. Map | List toggle + category filter chips.
   The map is MapLibre GL JS (free, no API keys) with OpenFreeMap vector
   tiles, 3D buildings + 3D terrain. Map pins use deterministic pseudo-coords
   around a labeled DEMO area (seed items have no real locations). */
(function(){
'use strict';
const CENTER=[32.7157,-117.1611]; // San Diego — demo area, labeled as such
const CENTER_LABEL='Demo area: San Diego';
const STYLE_LIGHT='https://tiles.openfreemap.org/styles/liberty';
const STYLE_DARK='https://tiles.openfreemap.org/styles/dark';
let map=null;
let mode='map'; // 'map' | 'list'
let cat='all';  // 'all' | 'market' | 'jobs' | 'events' | 'free' | 'study'
let hostEl=null;
let markers=[];
let geoStatus='pending'; // 'pending' | 'live' | 'fallback'
let liveCenter=null;     // [lat,lng] once geolocation succeeds
let tileErrorNoteShown=false;

/* deterministic hash -> stable pseudo coords per item id */
function hashStr(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
function pseudoCoord(id){
  const h1=hashStr('lat:'+id), h2=hashStr('lng:'+id);
  return [CENTER[0]+((h1%2000)/2000-0.5)*0.05, CENTER[1]+((h2%2000)/2000-0.5)*0.05];
}

/* deterministic pseudo distance (miles) mirroring market.js's own logic:
   real `dist` on user-posted listings, illustrative hash distance for seeds
   (their Sample badge discloses this). */
function distOfListing(l){
  if(typeof l.dist==='number'&&isFinite(l.dist)) return l.dist;
  return Math.round((0.2+(hashStr(String(l.id||l.title||'x'))%280)/100)*10)/10; // 0.2–3.0
}
/* haversine miles between two [lat,lng] pairs */
function haversineMi(a,b){
  const R=3958.8, dLa=(b[0]-a[0])*Math.PI/180, dLo=(b[1]-a[1])*Math.PI/180;
  const s=Math.sin(dLa/2)*Math.sin(dLa/2)+Math.cos(a[0]*Math.PI/180)*Math.cos(b[0]*Math.PI/180)*Math.sin(dLo/2)*Math.sin(dLo/2);
  return 2*R*Math.asin(Math.sqrt(s));
}
/* Market's current radius selection (its module var is private, so read the
   rendered control when the market tab has been opened; else its default). */
function marketRadius(){
  try{
    const on=document.querySelector('#mkRadius button.on');
    if(on) return on.dataset.r==='city'?'city':(+on.dataset.r||5);
  }catch(e){}
  return 5;
}
function scopeLabel(){ const r=marketRadius(); return r==='city'?'City-wide':'Within '+r+' mi'; }

const CATS=[
  {id:'all',   label:'All'},
  {id:'market',label:'🛒 Market'},
  {id:'jobs',  label:'💼 Jobs'},
  {id:'events',label:'🎉 Events'},
  {id:'free',  label:'🆓 Free stuff'},
  {id:'study', label:'📚 Study'},
];
const CAT_TITLE={market:'🛒 Market',jobs:'💼 Jobs',events:'🎉 Events',free:'🆓 Free stuff',study:'📚 Study'};
const PIN_COLOR={market:'#2563EB',jobs:'#B45309',events:'#FF5C38',free:'#1F7A4D',study:'#0D9488'}; /* orbit pins: market blue, jobs amber, events coral, free green, study teal — no purple */

function isStudyEvent(e){return ((e.emoji||'')+' '+(e.title||'')).includes('📚')||/study/i.test(e.title||'');}

/* same type-aware price label as market.js's priceLine, so the list and
   the map/discover surfaces never disagree about a listing's terms. */
function priceLabel(l,ui){
  if(l.type==='SELL') return ui.fmt$(l.price||0);
  if(l.type==='BUY') return l.price? 'Wants to buy · '+ui.fmt$(l.price) : 'Looking to buy';
  if(l.type==='SWAP') return 'Swap';
  if(l.type==='BORROW') return 'Borrow · '+(l.borrowFor||'ask me');
  return 'Free';
}

function collectItems(){
  const {store,ui}=HUB, st=store.state, out=[];
  for(const l of st.listings){
    if(ui.isBlocked(l.seller)) continue;
    if(l.type==='FREE') out.push({kind:'free',emoji:'🆓',title:l.title,meta:'Free · '+ui.timeAgo(l.createdAt),sample:l.sample,ref:l});
    else out.push({kind:'market',emoji:'🛒',title:l.title,meta:priceLabel(l,ui)+' · '+ui.timeAgo(l.createdAt),sample:l.sample,ref:l});
  }
  for(const j of st.jobs){
    if(ui.isBlocked(j.poster)) continue;
    out.push({kind:'jobs',emoji:'💼',title:j.title,meta:ui.fmt$(j.pay)+' · '+j.status+' · '+ui.timeAgo(j.createdAt),sample:j.sample,ref:j});
  }
  for(const e of st.events){
    const study=isStudyEvent(e);
    out.push({kind:study?'study':'events',emoji:e.emoji||'🎉',title:e.title,meta:(e.time||'')+(e.where?' · '+e.where:''),sample:e.sample,ref:e});
  }
  return out;
}

/* pins respect the Market radius logic: only items within the user's
   selected search radius appear on the map. */
function withinRadius(it){
  const r=marketRadius();
  if(r==='city') return true;
  if(it.kind==='market'||it.kind==='free') return distOfListing(it.ref)<=r;
  return haversineMi(liveCenter||CENTER,pseudoCoord(it.ref.id))<=r;
}
function visible(items){ const list=(cat==='all'?items:items.filter(i=>i.kind===cat)); return list.filter(withinRadius); }

/* tapping a pin goes to the item's existing destination — the same behavior
   as the list rows. (market.js / work.js keep their detail openers private,
   so discover reuses the tab navigation + the existing event sheet.) */
function openItemDetail(it){
  if(it.kind==='market'||it.kind==='free') HUB.showTab('market');
  else if(it.kind==='jobs') HUB.showTab('work');
  else openEventSheet(it.ref.id,it.kind);
}

/* ---------- 3D map ---------- */
function fallbackToList(box,why){
  const {ui}=HUB;
  box.outerHTML='<div class="map-fallback" role="note"><div class="big">🗺️</div>'+
    '<p><strong>3D map unavailable here</strong><br><span class="sub">'+ui.esc(why)+' Showing the list view instead — nothing is hidden.</span></p></div>'+
    '<div id="dvList"></div>';
}

function statusText(){
  if(geoStatus==='live') return '📍 Your location · demo pins only';
  if(geoStatus==='fallback') return '📍 Using community area — location unavailable';
  return '📍 Locating you…';
}

function setStatusChip(){
  const chip=document.getElementById('dvGeoChip');
  if(chip) chip.textContent=statusText();
}

function addUserDot(){
  if(!map||!liveCenter) return;
  try{
    const el=document.createElement('div');
    el.className='orbit-loc';
    el.title='Your location';
    new maplibregl.Marker({element:el,anchor:'center'}).setLngLat([liveCenter[1],liveCenter[0]]).addTo(map);
    map.jumpTo({center:[liveCenter[1],liveCenter[0]],zoom:14}); /* jumpTo: reliable even when base tiles are offline */
  }catch(e){}
}

function locateMe(){
  geoStatus='pending'; setStatusChip();
  if(!('geolocation' in navigator)){ geoStatus='fallback'; setStatusChip(); return; }
  try{
    navigator.geolocation.getCurrentPosition(
      function(pos){
        if(pos&&pos.coords){ liveCenter=[pos.coords.latitude,pos.coords.longitude]; geoStatus='live'; }
        else { geoStatus='fallback'; }
        setStatusChip(); addUserDot();
      },
      function(){ geoStatus='fallback'; setStatusChip(); },
      {enableHighAccuracy:true,timeout:8000,maximumAge:60000}
    );
  }catch(e){ geoStatus='fallback'; setStatusChip(); }
}

function addTerrain(){
  try{
    if(map.getSource('orbit-terrain')) return;
    map.addSource('orbit-terrain',{
      type:'raster-dem',
      tiles:['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
      tileSize:256,
      encoding:'terrarium',
      maxzoom:14,
      attribution:'Terrain: <a href="https://registry.opendata.aws/terrain-tiles/">AWS Terrain Tiles</a>'
    });
    map.setTerrain({source:'orbit-terrain',exaggeration:1.25});
  }catch(e){}
}

function addSky(){
  try{
    const dark=document.body.classList.contains('dark');
    map.setSky(dark?{
      'sky-color':'#0D100A','horizon-color':'#1B2115','fog-color':'#101408',
      'sky-horizon-blend':0.6,'horizon-fog-blend':0.5,'fog-ground-blend':0.12,'atmosphere-blend':0.6
    }:{
      'sky-color':'#8FC3F0','horizon-color':'#F2F6FB','fog-color':'#DBE7F3',
      'sky-horizon-blend':0.6,'horizon-fog-blend':0.5,'fog-ground-blend':0.1,'atmosphere-blend':0.6
    });
  }catch(e){}
}

/* 3D buildings on the openmaptiles `building` source-layer.
   The liberty style ships its own `building-3d`; only add ours when missing
   (e.g. the dark style), with height interpolated by zoom. */
function addBuildings3D(){
  try{
    if(map.getLayer('building-3d')||map.getLayer('orbit-buildings-3d')) return;
    const dark=document.body.classList.contains('dark');
    const layers=map.getStyle().layers||[];
    const labelLayer=layers.find(l=>l.type==='symbol'&&l.layout&&l.layout['text-field']);
    map.addLayer({
      id:'orbit-buildings-3d',
      type:'fill-extrusion',
      source:'openmaptiles',
      'source-layer':'building',
      minzoom:14,
      paint:{
        'fill-extrusion-color': dark?'#232B1E':'#D8DCCB',
        'fill-extrusion-height':['interpolate',['linear'],['zoom'],14,0,15,['coalesce',['get','render_height'],12]],
        'fill-extrusion-base':['coalesce',['get','render_min_height'],0],
        'fill-extrusion-opacity':0.85
      }
    },labelLayer&&labelLayer.id);
  }catch(e){}
}

function webglOK(){
  try{
    const c=document.createElement('canvas');
    return !!(c.getContext('webgl2')||c.getContext('webgl'));
  }catch(e){ return false; }
}

function initMap(items){
  const box=document.getElementById('dvMap');
  if(!box) return;
  if(typeof maplibregl==='undefined'||!webglOK()){
    fallbackToList(box,'The map library did not load, or this browser has no WebGL.');
    renderList(document.getElementById('dvList'),visible(collectItems()));
    return;
  }
  markers=[];
  tileErrorNoteShown=false;
  const dark=document.body.classList.contains('dark');
  try{
    map=new maplibregl.Map({
      container:'dvMap',
      style: dark?STYLE_DARK:STYLE_LIGHT,
      center:[CENTER[1],CENTER[0]],
      zoom:13.5,
      pitch:55,
      bearing:0,
      dragRotate:true,
      touchPitch:true,
      attributionControl:{compact:true}
    });
  }catch(e){
    fallbackToList(box,'The 3D map could not start here.');
    renderList(document.getElementById('dvList'),visible(collectItems()));
    return;
  }
  map.addControl(new maplibregl.NavigationControl({visualizePitch:true}),'top-right');

  /* offline/degraded tiles: say so honestly, keep pins working */
  map.on('error',function(){
    if(tileErrorNoteShown) return;
    tileErrorNoteShown=true;
    const chip=document.getElementById('dvGeoChip');
    if(chip) chip.textContent+=' · base tiles offline — pins still work';
  });

  map.on('load',function(){
    addTerrain();
    addSky();
    addBuildings3D();
  });
  locateMe(); /* don't wait for style load — geolocation must work even on slow/offline tiles */

  const pts=[];
  for(const it of items){
    const ll=pseudoCoord(it.ref.id); // [lat,lng]
    pts.push([ll[1],ll[0]]);
    try{
      const el=document.createElement('div');
      el.className='orbit-pin';
      el.title=(it.emoji+' '+it.title)+(it.sample?' (Sample)':'');
      el.innerHTML='<span class="hub-pin" style="--pin:'+(PIN_COLOR[it.kind]||'#2563EB')+'"></span>';
      el.addEventListener('click',function(ev){ ev.stopPropagation(); openItemDetail(it); });
      const m=new maplibregl.Marker({element:el,anchor:'center'}).setLngLat([ll[1],ll[0]]).addTo(map);
      markers.push(m);
    }catch(e){}
  }
  if(pts.length>1){
    try{
      const b=pts.reduce(function(bb,p){return bb.extend(p);},new maplibregl.LngLatBounds(pts[0],pts[0]));
      const cam=map.cameraForBounds(b,{padding:56,maxZoom:15});
      if(cam) map.jumpTo({center:cam.center,zoom:cam.zoom}); /* jumpTo, not fitBounds: animated moves never run when base tiles fail to load */
    }catch(e){}
  }
  setTimeout(function(){ try{ map.resize(); }catch(e){} },80);
}

function renderList(container,items){
  const {ui}=HUB;
  const order=['market','jobs','events','free','study'];
  let html='';
  for(const k of order){
    const group=items.filter(i=>i.kind===k);
    if(!group.length) continue;
    html+='<h2 style="margin:14px 0 8px">'+ui.esc(CAT_TITLE[k])+'</h2>';
    for(const it of group){
      const act=(k==='market'||k==='free')?'market':(k==='jobs'?'work':'sheet');
      html+='<div class="item" data-act="'+act+'" data-id="'+ui.esc(it.ref.id)+'" data-kind="'+k+'" role="button" tabindex="0">'+
        '<div class="grow"><h3>'+ui.esc(it.emoji+' '+it.title)+'</h3><div class="meta">'+ui.esc(it.meta)+'</div></div>'+
        ui.sampleBadge(it.sample)+'<span style="font-size:20px;color:var(--faint)">›</span></div>';
    }
  }
  if(!html) html='<div class="empty"><span class="empty-ico">'+HUB.icons.icon('nav-discover')+'</span><h3>Nothing in this category yet</h3><p class="sub">Try another category — or post the first listing yourself.</p><button class="btn btn-primary btn-sm" id="dvEmptyGo">Post in Market →</button></div>';
  container.innerHTML=html;
  const eg=container.querySelector('#dvEmptyGo'); if(eg) eg.onclick=()=>HUB.showTab('market');
  container.querySelectorAll('.item').forEach(el=>{
    const go=()=>{
      const act=el.dataset.act, id=el.dataset.id, kind=el.dataset.kind;
      if(act==='market') HUB.showTab('market');
      else if(act==='work') HUB.showTab('work');
      else openEventSheet(id,kind);
    };
    el.onclick=go;
    el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}};
  });
}

function openEventSheet(id,kind){
  const {store,ui}=HUB;
  const e=store.find('events',id);
  if(!e) return;
  ui.openSheet(
    '<h2>'+ui.esc(e.title)+'</h2>'+
    '<div class="kv"><span>When</span><b>'+ui.esc(e.time||'—')+'</b></div>'+
    '<div class="kv"><span>Where</span><b>'+ui.esc(e.where||'—')+'</b></div>'+
    '<div class="kv"><span>Type</span><b>'+ui.esc(CAT_TITLE[kind]||'Event')+'</b></div>'+
    '<div style="margin-top:10px">'+ui.sampleBadge(e.sample)+'</div>'+
    '<p class="hint">Pin location is a demo placeholder, not a real venue position.</p>'
  );
}

function render(el){
  hostEl=el;
  const {ui}=HUB;
  if(map){try{map.remove();}catch(e){} map=null;}
  markers=[];
  geoStatus='pending'; liveCenter=null;
  const items=visible(collectItems());
  const chips=CATS.map(c=>'<button class="chip'+(cat===c.id?' on':'')+'" data-cat="'+c.id+'">'+c.label+'</button>').join('');
  el.innerHTML=
    '<h1>Discover</h1><p class="sub" style="margin:4px 0 12px">What\'s happening around you</p>'+
    '<div class="seg" id="dvSeg"><button data-mode="map" class="'+(mode==='map'?'on':'')+'">🗺️ Map</button>'+
    '<button data-mode="list" class="'+(mode==='list'?'on':'')+'">📋 List</button></div>'+
    '<div class="chips">'+chips+'</div>'+
    '<div class="demo-note">📍 '+ui.esc(CENTER_LABEL)+' · '+ui.esc(scopeLabel())+' — demo pins only.</div>'+
    (mode==='map'?'<div class="mapbox" id="dvMapWrap"><div class="mapbox-inner" id="dvMap"></div><div class="map-status" id="dvGeoChip">📍 Locating you…</div></div>':'<div id="dvList"></div>');
  el.querySelectorAll('#dvSeg button').forEach(b=>{b.onclick=()=>{mode=b.dataset.mode;render(hostEl);};});
  el.querySelectorAll('.chip').forEach(b=>{b.onclick=()=>{cat=b.dataset.cat;render(hostEl);};});
  if(mode==='map') initMap(items);
  else renderList(el.querySelector('#dvList'),items);
}

HUB.views=HUB.views||{};
HUB.views.discover={render:render};
})();
