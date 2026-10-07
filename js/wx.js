/* HUB shared weather data layer (Workstream WX): real Open-Meteo data,
   free, no key. Extracted from js/daily.js so the Home car-dashboard strip
   and its glass detail view share one fetch/cache/unit/location pipeline.
   Remote data is always labeled by source; location + unit prefs stay in
   this browser (store.state.prefs.weatherLoc / weatherUnit). */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
/* Resilient fetch: retries + timeout (js/safeboot.js), plain-fetch fallback. */
const _fj=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){return fetch(u).then(function(r){if(!r.ok&&r.status!==0)throw new Error('http '+r.status);return r.json();});};
const st=function(){ return HUB.store.state; };
let wxCache=null; /* {key, at, data} — in-memory, 30 min */

/* ---------- condition groups ---------- */
const WX_GROUPS=[ /* [codes] -> daily.wx* key suffix, emoji */
  [[0,1],'wxClear','☀️'], [[2],'wxPartly','⛅'], [[3],'wxCloudy','☁️'],
  [[45,48],'wxFog','🌫️'], [[51,53,55,56,57],'wxDrizzle','🌦️'],
  [[61,63,65,66,67,80,81,82],'wxRain','🌧️'],
  [[71,73,75,77,85,86],'wxSnow','🌨️'], [[95,96,99],'wxStorm','⛈️']
];
function group(code){
  for(const g of WX_GROUPS) if(g[0].indexOf(code)>=0) return g;
  return [[],'wxCloudy','☁️'];
}
/* dashboard signal icon: sunny / raining / cloudy (car-dash style) */
function signal(code){
  const s=group(code)[1];
  if(s==='wxClear') return '☀️';
  if(s==='wxPartly') return '⛅';
  if(s==='wxRain'||s==='wxDrizzle'||s==='wxStorm') return '🌧️';
  if(s==='wxSnow') return '🌨️';
  return '☁️';
}

/* ---------- units / location ---------- */
function unit(){
  const p=st().prefs;
  if(!p.weatherUnit){
    let c=''; try{ c=HUB.i18n.getCountry()||HUB.i18n.guessCountry(); }catch(e){}
    p.weatherUnit=(c==='US'||c==='LR'||c==='MM')?'f':'c';
    HUB.store.save();
  }
  return p.weatherUnit;
}
function setUnit(u){
  st().prefs.weatherUnit=(u==='f'?'f':'c');
  wxCache=null; HUB.store.save();
}
function loc(){ return st().prefs.weatherLoc||null; }
function setLoc(l){ st().prefs.weatherLoc=l; wxCache=null; HUB.store.save(); }
function temp(v){ return Math.round(v)+'°'+(unit()==='f'?'F':'C'); }

/* ---------- fetch ---------- */
function wxURL(l){
  const u=unit();
  return 'https://api.open-meteo.com/v1/forecast?latitude='+l.lat+'&longitude='+l.lon+
    '&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m'+
    '&hourly=temperature_2m,weather_code,precipitation_probability'+
    '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'+
    '&timezone=auto&forecast_days=7'+
    '&temperature_unit='+(u==='f'?'fahrenheit':'celsius')+
    '&wind_speed_unit='+(u==='f'?'mph':'kmh');
}
/* sync read of whatever is cached (null when nothing cached yet) */
function data(){
  const l=loc(); if(!l) return null;
  const k=l.lat+','+l.lon+unit(), now=Date.now();
  if(wxCache&&wxCache.key===k&&now-wxCache.at<30*60*1000) return wxCache.data;
  return null;
}
/* one-shot: painter(null) while loading, painter(false) on error,
   painter(data) on success. Painters must re-query their target node —
   the view may have re-rendered while the fetch was in flight. */
function validWx(d){
  /* Open-Meteo answers HTTP 200 even for error payloads ({error:true});
     a malformed truthy body must never reach the painters — they index
     d.daily.*[0] directly. Invalid shape => honest failure UI. */
  return !!(d&&d.current&&typeof d.current==='object'
    &&isFinite(d.current.temperature_2m)&&isFinite(d.current.weather_code)
    &&d.daily&&typeof d.daily==='object'
    &&Array.isArray(d.daily.temperature_2m_max)&&d.daily.temperature_2m_max.length
    &&Array.isArray(d.daily.temperature_2m_min)&&d.daily.temperature_2m_min.length
    &&Array.isArray(d.daily.weather_code)&&d.daily.weather_code.length);
}
function refresh(painter){
  /* Weather needs internet */
  if(window.HUB&&HUB.offline&&HUB.offline.is()){ painter(false); return; }
  const l=loc(); if(!l) return;
  const k=l.lat+','+l.lon+unit(), now=Date.now();
  if(wxCache&&wxCache.key===k&&now-wxCache.at<30*60*1000){ painter(wxCache.data); return; }
  painter(null);
  _fj(wxURL(l))
    .then(function(d){
      if(!validWx(d)) throw new Error('bad wx shape');
      wxCache={key:k,at:now,data:d}; painter(d);
    })
    .catch(function(){ painter(false); });
}

/* ---------- city search + GPS ---------- */
function geoSearch(q){
  return _fj('https://geocoding-api.open-meteo.com/v1/search?name='+encodeURIComponent(q)+'&count=6&language=en&format=json')
    .then(function(d){
      return ((d&&d.results)||[]).map(function(r){
        return {name:r.name, sub:(r.admin1?r.admin1+', ':'')+(r.country||''), lat:r.latitude, lon:r.longitude};
      });
    });
}
function useGps(){
  return new Promise(function(res){
    if(!('geolocation' in navigator)){ res(null); return; }
    navigator.geolocation.getCurrentPosition(
      function(pos){ res((pos&&pos.coords)?{name:t('daily.wxGpsLoc'),lat:pos.coords.latitude,lon:pos.coords.longitude}:null); },
      function(){ res(null); },
      {timeout:9000,maximumAge:600000}
    );
  });
}

HUB.wx={group:group,signal:signal,unit:unit,setUnit:setUnit,loc:loc,setLoc:setLoc,
  temp:temp,data:data,refresh:refresh,geoSearch:geoSearch,useGps:useGps};
})();
