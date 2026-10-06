/* HUB HOME tab: greeting, summary stats, Explore Nearby, Ask Orbit (demo assistant), events preview.
   Everything below reads from HUB.store state (real + sample-flagged seeds). */
(function(){
'use strict';
const {store,ui}=HUB;
HUB.views=HUB.views||{};

const DAY=86400e3;

function docsNeedingAttention(){
  const now=Date.now();
  return store.state.memory.filter(m=>m.expiry && (m.expiry-now)<=45*DAY);
}

function statCard(icon,label,value,tab,sub){
  return '<div class="stat" data-goto="'+tab+'" style="cursor:pointer;text-align:left">'+
    '<div class="n">'+HUB.icons.icon(icon)+'<span>'+value+'</span></div>'+
    '<div class="l">'+label+'</div>'+
    (sub?'<div class="l" style="margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+sub+'</div>':'')+
  '</div>';
}

/* Ask Orbit lives in the ai domain module (js/ai.js). */
function askAnswer(q){ return HUB.ai.answer(q); }

HUB.views.home={
  render(el){
    const st=store.state, me=store.myName();
    const owed=store.householdOwed();
    const unread=store.unreadCount();
    const openJobs=st.jobs.filter(j=>j.status==='open');
    const docs=docsNeedingAttention();
    const events=st.events;
    const billTxt=owed.billDue? ui.esc(owed.billDue.item)+' '+ui.fmt$(owed.billDue.amount) : '—';

    // one honest hint if everything shown comes from samples
    const sampleBits=[openJobs,events,docs].flat();
    const allSample=sampleBits.length>0 && sampleBits.every(x=>x.sample);

    el.innerHTML =
      // 1. greeting header
      '<div style="padding:8px 0 14px"><div class="greet">'+ui.esc(ui.greeting())+', <span class="hl">'+ui.esc(me)+'</span></div>'+
      '<div class="sub" style="margin-top:4px">Your world today.</div></div>'+

      // 2. summary stat cards
      '<div class="grid2" id="homeStats" style="margin-bottom:14px">'+
        statCard('stat-money','Owed to you',ui.fmt$(owed.owedToMe),'groups')+
        statCard('stat-messages','Unread messages',String(unread),'home')+  // opens chat via chatFab; tab target handled below
        statCard('stat-jobs','Jobs near you',String(openJobs.length),'work')+
        statCard('stat-bill','Bill due',billTxt,'groups')+
        statCard('stat-events','Today\'s events',String(events.length),'discover')+
        statCard('stat-docs','Docs needing attention',String(docs.length),'me')+
      '</div>'+
      (allSample?'<p class="hint" style="margin:-6px 0 14px">Preview numbers use sample data until you add your own.</p>':'')+

      // 3. Explore Nearby
      '<button class="btn btn-primary btn-block" id="homeExplore" style="margin-bottom:16px">'+HUB.icons.icon('nav-discover')+' Explore Nearby →</button>'+

      // 4. Ask Orbit
      '<div class="card"><div class="row between"><h3 class="askh3">'+HUB.icons.icon('ask-hub')+'Ask Orbit</h3><span class="badge b-BUY">Demo assistant</span></div>'+
        '<p class="sub" style="margin-top:6px">Keyword-based demo helper — answers read from your actual Orbit data.</p>'+
        '<div class="askbox"><input class="input" id="askInput" placeholder="Try: moving, money, jobs…"><button class="btn btn-dark btn-sm" id="askSend">Send</button></div>'+
        '<div id="askResults"></div></div>'+

      // 5. events preview
      '<div class="row between" style="margin:4px 0 10px"><h2>What\'s happening</h2><button class="linklike" data-goto="discover">See all →</button></div>'+
      '<div id="homeEvents">'+
        (events.length? events.slice(0,3).map(e=>
          '<div class="item tight"><div style="font-size:28px">'+ui.esc(e.emoji)+'</div><div class="grow"><h3>'+ui.esc(e.title)+'</h3><div class="meta">'+ui.esc(e.time)+' · '+ui.esc(e.where)+'</div></div>'+ui.sampleBadge(e.sample)+'</div>'
        ).join('') : '<div class="empty"><span class="empty-ico">'+HUB.icons.icon('stat-events')+'</span><h3>No events yet</h3><p class="sub">See what\'s around you, or create something worth showing up for.</p><button class="btn btn-ghost btn-sm" id="homeEventsEmpty">Explore Discover →</button></div>')+
      '</div>';

    // ---- bindings (after innerHTML) ----
    document.getElementById('homeExplore').onclick=()=>HUB.showTab('discover');
    const hee=document.getElementById('homeEventsEmpty');
    if(hee) hee.onclick=()=>HUB.showTab('discover');

    HUB.ai.bindGotos(el); // generic [data-goto] navigation

    // stat taps: 📦 unread messages opens chat instead of a tab (must run after bindGotos)
    el.querySelectorAll('#homeStats [data-goto]').forEach(card=>{
      const label=card.querySelector('.l')?card.querySelector('.l').textContent:'';
      if(label==='Unread messages'){
        card.onclick=()=>{ if(HUB.chat) HUB.chat.openList(); };
      }
    });

    // Ask Orbit
    const input=document.getElementById('askInput'), results=document.getElementById('askResults');
    const runAsk=()=>{
      const q=input.value.trim();
      if(!q){ ui.toast('Type a question first'); return; }
      const card=document.createElement('div');
      card.className='card tight';
      card.style.marginTop='12px';
      card.innerHTML='<div class="sub" style="margin-bottom:8px">You asked: <b>'+ui.esc(q)+'</b></div>'+askAnswer(q);
      HUB.ai.bindGotos(card);
      results.prepend(card);
      input.value='';
    };
    document.getElementById('askSend').onclick=runAsk;
    input.addEventListener('keydown',e=>{ if(e.key==='Enter') runAsk(); });
  }
};
})();
