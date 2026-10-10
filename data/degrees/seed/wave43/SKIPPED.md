# Wave43 SKIPPED — Judson University (2026-2027 catalog)

Seeded: 1 plan (`judson-ba-architecture`, 129 cr, verified against live catalog 2026-10-10).

## Skipped (3) — extraction incomplete vs official requirements

Judson's catalog states **120 degree hours are required for bachelor's degrees**
(official transfer-policy page). The extracted four-year grids for these programs
fall well short and could not be verified against their live catalog pages
(catalog.judsonu.edu returned empty/202 responses for these pages on 2026-10-10).

| Program | Transcribed sum | Declared total | Reason |
|---|---|---|---|
| Graphic Design BFA | 101 cr | 120 (Judson bachelor's minimum) | Extraction ALSO contradicts the live catalog: extracted GDN-prefix curriculum (Typography I/II, Graphic Design III/IV) vs live catalog's DES-prefix curriculum (DES228, DES321/322, DES420, DES496/497) declaring "Total Hours 121-122". Stale/mismatched extraction. |
| Management BA | 97 cr | 120 (Judson bachelor's minimum) | 23 credits unaccounted; live page could not be fetched to verify. |
| Nursing (Pre-Licensure) BSN | 113 cr | 120 (Judson bachelor's minimum) | 7 credits unaccounted; live page could not be fetched to verify. |

Recommendation: route all three to the live-browser re-extraction queue
(`~/workspace/degree-tracker/workstreamA-browser-queue.md`). Do not seed from
the current extraction — a missing plan is better than a wrong plan.
