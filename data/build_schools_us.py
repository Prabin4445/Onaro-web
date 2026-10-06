#!/usr/bin/env python3
"""
Build ~/workspace/hub/data/schools_us.json — the official-data USA K-12 school
directory for the Onaro static app.

Inputs (official NCES sources only):
  1. CCD 2024-25 Public Elementary/Secondary School Universe
     https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip
  2. NCES EDGE 2023-24 public-school geocodes (join by NCES school ID)
     https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2324.zip
  3. NCES Private School Universe Survey (PSS) 2023-24 public-use file
     https://nces.ed.gov/surveys/pss/zip/pss2324_pu_csv.zip

Inclusion rules:
  - Public schools: SY_STATUS_TEXT in {Open, New, Reopened, Future, Added,
    "Changed Boundary/Agency"}. Closed and Inactive are EXCLUDED (not operating).
    All levels (elementary, middle, high, pre-K, other, secondary, ungraded, ...).
    All 50 states + DC + outlying areas (PR, GU, VI, MP, AS).
  - Private schools: all responding eligible schools in the PSS 2023-24
    public-use file (that file only contains active schools).
  - Coordinates are NEVER invented: public schools missing from the 2023-24
    EDGE file (e.g. new 2024-25 schools) get lat=null, lng=null.
  - Exact duplicates on (normalized name, city, state) are collapsed once.

Output: data/schools_us.json, same shape as data/colleges.json:
  {"source": "...", "fields": ["name","country","city","lat","lng"],
   "records": [[name, "United States", "City, ST", lat, lng], ...]}
sorted by name (deterministic).
"""
import csv
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))   # ~/workspace/hub/data
HUB = os.path.dirname(BASE)
DATA = os.path.expanduser("~/workspace/school-data")

CCD_CSV = "/tmp/ccd_sch_2425/ccd_sch_029_2425_w_1a_073025.csv"
EDGE_TXT = os.path.join(DATA, "edge2324/EDGE_GEOCODE_PUBLICSCH_2324/EDGE_GEOCODE_PUBLICSCH_2324.TXT")
PSS_CSV = os.path.join(DATA, "pss2324/pss2324_pu.csv")
OUT = os.path.join(BASE, "schools_us.json")

INCLUDE_STATUS = {"Open", "New", "Reopened", "Future", "Added", "Changed Boundary/Agency"}
EXCLUDE_STATUS = {"Closed", "Inactive"}


def norm_name(s):
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def dedupe_key(name, city, state):
    key = (norm_name(name) + "|" + norm_name(city) + "|" + (state or "").strip()).lower()
    key = re.sub(r"[^\w| ]", "", key)
    key = re.sub(r"\s+", " ", key)
    return key


def titlecase(s):
    # PSS is ALL CAPS; CCD is already mixed case. title() on mixed case is a no-op
    # for normal words; apply only when the string is predominantly uppercase.
    s = norm_name(s)
    if s and sum(1 for c in s if c.isupper()) > sum(1 for c in s if c.islower()):
        return s.title()
    return s


def load_edge_geocodes(path):
    """Map NCES school ID -> (lat, lon). EDGE TXT is pipe-delimited, no header.
    col1 = NCESSCH, col13 = LAT, col14 = LON."""
    geo = {}
    n = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("|")
            if len(parts) < 14:
                continue
            ncesid = parts[0].strip()
            try:
                lat = float(parts[12]); lon = float(parts[13])
            except ValueError:
                continue
            if ncesid and lat != 0 and lon != 0:
                geo[ncesid] = (lat, lon)
            n += 1
    print(f"EDGE rows read: {n}, usable geocodes: {len(geo)}")
    return geo


def main():
    geo = load_edge_geocodes(EDGE_TXT)

    records = []          # [name, country, "City, ST", lat, lng]
    seen = set()
    stats = {
        "ccd_total": 0, "ccd_included": 0, "ccd_excluded": 0,
        "ccd_geocoded": 0, "ccd_ungeocoded": 0,
        "pss_total": 0, "pss_included": 0,
        "dedup_dropped": 0,
        "states_public": set(), "states_private": set(),
    }

    # ---- 1. Public schools (CCD 2024-25) ----
    with open(CCD_CSV, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        hdr = next(r)
        NCESSCH = hdr.index("NCESSCH"); SCH_NAME = hdr.index("SCH_NAME")
        LCITY = hdr.index("LCITY"); LSTATE = hdr.index("LSTATE")
        STATUS = hdr.index("SY_STATUS_TEXT")
        for row in r:
            stats["ccd_total"] += 1
            status = (row[STATUS] or "").strip()
            if status not in INCLUDE_STATUS:
                stats["ccd_excluded"] += 1
                continue
            name = norm_name(row[SCH_NAME])
            city = titlecase(row[LCITY])
            state = (row[LSTATE] or "").strip().upper()
            if not name or not city or not state:
                stats["ccd_excluded"] += 1
                continue
            key = dedupe_key(name, city, state)
            if key in seen:
                stats["dedup_dropped"] += 1
                continue
            seen.add(key)
            lat = lng = None
            g = geo.get((row[NCESSCH] or "").strip())
            if g:
                lat, lng = g
                stats["ccd_geocoded"] += 1
            else:
                stats["ccd_ungeocoded"] += 1
            records.append([name, "United States", f"{city}, {state}", lat, lng])
            stats["ccd_included"] += 1
            stats["states_public"].add(state)

    # ---- 2. Private schools (PSS 2023-24) ----
    with open(PSS_CSV, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        hdr = next(r)
        PINST = hdr.index("PINST"); PCITY = hdr.index("PCITY")
        PSTABB = hdr.index("PSTABB"); LAT = hdr.index("LATITUDE24")
        LON = hdr.index("LONGITUDE24")
        for row in r:
            stats["pss_total"] += 1
            name = titlecase(row[PINST])
            city = titlecase(row[PCITY])
            state = (row[PSTABB] or "").strip().upper()
            if not name or not city or not state:
                continue
            key = dedupe_key(name, city, state)
            if key in seen:
                stats["dedup_dropped"] += 1
                continue
            seen.add(key)
            lat = lng = None
            try:
                lat = float(row[LAT]); lng = float(row[LON])
            except (ValueError, TypeError):
                lat = lng = None
            records.append([name, "United States", f"{city}, {state}", lat, lng])
            stats["pss_included"] += 1
            stats["states_private"].add(state)

    records.sort(key=lambda r: (r[0].lower(), r[2].lower()))

    source = (
        "USA K-12 schools, official NCES data. Public: NCES Common Core of Data (CCD) "
        "Public Elementary/Secondary School Universe 2024-25 "
        "(https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip), "
        "statuses included: Open, New, Reopened, Future, Added, Changed Boundary/Agency "
        "(Closed and Inactive excluded; not operating). Public coordinates: NCES EDGE "
        "2023-24 geocodes (https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2324.zip) "
        "joined by NCES school ID; schools with no match keep null coordinates (never invented). "
        "Private: NCES Private School Universe Survey (PSS) 2023-24 public-use file "
        "(https://nces.ed.gov/surveys/pss/zip/pss2324_pu_csv.zip; includes own lat/lon). "
        "50 states + DC + outlying areas (PR, GU, VI, MP, AS)."
    )
    payload = {
        "source": source,
        "fields": ["name", "country", "city", "lat", "lng"],
        "records": records,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    # ---- 3. Transparency: overlap with colleges.json ----
    colleges_path = os.path.join(BASE, "colleges.json")
    overlap = 0
    if os.path.exists(colleges_path):
        with open(colleges_path, encoding="utf-8") as f:
            colleges = json.load(f)["records"]
        college_names = set(norm_name(c[0]).lower() for c in colleges)
        for rec in records:
            if norm_name(rec[0]).lower() in college_names:
                overlap += 1

    print("=" * 60)
    print(f"CCD total rows:        {stats['ccd_total']}")
    print(f"CCD included (public): {stats['ccd_included']}")
    print(f"CCD excluded (closed/inactive/bad): {stats['ccd_excluded']}")
    print(f"CCD geocoded:          {stats['ccd_geocoded']}")
    print(f"CCD ungeocoded (null): {stats['ccd_ungeocoded']}")
    print(f"PSS total rows:        {stats['pss_total']}")
    print(f"PSS included (private):{stats['pss_included']}")
    print(f"Duplicates dropped:    {stats['dedup_dropped']}")
    print(f"TOTAL records written: {len(records)}")
    pub = sorted(stats["states_public"]); priv = sorted(stats["states_private"])
    print(f"Public state codes ({len(pub)}): {','.join(pub)}")
    print(f"Private state codes ({len(priv)}): {','.join(priv)}")
    need = [s for s in
            ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","PR","GU","VI","MP","AS"]
            if s not in pub]
    print(f"Missing from public (50+DC+5 outlying): {need or 'NONE'}")
    print(f"School names also present in colleges.json: {overlap}")
    print(f"Wrote {OUT} ({os.path.getsize(OUT)} bytes)")

    # validate
    with open(OUT, encoding="utf-8") as f:
        v = json.load(f)
    assert v["fields"] == ["name", "country", "city", "lat", "lng"]
    assert len(v["records"]) == len(records)
    assert all(r[1] == "United States" and ", " in r[2] for r in v["records"])
    print("JSON validates OK")


if __name__ == "__main__":
    main()
