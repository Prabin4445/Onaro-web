# HUB Design Deep-Dive — comparative analysis (Worker E, 2026-09-21)
Complements `design-research.md` (Worker D). Goes deeper on **concrete details**: exact nav structures, icon treatments, profile layouts, empty states, motion constants, dark-mode tokens, identity devices. All facts from the sources cited at the end.

Constraints held throughout: premium-minimal chrome, purple `#7C3AED`, 3D clay icon family as visual signature, no neon/glass excess, honest data only, mobile-first, light + true-black dark mode.

---

## 1. Award winners — what the juries actually rewarded

| Winner (award) | Navigation | Icons / visual signature | Profile | Motion | Dark mode | Identity device |
|---|---|---|---|---|---|---|
| **grug** (ADA 2026 Delight) | Single-column, hand-drawn everything | **Hand-drawn custom status bar** replacing iOS native bar; color personalization modes | N/A (affirmation app) | Hand-drawn onboarding animations + haptics | Full color personalization | The *one* memorable concept: Neolithic hand-drawn UI is the whole brand |
| **Moonlitt** (ADA 2026 Interaction) | Simple onboarding, platform-spanning | Liquid Glass integration | — | "Visual calm" — clarity-first animation | True dark sky palettes | Utility made distinctive without hiding data |
| **Tide Guide** (ADA 2026 Visuals) | Full-screen charts, hour-by-hour forecasts | Custom aquatic theme | — | Custom chart animations | Deep-sea dark | Cohesive theme where data *is* the aesthetic |
| **Focus Friend** (Google Play Best App 2025; Apple Cultural Impact 2025) | One-screen timer, minimal chrome | Cute "Bean Friend" avatar + decorate-its-room rewards | — | Focus timer as the interface | Calm palettes | **Prestige anti-pattern**: attention-protection is a category now |
| **Watch Duty** (ADA 2025 Social Impact) | Map-first, layers | Crisis data rendered legibly | — | Live updates, no ornament | High-contrast dark | Honest real-data presentation |

**Steal:** grug's "one drawn concept = the whole brand" → HUB's clay family must be the single visual concept, not decoration. Focus Friend's attention-protection → rewards for *finishing* real-world actions, not screen time.
**Avoid:** Liquid Glass as a whole-UI treatment (Awwwards failure pattern; iOS 26 native shader can't be replicated in web anyway).
**Beat:** grug owns hand-drawn; HUB owns *squish-physics clay* — grug never put 3D tactile material into the chrome.

## 2. Marketplace — Depop / Vinted / OfferUp / FB Marketplace

| App | Navigation | Listing card | Profile/trust | Empty states | Motion | Identity |
|---|---|---|---|---|---|---|
| **Vinted** | Bottom tabs (Home, Search, Sell, Inbox, Profile); camera-first sell | Image-dominant grid, price + size overlay; heart count public; "selling fast"/trending scarcity badges | ID-verified badge, reviews, seller stats; bundle discounts | Redirects to popular categories + "sellers nearby active" | Infinite scroll + horizontal carousels mixed for rhythm; feedback loops during listing build | Green, bargain feel; trust = less intermediation, more direct buyer chat |
| **Depop** | Social-feed home; Explore/search; Sell (central); Inbox; Profile | Square images, price bold; lifestyle shots encouraged; bio cadence ("New drops every Thursday") | Pro-seller base; follows; shops as profiles | Feed always populated via discovery | Social-media-like card rhythm; optimistic like pops | Designed *like a social network*; entertainment over utility |
| **OfferUp** | Home / Post (big "Post" button) / Inbox / Profile | Photo grid, price overlay, location-first | Star ratings both sides; profile + rating before deal | Location-radius empty → widen radius prompt | Simple; messaging instant | "Sell in 30 seconds" — speed of listing is the brand |
| **FB Marketplace** | Shop icon in bottom bar; separate Marketplace nav | **Heavily image-focused storefront: pictures + price only on first paint**, detail on tap; search by location/category/price | Basic seller info; "Make Offer" button; Messenger chat inline | "Similar items" surfaces | Minimal | Distance-from-user ranking; bargaining native |

**Steal:** FB's pictures+price-only first paint (nothing else competes). Vinted's public favorite-count scarcity cues → adapt as honest "3 people saved this" (real counts only). Depop's seller-bio rhythm.
**Avoid:** Vinted's ~100-image "Lifestyle" scroll wall; FB's post-purchase payment vacuum (HUB must keep in-app honest handoff).
**Beat:** none of them render trust tactile — HUB's clay trust chip (e.g. raised "✓ 47 deals") makes the one trust signal physical.

## 3. Chat — Telegram / WhatsApp / Messenger / Discord

| App | Navigation | Icon system | Profile | Empty states | Motion | Dark mode / identity |
|---|---|---|---|---|---|---|
| **Telegram** (2026 Liquid Glass overhaul) | **4-tab floating bottom nav**: Chats, Contacts, Settings, Profile; hamburger killed | Proprietary outlined icon vocabulary (not web-accessible-icon); 28pt icons, 10pt/500 labels, active = user-accent | Chat list row: 76pt height, 54pt avatar, name 17pt/600, preview 15pt, time 13pt | Search-first empty; contact import prompts | **Measured constants**: button state 0.2s; panel/bar swaps 0.25s slide+fade; sheet snaps 0.45s; spring damping 124 / stiffness 900 / mass 5 (~0.92 ratio). **Haptics sparse**: none on select — only `.error` on limit breach and impact on destructive. Button press = opacity only (0.4 on touch-down, 0.2s ease back), no scale | True-white light; crushed `#212121` dark + **separate OLED `#000000` toggle**; *every color themeable* (identity = rhythm, not color). Bubble: 17pt radius all corners except 6pt tail corner |
| **WhatsApp** | Bottom tabs: Chats, Communities, Calls, Updates | Filled-brand icons; 3×3 action-tile attach palette with spring scale entrance | Business profiles structured; personal minimal | Contact-discovery prompts | Composer send button **springs in only on empty⇄draft transition** (damping 0.6, scale 0.5→1) — never per keystroke | Cream-tint light; OLED dark |
| **Messenger** | Bottom tabs; Meta AI tab entry | Round, friendly; Meta-gradient accents | Rich: story highlights, custom chat themes per thread | Story/suggestion fill | Sticker/emoji heavy; bubble effects | Dark slate, brand purple-blue |
| **Discord** (mobile overhaul) | **4 tabs: Servers, Messages, Notifications, You**; vertical server rail kept after testing a horizontal dock (display density won) | Blurple; guild-icon rail; online-status dots | Profile = status + activity + "what they're doing now" (Spotify/game carousel) | Server-discovery prompts | 55% faster app-open claimed; multi-image uploads grouped into gallery view | **"Midnight" theme** = true-black OLED option; notification tab is fully actionable (tap jumps to mention) |

**Steal:** Telegram's sparse-haptic + opacity-only press rule (feels engineered, not toy-like); Discord's actionable notification tab (every notification deep-links to its target); Telegram's separate OLED toggle.
**Avoid:** Telegram's total-themeability (dilutes brand) — HUB keeps one identity: purple + clay. WhatsApp/Messenger sticker maximalism.
**Beat:** nobody puts tactile material in chat chrome — HUB's chat avatars/reactions could be mini clay renders (identity moment, not theme).

## 4. Fintech — Revolut / Monzo / Cash App / Splitwise / Venmo

| App | Navigation | Tab bar detail | Money view | Motion | Identity |
|---|---|---|---|---|---|
| **Revolut** (Revolut 10) | 5 tabs: Home, Cards, Wealth, Lifestyle, Hub; **search at top of every tab**; home widgets pinnable | Bold teal fill active icon; labels always visible (a11y); **active icon scales 24→26px with spring bounce on select** | One net-balance hero per account; per-account themes/backgrounds; multi-currency switching one tap | Bounce/spring on tab select; custom color-system algorithm | Consumer-energy brand; "Hub" tab = everything-else drawer |
| **Monzo** | 5 tabs: Home, Payments, Card, Pots, Account | **Filled coral pill (~52×32px) behind active icon**, not just tint; 11px labels; inactive at ~60% opacity; hairline top border, no blur in light | Pots as separate balance surfaces | Minimal; confident | Pill-highlight = the signature |
| **Starling** | 4 tabs | Teal accent, **labels hidden on inactive items** — documented as harder to scan; avoid | Clean cards | None | Over-minimal |
| **Splitwise** | Groups / Activity / Friends; central **Add-expense sheet with split-method selector** | Plain | **Net balance dominant; settle-up sheet pre-filled with balance, editable to any amount**; leftover-cent assigned randomly (fairness); "simplify debts" greedy view | Sheet-based | Ledger honesty: recompute-on-read, no patched balances |
| **Venmo** | Bottom tabs; Pay/Request central | Blue; social feed of payments | Payment feed w/ memo line (users dislike the social aspect — privacy preference) | Simple | Social-feed-as-ledger; trust via personal association |

**Steal:** Revolut's always-visible labels + spring bounce tab select; Monzo's pill-shaped active indicator (HUB: clay-embossed pill, original material); Splitwise's pre-filled editable settle-up sheet; "search in every tab."
**Avoid:** Starling's hidden inactive labels; Venmo's social payment feed (privacy-hostile); Chase/Barclays purely-conservative weight-only tabs (too cold for youth app).
**Beat:** Revolut 10's home-widget pinning → HUB's home could offer pinned *action widgets* ("split tonight's dinner", "relist couch") with clay iconography — same idea, different domain.

## 5. Community — Reddit / Discord / Geneva

| App | Navigation | Structure | Profile | Empty states | Motion | Identity |
|---|---|---|---|---|---|---|
| **Reddit** | Bottom tabs: Home, Communities, Create, Chat, Inbox | Subreddit = community unit; upvote/downvote sorting | Karma as reputation currency; trophy case | "Be the first to post" prompts | Minimal | Dense text; identity = information density |
| **Discord** | See §3 | Server → channel hierarchy; status/presence rail | Presence-first profile | Discovery tab | — | Blurple + Midnight |
| **Geneva** | Home (community spaces) / Rooms / Chat / Events | **"Homes" = topic spaces; inside: Chat Rooms, Post Rooms (forum), Audio Rooms, Video Rooms (16-up)** — room-type icons carry the nav | Member profiles light | Room-type onboarding | Native-feeling | Gen-Z club aesthetic; organized-group-chat |

**Steal:** Geneva's room-type model (chat/post/audio/video as distinct room *types* under one community) — maps directly to HUB groups (Market thread / Job board / Roommate chat / Voice hangout). Reddit's karma → HUB reputation ribbon.
**Avoid:** Reddit's density; Discord's desktop-first complexity ported to mobile.
**Beat:** Geneva's rooms are all flat-list; HUB can give each room type a *distinct clay icon identity* so "market room" vs "job room" is recognizable at a glance in the tab rail.

## 6. Campus / youth — Fizz / Yubo / Bumble BFF

| App | Navigation | Structure | Profile | Trust/safety | Identity |
|---|---|---|---|---|---|
| **Fizz** | New / Top / "Fizzin'" (last-12h hot) segmented feed; campus-gated by .edu email | Anonymous "fizzes" (short posts), upvote/downvote, custom flairs, campus-local mods, reveal-identity-on-demand DM | Minimal (anonymity-first) | College-gated trust | Reddit-like, campus-only |
| **Yubo** | Live (opens here) / Search / Chats / Friends tabs | No public like counts, no follower metrics — deliberate anti-attention-economy; live rooms first | Expanded customization; facial age estimation + ID checks (now 18+) | Safety-by-design as brand | Real-time over feed |
| **Bumble BFF** | Card-swipe matching → chat | Profile-first; women-message-first in dating, mutual in BFF | Photo + prompts + badges | Verified selfies | Yellow/black |

**Steal:** Yubo's no-public-like-counts → HUB social layer: show *saves* and *deals* (utility metrics), not vanity likes. Fizz's campus gating + "Fizzin'" recency feed → HUB campus feed: "Hot near you (24h)".
**Avoid:** Fizz anonymity model (HUB needs real identity for money/roommate trust — opposite requirement).
**Beat:** nobody merges campus community + real-money trust; HUB's verified reputation ribbon is the differentiator.

## 7. AI — ChatGPT / Perplexity / Meta AI / Gemini mobile

| App | Entry/navigation | Composer | Response design | Identity |
|---|---|---|---|---|
| **ChatGPT** | Sidebar (history, search, pin, rename; Projects/GPTs) → mobile: slide-out drawer | **Unified multimodal input bar**: textarea + `+`/paperclip attach, `@` mentions, image/voice/mic/camera tools; send `↑` circle inset inside textarea; thumbnail strip above input when attaching | Streaming w/ blinking cursor; message actions toolbar (Copy/Regenerate) *visible*, not long-press-hidden; canvas/artifacts side panel | Black/white; orb |
| **Claude** | Projects sidebar | Calm composer; file-aware context | **No avatars, centered content, assistant text flows without bubble** — reading-first | Warm neutrals |
| **Perplexity** | Thread-based | Ask bar with focus/source toggles | **Inline numbered citations** for every claim; sources collapsible | Teal; answer-engine |
| **Meta AI** | Bottom tab in FB/IG/WA + standalone app | Voice-first pill entry; imagine/generate shortcuts | Conversational + generated imagery | Meta blue gradient |
| **Gemini** | Long-press / system entry | Compact: text, camera, voice, context; action suggestions after answers | Lightweight result cards | Google gradient |

2026 convergence (June 2026 chatbot-UI research): mobile = **three-position bottom sheet** (PEEK handle-only 20px / INPUT 96px / HISTORY 75vh, spring `cubic-bezier(0.32,0.72,0,1)`); auto-scroll only within ~100px of bottom + "Jump to latest" button; first-token target <800ms; collapsible thinking section; non-blocking error banner between list and input that preserves the draft.

**Steal:** Inset send-button inside the textarea; suggestion chips under responses; Perplexity-style inline citations for any AI price/availability claim (honest-data rule); collapsible reasoning.
**Avoid:** ChatGPT's sidebar-on-mobile (drawer is fine, hamburger tab is not); full-screen AI takeover — HUB's AI stays a sheet/pill.
**Beat:** nobody ties the assistant to *the current screen's context* as its primary identity — HUB's "Ask HUB" pill is context-aware by default (knows which listing/group you're viewing).

## 8. Discovery / maps — Apple Maps / Google Maps / Yelp

| App | Discovery surface | Structure | Identity |
|---|---|---|---|
| **Apple Maps** (iOS 27) | **Local Lists**: trending collections surfaced inside Guides ("breakfast spots", "kid-friendly"), count + last-updated shown; **Guides We Love** editorial; "Featured in Guides" on place cards; Visited Places | Bottom-card swipe-up; search-field entry; profile → saved Places | Privacy-forward (insights never tied to users); Explore layer default |
| **Google Maps** | **Explore tab**: time-aware personalized carousels ("Neighborhood Gems", "Patio Dining" at lunch); tap category → map+list filter; **Gemini Insider Tips** (parking, dress code, secret menu from reviews); curated influencer lists | Persistent bottom nav; Explore is a first-class tab | AI-concierge; predictive (EV port availability) |
| **Yelp** | Search + category browse; review-first cards | List-first with map toggle; photo-heavy cards | Red; review authority |

**Steal:** Google Explore's **time-aware category carousels** ("Cheap eats open now", "Thrift drops this weekend") → HUB Discover: time+campus-aware horizontal chip carousels that filter the map/list in one tap. Apple Local Lists' count+updated metadata → honest freshness labeling.
**Avoid:** Yelp's review-bomb density; Google's AI tips without citation (HUB: label AI-generated tips as AI, with source).
**Beat:** neither map app connects discovery to *action* (message seller, split cost, join group) — HUB discovery cards carry one-tap clay action buttons.

## 9. 2026 icon-system & gallery consensus

- **Tactile Maximalism** (Mar 2026): clay/jelly/chrome icons that look pressable; "visual texture so convincing the brain registers pressure" — *without* haptics. many-pixels icon-trend roundup: **Soft 3D** = top 2026 trend for young audiences; keep it simple (one confident color + soft highlight reads better at small sizes than heavy render).
- **Awwwards rubric** (distilled 2025–26): Design 40 + Usability 30 + Creativity 20 + Content 10; **one signature moment beats ten effects**; art direction must survive a screenshot; jurors test throttled mid-range hardware; LCP <1.5s / CLS <0.05 / INP <100ms.
- **2026 mobile shifts** (Dreamfind, May 2026): passkeys replace passwords; 3–5 tabs; dark-first design; gestures with discoverable cues; interactions <300ms; pattern-recognition over novelty.
- **Split rule from the research**: 3D clay for *identity moments* (tabs' active state, create button, hero), thin uniform line icons for controls. Never color-mix in chrome — semantic tint only.

---

## Steal / avoid / beat — pattern verdicts

| Pattern | Verdict |
|---|---|
| Monzo pill active-indicator; Revolut 24→26px spring bounce tab select | **Steal** — as HUB's clay-embossed active pill |
| Telegram sparse haptics + opacity-only press | **Steal** — engineered feel, not toy |
| FB Marketplace pictures+price-only first paint | **Steal** — nothing else competes on the card |
| Google Explore time-aware carousels; Apple Local Lists freshness metadata | **Steal** — as honest discovery chips |
| Splitwise pre-filled editable settle-up sheet; recompute-on-read ledger | **Steal** — honesty architecture |
| Perplexity inline citations; ChatGPT inset send button; Claude no-avatar reading flow | **Steal** — for HUB AI sheet |
| Discord actionable notifications; Geneva room-type model; Yubo no-vanity-metrics | **Steal** |
| Starling hidden inactive labels | **Avoid** — fails scanning |
| Venmo social payment feed; Fizz anonymity | **Avoid** — privacy-hostile / trust-hostile for money |
| Full-app Liquid Glass / static blur panels pretending refraction | **Avoid** — can't be replicated in web, reads 2021 |
| Telegram total themeability | **Avoid** — dilutes the one identity |
| Clay in nav chrome as *the* signature | **Beat** — nobody does tactile material in chrome |
| Reputation as a clay "belt of proof" | **Beat** — Airbnb data, HUB material |
| AI pill that knows the current screen | **Beat** — no competitor's assistant is context-native |

---

## 8–12 concrete, implementable recommendations

1. **Tab bar: floating clay-active pill, 4 tabs max.** Build: fixed bottom pill bar (`position:fixed; bottom:calc(12px + env(safe-area-inset-bottom))`), 4 tabs — Home, Discover, Chat, Me. Active tab: clay-embossed pill behind icon (two-layer box-shadow: outer soft drop + inner top highlight), icon scales 24→26px with spring (`cubic-bezier(0.34,1.56,0.64,1)`, ~220ms) + light haptic on select only. Labels always visible, 10–11px, medium. Inactive: 60% opacity line icons. Never hide on scroll (iOS HIG hard rule).
2. **Profile hero: reputation ribbon.** Build: under the avatar, one horizontal swipeable strip of raised clay chips: `[✓ ID verified] [47 deals] [~2h response] [★ 4.8 · 23 reviews]` — each chip: `border-radius:14px`, clay shadows, real numbers from data only, never placeholders. Tap chip → detail sheet with structured review prompts.
3. **Listing card: image + price + ONE clay trust chip.** Build: aspect-ratio-boxed image (no layout shift), price bold 17px overlaid bottom-left, exactly one trust chip top-right (e.g. "✓ 47 deals") in clay material; spring pop-in on save (scale 0.9→1.1→1.0, 300ms). Nothing else on first paint.
4. **Discover: time-aware chip carousels.** Build: horizontally scrollable chip row above the feed ("Open now", "Under $20", "Thrift drops", "Roommates near campus"), time/context-aware ordering; one tap filters map+list simultaneously (like Google Explore). Each chip: 44px min-height, clay-flat style, active = purple fill.
5. **AI: "Ask HUB" pill + three-position sheet.** Build: floating pill above tab bar on every screen (never a tab). Tap → bottom sheet with PEEK (handle) / INPUT / HISTORY (75vh) positions, spring `cubic-bezier(0.32,0.72,0,1)`. Composer: auto-growing textarea, `↑` send circle inset bottom-right, `+` attach bottom-left, suggestion chips under each answer, Perplexity-style inline citations for any price/availability claim. Sheet context = current screen (listing/group being viewed).
6. **Chat list: Telegram-measured rows + actionable notifications.** Build: rows 76px, 54px circular avatars, name 17px/600, preview 15px, time 13px, unread = purple clay pill count. Swipe-left: mute/delete; swipe-right: pin/read. Notifications tab: every item deep-links to its mention/message.
7. **Settle-up: Splitwise-honest money sheet.** Build: group expense → add-expense sheet with split-method selector (equal/exact/%/shares); settle-up sheet pre-fills the exact balance, editable to any partial amount; balances derived from the transaction set (recomputed, never patched); leftover-cent rule documented in UI ("extra cent rotates fairly"). Net balance = one big number, muted red owed / calm green owed-to-you.
8. **Empty states: redirects with live counts.** Build: never "No results". Pattern: "Nothing here yet — {3} sellers active near {campus} · Browse thrift drops" with real counts from data; skeleton→content morph (aspect-ratio boxes), never spinners; acknowledge touch <100ms, optimistic like/comment.
9. **Motion system: one signature ease, sparse haptics.** Build: token `--ease-clay: cubic-bezier(0.34,1.56,0.64,1)`; durations: press 120ms (opacity-only), tab/panel swap 250ms slide+fade, sheet snap 450ms, micro-feedback <300ms. Haptics: none on selection — only on destructive actions and creation confirms. Respect `prefers-reduced-motion` (disable all).
10. **Dark mode: light + true-black OLED, purple warmth.** Build: `--bg: #FFFFFF` / dark `#0A0A0A` (near-black) + separate OLED `#000000` toggle in settings; tonal elevation via background lightening (no shadows in dark); accent saturation reduced 10–15% in dark; clay chips keep inner-highlight so they read as physical on black.
11. **Create flow: clay squish button → radial menu.** Build: center of tab bar = 3D clay "+" that visibly squishes on press (scaleY 0.85 → spring back) and opens a radial/bottom-sheet menu: List an item / Post a job / Find roommate / Ask AI. Camera-first listing; `inputmode="numeric"` on price; equal-split default with progressive disclosure.
12. **Icons: two-tier system, strict.** Build: Tier 1 (identity): 3D clay renders for tab active states, create button, category/room-type icons, trust chips — one confident purple/neutral color + one soft highlight, legible at 24px. Tier 2 (controls): single-weight thin outline line icons, 1.5px stroke, semantic tint only, 44px hit targets. Never mix the tiers in the same control.

## Sources
- Apple Design Awards 2026/2025 winners (9to5Mac, AppleInsider, Gadgets360) — grug hand-drawn UI (App Breakdown #82), Moonlitt Liquid Glass, Tide Guide charts
- Google Play Best of 2025 (blog.google, Android Police) — Focus Friend
- github.com/jonnymuir/umbraco.prism — Monzo/Revolut/Starling/Chase/Barclays tab-bar measurements (2026-07)
- github.com/lintendo/axhub-make telegram DESIGN.md + github.com/termio-sh/termio — Telegram 2026 Liquid Glass, spring constants, sparse haptics, row metrics
- github.com/fogyxt/jarvis — Chatbot UI patterns, June 2026 (three-position sheet, composer, citations)
- github.com/alanvaa06/award-craft — Awwwards rubric distilled 2025–26
- Digital Trends — Google Maps Explore + Gemini Insider Tips; MacObserver/iDownloadBlog — Apple Maps Local Lists (iOS 27)
- Medium: Tactile Maximalism (Mar 2026), Mobile App Design Inspiration 2026 (Dreamfind), Vinted redesign, Splitwise case studies
- github.com/kuldeephumbal/det-admin — Splitwise feature research (settle-up, simplify-debts, rounding)
- many-pixels icon trends 2026; designity.com 2026 mobile trends; TechCrunch/AndroidCentral/PhoneArena — Discord mobile overhaul (Servers/Messages/Notifications/You)
- Forbes India/ideausher — Geneva Homes/Rooms; Stanford/gulfpress — Fizz campus model; morningstar/makeuseof — Yubo 18+, no-like-counts
