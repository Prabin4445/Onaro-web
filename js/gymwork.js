/* Onaro Gym Fuel — Workout Plans UI.
   Push/Pull/Legs plan engine: setup wizard, plan home, day view, exercise
   player with timestamp-derived rest timer, BEAST MODE badge, gym buddies.
   Integrates by WRAPPING (never editing): HUB.gym.cardHTML,
   HUB.badges.headerHTML, HUB.badges.forPerson. Reuses HUB.chat.openWith for
   buddy chat. All state on-device in HUB.store.state.gym.workout.
   i18n: user strings via t('gymwork.…'); EN fallback lives in this file so
   DICT.en (and the lazy-locale key hash) stays untouched until the
   translation worker ships real locales.
   Classic IIFE, no modules. */
(function(){
'use strict';

/* ---------- i18n (local EN fallback) ---------- */
var EN={
'gymwork.cardTitle':'Workout Plans',
'gymwork.cardSub':'Push–Pull–Legs routines with animated demos, set tracking, and rest timers.',
'gymwork.open':'Open workout plans',
'gymwork.wiz.levelT':'Choose your level',
'gymwork.wiz.levelS':'Sets, reps, and rest adapt to you.',
'gymwork.level.beginner':'Beginner',
'gymwork.level.beginnerD':'New to lifting — lighter volume, longer rests.',
'gymwork.level.intermediate':'Intermediate',
'gymwork.level.intermediateD':'Training a while — solid volume, steady progress.',
'gymwork.level.advanced':'Advanced',
'gymwork.level.advancedD':'Experienced — high volume, short rests, heavy work.',
'gymwork.wiz.splitT':'Pick your split order',
'gymwork.wiz.splitS':'The order you rotate Push, Pull, and Legs days.',
'gymwork.split.ppl':'Push – Pull – Legs',
'gymwork.split.pplD':'Classic rotation: chest/shoulders/triceps, then back/biceps, then legs.',
'gymwork.split.ppl2':'Pull – Push – Legs',
'gymwork.split.ppl2D':'Back and biceps first — great if pulling is your priority.',
'gymwork.split.lpp':'Legs – Push – Pull',
'gymwork.split.lppD':'Legs lead the week — never skip leg day again.',
'gymwork.wiz.daysT':'Assign your training days',
'gymwork.wiz.daysS':'Tap a day to cycle it through your split. Sunday is always rest.',
'gymwork.rest':'Rest',
'gymwork.day.mon':'Monday','gymwork.day.tue':'Tuesday','gymwork.day.wed':'Wednesday',
'gymwork.day.thu':'Thursday','gymwork.day.fri':'Friday','gymwork.day.sat':'Saturday',
'gymwork.day.sun':'Sunday',
'gymwork.group.push':'Push','gymwork.group.pull':'Pull','gymwork.group.legs':'Legs',
'gymwork.back':'Back','gymwork.next':'Next','gymwork.done':'Done',
'gymwork.start':'Start workout','gymwork.today':'Today',
'gymwork.plan.thisWeek':'This week',
'gymwork.plan.change':'Change plan',
'gymwork.plan.confirmChange':'Start over with a new plan? Your workout log is kept.',
'gymwork.plan.keep':'Keep my plan',
'gymwork.plan.discard':'Start over',
'gymwork.sets':'sets','gymwork.reps':'reps','gymwork.restT':'Rest','gymwork.sec':'sec',
'gymwork.player.setOf':'Set {a} of {b}',
'gymwork.player.startSet':'Start set',
'gymwork.player.setDone':'Set done',
'gymwork.player.resting':'Resting…',
'gymwork.player.skipRest':'Skip rest',
'gymwork.player.completeEx':'Complete exercise',
'gymwork.player.nextUp':'Next up',
'gymwork.player.technique':'Technique',
'gymwork.player.targets':'Target muscles',
'gymwork.player.dayDoneT':'Day crushed! 🔥',
'gymwork.player.dayDoneS':'Every exercise complete. BEAST MODE energy.',
'gymwork.player.finish':'Finish',
'gymwork.badge.name':'BEAST MODE',
'gymwork.badge.gymmode':'Gym Mode',
'gymwork.badge.earnedT':'Badge earned!',
'gymwork.badge.earnedS':'You started your first workout.',
'gymwork.badge.desc':'Beast mode: on. Stay consistent, train hard.',
'gymwork.badge.info':'Badge info',
'gymwork.buddies.title':'Gym buddies',
'gymwork.buddies.sub':'Beast Mode lifters near you.',
'gymwork.buddies.chat':'Chat',
'gymwork.buddies.none':'No gym buddies yet.',
'gymwork.m.chest':'Chest','gymwork.m.shoulders':'Shoulders','gymwork.m.triceps':'Triceps',
'gymwork.m.lats':'Lats','gymwork.m.upperback':'Upper back','gymwork.m.biceps':'Biceps',
'gymwork.m.quads':'Quads','gymwork.m.hamstrings':'Hamstrings','gymwork.m.glutes':'Glutes',
'gymwork.m.calves':'Calves','gymwork.m.abs':'Abs','gymwork.m.forearms':'Forearms',
/* exercise names */
'gymwork.ex.benchpress':'Barbell Bench Press','gymwork.ex.overheadpress':'Overhead Press',
'gymwork.ex.pushup':'Push-Up','gymwork.ex.dips':'Dips','gymwork.ex.chestfly':'Dumbbell Chest Fly',
'gymwork.ex.tricepspushdown':'Triceps Pushdown','gymwork.ex.lateralraise':'Lateral Raise',
'gymwork.ex.pullup':'Pull-Up','gymwork.ex.bentrow':'Bent-Over Row','gymwork.ex.latpulldown':'Lat Pulldown',
'gymwork.ex.bicepscurl':'Dumbbell Curl','gymwork.ex.facepull':'Face Pull','gymwork.ex.deadlift':'Deadlift',
'gymwork.ex.squat':'Barbell Squat','gymwork.ex.lunges':'Walking Lunge','gymwork.ex.legpress':'Leg Press',
'gymwork.ex.legcurl':'Lying Leg Curl','gymwork.ex.calfraise':'Standing Calf Raise',
'gymwork.ex.rddeadlift':'Romanian Deadlift',
/* technique cues */
'gymwork.cue.benchpress1':'Grip just outside shoulder width, wrists straight.',
'gymwork.cue.benchpress2':'Lower the bar to mid-chest with control — no bouncing.',
'gymwork.cue.benchpress3':'Press up in a slight arc, squeeze the chest at the top.',
'gymwork.cue.overheadpress1':'Brace your core, squeeze your glutes.',
'gymwork.cue.overheadpress2':'Press the bar straight up, head moves slightly back then through.',
'gymwork.cue.overheadpress3':'Lock out fully without leaning back.',
'gymwork.cue.pushup1':'Body in one straight line from head to heels.',
'gymwork.cue.pushup2':'Chest to the floor, elbows about 45° from your body.',
'gymwork.cue.pushup3':'Push the floor away; don’t let hips sag.',
'gymwork.cue.dips1':'Lean slightly forward, chest proud.',
'gymwork.cue.dips2':'Lower until shoulders are below elbows.',
'gymwork.cue.dips3':'Press to full lockout without shrugging.',
'gymwork.cue.chestfly1':'Slight bend in the elbows — keep it fixed.',
'gymwork.cue.chestfly2':'Open wide until you feel a deep chest stretch.',
'gymwork.cue.chestfly3':'Hug an imaginary barrel on the way up.',
'gymwork.cue.tricepspushdown1':'Pin elbows at your sides — only forearms move.',
'gymwork.cue.tricepspushdown2':'Push down to full lockout, squeeze the triceps.',
'gymwork.cue.tricepspushdown3':'Control the return; don’t let the stack slam.',
'gymwork.cue.lateralraise1':'Lead with the elbows, slight bend, like pouring pitchers.',
'gymwork.cue.lateralraise2':'Raise to shoulder height — no higher.',
'gymwork.cue.lateralraise3':'No swinging; if you swing, the weight is too heavy.',
'gymwork.cue.pullup1':'Start from a dead hang, shoulders engaged.',
'gymwork.cue.pullup2':'Pull your chest to the bar, drive elbows down.',
'gymwork.cue.pullup3':'Lower all the way — full range every rep.',
'gymwork.cue.bentrow1':'Hinge at the hips, back flat like a tabletop.',
'gymwork.cue.bentrow2':'Pull the bar to your lower ribs.',
'gymwork.cue.bentrow3':'Squeeze shoulder blades together at the top.',
'gymwork.cue.latpulldown1':'Lean back just slightly, chest up.',
'gymwork.cue.latpulldown2':'Pull the bar to your upper chest.',
'gymwork.cue.latpulldown3':'No jerking — control the negative.',
'gymwork.cue.bicepscurl1':'Elbows pinned at your sides.',
'gymwork.cue.bicepscurl2':'Curl up with a full squeeze at the top.',
'gymwork.cue.bicepscurl3':'Lower slowly; the way down builds the muscle too.',
'gymwork.cue.facepull1':'Pull the rope to your forehead, thumbs toward you.',
'gymwork.cue.facepull2':'Rotate knuckles back — external rotation at the end.',
'gymwork.cue.facepull3':'Keep elbows high, level with shoulders.',
'gymwork.cue.deadlift1':'Bar over mid-foot, back flat, chest up before you pull.',
'gymwork.cue.deadlift2':'Push the floor away; hips and shoulders rise together.',
'gymwork.cue.deadlift3':'Stand tall, then hinge back down with control.',
'gymwork.cue.squat1':'Big breath, brace like someone will punch your stomach.',
'gymwork.cue.squat2':'Knees track over toes, chest stays proud.',
'gymwork.cue.squat3':'Drive through the whole foot to stand.',
'gymwork.cue.lunges1':'Long step, torso tall.',
'gymwork.cue.lunges2':'Front knee over ankle; back knee kisses the floor.',
'gymwork.cue.lunges3':'Push through the front heel to step forward.',
'gymwork.cue.legpress1':'Feet shoulder width, mid-platform.',
'gymwork.cue.legpress2':'Lower until knees hit 90° — no deeper if hips lift.',
'gymwork.cue.legpress3':'Never lock knees hard at the top.',
'gymwork.cue.legcurl1':'Hips stay glued to the pad.',
'gymwork.cue.legcurl2':'Curl heels to glutes, squeeze hard.',
'gymwork.cue.legcurl3':'Lower slowly — three seconds down.',
'gymwork.cue.calfraise1':'Full stretch at the bottom, pause one second.',
'gymwork.cue.calfraise2':'Rise as high as possible onto your toes.',
'gymwork.cue.calfraise3':'No bouncing — calves respond to control.',
'gymwork.cue.rddeadlift1':'Soft knees, push hips straight back.',
'gymwork.cue.rddeadlift2':'Feel the hamstrings load like a bowstring.',
'gymwork.cue.rddeadlift3':'Back flat; stop the descent when hips can’t go further.',
/* training sections */
'gymwork.plan.sectionsT':'Choose your training',
'gymwork.sec.plan':'Workout Plan','gymwork.sec.warmup':'Warm-Up','gymwork.sec.abs':'Abs',
'gymwork.sec.pilates':'Pilates','gymwork.sec.zumba':'Zumba',
'gymwork.sec.cooldown':'Cooldown',
'gymwork.secD.warmup':'Wake up your muscles before you train.',
'gymwork.secD.abs':'Build a strong, defined core.',
'gymwork.secD.pilates':'Controlled core strength and flexibility.',
'gymwork.secD.zumba':'Dance cardio that feels like a party.',
'gymwork.secD.cooldown':'Gentle stretches to bring your heart rate down.',
/* level switcher */
'gymwork.level.switchT':'Training level',
'gymwork.level.beginnerR':'Machines, dumbbells and bodyweight — no barbell yet.',
'gymwork.level.intermediateR':'Adds the barbell: squat, bench, deadlift and rows.',
'gymwork.level.advancedR':'Heavy barbell compounds and hard bodyweight work.',
/* detailed teaching */
'gymwork.teach.setup':'Setup','gymwork.teach.steps':'How to do it',
'gymwork.teach.breathing':'Breathing','gymwork.teach.mistakes':'Common mistakes',
'gymwork.player.secDoneT':'Section complete! 🎉',
'gymwork.player.secDoneS':'Every exercise finished. Well earned.',
/* new exercise names */
'gymwork.ex.push-up':'Push-Up','gymwork.ex.goblet-squat':'Goblet Squat',
'gymwork.ex.warmup-jumping-jacks':'Jumping Jacks','gymwork.ex.warmup-arm-circles':'Arm Circles',
'gymwork.ex.warmup-leg-swings':'Leg Swings','gymwork.ex.warmup-bodyweight-squat':'Bodyweight Squat',
'gymwork.ex.warmup-high-knees':'High Knees',
'gymwork.ex.abs-crunch':'Crunch','gymwork.ex.abs-plank':'Plank Hold','gymwork.ex.abs-leg-raise':'Leg Raise',
'gymwork.ex.abs-bicycle':'Bicycle Crunch','gymwork.ex.abs-mountain-climber':'Mountain Climber',
'gymwork.ex.abs-russian-twist':'Russian Twist','gymwork.ex.abs-dead-bug':'Dead Bug',
'gymwork.ex.pilates-hundred':'The Hundred','gymwork.ex.pilates-roll-up':'Roll-Up',
'gymwork.ex.pilates-single-leg-stretch':'Single-Leg Stretch','gymwork.ex.pilates-glute-bridge':'Glute Bridge',
'gymwork.ex.pilates-side-leg-lift':'Side-Lying Leg Lift','gymwork.ex.pilates-bird-dog':'Bird Dog',
'gymwork.ex.zumba-salsa-basic':'Salsa Basic Step','gymwork.ex.zumba-merengue':'Merengue March',
'gymwork.ex.zumba-cumbia':'Cumbia Side Step','gymwork.ex.zumba-reggaeton':'Reggaeton Stomp',
'gymwork.ex.zumba-cooldown':'Cool-Down Stretch',
'gymwork.ex.db-floor-press':'Dumbbell Floor Press',
'gymwork.ex.machine-chest-press':'Machine Chest Press',
'gymwork.ex.db-shoulder-press':'Dumbbell Shoulder Press',
'gymwork.ex.bench-dips':'Bench Dips',
'gymwork.ex.pec-deck':'Pec Deck Fly',
'gymwork.ex.pike-push-up':'Pike Push-Up',
'gymwork.ex.cable-crossover':'Cable Crossover',
'gymwork.ex.close-grip-bench-press':'Close-Grip Bench Press',
'gymwork.ex.seated-cable-row':'Seated Cable Row',
'gymwork.ex.db-single-arm-row':'Single-Arm Dumbbell Row',
'gymwork.ex.assisted-pull-up':'Assisted Pull-Up',
'gymwork.ex.preacher-curl':'Preacher Curl',
'gymwork.ex.db-shrugs':'Dumbbell Shrugs',
'gymwork.ex.straight-arm-pulldown':'Straight-Arm Pulldown',
'gymwork.ex.concentration-curl':'Concentration Curl',
'gymwork.ex.reverse-curl':'Reverse Curl',
'gymwork.ex.leg-extension':'Leg Extension',
'gymwork.ex.step-up':'Step-Up',
'gymwork.ex.hip-thrust':'Hip Thrust',
'gymwork.ex.bulgarian-split-squat':'Bulgarian Split Squat',
'gymwork.ex.seated-calf-raise':'Seated Calf Raise',
'gymwork.ex.sumo-deadlift':'Sumo Deadlift',
'gymwork.ex.glute-kickback':'Glute Kickback',
'gymwork.ex.hip-abduction-machine':'Hip Abduction Machine',
'gymwork.ex.torso-twists':'Torso Twists',
'gymwork.ex.hip-circles':'Hip Circles',
'gymwork.ex.shoulder-rolls':'Shoulder Rolls',
'gymwork.ex.inchworm':'Inchworm',
'gymwork.ex.cat-cow':'Cat-Cow',
'gymwork.ex.glute-bridge':'Glute Bridge',
'gymwork.ex.reverse-crunch':'Reverse Crunch',
'gymwork.ex.flutter-kicks':'Flutter Kicks',
'gymwork.ex.heel-taps':'Heel Taps',
'gymwork.ex.plank-shoulder-taps':'Plank Shoulder Taps',
'gymwork.ex.side-plank':'Side Plank',
'gymwork.ex.hollow-hold':'Hollow Hold',
'gymwork.ex.ab-wheel-rollout':'Ab Wheel Rollout',
'gymwork.ex.leg-circles':'Leg Circles',
'gymwork.ex.double-leg-stretch':'Double Leg Stretch',
'gymwork.ex.spine-twist':'Spine Twist',
'gymwork.ex.swan-prep':'Swan Prep',
'gymwork.ex.mermaid-stretch':'Mermaid Stretch',
'gymwork.ex.teaser-prep':'Teaser Prep',
'gymwork.ex.bachata-basic':'Bachata Basic',
'gymwork.ex.samba-step':'Samba Step',
'gymwork.ex.hiphop-groove':'Hip-Hop Groove',
'gymwork.ex.soca-bounce':'Soca Bounce',
'gymwork.ex.belly-shimmy':'Belly Shimmy',
'gymwork.ex.neck-stretch':'Neck Stretch',
'gymwork.ex.cross-shoulder-stretch':'Cross-Shoulder Stretch',
'gymwork.ex.overhead-tricep-stretch':'Overhead Tricep Stretch',
'gymwork.ex.standing-quad-stretch':'Standing Quad Stretch',
'gymwork.ex.hamstring-fold':'Standing Hamstring Fold',
'gymwork.ex.hip-flexor-stretch':'Hip Flexor Stretch',
'gymwork.ex.childs-pose':'Child\'s Pose',
'gymwork.ex.cobra-stretch':'Cobra Stretch',
/* new technique cues */
'gymwork.tech.push-up.1':'Body in one straight line, head to heels.',
'gymwork.tech.push-up.2':'Chest nearly touches the floor each rep.',
'gymwork.tech.push-up.3':'Elbows at 45 degrees, not flared wide.',
'gymwork.tech.goblet-squat.1':'Hold the dumbbell tight to your chest.',
'gymwork.tech.goblet-squat.2':'Elbows touch inner knees at the bottom.',
'gymwork.tech.goblet-squat.3':'Drive through your whole foot to stand.',
'gymwork.tech.warmup-jumping-jacks.1':'Land softly on the balls of your feet.',
'gymwork.tech.warmup-jumping-jacks.2':'Reach arms fully overhead each rep.',
'gymwork.tech.warmup-jumping-jacks.3':'Keep a steady rhythm, not a sprint.',
'gymwork.tech.warmup-arm-circles.1':'Arms straight out at shoulder height.',
'gymwork.tech.warmup-arm-circles.2':'Circle forward, then reverse backward.',
'gymwork.tech.warmup-arm-circles.3':'Keep the torso perfectly still.',
'gymwork.tech.warmup-leg-swings.1':'Swing the leg like a pendulum.',
'gymwork.tech.warmup-leg-swings.2':'Stay tall — no leaning or twisting.',
'gymwork.tech.warmup-leg-swings.3':'Switch legs halfway through.',
'gymwork.tech.warmup-bodyweight-squat.1':'Hips below knees, chest proud.',
'gymwork.tech.warmup-bodyweight-squat.2':'Knees track out over the toes.',
'gymwork.tech.warmup-bodyweight-squat.3':'Arms reach forward for balance.',
'gymwork.tech.warmup-high-knees.1':'Drive knees to hip height.',
'gymwork.tech.warmup-high-knees.2':'Pump arms in opposition.',
'gymwork.tech.warmup-high-knees.3':'Land light and quick on the balls of your feet.',
'gymwork.tech.abs-crunch.1':'Curl shoulders off the floor — 30 degrees is enough.',
'gymwork.tech.abs-crunch.2':'Hands are a pillow — never pull the neck.',
'gymwork.tech.abs-crunch.3':'Squeeze the abs at the top of every rep.',
'gymwork.tech.abs-plank.1':'One straight line, head to heels.',
'gymwork.tech.abs-plank.2':'Squeeze glutes and brace the core.',
'gymwork.tech.abs-plank.3':'Stop when hips sag — quality beats duration.',
'gymwork.tech.abs-leg-raise.1':'Lower back pinned to the floor, always.',
'gymwork.tech.abs-leg-raise.2':'Legs stop just above the floor.',
'gymwork.tech.abs-leg-raise.3':'Raise slowly — no swinging.',
'gymwork.tech.abs-bicycle.1':'Opposite elbow to knee each rep.',
'gymwork.tech.abs-bicycle.2':'Extended leg hovers, never rests.',
'gymwork.tech.abs-bicycle.3':'Rotate from the torso, not the arms.',
'gymwork.tech.abs-mountain-climber.1':'Hips stay level — no bouncing.',
'gymwork.tech.abs-mountain-climber.2':'Drive knees to the chest quickly.',
'gymwork.tech.abs-mountain-climber.3':'Keep hands planted under shoulders.',
'gymwork.tech.abs-russian-twist.1':'Lean back 45 degrees, chest lifted.',
'gymwork.tech.abs-russian-twist.2':'Rotate from the waist; hands touch the floor each side.',
'gymwork.tech.abs-russian-twist.3':'Keep hips still throughout.',
'gymwork.tech.abs-dead-bug.1':'Lower back never leaves the floor.',
'gymwork.tech.abs-dead-bug.2':'Extend opposite arm and leg slowly.',
'gymwork.tech.abs-dead-bug.3':'Move in slow motion — control is everything.',
'gymwork.tech.pilates-hundred.1':'Head and shoulders curled up.',
'gymwork.tech.pilates-hundred.2':'Pump arms in small quick beats.',
'gymwork.tech.pilates-hundred.3':'Breathe in 5 beats, out 5 beats.',
'gymwork.tech.pilates-roll-up.1':'Peel up one vertebra at a time.',
'gymwork.tech.pilates-roll-up.2':'No momentum — pure control.',
'gymwork.tech.pilates-roll-up.3':'Roll down just as slowly as you came up.',
'gymwork.tech.pilates-single-leg-stretch.1':'Stay curled up the whole set.',
'gymwork.tech.pilates-single-leg-stretch.2':'Switch legs in one smooth flow.',
'gymwork.tech.pilates-single-leg-stretch.3':'Extended leg hovers at 45 degrees.',
'gymwork.tech.pilates-glute-bridge.1':'Knees, hips, shoulders in one line.',
'gymwork.tech.pilates-glute-bridge.2':'Squeeze glutes two seconds at the top.',
'gymwork.tech.pilates-glute-bridge.3':'Never arch the lower back.',
'gymwork.tech.pilates-side-leg-lift.1':'Hips stacked, body one straight line.',
'gymwork.tech.pilates-side-leg-lift.2':'Lift to hip height only.',
'gymwork.tech.pilates-side-leg-lift.3':'Lower slowly without touching down.',
'gymwork.tech.pilates-bird-dog.1':'Back flat like a tabletop.',
'gymwork.tech.pilates-bird-dog.2':'Arm, torso and leg form one line.',
'gymwork.tech.pilates-bird-dog.3':'Hold two seconds — no hip rotation.',
'gymwork.tech.zumba-salsa-basic.1':'Forward, back, together — then mirror.',
'gymwork.tech.zumba-salsa-basic.2':'Shift your full weight each step.',
'gymwork.tech.zumba-salsa-basic.3':'Let the hips sway with the rhythm.',
'gymwork.tech.zumba-merengue.1':'March with light, bouncy knees.',
'gymwork.tech.zumba-merengue.2':'The hip sway IS the dance.',
'gymwork.tech.zumba-merengue.3':'Keep shoulders relaxed and low.',
'gymwork.tech.zumba-cumbia.1':'Glide side to side — out, together.',
'gymwork.tech.zumba-cumbia.2':'Sway hips with every step.',
'gymwork.tech.zumba-cumbia.3':'Never cross the feet.',
'gymwork.tech.zumba-reggaeton.1':'Wide stance, knees always bent.',
'gymwork.tech.zumba-reggaeton.2':'Stomp with attitude, stay springy.',
'gymwork.tech.zumba-reggaeton.3':'Let the arms move with the music.',
'gymwork.tech.zumba-cooldown.1':'Move slowly — this is recovery.',
'gymwork.tech.zumba-cooldown.2':'Breathe in 4 counts, out 6.',
'gymwork.tech.zumba-cooldown.3':'Stretch gently, never forcefully.',
'gymwork.tech.db-floor-press.1':'Lie on the floor, knees bent, dumbbells at chest.',
'gymwork.tech.db-floor-press.2':'Press up until your arms are straight over your chest.',
'gymwork.tech.db-floor-press.3':'Lower until your upper arms touch the floor.',
'gymwork.tech.machine-chest-press.1':'Seat height: handles at mid-chest.',
'gymwork.tech.machine-chest-press.2':'Press forward without locking elbows hard.',
'gymwork.tech.machine-chest-press.3':'Return slowly until you feel a stretch.',
'gymwork.tech.db-shoulder-press.1':'Sit tall, dumbbells at shoulder height.',
'gymwork.tech.db-shoulder-press.2':'Press straight up until your arms are fully extended.',
'gymwork.tech.db-shoulder-press.3':'Lower slowly; do not arch your lower back.',
'gymwork.tech.bench-dips.1':'Hands on the bench behind you, legs extended.',
'gymwork.tech.bench-dips.2':'Lower until your elbows reach 90 degrees.',
'gymwork.tech.bench-dips.3':'Keep your back close to the bench.',
'gymwork.tech.pec-deck.1':'Forearms against the pads, chest up.',
'gymwork.tech.pec-deck.2':'Bring the pads together in a wide arc.',
'gymwork.tech.pec-deck.3':'Squeeze your chest; do not rush.',
'gymwork.tech.pike-push-up.1':'Hips high in an upside-down V shape.',
'gymwork.tech.pike-push-up.2':'Lower the crown of your head toward the floor.',
'gymwork.tech.pike-push-up.3':'Elbows track back, not flared wide.',
'gymwork.tech.cable-crossover.1':'Step forward, slight lean, handles high.',
'gymwork.tech.cable-crossover.2':'Sweep the handles down and together.',
'gymwork.tech.cable-crossover.3':'Keep a soft bend in the elbows.',
'gymwork.tech.close-grip-bench-press.1':'Hands shoulder-width apart on the bar.',
'gymwork.tech.close-grip-bench-press.2':'Lower to the lower chest, elbows tucked.',
'gymwork.tech.close-grip-bench-press.3':'Press up without flaring the elbows.',
'gymwork.tech.seated-cable-row.1':'Sit tall, chest up, slight knee bend.',
'gymwork.tech.seated-cable-row.2':'Pull the handle to your lower ribs.',
'gymwork.tech.seated-cable-row.3':'Squeeze shoulder blades; do not lean back far.',
'gymwork.tech.db-single-arm-row.1':'One knee and hand on the bench, back flat.',
'gymwork.tech.db-single-arm-row.2':'Row the dumbbell to your hip.',
'gymwork.tech.db-single-arm-row.3':'Lower slowly with a full stretch.',
'gymwork.tech.assisted-pull-up.1':'Knees on the platform, grip wide.',
'gymwork.tech.assisted-pull-up.2':'Pull your chest up to the bar.',
'gymwork.tech.assisted-pull-up.3':'Lower all the way down each rep.',
'gymwork.tech.preacher-curl.1':'Upper arms flat on the pad.',
'gymwork.tech.preacher-curl.2':'Curl up without lifting the elbows.',
'gymwork.tech.preacher-curl.3':'Lower fully; do not bounce.',
'gymwork.tech.db-shrugs.1':'Stand tall, dumbbells at your sides.',
'gymwork.tech.db-shrugs.2':'Shrug straight up toward your ears.',
'gymwork.tech.db-shrugs.3':'Pause at the top; no rolling.',
'gymwork.tech.straight-arm-pulldown.1':'Slight lean forward, arms straight.',
'gymwork.tech.straight-arm-pulldown.2':'Pull the bar down to your thighs.',
'gymwork.tech.straight-arm-pulldown.3':'Arms stay straight; hinge only at shoulders.',
'gymwork.tech.concentration-curl.1':'Elbow braced against your inner thigh.',
'gymwork.tech.concentration-curl.2':'Curl slowly, squeeze at the top.',
'gymwork.tech.concentration-curl.3':'No swinging the torso.',
'gymwork.tech.reverse-curl.1':'Overhand grip, arms at your sides.',
'gymwork.tech.reverse-curl.2':'Curl to shoulder height, wrists straight.',
'gymwork.tech.reverse-curl.3':'Lower slowly; do not swing.',
'gymwork.tech.leg-extension.1':'Back flat against the pad, ankles behind the roller.',
'gymwork.tech.leg-extension.2':'Extend until your legs are straight.',
'gymwork.tech.leg-extension.3':'Pause and squeeze your quads.',
'gymwork.tech.step-up.1':'Full foot on the bench, chest up.',
'gymwork.tech.step-up.2':'Drive through the heel to stand.',
'gymwork.tech.step-up.3':'Lower slowly; do not push off the back leg.',
'gymwork.tech.hip-thrust.1':'Upper back on the bench, bar over hips.',
'gymwork.tech.hip-thrust.2':'Drive hips up until knees, hips and shoulders align.',
'gymwork.tech.hip-thrust.3':'Squeeze your glutes hard at the top.',
'gymwork.tech.bulgarian-split-squat.1':'Rear foot on the bench, torso upright.',
'gymwork.tech.bulgarian-split-squat.2':'Lower until the front thigh is parallel.',
'gymwork.tech.bulgarian-split-squat.3':'Drive through the front heel.',
'gymwork.tech.seated-calf-raise.1':'Balls of feet on the platform, pads on knees.',
'gymwork.tech.seated-calf-raise.2':'Raise your heels as high as possible.',
'gymwork.tech.seated-calf-raise.3':'Pause at the top, stretch at the bottom.',
'gymwork.tech.sumo-deadlift.1':'Wide stance, toes out, chest up.',
'gymwork.tech.sumo-deadlift.2':'Push the floor away; hips and chest rise together.',
'gymwork.tech.sumo-deadlift.3':'Lock out tall; do not lean back.',
'gymwork.tech.glute-kickback.1':'On all fours, core braced.',
'gymwork.tech.glute-kickback.2':'Kick one heel up and back, squeezing the glute.',
'gymwork.tech.glute-kickback.3':'Do not arch your lower back.',
'gymwork.tech.hip-abduction-machine.1':'Back against the pad, feet on the rests.',
'gymwork.tech.hip-abduction-machine.2':'Push the pads apart with your outer thighs.',
'gymwork.tech.hip-abduction-machine.3':'Control the return; do not let it slam.',
'gymwork.tech.torso-twists.1':'Feet shoulder-width, arms out.',
'gymwork.tech.torso-twists.2':'Rotate side to side from the waist.',
'gymwork.tech.torso-twists.3':'Hips face forward; only the torso turns.',
'gymwork.tech.hip-circles.1':'Hands on hips, feet hip-width.',
'gymwork.tech.hip-circles.2':'Circle the hips wide and smooth.',
'gymwork.tech.hip-circles.3':'Reverse direction halfway.',
'gymwork.tech.shoulder-rolls.1':'Stand tall, arms relaxed.',
'gymwork.tech.shoulder-rolls.2':'Roll shoulders up, back, and down.',
'gymwork.tech.shoulder-rolls.3':'Make the circles big and slow.',
'gymwork.tech.inchworm.1':'Bend forward, hands to the floor.',
'gymwork.tech.inchworm.2':'Walk your hands out to a plank.',
'gymwork.tech.inchworm.3':'Walk feet to hands; stand up.',
'gymwork.tech.cat-cow.1':'On all fours, wrists under shoulders.',
'gymwork.tech.cat-cow.2':'Inhale: drop belly, lift head (cow).',
'gymwork.tech.cat-cow.3':'Exhale: round back, tuck chin (cat).',
'gymwork.tech.glute-bridge.1':'Lie on your back, knees bent.',
'gymwork.tech.glute-bridge.2':'Drive hips up, squeezing glutes.',
'gymwork.tech.glute-bridge.3':'Lower slowly without touching down.',
'gymwork.tech.reverse-crunch.1':'Lie back, knees bent over hips.',
'gymwork.tech.reverse-crunch.2':'Curl your hips off the floor toward your chest.',
'gymwork.tech.reverse-crunch.3':'Lower slowly; do not swing.',
'gymwork.tech.flutter-kicks.1':'Lie back, hands under your glutes.',
'gymwork.tech.flutter-kicks.2':'Alternate small quick kicks.',
'gymwork.tech.flutter-kicks.3':'Keep your lower back pressed down.',
'gymwork.tech.heel-taps.1':'Lie back, knees bent, arms at sides.',
'gymwork.tech.heel-taps.2':'Crunch slightly and tap each heel.',
'gymwork.tech.heel-taps.3':'Alternate sides with control.',
'gymwork.tech.plank-shoulder-taps.1':'High plank, feet hip-width.',
'gymwork.tech.plank-shoulder-taps.2':'Tap the opposite shoulder.',
'gymwork.tech.plank-shoulder-taps.3':'Keep your hips perfectly still.',
'gymwork.tech.side-plank.1':'Elbow under shoulder, body straight.',
'gymwork.tech.side-plank.2':'Lift your hips; hold without sagging.',
'gymwork.tech.side-plank.3':'Repeat on the other side.',
'gymwork.tech.hollow-hold.1':'Lie back, arms overhead.',
'gymwork.tech.hollow-hold.2':'Lift shoulders and legs slightly off the floor.',
'gymwork.tech.hollow-hold.3':'Press your lower back into the floor.',
'gymwork.tech.ab-wheel-rollout.1':'Kneel with the wheel under your shoulders.',
'gymwork.tech.ab-wheel-rollout.2':'Roll forward, keeping your core tight.',
'gymwork.tech.ab-wheel-rollout.3':'Never let your back sag.',
'gymwork.tech.leg-circles.1':'Lie back, one leg up to the ceiling.',
'gymwork.tech.leg-circles.2':'Draw slow circles with your toes.',
'gymwork.tech.leg-circles.3':'Keep your hips still on the mat.',
'gymwork.tech.double-leg-stretch.1':'Curl up, knees to chest.',
'gymwork.tech.double-leg-stretch.2':'Extend arms and legs long together.',
'gymwork.tech.double-leg-stretch.3':'Circle arms back and hug knees in.',
'gymwork.tech.spine-twist.1':'Sit tall, legs extended, arms in a T.',
'gymwork.tech.spine-twist.2':'Twist from the waist, pulsing twice.',
'gymwork.tech.spine-twist.3':'Hips stay glued to the mat.',
'gymwork.tech.swan-prep.1':'Lie face down, hands by your ribs.',
'gymwork.tech.swan-prep.2':'Press up, lengthening your spine.',
'gymwork.tech.swan-prep.3':'Shoulders melt away from your ears.',
'gymwork.tech.mermaid-stretch.1':'Sit sideways, legs folded.',
'gymwork.tech.mermaid-stretch.2':'Reach one arm overhead and lean.',
'gymwork.tech.mermaid-stretch.3':'Feel the long side-body stretch.',
'gymwork.tech.teaser-prep.1':'Sit with knees bent, spine tall.',
'gymwork.tech.teaser-prep.2':'Roll back to your shoulder blades.',
'gymwork.tech.teaser-prep.3':'Balance, then roll back up.',
'gymwork.tech.bachata-basic.1':'Step side, together, side, tap.',
'gymwork.tech.bachata-basic.2':'Let your hips sway with each step.',
'gymwork.tech.bachata-basic.3':'Stay light on the balls of your feet.',
'gymwork.tech.samba-step.1':'Bounce softly in your knees.',
'gymwork.tech.samba-step.2':'Step forward and back with hip action.',
'gymwork.tech.samba-step.3':'Keep the bounce continuous.',
'gymwork.tech.hiphop-groove.1':'Wide stance, chest proud.',
'gymwork.tech.hiphop-groove.2':'Bounce and add arm styling.',
'gymwork.tech.hiphop-groove.3':'Hit the beat with attitude.',
'gymwork.tech.soca-bounce.1':'Feet together, knees soft.',
'gymwork.tech.soca-bounce.2':'Bounce and wave your arms high.',
'gymwork.tech.soca-bounce.3':'Jump lightly on the chorus.',
'gymwork.tech.belly-shimmy.1':'Knees soft, core engaged.',
'gymwork.tech.belly-shimmy.2':'Shake your hips fast and small.',
'gymwork.tech.belly-shimmy.3':'Keep shoulders relaxed and still.',
'gymwork.tech.neck-stretch.1':'Sit or stand tall.',
'gymwork.tech.neck-stretch.2':'Tilt your ear toward your shoulder.',
'gymwork.tech.neck-stretch.3':'Hold gently; repeat each side.',
'gymwork.tech.cross-shoulder-stretch.1':'Bring one arm across your chest.',
'gymwork.tech.cross-shoulder-stretch.2':'Hug it gently with the other arm.',
'gymwork.tech.cross-shoulder-stretch.3':'Keep the shoulder down and relaxed.',
'gymwork.tech.overhead-tricep-stretch.1':'Reach one arm overhead.',
'gymwork.tech.overhead-tricep-stretch.2':'Bend the elbow, hand down your back.',
'gymwork.tech.overhead-tricep-stretch.3':'Press the elbow gently back.',
'gymwork.tech.standing-quad-stretch.1':'Stand tall, hold a wall for balance.',
'gymwork.tech.standing-quad-stretch.2':'Pull one foot to your glute.',
'gymwork.tech.standing-quad-stretch.3':'Keep knees together, hips forward.',
'gymwork.tech.hamstring-fold.1':'Stand with feet hip-width.',
'gymwork.tech.hamstring-fold.2':'Fold forward, reaching toward your toes.',
'gymwork.tech.hamstring-fold.3':'Let your head and neck hang heavy.',
'gymwork.tech.hip-flexor-stretch.1':'Half-kneel with the back knee down.',
'gymwork.tech.hip-flexor-stretch.2':'Tuck your pelvis and shift forward.',
'gymwork.tech.hip-flexor-stretch.3':'Feel the stretch at the front of the hip.',
'gymwork.tech.childs-pose.1':'Kneel, big toes touching.',
'gymwork.tech.childs-pose.2':'Fold forward, arms reaching long.',
'gymwork.tech.childs-pose.3':'Breathe deep into your back.',
'gymwork.tech.cobra-stretch.1':'Lie face down, hands under shoulders.',
'gymwork.tech.cobra-stretch.2':'Press your chest up gently.',
'gymwork.tech.cobra-stretch.3':'Keep hips on the floor, breathe.'
};
function subVars(s,v){
  return String(s).replace(/\{(\w+)\}/g,function(m,kk){ return (v&&v[kk]!==undefined)?v[kk]:m; });
}
const t=function(k,v){
  var s=k;
  try{ s=HUB.i18n.t(k,v); }catch(e){ s=k; }
  if(s!==k) return s;
  var e=EN[k];
  return e===undefined?k:subVars(e,v);
};
const ui=function(){ return HUB.ui; };
const st=function(){ return HUB.store.state; };
const DW=function(){ return HUB.gymworkData; };
const AN=function(){ return HUB.gymworkAnim; };

var DAYS=['mon','tue','wed','thu','fri','sat','sun'];
var DAYKEY=['sun','mon','tue','wed','thu','fri','sat'];
var AV_COLORS=['#E8590C','#0D9488','#2563EB','#B45309','#1F7A4D','#C2255C','#5F6C00'];

/* ---------- state ---------- */
function gymW(){ var g=st().gym; return (g&&g.workout)||null; }
function saveW(w){ var s=st(); s.gym=s.gym||{}; s.gym.workout=w; HUB.store.save(); }
function hasBeast(){ var g=st().gym; return !!(g&&g.workoutBadge); }
function dayStr(d){ d=d||new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function todayKey(){ return DAYKEY[new Date().getDay()]; }
function hashN(s){ s=String(s==null?'':s); var h=2166136261; for(var i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); } return h>>>0; }
function isSelfPerson(p){
  if(!p) return false;
  if(p.self) return true;
  try{ return !!(ui().isMe&&ui().isMe(p.name)); }catch(e){ return false; }
}
function isBeastBuddy(p){
  if(!p||!p.id||isSelfPerson(p)) return false;
  if(!p.sample) return false; /* demo people only: never imply a real contact earned it */
  /* Gym buddies appear only on a MUTUAL follow: they follow you AND you follow them. */
  try{
    if(HUB.people&&HUB.people.isMutual) return HUB.people.isMutual(p.id);
  }catch(e){}
  return false;
}
function orderGroups(orderId){
  var list=(DW()&&DW().SPLIT_ORDERS)||[];
  for(var i=0;i<list.length;i++) if(list[i].id===orderId) return list[i].groups.slice();
  return ['push','pull','legs'];
}
function splitKeyFor(groups){
  var list=(DW()&&DW().SPLIT_ORDERS)||[];
  for(var i=0;i<list.length;i++){
    var g=list[i].groups;
    if(g.length===groups.length&&g.every(function(x,j){ return x===groups[j]; })){
      return list[i].id==='ppl'?'ppl':(list[i].id==='plp'?'ppl2':'lpp');
    }
  }
  return 'ppl';
}
function logFor(w,ds){ return (w.log&&w.log[ds])||{}; }
/* Exercise list for a plan muscle group (level-tiered) or a standalone
   section id (warmup/abs/pilates/zumba — same for every level). */
function listFor(w,id){
  if(id==='warmup'||id==='abs'||id==='pilates'||id==='zumba'||id==='cooldown') return DW().sectionExercises(id);
  return DW().exercisesFor(id,w.level);
}
function doneCount(w,groupId,ds){
  var exs=listFor(w,groupId), lg=logFor(w,ds||dayStr()), n=0;
  exs.forEach(function(e){ if(lg[e.id]&&lg[e.id].done) n++; });
  return {done:n,total:exs.length};
}

/* ---------- BEAST MODE badge art ---------- */
function beastSVG(size){
  size=size||84;
  return '<img class="gwb-art" src="img/beast-badge.png" width="'+size+'" height="'+size+'"'+
    ' alt="'+ui().esc(t('gymwork.badge.name'))+'" draggable="false"'+
    ' style="border-radius:50%;box-shadow:0 6px 18px rgba(0,0,0,.45),0 0 22px rgba(249,115,22,.25)"/>';
}
function beastBadgeHTML(size,mini){
  if(!mini&&!hasBeast()) return '';
  return '<span class="gw-beastbadge" data-gwbeast="'+(mini?'mini':'me')+'" role="button" tabindex="0" aria-label="'+
    ui().esc(t('gymwork.badge.name'))+'" title="'+ui().esc(t('gymwork.badge.name'))+'">'+beastSVG(size)+'</span>';
}
function openBeastInfo(){
  var U=ui();
  U.openSheet('<div class="gw-cele">'+beastSVG(84)+
    '<div class="gw-gymmode">'+U.esc(t('gymwork.badge.gymmode'))+'</div>'+
    '<h2 style="margin:10px 0 6px">'+U.esc(t('gymwork.badge.info'))+'</h2>'+
    '<div class="gw-cele-name">'+U.esc(t('gymwork.badge.name'))+'</div>'+
    '<p class="sub" style="margin-top:8px;line-height:1.55">'+U.esc(t('gymwork.badge.desc'))+'</p>'+
    '<button class="btn btn-dark btn-block" data-close style="margin-top:12px">'+U.esc(t('gymwork.done'))+'</button></div>');
}

/* ---------- entry card (wraps HUB.gym.cardHTML) ---------- */
function planSummary(w){
  var U=ui();
  var tk=todayKey(), g=w.days[tk], prog='';
  if(g){ var c=doneCount(w,g); prog=' · '+c.done+'/'+c.total+' '+U.esc(t('gymwork.today')).toLowerCase(); }
  return t('gymwork.level.'+w.level)+' · '+t('gymwork.split.'+splitKeyFor(w.order))+prog;
}
function planCardHTML(){
  var U=ui(), w=gymW();
  return '<div class="card gw-card" style="margin-bottom:14px">'+
    '<div class="gw-cardhead"><span class="gw-flame" aria-hidden="true">'+beastSVG(34)+'</span><div>'+
    '<h3 class="gw-cardtitle">'+U.esc(t('gymwork.cardTitle'))+'</h3>'+
    '<p class="sub" style="margin:2px 0 0">'+U.esc(w?planSummary(w):t('gymwork.cardSub'))+'</p>'+
    '</div></div>'+
    '<button class="btn btn-dark" id="gwOpen" style="margin-top:10px">'+U.esc(t('gymwork.open'))+'</button></div>';
}

/* ---------- overlay manager ---------- */
var OV=[];
function destroyAnims(root){
  if(!AN()||!AN().destroy) return;
  var nl=root.querySelectorAll('.gw-thumb,.gw-stage');
  for(var i=0;i<nl.length;i++){ try{ AN().destroy(nl[i]); }catch(e){} }
}
function openOverlay(id,html){
  closeOverlay(id);
  var root=document.createElement('div');
  root.className='gw-root'; root.id='gwov-'+id;
  root.innerHTML='<div class="gw-scrim" data-gwclose="1"></div>'+
    '<div class="gw-panel" role="dialog" aria-modal="true">'+html+'</div>';
  document.body.appendChild(root);
  OV.push({id:id,root:root});
  return root.querySelector('.gw-panel');
}
function closeOverlay(id){
  for(var i=OV.length-1;i>=0;i--){
    if(OV[i].id===id){
      var o=OV.splice(i,1)[0];
      if(id==='player') stopRest();
      destroyAnims(o.root);
      if(o.root.parentNode) o.root.parentNode.removeChild(o.root);
    }
  }
}
function topOverlay(){ return OV.length?OV[OV.length-1]:null; }
function overlayOpen(id){ return OV.some(function(o){ return o.id===id; }); }
function closeAll(){
  for(var i=OV.length-1;i>=0;i--) closeOverlay(OV[i].id);
  PL=null;
}

/* ---------- setup wizard (sheet) ---------- */
var WIZ=null;
function openWizard(){
  WIZ={step:0,level:'beginner',orderId:'ppl',
    days:{mon:'push',tue:'pull',wed:'legs',thu:'push',fri:'pull',sat:'legs'}};
  renderWizard();
}
function wizSplitKey(id){ return id==='ppl'?'ppl':(id==='plp'?'ppl2':'lpp'); }
function renderWizard(){
  var U=ui(), h='';
  h+='<div class="gw-wiz"><div class="gw-steps">'+
    [0,1,2].map(function(i){ return '<span class="gw-stepdot'+(i===WIZ.step?' on':'')+(i<WIZ.step?' past':'')+'"></span>'; }).join('')+'</div>';
  if(WIZ.step===0){
    h+='<h2>'+U.esc(t('gymwork.wiz.levelT'))+'</h2><p class="sub" style="margin:4px 0 12px">'+U.esc(t('gymwork.wiz.levelS'))+'</p><div class="gw-optlist">';
    DW().LEVELS.forEach(function(lv){
      h+='<button class="gw-opt'+(WIZ.level===lv?' on':'')+'" data-wlvl="'+lv+'">'+
        '<span class="gw-optname">'+U.esc(t('gymwork.level.'+lv))+'</span>'+
        '<span class="gw-optdesc">'+U.esc(t('gymwork.level.'+lv+'D'))+'</span></button>';
    });
    h+='</div>';
  }else if(WIZ.step===1){
    h+='<h2>'+U.esc(t('gymwork.wiz.splitT'))+'</h2><p class="sub" style="margin:4px 0 12px">'+U.esc(t('gymwork.wiz.splitS'))+'</p><div class="gw-optlist">';
    DW().SPLIT_ORDERS.forEach(function(o){
      var k=wizSplitKey(o.id);
      h+='<button class="gw-opt'+(WIZ.orderId===o.id?' on':'')+'" data-wsplit="'+o.id+'">'+
        '<span class="gw-optname">'+U.esc(t('gymwork.split.'+k))+'</span>'+
        '<span class="gw-optseq">'+o.groups.map(function(g){ return U.esc(t('gymwork.group.'+g)); }).join(' → ')+'</span>'+
        '<span class="gw-optdesc">'+U.esc(t('gymwork.split.'+k+'D'))+'</span></button>';
    });
    h+='</div>';
  }else{
    h+='<h2>'+U.esc(t('gymwork.wiz.daysT'))+'</h2><p class="sub" style="margin:4px 0 12px">'+U.esc(t('gymwork.wiz.daysS'))+'</p><div class="gw-daylist">';
    DAYS.forEach(function(d){
      if(d==='sun'){
        h+='<div class="gw-dayrow locked"><span>'+U.esc(t('gymwork.day.sun'))+'</span><span class="gw-resttag">'+U.esc(t('gymwork.rest'))+'</span></div>';
      }else{
        h+='<button class="gw-dayrow" data-wday="'+d+'"><span>'+U.esc(t('gymwork.day.'+d))+'</span>'+
          '<span class="gw-grouptag">'+U.esc(t('gymwork.group.'+WIZ.days[d]))+'</span></button>';
      }
    });
    h+='</div>';
  }
  h+='<div class="row" style="gap:10px;margin-top:14px">'+
    (WIZ.step>0?'<button class="btn btn-ghost" id="gwWizBack" style="flex:1">'+U.esc(t('gymwork.back'))+'</button>':'')+
    '<button class="btn btn-dark" id="gwWizNext" style="flex:2">'+U.esc(t(WIZ.step===2?'gymwork.done':'gymwork.next'))+'</button></div></div>';
  U.openSheet(h);
  bindWizard();
}
function bindWizard(){
  var panel=document.getElementById('sheetBox'); if(!panel) return;
  panel.querySelectorAll('[data-wlvl]').forEach(function(b){
    b.onclick=function(){ WIZ.level=b.getAttribute('data-wlvl'); renderWizard(); };
  });
  panel.querySelectorAll('[data-wsplit]').forEach(function(b){
    b.onclick=function(){ WIZ.orderId=b.getAttribute('data-wsplit'); renderWizard(); };
  });
  panel.querySelectorAll('[data-wday]').forEach(function(b){
    b.onclick=function(){
      var d=b.getAttribute('data-wday'), groups=orderGroups(WIZ.orderId);
      var ix=groups.indexOf(WIZ.days[d]);
      WIZ.days[d]=groups[(ix+1)%groups.length];
      renderWizard();
    };
  });
  var back=document.getElementById('gwWizBack');
  if(back) back.onclick=function(){ WIZ.step--; renderWizard(); };
  var next=document.getElementById('gwWizNext');
  if(next) next.onclick=function(){
    if(WIZ.step<2){ WIZ.step++; renderWizard(); } else finishWizard();
  };
}
function finishWizard(){
  var old=gymW();
  var w={level:WIZ.level,order:orderGroups(WIZ.orderId),days:Object.assign({},WIZ.days),
    log:(old&&old.log)||{},startedAt:(old&&old.startedAt)||Date.now()};
  saveW(w);
  WIZ=null;
  ui().closeSheet();
  openPlan();
}

/* ---------- plan home ---------- */
function buddies(){
  var ppl=st().people||[];
  return ppl.filter(isBeastBuddy).slice(0,12);
}
function planHTML(w){
  var U=ui(), tk=todayKey(), ds=dayStr();
  var h='<div class="gw-topbar"><button class="gw-iconbtn" data-gwclose="1" aria-label="'+U.esc(t('gymwork.back'))+'">‹</button>'+
    '<h2 class="gw-title">'+U.esc(t('gymwork.plan.thisWeek'))+'</h2>'+
    '<button class="gw-linkbtn" data-gw="change">'+U.esc(t('gymwork.plan.change'))+'</button></div>';
  h+='<p class="sub gw-plansub">'+U.esc(t('gymwork.level.'+w.level))+' · '+U.esc(t('gymwork.split.'+splitKeyFor(w.order)))+'</p>';
  /* training-section picker: plan + warmup/abs/pilates/zumba */
  h+='<p class="gw-seclbl">'+U.esc(t('gymwork.plan.sectionsT'))+'</p><div class="gw-secrow" role="group">';
  ['plan','warmup','abs','pilates','zumba','cooldown'].forEach(function(s){
    h+='<button class="gw-secchip'+(s==='plan'?' on':'')+'" data-gwsec="'+s+'">'+U.esc(t('gymwork.sec.'+s))+'</button>';
  });
  h+='</div>';
  /* level switcher: free movement between levels, logs and progress are kept */
  h+='<p class="gw-seclbl">'+U.esc(t('gymwork.level.switchT'))+'</p><div class="gw-lvlrow" role="group">';
  DW().LEVELS.forEach(function(lv){
    h+='<button class="gw-lvl'+(w.level===lv?' on':'')+'" data-gwlvl="'+lv+'">'+U.esc(t('gymwork.level.'+lv))+'</button>';
  });
  h+='</div><p class="sub gw-lvlr">'+U.esc(t('gymwork.level.'+w.level+'R'))+'</p>';
  h+='<div class="gw-daylist">';
  DAYS.forEach(function(d){
    var g=w.days[d], isT=(d===tk), cls='gw-dayrow'+(isT?' today':'');
    var right;
    if(!g) right='<span class="gw-resttag">'+U.esc(t('gymwork.rest'))+'</span>';
    else{
      var c=doneCount(w,g,ds);
      right='<span class="gw-grouptag">'+U.esc(t('gymwork.group.'+g))+'</span>'+
        (isT?'<span class="gw-prog">'+c.done+'/'+c.total+'</span>':'');
    }
    h+='<button class="'+cls+'" '+(g?'data-gwday="'+g+'"':'disabled')+'>'+
      '<span class="gw-dayname">'+U.esc(t('gymwork.day.'+d))+(isT?' <span class="gw-todaytag">'+U.esc(t('gymwork.today'))+'</span>':'')+'</span>'+
      '<span class="gw-dayright">'+right+'</span></button>';
  });
  h+='</div>';
  var tg=w.days[tk];
  if(tg){
    var c2=doneCount(w,tg,ds);
    h+='<div class="gw-todaybar"><div class="gw-todayinfo"><span class="gw-todaylbl">'+
      U.esc(t('gymwork.group.'+tg))+' · '+U.esc(t('gymwork.today'))+'</span>'+
      '<span class="gw-progbar"><span style="width:'+Math.round(c2.done/Math.max(1,c2.total)*100)+'%"></span></span></div>'+
      '<button class="btn btn-dark" id="gwStart">'+U.esc(t('gymwork.start'))+'</button></div>';
  }else{
    h+='<div class="gw-todaybar gw-restday"><span>😴 '+U.esc(t('gymwork.rest'))+' — '+U.esc(t('gymwork.day.'+tk))+'</span></div>';
  }
  /* gym buddies */
  var bs=buddies();
  h+='<div class="gw-buddies"><h3>'+U.esc(t('gymwork.buddies.title'))+'</h3>'+
    '<p class="sub" style="margin:2px 0 10px">'+U.esc(t('gymwork.buddies.sub'))+'</p>';
  if(!bs.length){
    h+='<p class="sub">'+U.esc(t('gymwork.buddies.none'))+'</p>';
  }else{
    h+='<div class="gw-buddylist">';
    bs.forEach(function(p){
      var col=AV_COLORS[Math.abs(hashN(p.id))%AV_COLORS.length];
      h+='<div class="gw-buddy"><span class="gw-av" style="background:'+col+'">'+U.esc(U.initials(p.name||'?'))+'</span>'+
        '<span class="gw-buddyname">'+U.esc(p.name||'')+'</span>'+
        '<span class="gw-beastbadge" data-gwbeast="mini" role="button" tabindex="0" aria-label="'+U.esc(t('gymwork.badge.name'))+'">'+beastSVG(26)+'</span>'+
        '<button class="btn btn-ghost btn-sm" data-gwchat="'+U.esc(String(p.id))+'">'+U.esc(t('gymwork.buddies.chat'))+'</button></div>';
    });
    h+='</div>';
  }
  h+='</div>';
  return h;
}
function openPlan(){
  var w=gymW(); if(!w){ openWizard(); return; }
  var panel=openOverlay('plan',planHTML(w));
  void panel;
}
function openChangeConfirm(){
  var U=ui();
  U.openSheet('<div class="gw-confirm"><h2>'+U.esc(t('gymwork.plan.change'))+'</h2>'+
    '<p class="sub" style="margin:8px 0 14px;line-height:1.55">'+U.esc(t('gymwork.plan.confirmChange'))+'</p>'+
    '<div class="row" style="gap:10px"><button class="btn btn-ghost" data-close style="flex:1">'+U.esc(t('gymwork.plan.keep'))+'</button>'+
    '<button class="btn btn-dark" id="gwDiscard" style="flex:1">'+U.esc(t('gymwork.plan.discard'))+'</button></div></div>');
  var d=document.getElementById('gwDiscard');
  if(d) d.onclick=function(){ U.closeSheet(); openWizard(); };
}
function openBuddyChat(pid){
  var found=null;
  (st().people||[]).forEach(function(p){ if(String(p.id)===String(pid)) found=p; });
  if(!found) return;
  closeOverlay('plan'); closeOverlay('day');
  try{
    if(HUB.chat&&HUB.chat.openWith) HUB.chat.openWith({name:found.name,phone:found.phone||''},null,{skipSafety:true});
  }catch(e){}
}

/* ---------- day view ---------- */
function exMeta(ex,w){
  var p=DW().levelParams(ex.id,w.level);
  var setWord=p.sets===1?t('gymwork.set1'):t('gymwork.sets');
  var repPart=(/min/.test(p.reps))?p.reps:(p.reps+' '+t('gymwork.reps'));
  return p.sets+' '+setWord+' × '+repPart+' · '+
    t('gymwork.restT')+' '+p.rest+' '+t('gymwork.sec');
}
function dayHTML(w,groupId){
  var U=ui(), ds=dayStr(), lg=logFor(w,ds);
  var h='<div class="gw-topbar"><button class="gw-iconbtn" id="gwDayBack" aria-label="'+U.esc(t('gymwork.back'))+'">‹</button>'+
    '<h2 class="gw-title">'+U.esc(t('gymwork.group.'+groupId))+'</h2><span class="gw-todaytag">'+U.esc(t('gymwork.today'))+'</span></div>';
  h+='<div class="gw-exlist">';
  listFor(w,groupId).forEach(function(ex){
    var done=!!(lg[ex.id]&&lg[ex.id].done);
    var sd=lg[ex.id]&&lg[ex.id].setsDone;
    h+='<button class="gw-exrow'+(done?' gw-done':'')+'" data-gwex="'+ex.id+'">'+
      '<span class="gw-thumb" data-ex="'+ex.id+'"></span>'+
      '<span class="gw-exmeta"><span class="gw-exname">'+U.esc(t(ex.nameKey))+'</span>'+
      '<span class="gw-exsub">'+U.esc(exMeta(ex,w))+'</span>'+
      (sd&&!done?'<span class="gw-exsets">'+U.esc(t('gymwork.player.setOf',{a:Math.min(sd,DW().levelParams(ex.id,w.level).sets),b:DW().levelParams(ex.id,w.level).sets}))+'</span>':'')+
      '</span><span class="gw-excheck" aria-hidden="true">'+(done?'✓':'›')+'</span></button>';
  });
  h+='</div>';
  return h;
}
function openDay(groupId){
  var w=gymW(); if(!w||!groupId) return;
  var panel=openOverlay('day',dayHTML(w,groupId));
  panel.querySelectorAll('.gw-thumb').forEach(function(th){
    try{ AN().render(th,th.getAttribute('data-ex'),{mode:'thumb'}); }catch(e){}
  });
  var back=document.getElementById('gwDayBack');
  if(back) back.onclick=function(){ closeOverlay('day'); openPlan(); };
}

/* ---------- standalone sections: warmup / abs / pilates / zumba ---------- */
function sectionHTML(w,sid){
  var U=ui(), ds=dayStr(), lg=logFor(w,ds);
  var h='<div class="gw-topbar"><button class="gw-iconbtn" id="gwSecBack" aria-label="'+U.esc(t('gymwork.back'))+'">‹</button>'+
    '<h2 class="gw-title">'+U.esc(t('gymwork.sec.'+sid))+'</h2></div>';
  h+='<p class="sub gw-plansub">'+U.esc(t('gymwork.secD.'+sid))+'</p>';
  h+='<div class="gw-exlist">';
  listFor(w,sid).forEach(function(ex){
    var done=!!(lg[ex.id]&&lg[ex.id].done);
    var sd=lg[ex.id]&&lg[ex.id].setsDone;
    h+='<button class="gw-exrow'+(done?' gw-done':'')+'" data-gwex="'+ex.id+'">'+
      '<span class="gw-thumb" data-ex="'+ex.id+'"></span>'+
      '<span class="gw-exmeta"><span class="gw-exname">'+U.esc(t(ex.nameKey))+'</span>'+
      '<span class="gw-exsub">'+U.esc(exMeta(ex,w))+'</span>'+
      (sd&&!done?'<span class="gw-exsets">'+U.esc(t('gymwork.player.setOf',{a:Math.min(sd,DW().levelParams(ex.id,w.level).sets),b:DW().levelParams(ex.id,w.level).sets}))+'</span>':'')+
      '</span><span class="gw-excheck" aria-hidden="true">'+(done?'✓':'›')+'</span></button>';
  });
  h+='</div>';
  return h;
}
function openSection(sid){
  var w=gymW(); if(!w||!sid) return;
  var panel=openOverlay('section',sectionHTML(w,sid));
  panel.querySelectorAll('.gw-thumb').forEach(function(th){
    try{ AN().render(th,th.getAttribute('data-ex'),{mode:'thumb'}); }catch(e){}
  });
  var back=document.getElementById('gwSecBack');
  if(back) back.onclick=function(){ closeOverlay('section'); };
}
function openSectionDone(w,sid){
  var U=ui();
  U.openSheet('<div class="gw-cele"><div class="gw-celeart">'+beastSVG(84)+'</div>'+
    '<div class="gw-gymmode">'+U.esc(t('gymwork.badge.gymmode'))+'</div>'+
    '<h2 style="margin:10px 0 6px">'+U.esc(t('gymwork.player.secDoneT'))+'</h2>'+
    '<p class="sub" style="line-height:1.55">'+U.esc(t('gymwork.player.secDoneS'))+'</p>'+
    '<button class="btn btn-dark btn-block" id="gwSecFinish" style="margin-top:12px">'+U.esc(t('gymwork.player.finish'))+'</button></div>');
  var f=document.getElementById('gwSecFinish');
  if(f) f.onclick=function(){ U.closeSheet(); closeOverlay('section'); openPlan(); };
}

/* ---------- exercise player ---------- */
var PL=null, restInt=null;
function stopRest(){ if(restInt){ clearInterval(restInt); restInt=null; } }
function persistSets(w,exId,setsDone){
  var ds=dayStr();
  w.log=w.log||{}; w.log[ds]=w.log[ds]||{};
  var rec=w.log[ds][exId]||{setsDone:0,done:false};
  rec.setsDone=setsDone;
  w.log[ds][exId]=rec;
  saveW(w);
}
function markDone(w,exId){
  var ds=dayStr();
  w.log=w.log||{}; w.log[ds]=w.log[ds]||{};
  var rec=w.log[ds][exId]||{setsDone:0,done:false};
  rec.done=true;
  rec.setsDone=Math.max(rec.setsDone,DW().levelParams(exId,w.level).sets);
  w.log[ds][exId]=rec;
  saveW(w);
}
function dayExIds(w,groupId){ return listFor(w,groupId).map(function(e){ return e.id; }); }
function setLevel(lv){
  var w=gymW(); if(!w||w.level===lv) return;
  w.level=lv; saveW(w); /* logs and progress are untouched */
  closeOverlay('plan'); openPlan();
}
function nextIncomplete(w,groupId,afterId){
  var ids=dayExIds(w,groupId), lg=logFor(w,dayStr()), start=ids.indexOf(afterId)+1;
  for(var i=start;i<ids.length;i++){ if(!(lg[ids[i]]&&lg[ids[i]].done)) return ids[i]; }
  return null;
}
function fmtRest(ms){
  var s=Math.max(0,Math.ceil(ms/1000));
  return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');
}
function playerHTML(w){
  var U=ui(), ex=DW().byId(PL.exId), ids=dayExIds(w,PL.groupId);
  var ix=ids.indexOf(PL.exId);
  var h='<div class="gw-topbar"><button class="gw-iconbtn" id="gwPBack" aria-label="'+U.esc(t('gymwork.back'))+'">‹</button>'+
    '<h2 class="gw-title">'+U.esc(t(ex.nameKey))+'</h2>'+
    '<span class="gw-count">'+(ix+1)+'/'+ids.length+'</span></div>';
  h+='<div class="gw-stagewrap"><div class="gw-stage"></div></div>';
  h+='<div class="gw-chips"><span class="gw-chips-lbl">'+U.esc(t('gymwork.player.targets'))+'</span><span class="gw-chiprow">';
  /* data uses hyphenated muscle ids ('upper-back'); landed i18n keys are
     unhyphenated ('gymwork.m.upperback') — normalize for lookup */
  function muscleKey(m){ return 'gymwork.m.'+String(m).replace(/-/g,''); }
  /* data cue keys use the gymwork.cue.* prefix; landed i18n uses gymwork.tech.* */
  function cueKey(ck){ return String(ck).replace(/^gymwork\.cue\./,'gymwork.tech.'); }
  ex.muscles.primary.forEach(function(m){ h+='<span class="gw-mchip solid">'+U.esc(t(muscleKey(m)))+'</span>'; });
  ex.muscles.secondary.forEach(function(m){ h+='<span class="gw-mchip">'+U.esc(t(muscleKey(m)))+'</span>'; });
  h+='</span></div>';
  h+='<div class="gw-cues"><span class="gw-chips-lbl">'+U.esc(t('gymwork.player.technique'))+'</span><ol class="gw-cuelist">';
  ex.cues.forEach(function(ck){ h+='<li>'+U.esc(t(cueKey(ck)))+'</li>'; });
  h+='</ol></div>';
  /* detailed teaching: setup, step-by-step, breathing, common mistakes */
  if(ex.teach){
    var tc=ex.teach;
    h+='<div class="gw-teach">';
    h+='<div class="gw-tsec"><span class="gw-chips-lbl">'+U.esc(t('gymwork.teach.setup'))+'</span><p>'+U.esc(tc.setup)+'</p></div>';
    h+='<div class="gw-tsec"><span class="gw-chips-lbl">'+U.esc(t('gymwork.teach.steps'))+'</span><ol class="gw-cuelist">';
    tc.steps.forEach(function(s){ h+='<li>'+U.esc(s)+'</li>'; });
    h+='</ol></div>';
    h+='<div class="gw-tsec"><span class="gw-chips-lbl">'+U.esc(t('gymwork.teach.breathing'))+'</span><p>'+U.esc(tc.breathing)+'</p></div>';
    h+='<div class="gw-tsec"><span class="gw-chips-lbl">'+U.esc(t('gymwork.teach.mistakes'))+'</span><ul class="gw-mistakes">';
    tc.mistakes.forEach(function(s){ h+='<li>'+U.esc(s)+'</li>'; });
    h+='</ul></div>';
    h+='</div>';
  }
  h+='<div class="gw-setbar"><span class="gw-setof" id="gwSetOf">'+U.esc(t('gymwork.player.setOf',{a:PL.set+1,b:PL.params.sets}))+'</span></div>';
  h+='<div class="gw-pactions" id="gwPActions"></div>';
  var nx=nextIncomplete(w,PL.groupId,PL.exId);
  if(nx) h+='<p class="sub gw-nextup" style="margin:8px 2px 0">'+U.esc(t('gymwork.player.nextUp'))+': '+U.esc(t(DW().byId(nx).nameKey))+'</p>';
  return h;
}
function renderPlayerAction(){
  var box=document.getElementById('gwPActions'); if(!box||!PL) return;
  var U=ui(), h='';
  if(PL.phase==='rest'){
    h='<div class="gw-restline"><span class="gw-restlbl">'+U.esc(t('gymwork.player.resting'))+'</span>'+
      '<span class="gw-restclock" id="gwRestClock">'+fmtRest(PL.restUntil-Date.now())+'</span></div>'+
      '<button class="btn btn-ghost btn-block" id="gwPSkip">'+U.esc(t('gymwork.player.skipRest'))+'</button>';
  }else if(PL.phase==='set'){
    h='<button class="btn btn-dark btn-block" id="gwPDone">'+U.esc(t('gymwork.player.setDone'))+'</button>';
  }else if(PL.phase==='ready'){
    h='<button class="btn btn-dark btn-block" id="gwPComplete">🔥 '+U.esc(t('gymwork.player.completeEx'))+'</button>';
  }else{
    h='<button class="btn btn-dark btn-block" id="gwPStart">'+U.esc(t('gymwork.player.startSet'))+'</button>';
  }
  box.innerHTML=h;
  var so=document.getElementById('gwSetOf');
  if(so) so.textContent=t('gymwork.player.setOf',{a:Math.min(PL.set+1,PL.params.sets),b:PL.params.sets});
  bindPlayerActions();
}
function bindPlayerActions(){
  var b;
  b=document.getElementById('gwPStart'); if(b) b.onclick=function(){ PL.phase='set'; renderPlayerAction(); };
  b=document.getElementById('gwPDone'); if(b) b.onclick=onSetDone;
  b=document.getElementById('gwPSkip'); if(b) b.onclick=function(){ stopRest(); PL.phase='idle'; renderPlayerAction(); };
  b=document.getElementById('gwPComplete'); if(b) b.onclick=onCompleteEx;
}
function startRestTick(){
  stopRest();
  restInt=setInterval(function(){
    if(!PL){ stopRest(); return; }
    var remain=PL.restUntil-Date.now();
    if(remain<=0){ stopRest(); PL.phase='idle'; renderPlayerAction(); return; }
    var c=document.getElementById('gwRestClock');
    if(c) c.textContent=fmtRest(remain);
  },250);
}
function onSetDone(){
  var w=gymW(); if(!w||!PL) return;
  PL.set++;
  persistSets(w,PL.exId,PL.set);
  if(PL.set>=PL.params.sets){ PL.phase='ready'; }
  else{ PL.phase='rest'; PL.restUntil=Date.now()+PL.params.rest*1000; startRestTick(); }
  renderPlayerAction();
}
function onCompleteEx(){
  var w=gymW(); if(!w||!PL) return;
  stopRest();
  markDone(w,PL.exId);
  var gid=PL.groupId, nx=nextIncomplete(w,gid,PL.exId);
  var isSec=(gid==='warmup'||gid==='abs'||gid==='pilates'||gid==='zumba'||gid==='cooldown');
  if(!nx){
    PL=null;
    closeOverlay('player');
    if(isSec){ openSection(gid); openSectionDone(w,gid); }
    else{ openDay(gid); openDayDone(w,gid); }
    return;
  }
  var U=ui();
  try{ U.toast(t('gymwork.player.nextUp')+': '+t(DW().byId(nx).nameKey)); }catch(e){}
  openPlayer(nx);
}
function openDayDone(w,groupId){
  var U=ui();
  U.openSheet('<div class="gw-cele"><div class="gw-celeart">'+beastSVG(84)+'</div>'+
    '<div class="gw-gymmode">'+U.esc(t('gymwork.badge.gymmode'))+'</div>'+
    '<h2 style="margin:10px 0 6px">'+U.esc(t('gymwork.player.dayDoneT'))+'</h2>'+
    '<p class="sub" style="line-height:1.55">'+U.esc(t('gymwork.player.dayDoneS'))+'</p>'+
    '<button class="btn btn-dark btn-block" id="gwFinish" style="margin-top:12px">'+U.esc(t('gymwork.player.finish'))+'</button></div>');
  var f=document.getElementById('gwFinish');
  if(f) f.onclick=function(){ U.closeSheet(); closeOverlay('day'); openPlan(); };
}
function openPlayer(exId){
  var w=gymW(); if(!w) return;
  var ex=DW().byId(exId); if(!ex) return;
  stopRest();
  PL={exId:exId,groupId:((ex.section&&ex.section!=='plan')?ex.section:ex.group),set:0,phase:'idle',restUntil:0,params:DW().levelParams(exId,w.level)};
  var ds=dayStr(), lg=logFor(w,ds), rec=lg[exId];
  if(rec&&!rec.done&&rec.setsDone>0) PL.set=Math.min(rec.setsDone,PL.params.sets);
  var panel=openOverlay('player',playerHTML(w));
  try{ AN().render(panel.querySelector('.gw-stage'),exId,{mode:'full'}); }catch(e){}
  renderPlayerAction();
  var back=document.getElementById('gwPBack');
  if(back) back.onclick=function(){ PL=null; stopRest(); closeOverlay('player'); };
}
function openEarnSheet(){
  var U=ui();
  U.openSheet('<div class="gw-cele"><div class="gw-celeart gw-pop">'+beastSVG(84)+'</div>'+
    '<div class="gw-earnedtag">'+U.esc(t('gymwork.badge.earnedT'))+'</div>'+
    '<div class="gw-gymmode">'+U.esc(t('gymwork.badge.gymmode'))+'</div>'+
    '<h2 style="margin:6px 0">'+U.esc(t('gymwork.badge.name'))+'</h2>'+
    '<p class="sub" style="line-height:1.55">'+U.esc(t('gymwork.badge.earnedS'))+' '+U.esc(t('gymwork.badge.desc'))+'</p>'+
    '<button class="btn btn-dark btn-block" data-close style="margin-top:12px">'+U.esc(t('gymwork.start'))+'</button></div>');
}
function startWorkout(){
  var w=gymW(); if(!w) return;
  var g=w.days[todayKey()]; if(!g) return;
  var s=st(); s.gym=s.gym||{};
  if(!s.gym.workoutBadge){
    s.gym.workoutBadge=true;
    HUB.store.save();
    openEarnSheet();
    return;
  }
  openDay(g);
}

/* ---------- entry ---------- */
function open(){ if(gymW()) openPlan(); else openWizard(); }

/* ---------- wiring: wraps + delegated events ---------- */
function installWraps(){
  try{
    if(HUB.gym&&HUB.gym.cardHTML&&!HUB.gym._gwWrapped){
      var _c=HUB.gym.cardHTML;
      HUB.gym.cardHTML=function(){
        var base='';
        try{ base=_c(); }catch(e){ base=''; }
        try{ return base+planCardHTML(); }catch(e2){ return base; }
      };
      HUB.gym._gwWrapped=true;
    }
  }catch(e){}
  try{
    if(HUB.badges&&!HUB.badges._gwHH){
      var _hh=HUB.badges.headerHTML;
      HUB.badges.headerHTML=function(p){
        var h='';
        try{ h=_hh(p); }catch(e){ h=''; }
        try{ return h+beastBadgeHTML(26,false); }catch(e2){ return h; }
      };
      HUB.badges._gwHH=true;
    }
    if(HUB.badges&&!HUB.badges._gwFP){
      var _fp=HUB.badges.forPerson;
      HUB.badges.forPerson=function(p){
        var h='';
        try{ h=_fp(p); }catch(e){ h=''; }
        try{ if(isBeastBuddy(p)) h+='<span class="gw-beastbadge" data-gwbeast="mini" role="button" tabindex="0" aria-label="'+ui().esc(t('gymwork.badge.name'))+'">'+beastSVG(26)+'</span>'; }
        catch(e2){}
        return h;
      };
      HUB.badges._gwFP=true;
    }
    /* tab switches clear overlays across the app (see showTab): a gymwork
       overlay must never cover the newly shown tab */
    if(HUB.showTab&&!HUB._gwShowTab){
      var _st=HUB.showTab;
      HUB.showTab=function(n){ try{ closeAll(); }catch(e){} return _st(n); };
      HUB._gwShowTab=true;
    }
  }catch(e){}
}

/* beast badge taps: capture phase so the surrounding badge buttons
   (me-badges / hp-badges showcase openers) never fire */
document.addEventListener('click',function(e){
  var b=e.target&&e.target.closest?e.target.closest('[data-gwbeast]'):null;
  if(!b) return;
  e.stopPropagation();
  e.preventDefault();
  openBeastInfo();
},true);

document.addEventListener('click',function(e){
  var q=function(sel){ return (e.target&&e.target.closest)?e.target.closest(sel):null; };
  var el;
  if(q('#gwOpen')){ open(); return; }
  if(q('#gwStart')){ startWorkout(); return; }
  if((el=q('[data-gwclose]'))){
    var ov=q('.gw-root');
    if(ov&&ov.id.indexOf('gwov-')===0) closeOverlay(ov.id.slice(5));
    return;
  }
  if((el=q('[data-gw="change"]'))){ openChangeConfirm(); return; }
  if((el=q('[data-gwday]'))){ openDay(el.getAttribute('data-gwday')); return; }
  if((el=q('[data-gwsec]'))){ var gs=el.getAttribute('data-gwsec'); if(gs&&gs!=='plan') openSection(gs); return; }
  if((el=q('[data-gwlvl]'))){ setLevel(el.getAttribute('data-gwlvl')); return; }
  if((el=q('[data-gwchat]'))){ openBuddyChat(el.getAttribute('data-gwchat')); return; }
  if((el=q('[data-gwex]'))){ openPlayer(el.getAttribute('data-gwex')); return; }
},false);

/* Escape: close my top overlay, but yield when a sheet or chat sits above */
document.addEventListener('keydown',function(e){
  if(e.key!=='Escape'&&e.key!=='Esc') return;
  if(!OV.length) return;
  var sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden) return;
  var ch=document.getElementById('chatRoot');
  if(ch&&!ch.hidden) return;
  var top=topOverlay();
  closeOverlay(top.id);
  if(top.id==='player'){ PL=null; }
  try{ e.stopImmediatePropagation(); }catch(e2){}
  e.preventDefault();
},false);

/* ---------- debug hooks ---------- */
var DBG={
  state:function(){ return gymW(); },
  seedPlan:function(){
    saveW({level:'beginner',order:['push','pull','legs'],
      days:{mon:'push',tue:'pull',wed:'legs',thu:'push',fri:'pull',sat:'legs'},
      log:{},startedAt:Date.now()});
    return gymW();
  },
  awardBadge:function(){
    var s=st(); s.gym=s.gym||{}; s.gym.workoutBadge=true; HUB.store.save(); return true;
  },
  reset:function(){
    var s=st(); s.gym=s.gym||{}; s.gym.workout=null; HUB.store.save(); return true;
  }
};

/* ---------- init ---------- */
try{ st().gym=st().gym||{}; }catch(e){}
installWraps();
/* app.js (which defines HUB.showTab) loads after this file, so retry the
   wraps on window load to catch late-arriving namespaces. installWraps is
   idempotent via its _gw* flags. */
if(document.readyState==='complete'){ installWraps(); }
else{ window.addEventListener('load',installWraps); }

HUB.gymwork={
  open:open, openWizard:openWizard, openPlan:openPlan, openDay:openDay,
  openPlayer:openPlayer, startWorkout:startWorkout, close:closeAll,
  hasPlan:function(){ return !!gymW(); }, hasBadge:hasBeast,
  beastSVG:beastSVG, planCardHTML:planCardHTML,
  _debug:DBG
};
})();
