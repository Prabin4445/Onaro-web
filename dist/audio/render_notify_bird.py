#!/usr/bin/env python3
"""Onaro bird-whistle notification chime — 100% original synthesis (2026-09-29).

PraBin's brief, round 3: remove sound effects from everything except the
ringtone and the notification; the notification should be a sweet bird
whistle. Original composition, nothing sampled/copied.

Composition (original):
  - 1.5 s, mono, 44100 Hz / 16-bit.
  - Voice: pure sine (real bird whistles are near-sinusoidal) with a fast
    warble vibrato (7-9 Hz, +/-90 cents) — that flutter is what reads as
    "bird", not a synth beep.
  - Phrase 1 (t=0.00-0.50): three quick ascending chirps, 2600 -> 3300 Hz
    glides, 0.09 s each, 0.07 s apart — like a songbird's opening call.
  - Phrase 2 (t=0.62-1.30): one long sweet descending warble, 3300 -> 2300
    Hz over 0.55 s with deeper vibrato — the gentle landing.
  - Every chirp: 8 ms raised-cosine attack (no click), natural decay;
    100 ms raised-cosine end-fade on the whole piece (no pop).
  - Mastered sweet, not startling: peak-normalized to 0.50 (-6.0 dBFS).

Regenerate: python3 audio/render_notify_bird.py /tmp/bird_out
(needs numpy), then encode:
  ffmpeg -i in.wav -codec:a libmp3lame -b:a 128k -ar 44100 out.mp3
  ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg
"""
import numpy as np
import wave, sys, os

SR = 44100
DUR = 1.5
N = int(SR * DUR)

def chirp(f0, f1, dur, vib_rate, vib_cents, rng):
    """Sine glide with warble vibrato. Returns array."""
    ln = int(dur * SR)
    t = np.arange(ln) / SR
    k = np.log(f1 / f0)
    inst = f0 * np.exp(k * t / dur)
    phase = 2 * np.pi * np.cumsum(
        inst * (1 + (vib_cents / 1200.0) * np.sin(2 * np.pi * vib_rate * t))) / SR
    y = np.sin(phase)
    # gentle per-chirp envelope: quick attack, soft decay
    a = int(0.008 * SR)
    y[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    y *= np.exp(-t / (dur * 1.4)) * 0.9 + 0.1
    return y

def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(21)
    y = np.zeros(N)

    # --- phrase 1: three ascending chirps ---
    for i, (f0, f1) in enumerate([(2600, 3050), (2750, 3200), (2900, 3350)]):
        c = chirp(f0, f1, 0.090, 8.5, 90.0, rng)
        s = int((i * 0.160) * SR)
        y[s:s + len(c)] += c * 0.55

    # --- phrase 2: long sweet descending warble ---
    w = chirp(3300, 2300, 0.55, 7.0, 120.0, rng)
    s = int(0.62 * SR)
    y[s:s + len(w)] += w * 0.50

    # --- 100 ms end-fade ---
    ef = int(0.100 * SR)
    y[-ef:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(ef) / ef)

    # --- master: peak 0.50 ---
    peak = np.max(np.abs(y))
    if peak > 0:
        y *= 0.50 / peak
    print(f"peak={np.max(np.abs(y)):.3f} rms={float(np.sqrt(np.mean(y**2))):.3f} dur={DUR}s")

    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    path = os.path.join(outdir, "notify.wav")
    with wave.open(path, "wb") as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(SR)
        wv.writeframes(pcm.tobytes())
    print("wrote", path)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/bird_out")
