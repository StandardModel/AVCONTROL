#!/usr/bin/env python3
"""Generate miniDSP Flex 96 kHz biquad voicing files.

The miniDSP Flex Device Console expects advanced PEQ biquad files at 96 kHz.
These profiles approximate a warm tube preamp tonal balance using linear EQ.
They do not add nonlinear tube harmonic distortion.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


FS = 96_000.0
OUT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class FilterSpec:
    kind: str
    freq_hz: float | None = None
    gain_db: float = 0.0
    q: float = 0.707
    note: str = ""


PROFILES: dict[str, list[FilterSpec]] = {
    "Warm_Tube_Subtle": [
        FilterSpec("gain", gain_db=-2.0, note="Safety pad / level match"),
        FilterSpec("low_shelf", 110, +0.8, 0.70, "Gentle bass warmth"),
        FilterSpec("peak", 240, +0.4, 0.80, "Lower-mid body"),
        FilterSpec("peak", 3000, -0.45, 0.85, "Softer presence"),
        FilterSpec("high_shelf", 7800, -0.85, 0.70, "Smoother top octave"),
        FilterSpec("peak", 12000, -0.25, 0.80, "Slight air restraint"),
    ],
    "Warm_Tube_Reference": [
        FilterSpec("gain", gain_db=-3.0, note="Safety pad / level match"),
        FilterSpec("low_shelf", 105, +1.3, 0.70, "Classic warm foundation"),
        FilterSpec("peak", 220, +0.7, 0.85, "Chest and instrument body"),
        FilterSpec("peak", 650, +0.3, 0.65, "Gentle harmonic density cue"),
        FilterSpec("peak", 2600, -0.8, 0.90, "Less forward upper mids"),
        FilterSpec("high_shelf", 6800, -1.4, 0.65, "Tube-like treble sweetness"),
        FilterSpec("peak", 11000, -0.4, 0.80, "Tame glare/edge"),
    ],
    "Warm_Tube_Rich": [
        FilterSpec("gain", gain_db=-4.0, note="Safety pad / level match"),
        FilterSpec("low_shelf", 115, +1.9, 0.70, "Richer bass warmth"),
        FilterSpec("peak", 260, +1.0, 0.85, "Fuller lower mids"),
        FilterSpec("peak", 520, +0.6, 0.75, "Added wood/body"),
        FilterSpec("peak", 1900, -0.4, 0.80, "Relaxed mid presence"),
        FilterSpec("peak", 3000, -1.1, 0.85, "Softer vocal bite"),
        FilterSpec("high_shelf", 6200, -2.0, 0.65, "Vintage-style top-end ease"),
        FilterSpec("peak", 10000, -0.6, 0.80, "Extra polish on bright recordings"),
    ],
}


def db_to_amp(db: float) -> float:
    return 10 ** (db / 20.0)


def normalize(b: list[float], a: list[float]) -> tuple[np.ndarray, np.ndarray]:
    a0 = a[0]
    return np.array([v / a0 for v in b], dtype=float), np.array([v / a0 for v in a], dtype=float)


def biquad_standard(spec: FilterSpec) -> tuple[np.ndarray, np.ndarray]:
    if spec.kind == "identity":
        return np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])
    if spec.kind == "gain":
        return np.array([db_to_amp(spec.gain_db), 0.0, 0.0]), np.array([1.0, 0.0, 0.0])

    if spec.freq_hz is None:
        raise ValueError(f"{spec.kind} requires freq_hz")

    w0 = 2.0 * math.pi * spec.freq_hz / FS
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    a_gain = 10 ** (spec.gain_db / 40.0)
    alpha = sin_w0 / (2.0 * spec.q)

    if spec.kind == "peak":
        b = [
            1.0 + alpha * a_gain,
            -2.0 * cos_w0,
            1.0 - alpha * a_gain,
        ]
        a = [
            1.0 + alpha / a_gain,
            -2.0 * cos_w0,
            1.0 - alpha / a_gain,
        ]
        return normalize(b, a)

    two_sqrt_a_alpha = 2.0 * math.sqrt(a_gain) * alpha
    if spec.kind == "low_shelf":
        b = [
            a_gain * ((a_gain + 1) - (a_gain - 1) * cos_w0 + two_sqrt_a_alpha),
            2 * a_gain * ((a_gain - 1) - (a_gain + 1) * cos_w0),
            a_gain * ((a_gain + 1) - (a_gain - 1) * cos_w0 - two_sqrt_a_alpha),
        ]
        a = [
            (a_gain + 1) + (a_gain - 1) * cos_w0 + two_sqrt_a_alpha,
            -2 * ((a_gain - 1) + (a_gain + 1) * cos_w0),
            (a_gain + 1) + (a_gain - 1) * cos_w0 - two_sqrt_a_alpha,
        ]
        return normalize(b, a)

    if spec.kind == "high_shelf":
        b = [
            a_gain * ((a_gain + 1) + (a_gain - 1) * cos_w0 + two_sqrt_a_alpha),
            -2 * a_gain * ((a_gain - 1) + (a_gain + 1) * cos_w0),
            a_gain * ((a_gain + 1) + (a_gain - 1) * cos_w0 - two_sqrt_a_alpha),
        ]
        a = [
            (a_gain + 1) - (a_gain - 1) * cos_w0 + two_sqrt_a_alpha,
            2 * ((a_gain - 1) - (a_gain + 1) * cos_w0),
            (a_gain + 1) - (a_gain - 1) * cos_w0 - two_sqrt_a_alpha,
        ]
        return normalize(b, a)

    raise ValueError(f"Unknown filter kind: {spec.kind}")


def minidsp_coefficients(spec: FilterSpec) -> tuple[float, float, float, float, float]:
    b, a = biquad_standard(spec)
    return (b[0], b[1], b[2], -a[1], -a[2])


def padded_specs(specs: list[FilterSpec]) -> list[FilterSpec]:
    padded = specs[:]
    while len(padded) < 10:
        padded.append(FilterSpec("identity", note="Unused slot reset to flat"))
    return padded[:10]


def response_db(specs: list[FilterSpec], freqs: np.ndarray, include_gain: bool = True) -> np.ndarray:
    z = np.exp(-1j * 2.0 * np.pi * freqs / FS)
    h = np.ones_like(z, dtype=np.complex128)
    for spec in specs:
        if not include_gain and spec.kind == "gain":
            continue
        b, a = biquad_standard(spec)
        h *= (b[0] + b[1] * z + b[2] * z**2) / (a[0] + a[1] * z + a[2] * z**2)
    return 20.0 * np.log10(np.maximum(np.abs(h), 1e-12))


def write_biquad_file(name: str, specs: list[FilterSpec]) -> None:
    lines: list[str] = []
    for idx, spec in enumerate(padded_specs(specs), start=1):
        b0, b1, b2, a1, a2 = minidsp_coefficients(spec)
        lines.extend(
            [
                f"biquad{idx},",
                f"b0={b0:.15g},",
                f"b1={b1:.15g},",
                f"b2={b2:.15g},",
                f"a1={a1:.15g},",
                f"a2={a2:.15g},",
            ]
        )
    lines[-1] = lines[-1].rstrip(",")
    (OUT_DIR / f"{name}_96k_biquads.txt").write_text("\n".join(lines) + "\n")


def write_settings_csv() -> None:
    with (OUT_DIR / "warm_tube_basic_settings.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["profile", "slot", "kind", "freq_hz", "gain_db", "q", "note"])
        for name, specs in PROFILES.items():
            for idx, spec in enumerate(padded_specs(specs), start=1):
                writer.writerow(
                    [
                        name,
                        idx,
                        spec.kind,
                        "" if spec.freq_hz is None else spec.freq_hz,
                        spec.gain_db,
                        "" if spec.kind in {"gain", "identity"} else spec.q,
                        spec.note,
                    ]
                )


def write_response_csv(freqs: np.ndarray) -> None:
    with (OUT_DIR / "warm_tube_frequency_response.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        header = ["frequency_hz"]
        for name in PROFILES:
            header.extend([f"{name}_actual_db", f"{name}_tone_only_db"])
        writer.writerow(header)
        for index, freq in enumerate(freqs):
            row: list[float] = [float(freq)]
            for specs in PROFILES.values():
                row.append(float(response_db(specs, freqs, include_gain=True)[index]))
                row.append(float(response_db(specs, freqs, include_gain=False)[index]))
            writer.writerow(row)


def write_plot(freqs: np.ndarray) -> None:
    plt.figure(figsize=(10, 5.6), dpi=160)
    for name, specs in PROFILES.items():
        plt.semilogx(freqs, response_db(specs, freqs, include_gain=False), label=name.replace("_", " "))
    plt.axhline(0, color="#555555", linewidth=0.8)
    plt.xlim(20, 20_000)
    plt.ylim(-3.0, 3.0)
    plt.grid(True, which="both", alpha=0.25)
    plt.title("miniDSP Flex Warm Tube Voicing Curves (tone only, pad excluded)")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Gain (dB)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "warm_tube_voicing_curves.png")
    plt.close()


def main() -> None:
    freqs = np.geomspace(20.0, 20_000.0, 400)
    for name, specs in PROFILES.items():
        write_biquad_file(name, specs)
    write_settings_csv()
    write_response_csv(freqs)
    write_plot(freqs)


if __name__ == "__main__":
    main()
