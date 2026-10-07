/* HUB GROUPS tab: Households (Roommate OS) + Communities.
   Sub-tab state and open-household state live in module vars so
   render() stays idempotent. All user data escaped. Seeds flagged. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
HUB.views=HUB.views||{};

let sub='clubs';        // 'clubs' | 'households' | 'campus' ('campus' = Communities view; key kept as internal identifier)
let openHh=null;        // household id in detail view, or null
let openClub=null;      // community-group id in detail view, or null
let clubQuery='';       // discovery search text (module-level so input keeps it across repaints)

function rerender(){ const el=document.getElementById('view-groups'); if(el) HUB.views.groups.render(el); }

function fmtShare(n){ return ui.fmt$(Math.round(n*100)/100); }
function oweName(n){ return n===store.myName()?t('groups.you'):n; }

/* receipt photo for bills: downscaled client-side to ~800px JPEG so it stays
   small in browser-local storage. Visible to everyone in the household. */
let billPhotoData='';
function readBillPhoto(file){
  billPhotoData='';
  const prev=document.getElementById('bPhotoPrev');
  const hide=()=>{ if(prev){ prev.removeAttribute('src'); prev.hidden=true; } };
  if(!file){ hide(); return; }
  const url=URL.createObjectURL(file), img=new Image();
  img.onload=()=>{
    URL.revokeObjectURL(url);
    const mx=800, sc=Math.min(1,mx/Math.max(img.width||1,img.height||1));
    const w=Math.max(1,Math.round(img.width*sc)), h=Math.max(1,Math.round(img.height*sc));
    const cv=document.createElement('canvas'); cv.width=w; cv.height=h;
    cv.getContext('2d').drawImage(img,0,0,w,h);
    billPhotoData=cv.toDataURL('image/jpeg',0.72);
    if(prev){ prev.src=billPhotoData; prev.hidden=false; }
  };
  img.onerror=()=>{ URL.revokeObjectURL(url); hide(); };
  img.src=url;
}

/* household photo: same ~800px JPEG downscale, stored on the household record */
let hhPhotoData='';
function readHousePhoto(file, prevId){
  const prev=prevId?document.getElementById(prevId):null;
  if(!file){ if(prev){ prev.removeAttribute('src'); prev.hidden=true; } return; }
  const url=URL.createObjectURL(file), img=new Image();
  img.onload=()=>{
    URL.revokeObjectURL(url);
    const mx=800, sc=Math.min(1,mx/Math.max(img.width||1,img.height||1));
    const w=Math.max(1,Math.round(img.width*sc)), h=Math.max(1,Math.round(img.height*sc));
    const cv=document.createElement('canvas'); cv.width=w; cv.height=h;
    cv.getContext('2d').drawImage(img,0,0,w,h);
    hhPhotoData=cv.toDataURL('image/jpeg',0.72);
    if(prev){ prev.src=hhPhotoData; prev.hidden=false; }
  };
  img.onerror=()=>{ URL.revokeObjectURL(url); };
  img.src=url;
}

/* ---------- aggregated balances for a household ----------
   Per bill: share = amount / split-members; every member except paidBy
   owes share to paidBy. Aggregate pairwise. Bills remember the members
   present when they were added (b.split); older bills fall back to the
   current member list. Removing a member keeps their existing shares
   honest (they still settle) while new bills exclude them. */
function hhAdmin(h){ return h.admin||h.members[0]||''; }
function hhIsAdmin(h){ return ui.isMe(hhAdmin(h)); }
/* Join-request decision (admin only). Approval adds the requester to the
   member list unless they're already there; both paths clear the request. */
function hhRequestDecide(h,name,approve){
  if(!hhIsAdmin(h)){ ui.toast(t('hh.notAdmin')); return; }
  const nmL=String(name||'').toLowerCase();
  h.requests=(h.requests||[]).filter(function(r){ return String(r.name||'').toLowerCase()!==nmL; });
  if(approve&&!h.members.some(function(m){ return String(m||'').toLowerCase()===nmL; })) h.members.push(name);
  store.save(); rerender();
  ui.toast(approve?t('hh.join.approved',{name:name}):t('hh.join.declined'));
}
function hhSplit(h,b){ return (b.split&&b.split.length)?b.split:h.members; }
function balances(h){
  const agg={};
  for(const b of h.bills){
    const amt=Number(b.amount)||0; if(amt<=0) continue;
    const sp=hhSplit(h,b), share=amt/(sp.length||1);
    for(const m of sp){
      if(m===b.paidBy) continue;
      const k=m+'\u0000'+b.paidBy;
      agg[k]=(agg[k]||0)+share;
    }
  }
  return Object.keys(agg).map(k=>{
    const [from,to]=k.split('\u0000');
    return {from,to,amt:Math.round(agg[k]*100)/100};
  }).filter(r=>r.amt>0.004);
}

/* ---- shared segment bar (all Groups-tab surfaces) ----
   Clubs (new community groups) | Households | Communities | People.
   gu-seg scopes the water-crystal restyle: bare .seg is ALSO used by the
   me.js gender picker, which must stay untouched. */
/* Groups UI (2026-09-23): decorative floating sparkle motes for surface
   headers — pure CSS animation, pointer-events:none, aria-hidden. */
function guMotes(){
  return '<div class="gu-motes" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div>';
}
/* ---- glossy-3D hero banner (2026-10-05 redesign) ----
   Gradient-bordered glossy banner with the volt-green groups icon,
   title + subtitle. Purely presentational; strings stay i18n-keyed. */
function grHero(title,sub){
  return '<div class="gr-hero">'+guMotes()
    +'<div class="gr-hero-ico" aria-hidden="true">'+HUB.icons.icon('qa-groups')+'</div>'
    +'<div class="gr-hero-tx"><h1>'+title+'</h1><p>'+sub+'</p></div>'
    +'</div>';
}
/* ---- group category pill (2026-10-05 redesign) ----
   Display label derived from the group's own name/description keywords.
   No category is stored or invented; unmatched groups get "Community". */
function cgCatKey(g){
  const s=((g.name||'')+' '+(g.desc||'')).toLowerCase();
  const hit=function(){ for(let i=0;i<arguments.length;i++){ if(s.indexOf(arguments[i])>=0) return true; } return false; };
  if(hit('study','math','exam','homework','school','class','tutor','learn')) return 'grp.cat.study';
  if(hit('game','gaming','pubg','esport','squad','chess')) return 'grp.cat.gaming';
  if(hit('run','fitness','gym','workout','yoga','sport','soccer','basketball','cycling')) return 'grp.cat.fitness';
  if(hit('music','guitar','band','jam','piano','sing')) return 'grp.cat.music';
  if(hit('food','cook','boba','coffee','dinner','lunch','brunch','restaurant','food truck')) return 'grp.cat.food';
  if(hit('book','read','novel','library')) return 'grp.cat.books';
  if(hit('art','design','photo','draw','sketch','paint')) return 'grp.cat.art';
  if(hit('code','coding','hackathon','tech','robot','developer','program')) return 'grp.cat.tech';
  if(hit('travel','hike','outdoor','camp','nature','adventure')) return 'grp.cat.outdoors';
  return 'grp.cat.community';
}
function segBar(){
  const items=[['clubs',t('cg.seg.groups')],['households',t('groups.seg.hh')],['campus',t('groups.seg.campus')],['people',t('groups.seg.people')]];
  return '<div class="seg gu-seg">'+items.map(function(it){
    return '<button data-sub="'+it[0]+'"'+(sub===it[0]?' class="on"':'')+'>'+it[1]+'</button>';
  }).join('')+'</div>';
}
function bindSeg(scope){
  scope.querySelectorAll('.seg [data-sub]').forEach(function(b){
    b.onclick=function(){ sub=b.dataset.sub; openHh=null; openClub=null; rerender(); };
  });
}

/* ================= HOUSEHOLDS LIST ================= */
function renderHouseholdsList(el){
  const hs=store.state.households;
  let html='<div class="gu">'+grHero(ui.esc(t('groups.title')),ui.esc(t('groups.subHome')));
  html+=segBar();
  html+='<button class="btn btn-ghost btn-block gu-new" id="newHh">'+t('groups.newHh')+'</button><div style="height:12px"></div>';
  if(!hs.length){
    html+='<div class="empty ps-empty"><div class="big">🏠</div><p>'+t('groups.emptyHh')+'</p></div>';
  }
  let hhI=0;
  for(const h of hs){
    const tot=h.bills.reduce((a,b)=>a+(Number(b.amount)||0),0);
    const bal=balances(h).filter(r=>r.to===store.myName());
    const owedIn=bal.reduce((a,r)=>a+r.amt,0);
    const openChores=h.chores.filter(c=>!c.done).length;
    html+='<div class="card tight hh-card hh-glass gu-hh gr-card" data-hh="'+h.id+'" style="cursor:pointer;--i:'+(hhI++)+'">'
      +'<div class="row between"><h3>'+ui.esc(h.name)+'</h3><span style="display:flex;gap:6px;align-items:center">'+ui.sampleBadge(h.sample)+'<span class="hhpriv">🔒 '+t('hh.priv')+'</span></span></div>'
      +'<div class="row" style="gap:10px;margin-top:6px;align-items:center">'
      +(h.photo?'<img class="hhphoto" src="'+ui.esc(h.photo)+'" alt="" style="width:44px;height:44px">':'')
      +'<div class="meta grow" style="margin-top:0">'+ui.esc(h.members.join(' · '))+'</div></div>'
      +'<div class="row between" style="margin-top:10px"><span class="sub">'+t('groups.hhBills',{n:h.bills.length})+' · '+t('groups.hhChores',{n:openChores})+'</span>'
      +'<span class="money '+(owedIn>0?'pos':'')+'" style="font-size:16px">'+(owedIn>0?t('groups.owedToYou',{amt:ui.fmt$(owedIn)}):t('groups.total',{amt:ui.fmt$(tot)}))+'</span></div>'
      +'</div>';
  }
  el.innerHTML=html+'</div>';
  bindSeg(el);
  el.querySelector('#newHh').onclick=newHouseholdSheet;
  el.querySelectorAll('.hh-card').forEach(c=>{ c.onclick=()=>{ openHh=c.dataset.hh; rerender(); }; });
}

function newHouseholdSheet(){
  const me=store.myName();
  ui.openSheet(
    '<h2>'+t('groups.nh.title')+'</h2>'
    +'<div class="field"><label>'+t('groups.nh.name')+'</label><input class="input" id="nhName" placeholder="'+t('groups.nh.namePh')+'"></div>'
    +'<div class="field"><label>'+t('groups.nh.members')+'</label><input class="input" id="nhMembers" placeholder="'+t('groups.nh.membersPh')+'" value="'+ui.esc(me)+'"></div>'
    +'<div class="field"><label>'+t('hh.photo')+'</label><input type="file" id="nhPhoto" accept="image/*" class="input" style="padding:10px">'
    +'<img id="nhPhotoPrev" hidden style="width:100%;border-radius:12px;margin-top:8px" alt=""></div>'
    +'<p class="hint">🔒 '+t('hh.priv')+' · '+t('hh.nh.autoNote')+'</p>'
    +'<button class="btn btn-primary btn-block" id="nhSave">'+t('groups.nh.save')+'</button>'
  );
  hhPhotoData='';
  document.getElementById('nhPhoto').onchange=e=>{ readHousePhoto(e.target.files&&e.target.files[0],'nhPhotoPrev'); };
  document.getElementById('nhSave').onclick=()=>{
    const name=document.getElementById('nhName').value.trim();
    if(!name){ui.toast(t('groups.nh.needName'));return;}
    const raw=document.getElementById('nhMembers').value.split(',').map(s=>s.trim()).filter(Boolean);
    const seen=new Set(), members=[];
    for(const m of raw){ if(!seen.has(m.toLowerCase())){seen.add(m.toLowerCase());members.push(m);} }
    if(!members.some(m=>m===me)) members.unshift(me);
    store.state.households.unshift({id:store.uid(),name,members,photo:hhPhotoData||'',admin:me,private:true,requests:[],bills:[],chores:[],shopping:[],notes:[],polls:[],sample:false});
    store.save(); ui.closeSheet(); openHh=store.state.households[0].id; sub='households'; rerender();
    ui.toast(t('groups.nh.done'));
  };
}

/* ================= HOUSEHOLD DETAIL ================= */
function renderHouseholdDetail(el, h){
  const me=store.myName(), isAdmin=hhIsAdmin(h);
  h.requests=h.requests||[];
  const meL=String(me||'').toLowerCase();
  const meIsMember=h.members.some(function(m){ return String(m||'').toLowerCase()===meL; });
  const meRequested=(h.requests||[]).some(function(r){ return String(r.name||'').toLowerCase()===meL; });
  /* Non-members (e.g. arriving via a #hjoin invite deep link) get a minimal
     gate: household name + request-to-join CTA. Bills, chores, member lists
     and announcements stay private until the admin approves them. */
  if(!meIsMember){
    el.innerHTML='<div class="gu"><button class="linklike gu-back" id="hhBack" style="margin-bottom:10px">'+t('groups.back')+'</button>'
      +'<h1 class="greet">'+ui.esc(h.name)+'</h1>'
      +'<p class="sub" style="margin:4px 0 14px">🔒 '+ui.esc(t('hh.priv'))+' · '+ui.esc(t('hh.join.members',{n:h.members.length}))+'</p>'
      +'<div class="card frq-card"><h2 style="margin-bottom:6px">🙋 '+ui.esc(t('hh.join.reqT'))+'</h2>'
      +'<p class="sub" style="margin:0 0 12px;line-height:1.55">'+ui.esc(t('hh.join.reqD',{name:h.name}))+'</p>'
      +(meRequested
        ?'<button class="btn btn-line btn-block" id="hhReqJoin" disabled>'+ui.esc(t('hh.join.reqHave'))+'</button>'
        :'<button class="btn btn-primary btn-block" id="hhReqJoin">'+ui.esc(t('hh.join.reqGo'))+'</button>')
      +'</div></div>';
    document.getElementById('hhBack').onclick=()=>{openHh=null;rerender();};
    const rqj=document.getElementById('hhReqJoin');
    if(rqj) rqj.onclick=()=>{
      if(!(h.requests||[]).some(function(r){ return String(r.name||'').toLowerCase()===meL; }))
        h.requests.push({name:me,at:Date.now()});
      store.save(); rerender(); ui.toast(t('hh.join.reqSent'));
    };
    return;
  }
  let html='<div class="gu"><button class="linklike gu-back" id="hhBack" style="margin-bottom:10px">'+t('groups.back')+'</button>';
  html+='<div class="row gu-hhrow" style="gap:12px;align-items:center">'+guMotes()
    +(h.photo?'<img class="hhphoto" src="'+ui.esc(h.photo)+'" alt="">':'')
    +'<div class="grow"><h1 class="greet gu-title" style="margin:0">'+ui.esc(h.name)+'</h1>'
    +'<div class="meta" style="margin-top:5px"><span class="hhpriv">🔒 '+t('hh.priv')+'</span> '+ui.sampleBadge(h.sample)+'</div></div>'
    +(isAdmin?'<button class="btn btn-line btn-sm" id="hhManage">⚙️ '+t('hh.manage')+'</button>':'')
    +'</div>';
  html+='<div class="cgchips" style="margin:10px 0 16px">'+h.members.map(function(m){
    return '<span class="cgchip"><span class="avatar">'+ui.avatarFor(m)+'</span>'+ui.esc(m)+(m===hhAdmin(h)?' 👑':'')+'</span>';
  }).join('')+'</div>';

  /* ---- household invite link + join requests (admin only) ---- */
  if(isAdmin){
    html+='<button class="btn btn-line btn-block" id="hhInviteLink" style="margin:0 0 4px">🔗 '+ui.esc(t('hh.join.invite'))+'</button>';
    const hjr=h.requests||[];
    html+='<div class="card frq-card"><div class="row between"><h2 style="margin:0">🙋 '+ui.esc(t('hh.join.pending'))+'</h2><span class="meta">'+hjr.length+'</span></div><div style="margin-top:10px">';
    if(!hjr.length) html+='<p class="sub">'+ui.esc(t('hh.join.noPending'))+'</p>';
    else for(const r of hjr){
      html+='<div class="kv"><div><div style="font-weight:700">'+ui.esc(r.name)+'</div><div class="meta">'+ui.timeAgo(r.at||Date.now())+'</div></div>'
        +'<div class="row" style="gap:6px"><button class="btn btn-primary btn-sm" data-happr="'+ui.esc(r.name)+'">'+ui.esc(t('hh.join.approve'))+'</button>'
        +'<button class="btn btn-line btn-sm" data-hdecl="'+ui.esc(r.name)+'">'+ui.esc(t('hh.join.decline'))+'</button></div></div>';
    }
    html+='</div></div>';
  }

  /* ---- Bills ---- */
  html+='<div class="card"><div class="row between"><h2>'+t('groups.bills')+'</h2><button class="btn btn-sm btn-ghost" id="addBill">'+t('groups.addBill')+'</button></div>';
  if(!h.bills.length){ html+='<p class="sub" style="margin-top:8px">'+t('groups.noBills')+'</p>'; }
  else{
    html+='<div class="hhbills" style="margin-top:8px">';
    for(let bi=0;bi<h.bills.length;bi++){
      const b=h.bills[bi];
      const spN=(b.split&&b.split.length)?b.split.length:(h.members.length||1), share=b.amount/spN;
      const core='<div style="min-width:0"><div style="font-weight:700">'+ui.esc(b.item)+'</div>'
        +'<div class="sub" style="font-size:12px">'+t('groups.billMeta',{name:ui.esc(oweName(b.paidBy)),due:ui.esc(b.due||'—'),share:fmtShare(share)})+'</div></div>'
        +(b.photo?'<img class="bill-thumb" data-bi="'+bi+'" src="'+ui.esc(b.photo)+'" alt="'+ui.esc(t('groups.viewReceipt'))+'" style="width:46px;height:46px;object-fit:cover;border-radius:10px;cursor:pointer;flex:none">':'')
        +'<div class="money" style="font-size:16px;margin-left:auto;flex:none">'+fmtShare(Number(b.amount)||0)+'</div>'
        +(isAdmin?'<button class="linklike hhb-more" data-bid="'+b.id+'" aria-label="'+ui.esc(t('hh.bill.options'))+'" style="flex:none;font-size:20px;line-height:1">⋯</button>':'');
      if(isAdmin){
        html+='<div class="hhb" data-bid="'+b.id+'"><div class="hhb-actions">'
          +'<button class="ba-edit" data-act="edit">'+ui.esc(t('hh.bill.edit'))+'</button>'
          +'<button class="ba-del" data-act="del">'+ui.esc(t('hh.bill.del'))+'</button>'
          +'</div><div class="hhb-inner">'+core+'</div></div>';
      }else{
        html+='<div class="kv">'+core+'</div>';
      }
    }
    html+='</div>';
  }
  const bal=balances(h);
  html+='<div class="divider"></div><h3 style="margin-bottom:6px">'+t('groups.balances')+'</h3>';
  if(!bal.length) html+='<p class="sub">'+t('groups.settled')+'</p>';
  else for(const r of bal) html+='<div class="kv"><span>'+t('groups.owes',{from:ui.esc(oweName(r.from)),to:ui.esc(oweName(r.to))})+'</span><span class="money" style="font-size:15px;color:var(--amber)">'+fmtShare(r.amt)+'</span></div>';
  html+='</div>';

  /* ---- Chores ---- */
  html+='<div class="card"><div class="row between"><h2>'+t('groups.chores')+'</h2><button class="btn btn-sm btn-ghost" id="addChore">'+t('groups.add')+'</button></div><div style="margin-top:8px">';
  if(!h.chores.length) html+='<p class="sub">'+t('groups.noChores')+'</p>';
  for(const c of h.chores){
    html+='<div class="item tight chore" data-cid="'+c.id+'" style="cursor:pointer;margin-bottom:8px;padding:10px 12px">'
      +'<span style="font-size:20px">'+(c.done?'✅':'⬜')+'</span>'
      +'<div class="grow"><h3 style="'+(c.done?'text-decoration:line-through;color:var(--faint)':'')+'">'+ui.esc(c.task)+'</h3>'
      +'<div class="meta">'+ui.esc(c.who||t('groups.anyone'))+'</div></div></div>';
  }
  html+='</div></div>';

  /* ---- Shopping ---- */
  const bought=h.shopping.filter(s=>s.done).length;
  html+='<div class="card"><div class="row between"><h2>'+t('groups.shopping')+'</h2><div class="row" style="gap:6px"><button class="btn btn-sm btn-line" id="clearBought">'+t('groups.clearBought')+'</button><button class="btn btn-sm btn-ghost" id="addShop">'+t('groups.add')+'</button></div></div><div style="margin-top:8px">';
  if(!h.shopping.length) html+='<p class="sub">'+t('groups.listEmpty')+'</p>';
  for(const s of h.shopping){
    html+='<div class="item tight shop" data-sid="'+s.id+'" style="cursor:pointer;margin-bottom:8px;padding:10px 12px">'
      +'<span style="font-size:20px">'+(s.done?'✅':'⬜')+'</span>'
      +'<div class="grow"><h3 style="'+(s.done?'text-decoration:line-through;color:var(--faint)':'')+'">'+ui.esc(s.item)+'</h3></div></div>';
  }
  if(bought) html+='<p class="hint">'+t('groups.bought',{n:bought})+'</p>';
  html+='</div></div>';

  /* ---- Announcements ---- */
  html+='<div class="card"><h2 style="margin-bottom:8px">'+t('groups.announce')+'</h2>'
    +'<div class="askbox"><input class="input" id="noteText" placeholder="'+t('groups.notePh')+'"><button class="btn btn-primary btn-sm" id="notePost">'+t('groups.cp.post')+'</button></div><div style="margin-top:10px">';
  if(!h.notes.length) html+='<p class="sub">'+t('groups.nothingPosted')+'</p>';
  const notes=[...h.notes].sort((a,b)=>(b.at||0)-(a.at||0));
  for(const n of notes) html+='<div class="item tight" style="padding:10px 12px;margin-bottom:8px"><div class="grow"><div style="font-size:14px">'+ui.esc(n.text)+'</div><div class="meta">'+ui.timeAgo(n.at||Date.now())+'</div></div></div>';
  html+='</div></div>';

  /* ---- Polls ---- */
  html+='<div class="card"><div class="row between"><h2>'+t('groups.polls')+'</h2><button class="btn btn-sm btn-ghost" id="addPoll">'+t('groups.newPoll')+'</button></div><div style="margin-top:10px">';
  if(!h.polls.length) html+='<p class="sub">'+t('groups.noPolls')+'</p>';
  for(const p of h.polls){
    const total=p.opts.reduce((a,o)=>a+(o.v||0),0);
    html+='<div style="margin-bottom:14px"><div class="row between"><strong style="font-size:15px">'+ui.esc(p.q)+'</strong>'+ui.sampleBadge(p.sample)+'</div>';
    p.opts.forEach((o,i)=>{
      const pct=total?Math.round(o.v/total*100):0;
      if(p.voted){
        html+='<div style="margin-top:6px"><div class="row between"><span style="font-size:13.5px">'+ui.esc(o.t)+'</span><span class="meta">'+o.v+' · '+pct+'%</span></div><div class="pollbar"><i style="width:'+pct+'%"></i></div></div>';
      }else{
        html+='<button class="btn btn-line btn-sm btn-block vote" data-pid="'+p.id+'" data-oi="'+i+'" style="margin-top:6px">'+ui.esc(o.t)+'</button>';
      }
    });
    if(p.voted) html+='<p class="hint">'+t('groups.youVoted',{n:total,v:t('groups.vote',{n:total})})+'</p>';
    html+='</div>';
  }
  html+='</div></div>';

  el.innerHTML=html+'</div>';
  document.getElementById('hhBack').onclick=()=>{openHh=null;rerender();};

  /* admin controls: manage household + swipe-to-edit/delete on bills */
  const hhM=document.getElementById('hhManage');
  if(hhM) hhM.onclick=()=>manageHouseholdSheet(h);
  /* household invite link + join requests (admin only) */
  const hhi=document.getElementById('hhInviteLink');
  if(hhi) hhi.onclick=()=>openHhInviteSheet(h);
  el.querySelectorAll('[data-happr]').forEach(function(b){
    b.onclick=function(){ hhRequestDecide(h,b.dataset.happr,true); };
  });
  el.querySelectorAll('[data-hdecl]').forEach(function(b){
    b.onclick=function(){ hhRequestDecide(h,b.dataset.hdecl,false); };
  });
  if(isAdmin){
    el.querySelectorAll('.hhb').forEach(row=>{ bindBillSwipe(row,h); });
    el.querySelectorAll('.hhb-more').forEach(btn=>{
      btn.onclick=e=>{ e.stopPropagation(); billActionsSheet(h,btn.dataset.bid); };
    });
  }

  /* receipt photo viewer — everyone in the household can see it */
  el.querySelectorAll('.bill-thumb').forEach(th=>{
    th.onclick=()=>{
      const b=h.bills[Number(th.dataset.bi)];
      if(!b||!b.photo) return;
      ui.openSheet('<h2>'+ui.esc(b.item)+'</h2>'
        +'<p class="sub" style="margin-bottom:10px">'+ui.esc(t('groups.viewReceipt'))+' · '+ui.esc(oweName(b.paidBy))+' · '+fmtShare(Number(b.amount)||0)+'</p>'
        +'<img src="'+ui.esc(b.photo)+'" style="width:100%;border-radius:14px" alt="'+ui.esc(t('groups.viewReceipt'))+'">');
    };
  });

  /* bills: shared add/edit sheet (edit = admin only, via swipe or ⋯) */
  document.getElementById('addBill').onclick=()=>billFormSheet(h,null);

  /* chores */
  document.getElementById('addChore').onclick=()=>{
    const opts=h.members.map(m=>'<option'+(m===me?' selected':'')+'>'+ui.esc(m)+'</option>').join('');
    ui.openSheet(
      '<h2>'+t('groups.ac.title')+'</h2>'
      +'<div class="field"><label>'+t('groups.ac.task')+'</label><input class="input" id="cTask" placeholder="'+t('groups.ac.taskPh')+'"></div>'
      +'<div class="field"><label>'+t('groups.ac.who')+'</label><select class="input" id="cWho">'+opts+'</select></div>'
      +'<button class="btn btn-primary btn-block" id="cSave">'+t('groups.ac.save')+'</button>'
    );
    document.getElementById('cSave').onclick=()=>{
      const task=document.getElementById('cTask').value.trim();
      if(!task){ui.toast(t('groups.ac.need'));return;}
      h.chores.push({id:store.uid(),task,who:document.getElementById('cWho').value,done:false});
      store.save(); ui.closeSheet(); rerender(); ui.toast(t('groups.ac.done'));
    };
  };
  el.querySelectorAll('.chore').forEach(c=>{ c.onclick=()=>{ const x=h.chores.find(z=>z.id===c.dataset.cid); if(x){x.done=!x.done;store.save();rerender();} }; });

  /* shopping */
  document.getElementById('addShop').onclick=()=>{
    ui.openSheet('<h2>'+t('groups.as.title')+'</h2><div class="field"><label>'+t('groups.as.item')+'</label><input class="input" id="sItem" placeholder="'+t('groups.as.itemPh')+'"></div><button class="btn btn-primary btn-block" id="sSave">'+t('groups.as.save')+'</button>');
    document.getElementById('sSave').onclick=()=>{
      const item=document.getElementById('sItem').value.trim();
      if(!item){ui.toast(t('groups.as.need'));return;}
      h.shopping.push({id:store.uid(),item,done:false});
      store.save(); ui.closeSheet(); rerender(); ui.toast(t('groups.as.done'));
    };
  };
  el.querySelectorAll('.shop').forEach(c=>{ c.onclick=()=>{ const x=h.shopping.find(z=>z.id===c.dataset.sid); if(x){x.done=!x.done;store.save();rerender();} }; });
  document.getElementById('clearBought').onclick=()=>{ h.shopping=h.shopping.filter(s=>!s.done); store.save(); rerender(); ui.toast(t('groups.as.cleared')); };

  /* notes */
  document.getElementById('notePost').onclick=()=>{
    const nt=document.getElementById('noteText').value.trim();
    if(!nt){ui.toast(t('groups.note.need'));return;}
    h.notes.push({id:store.uid(),text:nt,at:Date.now()});
    store.save(); rerender(); ui.toast(t('groups.note.done'));
  };

  /* polls */
  document.getElementById('addPoll').onclick=()=>{
    ui.openSheet(
      '<h2>'+t('groups.ap.title')+'</h2>'
      +'<div class="field"><label>'+t('groups.ap.q')+'</label><input class="input" id="pQ" placeholder="'+t('groups.ap.qPh')+'"></div>'
      +'<div class="field"><label>'+t('groups.ap.opts')+'</label><textarea class="textarea" id="pOpts" placeholder="Yes 🍿&#10;Saturday instead"></textarea></div>'
      +'<button class="btn btn-primary btn-block" id="pSave">'+t('groups.ap.save')+'</button>'
    );
    document.getElementById('pSave').onclick=()=>{
      const q=document.getElementById('pQ').value.trim();
      const opts=document.getElementById('pOpts').value.split('\n').map(s=>s.trim()).filter(Boolean).slice(0,4);
      if(!q){ui.toast(t('groups.ap.needQ'));return;}
      if(opts.length<2){ui.toast(t('groups.ap.needOpts'));return;}
      h.polls.unshift({id:store.uid(),q,opts:opts.map(o=>({t:o,v:0})),voted:false});
      store.save(); ui.closeSheet(); rerender(); ui.toast(t('groups.ap.done'));
    };
  };
  el.querySelectorAll('.vote').forEach(b=>{ b.onclick=()=>{ const p=h.polls.find(z=>z.id===b.dataset.pid); if(p&&!p.voted){ p.opts[Number(b.dataset.oi)].v+=1; p.voted=true; store.save(); rerender(); ui.toast(t('groups.ap.voted')); } }; });
}

/* ================= HOUSEHOLD ADMIN + BILL SWIPE (2026-09-22) =================
   Private households: creator is admin; bills snapshot their member list at
   creation so splits stay honest after removals. Admin-only swipe reveals
   Edit (volt) + Delete (red) on bill rows; a ⋯ button is the non-gesture
   fallback (desktop / headless QA). */
const HH_SWIPE_W=148;
function bindBillSwipe(row,h){
  if(row.dataset.sbound) return; row.dataset.sbound='1';
  const inner=row.querySelector('.hhb-inner');
  let sx=0, dx=0, dragging=false;
  const setX=x=>{ inner.style.transform='translateX('+x+'px)'; };
  row.addEventListener('pointerdown',e=>{ sx=e.clientX; dx=0; dragging=true; inner.style.transition=''; },{passive:true});
  row.addEventListener('pointermove',e=>{
    if(!dragging) return;
    dx=Math.min(0,e.clientX-sx); /* drag left to reveal actions */
    if(dx<0) setX(Math.max(-HH_SWIPE_W,dx));
  },{passive:true});
  const finish=()=>{
    if(!dragging) return; dragging=false;
    const open=dx<-HH_SWIPE_W*0.45;
    inner.style.transition='transform .18s ease';
    setX(open?-HH_SWIPE_W:0);
    setTimeout(()=>{ inner.style.transition=''; },220);
  };
  row.addEventListener('pointerup',finish);
  row.addEventListener('pointercancel',finish);
  row.querySelectorAll('[data-act]').forEach(b=>{
    b.addEventListener('click',e=>{
      e.stopPropagation();
      const bid=row.dataset.bid;
      inner.style.transition='transform .18s ease'; setX(0);
      setTimeout(()=>{ inner.style.transition=''; },220);
      if(b.dataset.act==='del') delBill(h,bid);
      else billFormSheet(h,bid);
    });
  });
}
function delBill(h,bid){
  if(!hhIsAdmin(h)){ ui.toast(t('hh.notAdmin')); return; }
  const b=h.bills.find(x=>x.id===bid); if(!b) return;
  if(confirm(t('hh.bill.delC'))){
    h.bills=h.bills.filter(x=>x.id!==bid);
    store.save(); rerender(); ui.toast(t('hh.bill.delDone'));
  }
}
function billActionsSheet(h,bid){
  if(!hhIsAdmin(h)){ ui.toast(t('hh.notAdmin')); return; }
  const b=h.bills.find(x=>x.id===bid); if(!b) return;
  ui.openSheet('<h2>'+ui.esc(b.item)+'</h2><p class="sub" style="margin:0 0 12px">'+ui.esc(t('hh.bill.options'))+'</p>'
    +'<div class="row" style="gap:8px"><button class="btn btn-line" id="baEdit" style="flex:1">✏️ '+ui.esc(t('hh.bill.edit'))+'</button>'
    +'<button class="btn" id="baDel" style="flex:1;background:#e5484d;color:#fff;border:0">🗑️ '+ui.esc(t('hh.bill.del'))+'</button></div>');
  document.getElementById('baEdit').onclick=()=>{ ui.closeSheet(); billFormSheet(h,bid); };
  document.getElementById('baDel').onclick=()=>{ ui.closeSheet(); delBill(h,bid); };
}
/* shared add/edit bill sheet. New bills split among ALL current members by
   default and store that snapshot (b.split); edits recompute shares. */
function billFormSheet(h,bid){
  if(bid&&!hhIsAdmin(h)){ ui.toast(t('hh.notAdmin')); return; }
  const me=store.myName();
  const b=bid?h.bills.find(x=>x.id===bid):null;
  const isEdit=!!b;
  const opts=h.members.map(m=>'<option'+(m===(isEdit?b.paidBy:me)?' selected':'')+'>'+ui.esc(m)+'</option>').join('');
  ui.openSheet(
    '<h2>'+t(isEdit?'hh.bill.editTitle':'groups.ab.title')+'</h2>'
    +'<div class="field"><label>'+t('groups.ab.item')+'</label><input class="input" id="bItem" placeholder="'+t('groups.ab.itemPh')+'" value="'+ui.esc(isEdit?b.item:'')+'"></div>'
    +'<div class="field"><label>'+t('groups.ab.amt')+'</label><input class="input" id="bAmt" type="number" min="0.01" step="0.01" inputmode="decimal" placeholder="0.00" value="'+(isEdit?b.amount:'')+'"></div>'
    +'<p class="sub" id="bSplitNote" style="margin:-4px 0 10px"></p>'
    +'<div class="field"><label>'+t('groups.ab.by')+'</label><select class="input" id="bBy">'+opts+'</select></div>'
    +'<div class="field"><label>'+t('groups.ab.due')+'</label><input class="input" id="bDue" placeholder="'+t('groups.ab.duePh')+'" value="'+ui.esc(isEdit?(b.due||''):'')+'"></div>'
    +(isEdit?'':'<div class="field"><label>'+t('groups.ab.photo')+'</label><input type="file" id="bPhoto" accept="image/*" class="input" style="padding:10px">'
    +'<img id="bPhotoPrev" hidden style="width:100%;border-radius:12px;margin-top:8px" alt=""></div>')
    +'<button class="btn btn-primary btn-block" id="bSave">'+t(isEdit?'hh.bill.save':'groups.ab.save')+'</button>'
  );
  const upd=()=>{
    const amt=parseFloat(document.getElementById('bAmt').value)||0;
    const n=h.members.length||1;
    document.getElementById('bSplitNote').textContent=t('hh.bill.split',{n:n,share:fmtShare(amt/n)});
  };
  document.getElementById('bAmt').addEventListener('input',upd); upd();
  if(!isEdit){
    billPhotoData='';
    document.getElementById('bPhoto').onchange=e=>{ readBillPhoto(e.target.files&&e.target.files[0]); };
  }
  document.getElementById('bSave').onclick=()=>{
    const item=document.getElementById('bItem').value.trim();
    const amount=parseFloat(document.getElementById('bAmt').value);
    if(!item){ui.toast(t('groups.ab.needItem'));return;}
    if(!(amount>0)){ui.toast(t('groups.ab.needAmt'));return;}
    const rec={item:item,amount:Math.round(amount*100)/100,paidBy:document.getElementById('bBy').value,due:document.getElementById('bDue').value.trim()||'—'};
    if(isEdit){ Object.assign(b,rec); ui.toast(t('hh.bill.saved')); }
    else{
      h.bills.push(Object.assign({id:store.uid(),split:h.members.slice(),photo:billPhotoData||'',at:Date.now()},rec));
      ui.toast(t('groups.ab.done'));
    }
    store.save(); ui.closeSheet(); rerender();
  };
}
/* admin: rename, change photo, add/remove members. Removing a member keeps
   their shares on existing bills (honest) but excludes them from new ones. */
function manageHouseholdSheet(h){
  if(!hhIsAdmin(h)){ ui.toast(t('hh.notAdmin')); return; }
  const me=store.myName();
  let mems=h.members.slice();
  hhPhotoData=h.photo||'';
  ui.openSheet(
    '<h2>'+t('hh.edit.title')+'</h2>'
    +'<div class="field"><label>'+t('hh.photo')+'</label><input type="file" id="hhPhoto" accept="image/*" class="input" style="padding:10px">'
    +(hhPhotoData?'<img id="hhPhotoPrev" src="'+ui.esc(hhPhotoData)+'" style="width:100%;border-radius:12px;margin-top:8px" alt="">':'<img id="hhPhotoPrev" hidden style="width:100%;border-radius:12px;margin-top:8px" alt="">')+'</div>'
    +'<div class="field"><label>'+t('hh.edit.name')+'</label><input class="input" id="hhName" maxlength="60" value="'+ui.esc(h.name)+'"></div>'
    +'<div class="field"><label>'+t('hh.edit.members')+'</label><div id="hhMemList"></div>'
    +'<div class="row" style="gap:8px;margin-top:6px"><input class="input" id="hhAddName" placeholder="'+ui.esc(t('hh.edit.addPh'))+'"><button class="btn btn-line" id="hhAddBtn" style="flex:none">'+t('hh.edit.add')+'</button></div></div>'
    +'<div class="field"><label>🙋 '+t('hh.join.pending')+'</label><div id="hhReqList"></div></div>'
    +'<p class="hint">'+t('hh.edit.removeNote')+'</p>'
    +'<button class="btn btn-primary btn-block" id="hhSave">'+t('hh.edit.save')+'</button>'
  );
  /* join requests live here too (admin only — the sheet already guards) */
  const paintReqs=()=>{
    const list=document.getElementById('hhReqList');
    const rq=h.requests||[];
    list.innerHTML=rq.length?rq.map(r=>
      '<div class="kv"><div><div style="font-weight:600">'+ui.esc(r.name)+'</div><div class="meta">'+ui.timeAgo(r.at||Date.now())+'</div></div>'
      +'<div class="row" style="gap:6px"><button class="btn btn-primary btn-sm" data-mhappr="'+ui.esc(r.name)+'">'+ui.esc(t('hh.join.approve'))+'</button>'
      +'<button class="btn btn-line btn-sm" data-mhdecl="'+ui.esc(r.name)+'">'+ui.esc(t('hh.join.decline'))+'</button></div></div>'
    ).join(''):'<p class="sub">'+ui.esc(t('hh.join.noPending'))+'</p>';
    list.querySelectorAll('[data-mhappr]').forEach(btn=>{
      btn.onclick=()=>{ ui.closeSheet(); hhRequestDecide(h,btn.dataset.mhappr,true); manageHouseholdSheet(h); };
    });
    list.querySelectorAll('[data-mhdecl]').forEach(btn=>{
      btn.onclick=()=>{ ui.closeSheet(); hhRequestDecide(h,btn.dataset.mhdecl,false); manageHouseholdSheet(h); };
    });
  };
  paintReqs();
  const paint=()=>{
    document.getElementById('hhMemList').innerHTML=mems.map(m=>
      '<div class="hhmmem"><span class="avatar">'+ui.avatarFor(m)+'</span><span class="grow" style="font-weight:600">'+ui.esc(m)+(m===hhAdmin(h)?' 👑':'')+'</span>'
      +(m===me?'':'<button class="linklike" data-rm="'+ui.esc(m)+'" aria-label="'+ui.esc(t('hh.edit.remove'))+'">✕</button>')+'</div>'
    ).join('');
    document.querySelectorAll('[data-rm]').forEach(btn=>{
      btn.onclick=()=>{
        const nm=btn.dataset.rm;
        if(confirm(t('hh.edit.removeC',{name:nm}))){
          mems=mems.filter(x=>x!==nm);
          syncMembers();
          ui.toast(t('hh.edit.removed',{name:nm}));
          paint();
        }
      };
    });
  };
  paint();
  document.getElementById('hhPhoto').onchange=e=>{ readHousePhoto(e.target.files&&e.target.files[0],'hhPhotoPrev'); };
  /* member add/remove persist immediately (not only on Save): on phones the
     sheet is often dismissed without tapping Save, which silently lost the
     member and looked like the Add button was broken. */
  const syncMembers=()=>{
    if(!mems.some(m=>ui.isMe(m))) mems.unshift(me); /* admin always stays */
    h.members=mems.slice(); store.save();
  };
  const addInput=document.getElementById('hhAddName');
  addInput.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); document.getElementById('hhAddBtn').click(); } });
  document.getElementById('hhAddBtn').onclick=()=>{
    const nm=addInput.value.trim();
    if(!nm) return;
    if(mems.some(x=>x.toLowerCase()===nm.toLowerCase())){ addInput.value=''; return; }
    mems.push(nm); addInput.value='';
    syncMembers();
    ui.toast(t('hh.edit.added',{name:nm})); paint();
  };
  document.getElementById('hhSave').onclick=()=>{
    const name=document.getElementById('hhName').value.trim();
    if(!name){ ui.toast(t('groups.nh.needName')); return; }
    if(!mems.some(m=>ui.isMe(m))) mems.unshift(me); /* admin always stays */
    if(!mems.some(m=>m===hhAdmin(h))) h.admin=mems[0];
    h.name=name; h.members=mems; h.photo=hhPhotoData||'';
    store.save(); ui.closeSheet(); rerender(); ui.toast(t('hh.edit.saved'));
  };
}

/* ================= COMMUNITIES ================= */
function renderCampus(el){
  const s=store.state, me=store.myName();
  let html='<div class="gu">'+grHero(ui.esc(t('groups.title')),ui.esc(t('groups.subCampus')));
  html+=segBar();

  html+='<div class="card tight gu-camp"><div class="row between"><div><div class="sub" style="font-size:12px">'+t('groups.yourCommunity')+'</div><h2>'+ui.esc(s.profile.campus||'—')+'</h2></div>'
    +'<button class="btn btn-line btn-sm" id="campusPickBtn" style="max-width:170px">'+ui.esc(t('groups.changeCommunity'))+'</button></div>'
    +'<p class="hint" style="margin:8px 0 0">'+t('intl.bundledDir')+' · '+t('honesty.sampleCommunities')+'</p></div>';

  html+='<button class="btn btn-primary btn-block" id="campusPost">'+t('groups.postCommunity')+'</button><div style="height:12px"></div>';

  /* marketplace cross-link */
  const nList=s.listings.length;
  html+='<button class="btn btn-line btn-block" id="goMarket" style="margin-bottom:14px">'+t('groups.marketItems',{n:nList})+'</button>';

  html+='<h2 style="margin-bottom:10px">'+t('groups.today')+'</h2>';
  let crI=0;
  for(const e of s.events){
    html+='<div class="item gu-row" style="--i:'+(crI++)+'"><div class="avatar" style="background:var(--surface2);color:var(--ink)">'+ui.esc(e.emoji)+'</div>'
      +'<div class="grow"><h3>'+ui.esc(e.title)+'</h3><div class="meta">'+ui.esc(e.time)+' · '+ui.esc(e.where)+'</div></div>'+ui.sampleBadge(e.sample)+'</div>';
  }
  const posts=[...s.campusPosts].filter(p=>!ui.isBlocked(p.author)).sort((a,b)=>(b.at||0)-(a.at||0));
  for(const p of posts){
    html+='<div class="item gu-row" style="--i:'+(crI++)+'"><div class="avatar">'+ui.initials(p.author)+'</div>'
      +'<div class="grow"><h3>'+ui.esc(p.author)+' <span class="meta">· '+ui.timeAgo(p.at||Date.now())+'</span></h3>'
      +'<div style="font-size:14.5px;line-height:1.45">'+ui.esc(p.text)+'</div></div>'+ui.sampleBadge(p.sample)+'</div>';
  }
  if(!s.events.length&&!posts.length) html+='<div class="empty ps-empty"><div class="big">🏘️</div><p>'+t('groups.quiet')+'</p></div>';

  el.innerHTML=html+'</div>';
  bindSeg(el);
  document.getElementById('campusPickBtn').onclick=()=>{
    ui.openInstitutionPicker({mode:ui.isCampusCommunity(s.profile.campus)?'student':'community',onPick:rec=>{
      s.profile.campus=rec.name; s.profile.campusSample=!!rec.sample; s.profile.campusKind=rec.kind||'';
      if(!rec.sample&&rec.lat!=null&&rec.lng!=null&&isFinite(rec.lat)&&isFinite(rec.lng)){ s.profile.campusCoords=[rec.lat,rec.lng]; s.profile.campusIso=rec.iso||''; s.profile.campusCity=rec.city||''; }
      else { delete s.profile.campusCoords; delete s.profile.campusIso; delete s.profile.campusCity; }
      store.save(); rerender(); ui.toast(t('intl.mapCenterSet',{name:rec.name}));
    }});
  };
  document.getElementById('goMarket').onclick=()=>HUB.showTab('market');
  document.getElementById('campusPost').onclick=()=>{
    ui.openSheet(
      '<h2>'+t('groups.cp.title')+'</h2>'
      +'<div class="field"><label>'+t('groups.cp.emoji')+'</label><input class="input" id="cpEmoji" maxlength="4" placeholder="💬"></div>'
      +'<div class="field"><label>'+t('groups.cp.what')+'</label><textarea class="textarea" id="cpText" placeholder="'+t('groups.cp.ph')+'"></textarea></div>'
      +'<button class="btn btn-primary btn-block" id="cpSave">'+t('groups.cp.post')+'</button>'
    );
    document.getElementById('cpSave').onclick=()=>{
      const text=document.getElementById('cpText').value.trim();
      if(!text){ui.toast(t('groups.cp.need'));return;}
      let emoji=document.getElementById('cpEmoji').value.trim()||'💬';
      store.add('campusPosts',{author:me,text:(emoji+' '+text).trim(),at:Date.now()});
      ui.closeSheet(); rerender(); ui.toast(t('groups.cp.done'));
    };
  };
}

/* ================= COMMUNITY GROUPS (2026-09-22) =================
   Interest groups (math study, PUBG squads, run clubs...). Any user can
   create one; groups start as drafts and the admin "makes them live".
   Live groups within CG_RADIUS_MI of the user surface in the 3D
   water-flow carousel here and in a "Groups near you" section on Home.
   Join flow: request access -> admin approves/declines from the group page
   (also surfaced as a notification row). Demo honesty: seeds are
   sample-flagged; real cross-device join requests need a backend. */
const CG_RADIUS_MI=50;
function cgAll(){ return store.state.cgroups||[]; }
function cgFind(id){ return cgAll().find(function(g){ return g.id===id; }); }
function myCoords(){
  const p=store.state.profile||{};
  if(p.campusCoords&&p.campusCoords[0]!=null&&p.campusCoords[1]!=null&&isFinite(p.campusCoords[0])&&isFinite(p.campusCoords[1]))
    return {lat:p.campusCoords[0],lng:p.campusCoords[1]};
  const home=store.cgHome||{lat:32.8674,lng:-96.9885};
  return {lat:home.lat,lng:home.lng};
}
function havMi(a,b,c,d){
  const R=3958.8, rad=Math.PI/180;
  const s1=Math.sin((c-a)*rad/2), s2=Math.sin((d-b)*rad/2);
  const h=s1*s1+Math.cos(a*rad)*Math.cos(c*rad)*s2*s2;
  return 2*R*Math.asin(Math.min(1,Math.sqrt(h)));
}
function cgDist(g){
  const m=myCoords();
  const la=isFinite(Number(g.lat))?Number(g.lat):m.lat;
  const ln=isFinite(Number(g.lng))?Number(g.lng):m.lng;
  return havMi(m.lat,m.lng,la,ln);
}
function cgAdminName(g){ return g.mine?store.myName():(g.admin||'—'); }
function cgMembers(g){
  const me=store.myName(), list=(g.members||[]).filter(Boolean);
  if(g.mine&&!list.some(function(n){ return String(n).toLowerCase()===String(me).toLowerCase(); }))
    return [me].concat(list);
  return list;
}
function cgIsMember(g){
  const me=String(store.myName()).toLowerCase();
  return cgMembers(g).some(function(n){ return String(n).toLowerCase()===me; });
}
function cgHasRequested(g){
  const me=String(store.myName()).toLowerCase();
  return (g.requests||[]).some(function(r){ return String(r.name||'').toLowerCase()===me; });
}
/* live groups within the radius, nearest first: [{g,d}] */
function cgNearby(limit){
  const out=cgAll().filter(function(g){ return g.live&&cgDist(g)<=CG_RADIUS_MI; })
    .map(function(g){ return {g:g,d:cgDist(g)}; })
    .sort(function(a,b){ return a.d-b.d; });
  return limit?out.slice(0,limit):out;
}
function openClubPage(id){
  openClub=id; openHh=null; sub='clubs';
  if(HUB.showTab) HUB.showTab('groups'); else rerender();
}

/* ---------- 3D water-flow carousel ----------
   Cover-flow feel: the centered card is forward and crisp, cards toward
   the edges recede (translateZ + rotateY + scale + fade). Transform and
   opacity only, driven by a rAF-throttled scroll listener. A gentle
   ping-pong auto-drift keeps it "flowing like water"; any touch/wheel
   pauses it for 6s, and prefers-reduced-motion disables it entirely. */
let flowSeq=0;
function carouselHTML(entries){
  const id='flow'+(++flowSeq);
  const cards=entries.map(function(e,ci){
    const g=e.g;
    const media=g.photo
      ? '<img src="'+ui.esc(g.photo)+'" alt="" loading="lazy">'
      : '<span class="gcard-emoji">'+ui.esc(g.emoji||'👥')+'</span>';
    return '<article class="gcard" data-club="'+g.id+'" tabindex="0" role="button" aria-label="'+ui.esc(g.name)+'" style="--i:'+ci+'">'
      +'<div class="gcard-media">'+media+'</div>'
      +(g.live?'<span class="gcard-live">'+ui.esc(t('cg.live'))+'</span>':'<span class="gcard-draft">'+ui.esc(t('cg.draft'))+'</span>')
      +'<div class="gcard-body"><h3>'+ui.esc(g.name)+'</h3>'
      +'<p>'+ui.esc(g.desc||'')+'</p>'
      +'<div class="gcard-meta"><span class="gdist">📍 '+ui.esc(t('cg.miAway',{n:e.d.toFixed(1)}))+'</span>'
      +'<span class="gmem">👥 '+cgMembers(g).length+'</span></div>'
      +'<span class="gcard-cat">'+ui.esc(t(cgCatKey(g)))+'</span>'
      +ui.sampleBadge(g.sample)
      +'</div></article>';
  }).join('');
  return '<div class="flowwrap"><div class="flow" id="'+id+'">'+cards+'</div></div>';
}
function bindFlow(scroller){
  if(scroller.dataset.fbound) return; scroller.dataset.fbound='1';
  const reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let raf=0, dead=false;
  /* Self-cleanup: when the scroller leaves the DOM (view re-render), kill the
     interval, the pending idle timeout, the resize listener and any queued
     rAF so nothing accumulates across re-renders. */
  const kill=function(){
    if(dead) return; dead=true;
    stop(); clearTimeout(idle);
    if(raf) cancelAnimationFrame(raf);
    window.removeEventListener('resize',onResize);
  };
  const alive=function(){ if(!scroller.isConnected){ kill(); return false; } return true; };
  const tilt=function(){
    raf=0;
    const sr=scroller.getBoundingClientRect(), cx=sr.left+sr.width/2;
    const kids=scroller.children;
    for(let i=0;i<kids.length;i++){
      const card=kids[i], r=card.getBoundingClientRect();
      const d=(r.left+r.width/2-cx)/sr.width;
      const ad=Math.min(1,Math.abs(d)*1.7);
      card.style.transform='translateZ('+(-ad*80).toFixed(1)+'px) rotateY('+(d*20).toFixed(1)+'deg) scale('+(1-ad*0.13).toFixed(3)+')';
      card.style.opacity=(1-ad*0.35).toFixed(2);
    }
  };
  const schedule=function(){ if(!raf&&!dead) raf=requestAnimationFrame(tilt); };
  const onResize=function(){ if(alive()) schedule(); };
  scroller.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',onResize);
  schedule();
  /* auto-drift: slow ping-pong, paused on interaction, off for reduced motion */
  let dir=1, timer=null, idle=null;
  const stop=function(){ if(timer){ clearInterval(timer); timer=null; } };
  const start=function(){
    if(reduce||timer||!alive()) return;
    timer=setInterval(function(){
      if(!alive()) return;
      if(document.hidden) return;
      scroller.scrollLeft+=dir*0.7;
      const max=scroller.scrollWidth-scroller.clientWidth-2;
      if(scroller.scrollLeft<=0){ scroller.scrollLeft=0; dir=1; }
      else if(scroller.scrollLeft>=max){ scroller.scrollLeft=max; dir=-1; }
    },32);
  };
  const poke=function(){ if(dead) return; stop(); clearTimeout(idle); idle=setTimeout(function(){ if(alive()) start(); },6000); };
  scroller.addEventListener('pointerdown',poke,{passive:true});
  scroller.addEventListener('touchstart',poke,{passive:true});
  scroller.addEventListener('wheel',poke,{passive:true});
  start();
}
function bindCarousels(scope){
  scope.querySelectorAll('.flow').forEach(bindFlow);
  /* quick "make live" inside Your-groups rows: don't also open the page */
  scope.querySelectorAll('[data-lvive]').forEach(function(b){
    if(b.dataset.cbound) return; b.dataset.cbound='1';
    b.addEventListener('click',function(e){
      e.stopPropagation();
      const g=cgFind(b.dataset.lvive);
      if(g){ g.live=true; store.save(); rerender(); ui.toast(t('cg.wentLive')); }
    });
  });
  scope.querySelectorAll('[data-club]').forEach(function(card){
    if(card.dataset.cbound) return; card.dataset.cbound='1';
    let px=0, py=0;
    card.addEventListener('pointerdown',function(e){ px=e.clientX; py=e.clientY; },{passive:true});
    const go=function(e){
      if(e&&Math.hypot((e.clientX||0)-px,(e.clientY||0)-py)>10) return; /* was a drag */
      openClubPage(card.dataset.club);
    };
    card.addEventListener('click',go);
    card.addEventListener('keydown',function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openClubPage(card.dataset.club); }
    });
  });
}

/* ---------- discovery view ---------- */
function clubsResultsHTML(){
  const q=clubQuery.trim().toLowerCase();
  const matchQ=function(g){ return !q||((g.name||'')+' '+(g.desc||'')).toLowerCase().indexOf(q)!==-1; };
  const nearF=cgNearby().filter(function(e){ return matchQ(e.g); });
  const mine=cgAll().filter(function(g){ return g.mine&&matchQ(g); });
  let html='<div class="sechd gu-sechd"><h2>🌊 '+t('cg.nearYou')+'</h2><span class="meta">'+nearF.length+'</span></div>';
  if(nearF.length) html+=carouselHTML(nearF);
  else html+='<div class="empty ps-empty"><div class="big">🌊</div><p>'+t(q?'cg.emptySearch':'cg.empty')+'</p></div>';
  if(nearF.length&&nearF.every(function(e){ return e.g.sample; }))
    html+='<p class="hint" style="margin:2px 2px 8px">'+t('cg.sampleHint')+'</p>';
  html+='<div class="sechd gu-sechd"><h2>🛠️ '+t('cg.yours')+'</h2><span class="meta">'+mine.length+'</span></div>';
  if(!mine.length) html+='<p class="sub" style="margin:0 2px 10px">'+t('cg.noYours')+'</p>';
  else html+=mine.map(function(g,gi){
    return '<div class="item gu-row" data-club="'+g.id+'" style="cursor:pointer;--i:'+gi+'" role="button" tabindex="0">'
      +'<div class="avatar" style="background:var(--surface2);overflow:hidden">'+(g.photo?'<img class="avimg" src="'+ui.esc(g.photo)+'" alt="">':ui.esc(g.emoji||'👥'))+'</div>'
      +'<div class="grow"><h3>'+ui.esc(g.name)+'</h3><div class="meta">'+(g.live?t('cg.live'):t('cg.draft'))+' · '+t('cg.members',{n:cgMembers(g).length})+'</div></div>'
      +(g.live?'':'<button class="btn btn-primary btn-sm" data-lvive="'+g.id+'">'+t('cg.makeLive')+'</button>')
      +'</div>';
  }).join('');
  return html;
}
function renderClubs(el){
  el.innerHTML='<div class="gu">'+grHero(ui.esc(t('cg.title')),ui.esc(t('cg.sub')))
    +segBar()
    +'<div class="field" style="margin:12px 0 4px"><input class="input" id="cgSearch" placeholder="'+ui.esc(t('cg.searchPh'))+'" autocomplete="off" value="'+ui.esc(clubQuery)+'"></div>'
    +'<button class="btn btn-primary btn-block gu-cta" id="cgNew" style="margin-bottom:4px">'+t('cg.new')+'</button>'
    +'<div id="cgResults">'+clubsResultsHTML()+'</div></div>';
  bindSeg(el);
  document.getElementById('cgNew').onclick=function(){ cgFormSheet(null); };
  const si=document.getElementById('cgSearch');
  let deb=null;
  si.oninput=function(){
    clearTimeout(deb);
    deb=setTimeout(function(){
      clubQuery=si.value;
      const host=document.getElementById('cgResults');
      if(host){ host.innerHTML=clubsResultsHTML(); bindCarousels(host); }
    },220);
  };
  bindCarousels(el);
}

/* ---------- group page ---------- */
/* ---------- block-aware group flows ----------
   A blocked user never stops you from seeing a group, but you always get
   the note first: stay or leave (member), join or not (requesting). */
function cgBlockedIn(g){
  const me=String(store.myName()).toLowerCase();
  return cgMembers(g).filter(function(n){
    return String(n).toLowerCase()!==me && HUB.block.isBlockedName(n);
  });
}
function leaveGroup(g){
  const my=String(store.myName()).toLowerCase();
  g.members=(g.members||[]).filter(function(n){ return String(n).toLowerCase()!==my; });
  store.save(); openClub=null; rerender(); ui.toast(t('cg.leftGroup',{name:g.name}));
}
/* member notice: blocked user in this group — stay or leave */
function cgStayNote(g,blkList){
  const seenKey=blkList.slice().sort().join('|');
  const dismissed=(store.state.blockStay&&store.state.blockStay[g.id])||'';
  if(dismissed===seenKey) return '';
  return '<div class="card" style="border:2px solid var(--danger)"><h2 style="margin-bottom:8px">⛔ '+t('cg.blockedInGroupT')+'</h2>'
    +'<p style="font-size:14.5px;line-height:1.5;margin:0 0 6px">'+ui.esc(t('cg.blockedInGroupD',{names:blkList.join(', ')}))+'</p>'
    +'<p style="font-size:14.5px;line-height:1.5;margin:0 0 10px;font-weight:700">'+t('cg.blockedStayQ')+'</p>'
    +'<div class="row" style="gap:8px"><button class="btn btn-primary" id="cgStayYes" data-key="'+ui.esc(seenKey)+'">'+t('cg.stayYes')+'</button>'
    +'<button class="btn btn-line" id="cgStayNo">'+t('cg.leaveNo')+'</button></div></div>';
}
/* requester flow: "do you want to join?" — yes continues, no cancels */
function cgJoinWarn(g,blkList){
  ui.openSheet(
    '<div class="sheeticon">⛔</div>'+
    '<h3>'+t('cg.blockedInGroupT')+'</h3>'+
    '<p>'+ui.esc(t('cg.blockedInGroupD',{names:blkList.join(', ')}))+'</p>'+
    '<p style="font-weight:700">'+t('cg.blockedJoinQ')+'</p>'+
    '<button class="btn btn-primary btn-block" id="cgJoinYes">'+t('cg.joinYes')+'</button>'+
    '<button class="btn btn-ghost btn-block" id="cgJoinNo" style="margin-top:8px">'+t('cg.joinNo')+'</button>'
  );
  document.getElementById('cgJoinYes').onclick=function(){
    /* PraBin: yes means they get IN the group right away (not a pending request) */
    var nm=store.myName();
    g.members=g.members||[];
    if(g.members.indexOf(nm)<0) g.members.push(nm);
    if(g.requests) g.requests=g.requests.filter(function(r){ return r.name!==nm; });
    store.save(); ui.closeSheet(); rerender(); ui.toast(t('cg.joinedNow'));
  };
  document.getElementById('cgJoinNo').onclick=ui.closeSheet;
}

function renderClubDetail(el,g){
  const mine=!!g.mine, member=cgIsMember(g), req=cgHasRequested(g);
  const d=cgDist(g);
  let html='<div class="gu"><button class="linklike gu-back" id="cgBack" style="margin-bottom:10px">'+t('cg.back')+'</button>';
  html+='<div class="cghero gu-hero">'+(g.photo?'<img src="'+ui.esc(g.photo)+'" alt="">':'<span>'+ui.esc(g.emoji||'👥')+'</span>')+'</div>';
  html+='<div class="row between gu-ctitle" style="align-items:flex-start;gap:10px">'+guMotes()+'<h1 class="greet gu-title" style="margin:0">'+ui.esc(g.name)+'</h1>'
    +(g.live?'<span class="livebadge gu-live">'+t('cg.live')+'</span>':'<span class="draftbadge gu-draft">'+t('cg.draft')+'</span>')+'</div>';
  html+='<p class="sub" style="margin:6px 0 4px">📍 '+ui.esc(t('cg.miAway',{n:d.toFixed(1)}))+' · '+ui.esc(t('cg.members',{n:cgMembers(g).length}))+'</p>';
  html+='<p class="sub" style="margin:0 0 4px">👑 '+ui.esc(cgAdminName(g))+'</p>'+ui.sampleBadge(g.sample);
  /* group chat entry: members get a prominent chat button; non-members
     keep the join-request flow below instead */
  if(member) html+='<button class="btn btn-primary btn-block gu-cta" id="cgChatBtn" style="margin:12px 0 2px">💬 '+ui.esc(t('gc.openChat'))+'</button>';
  /* group voice call entry (js/call.js): members can start/join a call */
  if(member) html+='<button class="btn btn-line btn-block gu-act" id="cgCallBtn" style="margin:10px 0 2px">📞 '+ui.esc(t('call.start'))+'</button>';
  /* invite link: admin + members can share live groups (drafts get a hint) */
  if(mine||member) html+='<button class="btn btn-line btn-block gu-act" id="cgInviteBtn" style="margin:10px 0 2px">🔗 '+ui.esc(t('ginv.invite'))+'</button>';
  html+='<div class="card gu-about" style="margin-top:10px"><h2 style="margin-bottom:6px">'+t('cg.about')+'</h2>'
    +'<p style="font-size:14.5px;line-height:1.5;margin:0">'+ui.esc(g.desc||'—')+'</p></div>';
  html+='<div class="card gu-members"><h2 style="margin-bottom:8px">'+t('cg.membersTitle')+'</h2><div class="cgchips">'
    +cgMembers(g).map(function(n){
      return '<span class="cgchip"><span class="avatar">'+ui.avatarFor(n)+'</span>'+ui.esc(n)+'</span>';
    }).join('')+'</div></div>';
  /* blocked member note (members): warn first, then stay or leave */
  if(member) html+=cgStayNote(g,cgBlockedIn(g));

  if(mine){
    html+='<div class="card"><h2 style="margin-bottom:8px">🛠️ '+t('cg.adminTools')+'</h2>'
      +'<div class="row" style="gap:8px;flex-wrap:wrap">'
      +'<button class="btn btn-line btn-sm" id="cgEdit">'+t('cg.edit')+'</button>'
      +(g.live?'<button class="btn btn-line btn-sm" id="cgUnpub">'+t('cg.unpublish')+'</button>'
              :'<button class="btn btn-primary btn-sm" id="cgLive">'+t('cg.makeLive')+'</button>')
      +'<button class="btn btn-ghost btn-sm" id="cgDel">'+t('cg.delete')+'</button>'
      +'</div>'
      +(g.live?'':'<p class="hint" style="margin:8px 0 0">'+t('cg.form.liveHint')+'</p>')
      +'</div>';
    const rq=g.requests||[];
    html+='<div class="card"><h2 style="margin-bottom:8px">'+t('cg.pending')+' ('+rq.length+')</h2>';
    if(!rq.length) html+='<p class="sub">'+t('cg.noPending')+'</p>';
    else for(const r of rq){
      html+='<div class="kv"><div><div style="font-weight:700">'+ui.esc(r.name)+'</div><div class="meta">'+ui.timeAgo(r.at||Date.now())+'</div></div>'
        +'<div class="row" style="gap:6px"><button class="btn btn-primary btn-sm" data-appr="'+ui.esc(r.name)+'">'+t('cg.approve')+'</button>'
        +'<button class="btn btn-line btn-sm" data-decl="'+ui.esc(r.name)+'">'+t('cg.decline')+'</button></div></div>';
    }
    html+='</div>';
  }else if(g.live){
    html+='<div style="margin:14px 0 6px">';
    if(member) html+='<button class="btn btn-line btn-block" disabled>'+t('cg.alreadyMember')+'</button>'
      +'<button class="btn btn-ghost btn-block btn-sm" id="cgLeave" style="margin-top:8px">'+t('cg.leaveGroup')+'</button>';
    else if(req) html+='<button class="btn btn-line btn-sm btn-block" disabled>'+t('cg.requested')+'</button>';
    else html+='<button class="btn btn-primary btn-block" id="cgReq">'+t('cg.request')+'</button>';
    html+='</div>';
  }else{
    html+='<p class="hint" style="margin:14px 0">'+t('cg.draftHidden')+'</p>';
  }

  el.innerHTML=html+'</div>';
  document.getElementById('cgBack').onclick=function(){ openClub=null; rerender(); };
  const chatBtn=document.getElementById('cgChatBtn');
  if(chatBtn) chatBtn.onclick=function(){ if(HUB.gchat) HUB.gchat.open(g.id); };
  const callBtn=document.getElementById('cgCallBtn');
  if(callBtn) callBtn.onclick=function(){ if(HUB.call){ if(HUB.call.pickKind) HUB.call.pickKind(g.id); else HUB.call.start(g.id,{outgoing:true}); } };
  if(HUB.call&&HUB.call.watch) HUB.call.watch(g.id); /* worker-mode incoming calls */
  const invBtn=document.getElementById('cgInviteBtn');
  if(invBtn) invBtn.onclick=function(){ openInviteSheet(g); };
  const ed=document.getElementById('cgEdit');
  if(ed) ed.onclick=function(){ cgFormSheet(g); };
  const lv=document.getElementById('cgLive');
  if(lv) lv.onclick=function(){ g.live=true; store.save(); rerender(); ui.toast(t('cg.wentLive')); };
  const up=document.getElementById('cgUnpub');
  if(up) up.onclick=function(){ g.live=false; store.save(); rerender(); ui.toast(t('cg.unpublished')); };
  const del=document.getElementById('cgDel');
  if(del) del.onclick=function(){
    if(confirm(t('cg.deleteConfirm'))){
      store.state.cgroups=cgAll().filter(function(x){ return x.id!==g.id; });
      store.save(); openClub=null; rerender(); ui.toast(t('cg.deleted'));
    }
  };
  const rqBtn=document.getElementById('cgReq');
  if(rqBtn) rqBtn.onclick=function(){
    const blkList=cgBlockedIn(g);
    if(blkList.length){ cgJoinWarn(g,blkList); return; }
    g.requests=g.requests||[];
    g.requests.push({name:store.myName(),at:Date.now()});
    store.save(); rerender(); ui.toast(t('cg.reqSent'));
  };
  const leaveBtn=document.getElementById('cgLeave');
  if(leaveBtn) leaveBtn.onclick=function(){ leaveGroup(g); };
  const stayYes=document.getElementById('cgStayYes');
  if(stayYes) stayYes.onclick=function(){
    store.state.blockStay=store.state.blockStay||{};
    store.state.blockStay[g.id]=stayYes.getAttribute('data-key');
    store.save(); rerender();
  };
  const stayNo=document.getElementById('cgStayNo');
  if(stayNo) stayNo.onclick=function(){ leaveGroup(g); };
  el.querySelectorAll('[data-appr]').forEach(function(b){
    b.onclick=function(){
      const nm=b.dataset.appr;
      g.requests=(g.requests||[]).filter(function(r){ return r.name!==nm; });
      if(!g.members) g.members=[];
      if(!g.members.some(function(m){ return String(m).toLowerCase()===String(nm).toLowerCase(); })) g.members.push(nm);
      store.save(); rerender(); ui.toast(t('cg.approved',{name:nm}));
    };
  });
  el.querySelectorAll('[data-decl]').forEach(function(b){
    b.onclick=function(){
      const nm=b.dataset.decl;
      g.requests=(g.requests||[]).filter(function(r){ return r.name!==nm; });
      store.save(); rerender(); ui.toast(t('cg.declined'));
    };
  });
}

/* ---------- shareable invite links (2026-09-22) ----------
   Hash-based so the static host serves them untouched:
   <origin>/#join=<groupId>&name=<url-encoded group name>.
   Only the group id + name travel in the link — nothing private. */
function cgInviteLink(g){
  var base=(location.protocol.indexOf('http')===0&&location.origin&&location.origin!=='null')
    ? location.origin : 'https://hub-preview.surge.sh';
  return base+'/#join='+encodeURIComponent(g.id)+'&name='+encodeURIComponent(g.name||'');
}
function cgCopyText(str,inp){
  function done(){ ui.toast(t('ginv.copied')); }
  function fallback(){
    try{ inp.focus(); inp.select(); document.execCommand('copy'); done(); }
    catch(e){ try{ inp.select(); }catch(e2){} }
  }
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(str).then(done,fallback);
  }else fallback();
}
function openInviteSheet(g){
  if(!g.live){ ui.toast(t('ginv.draftHint')); return; }
  var link=cgInviteLink(g);
  var canNative=!!(navigator.share);
  var html='<h2 style="margin:0 0 4px">🔗 '+ui.esc(t('ginv.title'))+'</h2>'
    +'<p class="sub" style="margin:0 0 10px">'+ui.esc(t('ginv.linkHint'))+'</p>'
    +'<input class="input" id="ginvLink" readonly value="'+ui.esc(link)+'">'
    +'<div class="row" style="gap:8px;margin-top:12px;flex-wrap:wrap">'
    +'<button class="btn btn-primary" id="ginvCopy" style="flex:1">📋 '+ui.esc(t('ginv.copyLink'))+'</button>'
    +(canNative?'<button class="btn btn-line" id="ginvShare" style="flex:1">📤 '+ui.esc(t('ginv.shareBtn'))+'</button>':'')
    +'</div>';
  ui.openSheet(html);
  var inp=document.getElementById('ginvLink');
  inp.onclick=function(){ inp.select(); };
  inp.select();
  document.getElementById('ginvCopy').onclick=function(){ cgCopyText(link,inp); };
  var sh=document.getElementById('ginvShare');
  if(sh) sh.onclick=function(){
    try{
      navigator.share({title:t('ginv.shareTitle',{name:g.name}),text:t('ginv.shareText',{name:g.name}),url:link})
        .catch(function(err){ if(err&&err.name!=='AbortError') cgCopyText(link,inp); });
    }catch(e){ cgCopyText(link,inp); }
  };
}
/* ---------- household invite links (2026-09-22) ----------
   Hash-based like community-group invites, but on a separate #hjoin= hash so
   the two deep-link flows never collide:
   <origin>/#hjoin=<householdId>&name=<url-encoded household name>.
   Only the household id + name travel in the link — nothing private.
   Opening the link as a non-member shows the join gate (renderHouseholdDetail
   handles it); the request lands in h.requests for the admin to approve.
   Honest caveat: browser-local demo — on another phone the id won't exist
   locally, so the landing sheet says so instead of faking a request. */
function hhInviteLink(h){
  var base=(location.protocol.indexOf('http')===0&&location.origin&&location.origin!=='null')
    ? location.origin : 'https://hub-preview.surge.sh';
  return base+'/#hjoin='+encodeURIComponent(h.id)+'&name='+encodeURIComponent(h.name||'');
}
function openHhInviteSheet(h){
  var link=hhInviteLink(h);
  var canNative=!!(navigator.share);
  var html='<h2 style="margin:0 0 4px">🔗 '+ui.esc(t('hh.join.title'))+'</h2>'
    +'<p class="sub" style="margin:0 0 10px">'+ui.esc(t('hh.join.hint'))+'</p>'
    +'<input class="input" id="hhinvLink" readonly value="'+ui.esc(link)+'">'
    +'<div class="row" style="gap:8px;margin-top:12px;flex-wrap:wrap">'
    +'<button class="btn btn-primary" id="hhinvCopy" style="flex:1">📋 '+ui.esc(t('ginv.copyLink'))+'</button>'
    +(canNative?'<button class="btn btn-line" id="hhinvShare" style="flex:1">📤 '+ui.esc(t('ginv.shareBtn'))+'</button>':'')
    +'</div>';
  ui.openSheet(html);
  var inp=document.getElementById('hhinvLink');
  inp.onclick=function(){ inp.select(); };
  inp.select();
  document.getElementById('hhinvCopy').onclick=function(){ cgCopyText(link,inp); };
  var sh=document.getElementById('hhinvShare');
  if(sh) sh.onclick=function(){
    try{
      navigator.share({title:t('hh.join.title'),text:t('hh.join.hint'),url:link})
        .catch(function(err){ if(err&&err.name!=='AbortError') cgCopyText(link,inp); });
    }catch(e){ cgCopyText(link,inp); }
  };
}
function openHouseholdPage(id){
  openHh=id; openClub=null; sub='households';
  if(HUB.showTab) HUB.showTab('groups'); else rerender();
}
/* Deep-link boot: #hjoin=<id>&name=<name> (household invites, separate hash
   from the community-group #join flow so the two never collide).
   Household exists locally -> open its page; renderHouseholdDetail shows the
   request gate for non-members. Unknown id -> honest landing sheet. */
function handleHhJoinHash(hsh){
  var m=hsh.match(/#hjoin=([^&]*)/);
  if(!m||!m[1]) return false;
  var hid=m[1], hnm='';
  try{ hid=decodeURIComponent(m[1]); }catch(e){}
  var nmM=hsh.match(/[&]name=([^&]*)/);
  if(nmM&&nmM[1]){ try{ hnm=decodeURIComponent(nmM[1]); }catch(e){ hnm=nmM[1]; } }
  try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){}
  var hh=(store.state.households||[]).find(function(x){ return x.id===hid; });
  if(hh){ openHouseholdPage(hid); return true; }
  ui.openSheet(
    '<h2 style="margin:0 0 4px">🎉 '+ui.esc(t('hh.join.landingT'))+'</h2>'
    +(hnm?'<p style="font-weight:700;font-size:17px;margin:8px 0">\u201C'+ui.esc(hnm)+'\u201D</p>':'')
    +'<p class="sub" style="margin:0 0 12px;line-height:1.55">'+ui.esc(t('hh.join.landingD'))+'</p>'
    +'<button class="btn btn-primary btn-block" id="hhinvBrowse">👥 '+ui.esc(t('hh.join.landingBrowse'))+'</button>'
  );
  document.getElementById('hhinvBrowse').onclick=function(){
    ui.closeSheet(); if(HUB.showTab) HUB.showTab('groups');
  };
  return true;
}
/* Deep-link boot: #join=<id>&name=<name>.
   Group exists locally -> open its page, join CTA emphasized for non-members.
   Unknown id -> honest landing sheet; never fake a membership. */
function handleJoinHash(){
  var h=String(location.hash||'');
  if(handleHhJoinHash(h)) return; /* household invites on their own hash */
  var m=h.match(/#join=([^&]*)/);
  if(!m||!m[1]) return;
  var id=m[1], nm='';
  try{ id=decodeURIComponent(m[1]); }catch(e){}
  var nmM=h.match(/[&]name=([^&]*)/);
  if(nmM&&nmM[1]){ try{ nm=decodeURIComponent(nmM[1]); }catch(e){ nm=nmM[1]; } }
  try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){}
  var g=cgFind(id);
  if(g){
    openClubPage(id);
    setTimeout(function(){
      var cta=document.getElementById('cgReq');
      if(cta){ cta.classList.add('pulse-hi'); try{ cta.scrollIntoView({block:'center'}); }catch(e){} }
    },80);
  }else{
    var html='<h2 style="margin:0 0 4px">🎉 '+ui.esc(t('ginv.landingTitle'))+'</h2>'
      +(nm?'<p style="font-weight:700;font-size:17px;margin:8px 0">\u201C'+ui.esc(nm)+'\u201D</p>':'')
      +'<p class="sub" style="margin:0 0 12px;line-height:1.55">'+ui.esc(t('ginv.landingBody'))+'</p>'
      +'<button class="btn btn-primary btn-block" id="ginvBrowse">👥 '+ui.esc(t('ginv.landingBrowse'))+'</button>';
    ui.openSheet(html);
    document.getElementById('ginvBrowse').onclick=function(){
      ui.closeSheet(); if(HUB.showTab) HUB.showTab('groups');
    };
  }
}

/* ---------- create / edit sheet ---------- */
let cgPhotoData='';
function cgReadPhoto(file){
  const prev=document.getElementById('cgPhotoPrev');
  const show=function(){ if(prev){ prev.src=cgPhotoData; prev.hidden=false; } };
  if(!file) return;
  const url=URL.createObjectURL(file), img=new Image();
  img.onload=function(){
    URL.revokeObjectURL(url);
    const mx=800, sc=Math.min(1,mx/Math.max(img.width||1,img.height||1));
    const w=Math.max(1,Math.round(img.width*sc)), h=Math.max(1,Math.round(img.height*sc));
    const cv=document.createElement('canvas'); cv.width=w; cv.height=h;
    cv.getContext('2d').drawImage(img,0,0,w,h);
    cgPhotoData=cv.toDataURL('image/jpeg',0.72);
    show();
  };
  img.onerror=function(){ URL.revokeObjectURL(url); };
  img.src=url;
}
function cgFormSheet(g){
  const isEdit=!!g;
  cgPhotoData=isEdit?(g.photo||''):'';
  ui.openSheet(
    '<h2>'+t(isEdit?'cg.form.editTitle':'cg.form.title')+'</h2>'
    +'<div class="field"><label>'+t('cg.form.name')+'</label><input class="input" id="cgName" maxlength="60" placeholder="'+ui.esc(t('cg.form.namePh'))+'" value="'+ui.esc(isEdit?g.name:'')+'"></div>'
    +'<div class="field"><label>'+t('cg.form.desc')+'</label><textarea class="textarea" id="cgDesc" rows="3" maxlength="280" placeholder="'+ui.esc(t('cg.form.descPh'))+'">'+ui.esc(isEdit?(g.desc||''):'')+'</textarea></div>'
    +'<div class="field"><label>'+t('cg.form.photo')+'</label><input type="file" id="cgPhoto" accept="image/*" class="input" style="padding:10px">'
    +(cgPhotoData?'<img id="cgPhotoPrev" src="'+ui.esc(cgPhotoData)+'" style="width:100%;border-radius:12px;margin-top:8px" alt="">':'<img id="cgPhotoPrev" hidden style="width:100%;border-radius:12px;margin-top:8px" alt="">')+'</div>'
    +'<button class="btn btn-primary btn-block" id="cgSave">'+t('cg.form.save')+'</button>'
  );
  document.getElementById('cgPhoto').onchange=function(e){ cgReadPhoto(e.target.files&&e.target.files[0]); };
  document.getElementById('cgSave').onclick=function(){
    const name=document.getElementById('cgName').value.trim();
    if(!name){ ui.toast(t('cg.form.needName')); return; }
    const desc=document.getElementById('cgDesc').value.trim();
    let id;
    if(isEdit){ g.name=name; g.desc=desc; g.photo=cgPhotoData; id=g.id; ui.toast(t('cg.form.saved')); }
    else{
      const m=myCoords();
      const ng={id:store.uid(),name:name,desc:desc,emoji:'👥',photo:cgPhotoData,admin:'',mine:true,
        members:[],requests:[],live:false,lat:m.lat,lng:m.lng,sample:false,createdAt:Date.now()};
      cgAll().unshift(ng); id=ng.id;
      ui.toast(t('cg.form.created'));
    }
    store.save(); ui.closeSheet(); sub='clubs'; openClub=id; rerender();
  };
}

/* ---------- Home "Groups near you" section ---------- */
function homeSectionHTML(){
  const near=cgNearby(8);
  if(!near.length) return '';
  let html='<div class="hsec-hd"><h2>'+t('cg.nearYou')+'</h2><button class="hsec-act" id="homeCgAll">'+t('common.seeAll')+'</button></div>';
  html+=carouselHTML(near);
  if(near.every(function(e){ return e.g.sample; }))
    html+='<p class="hnote">'+t('cg.sampleHint')+'</p>';
  return html;
}

/* ---------- People "nearby" glossy row (2026-10-05 redesign) ----------
   The people.js surface renders untouched into #grPplHost; this prepends the
   glossy hero and inserts a horizontal avatar row (gradient rings, first
   names, Sample flags) after its demo note, mockup-style. The green dot is
   honest local state ONLY: it marks people the user follows AND who follow
   back (isMutual) — never a fake "online" claim (see people.js privacy
   note). Taps open the person's existing profile. Empty -> row omitted. */
function grFirstName(n){ return String(n||'').trim().split(/\s+/)[0]||''; }
function grPplRowHTML(){
  let list=[];
  try{ list=(HUB.people&&HUB.people.visiblePeople)?HUB.people.visiblePeople():[]; }catch(e){ list=[]; }
  list=(list||[]).slice(0,14);
  if(!list.length) return '';
  const items=list.map(function(p){
    const mut=HUB.people.isMutual?HUB.people.isMutual(p.id):false;
    return '<button class="gr-pava" data-pid="'+ui.esc(p.id)+'" aria-label="'+ui.esc(p.name)+(mut?' · '+ui.esc(t('people.mutual')):'')+'">'
      +'<span class="gr-pring">'+(mut?'<i class="gr-pdot" aria-hidden="true"></i>':'')
      +'<span class="gr-pini">'+ui.esc(ui.initials(p.name))+'</span></span>'
      +'<span class="gr-pname">'+ui.esc(grFirstName(p.name))+'</span>'
      +(p.sample?'<span class="gr-psamp">'+ui.esc(t('honesty.sample'))+'</span>':'')
      +'</button>';
  }).join('');
  return '<section class="gr-pplsec" aria-label="'+ui.esc(t('home.pplNear'))+'">'
    +'<div class="gr-sechd"><h2>'+ui.esc(t('home.pplNear'))+'</h2><span class="gr-count">'+list.length+'</span></div>'
    +'<div class="gr-pplrow" role="list">'+items+'</div></section>';
}
function grPeopleEnhance(el){
  const host=el.querySelector('#grPplHost'); if(!host) return;
  const where=t(store.state.profile.audience==='student'?'people.atSchool':'people.inCommunity');
  const hero=document.createElement('div');
  hero.innerHTML=grHero(ui.esc(t('groups.title')),ui.esc(t('people.findAt',{where:where})));
  el.insertBefore(hero.firstChild,el.firstChild);
  const anchor=host.querySelector('.demo-note');
  if(!anchor) return;
  const row=document.createElement('div');
  row.innerHTML=grPplRowHTML();
  if(row.firstChild){
    anchor.parentNode.insertBefore(row.firstChild,anchor.nextSibling);
    el.querySelectorAll('.gr-pava').forEach(function(b){
      b.addEventListener('click',function(){ if(HUB.people&&HUB.people.openProfile) HUB.people.openProfile(b.dataset.pid); });
    });
  }
}

/* ================= VIEW ================= */
HUB.views.groups={ render(el){
  /* People mode: people.js renders its own surface here (untouched); toggle
     the .gu scope on the view root so groups-ui.css gives it the same
     water-crystal treatment as the other three modes. */
  el.classList.toggle('gu',sub==='people');
  /* Workstream D: the People discovery surface renders here when active.
     Guarded so groups.js keeps working if people.js hasn't loaded. */
  if(sub==='people'){
    if(HUB.people&&HUB.people.renderSurface){
      el.innerHTML='<div id="grPplHost"></div>';
      HUB.people.renderSurface(el.querySelector('#grPplHost'));
      grPeopleEnhance(el);
    }
    else el.innerHTML='<div class="empty"><div class="big">👤</div><p>'+t('people.loading')+'</p></div>';
    return;
  }
  if(sub==='campus'){ renderCampus(el); return; }
  if(sub==='clubs'){
    const g=openClub?cgFind(openClub):null;
    if(g) renderClubDetail(el,g);
    else { if(openClub) openClub=null; renderClubs(el); }
    return;
  }
  const h=openHh?store.state.households.find(x=>x.id===openHh):null;
  if(h) renderHouseholdDetail(el,h);
  else { if(openHh){openHh=null;} renderHouseholdsList(el); }
},
/* lets the people module (and anyone else) switch the groups sub-tab */
setSub(s){ sub=s; openClub=null; openHh=null; rerender(); }
};
/* Community-groups API used by Home (near-you section) and Notifications
   (join-request rows). */
HUB.cgroups={nearby:cgNearby,openClub:openClubPage,distMi:cgDist,carouselHTML:carouselHTML,
  bindCarousels:bindCarousels,homeSectionHTML:homeSectionHTML,handleJoinHash:handleJoinHash,inviteLink:cgInviteLink};
/* Households API: notifications (join-request rows) and deep-link targets. */
HUB.households={openHousehold:openHouseholdPage,inviteLink:hhInviteLink,decideRequest:hhRequestDecide,isAdmin:hhIsAdmin};
})();
