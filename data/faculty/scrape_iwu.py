#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

html = polite_get("https://indwes.edu/academics/faculty/")
soup = BeautifulSoup(html, "lxml")
cards = soup.select("div.faculty-card-col")
print("cards:", len(cards))
profs, seen = [], set()
STEM = ["Science, Technology, Engineering and Math", "DeVoe School of Business, Technology and Leadership",
        "School of Nursing and Health Professions", "School of Integrated Health"]
for c in cards:
    inner = c.select_one("div.filterDiv")
    if not inner:
        continue
    ds = inner.get("data-search", "")
    # name link
    a = c.find("a", title=re.compile(r"View .* Profile"))
    if not a:
        continue
    name = clean(re.sub(r"^View (.*) Profile$", r"\1", a.get("title", "")))
    if not name or name.lower() in seen:
        continue
    # title + school from data-search: "Name <title> <school> <division>"
    rest = clean(ds)
    rest = re.sub(r"^" + re.escape(name) + r"\s*", "", rest)
    school = ""
    for s in STEM:
        if s in rest:
            school = s
            break
    if not school:
        m = re.search(r"(School of [A-Za-z, &]+|John Wesley Honors College|Honors College|Wesley Seminary|DeVoe [A-Za-z, &]+?)(?=\s|$)", rest)
        if m:
            school = m.group(1).strip()
            # dedupe "School of X School of X"
            if school.startswith("School of ") and school.count("School of ") > 1:
                school = "School of " + school.split("School of ")[1].split("School of ")[0].strip()
            # strip trailing division text
            school = re.sub(r"\s+Division of.*$", "", school)
            # fix doubled phrases: "School of X X" -> "School of X"
            school = re.sub(r"^(School of ([A-Za-z]+(?: [A-Za-z,&]+)*)) \2$", r"\1", school)
            school = re.sub(r"\s*-\s*On Campus$", "", school).strip()
            if school == "DeVoe Division":
                school = "DeVoe Division of Business"
    title = clean(rest[:rest.find(school)].strip()) if school else rest
    seen.add(name.lower())
    profs.append({"name": name, "title": title, "dept": school, "courses": []})

print("parsed:", len(profs))
stem = [p for p in profs if p["dept"] in STEM]
print("STEM:", len(stem))
save_json("indiana-wesleyan-university.json",
          {"college": "Indiana Wesleyan University-National & Global",
           "country": "US", "professors": profs})
for p in profs[:8]:
    print(" ", p["name"], "|", p["title"][:50], "|", p["dept"][:50])
