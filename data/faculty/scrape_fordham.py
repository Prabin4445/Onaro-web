#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

BASE = "https://www.fordham.edu"
TITLE_RE = re.compile(
    r"(University Professor|Bepler Chair[^.;]*|Associate Professor|Assistant Professor|"
    r"Distinguished Professor|Teaching Professor|Clinical Professor|"
    r"Visiting Assistant Professor|Visiting Associate Professor|Visiting Professor|"
    r"Senior Lecturer|Lecturer|Professor|Instructor)", re.I)
TITLE_WORDS = ("professor", "lecturer", "instructor")

profs, seen = [], set()
def add(name, title, dept):
    name = clean(name).replace("Dr. ", "").replace("Dr.", "").strip(" ,")
    if not name or "@" in name or len(name) < 4:
        return
    if not re.match(r"^[A-ZÀ-Þ]", name):
        return
    if len(name.split()) > 6:
        return
    key = name.lower()
    if key in seen:
        return
    seen.add(key)
    profs.append({"name": name, "title": clean(title), "dept": dept, "courses": []})

def first_link_name(block):
    for a in block.find_all("a", href=True):
        t = clean(a.get_text(" "))
        if t and "@" not in t and len(t) >= 4 and re.match(r"^[A-ZÀ-Þ]", t) and len(t.split()) <= 5 \
           and not t.lower().startswith(("view ", "visit ", "explore", "more ")):
            return t
    return None

def parse_p_sections(dept, url, section_names):
    html = polite_get(BASE + url)
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup
    for h in main.find_all("h2"):
        sec = h.get_text(" ", strip=True).lower()
        if not any(s in sec for s in section_names):
            continue
        n = h
        while True:
            n = n.find_next_sibling()
            if n is None or n.name in ("h1", "h2"):
                break
            if n.name not in ("p", "div"):
                continue
            txt = clean(n.get_text(" "))
            if len(txt) < 12 or "postdoc" in txt.lower()[:80]:
                continue
            name = first_link_name(n)
            if not name:
                continue
            m = TITLE_RE.search(txt)
            title = m.group(1) if m else ""
            add(name, title, dept)

# --- CIS / Math / Psychology (p-block layout) ---
parse_p_sections("Computer and Information Science",
                 "/academics/departments/computer-and-information-science/faculty-and-administration/",
                 ("tenure-line faculty", "lecturers"))
parse_p_sections("Mathematics", "/academics/departments/mathematics/faculty/",
                 ("current faculty",))
parse_p_sections("Psychology", "/academics/departments/psychology/faculty-and-staff/",
                 ("faculty",))

# --- Biology: "Dr. Name - research; Title; degrees" ---
html = polite_get(BASE + "/academics/departments/biological-sciences/faculty-and-instructional-staff/")
txt = clean(BeautifulSoup(html, "lxml").get_text(" "))
bio_re = re.compile(r"Dr\.\s+([A-Za-zÀ-Þ.'\- ]+?)\s*[-–]\s*([^;]+?);\s*"
                    r"(Associate Professor|Assistant Professor|Professor|Senior Lecturer|Lecturer|Instructor)")
for m in bio_re.finditer(txt):
    name = m.group(1).strip(" -")
    if len(name.split()) <= 5:
        add(name, m.group(3), "Biological Sciences")

# --- Chemistry: "Name, Ph.D." lines, optional ", Role" next line ---
html = polite_get(BASE + "/academics/departments/chemistry-and-biochemistry/faculty/")
lines = [clean(x) for x in BeautifulSoup(html, "lxml").find("main").get_text("\n").split("\n")]
chem_re = re.compile(r"^([A-Z][A-Za-zÀ-Þ.'\- ]+?),\s*Ph\.?D\.?$")
i = 0
while i < len(lines):
    m = chem_re.match(lines[i])
    if m and len(m.group(1).split()) <= 4:
        role = ""
        if i + 1 < len(lines) and lines[i + 1].startswith(","):
            role = lines[i + 1].lstrip(", ")
        add(m.group(1), role, "Chemistry")
    i += 1

# --- Physics: from "Department Chair" onward, "Dr. Name" then title line ---
html = polite_get(BASE + "/academics/departments/physics-and-applied-physics/faculty-and-staff/")
txt = BeautifulSoup(html, "lxml").find("main").get_text("\n")
start = txt.find("Department Chair")
chunks = re.split(r"\bDr\.\s+", txt[start:])
for ch in chunks[1:]:
    lns = [clean(x) for x in ch.split("\n") if clean(x)]
    if not lns:
        continue
    name = lns[0]
    if len(name.split()) > 5 or "@" in name:
        continue
    title = ""
    for ln in lns[1:4]:
        lw = ln.lower()
        if any(w in lw for w in TITLE_WORDS) and len(ln) < 60:
            title = ln
            break
        if ln.startswith("Ph.D") or "@" in ln:
            break
    add(name, title, "Physics and Engineering Physics")

print("total:", len(profs))
for p in profs[:5]:
    print(p)
save_json("fordham-university.json",
          {"college": "Fordham University", "country": "US", "professors": profs})
