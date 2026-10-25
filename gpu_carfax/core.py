"""Health grading for used GPUs from nvidia-smi stress captures."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass, field

__all__ = ["CAPTURE_CMD", "parse_capture", "grade", "Report"]

FIELDS = [
    "timestamp",
    "name",
    "serial",
    "temperature.gpu",
    "power.draw",
    "power.limit",
    "clocks.sm",
    "clocks.max.sm",
    "utilization.gpu",
    "fan.speed",
    "ecc.errors.corrected.volatile.total",
    "ecc.errors.uncorrected.volatile.total",
    "retired_pages.pending",
]
MIN_LOAD_SAMPLES = 5  # seconds at >=90% utilisation; a seller cannot get an "A" from an idle or empty capture
CAPTURE_CMD = f"nvidia-smi --query-gpu={','.join(FIELDS)} --format=csv -l 1 > capture.csv"


def _num(v: str):
    v = v.strip()
    if v in {"", "[N/A]", "N/A", "[Not Supported]"}:
        return None
    if v.lower() in {"yes", "no"}:
        return 1.0 if v.lower() == "yes" else 0.0
    m = re.search(r"-?\d+(\.\d+)?", v)
    return float(m.group()) if m else None


def parse_capture(text: str) -> list[dict]:
    reader = csv.reader(io.StringIO(text))
    first = next(reader, None)
    if not first:
        raise ValueError("empty capture")
    header = [re.sub(r"\s*\[.*?\]", "", h).strip() for h in first]
    missing = [f for f in FIELDS if f not in header]
    if missing:
        # a dropped column (e.g. ECC) would otherwise read as "no problems found"
        raise ValueError(f"capture is missing fields {missing}; run: {CAPTURE_CMD}")
    rows = []
    for r in reader:
        if not r:
            continue
        row = dict(zip(header, r))
        parsed = {k: (row[k].strip() if k in ("timestamp", "name", "serial") else _num(row[k])) for k in row}
        rows.append(parsed)
    return rows


@dataclass
class Report:
    report_id: str
    gpu: str
    serial: str
    samples: int
    score: int
    grade: str
    deductions: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    price_multiplier: float = 1.0
    fair_price: float | None = None


def _vals(rows, key):
    return [r[key] for r in rows if r.get(key) is not None]


def grade(
    text: str,
    hours: float | None = None,
    mining: bool = False,
    market_price: float | None = None,
    throttle_temp: float = 83.0,
    min_load_samples: int = MIN_LOAD_SAMPLES,
) -> Report:
    for name, v in (("hours", hours), ("market_price", market_price)):
        if v is not None and not (math.isfinite(v) and v >= 0):
            raise ValueError(f"{name} must be a finite number >= 0, got {v!r}")
    rows = parse_capture(text)
    serials = {r.get("serial") for r in rows}
    if len(serials) > 1:
        raise ValueError(f"capture covers {len(serials)} GPUs ({sorted(serials)}); grade one card per capture")
    load = [r for r in rows if (r.get("utilization.gpu") or 0) >= 90]
    if len(load) < min_load_samples:
        raise ValueError(
            f"only {len(load)} samples at >=90% load (need {min_load_samples}); run a stress test while capturing"
        )
    temps = _vals(load, "temperature.gpu")
    clocks = _vals(load, "clocks.sm")
    max_clock = max(_vals(rows, "clocks.max.sm") or [0])
    power = _vals(load, "power.draw")
    limit = max(_vals(rows, "power.limit") or [0])
    fans = _vals(load, "fan.speed")
    ecc_c = max(_vals(rows, "ecc.errors.corrected.volatile.total") or [0])
    ecc_u = max(_vals(rows, "ecc.errors.uncorrected.volatile.total") or [0])
    retired = max(_vals(rows, "retired_pages.pending") or [0])

    m = {
        "peak_temp": max(temps) if temps else None,
        "sustained_temp": sorted(temps)[len(temps) // 2] if temps else None,
        "clock_ratio": (sum(clocks) / len(clocks) / max_clock) if clocks and max_clock else None,
        "power_ratio": (max(power) / limit) if power and limit else None,
        "fan_peak": max(fans) if fans else None,
        "ecc_corrected": ecc_c,
        "ecc_uncorrected": ecc_u,
        "retired_pending": retired,
    }
    d = []
    if m["peak_temp"] is not None and m["peak_temp"] >= throttle_temp:
        d.append(("thermal throttling reached", min(25, 5 + 3 * (m["peak_temp"] - throttle_temp))))
    elif m["sustained_temp"] is not None and m["sustained_temp"] >= throttle_temp - 8:
        d.append(("runs hot under load", 6))
    if m["clock_ratio"] is not None and m["clock_ratio"] < 0.9:
        d.append((f"SM clock only {m['clock_ratio']:.0%} of max boost", round(min(25, (0.9 - m["clock_ratio"]) * 100))))
    if m["power_ratio"] is not None and m["power_ratio"] < 0.8:
        d.append((f"can't reach power limit ({m['power_ratio']:.0%})", 8))
    if m["fan_peak"] is not None and m["fan_peak"] >= 95 and (m["sustained_temp"] or 0) >= throttle_temp - 8:
        d.append(("fan maxed while still hot - cooler/paste/pads need service", 10))
    if ecc_u:
        d.append((f"{ecc_u:.0f} uncorrected ECC errors", 40))
    if ecc_c:
        d.append((f"{ecc_c:.0f} corrected ECC errors", min(15, 3 + ecc_c / 10)))
    if retired:
        d.append(("memory page retirement pending", 20))
    if hours is not None and hours > 8760:
        d.append((f"{hours:,.0f} power-on hours", min(15, round((hours - 8760) / 2000))))
    if mining:
        d.append(("declared mining history", 8))

    score = max(0, round(100 - sum(p for _, p in d)))
    g = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 65 else "D" if score >= 50 else "F"
    mult = {"A": 1.0, "B": 0.92, "C": 0.8, "D": 0.6, "F": 0.3}[g]
    first = rows[0] if rows else {}
    return Report(
        report_id=hashlib.sha256(text.encode()).hexdigest()[:16],
        gpu=first.get("name", "?"),
        serial=first.get("serial", "?"),
        samples=len(rows),
        score=score,
        grade=g,
        deductions=[(r, round(p, 1)) for r, p in d],
        metrics=m,
        price_multiplier=mult,
        fair_price=round(market_price * mult, 2) if market_price else None,
    )
