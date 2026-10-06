# Market Tab Redesign Plan — "Real Commerce" (2026-09-22)

Source reports: `qa/market-research.md` (real-app UI: FB Marketplace, OfferUp, Mercari, Depop, Poshmark, eBay) + `qa/market-audit.md` (current code map). Read both fully before coding.

## Hard rules (from ~/AGENTS.md)
- Classic IIFE scripts, deterministic load order, NO ES modules, no bundler.
- NEVER name a local/param `t` (shadows the translation helper). Use `th`, `el`, `exp`.
- Theming via `body.dark` ONLY. Volt accent `#C6F135`. NO purple hexes (`#7C3AED`-family) anywhere.
- Any overlay class that sets `display` must also define `.cls[hidden]{display:none}`.
- Preserve `.phone>*{min-width:0}`.
- Fixed transient UI: `position:fixed`, viewport-anchored, docked to the 480px column via `max()` patterns.
- Global Escape in app.js defers when `.mkzoom` is open — VERIFY this code exists; if missing, add the defer (do not break the lightbox's own Escape).
- SCOPE: `js/market.js`, `styles.css` market sections, market i18n strings ONLY. Do NOT touch the tab bar, other tabs, global chrome, or store.js.

## 1. Listing cards (biggest visual change)
- `.mktile-media`: `aspect-ratio:1/1` (square, like OfferUp/Mercari/Depop), photo radius ~10px.
- Card body order: **price FIRST** — bold ~16px (`.money`, keep volt-ink on dark / strong ink on light); then title as **2-line clamp** (`-webkit-line-clamp:2`, regular weight, 14px); then ONE gray meta line: `{area} · {distance}` (condition stays detail-only, per real apps).
- Type badge: DELETE the pastel `b-SELL/b-BUY/b-SWAP/b-BORROW/b-FREE` rules. New single `.mkbadge` family: small uppercase pill, white bg + dark ink (light mode) / dark surface + light ink (dark mode), hairline border. Position: top-left on photo (keep existing placement). SELL variant `.mkbadge-volt` uses volt `#C6F135` bg + `#17200a` ink (brand accent, commerce-fresh). SOLD (if ever): dimmed photo + `.mkbadge-sold` banner overlay. Badge text uses the i18n type label (`market.type.X`), not raw uppercase key.
- No-photo fallback `.mktile-ico`: replace 46px clay svg with a neutral monochrome image/placeholder glyph (inline SVG, currentColor, low opacity).
- Keep the dashed Sample badge (honest labeling) but restyle it into the neutral family.
- Sponsored interleave: keep mechanics + "Sponsored"/"Demo ad" labels; restyle labels flat text (industry standard: quiet disclosure, not pills).

## 2. Filter row (professional)
- Type chips: TEXT-ONLY + counts, e.g. `All 12`, `For Sale 5`, `Wanted 2`, `Swap 1`, `Borrow 1`, `Free 3`. Remove `HUB.icons.icon(TYPE_ICON[ty])` clay icons from chips. Horizontally scrollable (keep `.chips` behavior). Active chip: volt fill (brand); inactive: outlined neutral.
- Keep the search bar (top) and radius segmented control; restyle to clean commerce controls. De-emoji `market.searchPh` (value edit: "Search listings…").
- Scope pill: de-emoji (value edit, drop 📍), keep honest "Within N mi · sorted by distance" text.

## 3. Honest demo banner
- Above the grid, when sample listings are present: a slim neutral banner — new key `market.demoNote` = "Sample listings — post yours to start selling" (es/ne/hi translations required). Subtle, one line, info styling (not a warning color).

## 4. Listing detail sheet
- Photo carousel: keep the water-crystal flow mechanism + pinch-zoom lightbox, but add a **photo counter badge** ("1 / 4", new key pattern `market.d.photoOf` already exists — reuse) and raise media height to ~260px. Dots optional; counter is enough.
- Price block: ~22px bold, directly under photos.
- Title: 16–17px, medium weight.
- **Specs grid**: 2-column label/value rows — Condition (only if present), Category (type label), Posted (time-ago), Distance. Use `.kv` rows or a proper grid; professional, no emoji.
- **Seller card**: avatar, name, "{n} listings" (REAL count from store — compute, do not invent), posted-ago. NO invented ratings, NO invented response times (honesty rule). New key `market.d.listings` = "{n} listings".
- Description block, then existing safety sections (meetup spots — de-emoji the 📍, keep the "sample suggestions" honest hint), then comments (existing).
- **Sticky CTA bar**: "Message seller" as a sticky bottom bar inside the sheet (primary volt button, full-width, safe-area padding). Read `ui.openSheet` in `js/app.js` first to anchor it correctly inside the sheet scroll container — it must not escape the 480px column or cover sheet content (add bottom padding to sheet body).
- **"You may also like"**: horizontal scroll row of up to 6 same-type listings (exclude self), compact tiles reusing the new card design. New key `market.d.similar` = "You may also like".

## 5. Post flow
- Type chips: text-only (same as filter chips, no clay icons).
- De-emoji chrome copy (value edits): `market.p.addPhotos`, `market.p.posted` ("Listing posted"), keep all honesty hints (`photosHint`, `areaHint`).
- Restyle to the professional tone; keep the 4-photo pipeline, char counter, two-tap nothing (publish is one tap + validation toasts, unchanged).

## 6. Float overlap fix (from his screenshot)
- Add `padding-bottom:calc(210px + env(safe-area-inset-bottom))` to `#view-market` (or `.mkgrid`) so the last card row clears the Ask pill (~100px) and the Post FAB (~152px).
- `#mkPostBtn`: REMOVE the inline pill override (`border-radius:999px;padding:0 22px;font-size:16px;font-weight:800` at market.js:155). Fall back to the shared `.fab` styling — verify `.fab` (styles.css ~656) is a proper circular volt button with a "+" glyph; if not, style `#mkPostBtn` as a restrained circular volt FAB (56px, "+", subtle shadow). It must remain `position:fixed` + column-docked.
- Check ≤360px widths: Ask pill + Post FAB must not collide.

## 7. Emoji purge (chrome copy — VALUE edits, not new keys)
`market.searchPh`, `market.scopePill`, `market.d.showPhone`, `market.d.msgSeller`, `market.d.report`, `market.d.block`, `market.d.delete`, `market.p.addPhotos`, `market.p.posted`, `market.d.noComments`, `market.emptyPost`, meetup `📍` (market.js:200), photo `🔍` (market.js:296 → replace with a small neutral magnifier SVG or drop), phone reveal `📞` (market.js:272 → drop, keep the number card). Seed titles in store.js are USER-GENERATED content — LEAVE THEM.

## 8. i18n
- New keys (MAX 3): `market.demoNote`, `market.d.similar`, `market.d.listings`.
- Value edits listed in §7 + §2.
- en/es/ne/hi in `js/i18n.js` + ALL 24 `data/locales/*.json`. Sorted values. Sibling keys verified intact in every file.
- `kh` recomputed LAST via djb2. Verify with the repo's existing hash script/pattern (check how i18n.js or a script computes it — the lazy-locale hash was `1pssdwc`; recompute and confirm all locales load).

## 9. QA (before deploy — no exceptions)
- `node --check js/market.js`; CSS braces balanced; no `t`-shadowing (grep for suspicious `let t|const t|=>t` in edited regions).
- Fresh-profile boot, ZERO uncaught console errors (wipe /tmp/hubqa-* before each run; CDP headless pattern in `qa/`; seed `profile.name`, hide `#wlcmHost`).
- 390×844 mobile emulation, dark + light: grid render, chip filter switching, search typing, radius change, detail open, carousel swipe, lightbox (pinch/double-tap/Escape), post flow open + validation, no horizontal overflow, no float overlap at top/middle/bottom scroll positions.
- Screenshots before/after in `qa/` (e.g. `market-new-grid-dark.png`, `market-new-detail-dark.png`, light variants).
- Deploy via surge ONLY after QA passes; curl-verify HTTP 200 on `styles.css`, `js/market.js`, and one locale JSON.

## 10. Handoff back must include
Research summary (which real-app patterns were adopted), files changed, QA pass count + error count, screenshots, deploy verification, anything simplified/left out, and the standing caveats: browser-local demo data only (real cross-device listings need a backend); final look-and-feel verdict is PraBin's physical-device check — explicitly ask him to review the new Market tab on his iPhone.
