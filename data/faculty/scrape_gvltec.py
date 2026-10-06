#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean

html = polite_get("http://catalog.gvltec.edu/faculty/")
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "lxml")
main = soup.find("main") or soup

DEG = re.compile(r"^(BS|MS|BA|MA|MLA|MAcc|MAT|MEd|M\.?S\.?|B\.?S\.?|A\.?S\.?|B\.?A\.?|"
                 r"M\.?A\.?|AS|AA|AAS|ADN|BSN|MSN|Ph\.?D|Ed\.?D|EdS|MBA|MFA|JD|"
                 r"DDS|DMD|DNP|Graduate Certificate|Advanced Level|"
                 r"Certified|Registered|Licensed|Diploma|Professional Engineer)\b", re.I)

profs, seen = [], set()
for p in main.find_all("p"):
    strong = p.find("strong")
    if not strong:
        continue
    parts = [clean(s) for s in p.stripped_strings]
    head = parts[0]
    m = re.match(r"^(.+?),\s*(Professor|Associate Professor|Assistant Professor|"
                 r"Instructor|Lecturer|Senior Lecturer|Adjunct .+)$", head, re.I)
    if not m:
        continue
    name, title = clean(m.group(1)), clean(m.group(2))
    dept_lines = []
    for s in parts[1:]:
        if not s:
            continue
        if DEG.match(s):
            break
        dept_lines.append(s)
    dept = clean("; ".join(dept_lines))
    key = name.lower()
    if key in seen or not dept:
        continue
    seen.add(key)
    profs.append({"name": name, "title": title, "dept": dept, "courses": []})

print("total:", len(profs))
save_json("greenville-technical-college.json",
          {"college": "Greenville Technical College", "country": "US",
           "professors": profs})
