# Onaro HUB — Completeness Audit: "What are we missing?"
**Date:** 2026-09-22 · **Read-only audit — no code changed, nothing deployed**

## Method
Two parallel tracks:
1. **In-app crawl** — CDP headless Chromium, 390×844 mobile emulation, iPhone UA/touch, fresh profiles per run, dark + light. Every tab (Home, Daily, Market, Work, Groups, Me), every sheet, overlay, detail view, menu, and reachable flow driven end-to-end. Zero console errors in every run. Evidence: `qa/audit-missing/` (screenshots) + `qa/audit-missing/findings-final.json`.
2. **Competitive research** — vs Facebook Marketplace, OfferUp, Mercari, Depop, Poshmark, eBay, WhatsApp, Telegram, Signal, iMessage, Discord, Reddit, Facebook Groups, TaskRabbit, Fiverr, Thumbtack, Nextdoor, MyStudyLife, Google Classroom, Canvas Student, Google Discover, TikTok, iOS widgets.

---

## Tier 1 — Broken (things that don't work today): **1 item**
1. **Daily → Happening: created events can NEVER be deleted.** Events made via the Create FAB have no delete affordance in the detail sheet and `js/daily.js` has no remove path. User-created data with zero removal path — highest priority fix.
   Evidence: `qa/audit-missing/audit-missing-evnodelete-light.png` · Feasibility: browser-local.

---

## Tier 2 — Expected-but-missing (real apps have it; browser-local feasible unless marked): **26 items**

**Chat** (vs WhatsApp/Telegram/iMessage)
- Voice notes (record/playback; transcription via free Web Speech API in Chrome) — youth send these constantly; absence felt in the first conversation.
- Quote-reply + emoji reactions — group chats become unreadable without replies once 3+ people talk.
- In-chat message search (old address/link retrieval).
- Edit message / delete-for-me (long-press → edit is session-one muscle memory).
- Media captions on photo send (meme without context = broken joke).
- Pinned messages + per-chat mute (admins want a pinned rules message immediately).

**Market** (vs FB Marketplace/OfferUp/Mercari/Depop/Poshmark/eBay)
- Saved searches (saves browser-local; **live new-match/price-drop alerts = backend**). FB buyers set this up in session one.
- Make-an-offer / negotiation flow (UI browser-local; **real counterparty = backend**). Resale shoppers look for "Make offer" instinctively.
- Item condition taxonomy on listings (New / Like new / Good / Fair) — buyers scan for it on every used listing.
- Seller trust surface (local listing-count stats browser-local; **real ratings = backend**).
- Meetup-safety tooling — safety tips/checklist browser-local (**live trip-sharing = backend**); youth audience will ask "is meeting up safe?" early.

**Groups** (vs Discord/Reddit/FB Groups)
- Report content / report member with reason → mod queue — safety flows are the first thing a cautious new member or parent looks for.
- Roles beyond admin (moderator tier + permissions) — any group over ~15 people wants this.
- Mute / timeout / ban toolkit (we have join-request remove only).
- Rules page + pinned/featured posts (persistent "read the rules" surface).
- Events with RSVPs — community groups live on events; "when's the next meetup?" has nowhere to live.

**Work — micro-jobs** (vs TaskRabbit/Fiverr/Thumbtack)
- Job filters: category + max price + distance (the expected browse trio).
- Structured posting with price estimates (category-suggested rates; AI keyword suggestion = "AI as glue" fit).
- Worker profiles with local history (**real ratings/reputation = backend** — #1 trust surface).
- In-job 1:1 chat thread with job context (vs negotiating in DMs with no context).

**Classes / campus** (vs MyStudyLife/Classroom/Canvas)
- Assignment / homework tracker with due dates (first thing students enter after their timetable).
- Exam countdowns + revision reminders (huge in finals season).
- ICS file import for timetable (**live calendar sync = backend/OAuth**).
- Grade trends over terms (we have GPA snapshot only; trends answer "am I improving?").

**Cross-cutting**
- First-run onboarding / 60-second tutorial — an "everything app" with no orientation reads as overwhelming on day one.
- Global app search over everything — user already reported search "completely broken"; in an everything-app, search is primary navigation for returning users.
- Report + block user (people-level, not just group gating) — youth-app safety baseline.
- Per-topic notification preferences + quiet hours (in-app routing browser-local; **real push = backend**).
- Export my data (JSON) + delete-everything — GDPR-era baseline, browser-local.
- Help / FAQ center (FAQ browser-local; **human support = backend**).

---

## Tier 3 — Polish gaps: **12 items**
- **No confirmation on delete** (4 surfaces): Home → Appointments ✕ deletes instantly; Home → Classes → Manage ✕ deletes instantly; Me → Vault memory delete instant; Me → Skills chip tap removes instantly. Toast-only after the fact.
  Evidence: `qa/audit-missing/audit-missing-{apdel,cldel,vaultdel,skilldel}-*.png` · Feasibility: browser-local.
- **"✓ Verified" badge on Groups → People sample profile** reads as real verification in a screenshot (page does carry a "Sample" tag + disclaimer — low severity, but the badge itself is the honest-label risk).
  Evidence: `qa/audit-missing/audit-missing-people-verified-badge-dark.png`.
- Offline honesty: the static app largely works offline but never says so; no queued-action outbox for flaky campus Wi-Fi.
- Accessibility pass never done: VoiceOver/TalkBack labels, focus order + focus traps in sheets, 44px touch targets, dynamic text scaling (iOS text-scaling will break fixed-pixel layouts on first use). Reduced-motion is already respected in carousels.
- Dark/light auto-schedule (follow system / sunset) — manual toggle only today.
- Seller listing insights (views/saves/messages per listing) — power-seller feature.
- Polls: no multi-select, timed auto-close, or anonymous voting (we have basic polls).
- Invite-link controls: permanent #join= links with no expiry/max-use/revoke (**real enforcement = backend**).
- Announcements vs discussion separation (single group chat mixes everything).
- Member directory with roles + search (essential at 50+ members).
- Join/screening questions on request-to-join (private-household use case would love this).
- Group insights (growth/engagement stats for admins).

---

## Tier 4 — Backend-blocked (impossible browser-local; named honestly, not hand-waved): **12 items**
1. **Push notifications when the app is closed** — Web Push needs a push server (VAPID); iOS additionally needs the PWA installed. While the page is open the Notification API works, but no backend = no alerts when closed. **Needs honest in-app copy NOW** — users will assume chat notifies them; the first missed message is the moment of betrayal.
2. Typing indicators / cross-device seen-by presence (can't know the other person's state without a server).
3. Secure payment / escrow on Work + dispute arbitration (payments/payouts/KYC infra).
4. Identity / background verification for workers (third-party services, legal).
5. Real cross-device sync + real accounts (data dies with browser data today).
6. Live listing / match / price-drop alerts (nothing watches while app is closed).
7. Real seller ratings & reviews.
8. Shipping labels / carrier integration (Market stays local-only by design without this).
9. Make-an-offer against real counterparties.
10. Live calendar sync (OAuth).
11. Native iOS/Android home-screen widgets (**platform-blocked** for a static web app, not just backend).
12. Chat cloud backup/sync (export-to-file IS browser-local feasible; real sync is not).

---

## Verified working (crawl coverage — not missing)
Home (6 tabs, 7 glance tiles all opening details, ask pill, capsule pill, appointments/classes cards), Daily (event create, 9-action create-FAB grid, gym setup drawer + reset with proper confirm sheet), Market (radius filter, post→publish, detail, Message seller → safety checklist → thread → send, two-tap listing delete), Work (post, accept with confirm, delete with confirm), Groups (create → make-live → invite share sheet, member chat send, call opens with honest "Demo — deploy the free signaling worker" label, request-to-join, households, contact-sync manual fallback, mutual-follow message gate), Me (profile edit, vault add, skill add, DOB, safety score "Demo" label), global search with good no-results state, pulse, notifications, chat list, astro calendar + horoscope, es/ne/hi i18n on Home, settings persistence across reload.

## Unreachable this pass (needs PraBin or infra)
Physical-iPhone touch feel · native share sheet (`navigator.share` absent headless) · Contact Picker · microphone/calls · camera uploads · live weather (sandbox egress blocked) · push (in-app only) · chat empty state (sample threads seeded) · onboarding (seeded past it).

## Standing caveats
- All data is browser-local demo data; real cross-device behavior needs a backend.
- Physical-iPhone feel is PraBin's check — desktop QA passes don't cover touch.

**Totals: Broken 1 · Expected-but-missing 26 · Polish 12 · Backend-blocked 12 = 51 items**
