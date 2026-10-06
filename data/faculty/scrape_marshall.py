#!/usr/bin/env python3
"""Marshall University COS + CECS directories -> marshall-university.json"""
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

profs, seen = [], set()
def add(name, title, dept):
    name = clean(re.sub(r"\s+", " ", name))
    title = clean(re.sub(r"\s+", " ", title))
    name = re.sub(r"^(Dr|Mr|Mrs|Ms|Miss|Prof)\.\s+", "", name)
    if not name or not re.search(r"Professor|Instructor|Lecturer", title, re.I):
        return
    if "emerit" in title.lower():
        return
    key = name.lower()
    if key in seen:
        return
    seen.add(key)
    profs.append({"name": name, "title": title, "dept": dept, "courses": []})

# College of Science print page: h2/h3 section -> table
html = polite_get("https://www.marshall.edu/cos/faculty-staff/print/")
soup = BeautifulSoup(html, "lxml")
skip = ("dean", "student services", "staff")
for h in soup.find_all(["h2", "h3"]):
    sec = h.get_text(strip=True)
    if any(w in sec.lower() for w in skip):
        continue
    tbl = h.find_next("table")
    if not tbl:
        continue
    for tr in tbl.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) >= 2:
            add(tds[0].get_text(" ", strip=True), tds[1].get_text(" ", strip=True),
                sec)

# CECS: single table; dept often embedded in title after "–"
html = polite_get("https://marshall.edu/cecs/directory/cecs/")
soup = BeautifulSoup(html, "lxml")
tbl = soup.find("table")
for tr in tbl.find_all("tr")[1:]:
    tds = tr.find_all("td")
    if len(tds) < 2:
        continue
    name, title = tds[0].get_text(" ", strip=True), tds[1].get_text(" ", strip=True)
    dept = "College of Engineering and Computer Sciences"
    m = re.search(r"[–-]\s*(Department of .+)$", title)
    if m:
        dept = m.group(1).strip()
        title = title[:m.start()].strip(" –-")
    add(name, title, dept)

print("faculty:", len(profs))
save_json("marshall-university.json",
          {"college": "Marshall University", "country": "US",
           "professors": profs})
import collections
print(collections.Counter(p["dept"] for p in profs).most_common(12))
