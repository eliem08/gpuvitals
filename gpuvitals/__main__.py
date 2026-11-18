import argparse
import csv
import json
import math
import os
import sys

from .calibrate import calibrate, load_cards, load_multipliers
from .core import CAPTURE_CMD, grade


def _finite_float(s: str) -> float:
    """argparse type: a float that is not nan/inf, so limits and prices cannot be bypassed."""
    v = float(s)
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {s!r}")
    return v


def build_parser():
    ap = argparse.ArgumentParser(prog="gpuvitals")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture-cmd")
    r = sub.add_parser("report")
    r.add_argument("capture")
    r.add_argument("--hours", type=_finite_float)
    r.add_argument("--mining", action="store_true")
    r.add_argument("--market-price", type=_finite_float)
    r.add_argument("--json", action="store_true")
    r.add_argument("--calibration", help="file from `calibrate` (default: built-in points)")
    c = sub.add_parser("calibrate", help="fit the grading to cards whose fate you know")
    c.add_argument("labels", help="CSV: capture, failed (yes/no)[, hours, mining]")
    c.add_argument("--captures", help="folder the capture paths are relative to (default: the CSV's folder)")
    c.add_argument("--out", help="write the calibration here, for report --calibration")
    return ap


def _run(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "capture-cmd":
        print("# Start a stress test (e.g. gpu-burn 600) in another terminal, then run:")
        print(CAPTURE_CMD)
        return 0
    if a.cmd == "calibrate":
        res = calibrate(load_cards(a.labels, a.captures))
        print(f"{res['cards']} cards, {res['failed']} failed")
        print(
            f"  ranking quality (AUC): built-in points {res['auc_default']:.3f}, "
            f"calibrated {res['auc_calibrated_cv']:.3f} (cross-validated)"
        )
        for k, v in res["multipliers"].items():
            print(f"  {k:<18} x{v:g}")
        if res["backwards_signs"]:
            print(f"  did not predict failure in your cards (set to 0): {', '.join(res['backwards_signs'])}")
        if res["too_rare_to_judge"]:
            print(f"  too few cards to judge (kept at 1): {', '.join(res['too_rare_to_judge'])}")
        for g in res["grades"]:
            rate = "-" if g["failure_rate"] is None else f"{g['failure_rate']:.0%} failed"
            print(f"  grade {g['grade']}  {g['cards']:>4} cards  {rate}")
        print(
            "calibration: " + ("use it" if res["recommended"] else "it does not beat the built-in points; keep those")
        )
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                json.dump(res, fh, indent=2)
            print(f"written to {a.out}; grade with report --calibration {a.out}")
        return 0
    mult = load_multipliers(a.calibration) if a.calibration else None
    with open(a.capture, encoding="utf-8-sig") as fh:
        rep = grade(fh.read(), a.hours, a.mining, a.market_price, multipliers=mult)
    if a.json:
        print(json.dumps(rep.__dict__, indent=2))
        return 0
    print(f"GPU HEALTH REPORT  #{rep.report_id}")
    print(f"{rep.gpu}  serial {rep.serial}  ({rep.samples} samples)")
    print(f"Grade {rep.grade}  -  {rep.score}/100")
    for k, v in rep.metrics.items():
        if v is not None:
            print(f"  {k:<18} {v:.2f}" if isinstance(v, float) else f"  {k:<18} {v}")
    for reason, pts in rep.deductions:
        print(f"  -{pts:<5} {reason}")
    if rep.fair_price:
        print(f"Fair price: ${rep.fair_price:,.2f} ({rep.price_multiplier:.0%} of market)")
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
