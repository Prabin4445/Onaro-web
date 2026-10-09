"""Wave 36: Louisburg College (Louisburg, NC, private 2-yr) — 7 plans from 2026-2027 catalog.
Source: https://www.louisburg.edu/academics/college-catalog/2026-27_Louisburg_College_Catalog.pdf
Credit ranges resolved at minimums with disclosure. Verified prereqs from course descriptions:
ACC 121 <- ACC 120; BIO 112 <- BIO 111 (C); BIO 169 <- BIO 168 (C); CHM 152 <- CHM 151 (C).
AS Environmental Science BLOCKED (Y2 Fall lists 14 cr, prints TOTAL 17; catalog's own min-60hr rule broken).
"""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
INST = {"name": "Louisburg College", "city": "Louisburg", "state": "NC", "kind": "private"}
SRC = "https://www.louisburg.edu/academics/college-catalog/2026-27_Louisburg_College_Catalog.pdf"

def c(code, title, credits, category="gened", choice=False, options=None, choice_note="", prereq=None):
    return {"code": code, "title": title, "credits": credits, "category": category,
            "choice": choice, "options": options or [], "choice_note": choice_note,
            "prereq": prereq or []}

def sem(n, label, courses):
    return {"n": n, "label": label, "courses": courses}

def choice_slot(code, title, credits, opts, note, category="gened"):
    return c(code, title, credits, category, True,
             [{"code": o[0], "credits": o[1], "title": o[2]} for o in opts], note)

PSY_SOC = [("PSY 150",3,"Introduction to Psychology"),("SOC 210",3,"Introduction to Sociology")]
HIS4 = [("HIS 111",3,"World Civilization I"),("HIS 112",3,"World Civilization II"),
        ("HIS 131",3,"American History to 1865"),("HIS 132",3,"American History since 1865")]
REL4 = [("REL 110",3,"World Religions"),("REL 211",3,"Old Testament"),
        ("REL 212",3,"New Testament"),("REL 221",3,"Religion in America Today")]
ENG_LIT6 = [("ENG 231",3,"American Literature I"),("ENG 232",3,"American Literature II"),
            ("ENG 241",3,"British Literature I"),("ENG 242",3,"British Literature II"),
            ("ART 111",3,"Art Appreciation"),("MUS 110",3,"Music Appreciation")]
CIS2 = [("CIS 110",3,"Introduction to Computers"),("CIS 115",3,"Introduction to Programming")]
PED2 = [("PED 110",2,"Fitness/Wellness for Life"),("HEA 110",3,"Personal Health/Wellness")]
ENG231_232 = [("ENG 231",3,"American Literature I"),("ENG 232",3,"American Literature II")]

BASE = ("Official Louisburg College 2026-2027 Catalog, Degree Plans (pp. 81-89), "
        "'Degree Plans show a possible arrangement of courses over a typical four-semester span. "
        "There is no requirement to take courses in this order.' "
        "Genuine catalog credit ranges resolved at MINIMUM credits with this disclosure. "
        "No TCCNS in NC; no equivalencies invented.")

def plan(pid, major, degree, notes, semesters):
    total = sum(x["credits"] for s in semesters for x in s["courses"])
    p = {"institution": INST,
         "plan": {"id": pid, "major": major, "degree": degree,
                  "catalog_year": "2026-2027", "notes": notes,
                  "semesters": semesters, "source_url": SRC,
                  "total_credits": total, "external_prereqs": [], "transfer_confidence": ""}}
    with open(os.path.join(OUT, pid + ".json"), "w") as f:
        json.dump(p, f)
    print(pid, "total =", total)

# 1. AA General College
plan("louisburg-college-aa-general-college", "General College", "AA", BASE + " 60-shc minimum + 2.0 GPA per catalog.",
 [sem(1,"Year 1 - Fall",[
   c("ENG 111","Writing and Inquiry",3),
   choice_slot("HUMFA-A","Humanities/Fine Arts Requirement",3,
               [("ART 111",3,"Art Appreciation"),("MUS 110",3,"Music Appreciation")],"ART 111 or MUS 110 (3 cr) - one slot"),
   choice_slot("MATHRQ-A","Mathematics Requirement",3,
               [("MAT 143",3,"Quantitative Literacy")],"MAT 143 or higher math (3/4 cr); modeled at 3 cr minimum with this disclosure"),
   c("ACA 122","College Transfer Success (if necessary)",1),
   choice_slot("SOCBEH-A","Social/Behavioral Science Requirement",3,PSY_SOC,"PSY 150 or SOC 210 (3 cr) - one slot"),
   choice_slot("PEDREQ-A","Fitness/Wellness Requirement",2,PED2,"PED 110 (2 cr) or HEA 110 (3 cr); modeled at 2 cr minimum with this disclosure")]),
  sem(2,"Year 1 - Spring",[
   c("ENG 112","Writing and Research in the Disciplines",3,prereq=[]),
   c("SCILAB-A","Lab Science",4,category="major"),
   choice_slot("ARTDRA-A","Art/Drama/Music Elective",3,
               [("ART 111",3,"Art Appreciation"),("DRA 111",3,"Theatre Appreciation"),("MUS 110",3,"Music Appreciation")],
               "Art, drama, or music elective (3 cr)",category="major"),
   c("COM 231","Public Speaking",3),
   choice_slot("HISREQ-A","History Requirement",3,HIS4,"HIS 111/112/131/132 (3 cr) - one slot")]),
  sem(3,"Year 2 - Fall",[
   choice_slot("RELREQ-A","Religion Requirement",3,REL4,"REL 110/211/212/221 (3 cr) - one slot"),
   c("LIT200-A","200-Level Literature",3),
   c("CIS 110","Introduction to Computers",3),
   choice_slot("ECOHIS-A","Economics/History Requirement",3,
               [("ECO 251",3,"Microeconomics"),("ECO 252",3,"Macroeconomics"),("HIS 111",3,"World Civilization I"),
                ("HIS 112",3,"World Civilization II"),("HIS 131",3,"American History to 1865"),("HIS 132",3,"American History since 1865")],
               "ECO 251/252 or HIS 111/112/131/132 (3 cr) - one slot"),
   c("FREELEC-A","Free Elective",3,category="major")]),
  sem(4,"Year 2 - Spring",[
   choice_slot("LITREQ-A","Literature Requirement",3,ENG231_232,"ENG 231 or ENG 232 (3 cr) - one slot"),
   c("FREELEC-B","Free Elective",3,category="major"),
   c("FREELEC-C","Free Elective",3,category="major"),
   c("FREELEC-D","Free Elective",3,category="major"),
   c("FREELEC-E","Free Elective",3,category="major")])])

# 2. AA Liberal Arts (concentration areas: English=HIS/POL/BUS243 lists in catalog, see p.82 note)
plan("louisburg-college-aa-liberal-arts", "Liberal Arts", "AA",
     BASE + " Areas of concentration (p. 82): English: 15 hrs from ENG; History: 15 hrs from HIS, POL or BUS 243; "
     "Religion: 15 hrs from REL or PHI. Concentration slots transcribed generically; student selects per area. "
     "Social Science Elective verified as a Year 2-Fall row (Fall sum 17/18 matches only with it in Fall).",
 [sem(1,"Year 1 - Fall",[
   c("ENG 111","Writing and Inquiry",3),
   c("ART 111","Art Appreciation",3),
   choice_slot("MATHRQ-A","Mathematics Requirement",3,
               [("MAT 143",3,"Quantitative Literacy")],"MAT 143 or higher math (3/4 cr); modeled at 3 cr minimum with this disclosure"),
   choice_slot("HISREQ-A","History Requirement",3,HIS4,"HIS 111/112/131/132 (3 cr) - one slot"),
   choice_slot("SOCBEH-A","Social/Behavioral Science Requirement",3,PSY_SOC,"PSY 150 or SOC 210 (3 cr) - one slot"),
   c("ACA 122","College Transfer Success (if necessary)",1)]),
  sem(2,"Year 1 - Spring",[
   c("ENG 112","Writing and Research in the Disciplines",3),
   c("SCILAB-A","Lab Science (BIO 110 recommended)",4,category="major"),
   choice_slot("FAELEC-A","Fine Arts Elective",3,
               [("ART 111",3,"Art Appreciation"),("DRA 111",3,"Theatre Appreciation"),
                ("MUS 110",3,"Music Appreciation"),("ENG 125",3,"Creative Writing I")],
               "Fine Arts elective: ART, DRA, MUS, or ENG 125 (3 cr)",category="major"),
   c("CIS 110","Introduction to Computers",3),
   c("CONC-1","Concentration Course 1",3,category="major")]),
  sem(3,"Year 2 - Fall",[
   choice_slot("RELREQ-A","Religion Requirement",3,
               [("REL 211",3,"Old Testament"),("REL 212",3,"New Testament")],"REL 211 or REL 212 (3 cr) - one slot"),
   choice_slot("LITREQ-A","Literature Requirement",3,ENG231_232,"ENG 231 or ENG 232 (3 cr) - one slot"),
   c("CONC-2","Concentration Course 2",3,category="major"),
   c("CONC-3","Concentration Course 3 (200+ Level)",3,category="major"),
   choice_slot("SOCSCIELEC-A","Social Science Elective",3,
               [("ECO 251",3,"Microeconomics"),("HIS 111",3,"World Civilization I"),
                ("POL 120",3,"American Government"),("PSY 150",3,"Introduction to Psychology"),("SOC 210",3,"Introduction to Sociology")],
               "ECO, HIS, POL, PSY, or SOC elective (3 cr)"),
   choice_slot("PEDREQ-A","Fitness/Wellness Requirement",2,PED2,"PED 110 (2 cr) or HEA 110 (3 cr); modeled at 2 cr minimum with this disclosure")]),
  sem(4,"Year 2 - Spring",[
   choice_slot("COMREQ-A","Communication Requirement",3,
               [("COM 120",3,"Interpersonal Communication"),("COM 231",3,"Public Speaking"),("BUS 260",3,"Business Communication")],
               "COM 120, COM 231, or BUS 260 (3 cr) - one slot"),
   c("CONC-4","Concentration Course 4 (200+ Level)",3,category="major"),
   c("CONC-5","Concentration Course 5 (200+ Level)",3,category="major"),
   c("FREELEC-A","Free Elective",3,category="major")])])

# 3. AS Business
plan("louisburg-college-as-business", "Business", "AS",
     BASE + " Prereqs from course descriptions: ACC 121 requires ACC 120.",
 [sem(1,"Year 1 - Fall",[
   c("ENG 111","Writing and Inquiry",3),
   c("BUS 110","Introduction to Business",3,category="major"),
   choice_slot("MATHRQ-A","Mathematics Requirement",3,
               [("MAT 152",4,"Statistical Methods I")],"MAT 152 or higher math (3/4 cr); modeled at 3 cr minimum with this disclosure",category="major"),
   c("ACA 122","College Transfer Success (if necessary)",1),
   choice_slot("CISREQ-A","Computer Requirement",3,CIS2,"CIS 110 or CIS 115 (3 cr) - one slot"),
   c("PED 110","Fitness/Wellness for Life",2)]),
  sem(2,"Year 1 - Spring",[
   c("ENG 112","Writing and Research in the Disciplines",3),
   c("BUS 125","Personal Finance",3,category="major"),
   choice_slot("HISREQ-A","History Requirement",3,
               [("HIS 131",3,"American History to 1865"),("HIS 132",3,"American History since 1865")],"HIS 131 or HIS 132 (3 cr) - one slot"),
   choice_slot("SOCBEH-A","Social/Behavioral Science Requirement",3,PSY_SOC,"PSY 150 or SOC 210 (3 cr) - one slot"),
   choice_slot("RELREQ-A","Religion Requirement",3,REL4,"REL 110/211/212/221 (3 cr) - one slot")]),
  sem(3,"Year 2 - Fall",[
   c("ACC 120","Principles of Financial Accounting",4,category="major"),
   c("ECO 251","Principles of Microeconomics",3,category="major"),
   c("BUS 260","Business Communication",3,category="major"),
   c("SCILAB-A","Lab Science",4),
   c("FREELEC-A","Free Elective",1,category="major")]),
  sem(4,"Year 2 - Spring",[
   c("ACC 121","Principles of Managerial Accounting",4,category="major",prereq=["ACC 120"]),
   c("ECO 252","Principles of Macroeconomics",3,category="major"),
   c("BUSELEC-A","Business Elective",3,category="major"),
   choice_slot("LITFA-A","Literature/Fine Arts Requirement",3,
               ENG231_232+[("ART 111",3,"Art Appreciation"),("MUS 110",3,"Music Appreciation")],
               "ENG 231/232, ART 111, or MUS 110 (3 cr) - one slot"),
   c("FREELEC-B","Free Elective",3,category="major")])])

# 4. AS General Science
plan("louisburg-college-as-general-science", "General Science", "AS", BASE + " 60-shc minimum + 2.0 GPA per catalog.",
 [sem(1,"Year 1 - Fall",[
   c("ENG 111","Writing and Inquiry",3),
   c("SCILAB-A","Lab Science",4,category="major"),
   c("MAT 171","Precalculus Algebra",4,category="major"),
   choice_slot("PEDREQ-A","Fitness/Wellness Requirement",2,PED2,"PED 110 (2 cr) or HEA 110 (3 cr); modeled at 2 cr minimum with this disclosure"),
   c("ACA 122","College Transfer Success",1)]),
  sem(2,"Year 1 - Spring",[
   c("ENG 112","Writing and Research in the Disciplines",3),
   c("SCILAB-B","Lab Science",4,category="major"),
   c("MAT 172","Precalculus Trigonometry",4,category="major"),
   choice_slot("HISREQ-A","History Requirement",3,HIS4,"HIS 111/112/131/132 (3 cr) - one slot"),
   c("FREELEC-A","Free Elective",1,category="major")]),
  sem(3,"Year 2 - Fall",[
   c("MATHSCIELEC-A","Math or Science Elective",4,category="major"),
   c("MATHSCIELEC-B","Math or Science Elective",4,category="major"),
   choice_slot("SOCBEH-A","Social/Behavioral Science Requirement",3,PSY_SOC,"PSY 150 or SOC 210 (3 cr) - one slot"),
   choice_slot("RELREQ-A","Religion Requirement",3,REL4,"REL 110/211/212/221 (3 cr) - one slot"),
   c("COM 231","Public Speaking",3)]),
  sem(4,"Year 2 - Spring",[
   c("MATHSCIELEC-C","Math or Science Elective",4,category="major"),
   c("MATHSCIELEC-D","Math or Science Elective",4,category="major"),
   choice_slot("CISREQ-A","Computer Requirement",3,CIS2,"CIS 110 or CIS 115 (3 cr) - one slot",category="major"),
   choice_slot("LITFA-A","Literature/Fine Arts Requirement",3,ENG_LIT6,"ENG 231/232/241/242, ART 111, or MUS 110 (3 cr) - one slot")])])

# 5. AS Health Science
plan("louisburg-college-as-health-science", "Health Science", "AS",
     BASE + " Prereq from course description: BIO 169 requires BIO 168 (C or higher).",
 [sem(1,"Year 1 - Fall",[
   c("ENG 111","Writing and Inquiry",3),
   c("BIO 111","General Biology I",4,category="major"),
   c("MAT 152","Statistical Methods I or higher",4,category="major"),
   choice_slot("HISREQ-A","History Requirement",3,HIS4,"HIS 111/112/131/132 (3 cr) - one slot")]),
  sem(2,"Year 1 - Spring",[
   c("ENG 112","Writing and Research in the Disciplines",3),
   c("BIO 161","Human Biology",4,category="major"),
   c("HEA 120","Community Health",3,category="major"),
   choice_slot("SOCBEH-A","Social/Behavioral Science Requirement",3,PSY_SOC,"PSY 150 or SOC 210 (3 cr) - one slot"),
   c("PED 110","Fitness/Wellness for Life",2)]),
  sem(3,"Year 2 - Fall",[
   c("BIO 168","Anatomy and Physiology I",4,category="major"),
   c("BIO 250","Genetics",4,category="major"),
   c("HEA 110","Personal Health and Wellness",3),
   choice_slot("RELREQ-A","Religion Requirement",3,REL4,"REL 110/211/212/221 (3 cr) - one slot"),
   c("COM 231","Public Speaking",3)]),
  sem(4,"Year 2 - Spring",[
   c("BIO 169","Anatomy and Physiology II",4,category="major",prereq=["BIO 168"]),
   c("BIO 275","Microbiology",4,category="major"),
   choice_slot("CISREQ-A","Computer Requirement",3,CIS2,"CIS 110 or CIS 115 (3 cr) - one slot",category="major"),
   choice_slot("LITFA-A","Literature/Fine Arts Requirement",3,ENG_LIT6,"ENG 231/232/241/242, ART 111, or MUS 110 (3 cr) - one slot"),
   c("CED 275","Cooperative Field Work",1,category="major")])])

# 6. AS Medical Science
plan("louisburg-college-as-medical-science", "Medical Science", "AS",
     BASE + " Prereqs from course descriptions: BIO 112 requires BIO 111 (C); BIO 169 requires BIO 168 (C); "
     "CHM 152 requires CHM 151 (C). Catalog prints BIO 111 as 3 cr in Year 1-Fall here (all other Louisburg plans "
     "and the NCCCS course show 4 cr); transcribed AS PRINTED (3 cr) with this disclosure; semester still sums to 16.",
 [sem(1,"Year 1 - Fall",[
   c("ENG 111","Writing and Inquiry",3),
   c("BIO 111","General Biology I",3,category="major"),
   c("MAT 152","Statistical Methods I or higher",4,category="major"),
   choice_slot("HISREQ-A","History Requirement",3,HIS4,"HIS 111/112/131/132 (3 cr) - one slot"),
   c("COM 231","Public Speaking",3)]),
  sem(2,"Year 1 - Spring",[
   c("ENG 112","Writing and Research in the Disciplines",3),
   c("BIO 112","General Biology II",4,category="major",prereq=["BIO 111"]),
   c("CHM 151","General Chemistry I",4,category="major"),
   choice_slot("SOCBEH-A","Social/Behavioral Science Requirement",3,PSY_SOC,"PSY 150 or SOC 210 (3 cr) - one slot"),
   c("HEA 110","Personal Health and Wellness",3)]),
  sem(3,"Year 2 - Fall",[
   c("BIO 168","Anatomy and Physiology I",4,category="major"),
   c("BIO 250","Genetics",4,category="major"),
   c("CHM 152","General Chemistry II",4,category="major",prereq=["CHM 151"]),
   choice_slot("RELREQ-A","Religion Requirement",3,REL4,"REL 110/211/212/221 (3 cr) - one slot")]),
  sem(4,"Year 2 - Spring",[
   c("BIO 169","Anatomy and Physiology II",4,category="major",prereq=["BIO 168"]),
   c("BIO 275","Microbiology",4,category="major"),
   choice_slot("CISREQ-A","Computer Requirement",3,CIS2,"CIS 110 or CIS 115 (3 cr) - one slot",category="major"),
   choice_slot("LITFA-A","Literature/Fine Arts Requirement",3,ENG_LIT6,"ENG 231/232/241/242, ART 111, or MUS 110 (3 cr) - one slot"),
   c("CED 275","Cooperative Field Work",1,category="major")])])

# 7. AS Sports Science
plan("louisburg-college-as-sports-science", "Sports Science", "AS",
     BASE + " Sports Science Elective (3 cr) from catalog's recommended list: SPM 279, PSY 271, BIO 112. "
     "BIO 111 requires a C or higher for this program (catalog note). Prereq: BIO 169 requires BIO 168 (C).",
 [sem(1,"Year 1 - Fall",[
   c("ENG 111","Writing and Inquiry",3),
   c("BIO 111","General Biology I",4,category="major"),
   c("MAT 152","Statistical Methods I or higher",4,category="major"),
   choice_slot("HISREQ-A","History Requirement",3,HIS4,"HIS 111/112/131/132 (3 cr) - one slot")]),
  sem(2,"Year 1 - Spring",[
   c("ENG 112","Writing and Research in the Disciplines",3),
   c("BIO 161","Human Biology",4,category="major"),
   c("PED 259","Prevention and Care of Athletic Injury",2,category="major"),
   choice_slot("SOCBEH-A","Social/Behavioral Science Requirement",3,PSY_SOC,"PSY 150 or SOC 210 (3 cr) - one slot"),
   c("PED 110","Fitness/Wellness for Life",2)]),
  sem(3,"Year 2 - Fall",[
   c("PED 165","Sport Science as a Career",3,category="major"),
   c("BIO 168","Anatomy and Physiology I",4,category="major"),
   c("HEA 110","Personal Health and Wellness",3),
   choice_slot("RELREQ-A","Religion Requirement",3,REL4,"REL 110/211/212/221 (3 cr) - one slot"),
   c("COM 231","Public Speaking",3),
   c("PED 291","Athletics' Training/Practicum I",1,category="major")]),
  sem(4,"Year 2 - Spring",[
   choice_slot("SPMSELEC-A","Sports Science Elective",3,
               [("SPM 279",3,"Sports Science Elective"),("PSY 271",3,"Sports Science Elective"),("BIO 112",4,"General Biology II")],
               "Recommended sports science electives: SPM 279, PSY 271, BIO 112 (3-4 cr); modeled at 3 cr minimum with this disclosure",category="major"),
   c("BIO 169","Anatomy and Physiology II",4,category="major",prereq=["BIO 168"]),
   choice_slot("CISREQ-A","Computer Requirement",3,CIS2,"CIS 110 or CIS 115 (3 cr) - one slot",category="major"),
   choice_slot("LITFA-A","Literature/Fine Arts Requirement",3,ENG_LIT6,"ENG 231/232/241/242, ART 111, or MUS 110 (3 cr) - one slot"),
   c("PED 292","Athletics' Training/Practicum II",1,category="major"),
   c("FREELEC-A","Free Elective",1,category="major")])])
