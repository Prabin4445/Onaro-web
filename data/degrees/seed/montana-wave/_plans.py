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

# ------------------------------------------------- UM Missoula BA Psychology (req-only)
PLANS.append({
 "id": "umontana-ba-psychology",
 "inst_name": "University of Montana", "inst_city": "Missoula, MT", "inst_kind": "university",
 "degree": "BA", "major": "Psychology", "catalog_year": "2026-2027",
 "source_url": "http://catalog.umt.edu/colleges-schools-programs/humanities-sciences/psychology/ba-psychology/",
 "total_credits": 45,
 "requirements_only": True,
 "notes": ("UM 2026-2027 catalog, B.A. in Psychology. The catalog publishes major course requirements (45-46 hours) "
  "with no official fully-specified semester sequence (the catalog four-year plan leaves most term slots as unlabeled "
  "general-education/category hour blocks) — collected as a single requirements block per coordinator convention. "
  "Full degree requires 120 credits including UM General Education; 60 credits must be in non-psychology courses. "
  "PSYX 330, 340, 360, 385 may count toward only one category. PSYX 290/292/298 limited to 6 hours; PSYX 390/392/398 "
  "limited to 3 hours. Choice slots recorded at catalog minimum credits."),
 "semesters": [
  {"n": 1, "label": "Degree Requirements (no official term sequence)", "courses": [
   ("PSYX 100S", "Intro to Psychology", 3, "major"),
   ("PSYX 120", "Introduction to Psychological Research Methods", 3, "major"),
   ("PSYX 222", "Psychological Statistics", 3, "major",
    {"choices": [("PSYX 222", "Psychological Statistics", 3), ("STAT 216", "Introduction to Statistics", 3)], "note": "Choose one statistics course."}),
   ("PSY-FUND-12", "Fundamental psychology courses (choose 12 credits)", 12, "major",
    {"choices": [("PSYX 233", "Fundamentals of Psychology of Aging", 3), ("PSYX 330", "Child Development", 3), ("PSYX 340", "Psychological Disorders", 3), ("PSYX 360", "Social Psychology", 3), ("PSYX 385", "Psychology of Personality", 3)], "note": "Choose 12 credits from the listed fundamental courses."}),
   ("PSY-FUND2-6", "Fundamental psychology courses (choose 6 credits)", 6, "major",
    {"choices": [("PSYX 250N", "Fundamentals of Biological Psychology", 3), ("PSYX 270", "Fundamentals of Psychology of Learning", 3), ("PSYX 280", "Fundamentals of Memory and Cognition", 3)], "note": "Choose 6 credits from the listed fundamental courses."}),
   ("PSY-UD-15", "Upper-division psychology electives (15 credits)", 15, "major",
    {"choices": [("PSYX 302", "Sexual Orientation and Gender Diversity in Psychology", 3), ("PSYX 320", "Advanced Psychological Research Methods", 3), ("PSYX 335", "Psychology of Gender", 3), ("PSYX 345", "Child and Adolescent Psychological Disorders", 3), ("PSYX 348", "Trauma and Resilience", 3), ("PSYX 352", "Comparative Psychology", 3), ("PSYX 356", "Human Neuropsychology", 3), ("PSYX 362", "Multicultural Psychology", 3), ("PSYX 376", "Evidence-Based Cognitive and Behavioral Treatments", 3), ("PSYX 378", "Introduction to Clinical Psychology", 3), ("PSYX 382", "Forensic Psychology", 3), ("PSYX 383", "Health Psychology", 3), ("PSYX 390", "Advanced Supervised Research (max 3 cr)", 3), ("PSYX 391", "Special Topics", 3), ("PSYX 400", "History and Systems in Psychology", 3), ("PSYX 430", "Counseling Theories in Context", 3), ("PSYX 491", "Special Topics", 3), ("PSYX 494", "Seminar/Workshop", 3), ("SW 423", "Addiction Studies", 3)], "note": "Choose 15 credits of upper-division PSYX electives. May not include PSYX 392, 398, or 499."}),
   ("MATH-PSY", "Mathematics requirement", 3, "gened",
    {"choices": [("M 121", "College Algebra", 3), ("M 151", "Precalculus", 3), ("M 115", "Probability and Linear Mathematics", 4), ("M 162", "Applied Calculus", 4), ("M 171", "Calculus I", 4)], "note": "Choose one; 3-4 credits, recorded at minimum 3."}),
  ]},
 ],
})

# ---------------------------------- UM Missoula BA Elementary Education (req-only)
PLANS.append({
 "id": "umontana-ba-elementary-education",
 "inst_name": "University of Montana", "inst_city": "Missoula, MT", "inst_kind": "university",
 "degree": "BA", "major": "Elementary Education", "catalog_year": "2026-2027",
 "source_url": "https://catalog.umt.edu/colleges-schools-programs/education/teaching-learning/ba-elementary-education/",
 "total_credits": 110,
 "allow_repeated_courses": True,
 "requirements_only": True,
 "notes": ("UM 2026-2027 catalog, B.A. in Elementary Education (K-8). The catalog publishes course requirements "
  "(110 hours) with no official semester sequence — collected as a single requirements block per coordinator "
  "convention. Requires 2.75 GPA and admission to the Teacher Education Program before enrolling in EDU courses. "
  "EDU 395 Clinical Experience is 1 credit in each of levels 1-3 (recorded as one 3-credit entry). EDU 397 is taken "
  "twice and EDU 497 four times, each with a different topic (allow_repeated_courses). Full degree also requires "
  "UM General Education beyond these 110 hours."),
 "semesters": [
  {"n": 1, "label": "Degree Requirements (no official term sequence)", "courses": [
   ("EDU 331", "Lit and Literacy for Children", 3, "major"),
   ("LIT-CHOICE", "Literature requirement (choose one)", 3, "major",
    {"choices": [("LIT 110L", "Introduction to Literature", 3), ("LIT 120L", "Poetry", 3), ("LIT 236L", "Literary Histories", 3), ("LIT 246L", "Genres, Themes, Approaches", 3), ("NASX 235X", "Oral and Written Traditions of Native Americans", 3)], "note": "Choose one literature course."}),
   ("M 132", "Numbers and Operations for Elementary School Teachers", 3, "major"),
   ("M 133", "Geometry and Measurement for Elementary School Teachers", 3, "major"),
   ("M 234", "Higher Mathematics for Elementary School Teachers", 3, "major"),
   ("BIOB 226N", "General Science: Chemical and Life Sciences", 5, "major"),
   ("GEO 224N", "General Science: Physics and Geoscience", 5, "major"),
   ("ENST 472", "General Science: Conservation Education", 3, "major"),
   ("HSTA 101H", "American History I", 4, "major",
    {"choices": [("HSTA 101H", "American History I", 4), ("HSTA 102H", "American History II", 4), ("HSTR 101H", "Western Civilization I", 4), ("HSTR 102H", "Western Civilization II", 4)], "note": "Choose one; catalog shows 4 credits for HSTA 101H."}),
   ("HSTA 255", "Montana History", 3, "major"),
   ("GPHY 121S", "Human Geography", 3, "major",
    {"choices": [("GPHY 121S", "Human Geography", 3), ("GPHY 141S", "Geography of World Regions", 3)], "note": "Choose one."}),
   ("NASX 105H", "Introduction to Native American Studies", 3, "major", {"note": "Other Native American Studies courses may fulfill this requirement; consult an education advisor."}),
   ("PSCI 210S", "Intro to American Government", 3, "major",
    {"choices": [("PSCI 210S", "Intro to American Government", 3), ("PSCI 220S", "Intro to Comparative Government", 3)], "note": "Choose one."}),
   ("EDU 222", "Educational Psychology and Child Development", 3, "major"),
   ("HEE 302", "Methods of Instructional Strategies in Elementary PE", 3, "major"),
   ("ARTZ 302A", "Teaching Early Childhood and Elementary Art", 2, "major"),
   ("MUSE 397", "Methods: K-8 Music", 2, "major"),
   ("THTR 239A", "Creative Drama/Dance: K-8", 2, "major"),
   ("EDU 340", "Classroom Management", 3, "major"),
   ("EDU 382", "Assessment, Curriculum, and Instruction", 3, "major"),
   ("EDU 395", "Clinical Experience", 3, "major", {"note": "1 credit in each of levels 1, 2, and 3; recorded as one 3-credit entry."}),
   ("EDU 397", "Methods: Teaching and Assessing (Early Numeracy K-4)", 3, "major"),
   ("EDU 397", "Methods: Teaching and Assessing (PK-3 Early Reading)", 3, "major"),
   ("EDU 339", "Teaching Assessment in PK-8 Language Arts", 3, "major"),
   ("EDU 346", "Addressing the Needs of Diverse Learners", 3, "major"),
   ("EDU 370", "Integrating Technology into Education", 3, "major"),
   ("EDU 497", "Teaching and Assessing (K-8 Social Studies)", 3, "major"),
   ("EDU 497", "Teaching and Assessing (5-8 Mathematics)", 3, "major"),
   ("EDU 497", "Teaching and Assessing (K-8 Science)", 3, "major"),
   ("EDU 497", "Teaching and Assessing (4-8 Reading)", 3, "major"),
   ("EDU 407E", "Ethics and Policy Issues", 3, "major"),
   ("EDU 494", "Seminar", 1, "major"),
   ("EDU 495", "Student Teaching", 14, "major"),
  ]},
 ],
})

# -------------------------------------- Montana Tech BS Mechanical Engineering
MT_ME_PROF_ELECTIVES = [
 ("CHMY 371", "Physical Chemistry-Quantum Chemistry and Spectroscopy", 3),
 ("EELE 203", "Circuits II for Engineering", 4),
 ("EELE 308", "Signals and Systems Analysis", 4),
 ("EELE 321", "Intro to Feedback Controls", 3),
 ("EELE 421", "Feedback Control II", 3),
 ("EGEN 474", "Intro to Micro/Nanoelectromechanical Systems", 2),
 ("EMEC 491", "Aerospace Propulsion", 3),
 ("EMAT 351", "Fundamentals of Materials", 3),
 ("EMEC 322", "Product Development", 3),
 ("EMEC 415", "Impact Dynamics", 3),
 ("EMEC 435", "Rocket Propulsion", 3),
 ("EMEC 448", "Heating, Ventilating and Air Conditioning (HVAC)", 3),
 ("EMEC 457", "Kinematics", 3),
 ("EMEC 490", "Undergraduate Research (variable credit)", 3),
 ("EMEC 491", "Special Topics (variable credit)", 3),
 ("EMEC 492", "Independent Study (variable credit)", 3),
 ("EMEC 498", "Internship (1-6 credits, 3 max toward degree)", 3),
 ("ENGR 5710", "Advanced Fluid Mechanics", 3),
 ("EWLD 314", "Introduction to Welding Engineering", 3),
 ("EWLD 340", "Welding Process Applications", 2),
 ("EWLD 341", "Welding Process Applications Lab", 1),
 ("EWLD 440", "Design of Welded Connections", 2),
 ("EWLD 443", "Physics of Welding", 2),
 ("EWLD 444", "Physics of Welding Lab", 1),
 ("EWLD 475", "Robotics and Automated Welding", 1),
 ("EWLD 476", "Nondestructive Examination", 3),
]
PLANS.append({
 "id": "montana-tech-bs-mechanical-engineering",
 "inst_name": "Montana Tech", "inst_city": "Butte, MT", "inst_kind": "university",
 "degree": "BS", "major": "Mechanical Engineering", "catalog_year": "2022-2023",
 "source_url": "https://catalog.mtech.edu/preview_program.php?catoid=14&poid=2692",
 "total_credits": 136,
 "requirements_only": False,
 "notes": ("Montana Tech 2022-2023 official catalog (archived edition; transcribed from the official catalog site), "
  "B.S. in Mechanical Engineering. 136 credits minimum. EGEN 434, EMEC 341, EGEN 489W, EMEC 455, EMEC 326, and EGEN "
  "499W are CORE courses that must be completed at Montana Tech (no transfer credit). Professional elective slots are "
  "choices from the catalog's approved list (options listed); focus areas (Control Systems, Nanotechnology, Mechanical "
  "Design, Welding) are recommended but not required. Free electives are 100-level and higher; COMX 111 recommended; "
  "HPER/Activity credits limited to 1 credit. Composite elective blocks use unique codes and are disclosed here."),
 "semesters": [
  {"n": 1, "courses": [
   ("CHMY 141", "College Chemistry I", 3, "major"),
   ("CHMY 142", "College Chemistry Laboratory I", 1, "major"),
   ("EGEN 101", "Introduction to Engineering Calculations and Problem Solving", 3, "major"),
   ("M 171", "Calculus I", 3, "major"),
   ("HUM-ELECT-MT-1", "Humanities Elective", 3, "gened"),
   ("EGEN 194", "Freshman Engineering Seminar", 1, "major"),
   ("WRIT 121", "Introduction to Technical Writing", 3, "gened",
    {"choices": [("WRIT 121", "Introduction to Technical Writing (preferred)", 3), ("WRIT 101", "College Writing I", 3)], "note": "WRIT 121 preferred; WRIT 101 accepted."}),
  ]},
  {"n": 2, "courses": [
   ("CHMY 143", "College Chemistry II", 3, "major"),
   ("CHMY 144", "College Chemistry Laboratory II", 1, "major"),
   ("EMEC 215", "Introduction to Modeling for Mechanical Engineers", 1, "major"),
   ("PHSX 234", "General Physics - Mechanics", 3, "major"),
   ("HUM-ELECT-MT-2", "Humanities Elective", 3, "gened"),
   ("M 172", "Calculus II", 3, "major"),
   ("CSCI 112", "Programming with C I", 3, "major",
    {"choices": [("CSCI 112", "Programming with C I", 3), ("CSCI 117", "Programming with Matlab (preferred)", 3), ("CSCI 135", "Fundamentals of Computer Science I", 3)], "note": "Choose one programming course; CSCI 117 preferred."}),
  ]},
  {"n": 3, "courses": [
   ("EGEN 201", "Engineering Mechanics - Statics", 3, "major"),
   ("M 273", "Multivariable Calculus", 4, "major"),
   ("EGEN 213", "Survey of MET and Materials Engineering", 3, "major"),
   ("PHSX 235", "General Physics - Heat, Sound and Optics", 3, "major"),
   ("PHSX 236", "General Physics - Heat, Sound and Optics Lab", 1, "major"),
   ("EELE 201", "Circuits I for Engineering", 3, "major"),
   ("EELE 202", "Circuits I for Engineering Lab", 1, "major"),
  ]},
  {"n": 4, "courses": [
   ("EGEN 202", "Engineering Mechanics - Dynamics", 3, "major"),
   ("FREE-ELECT-MT-1", "Free electives", 4, "elective", {"note": "Composite: free electives (100-level and higher); COMX 111 recommended."}),
   ("M 274", "Introduction to Differential Equations", 3, "major"),
   ("PHSX 237", "General Physics - Electricity, Magnetism and Motion", 3, "major"),
   ("PHSX 238", "General Physics - Electricity, Magnetism and Motion Lab", 1, "major"),
   ("EGEN 305", "Mechanics of Materials", 3, "major"),
   ("EGEN 306", "Mechanics of Materials Laboratory", 1, "major"),
  ]},
  {"n": 5, "courses": [
   ("EMEC 320", "Thermodynamics I", 3, "major"),
   ("MT-PROF-ELECT-1", "Professional electives (3 credits)", 3, "major",
    {"choices": MT_ME_PROF_ELECTIVES, "note": "3 credits of professional electives from the catalog's approved list."}),
   ("EMEC 341", "Advanced Mechanics of Materials", 3, "major", {"note": "CORE course: must be completed at Montana Tech."}),
   ("EGEN 318", "Computer Applications for Engineers", 2, "major"),
   ("EGEN 335", "Fluid Mechanics", 3, "major"),
   ("EGEN 336", "Fluid Mechanics Lab", 1, "major"),
   ("M 333", "Matrices and Linear Algebra", 3, "major",
    {"choices": [("M 333", "Matrices and Linear Algebra (preferred)", 3), ("STAT 332", "Statistics for Scientists and Engineers", 3)], "note": "Choose one; M 333 preferred."}),
  ]},
  {"n": 6, "courses": [
   ("EGEN 434", "Applied Thermodynamics II", 3, "major", {"note": "CORE course: must be completed at Montana Tech."}),
   ("MT-PROF-ELECT-2", "Professional electives (3 credits)", 3, "major",
    {"choices": MT_ME_PROF_ELECTIVES, "note": "3 credits of professional electives from the catalog's approved list."}),
   ("WRIT 321W", "Advanced Technical Writing", 3, "gened"),
   ("EELE 320", "Process Instrumentation and Control", 4, "major"),
   ("EMEC 455", "Mechanical Component Design", 3, "major", {"note": "CORE course: must be completed at Montana Tech."}),
  ]},
  {"n": 7, "courses": [
   ("EGEN 489W", "Engineering Design I", 2, "major", {"note": "CORE course: must be completed at Montana Tech."}),
   ("MT-PROF-ELECT-3", "Professional elective (2 credits)", 2, "major",
    {"choices": MT_ME_PROF_ELECTIVES, "note": "2 credits of professional electives from the catalog's approved list."}),
   ("MT-PROF-ELECT-4", "Professional electives (3 credits)", 3, "major",
    {"choices": MT_ME_PROF_ELECTIVES, "note": "3 credits of professional electives from the catalog's approved list."}),
   ("EMEC 326", "Fundamentals of Heat Transfer", 3, "major", {"note": "CORE course: must be completed at Montana Tech."}),
   ("EGEN 325", "Engineering Economic Analysis", 3, "major"),
   ("EMEC 445", "Mechanical Vibrations", 3, "major"),
  ]},
  {"n": 8, "courses": [
   ("EELE 355", "Electric Machine Fundamentals", 3, "major"),
   ("SOCSCI-ELECT-MT-1", "Social Science Elective", 3, "gened"),
   ("EGEN 499W", "Engineering Design II", 2, "major", {"note": "CORE course: must be completed at Montana Tech."}),
   ("EMEC 402", "Mechanical Engineering Laboratory", 1, "major"),
   ("MT-PROF-ELECT-5", "Professional electives (3 credits)", 3, "major",
    {"choices": MT_ME_PROF_ELECTIVES, "note": "3 credits of professional electives from the catalog's approved list."}),
   ("EGEN 488", "Fundamentals of Engineering Exam", 1, "major"),
   ("ECNS 201", "Principles of Microeconomics", 3, "gened",
    {"choices": [("ECNS 201", "Principles of Microeconomics", 3), ("ECNS 202", "Principles of Macroeconomics", 3), ("ECNS 203", "Principles of Micro and Macro (preferred)", 3)], "note": "Choose one; ECNS 203 preferred."}),
  ]},
 ],
})

# ============================================================ NEW 2026-10-10
# -------------------------------------------- MSU Bozeman BS Computer Science (Professional Option)
CS_UD_ELECTIVES = [
 ("CSCI 331", "Web Development", 3),
 ("CSCI 347", "Data Mining", 3),
 ("CSCI 351", "Systems Administration", 3),
 ("CSCI 432", "Advanced Algorithm Topics", 3),
 ("CSCI 440", "Database Systems", 3),
 ("CSCI 441", "Computer Graphics", 3),
 ("CSCI 442", "Comp Vision: Robot Vision", 3),
 ("CSCI 443", "User Interface Design", 3),
 ("CSCI 445", "Human Computer Interaction", 3),
 ("CSCI 446", "Artificial Intelligence", 3),
 ("CSCI 447", "Machine Learning", 3),
 ("CSCI 451", "Computational Biology", 3),
 ("CSCI 455", "Embedded Systems: Robotics", 3),
 ("CSCI 460", "Operating Systems", 3),
 ("CSCI 466", "Networks", 3),
 ("CSCI 493", "Study Abroad", 3),
 ("CSCI 495", "Field Work/Practicum", 1),
 ("EGEN 310R", "Multidisciplinary Engineering Design", 3),
 ("EIND 422", "Introduction to Simulation", 3),
 ("ESOF 422", "Advanced Software Engineering: Cybersecurity Practices", 3),
 ("ESOF 423", "Software Engineering Applications", 3),
 ("M 242", "Methods of Proof", 3),
 ("M 441", "Numerical Linear Algebra & Optimization", 3),
 ("M 442", "Numerical Solution of Differential Equations", 3),
 ("PHL 236Q", "Logic", 3),
 ("STAT 421", "Probability Theory", 3),
]
CS_REL_ELECTIVES = [
 ("MART 145RA", "Web Design", 3),
 ("CSCI 107", "Joy and Beauty of Computing", 3),
 ("CSCI 118", "School of Computing Introduction", 1),
 ("CSCI 204", "Multimedia Dev Methods", 3),
 ("CSCI 252", "Introduction to Data Science", 3),
 ("CSCI 290R", "Undergraduate Research (1-6 cr, min)", 1),
 ("CSCI 291", "Special Topics", 3),
 ("CSCI 292", "Independent Study (1-3 cr, min)", 1),
 ("CSCI 490R", "Undergraduate Research (1-6 cr, min)", 1),
 ("CSCI 491", "Special Topics (1-4 cr, min)", 1),
 ("CSCI 492", "Independent Study (1-4 cr, min)", 1),
 ("CSCI 494", "Seminar (1-3 cr, min)", 1),
 ("CSCI 498", "Internship (1-3 cr, min)", 1),
 ("EELE 261", "Intro To Logic Circuits", 4),
 ("EELE 367", "Logic Design", 4),
 ("EELE 371", "Microprocess HW and SW Systems", 4),
 ("EELE 465", "Microcontroller Applications", 4),
 ("EELE 467", "SoC FPGAs I: Hardware-Software Codesign", 4),
 ("EELE 468", "SoC FPGAs II: Application Specific Computing", 4),
]
PLANS.append({
 "id": "montana-state-bs-computer-science",
 "inst_name": "Montana State University", "inst_city": "Bozeman, MT", "inst_kind": "university",
 "degree": "BS", "major": "Computer Science (Professional Option)", "catalog_year": "2025-2026",
 "source_url": "https://catalog.montana.edu/archived-catalogs/2025-2026/undergraduate/engineering/computer-science/professional-option/professional-option.pdf",
 "total_credits": 120,
 "requirements_only": False,
 "notes": ("MSU 2025-2026 archived catalog, B.S. in Computer Science, Professional Option (Gianforte School of "
  "Computing; ABET-accredited). 120 credits minimum; 42 upper-division credits. 19 credits of Upper Division "
  "Elective Choices + 12 credits of CS or Related Electives; excess upper-division elective credits may fulfill "
  "CS-or-Related credits per the catalog. Variable-credit courses recorded at catalog minimum. CSCI 410 and "
  "CSCI 486 appear in the catalog's Upper Division Elective list without titles and are omitted here. CSCI 481 "
  "(0 cr) is a required zero-credit program assessment course. Composite elective/core blocks use unique codes "
  "and are disclosed here."),
 "semesters": [
  {"n": 1, "courses": [
   ("CSCI 127", "Joy and Beauty of Data", 4, "major"),
   ("M 171Q", "Calculus I", 4, "major"),
   ("WRIT 101W", "College Writing I", 3, "gened"),
   ("CORE-ELECT-CS-1", "University Core and Electives", 3, "gened", {"note": "Composite: University Core and electives per the catalog degree map."}),
  ]},
  {"n": 2, "courses": [
   ("CSCI 132", "Basic Data Structures and Algorithms", 4, "major"),
   ("M 172", "Calculus II", 4, "major"),
   ("CORE-SEM-CS", "University Seminar Core", 3, "gened", {"note": "Composite: University Seminar core per the catalog degree map."}),
   ("CORE-ELECT-CS-2", "University Core and Electives", 4, "gened", {"note": "Composite: University Core and electives per the catalog degree map."}),
  ]},
  {"n": 3, "courses": [
   ("CSCI 215CS", "Social & Ethical Issues in Computer Science", 3, "major"),
   ("CSCI 246", "Discrete Structures", 3, "major"),
   ("WRIT 221", "Intermediate Tech Writing", 3, "gened"),
   ("SCI-ELECT-CS-1", "Science elective", 4, "major", {"note": "Composite: science elective per the department's approved list."}),
   ("CORE-ELECT-CS-3", "University Core", 3, "gened", {"note": "Composite: University Core per the catalog degree map."}),
  ]},
  {"n": 4, "courses": [
   ("CSCI 112", "Programming with C I", 3, "major"),
   ("CSCI 232", "Data Structures and Algorithms", 4, "major"),
   ("MATH-ELECT-CS-1", "Math, Statistics, or Probability Elective", 3, "major", {"note": "Composite: math, statistics, or probability elective per the department list."}),
   ("SCI-ELECT-CS-2", "Science elective", 3, "major", {"note": "Composite: science elective per the department's approved list."}),
   ("CORE-ELECT-CS-4", "University Core", 3, "gened", {"note": "Composite: University Core per the catalog degree map."}),
  ]},
  {"n": 5, "courses": [
   ("ESOF 322", "Software Engineering", 3, "major"),
   ("CSCI 366", "Computer Systems", 3, "major"),
   ("UD-ELECT-CS-1", "Upper Division Elective", 3, "major",
    {"choices": CS_UD_ELECTIVES, "note": "3-credit choice from the catalog's Upper Division Elective Choices list."}),
   ("CSREL-ELECT-CS-1", "CS or Related Electives (6 credits)", 6, "major",
    {"choices": CS_REL_ELECTIVES, "note": "Choose CS or Related Electives totaling 6 credits from the catalog list."}),
  ]},
  {"n": 6, "courses": [
   ("CSCI 305", "Concepts/Programming Languages", 3, "major"),
   ("CSCI 338", "Computer Science Theory", 3, "major"),
   ("UD-ELECT-CS-2", "Upper Division Electives (6 credits)", 6, "major",
    {"choices": CS_UD_ELECTIVES, "note": "Choose Upper Division Electives totaling 6 credits from the catalog list."}),
   ("CSREL-ELECT-CS-2", "CS or Related Electives", 3, "major",
    {"choices": CS_REL_ELECTIVES, "note": "3-credit choice from the catalog's CS or Related Electives list."}),
  ]},
  {"n": 7, "courses": [
   ("UD-ELECT-CS-3", "Upper Division Electives (6 credits)", 6, "major",
    {"choices": CS_UD_ELECTIVES, "note": "Choose Upper Division Electives totaling 6 credits from the catalog list."}),
   ("CSREL-ELECT-CS-3", "CS or Related Electives", 3, "major",
    {"choices": CS_REL_ELECTIVES, "note": "3-credit choice from the catalog's CS or Related Electives list."}),
   ("MATH-ELECT-CS-2", "Math, Statistics, or Probability Elective", 3, "major", {"note": "Composite: math, statistics, or probability elective per the department list."}),
   ("ELECT-CS-1", "Free Electives", 3, "elective", {"note": "Composite: free electives per the catalog degree map."}),
  ]},
  {"n": 8, "courses": [
   ("CSCI 468", "Compilers", 4, "major"),
   ("CSCI 476", "Computer Security", 3, "major"),
   ("CSCI 481", "Program Assessment", 0, "major", {"zero": True, "note": "Required 0-credit program assessment course; excluded from credit sums."}),
   ("UD-ELECT-CS-4", "Upper Division Elective", 4, "major",
    {"choices": CS_UD_ELECTIVES, "note": "4-credit Upper Division Elective choice from the catalog list."}),
   ("ELECT-CS-2", "Free Electives", 3, "elective", {"note": "Composite: free electives per the catalog degree map."}),
  ]},
 ],
})

# ----------------- UM Missoula BS Biology (Cellular & Molecular Biology concentration)
PLANS.append({
 "id": "umontana-bs-biology-cellular-molecular",
 "inst_name": "University of Montana", "inst_city": "Missoula, MT", "inst_kind": "university",
 "degree": "BS", "major": "Biology (Cellular & Molecular Biology Concentration)", "catalog_year": "2024-2025",
 "source_url": "http://umt.edu/degree-maps/2024-2025-degree-maps/bs-biology-cellular-molecular-biology-24-25.pdf",
 "total_credits": 120,
 "requirements_only": False,
 "notes": ("University of Montana official Four-Year Academic Plan 2024-2025, B.S. in Biology, Cellular & Molecular "
  "Biology Concentration (College of Humanities and Sciences). The plan is labeled a sample academic plan; students "
  "meet with an academic advisor to formulate their own. Combined lecture/lab rows (e.g. BIOB 160/161N) are recorded "
  "as single entries exactly as printed. The senior-fall 'Major Elective (Disease)' slot is paired with an "
  "advanced-writing component on the degree map. Composite elective/general-education blocks use unique codes and "
  "are disclosed here."),
 "semesters": [
  {"n": 1, "courses": [
   ("BIOB 160/161N", "Principles of Living Systems/Lab", 4, "major"),
   ("CHMY 141N/142N", "College Chemistry I/Lab", 5, "major"),
   ("M 162", "Applied Calculus", 4, "major",
    {"choices": [("M 162", "Applied Calculus", 4), ("M 171", "Calculus I", 4)], "note": "M 162 Applied Calculus or M 171 Calculus I."}),
   ("ELECT-UMB-1", "Elective", 1, "elective", {"note": "Composite: 1-credit elective per the degree map."}),
  ]},
  {"n": 2, "courses": [
   ("BIOB 170N/171N", "Principles of Biological Diversity/Lab", 5, "major"),
   ("CHMY 143N/144N", "College Chemistry II/Lab", 5, "major"),
   ("WRIT 101", "College Writing I", 3, "gened"),
   ("GENED-UMB-1", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the degree map."}),
  ]},
  {"n": 3, "courses": [
   ("BIOB 260", "Cell & Molecular Biology", 4, "major"),
   ("CHMY 221/222", "Organic Chemistry I/Lab", 5, "major"),
   ("BIOM 360/361", "General Microbiology/Lab", 5, "major"),
   ("ELECT-UMB-2", "Elective", 1, "elective", {"note": "Composite: 1-credit elective per the degree map."}),
  ]},
  {"n": 4, "courses": [
   ("BIOB 272", "Genetics & Evolution", 4, "major"),
   ("CHMY 223/224", "Organic Chemistry II/Lab", 5, "major"),
   ("WRIT-INT-UMB", "Intermediate Writing Course", 3, "gened", {"note": "Composite: intermediate writing course per the degree map."}),
   ("GENED-UMB-2", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the degree map."}),
  ]},
  {"n": 5, "courses": [
   ("BCH 480", "Advanced Biochemistry I", 3, "major"),
   ("BIOB 301", "Developmental Biology", 3, "major"),
   ("PHSX 205N/206N", "College Physics I/Lab", 5, "major"),
   ("ELECT-UMB-3", "Elective", 4, "elective", {"note": "Composite: 4-credit elective per the degree map."}),
  ]},
  {"n": 6, "courses": [
   ("BCH 482", "Advanced Biochemistry II", 3, "major"),
   ("BIOB 375", "General Genetics", 3, "major"),
   ("PHSX 207N/208N", "College Physics II/Lab", 5, "major"),
   ("GENED-UMB-3", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the degree map."}),
  ]},
  {"n": 7, "courses": [
   ("MAJ-ELECT-DIS-UMB", "Major Elective (Disease)", 3, "major", {"note": "Major elective from the Disease category; the degree map pairs this slot with an advanced-writing component."}),
   ("MAJ-ELECT-LAB-UMB-1", "Major Elective (laboratory/research)", 2, "major", {"note": "Composite: major elective from the laboratory/research category per the degree map."}),
   ("CHEM-DEPTH-UMB", "Chemistry Depth", 4, "major", {"note": "Composite: chemistry depth course per the degree map."}),
   ("GENED-UMB-4", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the degree map."}),
   ("UD-ELECT-UMB-1", "Upper Division Elective", 3, "elective", {"note": "Composite: upper-division elective per the degree map."}),
  ]},
  {"n": 8, "courses": [
   ("BIOB 425", "Advanced Cell & Molecular Biology", 3, "major"),
   ("MAJ-ELECT-DEPTH-UMB", "Major Elective (Depth)", 3, "major", {"note": "Composite: major elective from the depth category per the degree map."}),
   ("MAJ-ELECT-LAB-UMB-2", "Major Elective (laboratory/research)", 1, "major", {"note": "Composite: major elective from the laboratory/research category per the degree map."}),
   ("GENED-UMB-5", "General Education Requirements", 6, "gened", {"note": "Composite: general education requirements per the degree map."}),
   ("UD-ELECT-UMB-2", "Upper Division Elective", 3, "elective", {"note": "Composite: upper-division elective per the degree map."}),
  ]},
 ],
})

# -------- UM Missoula BS Human Biology and Biomedical Sciences (Pre-Health Track)
PLANS.append({
 "id": "umontana-bs-human-biology-pre-health",
 "inst_name": "University of Montana", "inst_city": "Missoula, MT", "inst_kind": "university",
 "degree": "BS", "major": "Human Biology and Biomedical Sciences (Pre-Health Track)", "catalog_year": "2026-2027",
 "source_url": "https://catalog.umt.edu/colleges-schools-programs/science/biological-biomedical-sciences/bs-human-biology-biomedical-sciences/",
 "total_credits": 123,
 "requirements_only": False,
 "notes": ("UM 2026-2027 catalog, B.S. in Human Biology and Biomedical Sciences, Pre-Health Track four-year plan "
  "(updated Autumn 2026). The pre-health track is for students interested in health-related careers that do not "
  "require advanced chemistry (e.g. public health, occupational therapy, some physician assistant, most physical "
  "therapy). Paired lecture/lab rows are recorded as single entries exactly as printed in the catalog plan. The "
  "senior-year blank rows are recorded as general-education composites and disclosed here. Composite blocks use "
  "unique codes."),
 "semesters": [
  {"n": 1, "courses": [
   ("BIOB 160 & 161N", "Principles of Living Systems and Principles of Living Systems Lab", 4, "major"),
   ("CHMY 121N", "Introduction to General Chemistry", 4, "major"),
   ("M 162", "Applied Calculus", 4, "major",
    {"choices": [("M 162", "Applied Calculus", 4), ("M 171", "Calculus I", 4)], "note": "M 162 Applied Calculus or M 171 Calculus I."}),
   ("WRIT 101", "College Writing I", 4, "gened"),
  ]},
  {"n": 2, "courses": [
   ("BIOB 170N & 171N", "Principles of Biological Diversity and Principles of Biological Diversity Lab", 5, "major"),
   ("CHMY 123 & 124", "Introduction to Organic and Biochemistry and Lab", 6, "major"),
   ("PSYX 100S", "Intro to Psychology", 3, "gened"),
   ("HMED 140", "Introduction to Health Professions", 2, "major"),
  ]},
  {"n": 3, "courses": [
   ("BIOB 260", "Cellular and Molecular Biology", 4, "major"),
   ("BIOH 365 & 366", "Human Anatomy and Physiology for Health Professions I and Laboratory", 4, "major"),
   ("STAT 216", "Introduction to Statistics", 4, "major"),
   ("GENED-UMH-1", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the catalog plan."}),
  ]},
  {"n": 4, "courses": [
   ("BIOB 272", "Genetics and Evolution", 4, "major"),
   ("BIOH 370 & 371", "Human Anatomy and Physiology for Health Professions II and Laboratory", 4, "major"),
   ("GENED-UMH-2", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the catalog plan."}),
   ("GENED-UMH-3", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the catalog plan."}),
  ]},
  {"n": 5, "courses": [
   ("BIOM 360 & 361", "General Microbiology and General Microbiology Lab", 5, "major"),
   ("PHSX 205N & 206N", "College Physics I and College Physics I Laboratory", 5, "major"),
   ("GENED-UMH-4", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the catalog plan."}),
   ("ELECT-UMH-1", "Elective", 1, "elective", {"note": "Composite: 1-credit elective per the catalog plan."}),
  ]},
  {"n": 6, "courses": [
   ("BCH 380", "Biochemistry", 4, "major"),
   ("PHSX 207N & 208N", "College Physics II and College Physics II Laboratory", 5, "major"),
   ("GENED-UMH-5", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the catalog plan."}),
   ("GENED-UMH-6", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the catalog plan."}),
   ("ELECT-UMH-2", "Elective", 1, "elective", {"note": "Composite: 1-credit elective per the catalog plan."}),
  ]},
  {"n": 7, "courses": [
   ("BIOB 410 & BIOM 428", "Immunology and General Parasitology Lab", 5, "major"),
   ("BIOM 427 & BIOM 428", "General Parasitology and General Parasitology Lab", 4, "major"),
   ("GENED-UMH-7", "General Education Requirement", 3, "gened", {"note": "Composite: general education requirement per the catalog plan."}),
   ("GENED-UMH-8", "General Education / Electives", 5, "gened", {"note": "Composite: the catalog plan prints this 5-credit row blank."}),
  ]},
  {"n": 8, "courses": [
   ("BIOM 435", "Virology", 3, "major"),
   ("BIOM 402", "Pathogenic Microbes", 3, "major"),
   ("GENED-UMH-9", "General Education / Electives", 3, "gened", {"note": "Composite: the catalog plan prints this 3-credit row blank."}),
   ("GENED-UMH-10", "General Education / Electives", 6, "gened", {"note": "Composite: the catalog plan prints this 6-credit row blank."}),
  ]},
 ],
})

# ----------------------------------------------- MSU Billings ASN Registered Nurse
PLANS.append({
 "id": "msu-billings-asn-nursing",
 "inst_name": "Montana State University Billings", "inst_city": "Billings, MT", "inst_kind": "university",
 "degree": "ASN", "major": "Nursing (Registered Nursing)", "catalog_year": "2026-2027",
 "source_url": "https://catalog.msubillings.edu/cc/academic-programs-departments/asn/asn.pdf",
 "total_credits": 72,
 "requirements_only": False,
 "notes": ("MSU Billings (City College) current catalog, Associate of Science in Registered Nursing (ASN). Five-"
  "semester program with one semester of prerequisite courses; admission to the nursing program is required before "
  "second-semester coursework. 72 credits minimum; selective GPA of 2.75 from prerequisite courses plus an entrance "
  "exam and interview. Graduates must pass the NCLEX-RN for licensure."),
 "semesters": [
  {"n": 1, "label": "First Semester (prerequisites)", "courses": [
   ("BIOH 201", "Human Anatomy & Physiology I", 3, "major"),
   ("BIOH 202", "Human Anatomy & Phys I Lab", 1, "major"),
   ("CHMY 121", "Intro to General Chemistry", 3, "major"),
   ("CHMY 122", "Intro to Gen Chem Lab", 1, "major"),
   ("WRIT 101", "College Writing I", 3, "gened"),
   ("M 140", "College Math for Healthcare", 3, "major"),
  ]},
  {"n": 2, "label": "Second Semester", "courses": [
   ("BIOH 211", "Human Anatomy & Physiology II", 3, "major"),
   ("BIOH 212", "Human Anatomy & Phys II Lab", 1, "major"),
   ("NRSG 230", "Nursing Pharmacology", 3, "major"),
   ("NRSG 231", "Nursing Pharmacology Lab", 2, "major"),
   ("NRSG 232", "Foundations for Nursing", 3, "major"),
   ("NRSG 233", "Foundations of Nursing Lab", 3, "major"),
  ]},
  {"n": 3, "label": "Third Semester", "courses": [
   ("NRSG 256", "Pathophysiology", 3, "major"),
   ("NRSG 234", "Adult Nursing I", 3, "major"),
   ("NRSG 235", "Adult Nursing I Cl", 2, "major"),
   ("NRSG 236", "Health/Ill Maternity Nsg", 2, "major"),
   ("NRSG 237", "Health/Ill Maternal Nsg Cl", 1, "major"),
   ("PSYX 100", "Intro to Psychology", 3, "gened"),
  ]},
  {"n": 4, "label": "Fourth Semester", "courses": [
   ("NRSG 244", "Adult Nursing II", 3, "major"),
   ("NRSG 245", "Adult Nursing II Cl", 2, "major"),
   ("NRSG 254", "Mental Health Concepts", 3, "major"),
   ("NRSG 255", "Mental Health Concepts Cl", 1, "major"),
   ("NRSG 246", "Hlth/Illness Child/Fmly Nursng", 2, "major"),
   ("NRSG 247", "Hlth/Illness Child/Fam Nrs Cln", 1, "major"),
   ("SOCI 101", "Introduction to Sociology", 3, "gened"),
  ]},
  {"n": 5, "label": "Fifth Semester", "courses": [
   ("NRSG 259", "Adult Nursing III", 3, "major"),
   ("NRSG 260", "Adult Nursing III Lab", 1, "major"),
   ("NRSG 261", "Adult Nursing III Cl", 2, "major"),
   ("NRSG 266", "Managing Client Care RN", 2, "major"),
   ("NRSG 267", "Managing Client Care RN Cl", 2, "major"),
   ("BIOM 250", "Microbiology for Hlth Sciences", 3, "major"),
   ("BIOM 251", "Microbiology Hlth Sciences Lab", 1, "major"),
  ]},
 ],
})

# ------------------------------------------- MSU Billings RN-to-BSN (completion)
PLANS.append({
 "id": "msu-billings-bsn-rn-to-bsn",
 "inst_name": "Montana State University Billings", "inst_city": "Billings, MT", "inst_kind": "university",
 "degree": "BSN", "major": "Nursing (RN to BSN Degree Completion)", "catalog_year": "2026-2027",
 "source_url": "https://catalog.msubillings.edu/undergraduate/college-health-professions-science/department-health-sciences-and-human-performance/rn-bsn-completion-program/rn-bsn-completion-program.pdf",
 "total_credits": 49,
 "program_type": "completion",
 "requirements_only": False,
 "notes": ("MSU Billings current catalog, Registered Nurse (RN) to Bachelor of Science in Nursing Degree Completion "
  "Program (program_type=completion per the official catalog). For nurses holding an associate degree in nursing "
  "and an unencumbered RN license; 49 credits delivered online in a minimum of three semesters with rolling "
  "admission. A current unencumbered RN license is required to graduate; NRSG 301/302 and 463/464 include "
  "practice-oriented clinicals. The third-semester humanities slot is 'one course chosen from the Humanities "
  "category of Gen Ed, in consultation with an advisor' per the catalog. Composite blocks use unique codes and "
  "are disclosed here."),
 "semesters": [
  {"n": 1, "label": "Fall", "courses": [
   ("NRSG 320", "Nursing Informatics", 3, "major"),
   ("NRSG 325", "Health Assessment", 3, "major"),
   ("STAT 216", "Introduction to Statistics", 4, "gened"),
   ("WRIT 321", "Advanced Technical Writing", 3, "gened"),
   ("NRSG 424", "Nsg Research/Evidence-Based", 3, "major"),
  ]},
  {"n": 2, "courses": [
   ("NRSG 322", "Health Promotion and Ed", 3, "major"),
   ("NRSG 301", "Nursing in the Community", 5, "major"),
   ("NRSG 302", "Nursing in the Community Cl", 1, "major"),
   ("NRSG 326", "Complex Healthcare Needs", 3, "major"),
   ("PHL 326", "Death, Dying & Medical Ethics", 3, "gened"),
   ("PSYX 230", "Developmental Psychology", 3, "gened"),
  ]},
  {"n": 3, "courses": [
   ("NRSG 344", "Family Nursing", 3, "major"),
   ("NRSG 463", "Leader/Manage for the RN", 5, "major"),
   ("NRSG 464", "Leader/Manage for the RN Cl", 1, "major"),
   ("NRSG 361", "Global Nursing", 3, "major"),
   ("HUM-ELECT-MSUB", "Humanities elective", 3, "gened", {"note": "Composite: one course from the Humanities category of Gen Ed, in consultation with an advisor."}),
  ]},
 ],
})

# ---------------- MSU Billings BS Business Administration (General Business Option)
PLANS.append({
 "id": "msu-billings-bs-business-administration-general-business",
 "inst_name": "Montana State University Billings", "inst_city": "Billings, MT", "inst_kind": "university",
 "degree": "BS", "major": "Business Administration (General Business Option)", "catalog_year": "2026-2027",
 "source_url": "https://catalog.msubillings.edu/undergraduate/college-business/department-business-administration/bs-business-administration-general-business-option/",
 "total_credits": 122,
 "requirements_only": False,
 "notes": ("MSU Billings 2026-2027 catalog, B.S. in Business Administration, General Business Option, Suggested Plan "
  "of Study. The catalog's published semester rows sum to 122 credits while the degree minimum is 120; "
  "total_credits records the published rows exactly. Blank rows in the catalog plan are recorded as "
  "general-education/elective composites and disclosed here. The catalog notes students may not be able to follow "
  "the plan exactly and should consult an advisor. Composite blocks use unique codes."),
 "semesters": [
  {"n": 1, "courses": [
   ("ECNS 201", "Principles of Microeconomics", 3, "major"),
   ("M 143", "Finite Mathematics", 4, "major"),
   ("GENED-MSBU-1", "General Education", 6, "gened", {"note": "Composite: general education per the catalog plan (printed blank)."}),
   ("BGEN 105A", "Introduction to Business", 3, "major"),
  ]},
  {"n": 2, "courses": [
   ("ECNS 202", "Principles of Macroeconomics", 3, "major"),
   ("STAT 216", "Introduction to Statistics", 4, "major"),
   ("WRIT 220", "Business & Prof Writing", 3, "gened"),
   ("GENED-MSBU-2", "General Education", 6, "gened", {"note": "Composite: general education per the catalog plan (printed blank)."}),
  ]},
  {"n": 3, "courses": [
   ("ACTG 201", "Principles of Fin Acct", 3, "major"),
   ("GENED-MSBU-3", "General Education / Electives", 12, "gened", {"note": "Composite: general education/electives per the catalog plan (printed blank)."}),
  ]},
  {"n": 4, "courses": [
   ("ACTG 202", "Principles of Managerial Acct", 3, "major"),
   ("GENED-MSBU-4", "General Education / Electives", 9, "gened", {"note": "Composite: general education/electives per the catalog plan (printed blank)."}),
   ("BGEN 240", "Intro Business Data Analysis", 3, "major"),
  ]},
  {"n": 5, "courses": [
   ("BMGT 335", "Management & Organization", 3, "major"),
   ("BMKT 325", "Principles of Marketing", 3, "major"),
   ("BMGT 329", "Human Resource Management", 3, "major"),
   ("BGEN 235", "Business Law", 3, "major"),
   ("ELECT-MSBU-1", "Electives", 3, "elective", {"note": "Composite: electives per the catalog plan (printed blank)."}),
  ]},
  {"n": 6, "courses": [
   ("BMIS 311", "Management Information Systems", 3, "major"),
   ("BGEN 315", "Applied Business Decisions", 3, "major"),
   ("BGEN 360", "International Business", 3, "major"),
   ("BMGT 322", "Operations Management", 3, "major"),
   ("ELECT-MSBU-2", "Electives", 3, "elective", {"note": "Composite: electives per the catalog plan (printed blank)."}),
  ]},
  {"n": 7, "courses": [
   ("BFIN 322", "Business Finance", 3, "major"),
   ("BMKT 342", "Marketing Research", 3, "major"),
   ("BMGT 353", "Organizational Behavior", 3, "major"),
   ("BGEN 440", "Business and the Environment", 3, "major"),
   ("ELECT-MSBU-3", "Electives", 3, "elective", {"note": "Composite: electives per the catalog plan (printed blank)."}),
  ]},
  {"n": 8, "courses": [
   ("BGEN 499", "Capstone", 3, "major"),
   ("ELECT-MSBU-4", "Electives", 6, "elective", {"note": "Composite: electives per the catalog plan (printed blank)."}),
   ("BMGT 448", "Entrepreneurship", 3, "major"),
   ("ELECT-MSBU-5", "Electives", 3, "elective", {"note": "Composite: electives per the catalog plan (printed blank)."}),
  ]},
 ],
})

# ------------------------------------------------- Montana Tech BS Computer Science
PLANS.append({
 "id": "montana-tech-bs-computer-science",
 "inst_name": "Montana Tech", "inst_city": "Butte, MT", "inst_kind": "university",
 "degree": "BS", "major": "Computer Science", "catalog_year": "2024-2025",
 "source_url": "https://catalog.mtech.edu/preview_program.php?catoid=16&poid=3229&returnto=1641",
 "total_credits": 120,
 "requirements_only": False,
 "notes": ("Montana Tech 2024-2025 archived catalog, B.S. in Computer Science. 120 credits minimum. Elective-slot "
  "definitions transcribed from the catalog footnotes: CS/SE/DS/ITS Elective = any CSCI, ESOF, M, STAT, or ITS course "
  "not already required; Math/Science Elective = any course in the Math or Science General Education Core not "
  "already required. Composite elective blocks use unique codes and are disclosed here."),
 "semesters": [
  {"n": 1, "courses": [
   ("EGEN 194", "First-Year Engineering Seminar", 1, "major"),
   ("CSCI 135", "Fundamentals Of Computer Science I", 3, "major"),
   ("CSCI 102", "Computational Thinking with Lab", 3, "major"),
   ("M 171", "Calculus I", 3, "major"),
   ("HUM-ELECT-MT-1", "Humanities & Fine Arts Elective", 3, "gened", {"note": "Composite: humanities and fine arts elective per the catalog plan."}),
   ("WRIT 121", "Introduction To Technical Writing", 3, "gened",
    {"choices": [("WRIT 121", "Introduction To Technical Writing", 3), ("WRIT 101", "College Writing I", 3)], "note": "WRIT 121 or WRIT 101."}),
  ]},
  {"n": 2, "courses": [
   ("M 172", "Calculus II", 3, "major"),
   ("HUM-ELECT-MT-2", "Humanities & Fine Arts Elective", 3, "gened", {"note": "Composite: humanities and fine arts elective per the catalog plan."}),
   ("CSCI 210", "Web Programming", 3, "major"),
   ("CSCI 136", "Fundamentals Of Computer Science II", 3, "major"),
   ("SOC-ELECT-MT", "Social Science Elective", 3, "gened", {"note": "Composite: social science elective per the catalog plan."}),
  ]},
  {"n": 3, "courses": [
   ("CSCI 232", "Data Structures and Algorithms", 3, "major"),
   ("CSSEDSITS-ELECT-1", "CS/SE/DS/ITS Elective", 3, "major", {"note": "Composite: any CSCI, ESOF, M, STAT, or ITS course not already required."}),
   ("SCI-CORE-MT-1", "Physical & Life Science Core with Lab", 4, "major", {"note": "Composite: physical and life science core with lab per the catalog plan."}),
   ("CSCI 246", "Discrete Structures", 3, "major"),
   ("COMX 111", "Introduction to Public Speaking", 3, "gened",
    {"choices": [("COMX 111", "Introduction to Public Speaking", 3), ("COMX 230", "Presenting Technical Information", 3)], "note": "COMX 111 or COMX 230."}),
  ]},
  {"n": 4, "courses": [
   ("CSCI 332", "Design & Analysis of Algorithms", 3, "major"),
   ("M 333", "Matrices & Linear Algebra", 3, "major"),
   ("SCI-CORE-MT-2", "Physical & Life Science Core with Lab", 4, "major", {"note": "Composite: physical and life science core with lab per the catalog plan."}),
   ("MATHSCI-ELECT-MT", "Math/Science Elective", 3, "major", {"note": "Composite: any course in the Math or Science General Education Core not already required."}),
   ("CSSEDSITS-ELECT-2", "CS/SE/DS/ITS Elective", 3, "major", {"note": "Composite: any CSCI, ESOF, M, STAT, or ITS course not already required."}),
  ]},
  {"n": 5, "courses": [
   ("CSCI 305", "Concepts of Programming Languages", 3, "major"),
   ("ESOF 322", "Software Engineering", 3, "major"),
   ("STAT 332", "Statistics for Scientists and Engineers", 3, "major"),
   ("CSCI 347", "Data Mining", 3, "major"),
   ("WRIT 321W", "Advanced Technical Writing", 3, "gened",
    {"choices": [("WRIT 321W", "Advanced Technical Writing", 3), ("WRIT 322W", "Advanced Business Writing", 3), ("WRIT 325W", "Writing in the Sciences", 3)], "note": "WRIT 321W, 322W, or 325W."}),
  ]},
  {"n": 6, "courses": [
   ("ESOF 376", "Engineering Secure Software", 3, "major"),
   ("CSCI 361", "Computer Architecture", 3, "major"),
   ("CSCI 440", "Database Systems", 3, "major"),
   ("M 410", "Numerical Computing for Engineering & Science", 3, "major",
    {"choices": [("M 410", "Numerical Computing for Engineering & Science", 3), ("M 417", "Topological Data Analysis", 3), ("CSCI 477", "Computer Modeling and Simulation", 3)], "note": "M 410, M 417, or CSCI 477."}),
  ]},
  {"n": 7, "courses": [
   ("CSCI 486", "Senior Project", 3, "major"),
   ("CSCI 446", "Artificial Intelligence", 3, "major"),
   ("CSCI 466", "Networks", 3, "major"),
   ("CSCI 443", "User Interface Design", 3, "major"),
   ("CSCI 494", "Senior Seminar", 3, "major",
    {"choices": [("CSCI 494", "Senior Seminar", 3), ("CSCI 498", "Internship", 3)], "note": "CSCI 494 or CSCI 498."}),
  ]},
  {"n": 8, "courses": [
   ("CSCI 438", "Theory Of Computation", 3, "major"),
   ("CSCI 460", "Operating Systems", 3, "major"),
   ("CSCI 470", "Web Science", 3, "major"),
   ("CSCI 499W", "Capstone", 3, "major"),
   ("CSCI 447", "Machine Learning", 3, "major"),
  ]},
 ],
})

# ----------------------------------------- Flathead Valley CC ASN Registered Nursing
PLANS.append({
 "id": "fvcc-asn-nursing",
 "inst_name": "Flathead Valley Community College", "inst_city": "Kalispell, MT", "inst_kind": "community_college",
 "degree": "ASN", "major": "Nursing (Registered Nursing)", "catalog_year": "2025-2026",
 "source_url": "https://catalog.fvcc.edu/preview_program.php?catoid=14&poid=2601&returnto=1017&print",
 "total_credits": 73,
 "requirements_only": False,
 "notes": ("FVCC 2025-2026 catalog, Associate of Science in Nursing (Registered Nursing). 73 credits: 14 credits of "
  "required prerequisites (may be taken any semester) plus four nursing semesters. Competitive admission; BIOH 201 "
  "and BIOH 211 require B- or higher; CHMY 121, BIOH 201/211, and BIOM 250 must be taken within 5 years of program "
  "acceptance. The program holds NLN CNEA accreditation and Montana State Board of Nursing approval; graduates are "
  "eligible for the NCLEX-RN. Semester 1 is labeled 'Required Prerequisites (any semester)' per the catalog."),
 "semesters": [
  {"n": 1, "label": "Required Prerequisites (any semester)", "courses": [
   ("BIOH 201NL", "Human Anatomy and Physiology I", 4, "major"),
   ("CHMY 121NL", "Introduction to General Chemistry", 4, "major"),
   ("M 121M", "College Algebra", 3, "major",
    {"choices": [("M 121M", "College Algebra", 3), ("M 140M", "College Math for Healthcare", 3)], "note": "M 121M College Algebra or M 140M College Math for Healthcare."}),
   ("WRIT 101W", "College Writing I", 3, "gened"),
  ]},
  {"n": 2, "label": "First Year - Fall Semester", "courses": [
   ("BIOH 211NL", "Human Anatomy and Physiology II", 4, "major"),
   ("NRSG 230", "Nursing Pharmacology", 3, "major"),
   ("NRSG 231", "Nursing Pharmacology Lab", 2, "major"),
   ("NRSG 232", "Foundations of Nursing", 3, "major"),
   ("NRSG 233", "Foundations of Nursing Laboratory", 3, "major"),
  ]},
  {"n": 3, "label": "First Year - Spring Semester", "courses": [
   ("NRSG 234", "Adult Nursing I", 3, "major"),
   ("NRSG 235", "Adult Nursing I Clinical", 2, "major"),
   ("NRSG 236", "Health and Illness of Maternal Nursing", 2, "major"),
   ("NRSG 237", "Health and Illness of Maternal Nursing Clinical", 1, "major"),
   ("NRSG 256", "Nursing Pathophysiology", 3, "major"),
   ("PSYX 100A", "Introduction to Psychology", 4, "gened"),
  ]},
  {"n": 4, "label": "Second Year - Fall Semester", "courses": [
   ("NRSG 244", "Adult Nursing II", 3, "major"),
   ("NRSG 245", "Adult Nursing II Clinical", 2, "major"),
   ("NRSG 246", "Health and Illness of Child and Family Nursing", 2, "major"),
   ("NRSG 247", "Health and Illness of Child and Family Nursing Clinical", 1, "major"),
   ("NRSG 254", "Mental Health Concepts", 3, "major"),
   ("NRSG 255", "Mental Health Concepts Clinical", 1, "major"),
   ("SOCI 101A", "Introduction to Sociology", 3, "gened"),
  ]},
  {"n": 5, "label": "Second Year - Spring Semester", "courses": [
   ("BIOM 250NL", "Microbiology for Health Sciences", 4, "major"),
   ("NRSG 259", "Adult Nursing III", 3, "major"),
   ("NRSG 260", "Adult Nursing III Lab", 1, "major"),
   ("NRSG 261", "Adult Nursing III Clinical", 2, "major"),
   ("NRSG 266", "Managing Client Care for the RN", 2, "major"),
   ("NRSG 267", "Managing Client Care for the RN Clinical", 2, "major"),
  ]},
 ],
})

# -------------------------------- MSU Billings BS Business Administration (Management Option)
PLANS.append({
 "id": "msubillings-bs-business-administration-management",
 "inst_name": "Montana State University Billings", "inst_city": "Billings, MT", "inst_kind": "university",
 "degree": "BS", "major": "Business Administration (Management Option)", "catalog_year": "2025-2026",
 "source_url": "https://catalog.msubillings.edu/previouscatalogs/2025-2026/undergraduate/college-business/department-business-administration/bs-business-administration-management-option/bs-business-administration-management-option.pdf",
 "total_credits": 120,
 "requirements_only": False,
 "notes": ("MSU Billings 2025-2026 catalog, BS in Business Administration, Management Option. Official Suggested Plan "
  "of Study (8 semesters, 120 credits). Management option requirements (21 cr): BGEN 360, BGEN 440, BMGT 329, "
  "BMGT 353, BMGT 448, BMGT 467, BMKT 342. Restricted electives (9 cr): three upper-division (300/400-level) "
  "College of Business courses (ACTG, BFIN, BGEN, BMGT, BMIS, BMKT) or COMX 320 / COMX 426. Electives are variable "
  "(6-15 credits) as needed to reach 120. WRIT 101, ECNS 201, ECNS 202, M 143, and STAT 216 may also satisfy "
  "General Education requirements. Students should consult advisors before registering each term."),
 "semesters": [
  {"n": 1, "courses": [
   ("WRIT 101", "College Writing I", 3, "gened"),
   ("ECNS 201", "Principles of Microeconomics", 3, "gened"),
   ("GENED-MSBB-1", "General Education", 6, "gened", {"note": "Composite: 6 credits of General Education."}),
   ("ELECT-MSBB-1", "Electives", 3, "elective", {"note": "Composite: 3 credits of electives."}),
  ]},
  {"n": 2, "courses": [
   ("M 143", "Finite Mathematics", 4, "gened"),
   ("ECNS 202", "Principles of Macroeconomics", 3, "gened"),
   ("GENED-MSBB-2", "General Education", 9, "gened", {"note": "Composite: 9 credits of General Education."}),
  ]},
  {"n": 3, "courses": [
   ("STAT 216", "Introduction to Statistics", 4, "gened"),
   ("WRIT 220", "Business & Prof Writing", 3, "gened"),
   ("ACTG 201", "Principles of Fin Acct", 3, "major"),
   ("GENED-MSBB-3", "General Education", 3, "gened", {"note": "Composite: 3 credits of General Education."}),
   ("ELECT-MSBB-2", "Electives", 3, "elective", {"note": "Composite: 3 credits of electives."}),
  ]},
  {"n": 4, "courses": [
   ("ACTG 202", "Principles of Managerial Acct", 3, "major"),
   ("BGEN 235", "Business Law", 3, "major"),
   ("GENED-MSBB-4", "General Education", 7, "gened", {"note": "Composite: 7 credits of General Education."}),
   ("ELECT-MSBB-3", "Electives", 3, "elective", {"note": "Composite: 3 credits of electives."}),
  ]},
  {"n": 5, "courses": [
   ("BGEN 315", "Applied Business Decisions", 3, "major"),
   ("BMGT 335", "Management & Organization", 3, "major"),
   ("BMKT 325", "Principles of Marketing", 3, "major"),
   ("BMGT 322", "Operations Management", 3, "major"),
   ("BMIS 311", "Management Information Systems", 3, "major"),
  ]},
  {"n": 6, "courses": [
   ("BFIN 322", "Business Finance", 3, "major"),
   ("BMKT 342", "Marketing Research", 3, "major"),
   ("REST-MSBB-1", "Restricted Elective", 3, "major", {"choices": [("COMX 320", "Prin of Organizational Comm", 3), ("COMX 426", "Leadership and Communication", 3)], "note": "Restricted elective: COMX 320, COMX 426, or any upper-division (300/400-level) College of Business course (ACTG, BFIN, BGEN, BMGT, BMIS, BMKT) in consultation with an advisor."}),
   ("ELECT-MSBB-4", "Electives", 6, "elective", {"note": "Composite: 6 credits of electives."}),
  ]},
  {"n": 7, "courses": [
   ("BGEN 360", "International Business", 3, "major"),
   ("BMGT 448", "Entrepreneurship", 3, "major"),
   ("BMGT 467", "Supply Chain Management", 3, "major"),
   ("REST-MSBB-2", "Restricted Elective", 3, "major", {"choices": [("COMX 320", "Prin of Organizational Comm", 3), ("COMX 426", "Leadership and Communication", 3)], "note": "Restricted elective: COMX 320, COMX 426, or any upper-division (300/400-level) College of Business course (ACTG, BFIN, BGEN, BMGT, BMIS, BMKT) in consultation with an advisor."}),
   ("REST-MSBB-3", "Restricted Elective", 3, "major", {"choices": [("COMX 320", "Prin of Organizational Comm", 3), ("COMX 426", "Leadership and Communication", 3)], "note": "Restricted elective: COMX 320, COMX 426, or any upper-division (300/400-level) College of Business course (ACTG, BFIN, BGEN, BMGT, BMIS, BMKT) in consultation with an advisor."}),
  ]},
  {"n": 8, "courses": [
   ("BGEN 440", "Business and the Environment", 3, "major"),
   ("BMGT 329", "Human Resource Management", 3, "major"),
   ("BMGT 353", "Organizational Behavior", 3, "major"),
   ("BGEN 499", "Capstone", 3, "major"),
  ]},
 ],
})

# -------------------------------- MSU Billings BSEd Elementary Education (Broadfield Major)
PLANS.append({
 "id": "msubillings-bsed-elementary-education",
 "inst_name": "Montana State University Billings", "inst_city": "Billings, MT", "inst_kind": "university",
 "degree": "BSEd", "major": "Elementary Education (Broadfield Major)", "catalog_year": "2025-2026",
 "source_url": "https://catalog.msubillings.edu/previouscatalogs/2025-2026/undergraduate/college-education/department-educational-theory-practice/bsed-broadfield-major-elementary-education/bsed-broadfield-major-elementary-education.pdf",
 "total_credits": 127,
 "requirements_only": False,
 "notes": ("MSU Billings 2025-2026 catalog, Broadfield Major in Elementary Education, Bachelor of Science in "
  "Education. Official Suggested Plan of Study. IMPORTANT: the catalog states 'Total Minimum Credits 128', but the "
  "published per-semester totals sum to 127 (15+17+16+16+17+17+14+15); COLS 108 The College Experience appears in the "
  "General Education requirements but not in the suggested plan. This seed records the plan exactly as published "
  "with total 127. Area of Concentration electives (15 cr total, in consultation with advisor). Courses marked with "
  "* in the catalog (GPHY 121, SCIN 101/103, NASX 105/205) may satisfy General Education requirements."),
 "semesters": [
  {"n": 1, "courses": [
   ("EDU 105", "Education and Democracy", 3, "major"),
   ("M 130", "Math for Elementary Teachers I", 3, "major"),
   ("WRIT-MSBE-1", "College Writing", 3, "gened", {"choices": [("WRIT 101", "College Writing I", 3), ("WRIT 201", "College Writing II", 3)], "note": "Choose WRIT 101 or WRIT 201."}),
   ("HSTA-MSBE-1", "American History", 3, "gened", {"choices": [("HSTA 101", "American History I", 3), ("HSTA 102", "American History II", 3)], "note": "Choose HSTA 101 or HSTA 102."}),
   ("COMX-MSBE-1", "Communication", 3, "gened", {"choices": [("COMX 111", "Intro to Public Speaking", 3), ("COMX 115", "Intro to Interpersonal Comm", 3)], "note": "Choose COMX 111 or COMX 115."}),
  ]},
  {"n": 2, "courses": [
   ("PSCI-MSBE-1", "American Government", 3, "gened", {"choices": [("PSCI 210", "Intro to American Government", 3), ("PSCI 220", "Intro to Comparative Govt", 3)], "note": "Choose PSCI 210 or PSCI 220."}),
   ("ARTZ 102", "Fund of Art for Elem Teachers", 2, "major"),
   ("EDU 220", "Human Growth & Development", 3, "major"),
   ("EDU 220L", "Human Growth & Development Lab", 0, "major", {"zero": True, "note": "0-credit co-requisite lab with EDU 220."}),
   ("M 131", "Math for Elementary Teacher II", 3, "major"),
   ("MUSI 101", "Enjoyment of Music", 3, "gened"),
   ("GENED-MSBE-1", "Gen Ed Humanities", 3, "gened", {"note": "Composite: 3 credits of Gen Ed Humanities, select from list in consultation with advisor."}),
  ]},
  {"n": 3, "courses": [
   ("EDSP 204", "Intro to Tchng Exceptnl Lrnrs", 3, "major"),
   ("EDU 221", "Educ Psyc & Measurement", 3, "major"),
   ("EDU 270", "Instructional Technology", 3, "major"),
   ("HTH 201", "Health Issues for Educators", 3, "major"),
   ("SCIN 101", "Integrated Sciences I", 4, "major"),
  ]},
  {"n": 4, "courses": [
   ("SCIN 103", "Integrated Sciences II", 4, "major"),
   ("EDU 381", "Curriculum Theory & Design", 3, "major"),
   ("GPHY 121", "Human Geography", 3, "major"),
   ("NASX-MSBE-1", "Native American Studies", 3, "gened", {"choices": [("NASX 105", "Intro Native American Studies", 3), ("NASX 205", "Native Americans in Contmp Soc", 3)], "note": "Choose NASX 105 or NASX 205."}),
   ("EDU 331", "Lit & Literacy for Children", 3, "major"),
  ]},
  {"n": 5, "courses": [
   ("EDU 343", "Strat for Mnging Div Learners", 2, "major"),
   ("EDU 383", "Assessment in Education", 3, "major"),
   ("EDU 397A", "Methods: K-8 Language Arts", 3, "major"),
   ("EDU 397B", "Methods: K-8 Social Studies", 3, "major"),
   ("AOC-MSBE-1", "Area of Concentration electives", 6, "major", {"note": "Composite: 6 credits of Area of Concentration electives in consultation with advisor."}),
  ]},
  {"n": 6, "courses": [
   ("EDSP 410", "Spprtng Div Lrnrs thru Collab", 3, "major"),
   ("EDU 353", "Junior Field Experience", 2, "major"),
   ("EDU 397C", "Methods: K-8 Mathematics", 3, "major"),
   ("EDU 397D", "Methods: K-8 Science", 3, "major"),
   ("EDU 433", "Reflective Practice Tchng Rd", 3, "major"),
   ("AOC-MSBE-2", "Area of Concentration electives", 3, "major", {"note": "Composite: 3 credits of Area of Concentration electives in consultation with advisor."}),
  ]},
  {"n": 7, "courses": [
   ("EDU 397M", "Methods K-8:Intgrtng Arts/Curr", 2, "major"),
   ("HEE 309", "Health Enhancement Strat K-8", 3, "major"),
   ("EDU 438", "Literacy Assessmnt, Diag, Inst", 3, "major"),
   ("AOC-MSBE-3", "Area of Concentration electives", 6, "major", {"note": "Composite: 6 credits of Area of Concentration electives in consultation with advisor."}),
  ]},
  {"n": 8, "courses": [
   ("EDU 406", "Phil, Legal & Ethical Issues", 3, "major"),
   ("EDU 495B", "Student Teaching: K-8", 12, "major"),
  ]},
 ],
})

# -------------------------------- UM Western BS Business Administration (requirements-only)
PLANS.append({
 "id": "umwestern-bs-business-administration",
 "inst_name": "University of Montana Western", "inst_city": "Dillon, MT", "inst_kind": "university",
 "degree": "BS", "major": "Business Administration", "catalog_year": "2024-2025",
 "source_url": "https://catalog.umwestern.edu/preview_program.php?catoid=13&poid=2806&returnto=474",
 "total_credits": 120,
 "requirements_only": True,
 "notes": ("UM Western 2024-2025 archived catalog, BS in Business Administration. No official semester-by-semester "
  "sequence exists; the catalog publishes only a 'Recommended Four Year Course Sequence' at year-level granularity "
  "(freshman/sophomore/junior/senior groupings), so this plan records degree requirements only. Business "
  "Administration Core: 54 credits (BGEN 498 Cooperative Education/Internship is 1-12 credits with 6 required; "
  "capstone is BMGT 499I or BMGT 499G). General Education: 32 credits (includes WRIT 101, a math course, any ECNS "
  "101-299 for Behavioral & Social Sciences, and CAPP 131). A minor/option area of 20-34 credits is required; this "
  "plan uses the Small Business Management minor (32) as the representative option, with 2 elective credits to "
  "bring the degree total to 120. UM Western uses block (Experience One) scheduling with 4-credit courses."),
 "semesters": [
  {"n": 1, "label": "Degree Requirements (no official term sequence)", "courses": [
   ("GENED-UMW-1", "General Education (32 cr; incl. WRIT 101, math, ECNS 101-299, CAPP 131)", 32, "gened", {"note": "Composite: 32 credits of General Education per catalog."}),
   ("ACTG 201", "Principles of Financial Accounting", 4, "major"),
   ("ACTG 202", "Principles of Managerial Accounting", 4, "major"),
   ("BFIN 322", "Business Finance", 4, "major"),
   ("BGEN 217", "Business & Electronic Communications", 4, "major"),
   ("BGEN 235", "Business Law", 4, "major"),
   ("BGEN 253", "Business Statistics & Research", 4, "major"),
   ("BGEN 498", "Cooperative Education/Internship", 6, "major", {"note": "BGEN 498 is 1-12 credits; 6 credits required per catalog."}),
   ("BMGT 322", "Operations Management", 4, "major"),
   ("BMGT 335", "Management & Organization", 4, "major"),
   ("BMKT 325", "Principles of Marketing", 4, "major"),
   ("CAPP 131", "Basic Microsoft Office", 4, "major"),
   ("CAPP 315", "Business Software", 4, "major"),
   ("CAP-UMW-1", "Capstone Experience", 4, "major", {"choices": [("BMGT 499I", "Capstone", 4), ("BMGT 499G", "Capstone", 4)], "note": "Choose one capstone experience: BMGT 499I or BMGT 499G."}),
   ("MINOR-UMW-1", "Option area / minor (e.g. Small Business Management): 32 credits", 32, "major", {"note": "Composite: minor/option area; catalog lists options from 20-34 credits. Small Business Management minor (32) used as representative."}),
   ("ELECT-UMW-1", "Electives to bring degree total to 120", 2, "elective", {"note": "Composite: any college-level courses to reach 120 credits."}),
  ]},
 ],
})

# -------------------------------- Flathead Valley CC AAS Business Administration
PLANS.append({
 "id": "flathead-valley-cc-aas-business-administration",
 "inst_name": "Flathead Valley Community College", "inst_city": "Kalispell, MT", "inst_kind": "community_college",
 "degree": "AAS", "major": "Business Administration", "catalog_year": "2025-2026",
 "source_url": "https://catalog.fvcc.edu/preview_program.php?catoid=14&poid=2574",
 "total_credits": 65,
 "requirements_only": False,
 "notes": ("FVCC 2025-2026 Academic Catalog, Business: Business Administration, AAS. Official required-courses "
  "sequence (4 semesters, 65 credits). An internship (BGEN 298) is required; students apply the prior semester. "
  "All required courses must be taken for a letter grade. Some courses will transfer to four-year colleges as "
  "electives only; students should consult an advisor about transfer."),
 "semesters": [
  {"n": 1, "courses": [
   ("ACTG 201", "Principles of Financial Accounting", 4, "major"),
   ("BGEN 204B", "Business Fundamentals", 3, "major"),
   ("BMGT 205C", "Business Communication", 3, "major"),
   ("CAPP 156", "MS Excel", 3, "major"),
   ("ECNS 201B", "Principles of Microeconomics", 3, "major"),
  ]},
  {"n": 2, "courses": [
   ("ACTG 202", "Principles of Managerial Accounting", 4, "major"),
   ("BFIN 205", "Personal Finance", 3, "major"),
   ("BMGT 215", "Human Resource Management", 3, "major"),
   ("BMKT 225", "Marketing", 3, "major"),
   ("ECNS 202B", "Principles of Macroeconomics", 3, "major"),
  ]},
  {"n": 3, "courses": [
   ("BFIN 215", "Fundamentals of Entrepreneurial Finance", 4, "major"),
   ("BGEN 122", "Business Math", 3, "major"),
   ("BGEN 240", "Introduction to Business Data Analysis", 3, "major"),
   ("BMGT 235", "Management", 3, "major"),
   ("BMIS 211", "Data Analytics I", 4, "major"),
  ]},
  {"n": 4, "courses": [
   ("BGEN 110", "Applied Business Leadership", 3, "major"),
   ("BGEN 235", "Business Law", 4, "major"),
   ("BGEN 298", "Internship", 3, "major"),
   ("BGEN 299", "Capstone", 3, "major"),
   ("BMKT 131", "Introduction to Social Media Marketing", 3, "major"),
  ]},
 ],
})

# -------------------------------- Great Falls College MSU AAS Cybersecurity
PLANS.append({
 "id": "gfcmsu-aas-cybersecurity",
 "inst_name": "Great Falls College Montana State University", "inst_city": "Great Falls, MT", "inst_kind": "community_college",
 "degree": "AAS", "major": "Cybersecurity", "catalog_year": "2026-2027",
 "source_url": "https://catalog.gfcmsu.edu/academic-programs/cybersecurity-aas/cybersecurity-aas.pdf",
 "total_credits": 62,
 "requirements_only": False,
 "notes": ("Great Falls College MSU 2026-2027 Academic Catalog, Cybersecurity AAS. Official program requirements "
  "sequence (4 semesters, 62 credits), offered online. A grade of C or above is required for graduation in all "
  "program courses. Program outcomes based on the NICE Cybersecurity Workforce Framework; prepares students for "
  "CompTIA certifications (A+, Network+, Security+, CySA+, Linux+)."),
 "semesters": [
  {"n": 1, "courses": [
   ("CSCI 100", "Introduction to Programming", 3, "major"),
   ("CSCI 119", "Fundamentals of Artificial Intelligence", 3, "major"),
   ("ITS 280", "Computer Repair and Maintenance", 4, "major"),
   ("M 121", "College Algebra", 3, "gened"),
   ("WRIT-GFC-1", "Writing", 3, "gened", {"choices": [("WRIT 101", "College Writing I", 3), ("WRIT 121", "Introduction to Technical Writing", 3)], "note": "Choose WRIT 101 or WRIT 121."}),
  ]},
  {"n": 2, "courses": [
   ("COMX 115", "Introduction to Interpersonal Communication", 3, "gened"),
   ("ITS 164", "Networking Fundamentals", 3, "major"),
   ("ITS 210", "Network Operating System - Desktop", 3, "major"),
   ("ITS 218", "Network Security", 3, "major"),
   ("ITS 224", "Introduction To Linux", 4, "major"),
  ]},
  {"n": 3, "courses": [
   ("ITS 215", "Network Operating Systems - Directory/Infrastructure", 4, "major"),
   ("ITS 245", "Computer Forensics", 3, "major"),
   ("ITS 271", "Securing Desktop/Mobile Devices", 4, "major"),
   ("ITS 279", "Cloud Systems", 3, "major"),
  ]},
  {"n": 4, "courses": [
   ("BGEN 220", "Business Ethics and Social Responsibility", 3, "gened"),
   ("ITS 222", "Enterprise Security", 3, "major"),
   ("ITS 274", "Ethical Hacking and Network Defense", 3, "major"),
   ("ITS 277", "Software Assurance and File System Internals", 4, "major"),
   ("ITS-GFC-1", "Internship or Capstone", 3, "major", {"choices": [("ITS 298", "Internship", 3), ("ITS 299", "Capstone", 3)], "note": "Select one: ITS 298 Internship or ITS 299 Capstone."}),
  ]},
 ],
})

# -------------------------------- Miles CC Associate of Science in Nursing
PLANS.append({
 "id": "miles-cc-asn-nursing",
 "inst_name": "Miles Community College", "inst_city": "Miles City, MT", "inst_kind": "community_college",
 "degree": "ASN", "major": "Nursing", "catalog_year": "2026-2027",
 "source_url": "https://content.milescc.edu/DownloadFiles/WebCatalogs/Web_CatalogCurrent.pdf",
 "total_credits": 72,
 "requirements_only": False,
 "notes": ("Miles Community College 2026-2027 Academic Catalog & Student Handbook, Associate of Science in Nursing. "
  "Program course requirements presented in sequence (catalog page 128-129); block 1 = required prerequisites, "
  "blocks 2-5 = the four program semesters. Program total 72 credits. ACEN-accredited, Montana State Board of "
  "Nursing approved, prepares graduates for RN licensure. All prerequisite courses require a B- or higher with a "
  "selective prerequisite GPA of 2.75 for program admission; science courses must be less than five years old."),
 "semesters": [
  {"n": 1, "label": "Prerequisites", "courses": [
   ("CHMY 121", "Intro To General Chemistry", 3, "major"),
   ("CHMY 122", "Intro To General Chemistry Lab", 1, "major"),
   ("BIOH 201", "Human Anatomy & Physiology I", 3, "major"),
   ("BIOH 202", "Human Anatomy & Physiology I Lab", 1, "major"),
   ("WRIT 101", "College Writing I", 3, "gened"),
   ("M 140", "College Math for Healthcare", 3, "gened"),
  ]},
  {"n": 2, "courses": [
   ("BIOH 211", "Human Anatomy & Physiology II", 3, "major"),
   ("BIOH 212", "Human Anatomy & Physiology II Lab", 1, "major"),
   ("PSYX 100", "Intro to Psychology", 3, "gened"),
   ("NRSG 248", "Pharmacology I", 1, "major"),
   ("NRSG 268", "Pathophysiology I", 2, "major"),
   ("NRSG 232", "Foundations of Nursing", 3, "major"),
   ("NRSG 233", "Foundations of Nursing Lab", 3, "major"),
  ]},
  {"n": 3, "courses": [
   ("NRSG 231", "Nursing Pharmacology Lab", 2, "major"),
   ("NRSG 234", "Adult Nursing I", 3, "major"),
   ("NRSG 235", "Adult Nursing I Clinical", 2, "major"),
   ("NRSG 249", "Pharmacology II", 2, "major"),
   ("NRSG 269", "Pathophysiology II", 1, "major"),
   ("SOCI 101", "Intro to Sociology", 3, "gened"),
  ]},
  {"n": 4, "courses": [
   ("NRSG 244", "Adult Nursing II", 3, "major"),
   ("NRSG 245", "Adult Nursing II Lab", 2, "major"),
   ("NRSG 236", "Health and Illness of Maternal Nursing", 2, "major"),
   ("NRSG 237", "Health and Illness of Maternal Nursing Clinical", 1, "major"),
   ("BIOM 250", "Microbiology for Health Sciences", 3, "major"),
   ("BIOM 251", "Microbiology for Health Sciences Lab", 1, "major"),
   ("NRSG 254", "Mental Health Concepts", 3, "major"),
   ("NRSG 255", "Mental Health Concepts Clinical", 1, "major"),
  ]},
  {"n": 5, "courses": [
   ("NRSG 259", "Adult Nursing III", 3, "major"),
   ("NRSG 261", "Adult Nursing III Clinical", 3, "major"),
   ("NRSG 246", "Health & Illness of Child & Family Nursing", 2, "major"),
   ("NRSG 247", "Health & Illness of Child & Family Nursing Clinical", 1, "major"),
   ("NRSG 266", "Managing Client Care for the RN", 2, "major"),
   ("NRSG 267", "Managing Client Care for the RN Clinical", 2, "major"),
  ]},
 ],
})

# -------------------------------- Miles CC AAS Accounting Technology
PLANS.append({
 "id": "miles-cc-aas-accounting-technology",
 "inst_name": "Miles Community College", "inst_city": "Miles City, MT", "inst_kind": "community_college",
 "degree": "AAS", "major": "Accounting Technology", "catalog_year": "2026-2027",
 "source_url": "https://content.milescc.edu/DownloadFiles/WebCatalogs/Web_CatalogCurrent.pdf",
 "total_credits": 60,
 "requirements_only": False,
 "notes": ("Miles Community College 2026-2027 Academic Catalog & Student Handbook, A.A.S. Accounting Technology. "
  "Program course requirements presented in sequence (catalog page 130), program total 60 credits. Prepares students "
  "for general accounting occupations; can be completed online. Students select a written communication elective "
  "(WRIT 122 preferred), an oral communication elective, a mathematics elective (M 108 used as representative), "
  "and 6 credits of electives in consultation with an advisor."),
 "semesters": [
  {"n": 1, "courses": [
   ("CAPP 131", "Basic MS Office", 3, "major"),
   ("WRIT-MCCA-1", "Written Communication", 3, "gened", {"choices": [("WRIT 122", "Intro to Business Writing", 3), ("WRIT-ELECTIVE", "Written Communication elective", 3)], "note": "WRIT 122 preferred, or another written communication elective."}),
   ("M 108", "Business Math", 3, "gened", {"note": "M 108 or another mathematics elective."}),
   ("ACTG 201", "Principles of Financial Accounting", 4, "major"),
   ("ELECT-MCCA-1", "Electives", 3, "elective", {"note": "Composite: 3 credits of electives."}),
  ]},
  {"n": 2, "courses": [
   ("ORAL-MCCA-1", "Oral Communication elective", 3, "gened", {"note": "Composite: 3 credits of oral communication elective."}),
   ("CAPP 151", "MS Office", 3, "major"),
   ("ACTG 202", "Principles of Managerial Accounting", 4, "major"),
   ("ACTG 180", "Payroll Accounting", 3, "major"),
   ("COLS 111", "Career Development and Interpersonal Skills", 1, "major"),
  ]},
  {"n": 3, "courses": [
   ("ACTG 211", "Income Tax Fundamentals", 3, "major"),
   ("BMGT 215", "Human Resource Management", 3, "major"),
   ("BMKT 225", "Marketing", 3, "major"),
   ("BGEN 235", "Business Law", 3, "major"),
   ("CAPP 156", "MS Excel", 3, "major"),
  ]},
  {"n": 4, "courses": [
   ("BFIN 205", "Personal Finance", 3, "major"),
   ("ACTG 215", "Found. of Government & Not for Profit Accounting", 3, "major"),
   ("ACTG 205", "Computerized Accounting", 3, "major"),
   ("BGEN 298", "Business Internship", 3, "major"),
   ("ELECT-MCCA-2", "Electives", 3, "elective", {"note": "Composite: 3 credits of electives."}),
  ]},
 ],
})

# -------------------------------- Missoula College AAS Business Management (requirements-only)
PLANS.append({
 "id": "missoula-college-aas-business-management",
 "inst_name": "Missoula College - University of Montana", "inst_city": "Missoula, MT", "inst_kind": "community_college",
 "degree": "AAS", "major": "Business Management", "catalog_year": "2024-2025",
 "source_url": "https://catalog.umt.edu/archived-catalogs/2024-2025/colleges-schools-programs/missoula-college/business-technology/aas-business-management/aas-business-management.pdf",
 "total_credits": 65,
 "requirements_only": True,
 "notes": ("UM 2024-2025 archived catalog, Missoula College Business Management AAS. The catalog publishes course "
  "requirements (65 hours) but no official semester-by-semester sequence, so this plan records requirements only. "
  "Catalog quirk: BMKT 265 Social Media Strategy & Management is listed both as a required course and as the "
  "alternate for the MART 232 slot; recorded per the catalog. Choice slots recorded at catalog minimum credits. "
  "A grade of C or better is required in all program courses."),
 "semesters": [
  {"n": 1, "label": "Degree Requirements (no official term sequence)", "courses": [
   ("ACTG 101", "Accounting Procedures I", 3, "major"),
   ("ACTG 102", "Accounting Procedures II", 3, "major"),
   ("ACTG 130", "Applied Accounting & Decision Making", 3, "major"),
   ("BGEN 105S", "Introduction to Business", 3, "major"),
   ("BGEN 215", "Career Readiness", 3, "major"),
   ("BGEN 220E", "Business Ethics and Social Responsibility", 3, "major"),
   ("BFIN 205S", "Personal Finance", 3, "major"),
   ("BMGT 235", "Management", 3, "major"),
   ("BMGT 245", "Customer Service Management", 3, "major"),
   ("BMGT 298", "Management Internship", 2, "major"),
   ("BMGT 299", "Capstone: Entrepreneurship", 3, "major"),
   ("BMKT 112", "Applied Sales", 3, "major"),
   ("BMKT 240", "Advertising", 3, "major"),
   ("BMKT 265", "Social Media Strategy & Management", 3, "major"),
   ("COMX 250", "Introduction to Public Relations", 3, "major"),
   ("ECNS 201S", "Principles of Microeconomics", 3, "gened"),
   ("M 115", "Probability and Linear Mathematics", 3, "gened"),
   ("MART 214", "Digital Publishing & Design", 3, "major"),
   ("WRIT 101", "College Writing I", 3, "gened"),
   ("BMKT-UMC-1", "Marketing or Sustainability", 3, "major", {"choices": [("BMKT 225", "Marketing", 3), ("BGEN 160S", "Issues in Sustainability", 3)], "note": "Choose BMKT 225 or BGEN 160S."}),
   ("TECH-UMC-1", "Computer Modeling or Excel", 3, "major", {"choices": [("CSCI 172", "Intro to Computer Modeling", 3), ("CAPP 156", "MS Excel", 3)], "note": "Choose CSCI 172 or CAPP 156."}),
   ("MART-UMC-1", "Interactive Web or Social Media", 3, "major", {"choices": [("MART 232", "Interactive Web II", 3), ("BMKT 265", "Social Media Strategy & Management", 3)], "note": "Choose MART 232 or BMKT 265 (catalog also lists BMKT 265 as a required course; recorded as published)."}),
  ]},
 ],
})
