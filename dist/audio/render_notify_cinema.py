#!/usr/bin/env python3
"""Onaro cinematic notification chime — 100% original synthesis (2026-09-29).

PraBin's brief, round 2: the laser "pew" sounded like kids. He wants MOVIE
sounds — with bass on it, heavy, adult type, with some space feelings.
Think sci-fi trailer: sub-bass foundation, a deep braam hit, airy space
sweep on top. Original composition, nothing sampled/copied.

Composition (original):
  - 1.4 s, mono, 44100 Hz / 16-bit.
  - Sub-bass bed (the FOUNDATION): 49 Hz (G1) + 98 Hz sines, 0.25 s swell
    attack, release from 0.9 s — felt in the chest, not just heard.
  - Braam hit (the WEIGHT): A1+E2+A2+C3 minor stack at t=0.02, each note a
    low brass-ish voice (odd-harmonic stack 1/0.3/0.12, +/-4 cents detune),
    80 ms attack, ~0.7 s decay — heavy and adult, never harsh.
  - Punch transient: 130 -> 48 Hz sine drop over 0.12 s at the hit — the
    trailer "thump" that makes phone speakers push air.
  - Space sweep (the SPACE): 2800 -> 700 Hz airy sine sweep over 0.9 s at
    low gain, 0.2 s attack — sci-fi atmosphere.
  - Shimmer: sparse high sines (G6, C7), slow 0.4 s attack, low gain —
    distant stars, not sparkle-toy.
  - 150 ms raised-cosine end-fade: no pop. Everything rests by 1.4 s.
  - Mastered heavy but safe: peak-normalized to 0.60 (-4.4 dBFS).
    Strong 2nd/3rd harmonics throughout so the weight survives small
    phone speakers that can't move 49 Hz.

Regenerate: python3 audio/render_notify_cinema.py /tmp/cinema_out
(needs numpy), then encode:
  ffmpeg -i in.wav -codec:a libmp3lame -b:a 128k -ar 44100 out.mp3
  ffmpeg -i in.wav -codec:a libvorbis -q:a 4 -ar 44100 out.ogg
"""
import numpy as np
import wave, sys, os

SR = 44100
DUR = 1.4
N = int(SR * DUR)

def raised_cosine(n):
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)

def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(11)
    y = np.zeros(N)
    nn = np.arange(N)
    t = nn / SR

    # --- sub-bass bed: 49 Hz + 98 Hz, 0.25 s swell, release from 0.9 s ---
    atk = int(0.25 * SR)
    bed = np.sin(2 * np.pi * 49 * t) + 0.40 * np.sin(2 * np.pi * 98 * t + 0.7)
    env = np.ones(N)
    env[:atk] = raised_cosine(atk)
    rel0 = int(0.90 * SR)
    env[rel0:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(N - rel0) / (N - rel0))
    y += bed * env * 0.34

    # --- braam hit: A1 E2 A2 C3 minor stack at t=0.02 ---
    start = int(0.02 * SR)
    for f in (55.0, 82.41, 110.0, 130.81):
        det = 1.0 + rng.uniform(-4, 4) / 1200.0
        ln = N - start
        tn = np.arange(ln) / SR
        ph = 2 * np.pi * f * det * tn
        # low brass-ish voice: odd harmonics, slow attack, long decay
        tone = (np.sin(ph) + 0.30 * np.sin(3 * ph + 0.4)
                + 0.12 * np.sin(5 * ph + 1.1)) * np.exp(-tn / 0.70)
        a = int(0.080 * SR)
        tone[:a] *= raised_cosine(a)
        y[start:] += tone * 0.16

    # --- punch transient: 130 -> 48 Hz drop over 0.12 s ---
    pl = int(0.12 * SR)
    pt = np.arange(pl) / SR
    k = np.log(48.0 / 130.0)
    pphase = 2 * np.pi * np.cumsum(130.0 * np.exp(k * pt / 0.12)) / SR
    punch = np.sin(pphase) * np.exp(-pt / 0.05)
    y[start:start + pl] += punch * 0.42

    # --- space sweep: 2800 -> 700 Hz over 0.9 s from t=0.10, airy ---
    s0 = int(0.10 * SR)
    sl = int(0.90 * SR)
    st = np.arange(sl) / SR
    ks = np.log(700.0 / 2800.0)
    sph = 2 * np.pi * np.cumsum(2800.0 * np.exp(ks * st / 0.90)) / SR
    sweep = np.sin(sph) * np.exp(-st / 0.55)
    sa = int(0.20 * SR)
    sweep[:sa] *= raised_cosine(sa)
    y[s0:s0 + sl] += sweep * 0.055

    # --- shimmer: G6 + C7, slow attack, distant ---
    for f, g in ((1567.98, 0.045), (2093.0, 0.035)):
        det = 1.0 + rng.uniform(-5, 5) / 1200.0
        tone = np.sin(2 * np.pi * f * det * t + rng.uniform(0, 6.28)) * np.exp(-t / 0.50)
        a = int(0.40 * SR)
        tone[:a] *= raised_cosine(a)
        y += tone * g

    # --- 150 ms end-fade: no pop ---
    ef = int(0.150 * SR)
    y[-ef:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(ef) / ef)

    # --- master: peak 0.60 ---
    peak = np.max(np.abs(y))
    if peak > 0:
        y *= 0.60 / peak
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
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/cinema_out")
