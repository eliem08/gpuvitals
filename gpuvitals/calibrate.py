"""Fit the grading to cards whose fate you know (returned, failed in burn-in, RMA'd) instead of built-in guesses.

Input: a CSV of graded cards, with columns
  capture   the nvidia-smi capture file (relative to --captures, or a full path)
  failed    yes/no: did the card fail or come back?
  hours     optional power-on hours
  mining    optional yes/no
Each card's warning signs and their built-in points are taken from `grade`. A logistic regression (L2,
Newton's method, deterministic) then learns how much one point of each sign raises the odds of failure.
Each sign's multiplier is its learned effect relative to the average sign:
- a sign on fewer than MIN_SIGN cards keeps multiplier 1.0 (too little evidence either way)
- a sign that did not predict failure in your cards gets 0 and is named

Checks printed with the result: ranking quality (AUC) of the built-in points and of the calibrated points,
the latter by 5-fold cross-validation; the calibration is recommended only if it ranks better out of sample.
Failure rate per grade under the calibrated points.
"""

from __future__ import annotations

import csv
import json
import math
import os

from .core import SIGNALS, grade

MIN_CARDS, MIN_EACH, MIN_SIGN = 20, 5, 3
YES = {"1", "yes", "y", "true", "failed", "rma", "returned"}
NO = {"0", "no", "n", "false", "ok", "fine", "passed", ""}


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def _solve(a: list[list[float]], v: list[float]) -> list[float]:
    m = [[*row, vi] for row, vi in zip(a, v)]
    k = len(m)
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        if abs(m[c][c]) < 1e-12:
            raise ValueError("degenerate data")
        for r in range(k):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][k] / m[i][i] for i in range(k)]


def fit_logistic(x: list[list[float]], y: list[int], l2: float = 0.01, steps: int = 50):
    """L2-regularised logistic regression by Newton's method; returns (intercept, coefficients)."""
    n, k = len(x), len(x[0])
    rows = [[1.0, *xi] for xi in x]
    beta = [0.0] * (k + 1)
    for _ in range(steps):
        grad = [0.0] * (k + 1)
        hess = [[0.0] * (k + 1) for _ in range(k + 1)]
        for xi, yi in zip(rows, y):
            p = _sigmoid(sum(b * v for b, v in zip(beta, xi)))
            s = p * (1 - p)
            for i in range(k + 1):
                grad[i] += (p - yi) * xi[i]
                for j in range(k + 1):
                    hess[i][j] += s * xi[i] * xi[j]
        for i in range(1, k + 1):
            grad[i] += l2 * n * beta[i]
            hess[i][i] += l2 * n
        step = _solve(hess, grad)
        beta = [b - d for b, d in zip(beta, step)]
        if max(abs(d) for d in step) < 1e-8:
            break
    return beta[0], beta[1:]


def auc(scores: list[float], failed: list[int]) -> float:
    """Probability a random healthy card outscores a random failed one (ties count half)."""
    ok = [s for s, f in zip(scores, failed) if not f]
    bad = [s for s, f in zip(scores, failed) if f]
    if not ok or not bad:
        return float("nan")
    return sum((g > b) + 0.5 * (g == b) for g in ok for b in bad) / (len(ok) * len(bad))


def _flag(v: str, where: str) -> bool:
    t = (v or "").strip().lower()
    if t in YES:
        return True
    if t in NO:
        return False
    raise ValueError(f"{where}: expected yes or no, got {v!r}")


def load_cards(labels: str, captures_dir: str | None = None) -> list[dict]:
    base = captures_dir or os.path.dirname(os.path.abspath(labels))
    cards = []
    with open(labels, encoding="utf-8-sig", newline="") as fh:
        for n, row in enumerate(csv.DictReader(fh), 2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            where = f"{labels} line {n}"
            if not row.get("capture"):
                raise ValueError(f"{where}: capture is empty")
            path = row["capture"] if os.path.isabs(row["capture"]) else os.path.join(base, row["capture"])
            try:
                with open(path, encoding="utf-8-sig") as cf:
                    text = cf.read()
            except OSError as e:
                raise ValueError(f"{where}: cannot read {path} ({e.strerror})") from None
            hours = None
            if row.get("hours"):
                try:
                    hours = float(row["hours"])
                except ValueError:
                    raise ValueError(f"{where}: hours {row['hours']!r} is not a number") from None
            try:
                rep = grade(text, hours, _flag(row.get("mining", ""), where))
            except ValueError as e:
                raise ValueError(f"{where}: {e}") from None
            cards.append(
                {"capture": row["capture"], "failed": _flag(row.get("failed", ""), where), "signals": rep.signals}
            )
    return cards


def _score(signals: dict, mult: dict) -> float:
    return max(0.0, 100 - sum(p * mult.get(k, 1.0) for k, p in signals.items()))


def _multipliers(cards: list[dict], failed: list[int]) -> tuple[dict, list[str], list[str]]:
    seen = {k: sum(1 for c in cards if c["signals"].get(k)) for k in SIGNALS}
    used = [k for k in SIGNALS if seen[k] >= MIN_SIGN]
    sparse = [k for k in SIGNALS if 0 < seen[k] < MIN_SIGN]
    mult = {k: 1.0 for k in SIGNALS}
    if not used:
        return mult, [], sparse
    x = [[c["signals"].get(k, 0.0) for k in used] for c in cards]
    _, coefs = fit_logistic(x, failed)
    positive = [c for c in coefs if c > 0]
    if not positive:
        raise ValueError("no warning sign predicted failure in these cards; keep the built-in points")
    # weight each sign's effect by how often it appears, so a common sign anchors the scale
    anchor = sum(c * seen[k] for k, c in zip(used, coefs) if c > 0) / sum(seen[k] for k, c in zip(used, coefs) if c > 0)
    backwards = []
    for k, c in zip(used, coefs):
        if c <= 0:
            mult[k] = 0.0
            backwards.append(k)
        else:
            mult[k] = round(min(5.0, c / anchor), 3)
    return mult, backwards, sparse


def calibrate(cards: list[dict], folds: int = 5) -> dict:
    failed = [int(c["failed"]) for c in cards]
    if len(cards) < MIN_CARDS or min(sum(failed), len(failed) - sum(failed)) < MIN_EACH:
        raise ValueError(
            f"need at least {MIN_CARDS} cards with {MIN_EACH}+ failed and {MIN_EACH}+ healthy; "
            f"got {len(cards)} ({sum(failed)} failed)"
        )
    mult, backwards, sparse = _multipliers(cards, failed)
    cv = [0.0] * len(cards)
    for f in range(folds):
        train = [i for i in range(len(cards)) if i % folds != f]
        try:
            m, _, _ = _multipliers([cards[i] for i in train], [failed[i] for i in train])
        except ValueError:
            m = {}
        for i in range(f, len(cards), folds):
            cv[i] = _score(cards[i]["signals"], m)
    base = [_score(c["signals"], {}) for c in cards]
    calibrated = [_score(c["signals"], mult) for c in cards]
    grades = []
    for g, lo, hi in (("A", 90, 101), ("B", 80, 90), ("C", 65, 80), ("D", 50, 65), ("F", -1, 50)):
        members = [f for s, f in zip(calibrated, failed) if lo <= round(s) < hi]
        grades.append(
            {
                "grade": g,
                "cards": len(members),
                "failure_rate": round(sum(members) / len(members), 3) if members else None,
            }
        )
    auc_default, auc_cv = auc(base, failed), auc(cv, failed)
    return {
        "multipliers": mult,
        "recommended": auc_cv > auc_default,
        "auc_default": round(auc_default, 4),
        "auc_calibrated_cv": round(auc_cv, 4),
        "cards": len(cards),
        "failed": sum(failed),
        "backwards_signs": backwards,
        "too_rare_to_judge": sparse,
        "grades": grades,
    }


def load_multipliers(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        doc = json.load(fh)
    m = doc.get("multipliers", doc) if isinstance(doc, dict) else None
    if not isinstance(m, dict) or not set(m) <= set(SIGNALS):
        raise ValueError(f"{path}: multipliers must use the signs {list(SIGNALS)}")
    for k, v in m.items():
        if not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 10:
            raise ValueError(f"{path}: multiplier {k} must be between 0 and 10")
    return {k: float(v) for k, v in m.items()}
