/* HUB motivation quote: a curated bank of real, correctly-attributed
   quotes (data/quotes.json, 120 entries) with one picked per 12-hour slot,
   deterministic (UTC half-day number mod bank size) so it is stable within
   the slot and changes at midnight and noon UTC. Same-origin JSON, cached
   in localStorage for offline. */
(function(){
'use strict';
const {ui}=HUB;
/* Resilient fetch: retries + timeout (js/safeboot.js), plain-fetch fallback. */
const _fj=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){return fetch(u).then(function(r){if(!r.ok&&r.status!==0)throw new Error('http '+r.status);return r.json();});};
const t=function(k,v){ return HUB.i18n.t(k,v); };
const CACHE_KEY='orbit_quotes_v1';

function dayIndex(n){
  // UTC 12-hour slot number -> stable index into the bank; changes at
  // midnight and noon UTC (7am / 7pm America/Chicago).
  return Math.floor(Date.now()/43200000)%n;
}
function loadQuotes(cb){
  function fromCache(){
    try{
      const c=JSON.parse(localStorage.getItem(CACHE_KEY)||'null');
      if(c&&Array.isArray(c.quotes)&&c.quotes.length) return c.quotes;
    }catch(e){}
    return null;
  }
  _fj('data/quotes.json')
    .then(j=>{
      const arr=(j&&j.quotes)||[];
      if(arr.length){ try{ localStorage.setItem(CACHE_KEY,JSON.stringify({quotes:arr})); }catch(e){} cb(arr); }
      else cb(fromCache()||[]);
    })
    .catch(()=>cb(fromCache()||[]));
}
/* Slim horizontal band for the Home hero: one line of motivation, not a
   tall card. Same element ids so bindQuoteCard keeps working. */
function cardHTML(){
  return '<div class="qband" id="quoteCard">'
    +'<span class="qband-mark">&ldquo;</span>'
    +'<div class="qband-body">'
    +'<div class="qband-eyebrow">✨ '+ui.esc(t('quote.title'))+'</div>'
    +'<div class="qband-text" id="quoteText"><span class="meta">'+ui.esc(t('quote.loading'))+'</span></div>'
    +'<div class="qband-author meta" id="quoteAuthor"></div>'
    +'</div></div>';
}
function bandHTML(){ return cardHTML(); }
function bindQuoteCard(){
  const card=document.getElementById('quoteCard');
  if(!card) return;
  loadQuotes(arr=>{
    if(!arr.length) return;
    const q=arr[dayIndex(arr.length)];
    const te=document.getElementById('quoteText');
    const ae=document.getElementById('quoteAuthor');
    if(te) te.innerHTML='&ldquo;'+ui.esc(q.q)+'&rdquo;';
    if(ae) ae.textContent='— '+q.a;
  });
}

window.HUB=Object.assign(window.HUB||{},{
  quote:{cardHTML:cardHTML,bandHTML:bandHTML,bindQuoteCard:bindQuoteCard,dayIndex:dayIndex}
});
})();
