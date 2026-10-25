import argparse
import csv
import json
import math
import os
import sys

from .core import CAPTURE_CMD, grade


def _finite_float(s: str) -> float:
    """argparse type: a float that is not nan/inf, so limits and prices cannot be bypassed."""
    v = float(s)
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {s!r}")
    return v


def _run(argv=None):
    ap = argparse.ArgumentParser(prog="gpuvitals")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture-cmd")
    r = sub.add_parser("report")
    r.add_argument("capture")
    r.add_argument("--hours", type=_finite_float)
    r.add_argument("--mining", action="store_true")
    r.add_argument("--market-price", type=_finite_float)
    r.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "capture-cmd":
        print("# Start a stress test (e.g. gpu-burn 600) in another terminal, then run:")
        print(CAPTURE_CMD)
        return 0
    with open(a.capture, encoding="utf-8-sig") as fh:
        rep = grade(fh.read(), a.hours, a.mining, a.market_price)
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
