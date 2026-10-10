# Compact Montana plan definitions. Compiled by ~/workspace/degree-tracker/montana_compile.py.
# This file is NOT a seed (underscore prefix); the compiler emits *.json seeds.
# Convention reminders: choice slots recorded at catalog minimum credits;
# composite (non-course) blocks use unique ELECT/GENED/CORE codes and are disclosed in notes.

PLANS = []

# ---------------------------------------------------------------- MSU Bozeman BSN
PLANS.append({
 "id": "montana-state-bsn-nursing",
 "inst_name": "Montana State University", "inst_city": "Bozeman, MT", "inst_kind": "university",
 "degree": "BSN", "major": "Nursing", "catalog_year": "2026-2027",
 "source_url": "https://catalog.montana.edu/undergraduate/nursing/bsn/bsn.pdf",
 "total_credits": 120,
 "allow_repeated_courses": True,
 "requirements_only": False,
 "notes": ("MSU 2026-2027 catalog, Traditional BSN (Mark & Robyn Jones College of Nursing). "
  "Semesters 1-4 = published pre-nursing sample plan; semesters 5-8 = the four-semester nursing program courses "
  "(program total 60 credits; 120 minimum to graduate). NRSG 400 Nursing Simulation (1 cr) repeats in each of the "
  "four nursing semesters by catalog design. Labs CHMY 122IN, BIOM 251, CHMY 124 are co-required with their lecture "
  "courses; catalog credit figures (4 cr) cover lecture plus lab. M 140 exempt with MSU Math Placement level 400+. "
  "WRIT 101W exempt for students with a conferred baccalaureate degree. Competitive admission to the nursing major "
  "after pre-nursing coursework; C or better required in all nursing curriculum courses."),
 "semesters": [
  {"n": 1, "courses": [
   ("WRIT 101W", "College Writing I", 3, "gened", {"note": "Exempt for students with a conferred baccalaureate degree."}),
   ("CHMY 121IN", "Introduction to General Chemistry", 4, "major", {"note": "CHMY 122IN lab co-required; 4 credits cover lecture plus lab."}),
   ("COMX 111US", "Introduction to Public Speaking", 3, "gened"),
   ("M 140", "College Math for Healthcare", 3, "major", {"choices": [("M 140", "College Math for Healthcare", 3), ("M 121Q", "College Algebra", 3)], "note": "Exempt with MSU Math Placement level 400 or above."}),
   ("ELECT-BSN-1", "Free electives", 5, "elective", {"note": "Composite: electives as needed to reach 120 credits."}),
  ]},
  {"n": 2, "courses": [
   ("SOCI 101IS", "Introduction to Sociology", 3, "gened", {"choices": [("SOCI 101IS", "Introduction to Sociology", 3), ("PSYX 100IS", "Introduction to Psychology", 3)], "note": "Choose one."}),
   ("BIOM 250", "Microbiology for Health Sciences: Infectious Diseases", 4, "major", {"note": "BIOM 251 lab co-required; 4 credits cover lecture plus lab."}),
   ("CHMY 123", "Introduction to Organic Chemistry and Biochemistry", 4, "major", {"note": "CHMY 124 lab co-required; 4 credits cover lecture plus lab."}),
   ("CORE-IA-IH-D-1", "IA, IH, or D University Core", 3, "gened", {"note": "Composite: one University Core course from IA, IH, or D categories."}),
  ]},
  {"n": 3, "courses": [
   ("BIOH 201", "Human Anatomy and Physiology I", 4, "major"),
   ("WRIT 201", "College Writing II", 3, "gened"),
   ("HDFS 101IS", "Individual and Family Development: Lifespan", 3, "gened", {"choices": [("HDFS 101IS", "Individual and Family Development: Lifespan", 3), ("PSYX 230", "Developmental Psychology", 3)], "note": "Choose one."}),
   ("CORE-IA-IH-D-2", "IA, IH, or D University Core", 3, "gened", {"note": "Composite: one University Core course from IA, IH, or D categories."}),
  ]},
  {"n": 4, "courses": [
   ("BIOH 211", "Human Anatomy and Physiology II", 4, "major"),
   ("STAT 216Q", "Introduction to Statistics", 3, "gened"),
   ("NUTR 221CS", "Basic Human Nutrition", 3, "gened"),
   ("NRSG 116", "Introduction to Professional Nursing", 2, "major"),
   ("CORE-D-IA-IH-3", "D, IA, or IH University Core", 3, "gened", {"note": "Composite: one University Core course from D, IA, or IH categories."}),
  ]},
  {"n": 5, "courses": [
   ("NRSG 314", "Concepts in Psychosocial Nursing", 2, "major"),
   ("NRSG 316", "Pathophysiology and Pharmacotherapeutics for Nurses I", 3, "major"),
   ("NRSG 323", "Professional Development I: Professional and Ethical Nursing", 1, "major"),
   ("NRSG 327", "Foundations of Nursing Care", 2, "major"),
   ("NRSG 328", "Foundations of Nursing Lab", 3, "major"),
   ("NRSG 329", "Adult Health Assessment", 3, "major"),
   ("NRSG 400", "Nursing Simulation", 1, "major"),
  ]},
  {"n": 6, "courses": [
   ("NRSG 317", "Pathophysiology and Pharmacotherapeutics for Nurses II", 3, "major"),
   ("NRSG 324R", "Professional Development II: Evidence Based Practice", 3, "major"),
   ("NRSG 332", "Nursing Concepts for Health Promotion", 2, "major"),
   ("NRSG 334", "Nursing Practice for Health Promotion", 1, "major"),
   ("NRSG 354", "Nursing Concepts in Reproductive Health", 2, "major"),
   ("NRSG 357", "Nursing Concepts in Pediatric Care", 2, "major"),
   ("NRSG 359", "Nursing Practice in Reproductive Health and Pediatric Care", 3, "major"),
   ("NRSG 400", "Nursing Simulation", 1, "major"),
  ]},
  {"n": 7, "courses": [
   ("NRSG 400", "Nursing Simulation", 1, "major"),
   ("NRSG 403", "Professional Development III: Care Management", 2, "major"),
   ("NRSG 408", "Nursing Concepts in Chronic Care", 2, "major"),
   ("NRSG 409", "Nursing Practice in Chronic Care", 2, "major"),
   ("NRSG 426", "Nursing Concepts in Population Health", 2, "major"),
   ("NRSG 427", "Nursing Practice in Population Health", 2, "major"),
   ("NRSG 431", "Nursing Concepts in Psychiatric/Mental Health", 2, "major"),
   ("NRSG 432", "Nursing Practice in Psychiatric/Mental Health", 1, "major"),
  ]},
  {"n": 8, "courses": [
   ("NRSG 400", "Nursing Simulation", 1, "major"),
   ("NRSG 412", "Professional Development IV: Nursing Leadership and Transition to Practice", 2, "major"),
   ("NRSG 452", "Health Policy and Economics", 2, "major"),
   ("NRSG 470", "Nursing Concepts in Acute Care", 2, "major"),
   ("NRSG 471", "Nursing Practice in Acute Care", 2, "major"),
   ("NRSG 480", "Management of Healthcare Systems", 2, "major"),
   ("NRSG 488", "NCLEX Preparation", 1, "major"),
   ("NRSG 498", "Professional Internship", 2, "major"),
  ]},
 ],
})

# ------------------------------------------------- MSU Bozeman BS Business (Finance)
FIN_ELECTIVES = [
 ("BFIN 317", "American Financial Institutions", 3),
 ("BFIN 421", "Real Estate Investment Analysis", 3),
 ("BFIN 452", "International Finance", 3),
 ("BFIN 456", "Entrepreneurial Finance", 3),
 ("BFIN 458", "Commercial Bank Management", 3),
 ("BFIN 461", "Portfolio Management", 3),
 ("BFIN 465", "Financial Analytics with Python", 3),
 ("BFIN 498", "Internship (at least 3 cr; counts as 1 BFIN elective)", 3),
 ("ACTG 328", "Intermediate Financial Accounting and Reporting II", 3),
 ("ACTG 401", "Federal Income Taxation", 3),
 ("ACTG 421", "Data Analytics for Accountants", 3),
 ("ACTG 493", "Study Abroad", 3),
 ("ECNS 301", "Intermediate Microeconomics with Calculus", 3),
 ("ECNS 303", "Intermediate Macroeconomics with Calculus", 3),
 ("ECNS 345", "Economics of Organization, Finance and Credit", 3),
 ("ECNS 403R", "Introduction to Econometrics", 3),
 ("ECNS 406", "Industrial Organization", 3),
 ("STAT 411", "Methods for Data Analysis I", 3),
]
PLANS.append({
 "id": "montana-state-bs-business-finance",
 "inst_name": "Montana State University", "inst_city": "Bozeman, MT", "inst_kind": "university",
 "degree": "BS", "major": "Business (Finance Option)", "catalog_year": "2026-2027",
 "source_url": "https://catalog.montana.edu/undergraduate/business/finance/",
 "total_credits": 120,
 "requirements_only": False,
 "notes": ("MSU 2026-2027 catalog, Jake Jabs College of Business & Entrepreneurship, B.S. in Business, Finance Option. "
  "120 credits minimum; 42 upper-division credits; C- or better in all prerequisites, university core, required and "
  "elective business courses; 2.0 cumulative GPA. 9 credits of interdisciplinary electives required outside business, "
  "economics, and agricultural business; remaining elective blocks are free electives and/or University Core per the "
  "catalog degree map. Composite elective blocks use unique ELECT codes and are disclosed here."),
 "semesters": [
  {"n": 1, "courses": [
   ("BGEN 104US", "First Year Business Seminar", 3, "major", {"note": "BGEN 104US preferred; any University Seminar (US) core course may satisfy."}),
   ("M 121Q", "College Algebra", 3, "gened", {"note": "Exempt with MSU Math Placement level 400 or above."}),
   ("ECNS 101IS", "Economic Way of Thinking", 3, "gened"),
   ("ELECT-FIN-1", "Interdisciplinary electives, free electives, or University Core", 6, "elective"),
  ]},
  {"n": 2, "courses": [
   ("BGEN 204", "Business Fundamentals", 3, "major"),
   ("BMIS 211", "Data Analytics I", 3, "major"),
   ("STAT 216Q", "Introduction to Statistics", 3, "gened"),
   ("ELECT-FIN-2", "Interdisciplinary electives, free electives, or University Core", 6, "elective"),
  ]},
  {"n": 3, "courses": [
   ("ACTG 201", "Principles of Financial Accounting", 3, "major"),
   ("ECNS 204IS", "Microeconomics", 3, "gened"),
   ("BMGT 240IS", "Business Analytics", 3, "major"),
   ("ELECT-FIN-3", "Interdisciplinary electives, free electives, or University Core", 6, "elective"),
  ]},
  {"n": 4, "courses": [
   ("ACTG 223", "Principles of Financial Accounting II", 3, "major"),
   ("ECNS 202", "Principles of Macroeconomics", 3, "gened"),
   ("BMGT 205", "Professional Business Communication", 3, "major"),
   ("ELECT-FIN-4", "Interdisciplinary electives, free electives, or University Core", 6, "elective"),
  ]},
  {"n": 5, "courses": [
   ("BMGT 335", "Management and Organization", 3, "major"),
   ("BFIN 322", "Business Finance", 3, "major"),
   ("BMIS 312", "Data Analytics II", 3, "major"),
   ("BFIN 357", "Financial Markets and Institutions", 3, "major"),
   ("ACTG 327", "Intermediate Financial Accounting and Reporting I", 3, "major"),
  ]},
  {"n": 6, "courses": [
   ("BMGT 322", "Operations Management", 3, "major"),
   ("BMKT 325", "Principles of Marketing", 3, "major"),
   ("ACTG 441", "Financial Statement Analysis", 3, "major"),
   ("ELECT-FIN-5", "Interdisciplinary electives, free electives, or University Core", 6, "elective"),
  ]},
  {"n": 7, "courses": [
   ("BGEN 361", "Principles of Business Law", 3, "major"),
   ("BFIN 420R", "Investments", 3, "major"),
   ("BFIN 435", "Corporate Finance", 3, "major"),
   ("ELECT-FIN-6", "Interdisciplinary electives, free electives, or University Core", 6, "elective"),
  ]},
  {"n": 8, "courses": [
   ("BFIN 460", "Derivative Securities and Risk Management", 3, "major"),
   ("BGEN 499", "Senior Thesis/Capstone: Strategy Seminar", 3, "major"),
   ("ELECT-FIN-7", "Interdisciplinary electives, free electives, or University Core", 3, "elective"),
   ("FIN-ELECT-CHOICE", "Finance electives: choose two", 6, "major",
    {"choices": FIN_ELECTIVES, "note": "Choose two of the listed finance electives (6 credits)."}),
  ]},
 ],
})

# ------------------------------------------ MSU Bozeman BS Mechanical Engineering
ME_PROF_ELECTIVES = [
 ("BCH 441", "Biochemistry of Macromolecules", 3),
 ("BIOB 425", "Advanced Cell and Molecular Biology", 3),
 ("EBIO 461", "Principles of Biomedical Engineering", 3),
 ("ECHM 424", "Transport Analysis", 3),
 ("EELE 321", "Introduction to Feedback Controls", 3),
 ("EELE 371", "Microprocessor Hardware and Software Systems", 4),
 ("EGEN 415", "Advanced Mechanics of Solids", 3),
 ("EGEN 435", "Fluid Dynamics", 3),
 ("EIND 313", "Work Design and Analysis", 3),
 ("EIND 410/411", "Interaction Design and Interaction Design Project", 3),
 ("EIND 413", "Ergonomics and Human Factors Engineering", 3),
 ("EIND 425", "Technology Entrepreneurship", 3),
 ("EIND 434", "Project Management for Engineers", 3),
 ("EMAT 350", "Engineering Materials", 3),
 ("EMAT 460", "Polymeric Materials", 3),
 ("EMAT 461", "Friction and Wear of Materials", 3),
 ("EMAT 462", "Manufacturing of Composites", 3),
 ("EMAT 463", "Composite Materials", 3),
 ("EMAT 464", "Biomedical Materials Engineering", 3),
 ("EMEC 403", "CAE IV--Design Integration", 3),
 ("EMEC 405", "Finite Element Analysis", 3),
 ("EMEC 424", "Cellular Mechanotransduction", 3),
 ("EMEC 425", "Advanced Thermal Systems", 3),
 ("EMEC 426", "Thermodynamics of Propulsion Systems", 3),
 ("EMEC 430", "Introduction to Combustion", 3),
 ("EMEC 436", "Computational Fluid Dynamics", 3),
 ("EMEC 440", "Biomechanics of Human Movement", 3),
 ("EMEC 444", "Mechanical Behavior of Materials", 3),
 ("EMEC 447", "Aircraft Structures", 4),
 ("EMEC 462", "System Dynamics and Control", 3),
 ("EMEC 465", "Bio-inspired Engineering", 3),
 ("EMEC 466", "Acoustics, Engineering and the Environment", 3),
 ("EMEC 467", "Micro-Electromechanical Systems", 3),
 ("EMEC 490R", "Undergraduate Research (1-3 credits)", 3),
 ("EMEC 492", "Independent Study (1-3 credits)", 3),
 ("EMEC 498", "Internship (1-3 credits)", 3),
 ("ETME 410", "Computerized Numerical Control and Computer-aided Manufacturing Technology", 3),
 ("ETME 415", "Design for Manufacturing and Tooling", 3),
 ("ETME 422", "Principles of HVAC I", 3),
 ("ETME 462", "Industrial Processing Automation and Controls", 3),
 ("ETME 470", "Renewable Energy Applications", 3),
 ("M 349", "Techniques of Applied Mathematics II", 3),
 ("M 441", "Numerical Linear Algebra and Optimization", 3),
 ("M 442", "Numerical Solution of Differential Equations", 3),
 ("M 450", "Applied Mathematics I", 3),
 ("M 451", "Applied Mathematics II", 3),
 ("M 472", "Introduction to Complex Analysis", 3),
 ("PHSX 441", "Solid State Physics", 3),
]
PLANS.append({
 "id": "montana-state-bs-mechanical-engineering",
 "inst_name": "Montana State University", "inst_city": "Bozeman, MT", "inst_kind": "university",
 "degree": "BS", "major": "Mechanical Engineering", "catalog_year": "2026-2027",
 "source_url": "http://catalog.montana.edu/undergraduate/engineering/mechanical-industrial-engineering/mechanical-engineering/",
 "total_credits": 128,
 "requirements_only": False,
 "notes": ("MSU 2026-2027 catalog, Norm Asbjornson College of Engineering, B.S. in Mechanical Engineering (ABET "
  "accredited). 128 credits minimum; 42 upper-division credits. Professional elective slots are 3-credit choices from "
  "the catalog's Approved ME Professional Elective list (options listed). EGEN 488 is a required 0-credit "
  "Fundamentals of Engineering Exam course (required_zero). WRIT 101W: students exempt from the MSU writing "
  "requirement must still complete a 3-credit writing-intensive course."),
 "semesters": [
  {"n": 1, "courses": [
   ("COMX 111US", "Introduction to Public Speaking", 3, "gened", {"choices": [("COMX 111US", "Introduction to Public Speaking", 3), ("CLS 101US", "Knowledge and Community", 3)], "note": "Choose one University Seminar."}),
   ("M 171Q", "Calculus I", 4, "major"),
   ("EMEC 100", "Introduction to Mechanical Engineering", 1, "major"),
   ("EMEC 103", "CAE I - Engineering Graphics Communications", 2, "major"),
   ("PHSX 220", "Physics I with Calculus", 4, "major"),
   ("CORE-ELECT-ME-1", "University Core Electives", 3, "gened", {"note": "Composite: University Core electives per the catalog degree map."}),
  ]},
  {"n": 2, "courses": [
   ("CHMY 141", "College Chemistry I", 4, "major", {"note": "CHMY 142 lab co-required; 4 credits cover lecture plus lab."}),
   ("WRIT 101W", "College Writing I", 3, "gened"),
   ("M 172", "Calculus II", 4, "major"),
   ("PHSX 222", "Physics II with Calculus", 4, "major"),
   ("CORE-ELECT-ME-2", "University Core Electives", 3, "gened", {"note": "Composite: University Core electives per the catalog degree map."}),
  ]},
  {"n": 3, "courses": [
   ("EGEN 201", "Engineering Mechanics - Statics", 3, "major"),
   ("EMEC 203", "CAE II - Mechanical Engineering Computations", 2, "major"),
   ("ETME 215", "Manufacturing Processes", 3, "major"),
   ("ETME 216", "Manufacturing Process Laboratory", 1, "major"),
   ("M 273", "Multivariable Calculus", 4, "major"),
   ("CORE-ELECT-ME-3", "University Core Electives", 3, "gened", {"note": "Composite: University Core electives per the catalog degree map."}),
  ]},
  {"n": 4, "courses": [
   ("EGEN 202", "Engineering Mechanics - Dynamics", 3, "major"),
   ("EGEN 205", "Mechanics of Materials", 3, "major"),
   ("EGEN 350", "Applied Engineering Data Analysis", 2, "major"),
   ("EELE 250", "Circuits, Devices and Motors", 4, "major"),
   ("M 274", "Introduction to Differential Equations", 4, "major"),
  ]},
  {"n": 5, "courses": [
   ("EGEN 335", "Fluid Mechanics", 3, "major"),
   ("EMEC 250", "Mechanical Engineering Materials", 3, "major"),
   ("EMAT 252", "Materials Structure and Properties Lab", 1, "major"),
   ("EMEC 303", "CAE III - Systems Analysis", 3, "major"),
   ("EMEC 320", "Thermodynamics I", 3, "major"),
   ("EMEC 341", "Advanced Mechanics of Materials", 3, "major"),
  ]},
  {"n": 6, "courses": [
   ("EMEC 321", "Thermodynamics II", 3, "major"),
   ("EMEC 326", "Fundamentals of Heat Transfer", 3, "major"),
   ("EMEC 342", "Mechanical Component Design", 3, "major"),
   ("EMEC 360", "Measurement and Instrumentation", 3, "major"),
   ("EMEC 361", "Measurement and Instrumentation Lab", 1, "major"),
   ("EGEN 310R", "Multidisciplinary Engineering Design", 3, "major"),
  ]},
  {"n": 7, "courses": [
   ("EGEN 330", "Business Fundamentals for Technical Professionals", 3, "major"),
   ("EGEN 488", "Fundamentals of Engineering Exam", 0, "major", {"zero": True, "note": "Required 0-credit exam course; excluded from credit sums."}),
   ("EMEC 445", "Mechanical Vibrations", 3, "major"),
   ("EMEC 489R", "Mechanical Engineering Design Capstone I", 2, "major"),
   ("PROF-ELECT-ME-1", "Professional electives (6 credits)", 6, "major",
    {"choices": ME_PROF_ELECTIVES, "note": "Choose professional electives totaling 6 credits from the catalog's Approved ME Professional Elective list."}),
  ]},
  {"n": 8, "courses": [
   ("EMEC 499R", "Mechanical Engineering Design Capstone II", 3, "major"),
   ("PROF-ELECT-ME-2", "Professional electives (6 credits)", 6, "major",
    {"choices": ME_PROF_ELECTIVES, "note": "Choose professional electives totaling 6 credits from the catalog's Approved ME Professional Elective list."}),
   ("PROF-ELECT-ME-3", "Professional elective: take one", 3, "major",
    {"choices": [("EMEC 405", "Finite Element Analysis", 3), ("EMEC 436", "Computational Fluid Dynamics", 3)], "note": "Take one of the two listed professional electives."}),
   ("CORE-ELECT-ME-4", "University Core Electives", 3, "gened", {"note": "Composite: University Core electives per the catalog degree map."}),
  ]},
 ],
})

# ----------------------------------------------- MSU Bozeman BS Psychology (req-only)
PLANS.append({
 "id": "montana-state-bs-psychology",
 "inst_name": "Montana State University", "inst_city": "Bozeman, MT", "inst_kind": "university",
 "degree": "BS", "major": "Psychology", "catalog_year": "2026-2027",
 "source_url": "http://catalog.montana.edu/undergraduate/letters-science/psychology/psychological-science-applied-psychology-options/",
 "total_credits": 120,
 "requirements_only": True,
 "notes": ("MSU 2026-2027 catalog, B.S. in Psychology. The catalog publishes degree requirements with no official "
  "semester sequence — collected as a single requirements block per coordinator convention. Named courses are the "
  "required psychology core; remaining credits are University Core and psychology electives in the catalog's yearly "
  "blocks. 120 credits minimum; 42 upper-division credits. Psychology electives must be selected across the "
  "catalog's elective categories with advisor guidance."),
 "semesters": [
  {"n": 1, "label": "Degree Requirements (no official term sequence)", "courses": [
   ("PSYX 100IS", "Introduction to Psychology", 4, "major"),
   ("PSYX 194", "Psychology Pathways", 1, "major"),
   ("MATH-CHOICE-PSY", "Mathematics requirement", 3, "gened",
    {"choices": [("M 105Q", "Contemporary Mathematics", 3), ("M 121Q", "College Algebra", 3), ("STAT 216Q", "Introduction to Statistics", 3)], "note": "Choose one; exempt with math placement exam at level 400 or higher."}),
   ("PSYX 222", "Psychological Statistics", 4, "major"),
   ("PSYX 225", "Research Design and Analysis", 3, "major"),
   ("PSYX 490R", "Undergraduate Research", 3, "major", {"choices": [("PSYX 490R", "Undergraduate Research", 3), ("PSYX 495", "Field Practice in Applied Psychology", 3)], "note": "Choose one."}),
   ("PSYX 499R", "Senior Thesis/Capstone", 3, "major"),
   ("PSY-ELECT-YR1", "University Core and Psychology Electives (year 1 block)", 22, "elective"),
   ("PSY-ELECT-YR2", "University Core and Psychology Electives (year 2 block)", 23, "elective"),
   ("PSY-ELECT-YR3", "University Core and Psychology Electives (year 3 block)", 27, "elective"),
   ("PSY-ELECT-YR4", "University Core and Psychology Electives (year 4 block)", 27, "elective"),
  ]},
 ],
})

# -------------------------------- UM Missoula BS Business Administration (Management)
BMGT_ELECTIVES = [
 ("BGEN 445", "Sustainability Reporting", 3),
 ("BMGT 329", "Human Resource Management", 3),
 ("BMGT 402", "Principles of Entertainment and Sport Business", 3),
 ("BMGT 403", "Advanced Topics in Entertainment and Sport Business", 3),
 ("BMGT 410", "Sustainable Business Practices", 3),
 ("BMGT 458", "Advanced Entrepreneurship (up to 3 credits)", 3),
 ("BMGT 467", "Global Operations and Supply Chain Management", 3),
 ("BMGT 480", "Cross-Cultural Management", 3),
 ("BMGT 491", "Special Topics (up to 6 credits)", 3),
 ("BMGT 493", "International Experience (up to 6 credits)", 3),
 ("BMGT 494", "Seminar/Workshop (up to 6 credits)", 3),
 ("BMGT 498", "Internship (up to 3 credits)", 3),
 ("BMIS 326", "Introduction to Data Analytics", 3),
]
PLANS.append({
 "id": "umontana-bs-business-administration-management",
 "inst_name": "University of Montana", "inst_city": "Missoula, MT", "inst_kind": "university",
 "degree": "BS", "major": "Business Administration (Management)", "catalog_year": "2026-2027",
 "source_url": "https://catalog.umt.edu/colleges-schools-programs/business/management-marketing/bs-management/",
 "total_credits": 120,
 "requirements_only": False,
 "notes": ("UM 2026-2027 catalog, College of Business, Bachelor of Science in Business Administration - Business "
  "Management (official catalog Four Year Plan, last updated Autumn 2026). At least 54 credits in business classes; "
  "27 business credits at UM; 2.0 GPA in business courses. Choice slots recorded at catalog minimum credits "
  "(math/statistics/WRIT-COMX ranges 3-4 recorded at 3; plan total 120 matches the catalog's 120-124 range minimum). "
  "BMGT elective slots (12 credits total) are 3-credit choices from the catalog's Business Management elective list. "
  "Composite general-education/elective blocks use unique GENED codes and are disclosed here. WRIT 101 vs COMX 111A "
  "order: last names A-L take WRIT 101 in fall; M-Z in spring."),
 "semesters": [
  {"n": 1, "courses": [
   ("BGEN 105S", "Introduction to Business", 3, "major"),
   ("M 115", "Probability and Linear Mathematics", 3, "major",
    {"choices": [("M 115", "Probability and Linear Mathematics", 3), ("M 121", "College Algebra", 3), ("M 151", "Precalculus", 3), ("M 162", "Applied Calculus", 3)], "note": "Math requirement 3-4 credits; recorded at minimum 3."}),
   ("WRIT 101", "College Writing I", 3, "gened", {"choices": [("WRIT 101", "College Writing I", 3), ("COMX 111A", "Introduction to Public Speaking", 3)], "note": "Last names A-L take WRIT 101 in fall; M-Z in spring. 3-4 credits; recorded at 3."}),
   ("GENED-UM-1", "General education / electives", 6, "gened", {"note": "Composite: general education requirements or electives per the catalog degree map."}),
  ]},
  {"n": 2, "courses": [
   ("STAT 216", "Introduction to Statistics", 3, "major",
    {"choices": [("FORS 201", "Forest Biometrics", 3), ("PSYX 222", "Psychological Statistics", 3), ("SOCI 202", "Social Statistics", 3), ("STAT 216", "Introduction to Statistics (preferred)", 3)], "note": "Statistics requirement 3-4 credits; recorded at minimum 3."}),
   ("COMX 111A", "Introduction to Public Speaking", 3, "gened", {"choices": [("COMX 111A", "Introduction to Public Speaking", 3), ("WRIT 101", "College Writing I", 3)], "note": "Whichever of WRIT 101 / COMX 111A was not taken in fall. 3-4 credits; recorded at 3."}),
   ("ECNS 201S", "Principles of Microeconomics", 3, "major"),
   ("GENED-UM-2", "General education / electives", 6, "gened", {"note": "Composite: general education requirements or electives per the catalog degree map."}),
  ]},
  {"n": 3, "courses": [
   ("ACTG 201", "Principles of Financial Accounting", 3, "major"),
   ("BGEN 222", "Business Models and Operations", 3, "major"),
   ("ECNS 202S", "Principles of Macroeconomics", 3, "major"),
   ("GENED-UM-3", "General education / electives", 3, "gened"),
   ("GENED-UM-4", "General education / electives", 3, "gened"),
  ]},
  {"n": 4, "courses": [
   ("ACTG 202", "Principles of Managerial Accounting", 3, "major"),
   ("BMIS 270", "MIS Foundations for Business", 3, "major"),
   ("BGEN 220E", "Business Ethics and Social Responsibility", 3, "major"),
   ("GENED-UM-5", "General education / electives", 3, "gened"),
   ("GENED-UM-6", "General education / electives", 3, "gened"),
  ]},
  {"n": 5, "courses": [
   ("BMGT 448", "Entrepreneurship", 3, "major"),
   ("BGEN 341", "People, Process and Technology I", 3, "major"),
   ("BGEN 360", "International Business", 3, "major"),
   ("BMKT 325", "Principles of Marketing", 3, "major"),
   ("GENED-UM-7", "General education / electives", 3, "gened"),
  ]},
  {"n": 6, "courses": [
   ("BFIN 322", "Business Finance", 3, "major"),
   ("BGEN 342", "People, Process and Technology II", 3, "major"),
   ("BMGT-ELECT-1", "Business Management elective", 3, "major", {"choices": BMGT_ELECTIVES, "note": "3-credit Business Management elective from the catalog list."}),
   ("BMGT-ELECT-2", "Business Management elective", 3, "major", {"choices": BMGT_ELECTIVES, "note": "3-credit Business Management elective from the catalog list."}),
   ("GENED-UM-8", "General education / electives", 3, "gened"),
  ]},
  {"n": 7, "courses": [
   ("BMGT 420", "Leadership and Motivation", 3, "major"),
   ("BGEN 361", "Principles of Business Law", 3, "major"),
   ("BMGT-ELECT-3", "Business Management elective", 3, "major", {"choices": BMGT_ELECTIVES, "note": "3-credit Business Management elective from the catalog list."}),
   ("GENED-UM-9", "General education / electives", 6, "gened", {"note": "Composite: general education requirements or electives per the catalog degree map."}),
  ]},
  {"n": 8, "courses": [
   ("BGEN 499", "Strategic Management", 3, "major"),
   ("BMGT 444", "Leading Teams and Conflict Management", 3, "major"),
   ("BMGT-ELECT-4", "Business Management elective", 3, "major", {"choices": BMGT_ELECTIVES, "note": "3-credit Business Management elective from the catalog list."}),
   ("GENED-UM-10", "General education / electives", 6, "gened", {"note": "Composite: general education requirements or electives per the catalog degree map."}),
  ]},
 ],
})
