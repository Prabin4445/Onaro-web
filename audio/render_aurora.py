#!/usr/bin/env python3
"""Onaro Aurora ringtones — 100% original synthesis (2026-09-23, ring remix).

PraBin's brief: modern 2026 feel, SOFT, with bass — and now unmistakably
RINGTONE type: "make it feel like calls coming" / "with that base and some
tone on it". Two variants:
  - ringtone-aurora : "Aurora Soft"  (default call ringtone, fresh installs)
  - ringtone-breeze : "Aurora Breeze" (slightly brighter alt)

Composition (original, nothing sampled/copied):
  - 16.0 s seamless loop, 4 bars x 4 s: Fmaj7 -> Am7 -> Dm9 -> Bbmaj9
  - Sub-bass bed (the FOUNDATION): root sine (F1/A1/D2/Bb1) + faint 2nd
    harmonic, 0.5 Hz breathing swell, mono. Carries the whole tone.
  - Warm melodic lead (the TONE on the base): a soft rounded bell/piano
    voice playing the classic incoming-call cadence — one "ring" per bar:
    two warm strikes (fifth -> third of the bar chord), then a breathing
    pause. Instantly reads as a call, stays soft and modern.
  - Gentle rhythmic pulse: soft low "tock" on the beat during each ring
    phrase only (gives ringtone drive without filling the pauses).
  - Warm airy pads behind (detuned sine-partial stacks, slow attack,
    equal-gain crossfades at bar lines; bar 4's tail wraps onto bar 1 so
    the loop point is bit-continuous), sparse airy shimmer on top.
  - Mastered soft: peak normalized to 0.87 (-1.2 dBFS, so lossy encodes
    stay under -1 dBFS), RMS ~0.10-0.13. Never clipped.

Stereo: lead/pads/shimmer get gentle width (per-channel detune), bass
stays mono. Output: 44.1 kHz 16-bit stereo WAV -> caller encodes mp3/ogg.
"""
import numpy as np
import wave, struct, sys, os

SR = 44100
DUR = 16.0
N = int(SR * DUR)

def midi(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)

# bars: (name, pad midi notes, bass midi root)
BARS = [
    ("Fmaj7",  [53, 57, 60, 64], 29),   # F3 A3 C4 E4 / F1
    ("Am7",    [57, 60, 64, 67], 33),   # A3 C4 E4 G4 / A1
    ("Dm9",    [50, 53, 57, 60, 64], 38),# D3 F3 A3 C4 E4 / D2
    ("Bbmaj9", [46, 50, 53, 57, 60], 34),# Bb2 D3 F3 A3 C4 / Bb1
]
BAR = 4.0
XF = 1.5  # pad crossfade seconds at each bar line

# One "ring" per bar: (strike1_midi, strike2_midi) = fifth -> third of chord
RING_NOTES = [
    (72, 81),  # Fmaj7: C5 -> A5
    (76, 79),  # Am7:   E5 -> G5
    (81, 77),  # Dm9:   A5 -> F5
    (77, 74),  # Bbmaj9:F5 -> D5
]
RING_AT = [0.0, 4.0, 8.0, 12.0]   # ring starts (one per bar)
STRIKE2_OFF = 0.75                 # second strike offset (classic double-ring)
STRIKE1_OFF = 0.10

# sparse shimmer notes: (time_s, midi, gain)
SHIMMER = [(4.0, 84, 0.05), (9.5, 81, 0.055), (13.0, 77, 0.05)]

def raised_cosine_up(n):
    x = np.linspace(0, 1, n, endpoint=False)
    return 0.5 - 0.5 * np.cos(np.pi * x)

def bell(f, dur, rng, bright, vel):
    """Soft warm bell/piano-like voice: rounded partials, gentle attack,
    per-partial decay (highs die faster). Returns (ln, 2) stereo tone."""
    ln = int(dur * SR)
    nn = np.arange(ln)
    if bright:
        parts = [(1.0, 1.0, 1.0), (0.42, 2.0, 0.62), (0.20, 3.0, 0.42),
                 (0.10, 4.02, 0.30), (0.05, 5.03, 0.22)]
    else:
        parts = [(1.0, 1.0, 0.9), (0.32, 2.0, 0.55), (0.14, 3.0, 0.36),
                 (0.06, 4.02, 0.24)]
    tone = np.zeros((ln, 2))
    for ch in range(2):
        det = 1.0 + (rng.uniform(-3, 3) / 1200.0)
        ph = rng.uniform(0, 2 * np.pi)
        for (a, mu, tau) in parts:
            tone[:, ch] += a * np.exp(-nn / (SR * tau)) * np.sin(
                2 * np.pi * f * mu * det * nn / SR + ph)
    atk = int(0.008 * SR)
    tone[:atk] *= np.linspace(0, 1, atk)[:, None]
    tone *= 0.36 * vel
    # warm octave-down layer tying the tone to the bass bed ("tone on the base")
    sub = np.zeros((ln, 2))
    nn2 = np.arange(ln)
    for ch in range(2):
        det = 1.0 + (rng.uniform(-3, 3) / 1200.0)
        ph = rng.uniform(0, 2 * np.pi)
        sub[:, ch] = (np.exp(-nn2 / (SR * 1.1)) * np.sin(2 * np.pi * f / 2 * det * nn2 / SR + ph)
                      + 0.3 * np.exp(-nn2 / (SR * 0.7)) * np.sin(2 * np.pi * f * det * nn2 / SR + ph))
    sub[:atk] *= np.linspace(0, 1, atk)[:, None]
    tone += sub * 0.055 * vel
    # 50 ms end-fade: no step even if the note runs past the loop point
    fn = min(ln, int(0.05 * SR))
    tone[-fn:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(fn) / fn))[:, None]
    return tone

def tock(rng):
    """Soft low rhythmic 'tock' for ringtone drive during ring phrases."""
    ln = int(0.12 * SR)
    nn = np.arange(ln)
    env = np.exp(-nn / (SR * 0.028))
    s = (np.sin(2 * np.pi * 160 * nn / SR)
         + 0.4 * np.sin(2 * np.pi * 320 * nn / SR + 0.7)) * env * 0.045
    s = np.stack([s, s], axis=1)
    ph = rng.uniform(0, 2 * np.pi)
    # faint stereo wobble so it doesn't sit dead-center
    s[:, 0] *= 0.9 + 0.1 * np.cos(ph)
    s[:, 1] *= 0.9 + 0.1 * np.sin(ph)
    return s

def render(bright=False):
    out = np.zeros((N, 2))
    rng = np.random.default_rng(20260923)

    # ---------- pads (equal-gain crossfade at bar lines, wraps seamlessly)
    # Each bar renders [k*4s, k*4s+5.5s): full sustain 4 s + 1.5 s release tail
    # that overlaps the next bar's 1.5 s attack head; release+attack sum to 1.
    # Bar 3's tail (past 16 s) wraps onto [0, 1.5 s) -> loop point is seamless.
    pad_amps = np.array([1.0, 0.35, 0.18, 0.10, 0.05]) if not bright \
        else np.array([1.0, 0.45, 0.28, 0.16, 0.10])
    pad_mults = np.array([1.0, 2.0, 3.0, 4.01, 6.02])
    xa = int(XF * SR)
    atk = raised_cosine_up(xa)          # 0 -> 1
    rel = 0.5 + 0.5 * np.cos(np.pi * np.arange(xa) / xa)  # 1 -> 0 ; atk+rel == 1
    for k in range(4):
        _, notes, _ = BARS[k]
        seg_start = int(k * BAR * SR)
        seg_len = int((BAR + XF) * SR)
        seg_n = np.arange(seg_len)
        sig = np.zeros((seg_len, 2))
        for m in notes:
            f = midi(m)
            for ch in range(2):
                det = 1.0 + (rng.uniform(-4, 4) / 1200.0)  # +/-4 cents width
                ph = rng.uniform(0, 2 * np.pi)
                for a, mu in zip(pad_amps, pad_mults):
                    sig[:, ch] += a * np.sin(2 * np.pi * f * mu * det * seg_n / SR + ph)
        sig *= 0.024  # bed sits under the lead tone
        sig[:xa] *= atk[:, None]        # attack head (overlaps prev bar's tail)
        sig[-xa:] *= rel[:, None]       # release tail (overlaps next bar's head)
        # write, wrapping bar 3's overhang onto the loop head
        for i in range(seg_len):
            out[(seg_start + i) % N] += sig[i]

    # ---------- sub-bass bed (mono, the foundation)
    for k in range(4):
        _, _, root = BARS[k]
        f = midi(root)
        seg_len = int(BAR * SR)
        st = int(k * BAR * SR)
        nn = np.arange(seg_len)
        rate = 0.5 if not bright else 0.75
        swell = 0.72 + 0.28 * np.sin(2 * np.pi * rate * nn / SR - np.pi / 2)
        env = np.ones(seg_len)
        ae, re_ = int(0.3 * SR), int(0.4 * SR)
        env[:ae] = raised_cosine_up(ae)
        env[-re_:] = (0.5 + 0.5 * np.cos(np.pi * np.arange(re_) / re_))
        sig = (np.sin(2 * np.pi * f * nn / SR)
               + 0.15 * np.sin(2 * np.pi * 2 * f * nn / SR))
        sig = sig * swell * env * (0.18 if not bright else 0.21)
        out[st:st + seg_len, 0] += sig
        out[st:st + seg_len, 1] += sig

    # ---------- lead ring phrases: "ring... ring..." cadence
    # Two warm strikes per bar (fifth -> third), then a breathing pause.
    for k in range(4):
        t0 = RING_AT[k]
        n1, n2 = RING_NOTES[k]
        for (off, m, vel) in [(STRIKE1_OFF, n1, 0.85), (STRIKE2_OFF, n2, 0.70)]:
            ts = t0 + off
            f = midi(m)
            dur = 2.4  # decays well before the pause ends
            tone = bell(f, dur, rng, bright, vel)
            st = int(ts * SR)
            ln = tone.shape[0]
            if st + ln > N:
                ln = N - st
                tone = tone[:ln]
            out[st:st + ln] += tone
        # gentle rhythmic pulse under the phrase only (drive, not filler)
        for beat in [0.0, 0.5, 1.0, 1.5]:
            tk = tock(rng)
            st = int((t0 + STRIKE1_OFF + beat) * SR)
            ln = tk.shape[0]
            if st + ln > N:
                continue
            out[st:st + ln] += tk

    # ---------- shimmer
    sh_gain = 1.0 if not bright else 2.2
    for (ts, m, g) in SHIMMER:
        f = midi(m)
        dur = 3.0
        ln = int(dur * SR)
        st = int(ts * SR)
        nn = np.arange(ln)
        env = np.exp(-nn / (SR * 1.8))
        env[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
        s = (np.sin(2 * np.pi * f * nn / SR)
             + 0.3 * np.sin(2 * np.pi * 2 * f * nn / SR + 1.0)) * env * g * sh_gain
        fn = min(ln, int(0.05 * SR))
        s[-fn:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(fn) / fn)
        out[st:st + ln, 0] += s * 0.8
        out[st:st + ln, 1] += s * 1.0

    return out

def write_wav(path, sig):
    # No global crossfade: pads/bass are continuous by design (bar crossfades
    # wrap around the loop point) and every bell/tock/shimmer note gets its own
    # 50 ms end-fade, so there are no steps at the junction at all.
    # (A global tail crossfade was tried and REMOVED: for high-frequency
    # partials it creates a larger junction step than it fixes.)
    peak = np.max(np.abs(sig))
    print(f"pre-master peak: {peak:.4f}, rms: {np.sqrt(np.mean(sig**2)):.4f}")
    sig = sig / peak * 0.87  # -1.2 dBFS headroom (lossy encodes overshoot slightly)
    pcm = (np.clip(sig, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    # verify loop continuity: last vs first sample should be close
    print(f"loop discontinuity L/R: {abs(sig[0,0]-sig[-1,0]):.5f} / {abs(sig[0,1]-sig[-1,1]):.5f}")
    print(f"wrote {path}: {len(sig)/SR:.2f}s, peak {np.max(np.abs(sig)):.4f} "
          f"({20*np.log10(np.max(np.abs(sig))):.2f} dBFS)")

if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
    os.makedirs(dest, exist_ok=True)
    write_wav(os.path.join(dest, "ringtone-aurora.wav"), render(bright=False))
    write_wav(os.path.join(dest, "ringtone-breeze.wav"), render(bright=True))
