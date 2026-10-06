# ORBIT — Brand Rationale

## The mark
A solid planet disc wrapped by a single elliptical orbit ring tilted at a steep
−26°, with a small satellite dot riding the ring's upper-right arc. The ring
passes **in front of** the planet across its lower third and **behind** it at
the top, giving the flat mark a quiet sense of 3D depth. No rounded square, no
letterform, no resemblance to the old "H" mark.

## Why this concept won
Six concepts were explored (see `brand/concepts/`): steep-tilt ring, monoline
double-ring, crescent negative-space planet, mark+wordmark lockup, an "O"-as-planet,
and a heavy 3D-gradient ring. The steep-tilt ring won because it is the most
**recognizable at 48px and below** (three simple shapes: disc, one ring, one dot —
the monoline and "O" concepts turned to mush or read as a "no-entry" sign at small
sizes), the most **original** (the steep tilt + front-crossing arc is an ownable
construction, not a generic Saturn clip-art), and it carries the brand story
literally: *your orbit is a glowing ring around you* ("Deep Ink + Volt Signal"
identity, `tokens.css`).

## Colors (from `tokens.css` — purple ban respected)
- **Light surfaces:** planet `#101408` (deep ink), ring `#C6F135` (volt),
  satellite `#FF5C38` (signal coral).
- **Dark surfaces:** planet `#F4F6EC` (paper), ring `#D4F53F` (volt-bright),
  satellite `#FF7A5C` (coral, dark-tuned).
- The satellite is coral rather than volt for a functional reason: it sits **on**
  the volt ring, so a volt dot would disappear into it.
- No purple anywhere, per the brand rule. No gradients in the mark (flat fills only).

## Files
| File | Use |
|---|---|
| `brand/logo.svg` | Primary master vector (light) — hand-authored, infinitely scalable |
| `brand/logo-dark.svg` | Dark-surface master vector |
| `brand/logo-{512,192,96,48}.png` | App-icon / in-app sizes, transparent bg |
| `brand/logo-dark.png` (+ `-512/-192/-96/-48`) | Dark-background variants, transparent bg |
| `brand/favicon.svg` | Adaptive favicon (switches via `prefers-color-scheme`) |
| `favicon.svg` / `favicon.png` (hub root) | Live favicons referenced by `index.html` |
| `brand/concepts/` | The 6 AI shape-exploration renders (superseded by the vector) |

## Usage notes
- **Clear space:** keep at least the satellite dot's diameter of empty space on all
  sides; never let the ring touch other elements.
- **Minimum size:** 24px digital. Below that, use the planet disc alone (crop the
  ring) — the full mark's ring thins out under ~20px.
- **Backgrounds:** use `logo-*` on light/warm surfaces, `logo-dark-*` on dark/ink
  surfaces. Never place the light mark on a dark background or vice versa.
- **Do NOT:** recolor the mark (no purple, ever); add gradients, shadows, or
  outlines; rotate it further; put it inside a rounded square; stretch it;
  replace the coral satellite with another color; use the wordmark lockup from
  `concepts/` (its gray "orbit" type was a placeholder — in-app wordmark is
  Inter 800 via `.brand-name`).
- **Header wiring:** `index.html` includes both variants; `styles.css` toggles
  them with `body.dark` (the app's real dark-mode hook — see AGENTS.md).
