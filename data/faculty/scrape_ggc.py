#!/usr/bin/env python3
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

DEPTS = {
    "Biological Sciences": "491",
    "Chemistry": "492",
    "Exercise Science and Physical Education": "501",
    "Information Technology": "507",
    "Mathematics and Statistics": "510",
    "Physics and Pre-engineering": "512",
}
TITLE_RE = re.compile(r"(Assistant Professor|Associate Professor|Professor|"
                      r"Senior Lecturer|Lecturer|Instructor|Department Chair|Chair)", re.I)

profs, seen = [], set()
sources = []
for dept, tid in DEPTS.items():
    base = (f"https://www.ggc.edu/directory?department_filter%5B%5D={tid}"
            f"&name=&department=All&school=All")
    sources.append(base)
    n = 0
    page = 0
    max_page = 0
    while True:
        url = base + (f"&page={page}" if page else "")
        html = polite_get(url)
        soup = BeautifulSoup(html, "lxml")
        main = soup.find("main") or soup
        if page == 0:
            for a in main.find_all("a", href=True):
                mm = re.search(r"[?&]page=(\d+)", a.get("href", ""))
                if mm:
                    max_page = max(max_page, int(mm.group(1)))
        for item in main.find_all("div", class_="views-view-responsive-grid__item-inner"):
            txt = clean(item.get_text(" "))
            if len(txt) < 8:
                continue
            m = TITLE_RE.search(txt)
            if not m:
                continue
            name = clean(re.sub(r"^(Dr|Ms|Mr|Mrs)\.?\s+", "", txt[:m.start()]))
            title = clean(txt[m.start():])
            if not name or len(name.split()) > 5 or "@" in name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            profs.append({"name": name, "title": title, "dept": dept, "courses": []})
            n += 1
        # next page?
        if page < max_page:
            page += 1
        else:
            break
    print(f"{dept}: {n}")

print("total:", len(profs))
save_json("georgia-gwinnett-college.json",
          {"college": "Georgia Gwinnett College", "country": "US", "professors": profs})
