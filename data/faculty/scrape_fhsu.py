#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

BASE = "https://www.fhsu.edu"
DEPTS = {
    "Computer Science and Informatics": "informatics",
    "Mathematics": "math",
    "Physics": "physics",
    "Chemistry": "chemistry",
    "Biology": "biology",
}
TITLE_RE = re.compile(r"(Assistant Professor|Associate Professor|Professor|"
                      r"Senior Lecturer|Lecturer|Instructor|Dean|Department Chair|Chair)", re.I)
DEG_RE = re.compile(r",\s*(Ph\.?D\.?|J\.?D\.?|Ed\.?D\.?|D\.?B\.?A\.?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?|CCAI)\b.*$", re.I)
SKIP_TITLE = re.compile(r"administrative|secretary|technician|coordinator$", re.I)

def looks_like_name(line):
    core = DEG_RE.sub("", line)
    if not re.match(r"^[A-ZÀ-Þ]", core):
        return False
    if any(c in core for c in (":", "@")):
        return False
    if "(" in core and ")" in core and "Ph" not in core:
        return False
    words = core.split()
    if not (1 <= len(words) <= 5):
        return False
    if any(w in line for w in ["Faculty & Staff", "Department Staff"]):
        return False
    return True

def strip_name(line):
    line = re.sub(r"^(Dr|Ms|Mr|Mrs)\.?\s+", "", line)
    line = DEG_RE.sub("", line)
    return clean(line)

profs, seen = [], set()
sources = []
for dept, slug in DEPTS.items():
    url = f"{BASE}/{slug}/faculty-and-staff/"
    sources.append(url)
    html = polite_get(url)
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup.find("body")
    lines = [clean(x) for x in main.get_text("\n").split("\n")]
    lines = [l for l in lines if l]
    dept_count = 0
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        nxt = lines[i + 1]
        if looks_like_name(line) and not TITLE_RE.search(line) \
           and TITLE_RE.search(nxt) and not SKIP_TITLE.search(nxt) and len(nxt) < 90:
            name = strip_name(line)
            tm = TITLE_RE.search(nxt)
            title = tm.group(1)
            # extend title with " of X" phrase if present
            rest = nxt[tm.end():]
            m2 = re.match(r"\s+of\s+[A-Za-z &]+", rest)
            if m2:
                title += " " + m2.group(0).strip()
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                profs.append({"name": name, "title": clean(title), "dept": dept, "courses": []})
                dept_count += 1
        i += 1
    print(f"{dept}: {dept_count}")

print("total:", len(profs))
save_json("fort-hays-state-university.json",
          {"college": "Fort Hays State University", "country": "US", "professors": profs})
