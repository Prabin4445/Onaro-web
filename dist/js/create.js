/* HUB quick-create: central floating button + bottom-sheet with 9 actions.
   Routes to each domain's own post flow (DOM-triggered, zero edits to view files),
   or uses its own sheet writing straight to the store for bills/chores/events. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

function injectStyle(){
  if(document.getElementById('createFabStyle')) return;
  const s=document.createElement('style'); s.id='createFabStyle';
  s.textContent=
    /* central clay Create button — volt 3D clay "+", squish-on-press with spring release */
    '.createfab{position:fixed;bottom:calc(20px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);'+
    'width:60px;height:60px;border-radius:50%;border:0;cursor:pointer;z-index:35;'+
    'font-size:30px;font-weight:300;line-height:1;color:var(--accent-ink);'+
    'background:radial-gradient(circle at 32% 28%,var(--clay-hi) 0%,var(--volt) 42%,var(--clay-lo) 68%,var(--clay-deep) 100%);'+
    'box-shadow:inset 0 3px 6px rgba(255,255,255,.55),inset 0 -5px 10px color-mix(in srgb,var(--clay-deep) 45%,transparent),0 12px 28px rgba(var(--volt-rgb),.45);'+
    'transition:transform .45s cubic-bezier(.32,.72,0,1),box-shadow .2s}'+
    '.createfab:active{transform:translateX(-50%) scale(.9);'+
    'box-shadow:inset 0 3px 6px rgba(255,255,255,.55),inset 0 -5px 10px color-mix(in srgb,var(--clay-deep) 45%,transparent),0 5px 14px rgba(var(--volt-rgb),.4)}'+
    'body.dark .createfab{box-shadow:inset 0 3px 6px rgba(255,255,255,.4),inset 0 -5px 10px rgba(0,0,0,.5)}'+
    '.cgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}'+
    '.caction{border:1px solid var(--line);background:var(--surface);border-radius:16px;padding:14px 4px;min-height:96px;'+
    'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;'+
    'font-family:var(--font);font-size:12px;font-weight:700;color:var(--ink);cursor:pointer;'+
    'transition:transform .4s cubic-bezier(.32,.72,0,1),background .15s}'+
    '.caction:active{transform:scale(.94)}';
  document.head.appendChild(s);
}

function after(ms,fn){ setTimeout(fn,ms); }
function clickSel(sel,ms){
  after(ms==null?80:ms,()=>{ const b=document.querySelector(sel); if(b) b.click(); });
}
function go(tab){ HUB.showTab(tab); }
/* Keep bottom sheets and chatroot overlays mutually exclusive. */
function closeOverlays(){
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
}

/* ----- own sheets: event / expense / household task ----- */
function eventSheet(){
  closeOverlays();
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-event')+' '+t('create.ev.title')+'</h2>'+
    '<div class="field"><label>'+t('create.ev.emoji')+'</label><input class="input" id="evEmoji" placeholder="📌" maxlength="4" style="width:80px"></div>'+
    '<div class="field"><label>'+t('create.ev.titleLabel')+'</label><input class="input" id="evTitle" placeholder="'+t('create.ev.titlePh')+'" maxlength="80"></div>'+
    '<div class="field"><label>'+t('create.ev.whenLabel')+'</label><input class="input" id="evTime" placeholder="'+t('create.ev.whenPh')+'" maxlength="40"></div>'+
    '<div class="field"><label>'+t('create.ev.whereLabel')+'</label><input class="input" id="evWhere" placeholder="'+t('create.ev.wherePh')+'" maxlength="60"></div>'+
    '<button class="btn btn-primary btn-block" id="evSave">'+t('create.ev.save')+'</button>'
  );
  document.getElementById('evSave').onclick=()=>{
    const title=document.getElementById('evTitle').value.trim();
    const time=document.getElementById('evTime').value.trim();
    if(!title||!time){ui.toast(t('create.ev.need'));return;}
    store.add('events',{emoji:document.getElementById('evEmoji').value.trim()||'📌',title,time,where:document.getElementById('evWhere').value.trim()});
    ui.closeSheet(); ui.toast(t('create.ev.done'));
  };
}

function householdOptions(){
  return store.state.households.map(h=>'<option value="'+h.id+'">'+ui.esc(h.name)+'</option>').join('');
}
function expenseSheet(){
  closeOverlays();
  const hs=store.state.households;
  if(!hs.length){ui.toast(t('create.needHousehold'));go('groups');return;}
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-expense')+' '+t('create.ex.title')+'</h2>'+
    '<div class="field"><label>'+t('create.ex.hhLabel')+'</label><select class="input" id="exHh">'+householdOptions()+'</select></div>'+
    '<div class="field"><label>'+t('create.ex.whatLabel')+'</label><input class="input" id="exItem" placeholder="'+t('create.ex.whatPh')+'" maxlength="60"></div>'+
    '<div class="field"><label>'+t('create.ex.amtLabel')+'</label><input class="input" id="exAmt" type="number" min="0" step="0.01" placeholder="'+t('create.ex.amtPh')+'"></div>'+
    '<div class="field"><label>'+t('create.ex.byLabel')+'</label><input class="input" id="exBy" value="'+ui.esc(store.myName())+'" maxlength="40"></div>'+
    '<div class="field"><label>'+t('create.ex.dueLabel')+'</label><input class="input" id="exDue" placeholder="'+t('create.ex.duePh')+'" maxlength="20"></div>'+
    '<button class="btn btn-primary btn-block" id="exSave">'+t('create.ex.save')+'</button>'+
    '<p class="hint">'+t('create.ex.hint')+'</p>'
  );
  document.getElementById('exSave').onclick=()=>{
    const h=store.find('households',document.getElementById('exHh').value);
    const item=document.getElementById('exItem').value.trim();
    const amount=parseFloat(document.getElementById('exAmt').value);
    if(!h||!item||!(amount>0)){ui.toast(t('create.ex.need'));return;}
    h.bills.unshift({id:store.uid(),item,amount:Math.round(amount*100)/100,paidBy:document.getElementById('exBy').value.trim()||store.myName(),due:document.getElementById('exDue').value.trim()||'—'});
    if(!h.members.includes(document.getElementById('exBy').value.trim())&&document.getElementById('exBy').value.trim()) h.members.push(document.getElementById('exBy').value.trim());
    store.save(); ui.closeSheet(); ui.toast(t('create.ex.done'));
  };
}

function taskSheet(){
  closeOverlays();
  const hs=store.state.households;
  if(!hs.length){ui.toast(t('create.needHousehold'));go('groups');return;}
  const renderMembers=()=>{
    const h=store.find('households',document.getElementById('tkHh').value);
    document.getElementById('tkWho').innerHTML=(h?h.members:[]).map(m=>'<option>'+ui.esc(m)+'</option>').join('');
  };
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-task')+' '+t('create.task.title')+'</h2>'+
    '<div class="field"><label>'+t('create.task.hhLabel')+'</label><select class="input" id="tkHh">'+householdOptions()+'</select></div>'+
    '<div class="field"><label>'+t('create.task.label')+'</label><input class="input" id="tkTask" placeholder="'+t('create.task.ph')+'" maxlength="80"></div>'+
    '<div class="field"><label>'+t('create.task.who')+'</label><select class="input" id="tkWho"></select></div>'+
    '<button class="btn btn-primary btn-block" id="tkSave">'+t('create.task.save')+'</button>'
  );
  document.getElementById('tkHh').onchange=renderMembers; renderMembers();
  document.getElementById('tkSave').onclick=()=>{
    const h=store.find('households',document.getElementById('tkHh').value);
    const task=document.getElementById('tkTask').value.trim();
    if(!h||!task){ui.toast(t('create.task.need'));return;}
    h.chores.unshift({id:store.uid(),task,who:document.getElementById('tkWho').value||h.members[0],done:false});
    store.save(); ui.closeSheet(); ui.toast(t('create.task.done'));
  };
}

/* ----- the sheet ----- */
const ACTIONS=[
  {i:'act-sell',k:'create.sell',fn(){go('market');clickSel('#mkPostBtn',120);after(420,()=>{const c=document.querySelector('#mkTypeChips .chip[data-t="SELL"]');if(c)c.click();});}},
  {i:'act-buy',k:'create.buy',fn(){go('market');clickSel('#mkPostBtn',120);after(420,()=>{const c=document.querySelector('#mkTypeChips .chip[data-t="BUY"]');if(c)c.click();});}},
  {i:'act-job',k:'create.job',fn(){go('work');clickSel('#postJobBtn',120);}},
  {i:'act-event',k:'create.event',fn(){eventSheet();}},
  {i:'act-group',k:'create.group',fn(){go('groups');clickSel('#newHh',120);}},
  {i:'act-memory',k:'create.memory',fn(){go('me');after(150,()=>{const el=document.querySelector('#memTitle');if(el){el.scrollIntoView({block:'center'});el.focus();}});}},
  {i:'act-expense',k:'create.expense',fn(){expenseSheet();}},
  {i:'act-task',k:'create.task',fn(){taskSheet();}},
  {i:'act-post',k:'create.post',fn(){go('groups');after(120,()=>{const s=document.querySelector('[data-sub="campus"]');if(s)s.click();});after(320,()=>{const p=document.querySelector('#campusPost');if(p)p.click();});}},
];

function open(){
  closeOverlays();
  ui.openSheet(
    '<h2>'+t('create.title')+'</h2><p class="sub" style="margin-bottom:6px">'+t('create.sub')+'</p>'+
    '<div class="cgrid">'+ACTIONS.map((a,i)=>'<button class="caction" data-a="'+i+'"><span class="ca">'+HUB.icons.icon(a.i)+'</span><span>'+t(a.k)+'</span></button>').join('')+'</div>'
  );
  document.querySelectorAll('.caction').forEach(b=>{
    b.onclick=()=>{ closeOverlays(); ACTIONS[+b.dataset.a].fn(); };
  });
}

function mount(){
  injectStyle();
  if(document.getElementById('createFab')) return;
  const b=document.createElement('button');
  b.id='createFab'; b.className='createfab'; b.textContent='＋'; b.setAttribute('aria-label',t('create.aria'));
  b.onclick=open;
  document.getElementById('app').appendChild(b);
}

HUB.create={open,mount};
document.addEventListener('DOMContentLoaded',mount);
})();
