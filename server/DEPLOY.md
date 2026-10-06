# Onaro group calls — free signaling server (deploy once)

**What this is:** Group voice calls in the Onaro app need a tiny server so two
phones can find each other and exchange call setup messages (the actual voice
goes directly phone-to-phone, never through the server). Until this is
deployed, calls run in **demo mode**: they only work between tabs of the same
browser, and the app says so on screen.

**Cost:** $0 — Cloudflare's free tier is plenty for this.

## What you need

1. A free Cloudflare account → https://dash.cloudflare.com/sign-up
2. Node.js on your computer (https://nodejs.org — the LTS version is fine)

## Deploy (about 5 minutes)

Open a terminal and run:

```bash
npm i -g wrangler
wrangler login
```

A browser window opens — log in with your Cloudflare account.

```bash
mkdir onaro-signaling
cd onaro-signaling
wrangler init --yes
```

Now copy the file `server/signaling-worker.js` from the Onaro project over
`src/index.js` in this new folder (replace its contents completely), then:

```bash
wrangler deploy
```

Cloudflare prints a URL like:

```
https://onaro-signaling.yourname.workers.dev
```

## Connect the app to it

1. In the Onaro app, open any group chat and tap the 📞 call button.
2. Tap the **demo label** at the top of the call screen ("Demo — deploy the
   free signaling worker for real calls.").
3. Paste your URL with `wss://` in front and `/call` at the end, e.g.
   `wss://onaro-signaling.yourname.workers.dev/call`, then **Save**.
4. The label changes to "Live call · connected via your signaling worker".
   Calls now connect across devices. (Use **Use demo mode** to switch back.)

## Honest notes

- The worker only relays call setup messages (who's joining, mute states,
  raise-hand states). Voice audio is peer-to-peer and never touches Cloudflare.
- The worker trusts the app about who is admin/subadmin (the app knows the
  group creator). For a friends-and-campus preview this is fine; a public
  launch would need real login verification on the server.
- Rooms live in the worker's memory — if Cloudflare restarts it, active
  calls drop and everyone just rejoins. Free tier, no database needed.
- To update later: edit the file, run `wrangler deploy` again.

## Incoming-call push notifications (Web Push)

**What this is:** when the app is closed, a caller can't reach the other
person's screen — browsers can't do that on their own. Web Push closes the
gap: the worker sends a push to the callee's device, the phone shows
"Incoming Onaro call" with **Answer** / **Decline** buttons, and tapping
Answer opens the app straight into the call.

**Honest limits (tell users this):**
- No website can take over the iOS lock screen like a native phone call —
  CallKit is native-apps-only. Push opens the app; the full-screen answer UI
  lives inside the app.
- The person being called needs ALL of: Onaro installed to the home screen
  ("Add to Home Screen"), notification permission granted (the app asks when
  they flip the "Call notifications" toggle in Me > Settings), and this
  worker deployed with the steps below. On iOS this needs iOS 16.4+.
- Without the worker, the toggle says so honestly instead of pretending.

### 1. Generate VAPID keys (once)

```bash
npx -y web-push generate-vapid-keys
```

You get a public/private pair. Keep the private key secret.

### 2. Put the public key in the app

Open `js/push.js` in the Onaro project and replace
`REPLACE_WITH_YOUR_VAPID_PUBLIC_KEY` with your public key. Redeploy the
app (surge) afterwards.

### 3. Add the /push endpoint to the worker

In `src/index.js` (your copy of `server/signaling-worker.js`), next to the
`/call` handler, add:

```js
const SUBS = new Map(); // endpoint -> { sub, ts } (demo: memory; use KV in production)

if (url.pathname === '/push' && request.method === 'POST') {
  const body = await request.json().catch(() => ({}));
  if (body.remove) {
    for (const [ep, v] of SUBS) if (body.endpoint && ep === body.endpoint) SUBS.delete(ep);
    return new Response('ok');
  }
  if (body.subscription && body.subscription.endpoint)
    SUBS.set(body.subscription.endpoint, { sub: body.subscription, ts: Date.now() });
  return new Response('ok');
}
```

### 4. Send a push when a call starts

Wherever the worker learns a call started in a room (the `call-started`
broadcast in `handleSocket`), also push to every stored subscription:

```js
import webpush from 'web-push'; // npm i web-push (or use fetch to an push service)
webpush.setVapidDetails('mailto:you@example.com', VAPID_PUBLIC, VAPID_PRIVATE);
// payload the app's sw.js understands:
const payload = JSON.stringify({ callId, groupId, callerName,
  title: 'Incoming Onaro call', body: 'From ' + callerName });
for (const { sub } of SUBS.values())
  webpush.sendNotification(sub, payload).catch(e => {
    if (e.statusCode === 410 || e.statusCode === 404) SUBS.delete(sub.endpoint); // gone
  });
```

Notes:
- The app posts its subscription to `https://<your-worker>/push` automatically
  when the user enables "Call notifications" (it derives the URL from the
  saved `wss://…/call` worker URL).
- `mailto:` can be any contact address you own.
- Memory storage loses subscriptions on worker restart — fine for the free
  preview; use Workers KV before any public launch.
- Cost stays $0 on the free tier at friends-and-campus scale.
