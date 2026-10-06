# Onaro sounds — 100% original, synthesized in code

Every sound here was generated from scratch with Python + numpy. **No
samples, no stock audio, no copyrighted material** — every byte is a sine
partial computed at build time.

## Current ringtones (2026-09-23, PraBin's ask: "modern 2026, soft, with bass"
+ "make it feel like calls coming" + "with that base and some tone on it")

Two original ambient call tones, 16.0 s seamless stereo loops at
44100 Hz / 16-bit. Same original composition, two timbres:

- **Aurora Soft** (`ringtone-aurora`) — the default for fresh installs.
  The sub-bass bed is the FOUNDATION: root sine (F1/A1/D2/Bb1) + faint
  2nd harmonic, 0.5 Hz breathing swell, mono, across
  Fmaj7 → Am7 → Dm9 → Bbmaj9 (4 s each). ON TOP of the bass rides a warm
  melodic tone — a soft rounded bell/piano voice playing the classic
  incoming-call cadence: one "ring" per bar (two warm strikes,
  fifth → third of the bar chord: Fmaj7 C5→A5, Am7 E5→G5,
  Dm9 A5→F5, Bbmaj9 F5→D5), then a breathing pause.
  A gentle rhythmic pulse (soft low "tock" on the beat during each ring
  phrase only) gives ringtone drive without filling the pauses.
  Ring/pause contrast measured ≥1.5× RMS per bar — unmistakably a call,
  never alarm-like. Warm airy pads sit under the lead (detuned
  sine-partial stacks, equal-gain raised-cosine crossfades at bar lines;
  bar 4's tail wraps onto bar 1 so the loop point is bit-continuous),
  with sparse airy shimmer on top.
- **Aurora Breeze** (`ringtone-breeze`) — slightly brighter sibling:
  brighter pad/bell partials, ×2.2 shimmer, a touch more sub pulse
  (0.75 Hz).
- Seamless by construction: pads crossfade (atk+rel sum to 1), bass
  starts/ends each bar at 0, every bell/tock/shimmer note gets a 50 ms
  end-fade. Junction step measured < 1/10 of the signal's normal
  sample-to-sample variation on both channels — no clicks.
- Mastered SOFT: peak-normalized to 0.87 (−1.2 dBFS, so even the lossy
  encodes stay under −1 dBFS), RMS ≈ 0.17
  (the lead tone sits clearly on top of the bass bed, still calm —
  not alarm-like). Never clipped.
- Regenerate: `python3 audio/render_aurora.py /tmp/aurora_out`
  (needs numpy), then encode:
  `ffmpeg -i in.wav -codec:a libmp3lame -b:a 160k -ar 44100 out.mp3`
  `ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg`

## Recipe (ringtones v2 — removed 2026-09-22)

- Sample rate 44100 Hz, mono, 16-bit.
- **Onaro Classic** (`ringtone-classic`): warm marimba-like voice (sine +
  strong 4th partial + soft sub octave), playing an original 6-note arch
  melody in C major: E5 → G5 → A5 → G5 → E5 → D5. 1.6 s phrase × 2.
- **Onaro Warm** (`ringtone-warm`): gentle music-box voice (airy upper
  partials, longer ring), playing an original lullaby-like descent:
  C6 → A5 → F5 → G5 → A5(held). 1.8 s phrase × 2.
- Both: 25 ms raised-cosine attacks (never harsh), one phrase built in
  integer samples then tiled ×2 so the loop is bit-identical and
  click-free, 120 ms phrase-end fades.
- Mastering for loudness: peak-normalize → tanh soft saturation (gentle
  compression + harmonic richness) → peak 0.95. v2 RMS ≈ 0.40 vs v1's
  0.20 — roughly twice as loud, cuts through a noisy room.
- **Onaro Piano** (`ringtone-piano`): piano-like voice — 8 partials with
  per-partial exponential decay (high partials die faster), slight
  inharmonicity (B=0.0002), 8 ms hammer attack + tiny strike transient,
  bass notes ring longer. Original F-major descending phrase:
  C5 → Bb4 → A4 → G4 → F4(held). 1.6 s phrase × 2.
- **Onaro Violin** (`ringtone-violin`): bowed-string voice — 12-partial
  saw-ish series, 90 ms bow swell, 6 Hz vibrato ramping to ±0.7% depth,
  legato overlap between notes. Original D-major lyrical arch:
  D5 → F#5 → E5(held). 1.6 s phrase × 2.
- **Onaro Guitar** (`ringtone-guitar`): electric-lead voice — plucked 5 ms
  attack, mild tube-style tanh saturation (warm, tasteful, not harsh),
  one note carries a sung +1-semitone bend. Original A-minor-pentatonic
  lead line: A4 → C5 → D5 → E5(bent) → D5 → C5(held). 1.6 s phrase × 2.
- Mastering for pleasantness, NOT loudness: RMS normalize → gentle tanh
  saturation → peak 0.95 → final RMS trim to **0.40** (same as Classic/Warm —
  deliberately not hotter).
- (Removed 2026-09-22: the "Onaro Calling" vocal ringtone — PraBin found it
  too loud and harsh. Replaced by the three instrument ringtones above.)
- **notify** (0.7 s): two-note E5 → A5 bell chime in the same family,
  kept from v1 (not alarm-like).

## Files

`ringtone-aurora.{wav,mp3,ogg}` — "Aurora Soft": the modern 2026 ambient
call tone, default for fresh installs (16 s seamless stereo loop).
`ringtone-breeze.{wav,mp3,ogg}` — "Aurora Breeze": brighter alt (16 s).
`ringtone-phone.{wav,mp3,ogg}` — the classic old-telephone bell
("Classic Phone", 6.0 s click-free loop, kept for existing users).
`notify.{wav,mp3,ogg}` — toast/notification chime (unchanged).
MP3 (160k) + OGG (q4) via ffmpeg; WAV kept as the universal fallback.
`js/sound.js` picks MP3 first, WAV if the browser can't play MP3.

Set it in Me > Settings > Ringtone (persisted in prefs; default
Aurora Soft). "Use my own" lets the user add their own audio file.

## Removed 2026-09-22 (PraBin's order: "Remove all music we made")

All synthesized music ringtones were deleted:
`ringtone-classic.*`, `ringtone-warm.*`, `ringtone-piano.*`,
`ringtone-violin.*`, `ringtone-guitar.*` (and the earlier `ringtone-vocal.*`).
Saved prefs with any of those keys silently migrate to `aurora` on load.
Existing `phone` and `custom` choices are never touched.

## Recipe (Classic Phone bell)

- Sample rate 44100 Hz, mono, 16-bit.
- Two bells: A ~2100 Hz, B ~2550 Hz, struck alternately by the clapper at
  ~40 strikes/sec during the 2 s ON period. Each strike: inharmonic
  small-bell partials [1.00, 2.76, 5.40, 8.93] with exponential decay
  (highs die faster), 1.5 ms attack, ±5 cents detune and ±1.5 ms timing
  jitter per strike so it doesn't sound robotic.
- ON envelope: 5 ms fade-in, 60 ms raised-cosine fade-out; 4 s of silence
  after; the 6 s loop boundary sits inside silence → click-free.
- Mastering: ringing-period RMS → 0.40 (pleasant, same loudness as the
  old ringtones), gentle tanh warmth, peak capped at 0.95.
- Regenerate with: `python3 /tmp/synth_phone.py` (needs numpy + ffmpeg).

## Honest caveats

- Browser autoplay policies may block the first sound until the user has
  interacted with the page once; `HUB.sound` retries a blocked ringtone
  after the first tap/keypress and never throws.
- Regenerate instrumentals with: `python3 /tmp/synth_instruments.py`
  (needs numpy + ffmpeg). (v2 marimba/music-box: `python3 /tmp/synth_ringtones.py`.)

## Laser notification chime (2026-09-29, PraBin's ask: "laser beam sound effect")

- **Laser pew** (`notify`) — the toast/login notification chime, replacing the
  old generic chime. 0.65 s mono 44100 Hz / 16-bit: a 2100 -> 210 Hz
  exponential sine sweep with gentle vibrato (the classic laser "pew"),
  2nd/3rd-harmonic zap texture, a soft-clipped 5th-partial bite in the
  first 80 ms, and a 60 ms upward charge blip up front. 6 ms attack,
  80 ms end-fade, peak-normalized to 0.50 (-6.0 dBFS) like the mute cue.
- Regenerate: `python3 audio/render_laser.py /tmp/laser_out` (needs numpy),
  then encode:
  `ffmpeg -i in.wav -codec:a libmp3lame -b:a 128k -ar 44100 out.mp3`
  `ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg`
## Cinematic notification chime (2026-09-29, PraBin's ask round 2: "movie sounds,
bass on it, heavy, adult type, with some space feelings")

- Replaces the laser "pew" (he said it sounded like kids). 1.4 s mono
  44100 Hz / 16-bit: 49 Hz sub-bass swell foundation + A1/E2/A2/C3 minor
  braam stack (low brass-ish odd-harmonic voices) + 130->48 Hz punch
  transient + airy 2800->700 Hz space sweep + distant G6/C7 shimmer.
  150 ms end-fade, peak-normalized to 0.60 (-4.4 dBFS). 97.5% of energy
  below 160 Hz — genuinely bass-heavy; strong harmonics so the weight
  survives phone speakers.
- Regenerate: `python3 audio/render_notify_cinema.py /tmp/cinema_out`
  (needs numpy), then encode:
  `ffmpeg -i in.wav -codec:a libmp3lame -b:a 128k -ar 44100 out.mp3`
  `ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg`
## Sweet bird-whistle notification (2026-09-29, PraBin's ask round 3)

- "Remove sound effect from all except ringtone and notification. On
  notifications I want like a bird sound, sweet bird whistle sound."
- `notify` is now a sweet songbird whistle: 1.5 s mono 44100 Hz / 16-bit —
  three quick ascending chirps (2.6->3.35 kHz glides, 8.5 Hz warble) then a
  long descending warble (3.3->2.3 kHz, 7 Hz warble). Pure sine voice, 100%
  of energy in the 2-4 kHz whistle band, peak 0.50 (-6.0 dBFS).
- Removed in the same round: calculator key-click synth + its header toggle
  chip (js/calc.js), and the group-call admin mute cue (playMuteCue is now a
  silent no-op in js/sound.js; audio/mutecue.* deleted). Only the call
  ringtone and the notification whistle remain.
- Regenerate: `python3 audio/render_notify_bird.py /tmp/bird_out`
  (needs numpy), then encode:
  `ffmpeg -i in.wav -codec:a libmp3lame -b:a 128k -ar 44100 out.mp3`
  `ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg`

## All notification/UI sounds removed (2026-09-29, PraBin's ask round 4)

- "Remove that sound effect of changing gender and or saving anything within
  app and login. Make it all silent, I don't want any sound effect. Only
  need ringtone thats all"
- The sweet bird-whistle `notify` (round 3 above) is GONE: audio/notify.*
  deleted, `HUB.sound.playNotification()` is now a silent no-op in
  js/sound.js (callers in store.js toast and incoming.js keep working
  unchanged), and the store.js toast no longer attempts any chime — profile
  saves, gender changes, login and all other toasts are fully silent.
- Only the call ringtone (Aurora Soft default) remains audible anywhere in
  the app, incl. its ME-tab picker + preview. Generator script
  audio/render_notify_bird.py kept for documentation.
