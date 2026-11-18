"""Deterministic synthetic cards for tests and the example folder. Not real GPUs.

The hidden truth (adjustable): corrected ECC errors and low clocks make a card likely to fail; running hot
never does. With clock_effect=0, low clocks are harmless too, so the built-in points mis-rank cards.
"""

import math
import os
import random

HEADER = (
    "timestamp, name, serial, temperature.gpu, power.draw [W], power.limit [W], clocks.sm [MHz], "
    "clocks.max.sm [MHz], utilization.gpu [%], fan.speed [%], ecc.errors.corrected.volatile.total, "
    "ecc.errors.uncorrected.volatile.total, retired_pages.pending"
)


def capture(serial: str, temp: int, clock_ratio: float, ecc_c: int) -> str:
    rows = [HEADER]
    for s in range(10):
        rows.append(
            f"2026/10/24 10:00:{s:02d}.000, NVIDIA RTX A6000, {serial}, {temp}, 290.00 W, 300.00 W, "
            f"{round(2100 * clock_ratio)} MHz, 2100 MHz, 99 %, 70 %, {ecc_c}, 0, 0"
        )
    return "\n".join(rows) + "\n"


def make_cards(folder: str, n: int = 80, seed: int = 5, ecc_effect: float = 0.35, clock_effect: float = 0.25) -> str:
    """Write n captures and labels.csv into folder; return the labels path. Effects are per built-in point."""
    rng = random.Random(seed)
    lines = ["capture,failed"]
    for i in range(n):
        hot = rng.random() < 0.4
        temp = rng.randint(76, 82) if hot else rng.randint(60, 72)
        clock_ratio = rng.uniform(0.7, 0.88) if rng.random() < 0.3 else rng.uniform(0.92, 0.99)
        ecc_c = rng.choice([0, 0, 0, 20, 60, 120])
        clock_pts = max(0, (0.9 - clock_ratio) * 100)
        ecc_pts = min(15, 3 + ecc_c / 10) if ecc_c else 0
        p = 1 / (1 + math.exp(-(-3.0 + ecc_effect * ecc_pts + clock_effect * clock_pts)))
        failed = rng.random() < p
        name = f"card{i:03d}.csv"
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(capture(f"SN{i:05d}", temp, clock_ratio, ecc_c))
        lines.append(f"{name},{'yes' if failed else 'no'}")
    labels = os.path.join(folder, "labels.csv")
    with open(labels, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return labels
