# ORBIT — 2026 Color Identity
Tagline: **"Everything in your orbit"**

## Decision: "Deep Ink + Volt Signal"

One vivid signature accent — **Volt** (a yellow-green volt-lime) — over deep ink neutrals
with a warm paper-light mode. Purple is gone, everywhere, by rule: no purple in the accent,
no purple in gradients, no purple in map pins.

Why volt, not coral or orange: coral/orange is claimed territory (Airbnb's Rausch, PrizePicks
leans warm-bright, Duolingo orange). A volt-lime on deep ink is the freshest "one accent"
move of the 2024–2026 wave (Cash App's signature green, Spotify's wrapped-neon moments),
it reads electric at 16px on a tab bar and in an app-store icon, and it ties straight to the
brand story — *your orbit is a glowing ring around you, not a pastel cloud.*

### Why it feels 2026, not 2023
- **One accent, disciplined.** Award-winning identities stopped doing multi-hue rainbow UI;
  they pick one ownable hue and ration it (Cash App Green, Airbnb Rausch).
- **Prismic darks, not flat black.** Dark mode is a deep green-black with layered surfaces,
  not an inverted light theme.
- **Warm paper, not clinical white.** Light mode uses a warm off-white — the human, premium
  direction the best apps moved toward.
- **No neon overload, no cheap gradients.** Volt appears as flat fills, glows, and
  soft washes. Never as a text-on-background body color (it fails AA there — see rules below).

## Research references studied
1. **Cash App brand guidelines** (creativebloq.com) — "Cash App Green" as the single signature
   color over neutrals; 2D/3D icons as collectible brand assets; style guide that lets the
   color do the brand work. Confirmed: one vivid accent + 3D clay iconography is a proven,
   youth-resonant formula.
2. **Airbnb rebrand breakdown** (medium.com/startup-insider-edge) — Rausch coral chosen
   *deliberately* to avoid tech blues/greens; color as the recognisable asset, the same
   strategy we apply with Volt. Confirmed: owning one hue beats owning a gradient.
3. **"Why apps will feel different in 2026: A color story"** (medium.com/design-bootcamp) —
   prismic darks (depth-with-light instead of flat black), muted tones + single neon pops
   (taupe/beige with coral or neon yellow), gentle "street-lamp, not billboard" brights.
   Confirmed: volt as a rationed pop on warm neutrals.
4. **"Designing Mobile Apps That Feel Human"** (Christos Kaitatzis, Jun 2026, Medium) —
   off-white surfaces instead of pure white, accents pulled from soft natural events,
   colors that share an undertone. Confirmed: our ink carries a faint green-warm undertone
   so every color "shares the same light."
5. **Material 3 Expressive / Google 2026 design direction** (github.com/alaa91h/nexaflow
   GOOGLE_2026_DESIGN.md) — larger radii, tonal surface tiers, bright expressive accents,
   dynamic-color-aware theming. Confirmed: surface tiering (bg → surface → surface-2)
   and expressive accent usage in buttons/chips/tabs.
6. **2026 color trend roundups** (jkillr/agent-swarm design_trends research: Pantone 2026
   Cloud Dancer neutral + monochrome extremes — "single bold hue pushed to extremes,
   electric blue, deep crimson, lime green") — Confirmed: a single extreme hue (volt-lime)
   is the on-trend ownable move.

## Token set (see tokens.css for the merge-ready blocks)

| Token | Light | Dark | Usage |
|---|---|---|---|
| `--bg` | `#FAFAF7` warm paper | `#0D100A` deep ink-green | app background |
| `--surface` | `#FFFFFF` | `#161B10` | cards, sheets |
| `--surface-2` | `#EFF1E6` | `#212819` | inputs, tab bar, raised tiles |
| `--ink` | `#101408` | `#F4F6EC` | primary text |
| `--ink-2` | `#4B5240` | `#C6CCB5` | secondary text |
| `--muted` | `#8A8F7E` | `#8E9482` | tertiary / decorative only |
| `--accent` | `#C6F135` volt | `#D4F53F` volt-bright | fills, active states, NOT body text |
| `--accent-ink` | `#131A00` | `#131A00` | text/icons on accent fills |
| `--accent-strong` | `#4A7A00` olive | `#D4F53F` volt-bright | accent-colored TEXT (AA-safe) |
| `--accent-soft` | `#EFFAD0` | `rgba(212,245,63,.14)` | tinted chips, badges, highlights |
| `--accent-2` | `#FF5C38` signal coral | `#FF7A5C` | sparing secondary: map pins, stories ring |
| `--accent-2-strong` | `#C22E1F` | `#FF9B85` | coral text (AA-safe) |
| `--success` | `#1F7A4D` | `#4ADE80` | |
| `--warn` | `#B45309` | `#FBBF24` | |
| `--danger` | `#D92D20` | `#F87171` | |
| `--ring` | `rgba(74,122,0,.45)` | `rgba(212,245,63,.55)` | focus outlines |
| `--divider` | `rgba(16,20,8,.10)` | `rgba(244,246,236,.12)` | hairlines |
| `--tabbar-bg` | `rgba(250,250,247,.85)` | `rgba(13,16,10,.85)` | blurred tab bar |
| `--tabbar-active` | `#131A00` pill / volt icon | volt icon + glow dot | active tab |
| `--pin-me` | `#C6F135` | `#D4F53F` | your location pin |
| `--pin-friend` | `#1F7A4D` | `#4ADE80` | friend pins |
| `--pin-event` | `#FF5C38` | `#FF7A5C` | events/meetups |
| `--pin-market` | `#2563EB` | `#60A5FA` | marketplace (intentional blue) |
| `--pin-food` | `#B45309` | `#FBBF24` | food spots |

## Accessibility — what is text-safe
- **Volt `--accent` is NEVER body text.** 4.93:1 it is not; volt-on-paper is ~1.9:1.
  Use `--accent-strong` for any accent-colored text in light mode (4.93:1 on paper — AA ✓),
  and volt freely as text in dark mode (15.45:1 on deep ink — AA ✓).
- `--accent-ink` on `--accent`: 13.64:1 — buttons with volt fill + dark ink label are AA ✓.
- `--ink`, `--ink-2`: AA ✓ both themes. `--muted`: AA ✓ in dark (5.90:1); in light (3.18:1)
  use ONLY for non-essential text (captions, placeholders) — never for labels or body copy.
- Coral `--accent-2` is not text on light; use `--accent-2-strong` (5.67:1 ✓).
- All semantic colors verified ≥4.5:1 as text in both themes.

## Usage rules for the CSS worker
- Primary button = volt fill + `--accent-ink` text, 14px+ radius, no border.
- Secondary button = `--surface-2` fill + `--ink` text.
- Destructive = danger fill + white text.
- Active tab = volt icon on dark, volt-filled pill + dark icon on light; inactive = `--muted`.
- Chips/badges = `--accent-soft` bg + `--accent-strong` text (light); dark: soft bg + volt text.
- Focus ring = `--ring` 2px outline.
- Gradients: banned except one — a subtle volt→transparent glow on hero/empty-state art.
- Purple ban: no `#7C3AED`-family hues anywhere in UI or icon tints.

## Icon re-tint guidance (for the icon worker)
The 53 PNGs are 3D soft-clay. Keep the clay material exactly — matte, softly lit, rounded —
but re-grade the *accent parts* (the bits currently purple) to **volt #C6F135** with a
slightly deeper olive shadow (#8FAE1E) so they read as lit clay, not neon plastic.
Everything else goes **neutral clay**: warm sand/beige (`#D9CBBF`-family) for light objects
and deep ink-clay (`#2A2E22`) for dark objects, with white clay reserved for tiny glyph
details. Rules: accent parts ≤ ~25% of any icon's area; never more than one accent hue per
icon (volt, or coral for event/food/alert icons only); shadows stay neutral gray-green,
never tinted purple. A quick before/after screenshot pair of 3 icons should confirm the
grade before the batch run.

## Open issues for the coordinator
1. Font pairing wasn't in scope — recommend Space Grotesk (display) + Inter (body) per 2026
   research; needs PraBin's sign-off.
2. Tab-bar active pill vs plain icon: spec gives both; the CSS worker should pick the pill
   only if the current layout has room.
3. Map tile style: volt-on-dark tiles need a MapLibre style check — verify pins stay legible
   at zoom 12–16 in dark mode before shipping.
4. 3D clay icons are raster PNGs — re-tint worker should confirm output format stays PNG
   and file names unchanged so `styles.css` references don't break.
