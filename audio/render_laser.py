#!/usr/bin/env python3
"""Onaro laser notification chime — 100% original synthesis (2026-09-29).

PraBin's brief: replace the generic notification chime (heard at login and
on toasts) with a laser-beam sound effect — sci-fi "pew", but clean and
pleasant, not harsh. Original composition, nothing sampled/copied.

Composition (original):
  - 0.65 s, mono, 44100 Hz / 16-bit.
  - Main voice: a sine sweep falling exponentially from 2100 Hz to 210 Hz
    over 0.38 s (the classic laser "pew" gesture), with a gentle 28 Hz
    vibrato (+/-12 cents) for shimmer.
  - Zap texture: the sweep's 2nd and 3rd harmonics at low gain with faster
    decay give it edge without harshness; a faint square-ish bite (soft-
    clipped 5th partial) only in the first 80 ms for the "zap" attack.
  - Charge blip: a 60 ms upward flick (900 -> 2100 Hz) right before the main
    sweep at very low gain — reads as the beam charging, adds character.
  - Envelope: 6 ms raised-cosine attack (no click), exponential decay,
    80 ms raised-cosine end-fade (no pop). Everything rests by 0.65 s.
  - Mastered modest: peak-normalized to 0.50 (-6.0 dBFS) — a UI chime,
    same level as the mute cue, never clipping.

Regenerate: python3 audio/render_laser.py /tmp/laser_out
(needs numpy), then encode:
  ffmpeg -i in.wav -codec:a libmp3lame -b:a 128k -ar 44100 out.mp3
  ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg
"""
import numpy as np
import wave, sys, os

SR = 44100
DUR = 0.65
N = int(SR * DUR)

def exp_sweep(f0, f1, dur, rng, vib_rate=28.0, vib_cents=12.0):
    """Exponential downward/upward sweep with gentle vibrato. Returns array."""
    ln = int(dur * SR)
    nn = np.arange(ln)
    t = nn / SR
    k = np.log(f1 / f0)
    # exponential frequency trajectory with gentle vibrato (small FM)
    inst = f0 * np.exp(k * t / dur)
    phase = 2 * np.pi * np.cumsum(inst * (1 + (vib_cents / 1200.0) * np.sin(2 * np.pi * vib_rate * t))) / SR
    return np.sin(phase), inst

def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(7)
    y = np.zeros(N)

    # --- charge blip: 60 ms upward flick, low gain, at t=0 ---
    bl, _ = exp_sweep(900.0, 2100.0, 0.060, rng, vib_rate=40.0, vib_cents=8.0)
    y[:len(bl)] += bl * 0.10

    # --- main laser sweep: 2100 -> 210 Hz over 0.38 s, starts at t=0.05 ---
    start = int(0.050 * SR)
    sweep, inst = exp_sweep(2100.0, 210.0, 0.380, rng)
    ln = len(sweep)
    nn = np.arange(ln)
    t = nn / SR
    # exponential decay envelope (tau 0.16 s) + 6 ms attack
    env = np.exp(-t / 0.16)
    atk = int(0.006 * SR)
    env[:atk] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(atk) / atk)
    voice = sweep * env
    # zap texture: 2nd/3rd harmonics, faster decay
    h2 = np.sin(2 * np.pi * np.cumsum(2 * inst) / SR) * np.exp(-t / 0.09) * 0.28
    h3 = np.sin(2 * np.pi * np.cumsum(3 * inst) / SR) * np.exp(-t / 0.06) * 0.14
    voice = voice + h2 + h3
    # bite: soft-clipped 5th partial only in first 80 ms
    bite_n = int(0.080 * SR)
    fifth = np.sin(2 * np.pi * np.cumsum(5 * inst[:bite_n]) / SR)
    fifth = np.tanh(fifth * 2.0) * 0.5
    bite_env = np.exp(-np.arange(bite_n) / SR / 0.030)
    bite_env[:atk] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(atk) / atk)
    voice[:bite_n] += fifth * bite_env * 0.35
    y[start:start + ln] += voice * 0.85

    # --- 80 ms raised-cosine end-fade: no pop at the tail ---
    ef = int(0.080 * SR)
    y[-ef:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(ef) / ef)

    # --- master: peak-normalize to 0.50 (-6.0 dBFS) ---
    peak = np.max(np.abs(y))
    if peak > 0:
        y *= 0.50 / peak
    rms = float(np.sqrt(np.mean(y ** 2)))
    print(f"peak={np.max(np.abs(y)):.3f} rms={rms:.3f} dur={DUR}s")

    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    path = os.path.join(outdir, "notify.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", path)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/laser_out")
