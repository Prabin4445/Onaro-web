#!/usr/bin/env python3
"""MIT department faculty pages -> massachusetts-institute-of-technology.json"""
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

profs, seen = [], set()
def add(name, title, dept):
    name = clean(re.sub(r"\s+", " ", name))
    title = clean(re.sub(r"\s+", " ", title))
    if not name or not re.search(r"Professor|Lecturer", title, re.I):
        return
    if "emerit" in title.lower():
        return
    key = name.lower()
    if key in seen:
        return
    seen.add(key)
    profs.append({"name": name, "title": title, "dept": dept, "courses": []})

def flip(t):
    if "," in t:
        last, rest = t.split(",", 1)
        return clean(rest + " " + last)
    return t

# 1. EECS
html = polite_get("https://www.eecs.mit.edu/role/faculty/")
soup = BeautifulSoup(html, "lxml")
for div in soup.find_all("div", class_="people-entry"):
    h5 = div.find("h5")
    if not h5:
        continue
    name = h5.get_text(" ", strip=True)
    full = div.get_text(" | ", strip=True)
    rest = full.split("|", 1)[1] if "|" in full else ""
    title = rest.split("|")[0].strip()
    title = re.sub(r",?\s*\[[^\]]*\]", "", title).strip(" ,")
    add(name, title, "Department of Electrical Engineering and Computer Science")
print("eecs done")

# 2. DMSE
html = polite_get("https://dmse.mit.edu/people/faculty/")
soup = BeautifulSoup(html, "lxml")
for div in soup.find_all("div", class_="faculty-teaser"):
    a = div.find("a")
    if not a:
        continue
    parts = a.get_text("|", strip=True).split("|")
    if len(parts) >= 2:
        add(parts[0], parts[1], "Department of Materials Science and Engineering")
print("dmse done")

# 3. MechE
html = polite_get("https://meche.mit.edu/people")
soup = BeautifulSoup(html, "lxml")
for div in soup.find_all("div", class_="people-details"):
    nm = div.find("span", class_="name")
    if not nm:
        continue
    parts = div.get_text("|", strip=True).split("|")
    title = parts[1] if len(parts) > 1 else ""
    add(flip(nm.get_text(strip=True)), title, "Department of Mechanical Engineering")
print("meche done")

# 4. Math (detailed list text parse)
html = polite_get("https://math.mit.edu/directory/faculty/")
soup = BeautifulSoup(html, "lxml")
t = soup.get_text("\n", strip=True)
lines = [l.strip() for l in t.split("\n")]
i = lines.index("All Department Faculty") if "All Department Faculty" in lines else 0
name_re = re.compile(r"^[A-ZÀ-ÿ][\w.'’\-]+(?: [A-ZÀ-ÿ][\w.'’\-]+)*, [A-ZÀ-ÿ]")
office_re = re.compile(r"^\d+-\w+$")
cur_name, cur_title = None, None
def flush():
    global cur_name, cur_title
    if cur_name and cur_title:
        add(flip(cur_name), cur_title, "Department of Mathematics")
    cur_name, cur_title = None, None
for ln in lines[i:]:
    if name_re.match(ln) and len(ln) < 60:
        flush()
        cur_name = ln
    elif cur_name and office_re.match(ln):
        continue
    elif cur_name and not cur_title and re.search(r"Professor|Lecturer", ln, re.I):
        cur_title = ln
flush()
print("math done")

print("faculty:", len(profs))
save_json("massachusetts-institute-of-technology.json",
          {"college": "Massachusetts Institute of Technology", "country": "US",
           "professors": profs})
import collections
print(collections.Counter(p["dept"] for p in profs))
