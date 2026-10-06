# Mobile Marketplace UI Research — FB Marketplace / OfferUp / Mercari / Depop / Poshmark / eBay (2025–2026)

## 1. Listing card anatomy (grid)
Universal: 2-column grid, FLAT cards (no borders/shadows), photo-dominant. Photo square (OfferUp/Mercari/Depop/Poshmark) or ~4:3 (FB). Below photo: **price FIRST in bold ~15–16px** (price is #1, not title) → title truncated to **2 lines**, regular weight → one gray metadata row: city/location (FB), distance + city (OfferUp, e.g. "3 mi · Dallas"), shipping line (Mercari "Free shipping"; eBay 2025: delivery-range estimates and drive-time-to-pickup ON the card). Photo corner radius ~8–12px, text on same surface. Condition is NOT on grid cards (detail only). FREE → "FREE" in price slot. SOLD → dimmed photo + "SOLD" overlay banner/tag on photo. Depop is the exception: title first, then price; also shows like counts. OfferUp: "Ships to you" truck badge bottom-left on photo for shippable listings. Depop supports video slots (play indicator on card).

**Rule: state overlays (sold/free/video) go ON the photo; commerce info (price, shipping) goes below it.**

## 2. Badge systems
- Condition badges on-grid are rare (Poshmark: detail+filters only; OfferUp: small gray text for some categories; eBay 2025 "Top-Service" badge for fast+free shipping + trusted sellers).
- Shipping badges: OfferUp "Ships to you" (bottom-left on photo); Mercari "Free shipping" as text under price; eBay free/fast shipping text + delivery dates on card.
- Promoted/sponsored: small FLAT TEXT label, never a colored pill — disclosure stays visually quiet (eBay "Sponsored", OfferUp "Promoted").
- Verification badges live on the DETAIL seller card, never grid cards.

## 3. Filter/sort bar
- Horizontally scrollable TEXT-ONLY chip row under the search bar (rounded pills; active = filled/colored, inactive = outlined). Chips like "Price", "Condition", "Distance". FB uses a single "Filters" button → bottom sheet instead. OfferUp puts distance in the chip row.
- Category = filter-sheet drilldown, not a top-level chip. Mercari trend: AI auto-suggests category from photo.
- Distance/radius: first-class filter for local apps (slider or preset rings 5/10/25/50+ mi in a sheet).
- Sort: single "Sort: [Relevance ▾]" dropdown. Options: Recommended, Newest, Price low→high, Price high→low, Distance/Nearest (local), Ending soonest (eBay).

## 4. Search UX
- Search bar = topmost persistent element, rounded pill under header; location selector beside/below (current city, tap to change radius).
- Placeholder: short casual ("Search Marketplace"). Tapping field → recent searches (with × clear), trending searches, category shortcut chips. Autocomplete with thumbnails standard on eBay/Mercari.

## 5. Listing detail page anatomy (top → bottom)
1. Photo area: full-bleed swipeable carousel, square–4:3; dot/page indicators or "1/8" counter (Poshmark/Mercari style); tap → fullscreen zoom; back/share/heart overlay top corners. Depop: video as first slot.
2. Price block: large bold ~22–24px; struck-through original + discount % (Poshmark); "Free shipping"/shipping line under; eBay: bid + time left or BIN + "Best Offer accepted".
3. Title ~16–17px medium → details/specs: eBay "Item specifics" 2-col label/value grid (Condition, Brand, Model…); OfferUp/Mercari compact Details: Condition, Category, Posted date ("Listed 3 days ago in Austin, TX"), Delivery options.
4. Seller card: avatar, name, ★ rating + review count, trust extras (eBay feedback %; Poshmark Ambassador; OfferUp "Responds within ~1 hour" — HONESTY RULE: we must NOT invent ratings/response times we don't have). FB 2026: AI-generated trust digest (account age, listing history, ratings) atop seller pages.
5. Description: free text, "Read more" collapse beyond ~3 lines.
6. Safety tips: "Safety tips for transaction" collapsible AFTER description, BEFORE similar listings (FB + OfferUp pattern; shipping apps show buyer-protection badges instead).
7. Similar listings: "You may also like" grid at bottom — universal.
8. CTA: STICKY BOTTOM BAR is the 2025–2026 universal pattern. FB: big "Message seller"; OfferUp: "Ask" + "Make offer"; Mercari: "Buy now" + "Make offer"; eBay: "Buy It Now"/"Place bid"/"Make offer". Heart/save in photo overlay.

## 6. Trust signals
- Ratings: "★ 4.8 (127)" next to seller name; eBay "98.7% positive feedback".
- Verification: ID/phone checkmarks (OfferUp), Top Rated Seller (eBay), Ambassador (Poshmark).
- Response-time labels: "Responds within ~1 hour" (OfferUp).
- Meetup safety: in-listing tips + public-meetup-spot suggestions (FB/OfferUp); shipping apps use escrow/buyer-protection messaging.
- Escrow holds: Mercari holds funds until buyer confirms receipt; surface "Buyer Protection" near CTA.

## 7. Post-a-listing flow
Canonical: photos FIRST (multi-picker; Depop 4+1 video) → title (short cap) → category (hierarchical; AI auto-suggest) → condition (chips: New/Like new/Good/Fair; eBay added 3 pre-loved grades 2025) → price (numeric; **AI price suggestion from comps is now standard** — FB/Meta AI from similar local listings, Mercari fair-price range, eBay sold-comps price guide) → description (**AI draft from photos is the 2026 default** — Mercari AI Listing Support, Meta AI full description+price; seller edits/regenerates) → shipping vs local toggle → review & publish.
- Creation UI: full-screen modal/slide-up or dedicated page, never inline push-down. Photos upload while typing. Publish-in-60-seconds benchmark.
- 2026 extras: listing completeness meter (Mercari demotes attribute-poor listings 3×); seller dashboard (views→messages→sales); inbox threaded by listing.

## 8. Steal-list (priority order)
1. Card: square photo (8–12px radius) → bold price 16px → 2-line title → gray location/distance/shipping line; SOLD/FREE as on-photo overlays.
2. Detail: swipeable carousel w/ counter → price block → title → specs grid (condition/category/posted/location) → seller trust card → description → safety tips → similar items.
3. Sticky bottom CTA bar on detail ("Message seller" primary).
4. Seller card: avatar, name, honest trust info only — NO invented stats.
5. Filters: search bar + location on top → scrollable text chips → single Sort dropdown; distance slider in a filter sheet.
6. Sell flow: photos first → AI-style title/description/price suggestions (editable) → category → condition chips → shipping/local → publish; completeness nudges.
7. Safety: collapsible "Safe transaction tips" on every detail page; protection label near CTA.
