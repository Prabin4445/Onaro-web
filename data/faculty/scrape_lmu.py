#!/usr/bin/env python3
"""Loyola Marymount official directory (SearchStax Solr index powering
https://www.lmu.edu/directory/) -> loyola-marymount-university.json"""
import sys, re, json, time, urllib.parse, urllib.request; sys.path.insert(0, '.')
from _scrape_lib import save_json, clean, UA

base = "https://searchcloud-1-us-west-2.searchstax.com/29847/loyolamarymount-5444/emselect"
tok = "a3b311d037b9039727ede564f39132badd9b8697"
fl = "directoryName_t,directoryPosition_ss,directoryDepartment_ss,directoryCollege_t"

def fetch(start, rows=500):
    params = {"q": "*:*", "fq": "directoryName_t:[* TO *]", "rows": rows,
              "start": start, "wt": "json", "fl": fl}
    req = urllib.request.Request(base + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": UA, "Authorization": "Token " + tok,
                 "Accept": "application/json"})
    r = urllib.request.urlopen(req, timeout=60)
    return json.loads(r.read().decode())

first = fetch(0, 1)
total = first["response"]["numFound"]
print("total directory docs:", total)
docs = []
start = 0
while start < total:
    d = fetch(start, 500)
    docs.extend(d["response"]["docs"])
    start += len(d["response"]["docs"])
    time.sleep(1.2)
print("fetched:", len(docs))

profs, seen = [], set()
for doc in docs:
    name = clean(doc.get("directoryName_t") or "")
    pos = doc.get("directoryPosition_ss") or []
    depts = doc.get("directoryDepartment_ss") or []
    college = clean(doc.get("directoryCollege_t") or "")
    if not name:
        continue
    # name format "Higgins, Charles" -> "Charles Higgins"
    if "," in name:
        last, rest = name.split(",", 1)
        name = clean(rest + " " + last)
    title = clean(pos[0]) if pos else ""
    if not re.search(r"Professor|Instructor|Lecturer", title, re.I):
        continue
    dept = clean(depts[0]) if depts else college
    key = name.lower()
    if key in seen:
        continue
    seen.add(key)
    profs.append({"name": name, "title": title, "dept": dept, "courses": []})
print("faculty:", len(profs))
save_json("loyola-marymount-university.json",
          {"college": "Loyola Marymount University", "country": "US",
           "professors": profs})
import collections
print(collections.Counter(p["dept"] for p in profs).most_common(8))
