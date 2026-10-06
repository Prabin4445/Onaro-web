#!/usr/bin/env python3
import sys, re, json; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean

d = json.loads(polite_get("https://eapps.laredo.edu/webdirectory/retrievestaff"))
data = d["data"]
profs, seen = [], set()
for x in data:
    pos = clean(x.get("position") or "")
    if not re.search(r"Professor|Instructor|Lecturer", pos, re.I):
        continue
    name = clean((x.get("fname") or "") + " " + (x.get("lname") or ""))
    if not name.strip() or name.lower() in seen:
        continue
    seen.add(name.lower())
    profs.append({"name": name, "title": pos,
                  "dept": clean(x.get("department_name") or ""), "courses": []})
print("faculty:", len(profs))
save_json("laredo-college.json",
          {"college": "Laredo College", "country": "US", "professors": profs})
for p in profs[:5]:
    print(" ", p["name"], "|", p["title"][:45], "|", p["dept"][:40])
