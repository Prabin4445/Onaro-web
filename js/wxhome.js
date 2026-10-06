/* HUB HOME weather: a car-dashboard strip (Today + Tomorrow) sitting right
   below the Appointments card; tap it for the full glass detail view.
   Data flows through the shared HUB.wx layer (real Open-Meteo, free,
   no key); location + unit prefs stay in this browser. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
const ui=function(){ return HUB.ui; };
const wx=function(){ return HUB.wx; };
function esc(s){ return ui().esc(s); }

/* stylesheet injection — keeps the index.html edit surface to script lines */
(function(){
  if(document.querySelector('link[data-wx-css]')) return;
  const l=document.createElement('link');
  l.rel='stylesheet'; l.href='css/wx.css'; l.setAttribute('data-wx-css','1');
  document.head.appendChild(l);
})();

/* ---------- the car-dashboard strip ---------- */
function dayCell(dayLbl, code, big, hi, lo, rainP){
  const w=wx();
  return '<div class="wxdash-day">'+
    '<span class="wxdash-dlbl">'+esc(dayLbl)+'</span>'+
    '<span class="wxdash-ico">'+w.signal(code)+'</span>'+
    '<span class="wxdash-tmp">'+w.temp(big)+'</span>'+
    '<span class="wxdash-sub">'+esc(t('daily.hiLo',{h:w.temp(hi),l:w.temp(lo)}))+'</span>'+
    '<span class="wxdash-sub wxdash-rain">🌧️ '+(rainP||0)+'%</span>'+
  '</div>';
}
function stripInner(){
  const w=wx(); if(!w) return '';
  const l=w.loc();
  if(!l) return '<span class="wxdash-set">🌦️ '+esc(t('wx.setLoc'))+' <span class="wxdash-chev">›</span></span>';
  const d=w.data();
  if(d===null||d===undefined) return '<span class="wxdash-load">⏳ '+esc(t('daily.wxLoading'))+'</span>';
  if(d===false) return '<span class="wxdash-set">🌦️ '+esc(t('daily.wxFail'))+' <span class="wxdash-chev">›</span></span>';
  const day=d.daily, c=d.current;
  return dayCell(t('daily.today'), c.weather_code, c.temperature_2m,
      day.temperature_2m_max[0], day.temperature_2m_min[0], day.precipitation_probability_max[0])+
    '<div class="wxdash-sep"></div>'+
    dayCell(t('wx.tomorrow'), day.weather_code[1], day.temperature_2m_max[1],
      day.temperature_2m_max[1], day.temperature_2m_min[1], day.precipitation_probability_max[1])+
    '<span class="wxdash-chev">›</span>';
}
function stripHTML(){
  return '<button class="wxdash" id="wxStrip" aria-label="'+esc(t('daily.weather'))+'">'+stripInner()+'</button>';
}
function paintStrip(){
  const el=document.getElementById('wxStrip'); if(!el) return;
  el.innerHTML=stripInner();
}
/* one-shot: paint from cache now, then live-fill when the fetch lands */
function refresh(){
  const w=wx(); if(!w) return;
  if(!w.loc()){ paintStrip(); return; }
  w.refresh(paintStrip);
}
function bind(el){
  const s=el.querySelector('#wxStrip'); if(!s||s.dataset.wxbound) return;
  s.dataset.wxbound='1';
  s.addEventListener('click',function(){ openDetail(); });
  s.addEventListener('keydown',function(e){
    if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openDetail(); }
  });
}

/* ---------- the glass detail view ---------- */
function detailBodyHTML(d){
  const w=wx();
  if(d===null||d===undefined) return '<div class="sub" style="padding:18px 0">⏳ '+esc(t('daily.wxLoading'))+'</div>';
  if(d===false||!d.current)
    return '<div class="empty"><span class="empty-ico">🌦️</span><p class="sub">'+esc(t('daily.wxFail'))+'</p>'+
      '<button class="btn btn-ghost btn-sm" id="wxdRetry">'+esc(t('common.retry'))+'</button></div>';
  const c=d.current, g=w.group(c.weather_code), day=d.daily, today=0;
  const hi=w.temp(day.temperature_2m_max[today]), lo=w.temp(day.temperature_2m_min[today]);
  /* hourly: next 12 entries from now */
  let h0=0;
  try{
    const times=d.hourly.time, nowIso=new Date().toISOString().slice(0,13);
    for(let i=0;i<times.length;i++){ if(times[i].slice(0,13)>=nowIso){ h0=i; break; } }
  }catch(e){}
  let hours='';
  for(let i=h0;i<Math.min(h0+12,(d.hourly.time||[]).length);i++){
    const hg=w.group(d.hourly.weather_code[i]);
    const hh=d.hourly.time[i].slice(11,16);
    hours+='<div class="wxh"><div class="sub">'+esc(hh)+'</div><div style="font-size:22px">'+hg[2]+'</div><div><b>'+w.temp(d.hourly.temperature_2m[i])+'</b></div>'+
      '<div class="sub" style="color:var(--info)">'+(d.hourly.precipitation_probability[i]||0)+'%</div></div>';
  }
  let week='';
  const days=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  for(let i=0;i<Math.min(7,(day.time||[]).length);i++){
    const dg=w.group(day.weather_code[i]);
    const dt=new Date(day.time[i]+'T12:00:00');
    const lbl=i===0?t('daily.today'):(i===1?t('wx.tomorrow'):days[dt.getDay()]);
    week+='<div class="row between" style="padding:8px 2px;border-top:1px solid var(--line)">'+
      '<span style="width:72px">'+esc(lbl)+'</span><span style="font-size:20px">'+dg[2]+'</span>'+
      '<span class="sub">'+esc(t('daily.'+dg[1]))+'</span>'+
      '<span><b>'+w.temp(day.temperature_2m_max[i])+'</b> <span class="sub">'+w.temp(day.temperature_2m_min[i])+'</span></span>'+
      '<span class="sub" style="color:var(--info);width:44px;text-align:right">'+(day.precipitation_probability_max[i]||0)+'%</span></div>';
  }
  return '<div class="wxnow"><div><div class="wxbig">'+w.temp(c.temperature_2m)+'</div>'+
      '<div><span style="font-size:20px">'+g[2]+'</span> <b>'+esc(t('daily.'+g[1]))+'</b></div>'+
      '<div class="sub">'+esc(t('daily.hiLo',{h:hi,l:lo})+' · '+t('daily.feels',{v:w.temp(c.apparent_temperature)}))+'</div></div>'+
      '<div class="wxmeta"><div>💧 '+esc(t('daily.humidity'))+' <b>'+c.relative_humidity_2m+'%</b></div>'+
      '<div>💨 '+esc(t('daily.wind'))+' <b>'+Math.round(c.wind_speed_10m)+' '+(w.unit()==='f'?'mph':'km/h')+'</b></div>'+
      '<div>🌧️ '+esc(t('daily.rain',{p:day.precipitation_probability_max[today]||0}))+'</div></div></div>'+
    '<h3 style="margin:14px 0 6px">'+esc(t('daily.wxHourly'))+'</h3><div class="wxstrip">'+hours+'</div>'+
    '<h3 style="margin:14px 0 4px">'+esc(t('daily.wxWeek'))+'</h3>'+week+
    '<p class="hint" style="margin-top:10px">'+esc(t('daily.wxBy'))+'</p>';
}
function paintDetailBody(){
  const w=wx(), box=document.getElementById('wxdBody'); if(!box||!w) return;
  box.innerHTML=detailBodyHTML(w.data());
  w.refresh(function(d){
    const b=document.getElementById('wxdBody'); if(!b) return;
    b.innerHTML=detailBodyHTML(d);
    const rb=document.getElementById('wxdRetry'); if(rb) rb.onclick=function(){ paintDetailBody(); };
  });
  const rb0=document.getElementById('wxdRetry'); if(rb0) rb0.onclick=function(){ paintDetailBody(); };
}
function openDetail(){
  const w=wx(), U=ui(), l=w.loc(), u=w.unit();
  U.openSheet(
    '<div class="wxd-crystal"><div class="row between"><h2>🌦️ '+esc(t('daily.weather'))+'</h2>'+
    '<button class="chip'+(u==='c'?' on':'')+'" id="wxdUnit" aria-label="°C/°F">°'+u.toUpperCase()+'</button></div>'+
    '<div class="askbox" style="margin:10px 0"><input class="input" id="wxdIn" placeholder="'+esc(t('daily.wxSearchPh'))+'" value="'+esc(l?l.name:'')+'">'+
    '<button class="btn btn-dark btn-sm" id="wxdGo">🔍</button></div>'+
    '<button class="btn btn-ghost btn-sm" id="wxdGps" style="margin-bottom:6px">'+esc(t('daily.wxGps'))+'</button>'+
    '<div id="wxdRes"></div>'+
    (l?'<div class="sub" style="margin:6px 0">📍 <b>'+esc(l.name)+'</b></div><div id="wxdBody"></div>'
      :'<div class="empty" style="padding:14px"><span class="empty-ico">🌍</span><p class="sub">'+esc(t('daily.wxNoLoc'))+'</p></div><div id="wxdBody"></div>')+
    '</div>'
  );
  /* unit toggle */
  const ub=document.getElementById('wxdUnit');
  if(ub) ub.onclick=function(){ w.setUnit(w.unit()==='c'?'f':'c'); refresh(); openDetail(); };
  /* city search */
  const go=function(){
    const inp=document.getElementById('wxdIn'), resBox=document.getElementById('wxdRes');
    const q=inp?inp.value.trim():'';
    if(!q||!resBox) return;
    resBox.innerHTML='<div class="sub" style="padding:8px 2px">⏳ '+esc(t('daily.wxLoading'))+'</div>';
    w.geoSearch(q).then(function(res){
      const rb=document.getElementById('wxdRes'); if(!rb) return;
      if(!res.length){ rb.innerHTML='<div class="sub" style="padding:8px 2px">'+esc(t('daily.wxNoRes'))+'</div>'; return; }
      rb.innerHTML=res.map(function(r,i){
        return '<button class="item tight wxres" data-i="'+i+'"><div class="grow"><h3>'+esc(r.name)+'</h3>'+
          '<div class="meta">'+esc(r.sub)+'</div></div><span style="color:var(--faint)">›</span></button>';
      }).join('');
      rb.querySelectorAll('.wxres').forEach(function(b){
        b.onclick=function(){
          const r=res[+b.dataset.i];
          w.setLoc({name:r.name,lat:r.lat,lon:r.lon});
          refresh(); openDetail();
          U.toast('📍 '+r.name);
        };
      });
    }).catch(function(){
      const rb=document.getElementById('wxdRes'); if(rb) rb.innerHTML='<div class="sub" style="padding:8px 2px">'+esc(t('daily.wxFail'))+'</div>';
    });
  };
  const wi=document.getElementById('wxdIn');
  if(wi) wi.addEventListener('keydown',function(e){ if(e.key==='Enter') go(); });
  const wg=document.getElementById('wxdGo'); if(wg) wg.onclick=go;
  /* GPS */
  const gps=document.getElementById('wxdGps');
  if(gps) gps.onclick=function(){
    U.toast('📍 '+t('daily.wxLocating'));
    w.useGps().then(function(l2){
      if(l2){ w.setLoc(l2); refresh(); openDetail(); }
      else U.toast(t('daily.wxNoGps'));
    });
  };
  paintDetailBody();
}

HUB.wxhome={stripHTML:stripHTML,paintStrip:paintStrip,refresh:refresh,bind:bind,openDetail:openDetail};
})();
