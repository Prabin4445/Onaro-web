#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean

URL = ("https://cea.howard.edu/academics/departments/"
       "electrical-engineering-and-computer-science/people-eecs")
html = polite_get(URL)
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "lxml")
main = soup.find("main") or soup
lines = [clean(x) for x in main.get_text("\n", strip=True).split("\n")]
lines = [l for l in lines if l and not l.startswith("View Full Profile")]

profs, seen = [], set()
i = 0
while i < len(lines):
    # find name: line followed by title-ish line
    name = lines[i]
    j = i + 1
    if j < len(lines) and re.match(r"^(He/Him|She/Her|Him/He|Her/She|They/Them)$", lines[j], re.I):
        j += 1
    if j >= len(lines):
        break
    title = lines[j]
    # title must look like an academic title
    if not re.search(r"Professor|Lecturer|Scientist|Chair|Instructor|Fellow", title, re.I):
        i += 1
        continue
    # name sanity
    if (len(name.split()) > 6 or len(name.split()) < 2 or "@" in name
            or re.search(r"Department|University|Home|Academics|Menu|News", name, re.I)):
        i += 1
        continue
    name = re.sub(r",?\s*(Ph\.?D\.?|PhD)$", "", name).strip()
    key = name.lower()
    if key not in seen:
        seen.add(key)
        profs.append({"name": name, "title": clean(title),
                      "dept": "Electrical Engineering and Computer Science",
                      "courses": []})
    i = j + 1

print("total:", len(profs))
for p in profs[:5]:
    print(" ", p["name"], "|", p["title"])
save_json("howard-university.json",
          {"college": "Howard University", "country": "US", "professors": profs})
