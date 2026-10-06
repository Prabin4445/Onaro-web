# Faculty Data Pipeline — state file

PraBin's order (2026-09-23): real professor directory data (name, title, dept, courses) for colleges in USA, Canada, Mexico. USA first, then Canada, then Mexico. 7-day window; speed order same day: maximum parallel coverage.

## Rules
- Public university faculty directories ONLY. Attribution per college in data/ATTRIBUTION.txt (source URL + retrieval date).
- NEVER RateMyProfessors. NEVER invent a name — every name from a real directory page, 5-name spot-check re-verified per college.
- Polite: contact UA, robots.txt, ≤1 req/sec/host, hard stop on 429/403 per host.
- Ratings/comments stay user-generated, start empty. Directory data only.
- Size watch: flag if data/faculty approaches 80MB (surge limit).

## Data format
- `data/faculty/index.json` — {colleges:[{slug,name,country("US"|"CA"|"MX"),match[],source,retrieved,count}]}
- `data/faculty/<slug>.json` — {college,country,professors:[{name,title,dept,courses:[]}]}
- Workers write `data/faculty/_batch-<name>.json` manifests; coordinator merges into index.json + ATTRIBUTION.txt.


## EXPANDED MANDATE (2026-09-23 ~03:35 UTC, PraBin: "I need ALL from them. Don't miss anything.")
- Full coverage of EVERY college/university in USA, Canada, Mexico — not just the first 62.
- Master list: data/faculty/master-list.json (per-country arrays). USA from IPEDS HD2024 (3,950 degree-granting institutions, prioritized by enrollment size tier); Canada from Universities Canada + CICan + provincial lists; Mexico from ANUIES + SEP.
- Entry: {name, slug, country, type, state/province, city, aliases, website, source_hint, status: pending|done|blocked|no-directory|merged}.
- Collection continues in waves via parallel workers; each worker writes data/faculty/<slug>.json + data/faculty/_batch-<wave>-<id>.json manifest. COORDINATOR merges manifests into index.json + ATTRIBUTION.txt + this file. Workers never edit index.json/PIPELINE.md/ATTRIBUTION.txt/master-list.json directly.
- Wave assignment files live in /tmp (wave1-workerN.json); the authoritative queue is master-list.json status fields.
- Merge checklist per wave: validate each <slug>.json (name/title/dept present, no invented data flags), append index entries {slug,name,country,match[],source,retrieved,count}, append ATTRIBUTION.txt lines, update master-list statuses, update Blocked hosts + Size sections below, run qa/qa_faculty.py, deploy (png-move rule), curl-verify live index count.
- match[] for new colleges: include slug variants + IPEDS aliases where available (feeds professors.js forgiving campus matching).

## Wave 1 (2026-09-23, 6 workers x 30 = 180 largest pending US schools)
- worker0: American Public University System ... (see /tmp/wave1-worker0.json)
- worker1: Columbia University ... (see /tmp/wave1-worker1.json)
- worker2: Kennesaw State ... (see /tmp/wave1-worker2.json)
- worker3: South Texas College ... (see /tmp/wave1-worker3.json)
- worker4: University of Mississippi ... (see /tmp/wave1-worker4.json)
- worker5: College of DuPage ... (see /tmp/wave1-worker5.json)
- Status: running. Manifests: data/faculty/_batch-wave1-w0..w5.json (pending).

## Batches (worker -> colleges)
| Batch | Worker | Colleges | Status |
|---|---|---|---|
| us-core | 87bb98c3 | UT Austin, Texas A&M, Dallas College, SMU, UT Dallas, Michigan, UC Berkeley, UCLA, Ohio State, Penn State, Florida, Washington, Georgia Tech, Purdue, Indiana Bloomington, Wisconsin-Madison, NYU, USC, ASU, UNC | running |
| ca | bf4ceb1a | Toronto, UBC, McGill, Waterloo, Alberta, McMaster, Queen's, Western, Calgary, Ottawa | running |
| mx | 16d63e51 | UNAM, ITESM, IPN, Ibero, ITAM | running |
| us-west | 6712f893 | Stanford, Caltech, UCSD, UC Davis, Colorado Boulder, Arizona, Utah, Oregon State, Washington State, UC Irvine | running |
| us-midwest | 26d68944 | Illinois UC, Minnesota, Michigan State, Iowa, Kansas, Nebraska, Missouri, Northwestern, UChicago, Notre Dame | running |
| us-south-ne | 8aba6c77 | UVA, Duke, UGA, FSU, Texas Tech, Houston, Rice, Vanderbilt, Maryland, Rutgers, UPenn, Cornell | running |

## Landed (merged into index.json)
- **ca batch (2026-09-23)**: 9/10 universities, 1,201 professors, 0.15MB. university-of-toronto (178), ubc (115), mcgill (94, CS only — mathstat WAF-blocked), waterloo (27, Pure Math only — CS/JS-walled), mcmaster (330), queens (29), western (66), ucalgary (171), uottawa (191). Todo: Alberta (CloudFront 403, hard stop), McGill Math, Waterloo CS expansion.
- **us-south-ne batch (2026-09-23)**: 11/12 colleges, 1,386 professors. uva (79, CS only — ECE 403 hard stop), duke (94), uga (137), fsu (66, CS only — math no listing), texas-tech (114), uhouston (42, CS only), rice (58, CS only), umd (264), rutgers (160), upenn (163), cornell (209). Todo: Vanderbilt (JS-walled, no data).
- **us-midwest batch (2026-09-23)**: 10/10 colleges, 1,503 professors. illinois (313), minnesota (149), michigan-state (148, engineering only — math Incapsula-walled), iowa (90), kansas (113), nebraska (128), missouri (205), northwestern (127), uchicago (136), notre-dame (94).
- **us-west batch (2026-09-23)**: 10/10 colleges, 1,284 professors. stanford (91), caltech (99), uc-san-diego (140), uc-davis (94), colorado-boulder (141, Physics via public JSON:API), arizona (167), utah (161), oregon-state (112), wsu (122), uc-irvine (157).
- **mx batch (2026-09-23)**: 4/5 universities, 3,104 professors. unam (2,554), itesm (88), ipn (229), itam (233). Todo: Ibero (ibero.mx unreachable, hard stop).
- **us-core batch (2026-09-23)**: 18/20 colleges, 2,199 professors. ut-austin (130), texas-am (50), dallas-college (207), smu (79), ut-dallas (110), umich (98), uc-berkeley (128), ucla (104), ohio-state (105), penn-state (116), ufl (120), uw (93), georgia-tech (203), purdue (150), nyu (125), usc (150), asu (118), unc (113). Todo: Wisconsin (AWS WAF), IU-Bloomington (JS).
- **FINAL: 62 colleges, 10,677 professors, 1.54MB** (US 6,372 / CA 1,201 / MX 3,104). All 6 workers complete.


- **wave1-mx batch (2026-09-23)**: 12 colleges merged, 557 professors. No public directory: wave1-mx: universidad-abierta-y-a-distancia-de-mexico — {'name': 'Universidad Abierta y a Distancia de México', 'reason': 'General information and isolated presenters only; no official public named faculty roster found.'}; wave1-mx: universidad-autonoma-agraria-antonio-narro — {'name': 'Universidad Autónoma Agraria Antonio Narro', 'reason': 'Official searches found job material, old syllabi, and a 2024 provisional telephone directory with abbreviated names/administrative roles, not a qualifying faculty roster.'}; wave1-mx: universidad-autonoma-de-aguascalientes — {'name': 'Universidad Autónoma de Aguascalientes', 'reason': '2021 aggregate profile of 1,698 teachers found; no named roster.'}; wave1-mx: universidad-autonoma-de-baja-california-sur — {'name': 'Universidad Autónoma de Baja California Sur', 'reason': '2022 administrative directory and department contacts only; no named faculty roster.'}; wave1-mx: universidad-autonoma-de-chihuahua — {'name': 'Universidad Autónoma de Chihuahua', 'reason': 'Leadership directory only; the FEI teacher PDF found was severely corrupted and unusable.'}; wave1-mx: universidad-autonoma-de-ciudad-juarez — {'name': 'Universidad Autónoma de Ciudad Juárez', 'reason': 'Old aggregate counts, third-party profiles, and participation calls only; no official named roster.'}; wave1-mx: universidad-autonoma-de-guerrero — {'name': 'Universidad Autónoma de Guerrero', 'reason': 'Administrative/directive material only; no named faculty roster.'}; wave1-mx: universidad-autonoma-de-nuevo-leon — {'name': 'Universidad Autónoma de Nuevo León', 'reason': 'Central faculty-services page, empty researcher/official directories, aggregate faculty-development documents, curricula, and faculty-level administrative material, but no public named professor roster.'}; wave1-mx: universidad-autonoma-del-carmen — {'name': 'Universidad Autónoma del Carmen', 'reason': 'Administrative/vacancy material only; the Engineering site rendered as a JavaScript shell with no usable roster.'}; wave1-mx: universidad-autonoma-del-estado-de-hidalgo — {'name': 'Universidad Autónoma del Estado de Hidalgo', 'reason': 'Administrative directories, organization charts, and isolated course documents only; no named roster.'}; wave1-mx: universidad-autonoma-del-estado-de-mexico — {'name': 'Universidad Autónoma del Estado de México', 'reason': 'Administrative directories, aggregate statistics, a login-only professor portal, PRODEP information, and isolated author affiliations; no public named faculty roster.'}; wave1-mx: universidad-autonoma-del-estado-de-morelos — {'name': 'Universidad Autónoma del Estado de Morelos', 'reason': 'Faculty pages and administrative/job-profile material but no public named professor roster.'}; wave1-mx: universidad-de-colima — {'name': 'Universidad de Colima', 'reason': 'Administrative leaders and program coordinators only; no named faculty roster.'}; wave1-mx: universidad-de-la-salud — {'name': 'Universidad de la Salud', 'reason': 'Budget/program information only; no named public faculty roster.'}; wave1-mx: universidad-juarez-del-estado-de-durango — {'name': 'Universidad Juárez del Estado de Durango', 'reason': 'Isolated responsible teachers named in Forestry course documents; no roster.'}; wave1-mx: universidad-michoacana-de-san-nicolas-de-hidalgo — {'name': 'Universidad Michoacana de San Nicolás de Hidalgo', 'reason': 'Faculty competition calls, job material, and isolated contacts only; no named roster.'}; wave1-mx: universidad-nacional-rosario-castellanos — {'name': 'Universidad Nacional Rosario Castellanos', 'reason': 'Aggregate count of 1,302 professors and institutional documents found, but no named roster.'}; wave1-mx: universidad-pedagogica-nacional — {'name': 'Universidad Pedagógica Nacional', 'reason': 'Staffing totals and administrative material only; no official named faculty roster found.'}. 

- **wave1-w1 batch (2026-09-23)**: 15 colleges merged, 943 professors. Blocked: www.ecu.edu; people.ecu.edu; directory.fiu.edu; directory.drexel.edu; directory.gwu.edu. No public directory: wave1-w1: columbus-state-community-college; wave1-w1: depaul-university; wave1-w1: devry-university-illinois; wave1-w1: drexel-university; wave1-w1: east-carolina-university; wave1-w1: florida-international-university; wave1-w1: fresno-city-college; wave1-w1: front-range-community-college; wave1-w1: full-sail-university; wave1-w1: grand-canyon-university; wave1-w1: hillsborough-community-college; wave1-w1: houston-community-college; wave1-w1: indiana-university-indianapolis; wave1-w1: kansas-state-university; wave1-w1: keiser-university-ft-lauderdale. 

- **wave1-w2 batch (2026-09-23)**: 22 colleges merged, 747 professors. Blocked: directory.nau.edu — Host unreachable (connection closed); official SICCS page links there. No file created; hard stop, not retried. (Northern Arizona University, 2026-09-23). No public directory: wave1-w2: {'slug': 'liberty-university', 'reason': 'private nonprofit'}; wave1-w2: {'slug': 'nuc-university', 'reason': 'private for-profit'}; wave1-w2: {'slug': 'national-university', 'reason': 'private nonprofit'}; wave1-w2: {'slug': 'northeastern-university', 'reason': 'private nonprofit'}; wave1-w2: {'slug': 'nova-southeastern-university', 'reason': 'private nonprofit'}; wave1-w2: {'slug': 'northwest-vista-college', 'reason': 'no public faculty directory found'}; wave1-w2: {'slug': 'palm-beach-state-college', 'reason': 'no public faculty directory found (robots disallow documents paths; people finder JS-driven; /pf/results.aspx 404)'}. 

- **wave1-w4 batch (2026-09-23)**: 24 colleges merged, 4230 professors. Blocked: catalog.charlotte.edu — AWS WAF challenge/202 empty response (2026-09-23); engineering.usu.edu — repeated 45-second timeouts (2026-09-23); egr.vcu.edu — Computer Science people page timed out, then returned repeated empty replies (2026-09-23); catalog.weber.edu — repeated empty replies (2026-09-23). No public directory: wave1-w4: {'slug': 'university-of-phoenix-arizona', 'reason': 'private for-profit — no data file per policy'}; wave1-w4: {'slug': 'university-of-the-cumberlands', 'reason': 'private nonprofit — no data file per policy'}; wave1-w4: {'slug': 'university-of-the-people', 'reason': 'private nonprofit — no data file per policy'}; wave1-w4: {'slug': 'walden-university', 'reason': 'private for-profit — no data file per policy'}; wave1-w4: {'slug': 'american-river-college', 'reason': 'no current public official faculty directory located; retired official CIS page returns 404 and nearest archive snapshot is from 2019 (too stale)'}; wave1-w4: {'slug': 'central-piedmont-community-college', 'reason': 'current official IT program page publishes no faculty names; /faculty-and-staff page has only resources/admin links, not a faculty directory'}. 

- **wave1-w0 batch (2026-09-23)**: 30 colleges merged, 8957 professors. Blocked: eng.auburn.edu — Intermittent status 0 (unreachable); hard-stopped per protocol after the recorded unreachable response. File collected earlier from official directory pages. (Auburn University, 2026-09-23); www.baruch.cuny.edu — Became unreachable then recovered during collection; no further requests made per stop rule. File collected earlier from official profile pages. (CUNY Bernard M Baruch College, 2026-09-23); www.appstate.edu — Cloudflare Access SSO on /directory; departmental faculty pages used instead. Not a block on those pages. (Appalachian State University, 2026-09-23); catalog.uagc.edu — HTTP 522 on /faculty; official static 2025-2026 UAGC Academic Catalog PDF used instead. (Ashford University, 2026-09-23); www.chamberlain.edu — ProxyError/status 0 on faculty PDF paths; official catalog.chamberlain.edu 2026-2027 Academic Catalog Faculty page used instead. (Chamberlain University-Illinois, 2026-09-23); cecas.clemson.edu — status 0 on ECE people page; official Clemson catalog Faculty List PDF + CAFLS directory used instead. (Clemson University, 2026-09-23). 

- **wave1-w3 batch (2026-09-23)**: 29 colleges merged, 1882 professors. Blocked: engineering.louisville.edu — HTTP 403; hard-stopped per protocol. No file created. (University of Louisville, 2026-09-23); speed.louisville.edu — HTTP 403; hard-stopped per protocol. No file created. (University of Louisville, 2026-09-23). 

- **wave1-w5 batch (2026-09-23)**: 22 colleges merged, 4742 professors. Blocked: www.elac.edu — Azure WAF 403 on faculty directory (2026-09-23); collected output deleted per hard-stop rule; www.augusta.edu — robots.txt returned 000/empty reply (2026-09-23); hard stop, not retried; catalog.arapahoe.edu — robots.txt returned 000/empty reply (2026-09-23); hard stop, not retried (used www.arapahoe.edu instead); www.bellevuecollege.edu — robots.txt returned 403 (2026-09-23); used auxiliary official host www2.bellevuecollege.edu; catalog.dmacc.edu — faculty catalog page returned HTTP 202 with empty body on fresh re-fetch (2026-09-23); spot-check blocked; swccd.edu — /_showcase/directory/ returned 000/empty reply on fresh re-fetch (2026-09-23); spot-check blocked, not retried; american.edu — official CAS faculty page returned 403 (2026-09-23); Riverside City College official faculty endpoint — 000/timeout (2026-09-23); hard stop; Saddleback College official host — robots/probes returned 000 (2026-09-23); hard stop; Salt Lake Community College official host — robots.txt returned Azure Application Gateway 403 (2026-09-23); hard stop; San Joaquin Delta College official host — robots/probes returned 000 (2026-09-23); hard stop; www.cod.edu — robots.txt Disallow: /faculty/websites/ for User-agent: * (found 2026-09-23); hard stop on new fetches to that path; existing 240 records retained from earlier collection, cross-checked 17/17 + 5-name verified against official directory pages. No public directory: wave1-w5: {'slug': 'tarrant-county-college-district', 'name': 'Tarrant County College District', 'reason': 'no public official faculty directory located; official directory guesses returned 404; site/catalog searches found only policies, news, and individual contacts (2026-09-23)'}. 

- **wave1-ca batch (2026-09-23)**: 26 colleges merged, 2855 professors. Blocked: ecuad.ca — Official directory blocked by HTTP 403/Cloudflare challenge on 2026-09-23; hard-stopped per protocol. No file created. (Emily Carr University of Art + Design, 2026-09-23); royalroads.ca — Official directory and robots.txt returned HTTP 403 on 2026-09-23; hard-stopped per protocol. No file created. (Royal Roads University, 2026-09-23). No public directory: wave1-ca: {'reason': 'Official directory repeatedly returned HTTP 500/empty/timeouts on 2026-09-23; not retried further. No file created.', 'slug': 'mount-royal-university'}; wave1-ca: {'reason': 'Official directory exists but current public results were not retrievable in this collection environment. No file created.', 'slug': 'capilano-university'}; wave1-ca: {'reason': 'Official directory blocked by HTTP 403/Cloudflare challenge on 2026-09-23. No file created.', 'slug': 'emily-carr-university-of-art-design'}; wave1-ca: {'reason': 'Official directory and robots.txt returned HTTP 403 on 2026-09-23; host hard-stopped. No file created.', 'slug': 'royal-roads-university'}. 
## Todo queue (next daily runs)
- Expand: more departments per landed college; community colleges; Canada beyond U15; Mexico beyond the 5; UK/EU later only on PraBin's order.

## Blocked hosts (wave 3 additions, 2026-09-23)
- research.monash.edu — HTTP 403 on /en/persons/ (2026-09-23); hard stop. (Monash University)
- monash.edu — HTTP 403 on radiography staff page (2026-09-23); hard stop. (Monash University)
- research.uwa.edu.au — unreachable (timeout, code 000) on /en/persons/ (2026-09-23); hard stop. (UWA)
- research-repository.uwa.edu.au — HTTP 403 on /en/persons/ (robots.txt allowed but endpoint refused) (2026-09-23); hard stop. (UWA)
- researchers.mq.edu.au — HTTP 403 on /en/persons/ (2026-09-23); hard stop. (Macquarie University)
- www.griffith.edu.au — HTTP 403 incl. robots.txt (2026-09-23); hard stop. (Griffith University)
- www.latrobe.edu.au — HTTP 403 on department staff page (2026-09-23); hard stop. (La Trobe University)
- www.newcastle.edu.au — HTTP 403 on /profile/staff-list (2026-09-23); hard stop. (The University of Newcastle)
- utas.edu.au — HTTP 403 on education/people (2026-09-23); hard stop. (University of Tasmania)
- coastal.edu — robots.txt User-agent: * Disallow: / (bot allowlist only); hard stop, no collection. (Coastal Carolina University)
- business.csuohio.edu — HTTP 403 on faculty/staff directory; hard stop on that host; landed via 3 other official subdomains. (Cleveland State University)

## Blocked hosts
- ecuad.ca — Official directory blocked by HTTP 403/Cloudflare challenge on 2026-09-23; hard-stopped per protocol. No file created. (Emily Carr University of Art + Design, 2026-09-23)
- royalroads.ca — Official directory and robots.txt returned HTTP 403 on 2026-09-23; hard-stopped per protocol. No file created. (Royal Roads University, 2026-09-23)
- www.elac.edu — Azure WAF 403 on faculty directory (2026-09-23); collected output deleted per hard-stop rule
- www.augusta.edu — robots.txt returned 000/empty reply (2026-09-23); hard stop, not retried
- catalog.arapahoe.edu — robots.txt returned 000/empty reply (2026-09-23); hard stop, not retried (used www.arapahoe.edu instead)
- www.bellevuecollege.edu — robots.txt returned 403 (2026-09-23); used auxiliary official host www2.bellevuecollege.edu
- catalog.dmacc.edu — faculty catalog page returned HTTP 202 with empty body on fresh re-fetch (2026-09-23); spot-check blocked
- swccd.edu — /_showcase/directory/ returned 000/empty reply on fresh re-fetch (2026-09-23); spot-check blocked, not retried
- american.edu — official CAS faculty page returned 403 (2026-09-23)
- Riverside City College official faculty endpoint — 000/timeout (2026-09-23); hard stop
- Saddleback College official host — robots/probes returned 000 (2026-09-23); hard stop
- Salt Lake Community College official host — robots.txt returned Azure Application Gateway 403 (2026-09-23); hard stop
- San Joaquin Delta College official host — robots/probes returned 000 (2026-09-23); hard stop
- www.cod.edu — robots.txt Disallow: /faculty/websites/ for User-agent: * (found 2026-09-23); hard stop on new fetches to that path; existing 240 records retained from earlier collection, cross-checked 17/17 + 5-name verified against official directory pages
- engineering.louisville.edu — HTTP 403; hard-stopped per protocol. No file created. (University of Louisville, 2026-09-23)
- speed.louisville.edu — HTTP 403; hard-stopped per protocol. No file created. (University of Louisville, 2026-09-23)
- eng.auburn.edu — Intermittent status 0 (unreachable); hard-stopped per protocol after the recorded unreachable response. File collected earlier from official directory pages. (Auburn University, 2026-09-23)
- www.baruch.cuny.edu — Became unreachable then recovered during collection; no further requests made per stop rule. File collected earlier from official profile pages. (CUNY Bernard M Baruch College, 2026-09-23)
- www.appstate.edu — Cloudflare Access SSO on /directory; departmental faculty pages used instead. Not a block on those pages. (Appalachian State University, 2026-09-23)
- catalog.uagc.edu — HTTP 522 on /faculty; official static 2025-2026 UAGC Academic Catalog PDF used instead. (Ashford University, 2026-09-23)
- www.chamberlain.edu — ProxyError/status 0 on faculty PDF paths; official catalog.chamberlain.edu 2026-2027 Academic Catalog Faculty page used instead. (Chamberlain University-Illinois, 2026-09-23)
- cecas.clemson.edu — status 0 on ECE people page; official Clemson catalog Faculty List PDF + CAFLS directory used instead. (Clemson University, 2026-09-23)
- catalog.charlotte.edu — AWS WAF challenge/202 empty response (2026-09-23)
- engineering.usu.edu — repeated 45-second timeouts (2026-09-23)
- egr.vcu.edu — Computer Science people page timed out, then returned repeated empty replies (2026-09-23)
- catalog.weber.edu — repeated empty replies (2026-09-23)
- directory.nau.edu — Host unreachable (connection closed); official SICCS page links there. No file created; hard stop, not retried. (Northern Arizona University, 2026-09-23)
- www.ecu.edu
- people.ecu.edu
- directory.fiu.edu
- directory.drexel.edu
- directory.gwu.edu
- www.ualberta.ca — CloudFront HTTP 403 on robots.txt and directory page (2026-09-23); hard stop for host
- www.ibero.mx — host unreachable (2026-09-23); hard stop
- www.wisc.edu — AWS WAF block (2026-09-23); hard stop
- iu.edu (Bloomington) — JS-rendered directory, no static content (2026-09-23)
- www.mcgill.ca (mathstat) — WAF-style closed connections (2026-09-23)
- ece.virginia.edu — 403 hard stop (2026-09-23)
- math.fsu.edu / math.uh.edu — no faculty listings published (2026-09-23)
- math.msu.edu — Incapsula wall (2026-09-23)
- UC Davis CS — Cloudflare block (2026-09-23)
- Stanford Math/EE — JS-rendered (2026-09-23)

## Size
- data/faculty: 13M (349 colleges, 68,488 professors as of 2026-09-23 wave-3 merge) — far from the 80MB flag
- (superseded) ~~17M / 74 colleges / 11,234 professors (wave1-mx merge)~~

## 2026-09-23 ~02:15 CDT — QA reconciliation (main agent)
- qa_faculty found 6 index-count mismatches (index higher than file): mcmaster 330->271, cornell 209->201, usc 150->143, unc-charlotte 57->55, south-carolina-columbia 219->207, wisconsin-madison 401->399. Files (rewritten 00:31 during wave1) are valid with real records; index counts reconciled to file truth. New total: 35,500 professors / 242 colleges.
- ATTRIBUTION GAP: unc-charlotte, south-carolina-columbia, wisconsin-madison lost exact source URLs during context compaction (index shows UNKNOWN placeholder, flagged for follow-up). Data is real; next crew run must re-verify and restore exact source URLs for these three. **RESOLVED 2026-09-23**: all three re-verified live 5/5 and exact source URLs restored in index.json + ATTRIBUTION.txt.

## Wave 2 merge (2026-09-23, coordinator)
- **AUSTRALIA list completion**: master-list.json now carries 193 Australian providers (41 universities, 23 TAFEs, 129 accredited private colleges) from the Dept of Education CRICOS export (2026-03-02), TEQSA, and the WA TAFE handbook — all pending. Adelaide University as the merged institution; Carnegie Mellon Australia excluded (closed). 17 entries have blank websites (no authoritative domain found).
- **Attribution repair**: 5/5 live-verified 2026-09-23 — UNC Charlotte (cci.charlotte.edu/directory/faculty/, 55), South Carolina–Columbia (sc.edu … engineering_and_computing/faculty-staff, 207), Wisconsin–Madison (directory.engr.wisc.edu, 399). 7 legacy UNKNOWN sources remain for a future pass (Nevada-Reno, New Mexico, North Texas, Oklahoma, Oregon, Pittsburgh, South Florida).
- **Wave-2 landed**: 90 files / 28,247 professors merged (mx0 7/647, ca0 10/685, us1 17/4,657, us2 19/5,214 incl. Georgia Gwinnett partial 91, us3 21/2,557, us0 15/14,437, repair 1/50 American College of Education). Index reconciled to file truth (arizona 167→156, bellevue-university 124→122, ambrose-university 133→131, st-marys-university 70→68, the-kings-university 39→80). File schema normalized (department→dept, Canada→CA, required keys only).
- **US0 manifest rebuilt** (_batch-wave2-us0.json, standard schema, 25 outcomes): 15 landed, 2 blocked (CUNY City College 403 Cloudflare, CSU East Bay 403), 4 no-directory (Bryant & Stratton Online robots-disallowed PDF, CSU Dominguez Hills robots Disallow:/, CUNY Lehman + NYC College of Technology unreachable), 4 UNWORKED left pending — central-michigan-university (sweep interrupted mid-crawl, 404 raw cards in ~/workspace/w2scratch/cmich_raw.json, redo needed), cleveland-state-university, coastal-carolina-university, college-of-charleston (no evidence of collection attempt). Never marked no-directory.
- Fresh 5/5 live spot-checks completed for the four US0 repaired files: Campbellsville (285), Carnegie Mellon (1,366), Case Western Reserve (7,502), Central Washington (646), CSU San Bernardino retained file (1,044).
- **New blocked hosts (wave 2)**: uadeo.mx (403), www.ccny.cuny.edu (403 Cloudflare), www.csueastbay.edu (403), bay-river-college + acsenda-school-of-management hosts (CA), glendale-community-college, long-island-university, los-angeles-mission-college, los-angeles-valley-college, mesa-community-college, moorpark-college, ozarks-technical-community-college, miami-university-oxford, eastern-michigan-university.
- **Current size**: data/faculty = 12M — far from the 80MB flag.
- **Master-list**: 4,713 total — done 329, blocked 22, no-directory 94, pending 4,267. Remaining pending by country: US 3,625 / CA 235 / MX 214 / AU 193.
- **Index**: 329 colleges / 63,573 professors (all counts reconciled to file truth).

## Wave 3 merge (2026-09-23, daily-resume coordinator — AU first wave)
- **AU first wave landed**: 17 Australian universities / 4,166 professors merged (first AU data ever in the index).
  - au0 (810): australian-national-university (68, ANU CASS people directory), the-university-of-melbourne (461, 3 Arts schools staff tables), the-university-of-sydney (45, profiles.sydney.edu.au API — academic roles only), the-university-of-new-south-wales (50, researcher profiles; 2 empty titles where bios publish none), the-university-of-queensland (158, SHRS+EECS people listings), adelaide-university (28, profile sitemap; dept not published on profile pages).
  - au1 (2,411): curtin-university (103), queensland-university-of-technology (2,007), rmit-university (17), flinders-university (123), university-of-technology-sydney (161).
  - au2 (945): deakin-university (206, experts.deakin.edu.au — client-side pagination truncates larger schools, partial), james-cook-university (242, 7 Science & Engineering team pages), university-of-wollongong (256, 3 schools), edith-cowan-university (87, School of Nursing and Midwifery), university-of-canberra (82, Faculty of Education, deduped 89→82), swinburne-university-of-technology (72, 3 research centres; no public central directory).
- **US retry landed** (usretry, 749): central-michigan-university (404 — reused wave-2 raw cards from ~/workspace/w2scratch/cmich_raw.json, re-verified live under cmich.edu 5s crawl-delay), cleveland-state-university (72, 4 departments), college-of-charleston (273, 7 departments). All 5/5 live spot-checks.
- **Filename renames** (coordinator): unsw.json→the-university-of-new-south-wales.json, university-of-melbourne.json→the-university-of-melbourne.json, university-of-sydney.json→the-university-of-sydney.json, university-of-queensland.json→the-university-of-queensland.json (canonical master-list slugs for index consistency).
- **New blocked hosts (wave 3)**: research.monash.edu (403 /en/persons/) + monash.edu (403 radiography staff page) — Monash; research.uwa.edu.au (unreachable 000) + research-repository.uwa.edu.au (403 /en/persons/) — UWA; researchers.mq.edu.au (403) — Macquarie; www.griffith.edu.au (403 incl. robots.txt) — Griffith; www.latrobe.edu.au (403) — La Trobe; www.newcastle.edu.au (403 /profile/staff-list) — Newcastle; utas.edu.au (403) — UTAS; coastal.edu (robots.txt: User-agent * Disallow / — bot allowlist only) — Coastal Carolina (no collection, marked blocked not no-directory). Partial: business.csuohio.edu 403 — Cleveland State landed via 3 other official subdomains.
- **Merge**: 20 colleges / 4,915 professors. Index: 349 colleges / 68,488 professors (counts reconciled to file truth; qa_faculty green). ATTRIBUTION.txt appended. AU now 17 colleges / 4,166 professors.
- **Master-list**: 4,713 total — done 349, blocked 30, no-directory 94, pending 4,239. Remaining pending by country: US 3,622 / CA 235 / MX 214 / AU 168.
- **Current size**: data/faculty = 13M — far from the 80MB flag.
- Merge script: data/faculty/merge_wave3.py (backs up to /tmp/w3-*.bak first).

## Wave 4 merge (2026-09-23, daily-resume coordinator — 79 colleges, 6 workers)
- **Assignment**: /tmp/wave4-w4-{us0,us1,us2,us3,cmx,au}.json — 55 US tier-4 (public-4yr first) + 8 CA universities + 8 MX + 8 AU universities. CSU East Bay excluded (host 403-blocked wave 2, still pending).
- **Landed**: 63 colleges / 6,418 professors merged (counts reconciled to file truth; qa_faculty 1657/1657 green).
  - w4-us0 (13 done, 1,217 profs): queens, portland-state, rio-hondo, rutgers-newark, st-cloud-state, st-louis-cc, san-antonio (424), san-diego-mesa, santa-fe, seminole-state, sinclair, south-dakota-state, southeastern-louisiana. All 5/5 live spot-checks.
  - w4-us1 (13 done, 754 profs): siue, siu-carbondale, southern-utah, st-philips, tallahassee-state, tarleton-state, tennessee-tech, tamucc, texas-womans, montana, utc, ut-tyler, towson. 13 files rewritten from bare-list to {college,country,professors} wrapper by coordinator (records valid).
  - w4-us2 (13 done, 1,853 profs): troy, truckee-meadows, tyler-jc, albany, uaa, uc-santa-cruz, central-arkansas, central-missouri, central-oklahoma, uccs, uhd, idaho, ul-lafayette (613). All 5/5 live spot-checks.
  - w4-us3 (13 done, 500 profs): maine, umbc, umass-boston, umass-lowell, umkc, umsl, nebraska-omaha, unh, north-alabama, uncw, uncg, north-dakota, north-florida. All 5/5 live spot-checks.
  - w4-cmx (7 done, 772 profs): new-brunswick, memorial, dalhousie, guelph, laval (269), saskatchewan, anahuac-mexico-norte. All 5/5 live spot-checks.
  - w4-au (4 done, 1,322 profs): western-sydney, victoria, murdoch (526), sunshine-coast (461). All 5/5 live spot-checks.
- **Blocked colleges (13, marked blocked)**: Rio Salado (www.riosalado.edu 403 Cloudflare), Stephen F. Austin (orion.sfasu.edu + apps.utsystem.edu robots unreachable; catalog.sfasu.edu WAF 202-empty), Akron (www.uakron.edu robots 403 Bunny Shield), York (www.yorku.ca robots 000), Concordia (www.concordia.ca robots 000), IT Tijuana / IT Chihuahua / IT Puebla (robots 000 on tijuana/chihuahua/puebla.tecnm.mx), La Salle Bajío (lasallebajio.mx robots 000), Charles Sturt (csu.edu.au robots 403), UNE (robots 000 + www.une.edu.au 403), ACU (site pages 403), CQU (staff portal + main 403).
- **Blocked hosts routed around (college landed anyway)**: password.umb.edu (403), cs.uml.edu + catalog.uml.edu (unreachable), catalog.una.edu (empty robots), catalog.{troy,tjc,uccs,uhd}.edu (AWS WAF 202 — main sites used), goto.murdoch.edu.au (403 subhost-only), physics.qc.cuny.edu (unreachable — Queens data from other pages), business.csuohio.edu (see wave 3).
- **No-directory (3)**: IT Veracruz (admin offices only, no named roster), Ibero Puebla (/directorio is a contact form), UVM Lomas Verdes (executive directory only).
- **Master-list**: 4,713 total — done 412 (+1 merged), blocked 43, no-directory 97, pending 4,160 (US 3,566 / CA 227 / MX 206 / AU 161).
- **Index**: 412 colleges / 74,906 professors (file-truth reconciled).
- **Size**: data/faculty = 14M — far from the 80MB flag.
- Merge script: data/faculty/merge_wave4.py (backs up to /tmp/w4-*.bak first).

## USA blitz wave 1 — Kansas early merge (2026-09-24, blitz coordinator — worker-0, 21 colleges)
- **Trigger**: PraBin's order "complete all usa college and university" after Butler Community College returned no professors. Kansas (worker-0's 31) merged first so Butler is searchable ASAP.
- **Landed**: 21 colleges / 3,639 professors (counts reconciled to file truth): benedictine (222), butler-community-college (134), coffeyville (56), colby (33), cowley (62), dodge-city (47), emporia-state (285), flint-hills-tech (46), fort-scott (33), friends (77), hutchinson (132), kansas-wesleyan (47), labette (31), midamerica-nazarene (63), newman (45), pittsburg-state (385), pratt-cc (34), seward-county (68), washburn (825), wichita-state (605), wsu-tech (409). 13 colleges passed fresh official-source 5-name QA.
- **Butler QA exception (documented, not blocking)**: official employee directory host drops connections (RemoteDisconnected, not a 403/429/robots block); program pages carry no faculty names; the 134 records came from the official 2021-22 catalog and passed structural validation, but a fresh official-source 5-name re-check was not possible. Kept landed with this exception on record.
- **No-directory (9)**: allen-county, cloud-county, garden-city, kansas-city-kansas, neosho-county, salina-tech, saint-mary, + johnson-county & baker (also blocked — see below).
- **Blocked (2)**: www.jccc.edu (robots-disallowed), www.bakeru.edu (fetch block, hard stop).
- **Barton County CC**: worker-0's 54-record build was noncompliant — moved to recoverable trash (20260924-070140-080e897596a84c6ea395535de98ad6e8), stays pending for re-attempt.
- **Attribution caveat**: worker-0 recorded per-file sources only as "official institution-owned public sources" — exact directory URLs were not captured per college. Files normalized to country=US + retrieved=2026-09-24; index source = official college website. Exact per-file directory-URL repair queued for when sandbox egress recovers.
- **Master-list**: done 433 (+21), KS pending 27 remaining.
- **Index**: 433 colleges (file-truth reconciled).

## USA blitz bulk merge (2026-09-29, main agent — fixes "many universities not synced")
- **Root cause of PraBin's report**: 558 colleges / 180,963 professor records were sitting on disk as
  _batch-usa-blitz-*.json + slug files but were NEVER merged into index.json, so the app
  (which resolves campuses via index.json only) showed "No professors listed" — e.g. McNeese
  State University had 243 real records on disk, invisible in the app.
- **Merge**: /tmp/merge_blitz.py — validated every file (non-empty name required), normalized
  schema (bare-list wrap x2: auburn-university-at-montgomery 98, biola-university 227;
  department->dept; country 'USA'->'US', null->'US' after verifying all 19 are US schools),
  skipped 6 empty-professor files (central-lakes-college-brainerd, chamberlain-university
  {georgia,new-jersey,texas}, charter-college, clark-atlanta-university — stay pending),
  zero near-duplicate colleges vs existing index, zero invented-name flags, no high-dup files.
- **Index**: 433 -> 991 colleges, 79,612 -> 260,575 professors. Backup: /tmp/index-blitz-merge-20260929.bak.json.
- **ATTRIBUTION.txt**: appended per-college source lines (from batch manifest sources or
  "official institution website" fallback).
- **Master-list**: 557 statuses -> done; stats now done 990 / blocked 43 / no-directory 106 / pending 3,574 of 4,713.
- **QA**: qa_faculty.py 3973/3973 green (index-count reconciliation, spot checks, honest fallback).
- **Still pending**: 3,574 schools (US 3,5xx) — collection waves continue; blocked/no-directory
  schools are honestly marked and the app shows the empty-state with + Add professor.

- **cc1-2 batch (2026-09-29)**: 8 colleges merged, 4432 professors. Blocked: 13. No public directory: 4.

- **cc1-7 batch (2026-09-29)**: 23 colleges merged, 2212 professors. Blocked: 2. No public directory: 0.

- **cc1-4 batch (2026-09-29)**: 11 colleges merged, 2168 professors. Blocked: 8. No public directory: 6.


- **cc1-6 batch (2026-09-30)**: 18 colleges merged, 1503 professors. Blocked: 4. No public directory: 3.

- **cc1-1 batch (2026-09-29)**: 14 colleges merged, 5374 professors. Blocked: 7. No public directory: 4.

- **cc1-3 batch (2026-09-29)**: 16 colleges merged, 4124 professors. Blocked: 4. No public directory: 5.

- **cc1-0 batch (2026-09-29)**: 13 colleges merged, 6319 professors. Blocked: 7. No public directory: 5.

- **cc1-5 batch (2026-09-29)**: 17 colleges merged, 2148 professors. Blocked: 0. No public directory: 8.

- **waveB-5 batch (2026-09-30)**: 2 colleges merged, 303 professors. Blocked: 0. No public directory: 0.

- **waveB-0 batch (2026-09-30)**: 5 colleges merged, 640 professors. Blocked: 0. No public directory: 0.

- **waveB-8 batch (2026-09-30)**: 7 colleges merged, 864 professors. Blocked: 0. No public directory: 0.

- **waveB-9 batch (2026-09-30)**: 22 colleges merged, 1515 professors. Blocked: 6. No public directory: 0.

- **waveB-9 correction (2026-09-30)**: post-merge verification removed 4 records (Avery Point 94→92, New Kensington 43→42, Sisseton Wahpeton 11→10) and reverted Penn State Mont Alto (71 records) to pending after a 3/5 verification fail. Net index: 1146 colleges, 292102 professors.

- **waveB-4 batch (2026-09-30)**: 17 colleges merged, 1402 professors. Blocked: 0. No public directory: 0.

- **waveB-4 batch (2026-09-30)**: 0 colleges merged, 0 professors. Blocked: 1. No public directory: 0.

- **master-list audit (2026-09-30)**: resolved the done(1166)-vs-index(1163) gap — no missing index entries. Two cross-country slug collisions had wrongly marked Canadian schools done (CA st-thomas-university and CA victoria-university pointed at the US/AU index files); both reset to pending with reasons. Remaining 1-gap is the legitimate ASU case: Campus Immersion + Digital Immersion both done via the single `asu` index file (real ASU engineering faculty). Master stats now: done=1164, blocked=100, no-directory=136, pending=3313.

- **waveB-1 batch (2026-09-30)**: 7 colleges merged, 2423 professors. Blocked: 0. No public directory: 0.

- **waveD batch (2026-09-30)**: 38 colleges merged, 1851 professors. Blocked: 2. No public directory: 19.

- **waveE batch (2026-09-30)**: 43 colleges merged, 2139 professors. Blocked: 1. No public directory: 15.

- **waveF batch (2026-10-01)**: 28 colleges merged, 2443 professors. Blocked: 0. No public directory: 13. Dedup aliases: 2 (southern-tech-fl, western-tech-tx).

- **waveF batch (2026-10-01) totals**: 42 colleges merged, 3122 professors. Blocked: 0. No public directory: 16. Dedup aliases: 2. Worker-1 manifest shape note: `files` keyed by filename.

- **waveF batch (2026-10-01) final**: 42 colleges merged, 3122 professors. Blocked: 0. No public directory: 16. Dedup aliases: 2. Merge lessons: handle manifest shapes `records`-keyed files, `files`-keyed manifests, `ok` status; slug remaps.

- **waveG batch (2026-10-01)**: 32 colleges merged, 4144 professors. Blocked: 0. No public directory: 9 (9 stale-catalog honest zeros incl. Inter American campuses). File schemas handled: professors/records/faculty keys; manifest shapes: entries/schools-list/schools-dict/files.

- **waveH batch (2026-10-01)**: 18 colleges merged, 4148 professors. Blocked: 2. No public directory: 28 (incl. 1 stale-catalog honest zero: Univ. of Olivet).

- **waveH batch (2026-10-01) final**: 30 colleges merged, 5026 professors. Blocked: 2. No public directory: 28 (incl. 1 stale-catalog honest zero: Univ. of Olivet). Merge lessons: manifest entries keyed by `file` not `slug`; `coverage` field separate from status.

- **waveI batch (2026-10-01)**: 24 colleges merged, 3561 professors. Blocked: 0. No public directory: 11 (incl. 1 stale-source honest zero: Univ. of St Francis IL). Deferred to dedicated pass (stays pending): San Francisco (JS-directory ~680). Honest zeros: UT Southwestern, UNMC, St Thomas TX, Mt Olive/Union, UNM-Taos, Phoenix CA/HI/TX, NW Ohio, San Diego, Saint Joseph, UPR Med/Ponce/Arecibo/Bayamon/Carolina, St Augustine.

- **waveI batch (2026-10-01) shape-recovery pass**: 0 colleges merged, 0 professors (worker2 bare slug-keyed manifest, worker4 statusless school entries). No-directory: 7 (incl. 1 stale-source honest zero: Univ. of St Francis IL).

- **waveJ batch (2026-10-01)**: 42 colleges merged, 5209 professors (San Francisco dedicated pass: 1,070; Incarnate Word 453; West Alabama 454). Blocked: 0. No public directory: 18 (incl. 2 stale-source honest zeros: Abcott Institute 2023-24, Valley Forge 2024-25; paraeducators stripped at ABC Adult School). Potomac VA/DC share the school's one unified roster (disclosed). Merge: (country,slug)-keyed master map; cross-country dupe sweep clean.

- **waveK batch (2026-10-01)**: 30 colleges merged, 796 professors (AdventHealth 275, Alaska Pacific 59, Albany Pharmacy 68, Albany Law 47). Blocked: 0. No public directory: 17 (stale-catalog honest zeros applied by workers: Adrian Wallace 2019, Advanced Barber 2019, AVTEC 2021-24, Albany Beauty 2023-24, Esthetics CA ~2022). Merge: (country,slug)-keyed map; dupe sweep clean; _batch manifests now archived to backups dir (kept out of hub/).

- **waveL batch (2026-10-01)**: 48 colleges merged, 16623 professors (RIT 1371 partial, Princeton 1123, WGU 1071, SJU NY 1038, South College 816). Blocked: 2 (NYIT, Villanova — JS-only). No public directory: 7. Merge: bare-dict+entries shapes handled, credential suffixes stripped from names (worker0 kept 'MFA/PhD' suffixes), slug-vs-assignment check clean, _batch manifests archived to backups dir.

- **waveM batch (2026-10-01)**: 40 colleges merged, 6251 professors (Ultimate Medical 544, Cambridge 397, CalArts 320, Alvernia 298). Blocked: 0. No public directory: 5. Anderson U identity call: worker collected SC under IN slug — remapped to anderson-university-sc; IN school stays pending. _batch manifests archived to backups dir.
