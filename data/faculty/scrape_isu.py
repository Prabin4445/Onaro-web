#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

def parse_listing(url, dept):
    html = polite_get(url)
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup
    lines = main.get_text("\n", strip=True).split("\n")
    out = []
    for i, l in enumerate(lines):
        if re.match(r"^(Dr\.?\s+)?[A-Z][a-zA-Z'\-\.]+ [A-Z][a-zA-Z.'\- ]+(, Ph\.?D\.?)?$", l) \
           and i + 1 < len(lines):
            nxt = lines[i + 1]
            if re.search(r"Professor|Lecturer|Instructor|Chair", nxt, re.I) \
               and not re.search(r"Emeritus", nxt, re.I):
                name = clean(re.sub(r"^Dr\.?\s+", "", l))
                name = clean(re.sub(r",?\s*Ph\.?D\.?$", "", name))
                out.append((name, clean(nxt)))
    return dept, out

PAGES = [
    ("https://www.isu.edu/cs/people/faculty/staffdirectoryentries/", "Computer Science"),
    ("https://www.isu.edu/ece/people/faculty/staffdirectoryentries/",
     "Electrical and Computer Engineering"),
    ("https://www.isu.edu/math/people/tenure/", "Mathematics and Statistics"),
    ("https://www.isu.edu/math/people/faculty---non-tenure-track/",
     "Mathematics and Statistics"),
    ("https://www.isu.edu/math/people/faculty---adjunct-instructors/",
     "Mathematics and Statistics"),
]

profs, seen = [], set()
for url, dept in PAGES:
    dept, rows = parse_listing(url, dept)
    n = 0
    for name, title in rows:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        profs.append({"name": name, "title": title, "dept": dept, "courses": []})
        n += 1
    print(f"{dept}: {n}")

# Biology (tab section, names only)
html = polite_get("https://www.isu.edu/biology/people/faculty/")
soup = BeautifulSoup(html, "lxml")
main = soup.find("main") or soup
txt = main.get_text("\n", strip=True)
a = txt.find("\nProfessors\n"); b = txt.find("\nEmeritus\n")
for m in re.finditer(r"^([A-Z][a-zA-Z.\- ]+, Ph\.D\.)$", txt[a:b], re.M):
    name = clean(m.group(1).replace(", Ph.D.", ""))
    if name.lower() not in seen:
        seen.add(name.lower())
        profs.append({"name": name, "title": "Professor",
                      "dept": "Biological Sciences", "courses": []})
print("Biology: done")

# Physics (Name, Title blocks; skip staff & external affiliates)
html = polite_get("https://www.isu.edu/physics/people/faculty-and-staff/")
soup = BeautifulSoup(html, "lxml")
main = soup.find("main") or soup
lines = main.get_text("\n", strip=True).split("\n")
stop = lines.index("Affiliate/Adjunct/Visiting") if "Affiliate/Adjunct/Visiting" in lines else len(lines)
n = 0
for i, l in enumerate(lines[:stop]):
    m = re.match(r"^([A-Za-z\-']+),\s+([A-Za-z.\- '()]+?)(?:,?\s+(Ph\.?D\.?|M\.?S\.?|PhD))?$", l)
    if m and i + 1 < len(lines):
        nxt = lines[i + 1]
        if re.search(r"Professor|Lecturer", nxt, re.I):
            name = clean(m.group(2).replace("(", "").replace(")", "") + " " + m.group(1))
            if name.lower() not in seen:
                seen.add(name.lower())
                profs.append({"name": name, "title": clean(nxt),
                              "dept": "Physics", "courses": []})
                n += 1
print(f"Physics: {n}")

print("total:", len(profs))
save_json("idaho-state-university.json",
          {"college": "Idaho State University", "country": "US", "professors": profs})
