<!-- sell-kit:start -->
# GPU Vitals

[![CI](https://github.com/eliem08/gpuvitals/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/gpuvitals/actions/workflows/ci.yml)

> **A health report for a used GPU before you buy it.**

**Who it's for:** Buyers and sellers of secondhand GPUs, and the marketplaces in between.

**The problem:** Used GPUs, especially ex-mining cards, hide thermal, clock and memory problems that only show up after you've paid.

**What you get:** Grade an nvidia-smi stress capture from A to F with explained deductions and a fair-price multiplier.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install gpuvitals-0.1.0-py3-none-any.whl
gpuvitals capture-cmd
gpuvitals report examples/capture.csv --hours 14000 --market-price 800
```

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Single report** | $9 per GPU | A-F grade; Itemised deductions; Fair-price estimate |
| **Seller** | $49 per month | Unlimited reports; Shareable report IDs; Listing badge |
| **Marketplace** | $499 per month | API access; Bulk grading; Fraud checks |

To start a trial or buy a plan, email **sales@YOUR-DOMAIN.com**.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

- Parses `nvidia-smi --query-gpu=... --format=csv` captures taken during a
  stress run (`gpuvitals capture-cmd` prints the exact command)
- Checks:
  - **thermals**: peak and sustained temperature vs. throttle threshold
  - **clocks**: SM clock under load vs. max boost (throttling / degraded silicon)
  - **power**: can it reach its power limit under load (VRM / power delivery health)
  - **memory**: corrected / uncorrected ECC errors, retired pages
  - **fan**: fan at 100% while still hot = failing cooler / dried paste
- Optional seller declarations: power-on hours, mining history
- **Score 0–100, grade A–F**, itemised deductions, and a price adjustment vs. a
  reference market price
- Report ID = SHA-256 of the capture, so a buyer can verify the report matches the data

## Quickstart

```bash
pip install -e .
gpuvitals capture-cmd                    # run this on the seller's machine during a 10-min stress test
gpuvitals report capture.csv --hours 14000 --mining --market-price 1400
```

## Roadmap

- Signed capture agent (tamper-evident) + hosted public report pages
- Marketplace integrations: "Carfax verified" badge on listings
- Fleet-level history: same serial seen across resales

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
gpuvitals/core.py       domain logic (pure, importable, fully tested)
gpuvitals/__main__.py   CLI (`gpuvitals ...` / `python -m gpuvitals ...`)
tests/                unit tests + generated CLI smoke tests
examples/             sample inputs used by the docs and smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #18).
