# Onaro UX Research — What the Best Apps Do (2026-10-07)

Research coordinator synthesis from 3 parallel research workers. Full worker reports:
- Top-app techniques: `~/workspace/research/mobile-feel-techniques-2026.md`
- iOS web performance: `~/workspace/reports/ios-web-perf-2026.md`
- Gen Z delight: `~/workspace/research/genz-app-delight-2026.md`

## The 20 Named Techniques (from top-app research)

1. **Pointer-down press feedback** — visual response on `pointerdown` (not click), `:active{transform:scale(0.97)}` 100-150ms, `touch-action:manipulation` kills tap delay. Kills the #1 "web feels cheap" tell.
2. **Structured haptic vocabulary** — one haptic per action (light=press, medium=send, heavy=destructive). Web: `navigator.vibrate()` — **iOS Safari does NOT support it** (Android only, feature-guard).
3. **Spring physics** — critically damped default (damping 1.0/response 0.4s); bounce ONLY when gesture carried momentum. Vanilla: ~40-line Euler integrator or `cubic-bezier(0.34,1.56,0.64,1)` approximations.
4. **Swipe actions with threshold haptics** — iOS Mail pattern.
5. **Bottom sheet with drag physics** — 1:1 tracking, velocity snap, rubber-band, `overscroll-behavior:contain`.
6. **Skeleton screens** — perceived 30-40% faster than spinners at identical load times (LinkedIn research).
7. **Optimistic UI** — update instantly, rollback on failure. For reversible + >99% success actions only.
8. **Toast-with-Undo** — replaces confirm dialogs (Gmail archive pattern).
9. **Staggered list entrance** — 30-60ms/item, fade + 8-12px rise, cap at ~7, total <700ms.
10. **Celebration tiers** (Duolingo) — micro/medium/major; never block interaction behind confetti.
11. **Count-up number morphs** — digit-by-digit with `tabular-nums` (Stripe/Revolut).
12. **Shared-element transitions** — FLIP: animate ONE moving object, never fade-out+fade-in.
13. **Signature moments** — one iconic microinteraction per app (Cash App paper plane).
14. **Ambient/idle motion** — non-syncing loop durations (3s vs 4s) read organic; never move readable data.
15. **Frequency rule** — 100+/day actions get NO animation; exits faster than entrances.
16. **Long-press menus** — 500ms → haptic → origin-aware menu scale.
17. **Pull-to-refresh with brand play**.
18. **Mascot personification + coach micro-copy** — character nag forgiven, system error resented.
19. **Scarcity rituals (BeReal) + ambient presence (Locket)** — social synchrony over follower counts.
20. **Nothing's glyph philosophy** — pre-attentive glanceable cues.

## iOS Web Performance — Critical Findings

- **Compositor-safe = `transform` + `opacity` ONLY.** `filter`, `backdrop-filter`, `clip-path` are NOT compositor-only in WebKit — they repaint per frame.
- **`backdrop-filter` is the #1 jank risk.** Budget: ~3-5 simultaneous blurs on mobile. Never nest blurs. Near-opaque glass (>72%) should be flat translucent fill. (Onaro has ~90 usages — AUDIT NEEDED.)
- **`will-change`/`translateZ(0)`**: still useful on Safari 2026, but release after animation. Blanket use = memory spikes.
- **120Hz ProMotion**: page rendering capped ~60fps by Safari default; only the USER can unlock. Budget for 60fps.
- **`-webkit-overflow-scrolling: touch` is DEAD** (no-op since iOS 13). Delete it.
- **`content-visibility: auto`** works in Safari 18+ for long lists (zero JS).
- **Images**: AVIF > WebP, `decoding="async"`, `loading="lazy"` below fold, `width`/`height` always (cheapest CLS fix).
- **Safari 2026 APIs** (all `@supports`-gated): View Transitions, `@property` (animated gradients), scroll-driven animations, `@starting-style`, Popover API.

## Gen Z Delight — Ranked by Emotional Impact

1. **Streaks with safety nets** (Duolingo) — loss aversion is retention's #1 weapon.
2. **Time-aware app voice** — cheapest "alive" feeling. Character, not slang.
3. **Live presence cues** — "3 friends online", typing indicators.
4. **Weekly shareable rituals** — Locket's Rollcall model (small-team Wrapped).
5. **Unexpected micro-rewards** — surprise animations <1s, #1 screenshot source.
6. **Anti-doomscroll as feature** — "you've seen everything" end-of-feed (2026 defining trend).

**Anti-patterns**: notification spam, dark patterns, cringe copy, jank, forced onboarding.

## Ranked Recommendations for Onaro

| # | Improvement | Impact | Effort | Status |
|---|-------------|--------|--------|--------|
| 1 | Backdrop-filter audit (reduce to ~5 max visible) | HIGH (perf) | Medium | IMPLEMENTED 2026-10-07 |
| 2 | Remove dead `-webkit-overflow-scrolling` | Low (cleanup) | Trivial | IMPLEMENTED 2026-10-07 |
| 3 | Count-up number morphs (degree counts, points) | HIGH (polish) | Low | IMPLEMENTED 2026-10-07 |
| 4 | Haptic vocabulary (feature-guarded vibrate) | Medium (Android) | Low | IMPLEMENTED 2026-10-07 |
| 5 | Time-aware greeting personality | HIGH (delight) | Low | IMPLEMENTED 2026-10-07 |
| 6 | Optimistic UI on likes/saves | HIGH | Medium | Future |
| 7 | Tier-1 celebration kit (confetti) | HIGH | Low | Future |
| 8 | Drag-physics bottom sheet | HIGH | High (1-2d) | Future |
| 9 | Streaks with Freeze | HIGH (retention) | Medium | Future |
| 10 | Weekly shareable card | HIGH | Medium | Future |
| 11 | View Transitions API (`@supports`-gated) | Medium | Low | Future |
| 12 | `content-visibility` on long lists | Medium (perf) | Low | Future |
| 13 | Toast-with-Undo everywhere | Medium | Medium | Future |
| 14 | Image ladder (AVIF/WebP, lazy) | Medium (perf) | Medium | Future |
| 15 | Live presence cues | HIGH | High | Future |

## Implementation Notes (2026-10-07)

All implementations respect `prefers-reduced-motion`, dark-mode-only, no purple, iPhone-first.
See commit history for details.
