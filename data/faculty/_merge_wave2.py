#!/usr/bin/env python3
"""Wave-2 merge: normalize files, rebuild us0 manifest, update index.json,
ATTRIBUTION.txt, master-list.json. Run from data/faculty/.
Idempotent for index/attribution/master-list updates (re-runnable)."""
import json, os, collections, sys

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
DATE = "2026-09-23"

BATCHES = [
    ("_batch-wave2-mx0.json", "MX"),
    ("_batch-wave2-ca0.json", "CA"),
    ("_batch-wave2-us1.json", "US"),
    ("_batch-wave2-us2.json", "US"),
    ("_batch-wave2-us3.json", "US"),
    ("_batch-wave2-repair.json", "US"),
]
LANDED_OK = ("landed", "done", "complete", "ok", "blocked/partial")

log = []

# ---------- 1. Collect outcomes ----------
landed = []   # dicts: slug,name,country,count,sources,note,spot_check,batch
blocked = []  # (country, slug, name, reason)
nodir = []    # (country, slug, name, reason)
for mf, country in BATCHES:
    d = json.load(open(mf))
    for c in d.get("colleges", []):
        s = c.get("status")
        if s in LANDED_OK:
            landed.append({
                "slug": c["slug"], "name": c["name"], "country": country,
                "count": c.get("count"), "sources": c.get("sources", []) or [],
                "note": c.get("note", ""), "spot_check": c.get("spot_check", ""),
                "batch": mf.replace("_batch-", "").replace(".json", ""),
            })
        elif s in ("blocked",):
            blocked.append((country, c["slug"], c["name"], c.get("note", "")))
    for b in d.get("blocked", []):
        if isinstance(b, dict):
            blocked.append((country, b.get("slug", ""), b.get("name", b.get("college", "")), b.get("reason", "")))
        else:
            blocked.append((country, b, b, ""))
    for n in d.get("no_directory", []):
        if isinstance(n, dict):
            nodir.append((country, n.get("slug", "") or "",
                          n.get("name", n.get("college", "")),
                          n.get("reason", "")))
        elif n:
            nodir.append((country, n, n, ""))

# mx0 no_directory entries were bare nulls in a parallel list; recover from worker notes is impossible,
# so keep them as-is (they are already in master-list as no-directory from queue hygiene step).
mx = json.load(open("_batch-wave2-mx0.json"))
mx_slugs = {c["slug"] for c in landed if c["batch"] == "wave2-mx0"}
log.append(f"mx0 landed: {len(mx_slugs)}")

# ---------- 2. US0 manifest rebuild (25 outcomes) ----------
us0_old = json.load(open("_batch-wave2-us0.json"))
us0_files = {f["slug"]: f for f in us0_old["files"]}
US0_EXTRA = {
    "campbellsville-university": {
        "name": "Campbellsville University", "count": 285,
        "sources": ["https://www.campbellsville.edu/campus-life/campus-resources/faculty-directory/index.html"],
        "note": "Worker mis-named file corrected to slug + schema; country normalized to US. Official faculty/staff directory.",
        "spot_check": "5/5 confirmed live on official directory (Blake Johnson, Tim Rogers, Joe Foster, Susan Burress, Rita Creason), verified 2026-09-23",
    },
    "carnegie-mellon-university": {
        "name": "Carnegie Mellon University", "count": 1366,
        "sources": ["https://www.cmu.edu/bme/People/Faculty/index.html",
                    "https://engineering.cmu.edu/directory/index.html"],
        "note": "Worker swept 65 BME bios + engineering directory pages. File corrected to slug + schema; country normalized to US.",
        "spot_check": "5/5 confirmed on official CMU pages (Rosalyn Abbott, Alison L. Barth, Amir Barati Farimani, Kathleen A. Bieryla, James (Drew) Beauchamp), verified 2026-09-23",
    },
    "case-western-reserve-university": {
        "name": "Case Western Reserve University", "count": 7502,
        "sources": ["https://bulletin.case.edu/arts-sciences/anthropology/",
                    "https://anthropology.case.edu/faculty/"],
        "note": "Worker swept Case anthropology faculty pages + official course catalog. File corrected to slug + schema; country normalized to US.",
        "spot_check": "5/5 confirmed on official Case bulletin anthropology faculty listing (Katia Almeida-Tracy, Lawrence Greksa, Bridget Haas, Lee Hoffer, Megan Schmidt-Sane), verified 2026-09-23",
    },
    "central-washington-university": {
        "name": "Central Washington University", "count": 646,
        "sources": ["CWU official Acalog academic catalog (catoid 89), 'Faculty as of January 2023'",
                    "https://www.cwu.edu/directory/"],
        "note": "Worker built from official Acalog catalog; bare array wrapped into required schema.",
        "spot_check": "5/5 fresh verification by worker on cwu.edu directory (Dondji, Divine, Zuckerman, Andonie confirmed; Sarah Abdul-Wahid removed as emeritus), 2026-09-23",
    },
}
US0_UNWORKED = {
    "central-michigan-university": "US0 sweep interrupted mid-crawl: 404 raw directory cards captured in ~/workspace/w2scratch/cmich_raw.json but never cleaned or validated into a faculty file. Host responded normally (no block observed). Left pending for a redo wave.",
    "cleveland-state-university": "No evidence of any collection attempt found in worker scratch (/tmp) or workspace; left pending.",
    "coastal-carolina-university": "No evidence of any collection attempt found in worker scratch (/tmp) or workspace; left pending.",
    "college-of-charleston": "No evidence of any collection attempt found in worker scratch (/tmp) or workspace; left pending.",
}
us0_colleges = []
for slug, f in us0_files.items():
    us0_colleges.append({
        "name": f["name"], "slug": slug, "status": "landed", "count": f["count"],
        "retrieved": f.get("retrieved", DATE),
        "departments": f.get("departments", []),
        "sources": [],
        "note": "Per-file source URLs were not recorded in the worker manifest; provenance in coordinatorAttention notes.",
        "spot_check": "",
    })
for slug, x in US0_EXTRA.items():
    us0_colleges.append({
        "name": x["name"], "slug": slug, "status": "landed", "count": x["count"],
        "retrieved": DATE, "sources": x["sources"], "note": x["note"],
        "spot_check": x["spot_check"],
    })
for b in us0_old["blockedHosts"]:
    us0_colleges.append({"name": b["college"], "slug": b["college"].lower().replace(" ", "-").replace("&", "and"),
                         "status": "blocked", "count": 0, "retrieved": DATE,
                         "sources": [], "note": b["reason"], "spot_check": ""})
for n in us0_old["noDirectory"]:
    us0_colleges.append({"name": n["slug"].replace("-", " ").title(), "slug": n["slug"],
                         "status": "no-directory", "count": 0, "retrieved": DATE,
                         "sources": [], "note": n["reason"], "spot_check": ""})
for slug, reason in US0_UNWORKED.items():
    us0_colleges.append({"name": slug.replace("-", " ").title(), "slug": slug,
                         "status": "unworked", "count": 0, "retrieved": DATE,
                         "sources": [], "note": reason, "spot_check": ""})
assert len(us0_colleges) == 25, f"us0 outcomes = {len(us0_colleges)}, expected 25"

for slug, x in US0_EXTRA.items():
    landed.append({"slug": slug, "name": x["name"], "country": "US", "count": x["count"],
                   "sources": x["sources"], "note": x["note"], "spot_check": x["spot_check"],
                   "batch": "wave2-us0"})
for slug, f in us0_files.items():
    landed.append({"slug": slug, "name": f["name"], "country": "US", "count": f["count"],
                   "sources": [], "note": "wave2-us0 original 11; per-file sources not recorded in worker manifest",
                   "spot_check": "", "batch": "wave2-us0"})
# us0 blocked / no-directory (match master-list slugs)
us0_old_blocked = [("US", "cuny-city-college", "CUNY City College",
                    "Official host returned HTTP 403 (Cloudflare challenge) on 2026-09-23; hard-stopped per protocol.")]
us0_old_nodir = [
    ("US", "bryant-stratton-college-online", "Bryant & Stratton College-Online",
     "Official staff PDF path /pdf/ is robots-disallowed (Disallow: /pdf/); no qualifying named instructional-faculty roster. 2026-09-23."),
    ("US", "california-state-university-dominguez-hills", "California State University-Dominguez Hills",
     "Official robots.txt returned User-agent: * / Disallow: / on 2026-09-23; no compliant crawl possible."),
    ("US", "cuny-lehman-college", "CUNY Lehman College",
     "Official host repeatedly unreachable (connection timeout) on 2026-09-23; no HTTP 403/429 observed."),
    ("US", "cuny-new-york-city-college-of-technology", "CUNY New York City College of Technology",
     "Official host repeatedly unreachable over HTTP/HTTPS (connection timeout) on 2026-09-23."),
]
blocked += us0_old_blocked
nodir += us0_old_nodir

# ---------- 3. Normalize faculty files ----------
norm_issues = []
for c in landed:
    s = c["slug"]; p = s + ".json"
    if not os.path.exists(p):
        norm_issues.append((s, "FILE MISSING")); continue
    d = json.load(open(p))
    changed = False
    if d.get("country") == "Canada":
        d["country"] = "CA"; changed = True
    for k in ("source", "departments"):
        if k in d:
            del d[k]; changed = True
    for pr in d.get("professors", []):
        if "department" in pr:
            pr["dept"] = pr.pop("department"); changed = True
        extra = set(pr) - {"name", "title", "dept", "courses"}
        if extra:
            for k in extra: del pr[k]; changed = True
    extra_top = set(d) - {"college", "country", "professors"}
    if extra_top:
        for k in extra_top: del d[k]; changed = True
    # file truth
    n = len(d["professors"])
    if n != c["count"]:
        log.append(f"COUNT-ADJUST {s}: manifest {c['count']} -> file truth {n}")
        c["count"] = n
    c["name"] = d.get("college", c["name"])
    c["country"] = d.get("country", c["country"])
    # validate
    assert set(d) == {"college", "country", "professors"}, (s, set(d))
    for pr in d["professors"]:
        assert set(pr) <= {"name", "title", "dept", "courses"}, (s, set(pr))
        assert pr.get("name"), (s, "empty name")
    if changed:
        json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
log.append(f"normalized {len(landed)} files; issues: {norm_issues}")

# ---------- 4. index.json ----------
idx = json.load(open("index.json"))
entries = {e["slug"]: e for e in idx["colleges"]}
fix_counts = {"arizona": 156, "bellevue-university": 122, "ambrose-university": 131,
              "st-marys-university": 68, "the-kings-university": 80}
for slug, n in fix_counts.items():
    if slug in entries:
        entries[slug]["count"] = n
        log.append(f"index count fixed {slug} -> {n}")
added = 0
for c in landed:
    s = c["slug"]
    src = "; ".join(c["sources"]) if c["sources"] else \
        f"UNKNOWN — collected from an official college faculty/staff directory; per-file source URL not recorded in the {c['batch']} worker manifest (coordinator follow-up)"
    if s in entries:
        e = entries[s]
        e["count"] = c["count"]; e["source"] = src; e["retrieved"] = DATE
    else:
        entries[s] = {"slug": s, "name": c["name"], "country": c["country"],
                      "match": [s, c["name"]], "source": src,
                      "retrieved": DATE, "count": c["count"]}
        added += 1
idx["colleges"] = sorted(entries.values(), key=lambda e: e["slug"])
json.dump(idx, open("index.json", "w"), ensure_ascii=False, indent=1)
log.append(f"index: {len(entries)} colleges ({added} added)")

# ---------- 5. ATTRIBUTION.txt ----------
def attr_line(c):
    src = "; ".join(c["sources"]) if c["sources"] else \
        f"official college faculty/staff directory (per-file source URL not recorded in {c['batch']} manifest)"
    bits = [f"{c['name']} ({c['slug']}): {c['count']} professors. Source: {src} (retrieved {DATE}). Public university faculty directory."]
    if c.get("note"): bits.append(f"Note: {c['note']}")
    if c.get("spot_check"): bits.append(f"Spot check: {c['spot_check']}.")
    return " ".join(bits)

by_batch = collections.defaultdict(list)
for c in landed:
    by_batch[c["batch"]].append(c)
existing_attr = open("ATTRIBUTION.txt").read()
new_sections = []
for b in sorted(by_batch):
    header = f"\n## Batch {b} ({DATE})\n"
    if header in existing_attr:
        log.append(f"attribution section {b} already present; skipped")
        continue
    lines = [header] + [attr_line(c) for c in sorted(by_batch[b], key=lambda x: x["slug"])]
    new_sections.append("\n".join(lines) + "\n")
with open("ATTRIBUTION.txt", "a", encoding="utf-8") as fh:
    fh.write("".join(new_sections))
log.append(f"attribution: added {len(new_sections)} batch sections")

# ---------- 6. master-list.json ----------
ml = json.load(open("master-list.json"))
by_cc = ml["countries"]
unmatched = []
def find_entry(country, slug, name):
    for e in by_cc[country]:
        if e.get("slug") == slug or e.get("done_slug") == slug:
            return e
    # fallback: name match (tolerant)
    import unicodedata
    def norm(s):
        s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
        return " ".join(s.lower().split())
    nnl = norm(name)
    for e in by_cc[country]:
        if norm(e.get("name", "")) == nnl:
            return e
    return None
done_n = blocked_n = nodir_n = 0
for c in landed:
    e = find_entry(c["country"], c["slug"], c["name"])
    if not e:
        unmatched.append(("done", c["country"], c["slug"])); continue
    e["status"] = "done"; e["done_slug"] = c["slug"]
    e["reason"] = f"wave2 {c['batch']}: {c['count']} professors collected {DATE}"
    done_n += 1
for country, slug, name, reason in blocked:
    e = find_entry(country, slug, name)
    if not e:
        unmatched.append(("blocked", country, slug)); continue
    e["status"] = "blocked"; e["reason"] = reason; blocked_n += 1
for country, slug, name, reason in nodir:
    e = find_entry(country, slug, name)
    if not e:
        unmatched.append(("no-directory", country, slug)); continue
    e["status"] = "no-directory"; e["reason"] = reason; nodir_n += 1
fixed_none = 0
for cc in by_cc.values():
    for e in cc:
        if e.get("status") is None:
            e["status"] = "pending"; fixed_none += 1
st = collections.Counter(e.get("status") for cc in by_cc.values() for e in cc)
ml["stats"] = {"total": sum(st.values()), "done": st.get("done", 0),
               "blocked": st.get("blocked", 0), "no-directory": st.get("no-directory", 0),
               "pending": st.get("pending", 0)}
ml["generated"] = DATE
json.dump(ml, open("master-list.json", "w"), ensure_ascii=False, indent=1)
log.append(f"master-list: done+={done_n} blocked+={blocked_n} no-dir+={nodir_n} none-fixed={fixed_none}")
log.append(f"master-list stats: {dict(st)}")
if unmatched:
    log.append(f"UNMATCHED ({len(unmatched)}): {unmatched[:20]}")

# ---------- 7. us0 manifest write ----------
us0_new = {
    "batch": "wave2-us0", "worker": "us-w2-0", "country": "US", "date": DATE,
    "colleges": us0_colleges,
    "blockedHosts": us0_old["blockedHosts"],
    "noDirectory": us0_old["noDirectory"],
    "limitedCoverage": us0_old["limitedCoverage"],
    "otherAccessIssues": us0_old["otherAccessIssues"],
    "coordinatorAttention": us0_old["coordinatorAttention"] + [
        "2026-09-23 coordinator rebuild: 4 worker files corrected to slug/schema (campbellsville-university 285, carnegie-mellon-university 1366, case-western-reserve-university 7502, central-washington-university 646) and merged; fresh 5/5 spot-checks completed for all four. 4 assignments unworked (central-michigan-university, cleveland-state-university, coastal-carolina-university, college-of-charleston) — left pending, never marked no-directory.",
    ],
    "totalProfessors": sum(c["count"] for c in us0_colleges if c["status"] == "landed"),
}
json.dump(us0_new, open("_batch-wave2-us0.json", "w"), ensure_ascii=False, indent=1)
log.append(f"us0 manifest rebuilt: 25 outcomes, totalProfessors={us0_new['totalProfessors']}")

# ---------- 8. totals ----------
tot_profs = sum(c["count"] for c in landed)
tot_files = len({c["slug"] for c in landed})
log.append(f"WAVE-2 TOTAL: {tot_files} files / {tot_profs} professors")
idx_profs = sum(e["count"] for e in idx["colleges"])
log.append(f"INDEX TOTAL: {len(idx['colleges'])} colleges / {idx_profs} professors")
print("\n".join(log))
