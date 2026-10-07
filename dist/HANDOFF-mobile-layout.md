# Mobile Layout Fix — Handoff Note (2026-10-06)

Crew stood down mid-task per PraBin's order. This note covers what's done and what's still open.

## Committed (master `3fd6682`, NOT pushed — parent to push)

**`index.html`**
- Tagline: removed `display:block` from the inline style on `.brand .sub`. The inline
  style was overriding `@media(max-width:520px){.brand .sub{display:none}}`, so the
  tagline always rendered and crowded the header on narrow screens. Other inline
  styles (font-size etc.) kept.

**`styles.css`**
- `.tabbar`: added `-webkit-transform:translateX(-50%)` prefix and `translateZ(0)`
  (dedicated compositor layer — stops iOS Safari repaint/reposition jumps during
  toolbar show/hide and scroll). Added `env(...,0px)` fallback on safe-area.
- `.askpill`: added `max-width:calc(100% - 32px);overflow:hidden` — it had no right
  constraint and could overflow the viewport on narrow screens.
- `.brand`: added `min-width:0;flex-shrink:1;overflow:hidden`; `.brand-lockup`
  `min-width:0`; `.brand-name{white-space:nowrap}` — brand can no longer force the
  appbar wider than the viewport.
- `.kv`: added `>*{min-width:0}` and `.meta{overflow-wrap:anywhere;text-align:right}`
  — long values (emails) in key/value rows now wrap instead of overflowing.

**`profile.css`** (ME tab)
- `#view-me .me-repgrid>*{min-width:0}` — grid items default `min-width:auto`;
  long labels ("Marketplace exchanges") could blow out the 1fr tracks.
- `#view-me .me-replabel, .me-rephint{overflow-wrap:break-word}`.
- `#view-me .me-ribbon::after{content:'';flex:0 0 4px}` — trailing spacer so the
  last chip in the horizontal scroll ribbon can scroll fully into view with end padding.

## What I verified

- Headless Chromium audits at 390px and 320px (all 6 tabs): `document.scrollWidth`
  == viewport width, zero elements extending past viewport, zero inner-overflow
  (`scrollWidth > clientWidth`) offenders — **with seeded minimal data**.
- `.tabbar` measures 362px at 390px viewport, `position:fixed` — correct in Chrome.
- No ancestor of `.tabbar` has transform/filter/backdrop-filter (would break fixed
  positioning) — `.phone` and `body` are clean.
- `profile.css` DOES contain the ME styles (16KB) — earlier confusion was a grep
  that missed the root-level file.

## What's still broken / not verified (for the fresh crew)

1. **Could not reproduce PraBin's exact breakage in the sandbox.** His screenshots
   show the header/tabbar cut off on the LEFT and cards extending right — my audits
   with seeded data show no overflow. Likely causes: (a) his real data (reputation
   stats, deals, households) triggers paths my seed didn't; (b) the iOS app's
   WKWebView renders differently than Chrome; (c) possible pinch-zoom. The fresh
   crew should test with a full data seed (reputation, listings, households,
   communities) and ideally on a real iPhone.
2. **Tabbar "moves up and down"** — no JS moves it (verified: only a click
   listener in `js/app.js`). Likely iOS Safari toolbar show/hide or keyboard
   opening in the WKWebView. The `translateZ(0)` hardening is committed but
   **not verified on a real iPhone** — PraBin must confirm.
3. **"Ask Onaro" pill overlapping cards** — it's `position:fixed` by design
   (floats above the tabbar); it will overlap scrolled content. If PraBin wants it
   hidden while scrolling, wire it to the existing `.askpill.hide` class on scroll.
4. **ME tab "Something went wrong loading this tab"** — seen in my screenshots
   when the session seed was malformed; with a proper session the tab rendered in
   earlier audits. If it reproduces, check `js/me.js` render errors in console.
5. **Sandbox QA caveat**: `https://www.gstatic.com/*` must be blocked via
   `Network.setBlockedURLs` in CDP harnesses, otherwise the Firebase CDN scripts
   hang and `readyState` stays `loading` forever (boot watchdog fires). This is
   sandbox-only; on PraBin's iPhone gstatic.com is reachable.
6. **Login gate**: `window.__gateSkip` no longer exists (removed in Firebase
   rewrite). For QA, seed `hub_v1` in localStorage with
   `auth.users=[...]` + `auth.session={uid,...}` BEFORE boot via
   `Page.addScriptToEvaluateOnNewDocument`, then the gate stays shut.

## Test scripts (in /tmp, not committed)

- `/tmp/qa_layout_audit.py` — per-tab viewport-overflow audit (390/320)
- `/tmp/qa_deep.py` — inner-overflow (`scrollWidth > clientWidth`) audit
- `/tmp/qa_shots.py` — screenshots all 6 tabs at 390/320 (needs the gstatic
  block + hub_v1 session seed described above)
- `/tmp/qa_diag.py`, `/tmp/qa_mini.py`, `/tmp/qa_err.py` — one-off diagnostics
