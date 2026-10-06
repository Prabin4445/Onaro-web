/* Degree tracker smoke test: loads the real i18n/store/degree modules in jsdom,
   stubs fetch to read the real JSON, and drives the UI.
   Run:  cd /tmp && npm install jsdom   (once)
         node ~/workspace/hub/qa/qa_degree_smoke.js
   36 checks: entry card, picker (counts/filter/search), all-plan render,
   completion toggle + persistence, prereq warnings, choice sheets, transfer
   view, plan switching, Escape, active-plan resume. */
const fs=require('fs');
const {JSDOM}=require('/tmp/node_modules/jsdom');
const HUB='/home/hatch/workspace/hub';

const dom=new JSDOM(
 '<!DOCTYPE html><html><body>'+
 '<div id="app"></div>'+
 '<div id="sheetHost" hidden><div id="sheetBox"></div></div>'+
 '<div id="toastHost"></div>'+
 '</body></html>',
 {url:'https://hub-preview.surge.sh/', runScripts:'dangerously'});

/* fetch stub -> local files */
dom.window.fetch=function(url){
  const p=HUB+'/'+String(url).replace(/^\.\//,'');
  const ok=fs.existsSync(p);
  return Promise.resolve({
    ok:ok, status:ok?200:404,
    json:function(){ return Promise.resolve(JSON.parse(fs.readFileSync(p,'utf8'))); }
  });
};
/* silence animation bits jsdom lacks */
if(!dom.window.Element.prototype.setPointerCapture) dom.window.Element.prototype.setPointerCapture=function(){};

for(const f of ['js/i18n.js','js/store.js','js/degree.js']){
  dom.window.eval(fs.readFileSync(HUB+'/'+f,'utf8'));
}
const W=dom.window, D=W.document;
const tick=(ms)=>new Promise(r=>setTimeout(r,ms||60));
let pass=0, fail=0;
function eq(name,cond,extra){
  if(cond){ pass++; console.log('  PASS '+name); }
  else{ fail++; console.log('  FAIL '+name+(extra?' :: '+extra:'')); }
}

(async()=>{
  console.log('== entry card ==');
  const scope=D.createElement('div');
  scope.innerHTML=W.HUB.degree.entryHTML();
  W.HUB.degree.bindEntry(scope);
  await tick(80);
  eq('entry card markup', !!scope.querySelector('#homeDegEntry'));
  const sub=scope.querySelector('#homeDegSub').textContent;
  eq('entry sub has honest counts', sub==='7 plans · 3 schools', sub);

  console.log('== picker ==');
  W.HUB.degree.open(null);
  await tick(120);
  let schools=D.querySelectorAll('.deg-school');
  eq('3 school cards', schools.length===3, schools.length);
  const dc=[...schools].find(s=>s.querySelector('h3').textContent==='Dallas College');
  eq('coverage text', dc.querySelector('.meta').textContent==='3 of 102 programs', dc.querySelector('.meta').textContent);
  eq('more-coming badge', !!dc.querySelector('.deg-more'));
  let rows=D.querySelectorAll('.deg-planrow');
  eq('7 collected plan rows', rows.length===7, rows.length);
  eq('block badge', [...D.querySelectorAll('.deg-tcbadge')].some(b=>b.textContent.includes('block')));
  eq('pending toggles', D.querySelectorAll('.deg-pending-tgl').length===3);
  const pendBox=D.querySelector('[data-pendbox="dallas-college"]');
  eq('pending collapsed by default', pendBox&&pendBox.hidden===true);
  /* filter to bachelor */
  D.querySelector('.deg-chip[data-level="bachelor"]').click();
  await tick(80);
  eq('bachelor filter -> 2 schools', D.querySelectorAll('.deg-school').length===2);
  eq('bachelor filter -> 4 plan rows', D.querySelectorAll('.deg-planrow').length===4);
  D.querySelector('.deg-chip[data-level="all"]').click();
  await tick(80);
  /* search */
  const q=D.getElementById('degQ');
  q.value='nursing';
  q.dispatchEvent(new W.Event('input',{bubbles:true}));
  await tick(500);
  eq('search nursing -> 2 schools', D.querySelectorAll('.deg-school').length===2, D.querySelectorAll('.deg-school').length);
  eq('search expands pending', D.querySelector('[data-pendbox="dallas-college"]').hidden===false);

  console.log('== tracker: utd-bs-computer-science (no xfer) ==');
  W.HUB.degree.open('utd-bs-computer-science');
  await tick(150);
  eq('8 semester sections', D.querySelectorAll('.deg-sem').length===8);
  eq('44 course tiles', D.querySelectorAll('.deg-tile').length===44, D.querySelectorAll('.deg-tile').length);
  const pace=D.querySelector('.deg-pace').textContent;
  eq('fresh plan on track', pace.includes('On track'), pace);
  eq('ring shows 0%', D.querySelector('.deg-ring-num').textContent==='0%');
  eq('source line', D.querySelector('.deg-source').textContent.includes('2025-2026'));
  eq('finish hint', D.querySelector('.deg-finish').textContent.includes('15 credits/semester'));
  D.getElementById('degTabXfer').click();
  await tick(60);
  eq('UTD xfer honest empty', D.querySelector('.deg-body').textContent.includes('No verified equivalencies yet'));
  D.getElementById('degTabPlan').click();
  await tick(60);

  console.log('== toggle completion + persistence ==');
  const before=W.HUB.store.state.degree;
  D.querySelector('.deg-tile[data-slot="s1-1"] [data-check]').click();
  await tick(60);
  const prog=W.HUB.store.state.degree.progress['utd-bs-computer-science'];
  eq('slot recorded', !!(prog&&prog.done['s1-1']&&prog.done['s1-1'].code==='RHET 1302'));
  eq('toast fired', D.getElementById('toastHost').textContent.includes('completed'));
  eq('ring updated', D.querySelector('.deg-ring-num').textContent!=='0%', D.querySelector('.deg-ring-num').textContent);
  eq('tile done class', !!D.querySelector('.deg-tile[data-slot="s1-1"].done'));
  eq('burst animation class', !!D.querySelector('.deg-tile[data-slot="s1-1"].deg-pop'));
  eq('float chip', !!D.querySelector('.deg-tile[data-slot="s1-1"] .deg-float'));
  /* unmark */
  D.querySelector('.deg-tile[data-slot="s1-1"] [data-check]').click();
  await tick(60);
  eq('slot unmarked', !W.HUB.store.state.degree.progress['utd-bs-computer-science'].done['s1-1']);

  console.log('== prereq warnings (uta-bs-computer-science) ==');
  W.HUB.degree.open('uta-bs-computer-science');
  await tick(150);
  const warns=D.querySelectorAll('.deg-warn');
  eq('prereq warnings present', warns.length>0, warns.length);
  const wtxt=[...warns].map(w=>w.textContent).join(' | ');
  eq('ENGL 1301 prereq warning', wtxt.includes('ENGL 1301'), wtxt.slice(0,120));

  console.log('== choice slots ==');
  const choiceTile=D.querySelector('.deg-tile .deg-choice-chip');
  eq('choice chips present', !!choiceTile);
  /* open a choice slot with enumerated options via detail path: find one with options */
  /* use the sheet directly: pick first choice tile's data-open */
  const firstChoice=[...D.querySelectorAll('.deg-tile')].find(tl=>tl.querySelector('.deg-choice-chip'));
  firstChoice.querySelector('[data-open]').click();
  await tick(60);
  const sheet=D.getElementById('sheetBox').innerHTML;
  eq('choice sheet opened', sheet.includes('Choose a course')||sheet.includes('degChoiceCode'));

  console.log('== transfer view (dallas-college-as-computer-science) ==');
  W.HUB.degree.open('dallas-college-as-computer-science');
  await tick(150);
  D.getElementById('degTabXfer').click();
  await tick(60);
  const xb=D.querySelector('.deg-body').textContent;
  eq('xfer summaries', xb.includes('credits transfer to'), xb.slice(0,100));
  eq('xfer rows', D.querySelectorAll('.deg-xrow').length>0);

  console.log('== switch plan + escape ==');
  D.getElementById('degTabPlan').click(); await tick(40);
  D.getElementById('degSwitch').click(); await tick(200);
  eq('switch -> picker preserves search', D.querySelectorAll('.deg-school').length===2&&D.getElementById('degQ').value==='nursing',
     'schools='+D.querySelectorAll('.deg-school').length+' q='+JSON.stringify(D.getElementById('degQ').value));
  D.dispatchEvent(new W.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  await tick(40);
  eq('escape closed overlay', !D.getElementById('hubDegRoot'));

  console.log('== reopen resumes active plan ==');
  W.HUB.degree.open(W.HUB.degree._state().active||null);
  await tick(150);
  eq('resumed tracker (8 sems = utd plan was last? no: dallas AS=4)',
     D.querySelectorAll('.deg-sem').length===4, D.querySelectorAll('.deg-sem').length);

  console.log('\nRESULT: '+pass+' pass, '+fail+' fail');
  process.exit(fail?1:0);
})().catch(e=>{ console.error('HARNESS ERROR',e); process.exit(2); });
