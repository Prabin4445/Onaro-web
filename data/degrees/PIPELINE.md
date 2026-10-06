# Degree Plan Tracker — data pipeline

## Flow
`~/workspace/degree-tracker/seed/*.json` (collector output, official catalogs only)
→ `python3 build.py [seed_dir]` → `index.json` + `<slug>.json` (runtime files)

## Rules
- Never hand-edit runtime files; regenerate via build.py.
- build.py validates (required fields, credit sums, duplicate codes, prereq
  existence) and computes `xfer` transfer lists from shared TCCNS numbers.
- Warnings never block; invalid plans are skipped with a logged reason.
- Honesty: collectors record source_url + catalog_year per plan; blocked
  catalogs are noted, never bypassed or filled from memory.
- Schema: ~/workspace/degree-tracker/SCHEMA.md
- Semester-number gate (2026-10-01): every semester MUST carry a positive
  integer `n`, unique within the plan. build.py normalizes missing/invalid
  `n` to 1-based catalog order (after the content_hash check, so stored
  hashes stay valid) and rejects duplicate `n`. slot_id is derived as
  `s{n}-{course_index}`, so this gate makes duplicate slot_ids impossible
  by construction; a defensive duplicate check still drops the plan if the
  invariant is ever violated.
- Stale runtime files (slugs no longer in the index, e.g. from pulled or
  renamed plans) are deleted on each build.
