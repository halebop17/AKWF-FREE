#!/usr/bin/env python3
"""
generate_chip_waves.py — Phase 1A
Halebop SCWBrowser / AKWF-FREE repo

Generates hardware-modelled single-cycle waveforms for classic sound chips
and copies Adventure Kid's authoritative NES originals.

Output : AKWF/Halebop_chip/
Format : 600 samples, 16-bit signed, 44100 Hz, mono WAV

Generated waveforms are CC0 / public domain.
NES waveforms by Adventure Kid (adventurekid.se), CC0.

Chips covered
─────────────
  NES 2A03          — pulse 12.5 / 25 / 50 %, triangle (4-bit quantised), noise
                      (copied directly from AKWF originals, not re-generated)
  Game Boy DMG      — pulse 12.5 / 25 / 50 / 75 %;
                      Wave-RAM sawtooth and triangle (32-step 4-bit)
  C64 SID 6581/8580 — sawtooth, triangle, pulse 25 % and 50 %

Not included as separate waveforms
───────────────────────────────────
  SN76489 (Sega MS/GG) and AY-3-8910 (ZX Spectrum / MSX) both output only
  a 50 % square wave — identical in shape to gb_pulse_50 and sid_pulse_50.
  Including them would add duplicate content with different labels.
  LFSR-based noise channels (SID, SN76489, AY) are non-repeating and therefore
  not representable as a single cycle.
"""

import os
import shutil
import struct
import wave

# ── Constants ─────────────────────────────────────────────────────────────────

N    = 600    # samples per cycle  (AKWF standard)
RATE = 44100  # Hz
PEAK = 32767  # 16-bit signed peak amplitude

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(SCRIPT_DIR)
OUT_DIR    = os.path.join(REPO_ROOT, "AKWF", "Halebop_chip")
NES_SRC    = os.path.join(REPO_ROOT, "Files", "nes-single-cycle")


# ── WAV writer ────────────────────────────────────────────────────────────────

def write_wav(filename, samples):
    """Write a list of floats in [-1.0, 1.0] as a 16-bit mono WAV."""
    path = os.path.join(OUT_DIR, filename)
    ints = [max(-PEAK, min(PEAK, int(round(s * PEAK)))) for s in samples]
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(struct.pack(f"<{N}h", *ints))
    print(f"  wrote   {filename}")


# ── Waveform generators ───────────────────────────────────────────────────────

def gen_pulse(duty):
    """
    Pulse / square wave.
    duty  : fraction of the cycle that is +1  (e.g. 0.25 = 25 %)
    """
    cut = int(N * duty)
    return [1.0 if i < cut else -1.0 for i in range(N)]


def gen_gb_4bit(values_32):
    """
    Game Boy Wave channel.
    values_32 : exactly 32 integers in 0–15 (one full Wave-RAM cycle)
    Normalised so that 0 → -1.0 and 15 → +1.0, then stretched to N samples
    using nearest-neighbour indexing (preserving the stepped character).
    """
    assert len(values_32) == 32, "Wave RAM requires exactly 32 nibble values"
    norm = [(v - 7.5) / 7.5 for v in values_32]
    return [norm[min(int(i / N * 32), 31)] for i in range(N)]


def gen_sid_sawtooth():
    """
    C64 SID sawtooth.
    The SID phase accumulator is a linear ramp; the sawtooth output is
    the top bits with no additional shaping — perfectly linear.
    (The analogue filter gives the SID its character, not the wave shape.)
    """
    return [(i / (N - 1)) * 2.0 - 1.0 for i in range(N)]


def gen_sid_triangle():
    """
    C64 SID triangle.
    Internal XOR on the accumulator MSB folds the rising ramp into a triangle.
    Result: clean linear triangle — no quantisation (unlike NES).
    Rises from -1 at t=0 to +1 at t=0.5, then falls back to -1 at t=1.
    """
    out = []
    for i in range(N):
        t = i / N
        out.append(t * 4.0 - 1.0 if t < 0.5 else 3.0 - t * 4.0)
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Output → {OUT_DIR}\n")

    # ── NES 2A03 ──────────────────────────────────────────────────────────────
    # Adventure Kid's own NES single-cycle set (CC0).
    # Copied and given shorter filenames for consistency with this bank.
    print("NES 2A03  (copying from AKWF originals):")
    nes_map = {
        "AKWF_nes_pulse_12_5.wav": "nes_pulse_12_5.wav",
        "AKWF_nes_pulse_25.wav":   "nes_pulse_25.wav",
        "AKWF_nes_square.wav":     "nes_square.wav",
        "AKWF_nes_triangle.wav":   "nes_triangle.wav",
        "AKSA_nes_noise.wav":      "nes_noise.wav",
    }
    for src_name, dst_name in nes_map.items():
        src = os.path.join(NES_SRC, src_name)
        dst = os.path.join(OUT_DIR, dst_name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  copied  {dst_name}")
        else:
            print(f"  MISSING {src_name}  — skipped")

    # ── Game Boy DMG ──────────────────────────────────────────────────────────
    # Pulse channel: 4 fixed duty cycles (12.5 / 25 / 50 / 75 %).
    # Wave channel: 32 x 4-bit Wave RAM — distinctive stepped timbre.
    print("\nGame Boy DMG  (generated):")
    write_wav("gb_pulse_12_5.wav",    gen_pulse(0.125))
    write_wav("gb_pulse_25.wav",      gen_pulse(0.25))
    write_wav("gb_pulse_50.wav",      gen_pulse(0.50))
    write_wav("gb_pulse_75.wav",      gen_pulse(0.75))

    # Wave-RAM sawtooth: 32 evenly-spaced ascending 4-bit steps (0…15)
    gb_saw = [i // 2 for i in range(32)]        # [0,0,1,1,2,2,...,15,15]
    write_wav("gb_wave_saw.wav",      gen_gb_4bit(gb_saw))

    # Wave-RAM triangle: ascend 0→15, descend 15→0  (32 steps total)
    gb_tri = list(range(0, 16)) + list(range(15, -1, -1))
    write_wav("gb_wave_triangle.wav", gen_gb_4bit(gb_tri))

    # ── C64 SID 6581 / 8580 ───────────────────────────────────────────────────
    # Three oscillator waveforms: sawtooth, triangle, pulse.
    # SID noise is a 23-bit LFSR — non-repeating, excluded.
    print("\nC64 SID  (generated):")
    write_wav("sid_sawtooth.wav",  gen_sid_sawtooth())
    write_wav("sid_triangle.wav",  gen_sid_triangle())
    write_wav("sid_pulse_25.wav",  gen_pulse(0.25))
    write_wav("sid_pulse_50.wav",  gen_pulse(0.50))

    # ── Summary ───────────────────────────────────────────────────────────────
    n_wav = len([f for f in os.listdir(OUT_DIR) if f.lower().endswith(".wav")])
    print(f"\nDone — {n_wav} WAV files written to AKWF/Halebop_chip/")


if __name__ == "__main__":
    main()
