#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

PAGES = [
    ("https://www.lamar.edu/engineering/industrial/faculty/index.html",
     "Industrial and Systems Engineering"),
    ("https://www.lamar.edu/engineering/chemical/faculty/index.html",
     "Chemical and Biomolecular Engineering"),
    ("https://www.lamar.edu/engineering/civil/faculty/index.html",
     "Civil and Environmental Engineering"),
    ("https://www.lamar.edu/engineering/electrical/faculty-and-staff/index.html",
     "Electrical and Computer Engineering"),
    ("https://www.lamar.edu/engineering/mechanical/faculty-staff/index.html",
     "Mechanical Engineering"),
    ("https://www.lamar.edu/arts-sciences/computer-science/faculty-staff/index.html",
     "Computer Science"),
    ("https://www.lamar.edu/arts-sciences/mathematics/faculty/index.html",
     "Mathematics"),
    ("https://www.lamar.edu/arts-sciences/physics/faculty-staff/index.html",
     "Physics"),
    ("https://www.lamar.edu/arts-sciences/biology/faculty-staff/index.html",
     "Biology"),
    ("https://www.lamar.edu/arts-sciences/chemistry-and-biochemistry/faculty-and-staff/index.html",
     "Chemistry and Biochemistry"),
]

NAME_RE = re.compile(r"^(Mr\.|Ms\.|Mrs\.|Dr\.)?\s*[A-Z][a-zA-Z'\-\.]+ [A-Z][a-zA-Z.'\- ]*(,?\s*(Ph\.?D\.?|P\.?E\.?|C\.?P\.?E\.?))*\.?$")
TITLE_RE = re.compile(r"Professor|Lecturer|Instructor|Chair|Coordinator", re.I)
STAFF_WORDS = re.compile(r"Administrative|Assistant to|Secretary|Technician|Specialist$", re.I)

profs, seen = [], set()
for url, dept in PAGES:
    html = polite_get(url)
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup.find("body")
    lines = main.get_text("\n", strip=True).split("\n")
    n = 0
    i = 0
    while i < len(lines):
        l = clean(lines[i])
        if NAME_RE.match(l) and not TITLE_RE.search(l) and i + 1 < len(lines):
            nxt = clean(lines[i + 1])
            if nxt.lower().rstrip(":") == "position" and i + 2 < len(lines):
                nxt = clean(lines[i + 2])
            if re.match(r"^(Associate|Assistant|Clinical|Visiting|Adjunct)$", nxt, re.I) and i + 2 < len(lines):
                nxt = nxt + " " + clean(lines[i + 2])
            if TITLE_RE.search(nxt) and not re.search(r"Emeritus", nxt, re.I):
                name = clean(re.sub(r"^(Mr\.|Ms\.|Mrs\.|Dr\.)\s+", "", l))
                prev = None
                while prev != name:
                    prev = name
                    name = clean(re.sub(r",?\s*(Ph\.?D\.?|P\.?E\.?|C\.?P\.?E\.?|D\.?E\.?)\.?$", "", name))
                title = clean(nxt.split("Research:")[0])
                if name.lower() not in seen and not STAFF_WORDS.search(title):
                    seen.add(name.lower())
                    profs.append({"name": name, "title": title, "dept": dept, "courses": []})
                    n += 1
        i += 1
    print(f"{dept}: {n}")

print("total:", len(profs))
save_json("lamar-university.json",
          {"college": "Lamar University", "country": "US", "professors": profs})
