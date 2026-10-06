#!/usr/bin/env python3
"""Loyola University Chicago STEM dept directories -> loyola-university-chicago.json"""
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

def is_name(t):
    if not t or len(t) > 60:
        return False
    tl = t.lower()
    if any(w in tl for w in ("view", "faculty", "staff", "search", "directory", "category")):
        return False
    return bool(re.match(r"^[A-Za-zÀ-ÿ.'\-() ]+,?\s+[A-Za-zÀ-ÿ.'\-() ]+$", t))

def flip(t):
    if "," in t:
        last, rest = t.split(",", 1)
        return clean(rest + " " + last)
    return t

profs, seen = [], set()
def add(name, title, dept):
    name, title = clean(name), clean(title)
    if not name or not re.search(r"Professor|Instructor|Lecturer", title, re.I):
        return
    if "emerit" in title.lower():
        return
    key = name.lower()
    if key in seen:
        return
    seen.add(key)
    profs.append({"name": name, "title": title, "dept": dept, "courses": []})

def scrape_h4(url, dept, name_flip=True):
    html = polite_get(url)
    soup = BeautifulSoup(html, "lxml")
    for h in soup.find_all("h4"):
        t = h.get_text(strip=True)
        if not is_name(t):
            continue
        p = h.find_next_sibling("p")
        title = p.get_text(strip=True) if p else ""
        add(flip(t) if name_flip else t, title, dept)

# Biology: table under Faculty section
html = polite_get("https://www.luc.edu/biology/aboutus/facultystaffdirectory/")
soup = BeautifulSoup(html, "lxml")
tbl = soup.find("table")
for tr in tbl.find_all("tr")[1:]:
    tds = tr.find_all("td")
    if len(tds) >= 2:
        name = tds[0].get_text(strip=True)
        title = tds[1].get_text(" ", strip=True)
        if is_name(name):
            add(flip(name), title, "Department of Biology")

scrape_h4("https://www.luc.edu/chemistry/facultystaff/index.shtml",
          "Department of Chemistry and Biochemistry")
scrape_h4("https://www.luc.edu/physics/faculty.shtml", "Department of Physics",
          name_flip=False)  # uses li instead; handled below

# Physics: li "Name, Title"
html = polite_get("https://www.luc.edu/physics/faculty.shtml")
soup = BeautifulSoup(html, "lxml")
for li in soup.find_all("li"):
    t = li.get_text(" ", strip=True)
    m = re.match(r"^([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+)+),\s*(.+)$", t)
    if m and re.search(r"Professor|Instructor|Lecturer", m.group(2), re.I):
        add(m.group(1), m.group(2), "Department of Physics")

scrape_h4("https://www.luc.edu/math/facstaff.shtml",
          "Department of Mathematics and Statistics")
scrape_h4("https://www.luc.edu/cs/aboutus/people/", "Department of Computer Science",
          name_flip=False)
scrape_h4("https://www.luc.edu/psychology/people/facultyandstaffdirectory/",
          "Department of Psychology", name_flip=False)

print("faculty:", len(profs))
save_json("loyola-university-chicago.json",
          {"college": "Loyola University Chicago", "country": "US",
           "professors": profs})
import collections
print(collections.Counter(p["dept"] for p in profs))
