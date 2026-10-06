# Marketplace Tab Code Audit — Onaro HUB (2026-09-22)

## 1. View map
- **Grid (browse)** — `market.js` `render(el)` (L118–160). Mounted into `#view-market` (`index.html:32`); `HUB.views.market.render` registered at `market.js:445`; `app.js` `showTab()` re-renders each tab switch. DOM: `<h1>` (market.title), `.sub` (market.sub), "Search radius" label + `#mkRadius.seg.seg-compact` (6 radius buttons), `.field > #mkSearch.input`, `.chips` (ALL + 5 type chips), `#mkScopePill.scope-pill`, `.mkgrid#mkList` (two-column), `#mkPostBtn.fab` (full-width pill via inline style override).
- **Detail** — bottom sheet `openDetail(id)` (market.js L194–290) via `ui.openSheet(html)` (L268); `closeOverlays()` (L111–116) closes sheet + search/pulse/notifications/chat so overlays never stack. Contents: h2 title, `badge b-<TYPE>` + sample badge, photo flow carousel, price, desc, kv rows (location/distance/condition), seller row, `📞 Show seller's number`, `💬 Message seller` (deep-links `HUB.chat.openWith`), Report/Block/Delete ghosts, `meetupSpotsHTML()` safe-meetup, `HUB.trust.safeMeetupHTML()`, comments + askbox.
- **Post flow** — bottom sheet `openPost()` (market.js L350–445). Fields: title, type chips (toggle price/swap/borrow fields), condition select, desc (500-char counter), area select, photo picker (max 4, downscale ~1000px JPEG, per-photo ✕), phone. Publish → `store.add('listings')`, close, toast, re-render grid.
- **Photo viewer** — `openLightbox(src)` (market.js L295–350), `.mkzoom` (styles.css:1416–1423): `position:fixed;inset:0;z-index:300`, pinch (1–4×), double-tap 2.5×, pan when zoomed, wheel zoom, ✕/backdrop/Escape dismiss. Exposed as `HUB.mkZoom.open`.
- **Detail carousel** — `photoFlowHTML()` (market.js L292–299): shared groups water-crystal carousel (`.flowwrap > .flow#mkPhotoFlow`, `.gcard.mkphoto`, 200px media, styles.css:1415), tilt/drift via `HUB.cgroups.bindCarousels`.
- **Filters/sort/search**: `#mkRadius` seg control, `#mkSearch` (live re-render + `keepFocus()`), type chips, scope pill, hardcoded distance-then-newest sort (`filtered()`, market.js:104–110). Empty state `.empty` with clay `intent-free` icon. Sponsored cards interleave every 5th via `HUB.ads.interleaveFeed` (market.js:173–177), full-row via `.mkgrid>.item{grid-column:1/-1}` (styles.css:1402).

## 2. "Cartoonish" inventory (exact references)
- Type badges `badge b-SELL/b-BUY/b-SWAP/b-BORROW/b-FREE` (market.js:245, :215): pastel candy pills — BUY `#EFF6FF/#1D4ED8`, SWAP `#FFFBEB/#B45309`, BORROW `#F0FDFA/#0F766E`, FREE `#F7FEE7/#4D7C0F` (styles.css:332–347 + dark variants). SELL is accent-soft (fine); other four are toy-store.
- Clay 3D intent icons (verified: `icons/intent-free.png` is glossy clay gift box): filter chips (market.js:128 `HUB.icons.icon(TYPE_ICON[ty])`), empty state `.empty-ico` (market.js:182), tile fallback `.mktile-ico` 46px clay svg (market.js:238; styles.css:1408–1409).
- Emoji in SEED titles (store.js:96–101): `📚 Calculus textbook`, `🖥️ 24" Monitor`, `💡 Desk lamp`, `📦 Moving boxes`, `🪴 Cherry tomato seedlings`, `🚲 City commuter bike`. → DECISION: treat as user-generated content, LEAVE (do not touch store.js; scope is market surface only).
- Emoji in CHROME copy (purge): `market.searchPh`=`🔍 Search listings…`; `market.scopePill`=`📍 {scope} · sorted by distance`; `market.d.showPhone`=`📞 …`; `market.d.msgSeller`=`💬 …`; `market.d.report`=`🚩 …`; `market.d.block`=`⛔ …`; `market.d.delete`=`🗑 …`; `market.p.addPhotos`=`📷 …`; `market.emptyPost`=`＋ Post a listing`; `market.p.posted`=`Listing posted 🎉`; `market.d.noComments`=`No comments yet — ask a question!`; meetup spots `📍` (market.js:200); photo zoom `🔍` (market.js:296); phone reveal `📞` (market.js:272).
- `＋ Post` pill FAB (market.js:155, inline `border-radius:999px;padding:0 22px;font-size:16px;font-weight:800`) — chunky toy button.
- Pastel hexes hardcoded, not tokens (styles.css:334–337, 344–347). No banned purple. No `t`-shadowing, no data-theme violations. `body.dark` + volt used correctly.
- Tab bar fallback icon `index.html:41` `<span class="tab-ico">🔄</span>` — out of scope (do not touch tab bar).

## 3. Keepers
- Two-column `.mkgrid` (styles.css:1401), 4:3 media tiles → will become square.
- 4-photo downscale pipeline + session honesty copy; `.mkzoom` lightbox mechanics; water-crystal carousel mechanism; distance sort + radius control + scope pill; `ui.openSheet` + `closeOverlays()` hygiene; two-tap delete; comments; blocked-seller filtering.
- Honest labeling: `sample:true` seeds → dashed `badge.sample` (market.js:248, :215 via `ui.sampleBadge`); meetup spots labeled samples (`market.d.meetupHint`); user listings `dist:0.1`; seed distances deterministic illustrative (market.js:64–68).
- CSS map: `.mkgrid` 1401–1402, `.mktile` 1403–1414, `.mkphoto-media` 1415, `.mkzoom` 1416–1423, `.fab` ~656, `.askpill` 751–752, `#view-market .fab` override ~885, sheet host ~572.

## 4. Layout hazards
- **Float-over-cards bug CONFIRMED**: `#view-market .fab{bottom:calc(152px + safe-area)}` lifts ＋Post above `.askpill` (fixed, bottom:100px), but grid has NO bottom clearance — last row scrolls under both floats. FIX: `padding-bottom:calc(210px + env(safe-area-inset-bottom))` on `#view-market` or `.mkgrid`.
- Docking correct: `.fab{right:max(20px,calc(50% - 220px))}`, `.askpill{left:max(16px,calc(50% - 232px))}`, both `position:fixed`. z-stack: fab 25 < askpill 32 < sheet 70 < mkzoom 300. Good.
- ≤360px screens: ask pill + Post pill can visually crowd; the 152px lift mitigates.
- VERIFY: app.js global Escape handler actually defers when `.mkzoom` open (AGENTS.md documents the rule; code not confirmed).
- VERIFY: `.photo-prev/.ph-thumb` CSS exists with sane constraints.
- `.mktile-body h3` single-line ellipsis (styles.css:1413) → upgrade to 2-line clamp.

## 5. Sample data
- `store.js:96–101` `listings:[...]` (6 seeds, all `sample:true`). Fields: id, type, title, photos[] (`market/photos/*.webp` real bundled), price, swapFor/borrowFor, desc, campus/area, seller, phone, createdAt, sample:true. No `dist` → `distOf()` fabricates 0.2–3.0 mi hash distance (disclosed by Sample badge). No seed has `condition` → detail condition kv renders only when present. store.js:235 purges samples on some path.

## 6. i18n surface (92 market.* keys)
Header/filter: title, sub, searchRadius, radius.1/.5/.10/.20/.25/.city, searchPh, all, type.SELL/BUY/SWAP/BORROW/FREE, scopeMi, scopePill, nearYou, miAway. Empty: emptyTitle, emptyWithin, emptySub, widen, emptyPost. Post CTA: postAria, postShort. Price: price.wantBuy, price.lookingBuy, price.swapFor, price.swap, price.borrow, price.askme, price.free. Detail (market.d.*): location, distance, condition, posted, showPhone, noNumber, msgSeller, report, block, delete, confirmDelete, deleted, comments, noComments, commentPh, meetupTitle, meetupHint, spot.1–5, chatNotReady, trustNotReady, closePhoto, photoOf. Post (market.p.*): title, titleLabel, titlePh, typeLabel, priceLabel, pricePh, swapLabel, swapPh, borrowLabel, borrowPh, condLabel, condChoose, cond.new/likenew/good/fair, descLabel, descPh, areaLabel, areaHint, photosLabel, addPhotos, photosCount, photosHint, maxPhotos, removePhoto, phoneLabel, phonePh, publish, needTitle, needType, posted. Mirrored in es/ne/hi (i18n.js:1967+).

## Punch-list (by visual impact)
1. Neutral badge family replacing pastel b-TYPE pills.
2. Clay intent icons → flat/monochrome; neutral photo placeholder for tile fallback.
3. Emoji purge from chrome copy (value edits).
4. Float-over-cards: bottom clearance.
5. Restyle ＋Post FAB → standard commerce CTA.
6. Persistent honest "Sample listings" banner above grid.
7. Pastel hexes → theme tokens.
8. Verify app.js Escape defer for .mkzoom; verify .photo-prev/.ph-thumb CSS.
9. KEEP: grid, photo pipeline, lightbox, carousel, distance sort, sheet hygiene, delete confirm, comments, honesty labels.
