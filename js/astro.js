/* HUB astro + calendar: DOB -> zodiac sign -> daily horoscope (server-baked
   data/horoscopes.json, cached per day, honest offline fallback), plus a country-aware calendar:
   Gregorian default, Bikram Sambat for Nepal (embedded conversion table,
   anchor BS 2000-01-01 = AD 1943-04-14, verified against nepali-date-converter).
   Day notes (birthday/exam/special) with in-app reminders surfaced through the
   notifications center. All browser-local. No push backend — reminders appear
   in-app only, and the UI says so. */
(function(){
'use strict';
/* Resilient fetch: retries + timeout (js/safeboot.js), plain-fetch fallback. */
const _fj=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){return fetch(u).then(function(r){if(!r.ok&&r.status!==0)throw new Error('http '+r.status);return r.json();});};
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

/* ================= Bikram Sambat conversion =================
   Month lengths for BS 2000-2090 (nepali-date-converter data, MIT).
   Local-time based (matches the reference library's behavior). */
const BS_TABLE={"2000":[30,32,31,32,31,30,30,30,29,30,29,31],"2001":[31,31,32,31,31,31,30,29,30,29,30,30],"2002":[31,31,32,32,31,30,30,29,30,29,30,30],"2003":[31,32,31,32,31,30,30,30,29,29,30,31],"2004":[30,32,31,32,31,30,30,30,29,30,29,31],"2005":[31,31,32,31,31,31,30,29,30,29,30,30],"2006":[31,31,32,32,31,30,30,29,30,29,30,30],"2007":[31,32,31,32,31,30,30,30,29,29,30,31],"2008":[31,31,31,32,31,31,29,30,30,29,29,31],"2009":[31,31,32,31,31,31,30,29,30,29,30,30],"2010":[31,31,32,32,31,30,30,29,30,29,30,30],"2011":[31,32,31,32,31,30,30,30,29,29,30,31],"2012":[31,31,31,32,31,31,29,30,30,29,30,30],"2013":[31,31,32,31,31,31,30,29,30,29,30,30],"2014":[31,31,32,32,31,30,30,29,30,29,30,30],"2015":[31,32,31,32,31,30,30,30,29,29,30,31],"2016":[31,31,31,32,31,31,29,30,30,29,30,30],"2017":[31,31,32,31,31,31,30,29,30,29,30,30],"2018":[31,32,31,32,31,30,30,29,30,29,30,30],"2019":[31,32,31,32,31,30,30,30,29,30,29,31],"2020":[31,31,31,32,31,31,30,29,30,29,30,30],"2021":[31,31,32,31,31,31,30,29,30,29,30,30],"2022":[31,32,31,32,31,30,30,30,29,29,30,30],"2023":[31,32,31,32,31,30,30,30,29,30,29,31],"2024":[31,31,31,32,31,31,30,29,30,29,30,30],"2025":[31,31,32,31,31,31,30,29,30,29,30,30],"2026":[31,32,31,32,31,30,30,30,29,29,30,31],"2027":[30,32,31,32,31,30,30,30,29,30,29,31],"2028":[31,31,32,31,31,31,30,29,30,29,30,30],"2029":[31,31,32,31,32,30,30,29,30,29,30,30],"2030":[31,32,31,32,31,30,30,30,29,29,30,31],"2031":[30,32,31,32,31,30,30,30,29,30,29,31],"2032":[31,31,32,31,31,31,30,29,30,29,30,30],"2033":[31,31,32,32,31,30,30,29,30,29,30,30],"2034":[31,32,31,32,31,30,30,30,29,29,30,31],"2035":[30,32,31,32,31,31,29,30,30,29,29,31],"2036":[31,31,32,31,31,31,30,29,30,29,30,30],"2037":[31,31,32,32,31,30,30,29,30,29,30,30],"2038":[31,32,31,32,31,30,30,30,29,29,30,31],"2039":[31,31,31,32,31,31,29,30,30,29,30,30],"2040":[31,31,32,31,31,31,30,29,30,29,30,30],"2041":[31,31,32,32,31,30,30,29,30,29,30,30],"2042":[31,32,31,32,31,30,30,30,29,29,30,31],"2043":[31,31,31,32,31,31,29,30,30,29,30,30],"2044":[31,31,32,31,31,31,30,29,30,29,30,30],"2045":[31,32,31,32,31,30,30,29,30,29,30,30],"2046":[31,32,31,32,31,30,30,30,29,29,30,31],"2047":[31,31,31,32,31,31,30,29,30,29,30,30],"2048":[31,31,32,31,31,31,30,29,30,29,30,30],"2049":[31,32,31,32,31,30,30,30,29,29,30,30],"2050":[31,32,31,32,31,30,30,30,29,30,29,31],"2051":[31,31,31,32,31,31,30,29,30,29,30,30],"2052":[31,31,32,31,31,31,30,29,30,29,30,30],"2053":[31,32,31,32,31,30,30,30,29,29,30,30],"2054":[31,32,31,32,31,30,30,30,29,30,29,31],"2055":[31,31,32,31,31,31,30,29,30,29,30,30],"2056":[31,31,32,31,32,30,30,29,30,29,30,30],"2057":[31,32,31,32,31,30,30,30,29,29,30,31],"2058":[30,32,31,32,31,30,30,30,29,30,29,31],"2059":[31,31,32,31,31,31,30,29,30,29,30,30],"2060":[31,31,32,32,31,30,30,29,30,29,30,30],"2061":[31,32,31,32,31,30,30,30,29,29,30,31],"2062":[30,32,31,32,31,31,29,30,29,30,29,31],"2063":[31,31,32,31,31,31,30,29,30,29,30,30],"2064":[31,31,32,32,31,30,30,29,30,29,30,30],"2065":[31,32,31,32,31,30,30,30,29,29,30,31],"2066":[31,31,31,32,31,31,29,30,30,29,29,31],"2067":[31,31,32,31,31,31,30,29,30,29,30,30],"2068":[31,31,32,32,31,30,30,29,30,29,30,30],"2069":[31,32,31,32,31,30,30,30,29,29,30,31],"2070":[31,31,31,32,31,31,29,30,30,29,30,30],"2071":[31,31,32,31,31,31,30,29,30,29,30,30],"2072":[31,32,31,32,31,30,30,29,30,29,30,30],"2073":[31,32,31,32,31,30,30,30,29,29,30,31],"2074":[31,31,31,32,31,31,30,29,30,29,30,30],"2075":[31,31,32,31,31,31,30,29,30,29,30,30],"2076":[31,32,31,32,31,30,30,30,29,29,30,30],"2077":[31,32,31,32,31,30,30,30,29,30,29,31],"2078":[31,31,31,32,31,31,30,29,30,29,30,30],"2079":[31,31,32,31,31,31,30,29,30,29,30,30],"2080":[31,32,31,32,31,30,30,30,29,29,30,30],"2081":[31,32,31,32,31,30,30,30,29,30,29,31],"2082":[31,31,32,31,31,31,30,29,30,29,30,30],"2083":[31,31,32,31,31,31,30,29,30,29,30,30],"2084":[31,32,31,32,31,30,30,30,29,29,30,31],"2085":[30,32,31,32,31,30,30,30,29,30,29,31],"2086":[31,31,32,31,31,31,30,29,30,29,30,30],"2087":[31,31,32,31,31,31,30,30,29,30,30,30],"2088":[30,31,32,32,30,31,30,30,29,30,30,30],"2089":[30,32,31,32,31,30,30,30,29,30,30,30],"2090":[30,32,31,32,31,30,30,30,29,30,30,30]};
const BS_MONTHS=['Baisakh','Jestha','Asar','Shrawan','Bhadra','Aswin','Kartik','Mangsir','Poush','Magh','Falgun','Chaitra'];
const BS_MIN=2000, BS_MAX=2090;
function bsRow(y){ return BS_TABLE[String(y)]||null; }
function bsYearDays(y){ const r=bsRow(y); return r?r.reduce((a,b)=>a+b,0):0; }
/* days from BS 2000-01-01 to BS y-m-d (m,d 1-based) */
function bsDaysSinceAnchor(y,m,d){
  let n=0;
  for(let yy=BS_MIN; yy<y; yy++) n+=bsYearDays(yy);
  const r=bsRow(y); if(!r) return -1;
  for(let mm=1; mm<m; mm++) n+=r[mm-1];
  return n+(d-1);
}
/* AD (local date) -> [bsY,bsM,bsD] or null when out of table range */
function adToBs(y,m,d){
  const anchor=new Date(1943,3,14); // BS 2000-01-01, local time
  let n=Math.round((new Date(y,m-1,d)-anchor)/864e5);
  if(n<0) return null;
  let yy=BS_MIN;
  for(;;){
    const yd=bsYearDays(yy);
    if(!yd||yy>BS_MAX) return null;
    if(n<yd) break;
    n-=yd; yy++;
  }
  const r=bsRow(yy); let mm=1;
  while(mm<=12 && n>=r[mm-1]){ n-=r[mm-1]; mm++; }
  if(mm>12) return null;
  return [yy,mm,n+1];
}
/* BS y-m-d -> [adY,adM,adD] (local) or null */
function bsToAd(y,m,d){
  const n=bsDaysSinceAnchor(y,m,d);
  if(n<0) return null;
  const dt=new Date(new Date(1943,3,14).getTime()+n*864e5);
  return [dt.getFullYear(),dt.getMonth()+1,dt.getDate()];
}
function bsMonthLen(y,m){ const r=bsRow(y); return r?r[m-1]:30; }
function bsToday(){ const n=new Date(); return adToBs(n.getFullYear(),n.getMonth()+1,n.getDate()); }

/* ================= zodiac ================= */
const SIGNS=[
  {n:'Capricorn',i:'♑',icon:'zodiac-capricorn',from:[12,22],to:'Jan 19'},
  {n:'Aquarius', i:'♒',icon:'zodiac-aquarius',from:[1,20], to:'Feb 18'},
  {n:'Pisces',   i:'♓',icon:'zodiac-pisces',from:[2,19], to:'Mar 20'},
  {n:'Aries',    i:'♈',icon:'zodiac-aries',from:[3,21], to:'Apr 19'},
  {n:'Taurus',   i:'♉',icon:'zodiac-taurus',from:[4,20], to:'May 20'},
  {n:'Gemini',   i:'♊',icon:'zodiac-gemini',from:[5,21], to:'Jun 20'},
  {n:'Cancer',   i:'♋',icon:'zodiac-cancer',from:[6,21], to:'Jul 22'},
  {n:'Leo',      i:'♌',icon:'zodiac-leo',from:[7,23], to:'Aug 22'},
  {n:'Virgo',    i:'♍',icon:'zodiac-virgo',from:[8,23], to:'Sep 22'},
  {n:'Libra',    i:'♎',icon:'zodiac-libra',from:[9,23], to:'Oct 22'},
  {n:'Scorpio',  i:'♏',icon:'zodiac-scorpio',from:[10,23],to:'Nov 21'},
  {n:'Sagittarius',i:'♐',icon:'zodiac-sagittarius',from:[11,22],to:'Dec 21'}
];
function signFor(m,d){
  /* Capricorn spans the year boundary (Dec 22 - Jan 19): handle it first,
     because the ascending loop below would otherwise let every Jan-Nov sign
     match m=12 and leave December 22-31 stuck on Sagittarius. */
  if((m===12&&d>=22)||(m===1&&d<=19)) return SIGNS[0];
  let cur=SIGNS[1];
  for(const s of SIGNS.slice(1)){ const f=s.from; if(m>f[0]||(m===f[0]&&d>=f[1])) cur=s; }
  return cur;
}
function signForDob(dob){ // dob: 'YYYY-MM-DD'
  const p=String(dob||'').split('-');
  if(p.length<3) return null;
  return signFor(+p[1],+p[2]);
}

/* ================= daily horoscope =================
   Readings are baked into data/horoscopes.json by a daily server fetch
   (freehoroscopeapi.com, no key) and read same-origin, so phones are not
   blocked by the API's missing CORS headers. The freshest same-day reading
   is also cached per sign in localStorage for offline use. */
const HORO_KEY='orbit_horo_v1';
function horoCache(){ try{ return JSON.parse(localStorage.getItem(HORO_KEY))||{}; }catch(e){ return {}; } }
function horoSave(c){ try{ localStorage.setItem(HORO_KEY,JSON.stringify(c)); }catch(e){} }
function todayStr(){ const n=new Date(); return n.getFullYear()+'-'+String(n.getMonth()+1).padStart(2,'0')+'-'+String(n.getDate()).padStart(2,'0'); }
function horoURLs(){
  /* Phase 1 backend (js/api.js): API first when configured, then the baked
     static file. The API fetches fresh readings server-side daily, so this
     permanently fixes stale horoscopes once the backend is live. */
  var urls=[];
  try{ if(window.HUB&&HUB.api&&HUB.api.on()) urls.push(HUB.api.horoscopeURL()); }catch(e){}
  urls.push('data/horoscopes.json');
  return urls;
}
function horoFetch(){
  var urls=horoURLs(), p=Promise.reject();
  urls.forEach(function(u){ p=p.catch(function(){ return _fj(u); }); });
  return p;
}
function fetchHoroscope(sign,cb){
  const c=horoCache(), today=todayStr(), hit=c[sign]&&c[sign].date===today?c[sign]:null;
  if(hit){ cb(hit); return; }
  horoFetch()
    .then(j=>{
      const sgn=String(sign).toLowerCase();
      const txt=String((j&&j.signs&&j.signs[sgn])||'').trim();
      const fdate=String((j&&j.date)||'');
      if(!txt){ cb(c[sign]||null); return; }
      // Only treat as "today" when the baked file's date matches the device date.
      if(fdate===today){
        const rec={date:today,text:txt,src:'daily'};
        c[sign]=rec; horoSave(c); cb(rec);
      } else {
        cb({date:fdate,text:txt,src:'daily',stale:true});
      }
    })
    .catch(()=>cb(c[sign]||null));
}

/* ================= calendar notes (browser-local) ================= */
const KINDS={birthday:'🎂',exam:'📝',special:'✨',other:'📌'};
function notes(){ const st=store.state; if(!Array.isArray(st.calNotes)) st.calNotes=[]; return st.calNotes; }
function kindEmoji(k){ return KINDS[k]||KINDS.other; }
function notesOn(cal,y,m,d){ return notes().filter(n=>n.cal===cal&&n.y===y&&n.m===m&&n.d===d); }
function addNote(o){ o.id=store.uid(); o.createdAt=Date.now(); notes().push(o); store.save(); return o; }
function delNote(id){ store.state.calNotes=(store.state.calNotes||[]).filter(n=>n.id!==id); store.save(); }
function userCal(){ return (HUB.i18n.getCountry()==='NP')?'BS':'AD'; }

/* ================= month grid ================= */
const AD_MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
const WD=['S','M','T','W','T','F','S'];
let view=null; // {cal,y,m,cc}
function openView(){
  const cc=HUB.i18n.getCountry()||'';
  if(view&&view.cc===cc) return view;
  return resetView(cc);
}
function resetView(cc){
  if(cc===undefined) cc=HUB.i18n.getCountry()||'';
  const cal=(cc==='NP')?'BS':'AD', n=new Date();
  if(cal==='BS'){ const b=bsToday()||[2083,6,5]; view={cal:cal,y:b[0],m:b[1],cc:cc}; }
  else view={cal:'AD',y:n.getFullYear(),m:n.getMonth()+1,cc:cc};
  return view;
}
function monthTitle(v){
  return v.cal==='BS' ? BS_MONTHS[v.m-1]+' '+v.y : t('cal.month.'+(v.m-1))+ ' '+v.y;
}
function monthLen(v){
  if(v.cal==='BS') return bsMonthLen(v.y,v.m);
  return new Date(v.y,v.m,0).getDate();
}
function monthStartWd(v){
  if(v.cal==='BS'){ const a=bsToAd(v.y,v.m,1); return a?new Date(a[0],a[1]-1,a[2]).getDay():0; }
  return new Date(v.y,v.m-1,1).getDay();
}
function isTodayCell(v,d){
  const n=new Date();
  if(v.cal==='BS'){ const b=bsToday(); return b&&b[0]===v.y&&b[1]===v.m&&b[2]===d; }
  return n.getFullYear()===v.y&&(n.getMonth()+1)===v.m&&n.getDate()===d;
}
function gridHTML(v){
  const len=monthLen(v), start=monthStartWd(v);
  let h='<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;text-align:center">';
  for(const w of WD) h+='<div style="font-size:11px;color:var(--muted);font-weight:700;padding:4px 0">'+w+'</div>';
  for(let i=0;i<start;i++) h+='<div></div>';
  for(let d=1;d<=len;d++){
    const has=notesOn(v.cal,v.y,v.m,d).length>0, tod=isTodayCell(v,d);
    h+='<button data-calday="'+d+'" style="aspect-ratio:1;border-radius:12px;border:'+(tod?'2px solid var(--accent)':'1px solid var(--line)')+';'
      +'background:'+(tod?'var(--accent-soft)':'var(--card)')+';color:var(--ink);font-size:14px;font-weight:'+(tod?'800':'500')
      +';position:relative;cursor:pointer;min-height:44px">'+d
      +(has?'<span style="position:absolute;bottom:5px;left:50%;transform:translateX(-50%);width:6px;height:6px;border-radius:50%;background:var(--accent)"></span>':'')
      +'</button>';
  }
  return h+'</div>';
}

/* ================= calendar sheet ================= */
function openCalendar(){
  const v=openView();
  const sub=v.cal==='BS' ? t('cal.bsSub') : t('cal.adSub');
  ui.openSheet(
    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:2px">'
    +'<h2 style="margin:0;flex:1">📅 '+ui.esc(t('cal.title'))+'</h2>'
    +'<button id="calToggle" class="btn ghost" style="font-size:12px;padding:6px 10px">'+ui.esc(v.cal==='BS'?'AD':'BS')+'</button>'
    +'<button class="btn ghost" data-close style="font-size:12px;padding:6px 10px">✕</button></div>'
    +'<div class="meta" style="margin-bottom:10px">'+ui.esc(sub)+'</div>'
    +'<div id="calBody"></div>',
    {sheet:true}
  );
  renderCalBody();
  document.getElementById('calToggle').onclick=()=>{
    const cur=openView(), cc=HUB.i18n.getCountry()||'';
    if(cur.cal==='BS'){ const n=new Date(); view={cal:'AD',y:n.getFullYear(),m:n.getMonth()+1,cc:cc}; }
    else { const b=bsToday(); view=b?{cal:'BS',y:b[0],m:b[1],cc:cc}:cur; }
    ui.closeSheet(); openCalendar();
  };
  document.getElementById('calBody').addEventListener('click',e=>{
    const b=e.target.closest('[data-calday]');
    if(b) openDay(openView(),+b.getAttribute('data-calday'));
    const nav=e.target.closest('[data-calnav]');
    if(nav){ navMonth(+nav.getAttribute('data-calnav')); }
  });
}
function navMonth(dir){
  const v=openView();
  v.m+=dir;
  if(v.m<1){ v.m=12; v.y--; } if(v.m>12){ v.m=1; v.y++; }
  renderCalBody();
}
function renderCalBody(){
  const v=openView(), el=document.getElementById('calBody');
  if(!el) return;
  el.innerHTML=
    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
    +'<button data-calnav="-1" class="btn ghost" style="padding:6px 12px">‹</button>'
    +'<div style="flex:1;text-align:center;font-weight:800;font-size:16px">'+ui.esc(monthTitle(v))+'</div>'
    +'<button data-calnav="1" class="btn ghost" style="padding:6px 12px">›</button></div>'
    +gridHTML(v)
    +'<button id="calTodayBtn" class="btn ghost" style="width:100%;margin-top:10px">'+ui.esc(t('cal.todayBtn'))+'</button>';
  const tb=document.getElementById('calTodayBtn');
  if(tb) tb.onclick=()=>{ resetView(); ui.closeSheet(); openCalendar(); };
}
function fmtDayTitle(v,d){
  if(v.cal==='BS') return d+' '+BS_MONTHS[v.m-1]+' '+v.y;
  return t('cal.month.'+(v.m-1))+' '+d+', '+v.y;
}
function openDay(v,d){
  const list=notesOn(v.cal,v.y,v.m,d);
  let h='<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
    +'<h2 style="margin:0;flex:1;font-size:17px">'+ui.esc(fmtDayTitle(v,d))+'</h2>'
    +'<button class="btn ghost" data-close style="font-size:12px;padding:6px 10px">✕</button></div>';
  if(!list.length) h+='<div class="meta" style="margin-bottom:10px">'+ui.esc(t('cal.noNotes'))+'</div>';
  for(const n of list){
    h+='<div class="item"><div style="font-size:22px">'+kindEmoji(n.kind)+'</div>'
      +'<div class="grow"><h3 style="margin:0;font-size:14px">'+ui.esc(n.text)+'</h3>'
      +'<div class="meta">'+ui.esc(t('cal.kind.'+(n.kind||'other')))+(n.remind?' · 🔔 '+ui.esc(t('cal.remindOn')):'')+'</div></div>'
      +'<button class="btn ghost" data-candel="'+n.id+'" style="font-size:12px;padding:6px 10px">'+ui.esc(t('cal.delete'))+'</button></div>';
  }
  h+='<div style="margin-top:12px;border-top:1px solid var(--line);padding-top:12px">'
    +'<div style="font-weight:700;margin-bottom:8px;font-size:14px">'+ui.esc(t('cal.addNote'))+'</div>'
    +'<input id="calText" class="input" placeholder="'+ui.esc(t('cal.notePh'))+'" style="margin-bottom:8px">'
    +'<div style="display:flex;gap:8px;margin-bottom:8px">'
    +'<select id="calKind" class="input" style="flex:1">'
    +['birthday','exam','special','other'].map(k=>'<option value="'+k+'">'+kindEmoji(k)+' '+ui.esc(t('cal.kind.'+k))+'</option>').join('')
    +'</select>'
    +'<label style="display:flex;align-items:center;gap:6px;font-size:13px;flex:1"><input type="checkbox" id="calRemind" checked> '+ui.esc(t('cal.remind'))+'</label>'
    +'</div>'
    +'<button id="calSave" class="btn primary" style="width:100%">'+ui.esc(t('cal.save'))+'</button></div>';
  ui.openSheet(h,{sheet:true});
  document.getElementById('calSave').onclick=()=>{
    const txt=document.getElementById('calText').value.trim();
    if(!txt){ document.getElementById('calText').focus(); return; }
    addNote({cal:v.cal,y:v.y,m:v.m,d:d,text:txt,
      kind:document.getElementById('calKind').value,
      remind:document.getElementById('calRemind').checked});
    ui.closeSheet(); ui.closeSheet(); openCalendar();
  };
  document.querySelectorAll('[data-candel]').forEach(b=>b.onclick=()=>{
    delNote(b.getAttribute('data-candel'));
    ui.closeSheet(); ui.closeSheet(); openCalendar();
  });
}

/* ================= home card ================= */
function homeCardHTML(){
  const p=store.state.profile||{};
  const dob=p.dob||'';
  if(!dob){
    /* No DOB: 3D wax zodiac picker with floating animation */
    return '<div class="card astro-picker" id="astroCard" style="cursor:pointer">'
      +'<div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">'
      +'<div style="font-size:26px;animation:astroFloat 3s ease-in-out infinite">🔮</div>'
      +'<div class="grow"><h3 style="margin:0;font-size:15px">'+ui.esc(t('astro.cardT'))+'</h3>'
      +'<div class="meta">'+ui.esc(t('astro.pickSign'))+'</div></div>'
      +'<span class="chev">›</span></div>'
      +'<div class="astro-sign-grid" id="astroSignGrid">'
      +SIGNS.map(function(s,i){
        const delay=(i*0.15).toFixed(2);
        return '<button class="astro-sign-btn" data-sign="'+i+'" style="animation-delay:'+delay+'s" title="'+ui.esc(s.n)+'">'
          +'<span class="astro-sign-icon">'+HUB.icons.icon(s.icon,'astro-sign-img')+'</span>'
          +'<span class="astro-sign-name">'+ui.esc(s.n)+'</span></button>';
      }).join('')
      +'</div></div>';
  }
  const s=signForDob(dob);
  const todayN=notes().filter(n=>{
    const now=new Date();
    if(n.cal==='BS'){ const b=bsToday(); return b&&n.y===b[0]&&n.m===b[1]&&n.d===b[2]; }
    return n.cal==='AD'&&n.y===now.getFullYear()&&n.m===now.getMonth()+1&&n.d===now.getDate();
  });
  return '<div class="card" id="astroCard" style="cursor:pointer">'
    +'<div style="display:flex;gap:10px;align-items:center;margin-bottom:6px"><div style="font-size:26px">'+s.i+'</div>'
    +'<div class="grow"><h3 style="margin:0;font-size:15px">'+ui.esc(s.n)+' · '+ui.esc(t('astro.today'))+'</h3>'
    +'<div class="meta">'+ui.esc(t('astro.tapFull'))+'</div></div>'
    +'<button id="astroCalBtn" class="btn ghost" style="font-size:12px;padding:6px 10px">📅 '+ui.esc(t('cal.title'))+'</button></div>'
    +'<div id="astroSnippet" class="meta" style="font-size:13px;line-height:1.5">'+ui.esc(t('astro.loading'))+'</div>'
    +(todayN.length?'<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">'
      +todayN.slice(0,3).map(n=>'<span style="font-size:12px;background:var(--accent-soft);border:1px solid var(--line);border-radius:20px;padding:4px 10px">'+kindEmoji(n.kind)+' '+ui.esc(n.text)+'</span>').join('')
      +'</div>':'')
    +'</div>';
}
function bindHomeCard(){
  const card=document.getElementById('astroCard');
  if(!card) return;
  const p=store.state.profile||{};
  if(!p.dob){
    /* Sign picker: tapping a sign opens its horoscope directly */
    const grid=document.getElementById('astroSignGrid');
    if(grid) grid.onclick=function(e){
      const btn=e.target.closest('[data-sign]');
      if(!btn) return;
      e.stopPropagation();
      const s=SIGNS[parseInt(btn.getAttribute('data-sign'),10)];
      if(s) openHoroscope(s);
    };
    /* Tapping the card header still goes to profile to set DOB */
    card.onclick=function(e){
      if(e.target.closest('#astroSignGrid')) return;
      HUB.showTab('me');
    };
    return;
  }
  const s=signForDob(p.dob);
  const calBtn=document.getElementById('astroCalBtn');
  if(calBtn) calBtn.onclick=e=>{ e.stopPropagation(); openCalendar(); };
  card.onclick=e=>{ if(e.target.closest('#astroCalBtn')) return; openHoroscope(s); };
  fetchHoroscope(s.n,snip=>{
    const el=document.getElementById('astroSnippet');
    if(!el) return;
    el.textContent=(snip&&snip.text&&!snip.stale) ? snip.text.split(/(?<=[.!?])\s/)[0] : t('astro.offline');
  });
}
/* Lucky number + color: deterministic per sign+day (same all day, new tomorrow).
   Generated on-device for fun — not from the horoscope text service. */
const LUCKY_COLORS=[
  ['Gold','#C9A227'],['Emerald','#1F7A4D'],['Crimson','#D7263D'],
  ['Sapphire','#2563EB'],['Amber','#E8930C'],['Teal','#0E9F8A'],
  ['Rose','#F43F5E'],['Jade','#0FA968'],['Coral','#FF6B4A'],
  ['Azure','#2AA8E0'],['Copper','#B87333'],['Mint','#3EBF8F']
];
function luckyFor(sign,dateStr){
  let h=0; const s=String(sign)+'|'+String(dateStr);
  for(let i=0;i<s.length;i++) h=(h*31+s.charCodeAt(i))>>>0;
  return {n:(h%99)+1, c:LUCKY_COLORS[h%LUCKY_COLORS.length]};
}
function fillLucky(s){
  const el=document.getElementById('horoLucky'); if(!el) return;
  const L=luckyFor(s.n,todayStr());
  el.innerHTML=
    '<div class="card" style="flex:1;margin:0;padding:10px 12px;text-align:center">'
    +'<div style="font-size:20px">🍀</div>'
    +'<div class="meta" style="font-size:11px">'+ui.esc(t('astro.luckyN'))+'</div>'
    +'<div style="font-size:22px;font-weight:800">'+L.n+'</div></div>'
    +'<div class="card" style="flex:1;margin:0;padding:10px 12px;text-align:center">'
    +'<div style="font-size:20px">🎨</div>'
    +'<div class="meta" style="font-size:11px">'+ui.esc(t('astro.luckyC'))+'</div>'
    +'<div style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:15px;font-weight:700">'
    +'<span style="width:14px;height:14px;border-radius:50%;background:'+L.c[1]+';display:inline-block;border:1px solid rgba(0,0,0,.15)"></span>'
    +ui.esc(L.c[0])+'</div></div>';
}
function openHoroscope(s){
  const p=store.state.profile||{};
  ui.openSheet(
    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
    +'<h2 style="margin:0;flex:1">'+s.i+' '+ui.esc(s.n)+'</h2>'
    +'<button class="btn ghost" data-close style="font-size:12px;padding:6px 10px">✕</button></div>'
    +'<div class="meta" style="margin-bottom:10px">'+ui.esc(t('astro.dobLine',{dob:p.dob||'—'}))+' · '+ui.esc(s.from[0]+'/'+s.from[1]+' – '+s.to)+'</div>'
    +'<div id="horoDateLine" class="meta" style="margin-bottom:10px;font-weight:700"></div>'
    +'<div id="horoFull" class="meta" style="font-size:14px;line-height:1.65">'+ui.esc(t('astro.loading'))+'</div>'
    +'<div id="horoLucky" style="display:flex;gap:10px;margin-top:14px"></div>',
    {sheet:true}
  );
  fillLucky(s);
  fetchHoroscope(s.n,snip=>{
    const el=document.getElementById('horoFull');
    if(!el) return;
    if(snip&&snip.text){
      el.textContent=snip.text;
      if(snip.stale){
        const dl=document.getElementById('horoDateLine');
        if(dl) dl.textContent=t('astro.forDate',{date:snip.date});
      }
    } else el.textContent=t('astro.offline');
  });
}

/* ================= reminders -> notifications center ================= */
function isNoteToday(n){
  const now=new Date();
  if(n.cal==='BS'){ const b=bsToday(); return !!(b&&n.y===b[0]&&n.m===b[1]&&n.d===b[2]); }
  return n.cal==='AD'&&n.y===now.getFullYear()&&n.m===now.getMonth()+1&&n.d===now.getDate();
}
function reminderItems(){
  const out=[];
  for(const n of notes()){
    if(!n.remind||!isNoteToday(n)) continue;
    out.push({nid:'cal-'+n.id, system:'calendar', prio:'high', emoji:kindEmoji(n.kind),
      title:t('astro.remindT',{text:n.text}),
      sub:t('astro.remindS',{kind:t('cal.kind.'+(n.kind||'other'))}),
      tab:'home', ts:n.createdAt||0});
  }
  return out;
}

HUB.astro={
  openCalendar:openCalendar, homeCardHTML:homeCardHTML, bindHomeCard:bindHomeCard,
  reminderItems:reminderItems, adToBs:adToBs, bsToAd:bsToAd, signForDob:signForDob,
  notes:notes, notesOn:notesOn, luckyFor:luckyFor
};
})();
