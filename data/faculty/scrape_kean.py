#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

TITLE_RE = re.compile(r"Professor|Lecturer|Instructor", re.I)
UNIT_RE = re.compile(r"^(The )?(Department|School|Division|College|Center|Program) of\b|^Michael Graves College|^Nathan Weiss|^The Dorothy|^New Jersey Center|^Kean Ocean", re.I)

def clean_name(n):
    n = clean(n)
    n = re.sub(r",\s*(Ph\.?D\.?|Ed\.?D\.?|M\.?S\.?|M\.?A\.?|M\.?F\.?A\.?|M\.?B\.?A\.?|J\.?D\.?|D\.?N\.?P\.?|Psy\.?D\.?|D\.?P\.?T\.?|NCIDQ|LEED GA|C\.?G\.?C\.?|CCC-SLP|PA-C|MS-PA-C|A\.?R\.?N\.?P\.?|C\.?N\.?E\.?|R\.?N\.?)\.?$", "", n).strip().rstrip(",")
    return n

profs, seen = [], set()
for page in range(18):
    html = polite_get(f"https://www.kean.edu/directory?page={page}")
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup.find("body")
    n = 0
    for h in main.find_all("h3"):
        name = clean_name(h.get_text(" ", strip=True))
        if not name or name.lower() in seen:
            continue
        d = h.find_next_sibling("div")
        if not d:
            continue
        lines = [clean(x) for x in d.get_text("\n", strip=True).split("\n") if clean(x)]
        units = [l for l in lines if UNIT_RE.match(l)]
        titles = [l for l in lines if TITLE_RE.search(l)]
        if not titles:
            continue  # staff, not faculty
        dept = ""
        for l in units:
            if re.match(r"^Department of\b", l, re.I):
                dept = l
                break
        if not dept:
            for l in reversed(units):
                if re.match(r"^(The )?(School|Division) of\b", l, re.I):
                    dept = l
                    break
        if not dept and units:
            dept = units[0]
        if not dept:
            # fallback: first line that is not the title and not contact info
            for l in lines:
                if l not in titles and l.lower() not in ("email", "phone", "office location"):
                    dept = l
                    break
        title = titles[0] if titles else ""
        seen.add(name.lower())
        profs.append({"name": name, "title": title, "dept": dept, "courses": []})
        n += 1
    print(f"page {page}: {n}")

print("total:", len(profs))
save_json("kean-university.json",
          {"college": "Kean University", "country": "US", "professors": profs})
