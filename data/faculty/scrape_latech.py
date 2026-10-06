#!/usr/bin/env python3
"""Louisiana Tech official directory -> louisiana-tech-university.json"""
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean

html = polite_get("https://www.latech.edu/directory/")
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "lxml")
cells = soup.find_all("div", class_=lambda c: c and "cell" in c and "mix" in c)
profs, seen = [], set()
for cell in cells:
    parts = [p for p in cell.get_text("|", strip=True).split("|") if p.strip()]
    if len(parts) < 2:
        continue
    name = clean(parts[0])
    title = clean(parts[1])
    if not re.search(r"Professor|Instructor|Lecturer", title, re.I):
        continue
    dept = ""
    cls = cell.get("class", [])
    for c in cls:
        if c.startswith("school-"):
            rest = c[len("school-"):]
            if rest.startswith("of-"):
                rest = rest[3:]
            dept = "School of " + clean(rest.replace("-", " ").title())
            break
    if not dept:
        for c in cls:
            if c in ("cell", "mix") or c.startswith("item-filter") or c.startswith("college-"):
                continue
            dept = clean(c.replace("-", " ").title())
            break
    if not dept:
        for c in cls:
            if c.startswith("college-"):
                dept = clean(c.replace("-", " ").title())
                break
    dept = dept.replace(" Of ", " of ")
    key = name.lower()
    if key in seen:
        continue
    seen.add(key)
    profs.append({"name": name, "title": title, "dept": dept, "courses": []})
print("faculty:", len(profs))
save_json("louisiana-tech-university.json",
          {"college": "Louisiana Tech University", "country": "US",
           "professors": profs})
import collections
print(collections.Counter(p["title"] for p in profs).most_common(8))
for p in profs[:4]:
    print(" ", p["name"], "|", p["title"], "|", p["dept"])
