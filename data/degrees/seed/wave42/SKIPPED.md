# Wave 42 — Millersville University (2026-10-09): ALL 6 PROGRAMS SKIPPED

Source: `~/workspace/degree-tracker/browser-extracts/millersville-2025-2026.json`

The browser extract contains program-level metadata ONLY (program name, degree,
catalog year 2025-2026, total credits 120, source URL, notes). It contains NO
course-level data: no course codes, no titles, no per-course credits.

The strict validator requires every course to carry numeric credits and the
credit sum to equal the declared total exactly. There is no way to seed these
plans without inventing course data, which is prohibited.

Skipped programs (all requirements_only, all 120 credits, catalog 2025-2026):
1. Business Administration - General Business (BS) — catalog pages show requirement-block totals only, no per-course credits
2. Social Work (BA) — major 60 credits; term-by-term PDF existed but page 2 unreadable
3. Nursing / RN-to-BSN (BSN) — 30 lower-division credits awarded on associate degree; 31 credits across 9 required courses (course list not captured)
4. Computer Science (BS) — major 52 credits; per-course credits not listed on catalog pages
5. Psychology (BA) — major 29-39 credits; per-course credits not listed except PSY 100 (3)
6. Early Childhood Education (BSEd) — PreK-Grade 4; major 54 + professional ed 21; per-course credits not listed

Recommendation: route to the live-browser delegation queue for re-extraction
with per-course credit capture (catalog.millersville.edu curriculum pages).
