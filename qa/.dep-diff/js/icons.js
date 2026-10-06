/* HUB 3D clay icon family — generated asset helper (Worker A).
 * Pure helper: inlines the manifest from icons/manifest.json.
 * HUB.icons.icon(name, cls) -> HTML string with <img> + srcset (96px/144px)
 *   and an onerror hook that swaps a broken/missing icon for its emoji fallback,
 *   so nothing ever renders blank. Unknown names return ''.
 * HUB.icons.fallback(img) -> replaces the <img> with the emoji fallback span.
 * No dependencies. Safe to load before or after any other hub script.
 */
(function(){'use strict';

var M = {"act-buy":{"fb":"🛍️","src":"icons/act-buy.png","src2x":"icons/act-buy@2x.png"},"act-event":{"fb":"📅","src":"icons/act-event.png","src2x":"icons/act-event@2x.png"},"act-expense":{"fb":"🧾","src":"icons/act-expense.png","src2x":"icons/act-expense@2x.png"},"act-group":{"fb":"👥","src":"icons/nav-groups.png","src2x":"icons/nav-groups@2x.png"},"act-job":{"fb":"🪖","src":"icons/act-job.png","src2x":"icons/act-job@2x.png"},"act-memory":{"fb":"🧠","src":"icons/act-memory.png","src2x":"icons/act-memory@2x.png"},"act-post":{"fb":"📣","src":"icons/act-post.png","src2x":"icons/act-post@2x.png"},"act-sell":{"fb":"🏷️","src":"icons/act-sell.png","src2x":"icons/act-sell@2x.png"},"act-task":{"fb":"📋","src":"icons/act-task.png","src2x":"icons/act-task@2x.png"},"ask-hub":{"fb":"✨","src":"icons/ask-hub.png","src2x":"icons/ask-hub@2x.png"},"ic-bell":{"fb":"🔔","src":"icons/ic-bell.png","src2x":"icons/ic-bell@2x.png"},"ic-chat":{"fb":"💬","src":"icons/ic-chat.png","src2x":"icons/ic-chat@2x.png"},"ic-pulse":{"fb":"⚡","src":"icons/ic-pulse.png","src2x":"icons/ic-pulse@2x.png"},"ic-search":{"fb":"🔍","src":"icons/ic-search.png","src2x":"icons/ic-search@2x.png"},"intent-borrow":{"fb":"🤝","src":"icons/intent-borrow.png","src2x":"icons/intent-borrow@2x.png"},"intent-buy":{"fb":"🛍️","src":"icons/act-buy.png","src2x":"icons/act-buy@2x.png"},"intent-free":{"fb":"🎁","src":"icons/intent-free.png","src2x":"icons/intent-free@2x.png"},"intent-sell":{"fb":"🏷️","src":"icons/act-sell.png","src2x":"icons/act-sell@2x.png"},"intent-swap":{"fb":"🔄","src":"icons/intent-swap.png","src2x":"icons/intent-swap@2x.png"},"nav-discover":{"fb":"📍","src":"icons/nav-discover.png","src2x":"icons/nav-discover@2x.png"},"nav-groups":{"fb":"👥","src":"icons/nav-groups.png","src2x":"icons/nav-groups@2x.png"},"nav-home":{"fb":"🏠","src":"icons/nav-home.png","src2x":"icons/nav-home@2x.png"},"nav-market":{"fb":"🏪","src":"icons/nav-market.png","src2x":"icons/nav-market@2x.png"},"nav-me":{"fb":"🙂","src":"icons/nav-me.png","src2x":"icons/nav-me@2x.png"},"nav-work":{"fb":"💼","src":"icons/nav-work.png","src2x":"icons/nav-work@2x.png"},"stat-bill":{"fb":"🧾","src":"icons/stat-bill.png","src2x":"icons/stat-bill@2x.png"},"stat-docs":{"fb":"📄","src":"icons/stat-docs.png","src2x":"icons/stat-docs@2x.png"},"stat-events":{"fb":"📅","src":"icons/act-event.png","src2x":"icons/act-event@2x.png"},"stat-jobs":{"fb":"💼","src":"icons/nav-work.png","src2x":"icons/nav-work@2x.png"},"stat-messages":{"fb":"💬","src":"icons/stat-messages.png","src2x":"icons/stat-messages@2x.png"},"stat-money":{"fb":"💰","src":"icons/stat-money.png","src2x":"icons/stat-money@2x.png"}};

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}

var api = {
  map: M,

  icon: function(name, cls){
    var m = M[name];
    if(!m) return '';
    return '<span class="ico'+(cls?' '+esc(cls):'')+'">'
      + '<img data-icon="'+esc(name)+'" src="'+esc(m.src)+'"'
      + ' srcset="'+esc(m.src2x)+' 96w, '+esc(m.src)+' 144w" sizes="48px"'
      + ' alt="" loading="lazy" draggable="false"'
      + ' onerror="HUB.icons.fallback(this)">'
      + '</span>';
  },

  fallback: function(img){
    try{
      var name = img.getAttribute('data-icon') || '';
      var m = M[name] || {};
      var s = document.createElement('span');
      s.className = 'ico-fb';
      s.setAttribute('data-icon', name);
      s.textContent = m.fb || '❔';
      img.replaceWith(s);
    }catch(e){ /* never let a broken icon break the page */ }
  }
};

window.HUB = Object.assign(window.HUB || {}, {icons: api});

})();
