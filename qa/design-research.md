# HUB Design Research Brief — 2026 mobile design references
*Compiled 2026-09-21 by Worker D. Context: HUB is a mobile-first web app (young people: organization, marketplace, micro-jobs, roommates, campus, local discovery, AI glue). Premium-minimal identity, purple #7C3AED, 3D clay icon family as signature.*

## 1. Interaction patterns worth stealing
- **Floating glass tab bar, 3–5 tabs, bottom of thumb zone** — iOS 26 "Liquid Glass" (tab bars shrink on scroll, live in a controls layer floating above content), Android floating pill (Telegram). Content scrolls *under* chrome; never inset content away from it.
- **Bottom-sheet everything** — filters, actions, detail-in-place (Material sheets, iOS detents). Marketplaces: filters in a bottom sheet, never a sidebar (U1CORE 2026). Sheet drag hand-off: drag only when inner content is at scroll-top.
- **Listing card = image + price + title + ONE trust signal** — Airbnb/Etsy/Facebook Marketplace pattern. Everything extra reduces CTR. Detail page carries trust layer (seller info, fees visible pre-confirmation).
- **One-tap create flows** — Depop/Cash App: central create action, progressive disclosure (equal split default → customize on demand, per Splitwise 2026 flows). Camera-first listing; correct `inputmode` per field (numeric pad for amounts, OTP autofill).
- **Skeleton → content morph, not spinners** — best 2026 apps morph skeletons into real content; acknowledge every touch <100ms; zero layout shift (reserve aspect-ratio boxes); optimistic UI for likes/sends (STIFF mobile-ux playbook).
- **Empty states as redirects** — "Nothing here yet — browse popular categories / 3 sellers nearby are active", never dead ends (marketplace rule).
- **AI chat entry as bottom pill, chips for intents** — ChatGPT/Meta AI/Perplexity mobile: composer pinned bottom, suggested-prompt chips, inline streaming. Keep AI opt-in, reversible, quiet-by-default.
- **Hamburger is where features die** — 3–5 visible tabs only; hamburger measurable drops discovery (STIFF audit).

## 2. Icon system trends for 2026
- **3D clay/squishy icons** — "Tactile maximalism": high-fidelity 3D-rendered icons that look touchable; squish-on-press deformation. HUB's clay family already rides the top trend.
- **SF Symbols-style thin outline in chrome** — controls layer uses thin, uniform-weight line icons (iOS 26); brand/3D icons live in content. Rule: 3D clay for *identity* moments (tabs' active state, create button, hero), line icons for controls.
- **No literal color mixing in chrome** — semantic tint only; single 24pt hit-area glyph padded to 44–48pt.

## 3. Profile page patterns (real-identity apps)
- **Reputation hero, not bio hero** — Airbnb/Etsy pattern: verified badge, completed-deal count, "responds in ~2h", review snippet — specific numbers beat 4.8★ (U1CORE: when every seller is 4.7–4.9, stars mean nothing).
- **Structured reviews** — prompt specifics (item as described? communication? speed?) so trust profiles read real.
- **Dual identity (human + trader)** — profile shows the person (name, photo) then their role stats (seller/jobs/roommate verifications) as separate ribbons; LinkedIn-style credibility, not Instagram-grid.
- **Money views: net balance dominant** — fintech rule: one big net number, directional labels, muted red for owed, calm green/blue for owed-to-you; audit feed chronologically (Splitwise patterns).

## 4. Motion language of 2026
- **Spring physics everywhere** — underdamped springs for sheets, tab transitions, dismissals; nothing eases linearly. Micro-spring on confirm (haptic + bounce).
- **Sheets with detents, scroll-edge minimization** — tab bar shrinks on scroll-down (iOS `tabBarMinimizeBehavior`), restore on scroll-up; FAB hides on scroll-down.
- **Shared-element continuity** — card → detail with image cross-fade; theme/icon morphs (FAB morphing per iOS 26 adoption notes).
- **Purposeful micro-animation only** — every animation explains a state change (skeleton→content, optimistic like pop, settle confirmation). Ornamental motion = dated.
- **Pull-down-to-search** — summon search from mid-screen instead of reaching top (Safari-style).

## 5. Anti-patterns to avoid (feels cheap/dated now)
- Hidden fees, "Confirm" without variables stated, fee-surprise at checkout.
- Dead-end empty states; "No results found" with no redirect.
- Generic glassmorphism blur panels — iOS 26 Liquid Glass is *dynamic refraction*, static blur panels read as 2021. On web: use HUB's own glass tokens, never pretend native refraction.
- Top-anchored primary actions on 6.7" screens (top 40% is the dead zone).
- Tiny/grey text as sole contrast; WCAG-floor 24px targets; adjacent destructive+primary with no gap.
- Hamburger nav; >5 tabs; custom gestures with no button fallback; gesture conflicts (sheet-vs-scroll).
- Flat minimalism + thin grey everything — 2026 expects tactile texture (clay!) and true-black OLED dark mode with tonal elevation (no shadows-in-dark).
- Password-first login screens — passkeys/biometrics, progressive onboarding (auth only at value-exchange).

## 6. SIGNATURE decisions — original to HUB (implementable in CSS/JS)
1. **Floating orbit tab bar with a central clay Create button.** A glass floating-pill tab bar (3 tabs + Search) where the center slot is a 3D clay "+" that physically squishes on press and springs up a radial create menu (List an item / Post a job / Find a roommate / Ask AI). No app does clay-tactile in the nav chrome — it makes HUB's visual signature the literal entry point to creation.
2. **Reputation ribbon profile hero.** One horizontal clay-embossed ribbon under the avatar: `[✓ ID verified] [47 deals] [responds ~2h] [★ 4.8 · 23 reviews]` as a single swipeable strip. Not a star grid — a *belt of proof* readable in one glance, in HUB's clay material. Steal the Airbnb data, invent the ribbon.
3. **AI as a bottom "Ask HUB" pill, not a tab.** A floating glass pill above the tab bar on every screen; tapping expands a bottom sheet (not a new page) with intent chips ("Split this bill", "Price my listing", "Draft my roommate ad"). Quiet-by-default, context-aware of the current screen. No competitor merges assistant-into-navigation like this.
4. **Trust-first listing cards with clay trust badges.** Marketplace card keeps image/price/title + one trust signal, but the trust signal is a raised clay chip (e.g. "✓ 47 deals") with a real 3D pop on scroll into view — hover-lift + spring pop-in on save (steal the motion, own the material). Makes trust *tactile*.
5. **Tonal-dark + true-black OLED default with purple warmth shift.** Dark-first (#000), tonal elevation surfaces, and HUB purple re-tinting subtly warmer in the evening (per adaptive dark themes). Combined with concentric-radius glass (iOS 26 concentricity rule), HUB feels like a physical object, not a page — distinct from both Apple's cold glass and Material's pastels.

*Sources: iOS 26 Liquid Glass HIG specs (github native_adaptive_ui, archflow), react-native-glass-tabs writeup, Jackson Ford "7 App Design Trends 2026", U1CORE "Marketplace UX Design 2026", STIFF mobile-ux SKILL, allclonescript split-bill UX guide 2026, ForaSoft 2026 best-practices playbook.*
