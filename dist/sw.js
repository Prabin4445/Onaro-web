/* Onaro service worker — incoming-call Web Push (no build step).
   - push event: shows "Incoming Onaro call" with Answer / Decline actions.
   - notificationclick: Answer opens ./#call=<groupId> (the app joins the call);
     Decline tells the app (BroadcastChannel 'onaro-call') so it can run the
     reject path down the signaling channel; a plain tap just opens the app.
   Honest limits: Web Push only reaches a closed app if (a) Onaro is installed
   to the home screen, (b) notification permission is granted, and (c) the
   free signaling worker is deployed and sending pushes (see server/DEPLOY.md).
   On iOS this needs iOS 16.4+ with the app added to the home screen. */
'use strict';
var BC_NAME = 'onaro-call';

self.addEventListener('push', function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { /* keep defaults */ }
  var callId = d.callId || String(Date.now());
  var title = d.title || 'Incoming Onaro call';
  var body = d.body || (d.callerName ? ('From ' + d.callerName) : 'Someone is calling you on Onaro.');
  var opts = {
    body: body,
    tag: 'onaro-call-' + callId,
    icon: 'icons/icon-192.png',
    badge: 'icons/icon-192.png',
    vibrate: [200, 100, 200, 100, 400],
    renotify: true,
    requireInteraction: true,
    data: { groupId: d.groupId || '', callId: callId, callerName: d.callerName || '' },
    actions: [
      { action: 'answer', title: 'Answer' },
      { action: 'decline', title: 'Decline' }
    ]
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var data = e.notification.data || {};
  var bc = null;
  function tellApp(msg) {
    try {
      bc = new BroadcastChannel(BC_NAME);
      bc.postMessage(msg);
      /* keep the channel alive a moment so the message gets through */
      setTimeout(function () { try { bc.close(); } catch (x) {} }, 1500);
    } catch (x) { /* older browsers: nothing to tell */ }
  }
  if (e.action === 'answer') {
    var url = './#call=' + encodeURIComponent(data.groupId || '');
    /* any open window under this service worker's scope is the app */
    var scope = (self.registration && self.registration.scope) || self.location.origin + '/';
    e.waitUntil(
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
        for (var i = 0; i < list.length; i++) {
          var c = list[i];
          if (c.url && c.url.indexOf(scope) === 0) {
            /* an app window is already open: hand it the call id, don't spawn a tab */
            tellApp({ type: 'answer', callId: data.callId, groupId: data.groupId });
            if (c.focus) return c.focus();
            return;
          }
        }
        return self.clients.openWindow(url);
      })
    );
  } else if (e.action === 'decline') {
    tellApp({ type: 'decline', callId: data.callId, groupId: data.groupId });
  } else {
    e.waitUntil(self.clients.openWindow('./'));
  }
});

/* Tapping "Answer" on an already-open app: the client (js/push.js) listens
   on the same BroadcastChannel and joins the call in place. */
self.addEventListener('message', function () { /* reserved */ });
