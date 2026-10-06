/* ONARO ADS — sponsored placement infrastructure (IIFE module, exposes HUB.ads).
   ============================================================================
   WHAT IS REAL: the placement system — slot registry, frequency rules, labeling
   helpers, demo-sheet flow. Real advertisers can plug into these slots later.
   WHAT IS DEMO: the inventory. Every ad rendered is a FICTIONAL brand, and
   every ad surface carries BOTH "Sponsored" AND "Demo ad" labels so nobody
   mistakes it for a real business. NEVER invent ads for real businesses.

   TARGETING (demo): none. No user data is used to choose or rank ads — the
   demo inventory simply rotates. Production targeting MUST be opt-in and MUST
   NEVER sell user data. (See note on rotation below.)

   Slots:
     1. marketFeed  — interleaved sponsored cards in the Market listing feed.
     2. homeCarousel — "Sponsored near you" horizontal carousel on Home.

   Load order: after i18n.js + store.js (uses HUB.i18n.t and HUB.ui at call
   time only). market.js / home.js call into HUB.ads — they guard
   with `HUB.ads &&` so the app still works if this file is missing.
*/
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };

/* ---------------- frequency rules (tunable) ---------------- */
const RULES={
  marketFeedEvery:5,  // insert one sponsored card after every N organic listings
  marketFeedMax:3,    // hard cap of sponsored cards per market feed render
  trayMax:2,          // sponsored rings shown at the end of the story tray
  homeCarouselMax:4,  // tiles in the "Sponsored near you" carousel
};

/* ---------------- demo inventory: FICTIONAL brands only ----------------
   Fields: id, brand, tagline, emoji, grad (index into AD_GRADS), cta key.
   Rotation is a plain round-robin (no user data involved — see header). */
const AD_GRADS=[
  'linear-gradient(135deg,#C6F135,#4D7C0F)',
  'linear-gradient(135deg,#7C5CFF,#2A1B6B)',
  'linear-gradient(135deg,#FF9D5C,#B45309)',
  'linear-gradient(135deg,#5CC8FF,#0F5E8A)',
  'linear-gradient(135deg,#F472B6,#7C2D52)',
];
const DEMO=[
  {id:'ad-volt',      brand:'Volt Cycles',   tagline:'E-bike tune-ups from $29 — free pickup this week.',        emoji:'🚲', grad:0},
  {id:'ad-studyfuel', brand:'StudyFuel Café',tagline:'Free coffee with any sandwich before 10 AM.',              emoji:'☕', grad:2},
  {id:'ad-swiftmove', brand:'SwiftMove',     tagline:'Student moving help at honest flat rates.',               emoji:'📦', grad:3},
  {id:'ad-laundry',   brand:'LaundryLoop',   tagline:'Wash & fold pickup near you — first bag half off.',       emoji:'👕', grad:1},
  {id:'ad-pixel',     brand:'PixelPrint',    tagline:'Posters & resumes printed in about an hour.',             emoji:'🖨️', grad:4},
];
let rot=0;
function nextAds(n){
  /* Round-robin rotation. DEMO ONLY — production replaces this with the real
     ad server; any targeting there must be opt-in and never sell user data. */
  const out=[];
  for(let i=0;i<n;i++){ out.push(DEMO[(rot+i)%DEMO.length]); }
  rot=(rot+n)%DEMO.length;
  return out;
}
function findAd(id){ return DEMO.find(a=>a.id===id)||null; }

/* ---------------- shared label fragments ---------------- */
function sponsoredLabels(){
  return '<span class="badge adsponsored">'+t('ads.sponsored')+'</span>'+
         '<span class="badge addemo">'+t('ads.demoAd')+'</span>';
}

/* ---------------- 1. market feed: interleaved sponsored cards ---------------- */
function feedCard(ad){
  const bg=AD_GRADS[ad.grad%AD_GRADS.length];
  return '<div class="item adcard" data-adcard="'+ad.id+'" role="article" aria-label="'+HUB.ui.esc(ad.brand)+' — '+HUB.ui.esc(t('ads.sponsored'))+'">'+
    '<div class="adthumb" style="background:'+bg+'"><span>'+ad.emoji+'</span></div>'+
    '<div class="grow">'+
      '<div style="display:flex;gap:6px;align-items:center;margin-bottom:5px;flex-wrap:wrap">'+sponsoredLabels()+'</div>'+
      '<h3>'+HUB.ui.esc(ad.brand)+'</h3>'+
      '<div class="meta">'+HUB.ui.esc(ad.tagline)+'</div>'+
      '<div style="margin-top:8px"><span class="adcta">'+t('ads.learnMore')+' →</span></div>'+
    '</div></div>';
}
/* Build the market list HTML with sponsored cards interleaved. `cards` is the
   array of organic listing card strings. Returns the joined HTML. */
function interleaveFeed(cards){
  const out=[];
  let adsUsed=0;
  const adPool=nextAds(RULES.marketFeedMax);
  for(let i=0;i<cards.length;i++){
    out.push(cards[i]);
    if((i+1)%RULES.marketFeedEvery===0 && adsUsed<RULES.marketFeedMax && adPool[adsUsed]){
      out.push(feedCard(adPool[adsUsed])); adsUsed++;
    }
  }
  return out.join('');
}
/* Wire taps on any [data-adcard] inside scopeEl (call after innerHTML). */
function bind(scopeEl){
  if(!scopeEl||!scopeEl.querySelectorAll) return;
  scopeEl.querySelectorAll('[data-adcard]').forEach(function(el){
    el.style.cursor='pointer';
    el.onclick=function(e){ e.stopPropagation(); openDemoSheet(el.dataset.adcard); };
  });
  scopeEl.querySelectorAll('[data-adtile]').forEach(function(el){
    el.onclick=function(e){ e.stopPropagation(); openDemoSheet(el.dataset.adtile); };
  });
}

/* ---------------- 2. home: "Sponsored near you" carousel ---------------- */
function carouselHTML(){
  const ads=nextAds(RULES.homeCarouselMax);
  let h='<div class="adcarwrap"><div class="hsec-hd">'+
    '<h2>'+t('ads.sponsoredNearYou')+'</h2>'+
    '<span class="hsec-act" style="cursor:default">'+t('ads.demoAd')+'</span></div>'+
    '<div class="adcarousel" role="list" aria-label="'+HUB.ui.esc(t('ads.sponsoredNearYou'))+'">';
  ads.forEach(function(ad){
    const bg=AD_GRADS[ad.grad%AD_GRADS.length];
    h+='<button class="adtile" data-adtile="'+ad.id+'" role="listitem" aria-label="'+HUB.ui.esc(ad.brand)+' — '+HUB.ui.esc(t('ads.sponsored'))+'">'+
      '<span class="adtile-emoji" style="background:'+bg+'">'+ad.emoji+'</span>'+
      '<span class="adtile-brand">'+HUB.ui.esc(ad.brand)+'</span>'+
      '<span class="adtile-tag">'+HUB.ui.esc(ad.tagline)+'</span>'+
      '<span class="badge adsponsored" style="font-size:9px;padding:2px 8px">'+t('ads.sponsored')+'</span>'+
    '</button>';
  });
  h+='</div><p class="hnote">'+t('ads.demoNote')+'</p></div>';
  return h;
}

/* ---------------- demo honesty sheet ---------------- */
function openDemoSheet(adId){
  const ad=findAd(adId); if(!ad||!HUB.ui) return;
  const bg=AD_GRADS[ad.grad%AD_GRADS.length];
  HUB.ui.openSheet(
    '<div style="display:flex;gap:12px;align-items:center;margin-bottom:12px">'+
      '<div class="adthumb" style="background:'+bg+';width:64px;height:64px;font-size:30px"><span>'+ad.emoji+'</span></div>'+
      '<div><h2 style="margin:0 0 4px">'+HUB.ui.esc(ad.brand)+'</h2>'+
      '<div style="display:flex;gap:6px;flex-wrap:wrap">'+sponsoredLabels()+'</div></div>'+
    '</div>'+
    '<h3 style="margin-bottom:6px">'+t('ads.demoSheet')+'</h3>'+
    '<p class="sub" style="margin-bottom:10px">'+HUB.ui.esc(ad.tagline)+'</p>'+
    '<p class="hint" style="margin-bottom:14px">'+t('ads.demoSheetSub')+'</p>'+
    '<button class="btn btn-primary btn-block" id="adDemoLink">'+t('ads.learnMore')+'</button>'+
    '<button class="btn btn-ghost btn-block" id="adDemoClose" style="margin-top:8px">'+t('common.close')+'</button>'
  );
  document.getElementById('adDemoClose').onclick=HUB.ui.closeSheet;
  /* Demo inventory has no real destination — say so instead of navigating. */
  document.getElementById('adDemoLink').onclick=function(){
    HUB.ui.closeSheet();
    HUB.ui.toast(t('ads.demoAd')+' — '+t('ads.demoNote'));
  };
}

HUB.ads={
  RULES:RULES,
  interleaveFeed:interleaveFeed, feedCard:feedCard, bind:bind,
  carouselHTML:carouselHTML,
  openDemoSheet:openDemoSheet,
  isAd:function(s){ return !!(s&&(s.ad||s.adId)); },
};
})();
