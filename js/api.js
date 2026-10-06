/* HUB.api — optional backend data layer (Phase 1, 2026-10-05).
   When an API base URL is configured, degree plans, professor directory and
   horoscopes load from the FastAPI backend instead of the bundled static
   JSON files. API responses are adapted back into the EXACT shapes the app
   already expects, so no other app code changes.

   Configuration (first match wins):
     1. window.__ONARO_API_BASE  (build/deploy-time flag)
     2. localStorage 'onaro_api_base' (operator override, e.g. for testing)
   When neither is set, everything works exactly as before (static JSON).
   If the API is reachable but a request fails, each loader falls back to
   the static file — the app never hard-depends on the backend. */
(function(){
  'use strict';
  var LS_KEY='onaro_api_base';
  function base(){
    try{
      if(window.__ONARO_API_BASE) return String(window.__ONARO_API_BASE).replace(/\/+$/,'');
      var v=null;
      try{ v=localStorage.getItem(LS_KEY); }catch(e){}
      if(v) return String(v).replace(/\/+$/,'');
    }catch(e){}
    return '';
  }
  function on(){ return !!base(); }
  function aj(path){
    /* Use the safe fetch with retries (js/safeboot.js) — Render free tier
       sleeps and needs 30-60s to wake. Plain fetch fails once and gives up,
       leaving the app with "0 plans". Use generous retries for cold starts. */
    var f=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){
      return fetch(u).then(function(r){
        if(!r.ok&&r.status!==0) throw new Error('http '+r.status);
        return r.json();
      });
    };
    /* 5 retries × 15s timeout = up to ~75s for Render cold start */
    return f(base()+path, {retries:5, timeout:15000});
  }

  /* ---------- degree plans ---------- */
  // -> {plans:[{slug,school,school_slug,city,state,kind,degree,major,credits,
  //             semesters,catalog,source,transfer_confidence,level}], schools:[...]}
  function degreeIndex(){
    return Promise.all([
      aj('/api/degrees/search?limit=20000'),
      aj('/api/schools?limit=20000').catch(function(){ return {items:[]}; })
    ]).then(function(res){
      var dj=res[0], sj=res[1];
      var plans=(dj.items||[]).map(function(p){
        return {
          slug:p.plan_slug, school:p.institution_name, school_slug:p.institution_slug,
          city:p.city||'', state:p.state||'', kind:p.kind||'',
          degree:p.degree, major:p.major,
          credits:p.total_credits, semesters:null,
          catalog:p.catalog_year||'', source:p.source_url||'',
          transfer_confidence:'', level:p.level||''
        };
      });
      var schools=(sj.items||[]).map(function(s){
        return {slug:s.slug, name:s.name, city:s.city||'', state:s.state||'',
                kind:s.kind||'', country:s.country||'US', programs:[],
                programs_collected:0, programs_total:0};
      });
      /* Group plans by school to build the programs array the UI expects */
      var schoolBySlug={};
      schools.forEach(function(sch){ schoolBySlug[sch.slug]=sch; });
      plans.forEach(function(pl){
        var sch=schoolBySlug[pl.school_slug];
        if(sch){
          sch.programs.push({
            status:'collected', plan_id:pl.slug,
            program:pl.major, degree:pl.degree
          });
          sch.programs_collected++;
          sch.programs_total++;
        }
      });
      return {plans:plans, schools:schools};
    });
  }
  // -> {institution:{name,slug}, plan:{id,degree,major,catalog_year,total_credits,
  //        source_url,transfer_confidence,last_verified,notes,semesters:[...]}}
  //    course: {slot_id,code,title,credits,category,choice,choice_note,prereq,tccns}
  function degreeFile(slug){
    return aj('/api/degrees/'+encodeURIComponent(slug)).then(function(p){
      return {
        institution:{name:p.institution_name, slug:p.institution_slug},
        plan:{
          id:p.plan_slug, degree:p.degree, major:p.major,
          catalog_year:p.catalog_year, total_credits:p.total_credits,
          source_url:p.source_url, transfer_confidence:p.transfer_confidence,
          content_hash:'', last_verified:p.last_verified, notes:p.notes,
          semesters:(p.semesters||[]).map(function(s){
            return {n:s.n, label:s.label, courses:(s.courses||[]).map(function(c){
              return {slot_id:c.slot_id, code:c.code, title:c.title,
                      credits:c.credits, category:c.category,
                      choice:!!c.is_choice, choice_note:c.choice_note,
                      prereq:c.prereq||[], tccns:c.tccns};
            })};
          })
        }
      };
    });
  }

  /* ---------- professor directory ---------- */
  // -> {colleges:[{slug,name,country,match,source,retrieved,count}]}
  function facultyIndex(){
    return aj('/api/schools?limit=20000').then(function(j){
      return {colleges:(j.items||[]).map(function(s){
        return {slug:s.slug, name:s.name, country:s.country||'US', match:[],
                source:s.source_url||'', retrieved:'', count:0};
      })};
    });
  }
  // -> {professors:[{name,title,dept,courses}]}
  function facultyFile(slug){
    return aj('/v1/institutions/'+encodeURIComponent(slug)+'/professors?limit=20000')
      .then(function(j){
        return {professors:(j.items||[]).map(function(p){
          return {name:p.name, title:p.title, dept:p.dept, courses:p.courses||[]};
        })};
      });
  }

  /* ---------- horoscopes ---------- */
  // -> {date, signs:{...}} — same shape the app already reads.
  function horoscopeURL(){ return base()+'/api/horoscopes/today'; }

  window.HUB=window.HUB||{};
  window.HUB.api={
    on:on, base:base,
    degreeIndex:degreeIndex, degreeFile:degreeFile,
    facultyIndex:facultyIndex, facultyFile:facultyFile,
    horoscopeURL:horoscopeURL
  };
})();
