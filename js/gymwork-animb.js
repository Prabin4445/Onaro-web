/* Onaro Gym Fuel — workout motion scripts (batch B: full biomechanical rebuild).
   Registers 19 exercise scripts with the mannequin engine core
   (HUB.gymworkAnim._register). Classic IIFE, no modules.
   Pose contract: every pose is pelvis + wrist (hand) + ankle (foot) TARGETS.
     pelvis:[x,y]  torso:deg (0 upright; + = lean forward, side view facing +x;
                 negative values are mirrored by the engine for head-left poses)
     head:deg (0 neutral; + = chin tucks toward chest)
     hands:{R:[x,y],L:[x,y]}  // wrist targets; side view: R = near arm
     feet:{R:[x,y],L:[x,y]}   // ankle targets; side view: R = near leg
   top = contracted/lockout end of the rep; bottom = stretched/lowered end.
   The engine's IK solver places elbows/knees; equipment follows the wrist
   targets every frame, so bars/ropes cannot detach from the hands.
   All targets validated reachable: wrist <= 65 from its shoulder (>= 10),
   ankle <= 112 from its hip (the rig's own standing reference is 110, so
   109 is unreachable in practice), and every target inside x:[15,185],
   y:[8,246]. See /tmp/validate-anims.js (PASS: 40/40).
   Rule: never name a local variable t (it shadows the i18n helper). */
(function(){
'use strict';

function reg(){
  var anim=(window.HUB&&window.HUB.gymworkAnim)||null;
  if(!anim||typeof anim._register!=='function') return;

  /* ============ PUSH ============ */

  /* 1. Bench press — supine on flat bench, head LEFT. Bar touches mid-chest
     at bottom, pressed to lockout over the shoulders at top. */
  anim._register('bench-press',{
    view:'side', equipment:'bench-flat',
    top:{ pelvis:[120,184], torso:-75, head:0,
      hands:{R:[58,104],L:[58,104]}, feet:{R:[150,234],L:[156,233]} },
    bottom:{ pelvis:[120,184], torso:-75, head:0,
      hands:{R:[58,148],L:[58,148]}, feet:{R:[150,234],L:[156,233]} }
  });

  /* 2. Overhead press — standing, bar from collarbone to full lockout.
     Pelvis lowered a touch so the bar clears the crown at top. */
  anim._register('overhead-press',{
    view:'front', equipment:'bar-full',
    top:{ pelvis:[100,142], torso:0, head:8,
      hands:{R:[80,16],L:[120,16]}, feet:{R:[89,234],L:[111,234]} },
    bottom:{ pelvis:[100,142], torso:0, head:0,
      hands:{R:[70,70],L:[130,70]}, feet:{R:[89,234],L:[111,234]} }
  });

  /* 3. Incline dumbbell press — torso on a 30-degree incline, head LEFT.
     Dumbbells arc slightly inward on the way up. */
  anim._register('incline-db-press',{
    view:'side', equipment:'bench-incline',
    top:{ pelvis:[108,196], torso:-60, head:0,
      hands:{R:[70,104],L:[64,106]}, feet:{R:[148,234],L:[154,233]} },
    bottom:{ pelvis:[108,196], torso:-60, head:0,
      hands:{R:[66,150],L:[60,152]}, feet:{R:[148,234],L:[154,233]} }
  });

  /* 4. Lateral raise — standing tall, torso locked at 0 (no swing).
     Dumbbells rise to just below shoulder height, wide of the shoulders. */
  anim._register('lateral-raise',{
    view:'front', equipment:'dumbbell',
    top:{ pelvis:[100,124], torso:0, head:0,
      hands:{R:[44,72],L:[156,72]}, feet:{R:[89,234],L:[111,234]} },
    bottom:{ pelvis:[100,124], torso:0, head:0,
      hands:{R:[70,124],L:[130,124]}, feet:{R:[89,234],L:[111,234]} }
  });

  /* 5. Triceps pushdown — elbows pinned at the sides. Wrists travel straight
     down under the shoulders, so only the forearms appear to move. */
  anim._register('tricep-pushdown',{
    view:'side', equipment:'cable-pushdown',
    top:{ pelvis:[100,124], torso:5, head:0,
      hands:{R:[124,92],L:[118,92]}, feet:{R:[111,234],L:[89,234]} },
    bottom:{ pelvis:[100,124], torso:5, head:0,
      hands:{R:[122,124],L:[116,124]}, feet:{R:[111,234],L:[89,234]} }
  });

  /* 6. Dips — wrists pinned on the fixed rails. Pelvis drops until the
     shoulders sink below elbow level, with a slight forward lean. */
  anim._register('dips',{
    view:'side', equipment:'dip-bars',
    top:{ pelvis:[100,148], torso:0, head:0,
      hands:{R:[100,150],L:[96,150]}, feet:{R:[96,214],L:[90,216]} },
    bottom:{ pelvis:[100,178], torso:12, head:0,
      hands:{R:[100,150],L:[96,150]}, feet:{R:[92,228],L:[86,230]} }
  });

  /* ============ PULL ============ */

  /* 7. Deadlift — facing right. Bottom: hips back, flat back, bar at shin
     height touching the shins. Top: hips driven through, bar against the
     thighs. The bar drifts straight back 24px along the legs — no S-curve,
     no floating away from the body. */
  anim._register('deadlift',{
    view:'side', equipment:'bar-endon',
    top:{ pelvis:[100,124], torso:4, head:0,
      hands:{R:[105,124],L:[99,124]}, feet:{R:[133,234],L:[101,234]} },
    bottom:{ pelvis:[84,160], torso:50, head:0,
      hands:{R:[129,184],L:[123,184]}, feet:{R:[133,234],L:[101,234]} }
  });

  /* 8. Pull-up — front view, wrists snapped to the fixed bar. Dead hang at
     bottom, chin clearing the bar at top. Feet dangle off the floor. */
  anim._register('pull-up',{
    view:'front', equipment:'pullup-bar',
    top:{ pelvis:[100,108], torso:0, head:0,
      hands:{R:[72,42],L:[128,42]}, feet:{R:[94,196],L:[106,196]} },
    bottom:{ pelvis:[100,168], torso:0, head:0,
      hands:{R:[72,42],L:[128,42]}, feet:{R:[92,246],L:[108,246]} }
  });

  /* 9. Barbell row — torso hinged near-parallel and FROZEN there: pelvis and
     torso are identical in both poses, so only the arms move. Bar rows from
     below the knees to the lower ribs. */
  anim._register('barbell-row',{
    view:'side', equipment:'bar-endon',
    top:{ pelvis:[96,150], torso:72, head:0,
      hands:{R:[128,150],L:[122,150]}, feet:{R:[90,234],L:[112,234]} },
    bottom:{ pelvis:[96,150], torso:72, head:0,
      hands:{R:[152,194],L:[146,194]}, feet:{R:[90,234],L:[112,234]} }
  });

  /* 10. Lat pulldown — seated, facing right. Arms extend overhead at bottom,
      bar pulls to the upper chest at top with a slight lean-back. */
  anim._register('lat-pulldown',{
    view:'side', equipment:'lat-machine',
    top:{ pelvis:[104,196], torso:-6, head:0,
      hands:{R:[108,142],L:[96,148]}, feet:{R:[120,234],L:[126,234]} },
    bottom:{ pelvis:[104,196], torso:6, head:0,
      hands:{R:[106,72],L:[100,72]}, feet:{R:[120,234],L:[126,234]} }
  });

  /* 11. Face pull — front view, tower on the left. Rope V runs from the
      pulley into both hands at all times; at top the rope reaches the face
      with elbows high and wide. */
  anim._register('face-pull',{
    view:'front', equipment:'facepull-tower',
    top:{ pelvis:[100,128], torso:-4, head:0,
      hands:{R:[74,52],L:[120,48]}, feet:{R:[89,234],L:[111,234]} },
    bottom:{ pelvis:[100,128], torso:0, head:0,
      hands:{R:[60,80],L:[88,76]}, feet:{R:[89,234],L:[111,234]} }
  });

  /* 12. Barbell curl — elbows pinned at the sides (wrists stay on the same
      vertical line), torso locked at 0, no swing. */
  anim._register('barbell-curl',{
    view:'front', equipment:'bar-full',
    top:{ pelvis:[100,124], torso:0, head:0,
      hands:{R:[72,78],L:[128,78]}, feet:{R:[89,234],L:[111,234]} },
    bottom:{ pelvis:[100,124], torso:0, head:0,
      hands:{R:[76,126],L:[124,126]}, feet:{R:[89,234],L:[111,234]} }
  });

  /* 13. Hammer curl — same strict form as the barbell curl, neutral grip,
      dumbbells riding slightly wider at the top. */
  anim._register('hammer-curl',{
    view:'front', equipment:'dumbbell',
    top:{ pelvis:[100,124], torso:0, head:0,
      hands:{R:[70,80],L:[130,80]}, feet:{R:[89,234],L:[111,234]} },
    bottom:{ pelvis:[100,124], torso:0, head:0,
      hands:{R:[76,126],L:[124,126]}, feet:{R:[89,234],L:[111,234]} }
  });

  /* ============ LEGS ============ */

  /* 14. Back squat — facing right, bar across the upper back (hands grip it
      there). Hips travel back and down; knees track over the toes. */
  anim._register('back-squat',{
    view:'side', equipment:'squat-bar',
    top:{ pelvis:[100,124], torso:8, head:0,
      hands:{R:[100,64],L:[98,66]}, feet:{R:[111,234],L:[89,234]} },
    bottom:{ pelvis:[86,170], torso:30, head:0,
      hands:{R:[108,114],L:[106,116]}, feet:{R:[111,234],L:[89,234]} }
  });

  /* 15. Romanian deadlift — a pure hip hinge: pelvis pushes straight BACK,
      torso folds forward, knees stay soft, back flat. Bar slides down the
      thighs to just below the knees. */
  anim._register('romanian-deadlift',{
    view:'side', equipment:'bar-endon',
    top:{ pelvis:[100,124], torso:4, head:0,
      hands:{R:[104,124],L:[98,124]}, feet:{R:[111,234],L:[89,234]} },
    bottom:{ pelvis:[76,148], torso:62, head:0,
      hands:{R:[126,182],L:[120,182]}, feet:{R:[111,234],L:[89,234]} }
  });

  /* 16. Leg press — reclined, torso glued to the pad at the same angle in
      both poses. Feet push the platform from deep knee bend to soft knees;
      the platform face follows the ankles exactly. */
  anim._register('leg-press',{
    view:'side', equipment:'legpress',
    top:{ pelvis:[66,202], torso:-42, head:0,
      hands:{R:[80,150],L:[74,152]}, feet:{R:[150,140],L:[144,142]} },
    bottom:{ pelvis:[66,202], torso:-42, head:0,
      hands:{R:[80,150],L:[74,152]}, feet:{R:[128,168],L:[122,170]} }
  });

  /* 17. Lying leg curl — prone, head LEFT, hips pinned to the pad (pelvis
      identical in both poses). Heels curl from straight legs to the glutes;
      the ankle roller follows the ankles. */
  anim._register('lying-leg-curl',{
    view:'side', equipment:'legcurl',
    top:{ pelvis:[104,196], torso:-84, head:0,
      hands:{R:[40,200],L:[46,202]}, feet:{R:[116,150],L:[110,152]} },
    bottom:{ pelvis:[104,196], torso:-84, head:0,
      hands:{R:[40,200],L:[46,202]}, feet:{R:[170,206],L:[164,208]} }
  });

  /* 18. Calf raise — forefoot on the step edge, straight knees. Ankles rise
      from heels-dropped to full tiptoe; hands hold a rail lightly. */
  anim._register('calf-raise',{
    view:'side', equipment:'step',
    top:{ pelvis:[100,124], torso:2, head:0,
      hands:{R:[128,96],L:[122,96]}, feet:{R:[112,218],L:[106,218]} },
    bottom:{ pelvis:[100,124], torso:2, head:0,
      hands:{R:[128,96],L:[122,96]}, feet:{R:[112,232],L:[106,232]} }
  });

  /* 19. Walking lunge — long step, torso STAYS upright (no forward
      collapse), back knee hovers off the floor. alt mirrors the lead leg so
      the loop alternates sides. */
  anim._register('walking-lunge',{
    view:'side', equipment:'none',
    top:{ pelvis:[100,124], torso:0, head:0,
      hands:{R:[124,120],L:[118,120]}, feet:{R:[111,234],L:[89,234]} },
    bottom:{ pelvis:[102,168], torso:3, head:0,
      hands:{R:[124,140],L:[118,140]}, feet:{R:[150,234],L:[52,228]} },
    alt:{
      top:{ pelvis:[100,124], torso:0, head:0,
        hands:{R:[118,120],L:[124,120]}, feet:{R:[111,234],L:[89,234]} },
      bottom:{ pelvis:[102,168], torso:3, head:0,
        hands:{R:[118,140],L:[124,140]}, feet:{R:[52,228],L:[150,234]} }
    }
  });
}

reg();
})();
