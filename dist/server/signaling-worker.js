/* ONARO group-call signaling worker (2026-09-22) — FREE Cloudflare Worker.
   WebSocket signaling for real cross-device group voice calls. Rooms are
   keyed per group call (?room=<groupId>); the worker relays SDP offers /
   answers + ICE candidates, keeps the participant roster, enforces
   admin/subadmin mute (only role admin|subadmin — or self — may mute), and
   relays raise-hand / lower-hand states (admin "Let speak" lowers a raiser's
   hand). Roles are CLAIMED by the app (group creator = admin, g.callAdmins =
   subadmins): honest demo-grade trust — a production backend must verify
   group membership server-side. Rooms live in worker memory (fine for
   demo scale; use Durable Objects if a room ever outgrows one isolate).
   No audio passes through here — WebRTC stays peer-to-peer (STUN only).

   ---- DEPLOY (free Cloudflare account, ~5 minutes) ----
   1. npm i -g wrangler && wrangler login
   2. mkdir onaro-signaling && cd onaro-signaling && wrangler init --yes
   3. Copy this file over src/index.js
   4. wrangler deploy
   5. Copy the printed https://<name>.<you>.workers.dev URL.
   6. In the Onaro app: start any group call, tap the demo label at the top,
      paste wss://<name>.<you>.workers.dev/call, Save. Calls are now real.
   Full plain-language guide: server/DEPLOY.md

   ---- protocol (JSON over ws) ----
   C->S: {type:'join',room,name,role,peerId} | {type:'join',room,watch:true}
         {type:'signal',to,kind,data}            kind: offer|answer|ice
         {type:'mute'|'unmute',target}
         {type:'request-unmute'}                  -> forwarded to admins
         {type:'role',name,role}                  admin only: subadmin|member
         {type:'raise-hand',raised}               broadcast my hand state
         {type:'lower-hand',target}               admin/subadmin: clear a raiser's hand
         {type:'leave'}
   S->C: {type:'welcome',you,callId,isFirst,peers:[{peerId,name,role,muted,mutedBy,handRaised}]}
         {type:'peer-join',peer} {type:'peer-leave',peerId}
         {type:'signal',from,kind,data}
         {type:'muted'|'unmuted',target,by,byName}
         {type:'unmute-request',from,fromName}
         {type:'role-changed',name,role,by}
         {type:'hand',from,name,raised}           someone's hand state changed
         {type:'lower-hand'}                      directed: you must lower your hand
         {type:'call-started',room,callId,by,at}  (watchers only)
         {type:'call-ended',room}                 (watchers only)
         {type:'error',message}
*/
const rooms = new Map(); // roomId -> {peers, watchers, callId, by, at}

function roomOf(id) {
  let r = rooms.get(id);
  if (!r) { r = { peers: new Map(), watchers: new Set(), callId: null, by: null, at: 0 }; rooms.set(id, r); }
  return r;
}
function send(ws, obj) { try { ws.send(JSON.stringify(obj)); } catch (e) {} }
function pub(p) { return { peerId: p.peerId, name: p.name, role: p.role, muted: p.muted, mutedBy: p.mutedBy, handRaised: !!p.handRaised }; }
function bcast(room, obj, except) { room.peers.forEach(function (p) { if (!except || p.ws !== except) send(p.ws, obj); }); }
function cleanRole(r) { return r === 'admin' || r === 'subadmin' ? r : 'member'; }

export default {
  async fetch(req) {
    const url = new URL(req.url);
    if (url.pathname !== '/call')
      return new Response('Onaro call signaling. WebSocket endpoint: /call?room=<groupId>', { status: 200 });
    if (req.headers.get('Upgrade') !== 'websocket')
      return new Response('Expected WebSocket', { status: 426 });
    const roomId = url.searchParams.get('room');
    if (!roomId) return new Response('missing ?room=', { status: 400 });
    const pair = new WebSocketPair();
    handleSocket(pair[1], roomId);
    return new Response(null, { status: 101, webSocket: pair[0] });
  }
};

function handleSocket(ws, roomId) {
  ws.accept();
  const room = roomOf(roomId);
  let me = null;      // {peerId,name,role,ws,muted,mutedBy}
  let watching = false;

  function cleanup() {
    if (me) { room.peers.delete(me.peerId); bcast(room, { type: 'peer-leave', peerId: me.peerId }); me = null; }
    if (watching) { room.watchers.delete(ws); watching = false; }
    if (room.peers.size === 0) {
      room.watchers.forEach(function (w) { send(w, { type: 'call-ended', room: roomId }); });
      rooms.delete(roomId);
    }
  }

  ws.addEventListener('message', function (ev) {
    let m; try { m = JSON.parse(ev.data); } catch (e) { send(ws, { type: 'error', message: 'bad json' }); return; }

    if (m.type === 'join') {
      if (m.watch) { // lightweight watcher: only call-started / call-ended
        watching = true; room.watchers.add(ws);
        if (room.callId) send(ws, { type: 'call-started', room: roomId, callId: room.callId, by: room.by, at: room.at });
        return;
      }
      if (!m.peerId || !m.name) { send(ws, { type: 'error', message: 'join needs peerId+name' }); return; }
      const isFirst = room.peers.size === 0;
      me = { peerId: String(m.peerId), name: String(m.name).slice(0, 40), role: cleanRole(m.role),
             ws: ws, muted: false, mutedBy: null, handRaised: false };
      if (isFirst) {
        room.callId = 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
        room.by = me.name; room.at = Date.now();
        room.watchers.forEach(function (w) { send(w, { type: 'call-started', room: roomId, callId: room.callId, by: room.by, at: room.at }); });
      }
      room.peers.set(me.peerId, me);
      const roster = [];
      room.peers.forEach(function (p) { if (p.peerId !== me.peerId) roster.push(pub(p)); });
      send(ws, { type: 'welcome', you: me.peerId, callId: room.callId, isFirst: isFirst, peers: roster });
      bcast(room, { type: 'peer-join', peer: pub(me) }, ws);
      return;
    }

    if (!me && !watching) { send(ws, { type: 'error', message: 'join first' }); return; }

    if (m.type === 'signal') {
      const tp = room.peers.get(m.to);
      if (tp) send(tp.ws, { type: 'signal', from: me.peerId, kind: m.kind, data: m.data });
      return;
    }

    if (m.type === 'mute' || m.type === 'unmute') {
      const tp = room.peers.get(m.target);
      const selfMute = tp && me && tp.peerId === me.peerId;
      const privileged = me && (me.role === 'admin' || me.role === 'subadmin');
      if (!tp || !me || (!selfMute && !privileged)) { send(ws, { type: 'error', message: 'not allowed' }); return; }
      if (!selfMute && tp.role === 'admin' && me.role !== 'admin') { send(ws, { type: 'error', message: 'not allowed' }); return; }
      tp.muted = (m.type === 'mute'); tp.mutedBy = tp.muted ? me.name : null;
      bcast(room, { type: tp.muted ? 'muted' : 'unmuted', target: tp.peerId, by: me.peerId, byName: me.name });
      return;
    }

    if (m.type === 'request-unmute') {
      if (!me) return;
      room.peers.forEach(function (p) {
        if (p.role === 'admin' || p.role === 'subadmin')
          send(p.ws, { type: 'unmute-request', from: me.peerId, fromName: me.name });
      });
      return;
    }

    if (m.type === 'raise-hand') {
      if (!me) return;
      me.handRaised = !!m.raised;
      bcast(room, { type: 'hand', from: me.peerId, name: me.name, raised: me.handRaised }, ws);
      return;
    }

    if (m.type === 'lower-hand') {
      // admin/subadmin "Let speak": clear a raiser's hand. The target's own
      // client clears its local state via the directed message, then
      // re-broadcasts raised:false through 'raise-hand' so all tabs agree.
      if (!me) return;
      const tp = room.peers.get(m.target);
      if (!tp) { send(ws, { type: 'error', message: 'no such peer' }); return; }
      const selfLower = tp.peerId === me.peerId;
      const privileged = me.role === 'admin' || me.role === 'subadmin';
      if (!selfLower && !privileged) { send(ws, { type: 'error', message: 'not allowed' }); return; }
      if (!selfLower && tp.role === 'admin' && me.role !== 'admin') { send(ws, { type: 'error', message: 'not allowed' }); return; }
      tp.handRaised = false;
      send(tp.ws, { type: 'lower-hand' });
      bcast(room, { type: 'hand', from: tp.peerId, name: tp.name, raised: false }, tp.ws);
      return;
    }

    if (m.type === 'role') { // promote / demote subadmin — group admin only
      if (!me || me.role !== 'admin') { send(ws, { type: 'error', message: 'admin only' }); return; }
      const nr = m.role === 'subadmin' ? 'subadmin' : 'member';
      let tp = null;
      room.peers.forEach(function (p) { if (p.name === m.name) tp = p; });
      if (tp && tp.role !== 'admin') { tp.role = nr; bcast(room, { type: 'role-changed', name: tp.name, role: nr, by: me.name }); }
      return;
    }

    if (m.type === 'leave') { try { ws.close(); } catch (e) {} return; }
  });

  ws.addEventListener('close', cleanup);
  ws.addEventListener('error', cleanup);
}
