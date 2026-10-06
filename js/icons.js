/* HUB 3D clay icon family — generated asset helper (Worker A).
 * Pure helper: inlines the manifest from icons/manifest.json.
 * HUB.icons.icon(name, cls) -> HTML string with <img> + srcset (96px/144px)
 *   and an onerror hook that swaps a broken/missing icon for its emoji fallback,
 *   so nothing ever renders blank. Unknown names return ''.
 * HUB.icons.fallback(img) -> replaces the <img> with the emoji fallback span.
 * No dependencies. Safe to load before or after any other hub script.
 */
(function(){'use strict';

var M = {"act-buy":{"fb":"🛍️","src":"icons/act-buy.png","src2x":"icons/act-buy@2x.png"},"act-event":{"fb":"📅","src":"icons/act-event.png","src2x":"icons/act-event@2x.png"},"act-expense":{"fb":"🧾","src":"icons/act-expense.png","src2x":"icons/act-expense@2x.png"},"act-group":{"fb":"👥","src":"icons/nav-groups.png","src2x":"icons/nav-groups@2x.png"},"act-job":{"fb":"🪖","src":"icons/act-job.png","src2x":"icons/act-job@2x.png"},"act-memory":{"fb":"🧠","src":"icons/act-memory.png","src2x":"icons/act-memory@2x.png"},"act-post":{"fb":"📣","src":"icons/act-post.png","src2x":"icons/act-post@2x.png"},"act-sell":{"fb":"🏷️","src":"icons/act-sell.png","src2x":"icons/act-sell@2x.png"},"act-task":{"fb":"📋","src":"icons/act-task.png","src2x":"icons/act-task@2x.png"},"ask-hub":{"fb":"✨","src":"icons/ask-hub.png","src2x":"icons/ask-hub@2x.png"},"ic-bell":{"fb":"🔔","src":"icons/ic-bell.png","src2x":"icons/ic-bell@2x.png"},"ic-chat":{"fb":"💬","src":"icons/ic-chat.png","src2x":"icons/ic-chat@2x.png"},"ic-pulse":{"fb":"⚡","src":"icons/ic-pulse.png","src2x":"icons/ic-pulse@2x.png"},"ic-search":{"fb":"🔍","src":"icons/ic-search.png","src2x":"icons/ic-search@2x.png"},"intent-borrow":{"fb":"🤝","src":"icons/intent-borrow.png","src2x":"icons/intent-borrow@2x.png"},"intent-buy":{"fb":"🛍️","src":"icons/act-buy.png","src2x":"icons/act-buy@2x.png"},"intent-free":{"fb":"🎁","src":"icons/intent-free.png","src2x":"icons/intent-free@2x.png"},"intent-sell":{"fb":"🏷️","src":"icons/act-sell.png","src2x":"icons/act-sell@2x.png"},"intent-swap":{"fb":"🔄","src":"icons/intent-swap.png","src2x":"icons/intent-swap@2x.png"},"nav-daily":{"fb":"📅","src":"icons/nav-daily.png","src2x":"icons/nav-daily@2x.png"},"nav-discover":{"fb":"📍","src":"icons/nav-discover.png","src2x":"icons/nav-discover@2x.png"},"nav-groups":{"fb":"👥","src":"icons/nav-groups.png","src2x":"icons/nav-groups@2x.png"},"nav-home":{"fb":"🏠","src":"icons/nav-home.png","src2x":"icons/nav-home@2x.png"},"nav-market":{"fb":"🏪","src":"icons/nav-market.png","src2x":"icons/nav-market@2x.png"},"nav-me":{"fb":"🙂","src":"icons/nav-me.png","src2x":"icons/nav-me@2x.png"},"nav-me-girl":{"fb":"👩","src":"icons/nav-me-girl.png","src2x":"icons/nav-me-girl@2x.png"},"nav-me-rainbow":{"fb":"🌈","src":"icons/nav-me-rainbow.png","src2x":"icons/nav-me-rainbow@2x.png"},"nav-me-ninja":{"fb":"🥷","src":"icons/nav-me-ninja.png","src2x":"icons/nav-me-ninja@2x.png"},"nav-prof":{"fb":"🎓","src":"icons/nav-prof.png","src2x":"icons/nav-prof@2x.png"},"nav-work":{"fb":"💼","src":"icons/nav-work.png","src2x":"icons/nav-work@2x.png"},"stat-bill":{"fb":"🧾","src":"icons/stat-bill.png","src2x":"icons/stat-bill@2x.png"},"stat-docs":{"fb":"📄","src":"icons/stat-docs.png","src2x":"icons/stat-docs@2x.png"},"stat-events":{"fb":"📅","src":"icons/act-event.png","src2x":"icons/act-event@2x.png"},"stat-jobs":{"fb":"💼","src":"icons/nav-work.png","src2x":"icons/nav-work@2x.png"},"stat-messages":{"fb":"💬","src":"icons/stat-messages.png","src2x":"icons/stat-messages@2x.png"},"stat-money":{"fb":"💰","src":"icons/stat-money.png","src2x":"icons/stat-money@2x.png"},"calc-title":{"fb":"🧮","src":"icons/calc-title.png","src2x":"icons/calc-title@2x.png"},"calc-adv":{"fb":"🎚️","src":"icons/calc-adv.png","src2x":"icons/calc-adv@2x.png"},"calc-keypad":{"fb":"🔢","src":"icons/calc-keypad.png","src2x":"icons/calc-keypad@2x.png"},"calc-snd-on":{"fb":"🔊","src":"icons/calc-snd-on.png","src2x":"icons/calc-snd-on@2x.png"},"calc-snd-off":{"fb":"🔇","src":"icons/calc-snd-off.png","src2x":"icons/calc-snd-off@2x.png"},"call-micmute":{"fb":"🎙️","src":"icons/call-micmute.png","src2x":"icons/call-micmute@2x.png"},"calc-set":{"fb":"⚙️","src":"icons/calc-set.png","src2x":"icons/calc-set@2x.png"}};

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}

/* Event-category clay icons (2026): emoji -> clay 3D icon for event cards. */
Object.assign(M,{
 'ev-food':{fb:'🍕',src:'icons/ev-food.png',src2x:'icons/ev-food@2x.png'},
 'ev-career':{fb:'💼',src:'icons/ev-career.png',src2x:'icons/ev-career@2x.png'},
 'ev-sports':{fb:'🏀',src:'icons/ev-sports.png',src2x:'icons/ev-sports@2x.png'},
 'ev-study':{fb:'📚',src:'icons/ev-study.png',src2x:'icons/ev-study@2x.png'},
 'ev-art':{fb:'🎨',src:'icons/ev-art.png',src2x:'icons/ev-art@2x.png'},
 'ev-party':{fb:'🎉',src:'icons/ev-party.png',src2x:'icons/ev-party@2x.png'},
 /* Subject icons (2026): clay 3D symbol for each school subject. */
 'subj-math':{fb:'🧮',src:'icons/subj-math.png',src2x:'icons/subj-math@2x.png'},
 'subj-bio':{fb:'🧬',src:'icons/subj-bio.png',src2x:'icons/subj-bio@2x.png'},
 'subj-chem':{fb:'⚗️',src:'icons/subj-chem.png',src2x:'icons/subj-chem@2x.png'},
 'subj-physics':{fb:'⚛️',src:'icons/subj-physics.png',src2x:'icons/subj-physics@2x.png'},
 'subj-computer':{fb:'💻',src:'icons/subj-computer.png',src2x:'icons/subj-computer@2x.png'},
 'subj-english':{fb:'📖',src:'icons/subj-english.png',src2x:'icons/subj-english@2x.png'},
 'subj-history':{fb:'🏛️',src:'icons/subj-history.png',src2x:'icons/subj-history@2x.png'},
 'subj-language':{fb:'🌍',src:'icons/subj-language.png',src2x:'icons/subj-language@2x.png'},
 'subj-music':{fb:'🎵',src:'icons/subj-music.png',src2x:'icons/subj-music@2x.png'},
 'subj-science':{fb:'🔬',src:'icons/subj-science.png',src2x:'icons/subj-science@2x.png'},
 /* Appointment icons (2026): clay 3D symbol for each appointment kind. */
 'appt-medical':{fb:'🩺',src:'icons/appt-medical.png',src2x:'icons/appt-medical@2x.png'},
 'appt-dental':{fb:'🦷',src:'icons/appt-dental.png',src2x:'icons/appt-dental@2x.png'},
 'appt-car':{fb:'🚗',src:'icons/appt-car.png',src2x:'icons/appt-car@2x.png'},
 /* Period & Wellness clay icons (2026): wl-* set for the wellness dashboard. */
 'wl-heart':{fb:'🩷',src:'icons/wl-heart.png',src2x:'icons/wl-heart@2x.png'},
 'wl-droplet':{fb:'💧',src:'icons/wl-droplet.png',src2x:'icons/wl-droplet@2x.png'},
 'wl-calendar':{fb:'📅',src:'icons/wl-calendar.png',src2x:'icons/wl-calendar@2x.png'},
 'wl-activity':{fb:'💓',src:'icons/wl-activity.png',src2x:'icons/wl-activity@2x.png'},
 'wl-smile':{fb:'🙂',src:'icons/wl-smile.png',src2x:'icons/wl-smile@2x.png'},
 'wl-moon':{fb:'🌙',src:'icons/wl-moon.png',src2x:'icons/wl-moon@2x.png'},
 'wl-leaf':{fb:'🍃',src:'icons/wl-leaf.png',src2x:'icons/wl-leaf@2x.png'},
 'wl-sprout':{fb:'🌱',src:'icons/wl-sprout.png',src2x:'icons/wl-sprout@2x.png'},
 'wl-flower':{fb:'🌸',src:'icons/wl-flower.png',src2x:'icons/wl-flower@2x.png'},
 'wl-bowl':{fb:'🥣',src:'icons/wl-bowl.png',src2x:'icons/wl-bowl@2x.png'},
 'wl-book':{fb:'📖',src:'icons/wl-book.png',src2x:'icons/wl-book@2x.png'},
 'wl-clock':{fb:'🕐',src:'icons/wl-clock.png',src2x:'icons/wl-clock@2x.png'},
 'wl-bell':{fb:'🔔',src:'icons/wl-bell.png',src2x:'icons/wl-bell@2x.png'},
 'wl-shield':{fb:'🛡️',src:'icons/wl-shield.png',src2x:'icons/wl-shield@2x.png'},
 'wl-lock':{fb:'🔒',src:'icons/wl-lock.png',src2x:'icons/wl-lock@2x.png'},
 'wl-note':{fb:'📝',src:'icons/wl-note.png',src2x:'icons/wl-note@2x.png'},
 'wl-sparkle':{fb:'✨',src:'icons/wl-sparkle.png',src2x:'icons/wl-sparkle@2x.png'},
 'scan-doc':{fb:'📄',src:'icons/scan-doc.png',src2x:'icons/scan-doc@2x.png'},
 'wl-mood-great':{fb:'😊',src:'icons/wl-mood-great.png',src2x:'icons/wl-mood-great@2x.png'},
 'wl-mood-good':{fb:'🙂',src:'icons/wl-mood-good.png',src2x:'icons/wl-mood-good@2x.png'},
 'wl-mood-okay':{fb:'😐',src:'icons/wl-mood-okay.png',src2x:'icons/wl-mood-okay@2x.png'},
 'wl-mood-low':{fb:'😔',src:'icons/wl-mood-low.png',src2x:'icons/wl-mood-low@2x.png'},
 'wl-mood-hard':{fb:'😣',src:'icons/wl-mood-hard.png',src2x:'icons/wl-mood-hard@2x.png'},
 /* Style Closet clay icons (2026-10-01): st-* set — 14 category icons +
    styleme/calendar/laundry/packing/closet feature icons. */
 'st-tops':{fb:'👕',src:'icons/st-tops.png',src2x:'icons/st-tops@2x.png'},
 'st-bottoms':{fb:'👖',src:'icons/st-bottoms.png',src2x:'icons/st-bottoms@2x.png'},
 'st-dresses':{fb:'👗',src:'icons/st-dresses.png',src2x:'icons/st-dresses@2x.png'},
 'st-jackets':{fb:'🧥',src:'icons/st-jackets.png',src2x:'icons/st-jackets@2x.png'},
 'st-sweaters':{fb:'🧶',src:'icons/st-sweaters.png',src2x:'icons/st-sweaters@2x.png'},
 'st-shoes':{fb:'👟',src:'icons/st-shoes.png',src2x:'icons/st-shoes@2x.png'},
 'st-bags':{fb:'👜',src:'icons/st-bags.png',src2x:'icons/st-bags@2x.png'},
 'st-jewelry':{fb:'💍',src:'icons/st-jewelry.png',src2x:'icons/st-jewelry@2x.png'},
 'st-accessories':{fb:'⌚',src:'icons/st-accessories.png',src2x:'icons/st-accessories@2x.png'},
 'st-swimwear':{fb:'🩱',src:'icons/st-swimwear.png',src2x:'icons/st-swimwear@2x.png'},
 'st-basics':{fb:'🧦',src:'icons/st-basics.png',src2x:'icons/st-basics@2x.png'},
 'st-activewear':{fb:'👚',src:'icons/st-activewear.png',src2x:'icons/st-activewear@2x.png'},
 'st-sleepwear':{fb:'💤',src:'icons/st-sleepwear.png',src2x:'icons/st-sleepwear@2x.png'},
 'st-seasonal':{fb:'🧣',src:'icons/st-seasonal.png',src2x:'icons/st-seasonal@2x.png'},
 'st-styleme':{fb:'✨',src:'icons/st-styleme.png',src2x:'icons/st-styleme@2x.png'},
 'st-calendar':{fb:'📅',src:'icons/st-calendar.png',src2x:'icons/st-calendar@2x.png'},
 'st-laundry':{fb:'🧺',src:'icons/st-laundry.png',src2x:'icons/st-laundry@2x.png'},
 'st-packing':{fb:'🧳',src:'icons/st-packing.png',src2x:'icons/st-packing@2x.png'},
 'st-closet':{fb:'👗',src:'icons/st-closet.png',src2x:'icons/st-closet@2x.png'},
 'st-insights':{fb:'📊',src:'icons/st-insights.png',src2x:'icons/st-insights@2x.png'},
 'st-builder':{fb:'🧩',src:'icons/st-builder.png',src2x:'icons/st-builder@2x.png'},
 /* Style Closet utility clay icons (2026-10-01): statuses, settings, photo, price. */
 'st-hanger':{fb:'🧷',src:'icons/st-hanger.png',src2x:'icons/st-hanger@2x.png'},
 'st-camera':{fb:'📷',src:'icons/st-camera.png',src2x:'icons/st-camera@2x.png'},
 'st-pricetag':{fb:'🏷️',src:'icons/st-pricetag.png',src2x:'icons/st-pricetag@2x.png'},
 'st-check':{fb:'✅',src:'icons/st-check.png',src2x:'icons/st-check@2x.png'},
 'st-gear':{fb:'⚙️',src:'icons/st-gear.png',src2x:'icons/st-gear@2x.png'},
 'st-lock':{fb:'🔒',src:'icons/st-lock.png',src2x:'icons/st-lock@2x.png'},
 'st-borrowed':{fb:'🤝',src:'icons/st-borrowed.png',src2x:'icons/st-borrowed@2x.png'},
 /* Style Closet occasion clay icons (2026-10-01). */
 'st-occ-class':{fb:'🎓',src:'icons/st-occ-class.png',src2x:'icons/st-occ-class@2x.png'},
 'st-occ-coffee':{fb:'☕',src:'icons/st-occ-coffee.png',src2x:'icons/st-occ-coffee@2x.png'},
 'st-occ-interview':{fb:'💼',src:'icons/st-occ-interview.png',src2x:'icons/st-occ-interview@2x.png'},
 'st-occ-dinner':{fb:'🍽️',src:'icons/st-occ-dinner.png',src2x:'icons/st-occ-dinner@2x.png'},
 'st-occ-party':{fb:'🪩',src:'icons/st-occ-party.png',src2x:'icons/st-occ-party@2x.png'},
 'st-occ-gym':{fb:'🏋️',src:'icons/st-occ-gym.png',src2x:'icons/st-occ-gym@2x.png'},
 'st-occ-airport':{fb:'✈️',src:'icons/st-occ-airport.png',src2x:'icons/st-occ-airport@2x.png'},
 'st-occ-vacation':{fb:'🏖️',src:'icons/st-occ-vacation.png',src2x:'icons/st-occ-vacation@2x.png'},
 'st-occ-wedding':{fb:'💍',src:'icons/st-occ-wedding.png',src2x:'icons/st-occ-wedding@2x.png'},
 'st-occ-birthday':{fb:'🎂',src:'icons/st-occ-birthday.png',src2x:'icons/st-occ-birthday@2x.png'},
 'st-occ-casual':{fb:'🏠',src:'icons/st-occ-casual.png',src2x:'icons/st-occ-casual@2x.png'},
 'st-occ-work':{fb:'💻',src:'icons/st-occ-work.png',src2x:'icons/st-occ-work@2x.png'},
 /* Style Closet weather clay icons (2026-10-01). */
 'st-wx-hot':{fb:'☀️',src:'icons/st-wx-hot.png',src2x:'icons/st-wx-hot@2x.png'},
 'st-wx-warm':{fb:'🌤️',src:'icons/st-wx-warm.png',src2x:'icons/st-wx-warm@2x.png'},
 'st-wx-cool':{fb:'🍂',src:'icons/st-wx-cool.png',src2x:'icons/st-wx-cool@2x.png'},
 'st-wx-cold':{fb:'❄️',src:'icons/st-wx-cold.png',src2x:'icons/st-wx-cold@2x.png'},
 'st-wx-rainy':{fb:'🌧️',src:'icons/st-wx-rainy.png',src2x:'icons/st-wx-rainy@2x.png'},
 'st-wx-auto':{fb:'🪄',src:'icons/st-wx-auto.png',src2x:'icons/st-wx-auto@2x.png'},
 /* Style Closet vibe clay icons (2026-10-01). */
 'st-vibe-minimal':{fb:'⚪',src:'icons/st-vibe-minimal.png',src2x:'icons/st-vibe-minimal@2x.png'},
 'st-vibe-feminine':{fb:'🎀',src:'icons/st-vibe-feminine.png',src2x:'icons/st-vibe-feminine@2x.png'},
 'st-vibe-edgy':{fb:'⚡',src:'icons/st-vibe-edgy.png',src2x:'icons/st-vibe-edgy@2x.png'},
 'st-vibe-clean':{fb:'💧',src:'icons/st-vibe-clean.png',src2x:'icons/st-vibe-clean@2x.png'},
 'st-vibe-soft':{fb:'🌸',src:'icons/st-vibe-soft.png',src2x:'icons/st-vibe-soft@2x.png'},
 'st-vibe-bold':{fb:'🔥',src:'icons/st-vibe-bold.png',src2x:'icons/st-vibe-bold@2x.png'},
 'st-vibe-casual':{fb:'👟',src:'icons/st-vibe-casual.png',src2x:'icons/st-vibe-casual@2x.png'},
 'st-vibe-professional':{fb:'👔',src:'icons/st-vibe-professional.png',src2x:'icons/st-vibe-professional@2x.png'},
 'st-vibe-streetwear':{fb:'🧢',src:'icons/st-vibe-streetwear.png',src2x:'icons/st-vibe-streetwear@2x.png'},
 'st-vibe-comfortable':{fb:'🌿',src:'icons/st-vibe-comfortable.png',src2x:'icons/st-vibe-comfortable@2x.png'},
 /* Style Closet feel clay icons (2026-10-01). */
 'st-feel-confident':{fb:'🏅',src:'icons/st-feel-confident.png',src2x:'icons/st-feel-confident@2x.png'},
 'st-feel-cute':{fb:'💛',src:'icons/st-feel-cute.png',src2x:'icons/st-feel-cute@2x.png'},
 'st-feel-elegant':{fb:'🦪',src:'icons/st-feel-elegant.png',src2x:'icons/st-feel-elegant@2x.png'},
 'st-feel-relaxed':{fb:'🌙',src:'icons/st-feel-relaxed.png',src2x:'icons/st-feel-relaxed@2x.png'},
 /* Style Closet trip + action clay icons (2026-10-01). */
 'st-trip-city':{fb:'🏙️',src:'icons/st-trip-city.png',src2x:'icons/st-trip-city@2x.png'},
 'st-trip-mountain':{fb:'⛰️',src:'icons/st-trip-mountain.png',src2x:'icons/st-trip-mountain@2x.png'},
 'st-shuffle':{fb:'🔀',src:'icons/st-shuffle.png',src2x:'icons/st-shuffle@2x.png'},
 'st-photo':{fb:'🖼️',src:'icons/st-photo.png',src2x:'icons/st-photo@2x.png'},
 /* Home-screen redesign artwork (2026-10-05): hm-* hero/banners + module
    icons, qa-* quick-access icons. Glossy 3D, all original, no purple. */
 'hm-hero-astro':{fb:'🚀',src:'icons/hm-hero-astro.png',src2x:'icons/hm-hero-astro@2x.png'},
 'zodiac-capricorn':{fb:'♑',src:'icons/zodiac-capricorn.png'},
 'zodiac-aquarius':{fb:'♒',src:'icons/zodiac-aquarius.png'},
 'zodiac-pisces':{fb:'♓',src:'icons/zodiac-pisces.png'},
 'zodiac-aries':{fb:'♈',src:'icons/zodiac-aries.png'},
 'zodiac-taurus':{fb:'♉',src:'icons/zodiac-taurus.png'},
 'zodiac-gemini':{fb:'♊',src:'icons/zodiac-gemini.png'},
 'zodiac-cancer':{fb:'♋',src:'icons/zodiac-cancer.png'},
 'zodiac-leo':{fb:'♌',src:'icons/zodiac-leo.png'},
 'zodiac-virgo':{fb:'♍',src:'icons/zodiac-virgo.png'},
 'zodiac-libra':{fb:'♎',src:'icons/zodiac-libra.png'},
 'zodiac-scorpio':{fb:'♏',src:'icons/zodiac-scorpio.png'},
 'zodiac-sagittarius':{fb:'♐',src:'icons/zodiac-sagittarius.png'},
 'hm-ask-robot':{fb:'🤖',src:'icons/hm-ask-robot.png',src2x:'icons/hm-ask-robot@2x.png'},
 'hm-mod-daily':{fb:'📓',src:'icons/hm-mod-daily.png',src2x:'icons/hm-mod-daily@2x.png'},
 'hm-mod-memory':{fb:'🗂️',src:'icons/hm-mod-memory.png',src2x:'icons/hm-mod-memory@2x.png'},
 'hm-mod-market':{fb:'🛍️',src:'icons/hm-mod-market.png',src2x:'icons/hm-mod-market@2x.png'},
 'hm-mod-work':{fb:'💼',src:'icons/hm-mod-work.png',src2x:'icons/hm-mod-work@2x.png'},
 'qa-closet':{fb:'👗',src:'icons/qa-closet.png',src2x:'icons/qa-closet@2x.png'},
 'qa-beauty':{fb:'💄',src:'icons/qa-beauty.png',src2x:'icons/qa-beauty@2x.png'},
 'qa-groups':{fb:'👥',src:'icons/qa-groups.png',src2x:'icons/qa-groups@2x.png'},
 'qa-decor':{fb:'🏠',src:'icons/qa-decor.png',src2x:'icons/qa-decor@2x.png'},
 'qa-travel':{fb:'✈️',src:'icons/qa-travel.png',src2x:'icons/qa-travel@2x.png'},
 'qa-safety':{fb:'🛡️',src:'icons/qa-safety.png',src2x:'icons/qa-safety@2x.png'},

});
var EVTMAP={'🍕':'ev-food','💼':'ev-career','🏀':'ev-sports','📚':'ev-study','🎨':'ev-art','🎉':'ev-party'};

/* Keyword matcher for contextual icons (subjects + appointments).
   hasWord() matches whole words (unicode-aware) with an optional english
   plural suffix, so 'art' won't fire inside 'earth', but 'maths' matches. */
function escRe(s){return String(s).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}
function hasWord(s, kw){
  try{
    return new RegExp('(^|[^\\p{L}])'+escRe(kw)+'(s|es)?([^\\p{L}]|$)','iu').test(s);
  }catch(e){ return String(s).toLowerCase().indexOf(String(kw).toLowerCase())>=0; }
}
function matchKeys(s, groups){
  for(var i=0;i<groups.length;i++){
    var g=groups[i];
    for(var j=0;j<g.kws.length;j++) if(hasWord(s,g.kws[j])) return g.icon;
  }
  return '';
}
/* Order matters: specific sciences (bio/chem/physics) come before general science. */
var SUBJGROUPS=[
 {icon:'subj-math',kws:['mathematics','math','maths','algebra','calculus','geometry','trigonometry','statistics','गणित','matemáticas','mathématiques']},
 {icon:'subj-bio',kws:['biology','bio','botany','zoology','anatomy','जीवविज्ञान','biología','biologie']},
 {icon:'subj-chem',kws:['chemistry','chem','organic chem','रसायन','química','chimie']},
 {icon:'subj-physics',kws:['physics','quantum','thermodynamics','भौतिक','física','physique']},
 {icon:'subj-computer',kws:['computer','coding','programming','software','python','javascript','java','कम्प्युटर','informática','informatique']},
 {icon:'subj-english',kws:['english','literature','writing','composition','अंग्रेजी','inglés','anglais']},
 {icon:'subj-history',kws:['history','इतिहास','historia','histoire']},
 {icon:'subj-language',kws:['language','spanish','french','german','nepali','hindi','chinese','japanese','भाषा','idioma','langue']},
 {icon:'subj-music',kws:['music','band','choir','piano','guitar','संगीत','música','musique']},
 {icon:'subj-science',kws:['science','विज्ञान','ciencia']},
 {icon:'ev-art',kws:['art','drawing','painting','design','photography','कला','arte']}
];
var APPTGROUPS=[
 {icon:'appt-medical',kws:['doctor','dr','clinic','hospital','physician','nurse','checkup','check-up','health','pharmacy','therapist','therapy','physio','डाक्टर','चिकित्सक','médico']},
 {icon:'appt-dental',kws:['dentist','dental','tooth','teeth','orthodontist','दाँत']},
 {icon:'appt-car',kws:['car','vehicle','auto','garage','mechanic','oil change','tire','tyre','service center','गाडी']},
 {icon:'ev-party',kws:['birthday','party','celebration','anniversary','जन्मदिन','fiesta']},
 {icon:'ev-food',kws:['lunch','dinner','breakfast','brunch','food','restaurant','coffee','café','cafe','खाना','comida']},
 {icon:'ev-sports',kws:['gym','workout','training','sport','football','soccer','basketball','game','match','swim','tennis','खेल','deporte']},
 {icon:'ev-study',kws:['exam','test','study','class','school','college','tutor','tutoring','परीक्षा','examen']},
 {icon:'ev-career',kws:['interview','meeting','work','job','boss','office','conference','client','काम','trabajo']},
 {icon:'ev-art',kws:['haircut','salon','spa','beauty','nails','barber','कपाल']}
];

var api = {
  map: M,

  icon: function(name, cls){
    var m = M[name];
    if(!m) return '';
    return '<span class="ico'+(cls?' '+esc(cls):'')+'">'
      + '<img data-icon="'+esc(name)+'" src="'+esc(m.src)+'"'
      + ' srcset="'+esc(m.src2x)+' 96w, '+esc(m.src)+' 144w" sizes="48px"'
      + ' alt="" loading="lazy" decoding="async" draggable="false"'
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
  },

  /* eventIcon(emoji) -> clay 3D icon HTML for a known event emoji;
     unknown/custom emoji stay as-is so user content is preserved. */
  eventIcon: function(emoji){
    var n = EVTMAP[emoji||''];
    if(n && M[n]) return api.icon(n, 'ev-ico');
    return '<span class="ev-emoji">'+esc(emoji||'🎉')+'</span>';
  },

  /* subjectIcon(subject, isShift) -> clay 3D icon HTML right beside a
     class/shift subject: math gets a calculator, biology a DNA helix, etc.
     Keyword matching is multilingual (en/es/ne/hi). Unknown subjects fall
     back to the books icon (briefcase in shift/work mode). */
  subjectIcon: function(subject, isShift){
    var n = matchKeys(String(subject||''), SUBJGROUPS);
    if(!n) n = isShift ? 'ev-career' : 'ev-study';
    return api.icon(n, 'subj-ico');
  },

  /* apptIcon(title) -> clay 3D icon HTML right beside an appointment title:
     doctor gets a stethoscope, car gets a car, etc. Unknown titles get a
     plain pin so nothing renders blank. */
  apptIcon: function(title){
    var n = matchKeys(String(title||''), APPTGROUPS);
    if(n && M[n]) return api.icon(n, 'appt-ico');
    return '<span class="appt-fb">📌</span>';
  }
};

window.HUB = Object.assign(window.HUB || {}, {icons: api});

})();

/* 2026 chrome line-icon family — SF/Lucide-style, 24px grid, stroke=currentColor.
   Replaces the clay PNGs for the tab bar + header chrome so the app chrome
   reads premium and mature. Content-area HUB.icons.icon() PNGs are untouched. */
(function(){'use strict';
var SVG={
 'nav-home':'<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
 'nav-discover':'<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
 'nav-market':'<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
 'nav-work':'<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
 'nav-groups':'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
 'nav-me':'<path d="M18 20a6 6 0 0 0-12 0"/><circle cx="12" cy="10" r="4"/><circle cx="12" cy="12" r="10"/>',
 'ic-search':'<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
 'ic-pulse':'<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
 'ic-bell':'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
 'ic-chat':'<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
 'ask-hub':'<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/>'
};
function esc2(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}
HUB.icons.svg=function(name,cls){
  var p=SVG[name]; if(!p) return '';
  return '<svg class="lnico'+(cls?' '+esc2(cls):'')+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+p+'</svg>';
};
HUB.icons.svgNames=function(){ return Object.keys(SVG); };
/* Animated planet wordmark: the planet IS the O in "Onaro". p = id prefix so
   multiple instances (header, welcome, splash) don't collide on ids.
   2026-09-23 3D redesign (PraBin's order: "more 3D, magical, eye-catching"):
   a LUMINOUS golden/amber planet jewel (molten-lit crescent, amber midtones,
   terminator shadow, cloud bands, specular pop, volt rim-light) wrapped by a
   volt ring with TRUE depth — the back arc renders BEHIND the sphere, the
   front arc IN FRONT. Two hot light pulses circulate the ring 180deg apart,
   the white comet + red satellite ride the full orbit (SMIL <set> hands each
   rider from its back copy to its front copy exactly at the limbs, so they
   genuinely pass behind the planet), plus a soft golden aura and twinkling
   star specks. Pure SVG + CSS; SMIL only for the riders. */
HUB.icons.logoMark=function(p){
  p=p||'X';
  var BACK='M87.9 177.9 A112 34 -24 1 1 191.9 131.6';
  var FRONT='M191.9 131.6 A112 34 -24 0 1 87.9 177.9';
  var LOOP='M87.9 177.9 A112 34 -24 1 1 191.9 131.6 A112 34 -24 0 1 87.9 177.9 Z';
  function mark(mode){
    var d=mode==='d';
    var ring=(HUB.theme?HUB.theme.accent():(d?'#D4F53F':'#C6F135')); /* follows gender theme */
    var hot=d?'#F2FF8A':'#E4FF5C';
    var sat=d?'#FF7A5C':'#FF5C38';
    var sfx=p+(d?'D':'L');
    var gid='lg'+sfx, oid='orb'+sfx, au='au'+sfx, bk='bk'+sfx, fr='fr'+sfx;
    var cp='cp'+sfx, tm='tm'+sfx, sc='sc'+sfx;
    /* golden jewel sphere stops: molten highlight -> amber -> deep shadow limb */
    var sp=d?[["0","#FFF9E0"],[".22","#FFE9A3"],[".48","#F7C65C"],[".72","#A8641A"],[".9","#4A2A0C"],["1","#1E1206"]]
            :[["0","#FFF6D2"],[".25","#FFE49A"],[".5","#EFA93A"],[".75","#9A5E15"],["1","#241503"]];
    var sps=''; for(var i=0;i<sp.length;i++){ sps+='<stop offset="'+sp[i][0]+'" stop-color="'+sp[i][1]+'"/>'; }
    /* rider with true occlusion: back copy visible on the far half [0,T/2),
       front copy on the near half [T/2,T), handed off at the limbs */
    function rider(dur,half,back,inner){
      var a=back?'<set attributeName="opacity" to="1" begin="0s" dur="'+half+'" repeatCount="indefinite"/>'
                  +'<set attributeName="opacity" to="0" begin="'+half+'" dur="'+half+'" repeatCount="indefinite"/>'
                :'<set attributeName="opacity" to="0" begin="0s" dur="'+half+'" repeatCount="indefinite"/>'
                  +'<set attributeName="opacity" to="1" begin="'+half+'" dur="'+half+'" repeatCount="indefinite"/>';
      return '<g class="logo-rider" opacity="'+(back?'1':'0')+'">'
        +'<animateMotion dur="'+dur+'" repeatCount="indefinite"><mpath href="#'+oid+'"/></animateMotion>'
        +a+inner+'</g>';
    }
    var comet='<circle r="11" fill="#ffffff" opacity=".22"/><circle r="5" fill="#FFF6D8"/>';
    var satc='<circle r="9" fill="'+sat+'"/>';
    return '<svg class="logo-'+(d?'dark':'light')+' logo-anim" viewBox="0 0 256 256" aria-hidden="true">'
      +'<defs>'
      +'<radialGradient id="'+gid+'" cx="36%" cy="28%" r="82%">'+sps+'</radialGradient>'
      +'<radialGradient id="'+tm+'" cx="72%" cy="78%" r="65%">'
      +'<stop offset="0" stop-color="#140A00" stop-opacity="0"/><stop offset=".6" stop-color="#140A00" stop-opacity=".28"/><stop offset="1" stop-color="#140A00" stop-opacity=".62"/>'
      +'</radialGradient>'
      +'<radialGradient id="'+sc+'" cx="50%" cy="50%" r="50%">'
      +'<stop offset="0" stop-color="#FFFDF4" stop-opacity=".85"/><stop offset="1" stop-color="#FFFDF4" stop-opacity="0"/>'
      +'</radialGradient>'
      +'<radialGradient id="'+au+'" cx="50%" cy="50%" r="50%">'
      +'<stop offset="0" stop-color="#F2B84B" stop-opacity=".20"/><stop offset=".55" stop-color="#F2B84B" stop-opacity=".07"/><stop offset="1" stop-color="#F2B84B" stop-opacity="0"/>'
      +'</radialGradient>'
      +'<linearGradient id="'+bk+'" gradientUnits="userSpaceOnUse" x1="87.9" y1="177.9" x2="191.9" y2="131.6">'
      +'<stop offset="0" stop-color="#A9BC3F"/><stop offset=".4" stop-color="#5E6A1E"/><stop offset=".6" stop-color="#5E6A1E"/><stop offset="1" stop-color="#A9BC3F"/>'
      +'</linearGradient>'
      +'<linearGradient id="'+fr+'" gradientUnits="userSpaceOnUse" x1="191.9" y1="131.6" x2="87.9" y2="177.9">'
      +'<stop offset="0" stop-color="#F2FF8A"/><stop offset=".5" stop-color="'+ring+'"/><stop offset="1" stop-color="#F2FF8A"/>'
      +'</linearGradient>'
      +'<clipPath id="'+cp+'"><circle cx="128" cy="128" r="64"/></clipPath>'
      +'<path id="'+oid+'" d="'+LOOP+'" fill="none"/>'
      +'</defs>'
      /* golden aura + twinkling star specks */
      +'<circle cx="128" cy="128" r="118" fill="url(#'+au+')"/>'
      +'<circle class="logo-twinkle" cx="44" cy="52" r="2.2" fill="#FFF6D8"/>'
      +'<circle class="logo-twinkle" cx="212" cy="64" r="1.8" fill="#FFF6D8" style="animation-delay:-1.1s"/>'
      +'<circle class="logo-twinkle" cx="208" cy="208" r="2.4" fill="#FFF6D8" style="animation-delay:-2.1s"/>'
      /* BACK ring: soft glow + main arc + traveling pulse, all behind the sphere */
      +'<path class="logo-backarc" d="'+BACK+'" fill="none" stroke="url(#'+bk+')" stroke-width="18" opacity=".22"/>'
      +'<path class="logo-backarc" d="'+BACK+'" fill="none" stroke="url(#'+bk+')" stroke-width="7" opacity=".5"/>'
      +'<path class="logo-backarc logo-ringflow" d="'+BACK+'" fill="none" stroke="'+hot+'" stroke-width="7" stroke-linecap="round" pathLength="100" stroke-dasharray="22 78" opacity=".85"/>'
      /* riders, far halves */
      +rider('6s','3s',true,comet)
      +rider('16s','8s',true,satc)
      /* the golden planet jewel */
      +'<circle class="logo-planet" cx="128" cy="128" r="64" fill="url(#'+gid+')"/>'
      +'<g clip-path="url(#'+cp+')">'
      +'<ellipse cx="128" cy="112" rx="66" ry="11" transform="rotate(-8 128 112)" fill="#5E3408" opacity=".10"/>'
      +'<ellipse cx="128" cy="146" rx="66" ry="9" transform="rotate(-8 128 146)" fill="#5E3408" opacity=".08"/>'
      +'<circle cx="128" cy="128" r="64" fill="url(#'+tm+')"/>'
      +'<ellipse cx="104" cy="100" rx="17" ry="12" transform="rotate(-30 104 100)" fill="url(#'+sc+')" opacity=".7"/>'
      +'</g>'
      /* volt rim-light on the lit limb */
      +'<path d="M64 128 A64 64 0 0 1 128 64" fill="none" stroke="#FFE9A3" stroke-width="9" opacity=".15" stroke-linecap="round"/>'
      +'<path d="M64 128 A64 64 0 0 1 128 64" fill="none" stroke="#FFF3C4" stroke-width="3.5" opacity=".85" stroke-linecap="round"/>'
      /* FRONT ring: glow + main arc + traveling pulse, in front of the sphere */
      +'<path class="logo-frontarc" d="'+FRONT+'" fill="none" stroke="'+ring+'" stroke-width="18" opacity=".25"/>'
      +'<path class="logo-frontarc" d="'+FRONT+'" fill="none" stroke="url(#'+fr+')" stroke-width="7.5"/>'
      +'<path class="logo-frontarc logo-ringflow" d="'+FRONT+'" fill="none" stroke="'+hot+'" stroke-width="7.5" stroke-linecap="round" pathLength="100" stroke-dasharray="22 78"/>'
      /* riders, near halves */
      +rider('6s','3s',false,comet)
      +rider('16s','8s',false,satc)
      +'</svg>';
  }
  return mark('l')+mark('d');
};
/* Freeze the logo riders for reduced-motion users (SMIL ignores CSS). */
HUB.icons.freezeLogos=function(){
  try{
    if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches){
      document.querySelectorAll('svg.logo-anim').forEach(function(s){ try{ s.pauseAnimations(); }catch(e){} });
    }
  }catch(e){}
};
})();
