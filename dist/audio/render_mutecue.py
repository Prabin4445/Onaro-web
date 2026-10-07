#!/usr/bin/env python3
"""Onaro mute cue — 100% original synthesis (2026-09-23).

PraBin's brief: when an admin mutes someone in a group call, the generic
notification chime was "not good listening" — this is a dedicated, soft,
gentle feedback cue: a descending two-note chime, modern and smooth,
clearly feedback (not an alarm, not a ringtone).

Composition (original, nothing sampled/copied):
  - 1.0 s, mono, 44100 Hz / 16-bit.
  - Two soft warm bell notes, descending: A5 -> E5 (the notification chime
    plays E5 -> A5; the mute cue uses the same notes reversed, so it sits
    in the same sonic family but reads as "settling down", not "alert").
  - Note 1 at t=0.0 s (vel 0.75), note 2 at t=0.38 s (vel 0.60), slight
    overlap for a gentle legato feel; everything rests by t=1.0 s.
  - Voice: soft bell (same family as the Aurora ringtone lead) — sine
    partials [1.0, 0.32, 0.14, 0.06] at [1, 2, 3, 4.02]x, per-partial
    exponential decay (highs die faster), 20 ms raised-cosine attack
    (never harsh), 60 ms raised-cosine end-fade on every note, plus a
    faint octave-down warmth layer at low gain tying it to the Aurora bed.
  - Mastered quiet: peak-normalized to 0.50 (-6.0 dBFS) — deliberately
    modest next to the ringtones (peak 0.87), clearly a feedback tick,
    never clipping.

Regenerate: python3 audio/render_mutecue.py /tmp/mutecue_out
(needs numpy), then encode:
  ffmpeg -i in.wav -codec:a libmp3lame -b:a 128k -ar 44100 out.mp3
  ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg
"""
import numpy as np
import wave, sys, os

SR = 44100
DUR = 1.0
N = int(SR * DUR)

def midi(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)

# (start_s, midi_note, velocity) — soft descending pair, gentle overlap
NOTES = [
    (0.00, 81, 0.75),  # A5
    (0.38, 76, 0.60),  # E5
]
NOTE_DUR = 0.62         # each note rings out 0.62 s
ATK = 0.020             # 20 ms raised-cosine attack
ENDFADE = 0.060         # 60 ms raised-cosine end-fade: no clicks/pops

def bell(f, dur, rng, vel):
    """Soft warm bell voice (Aurora family): rounded partials with
    per-partial decay, gentle attack, own end-fade."""
    ln = int(dur * SR)
    nn = np.arange(ln)
    parts = [(1.00, 1.00, 0.90), (0.32, 2.00, 0.55),
             (0.14, 3.00, 0.36), (0.06, 4.02, 0.24)]
    tone = np.zeros(ln)
    det = 1.0 + rng.uniform(-3, 3) / 1200.0   # +/-3 cents, not robotic
    ph = rng.uniform(0, 2 * np.pi)
    for (a, mu, tau) in parts:
        tone += a * np.exp(-nn / (SR * tau)) * np.sin(
            2 * np.pi * f * mu * det * nn / SR + ph)
    atk = int(ATK * SR)
    tone[:atk] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(atk) / atk)
    tone *= 0.30 * vel
    # faint octave-down warmth layer (Aurora-family bed tie-in)
    sub = (np.exp(-nn / (SR * 1.1)) * np.sin(2 * np.pi * f / 2 * det * nn / SR + ph)
           + 0.3 * np.exp(-nn / (SR * 0.7)) * np.sin(2 * np.pi * f * det * nn / SR + ph))
    sub[:atk] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(atk) / atk)
    tone += sub * 0.030 * vel
    # 60 ms end-fade: no step at the note tail, no click
    fn = min(ln, int(ENDFADE * SR))
    tone[-fn:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(fn) / fn)
    return tone

def render():
    out = np.zeros(N)
    rng = np.random.default_rng(20260923)
    for (ts, m, vel) in NOTES:
        f = midi(m)
        tone = bell(f, NOTE_DUR, rng, vel)
        st = int(ts * SR)
        ln = tone.shape[0]
        out[st:st + ln] += tone[:min(ln, N - st)]
    return out

def write_wav(path, sig):
    peak = np.max(np.abs(sig))
    rms = np.sqrt(np.mean(sig ** 2))
    print(f"pre-master peak: {peak:.4f}, rms: {rms:.4f}")
    sig = sig / peak * 0.50          # -6.0 dBFS: modest feedback level
    # global guard: whole cue starts and ends in silence by design, but a
    # 5 ms pad on each end guarantees no boundary step after mastering
    pad = int(0.005 * SR)
    sig = np.concatenate([np.zeros(pad), sig, np.zeros(pad)])
    pcm = (np.clip(sig, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {path}: {len(sig)/SR:.3f}s, peak {np.max(np.abs(sig)):.4f} "
          f"({20*np.log10(np.max(np.abs(sig))):.2f} dBFS), "
          f"rms {np.sqrt(np.mean(sig.astype(np.float64)**2)):.4f}")

if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
    os.makedirs(dest, exist_ok=True)
    write_wav(os.path.join(dest, "mutecue.wav"), render())
