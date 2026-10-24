# gpu-carfax

[![CI](https://github.com/eliem08/gpu-carfax/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/gpu-carfax/actions/workflows/ci.yml)

> **Carfax for used GPUs** — a health report before you buy secondhand.

A wave of ex-datacenter and ex-mining GPUs is hitting eBay. Some are fine;
some have been cooked at 90 °C for two years and throw ECC errors under load.
`gpu-carfax` turns a short stress-test telemetry capture into a graded,
shareable health report — so buyers know what they're getting and honest
sellers get a better price.

## What the MVP does

- Parses `nvidia-smi --query-gpu=... --format=csv` captures taken during a
  stress run (`gpu-carfax capture-cmd` prints the exact command)
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
gpu-carfax capture-cmd                    # run this on the seller's machine during a 10-min stress test
gpu-carfax report capture.csv --hours 14000 --mining --market-price 1400
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
gpu_carfax/core.py       domain logic (pure, importable, fully tested)
gpu_carfax/__main__.py   CLI (`gpu-carfax ...` / `python -m gpu_carfax ...`)
tests/                unit tests + generated CLI smoke tests
examples/             sample inputs used by the docs and smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #18).
