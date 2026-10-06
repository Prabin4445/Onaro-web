#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

FAC = re.compile(r"Faculty|AD TG|ADJ Teaching|Teaching - AFO|Instructor|AD CL|"
                 r"Adjunct Clinical", re.I)
STAFF = re.compile(r"Associate\b|Assistant to|Advisor|Analyst|Coordinator|Manager|"
                   r"Specialist|Director|Secretary|Proctor|Supervisor|Dean|"
                   r"Associate I\b|Associate II\b|Librarian|Counselor", re.I)

profs, seen = [], set()
page = 0
while True:
    url = f"https://www.hfcc.edu/employee-directory?page={page}"
    html = polite_get(url)
    soup = BeautifulSoup(html, "lxml")
    tbl = soup.find("table")
    rows = tbl.find_all("tr")[1:]
    if not rows:
        break
    for r in rows:
        cells = r.find_all("td")
        if len(cells) < 2:
            continue
        name_raw = clean(cells[0].get_text(" "))
        pos = clean(cells[1].get_text(" "))
        name = clean(name_raw.split(",")[0])
        if not name or not FAC.search(pos) or STAFF.search(pos):
            continue
        # title from position
        first = pos.split(",")[0]
        if re.search(r"FT Faculty", pos, re.I):
            title = "Full-Time Faculty"
        elif re.search(r"Adjunct Faculty|AD TG|ADJ Teaching|Teaching - AFO", pos, re.I):
            title = "Adjunct Faculty"
        elif re.search(r"Instructor", pos, re.I):
            title = "Instructor"
        elif re.search(r"Adjunct Clinical|AD CL", pos, re.I):
            title = "Clinical Instructor"
        else:
            title = "Faculty"
        dept = clean(pos.split(",")[-1]) or clean(first)
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        profs.append({"name": name, "title": title, "dept": dept, "courses": []})
    print(f"page {page}: {len(rows)} rows, total faculty so far {len(profs)}")
    # next page?
    nxt = soup.find("a", href=re.compile(r"\?page=%d$" % (page + 1)))
    if nxt:
        page += 1
    else:
        break

print("total:", len(profs))
save_json("henry-ford-college.json",
          {"college": "Henry Ford College", "country": "US", "professors": profs})
