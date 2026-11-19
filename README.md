<!-- sell-kit:start -->
# GPU Vitals

[![CI](https://github.com/eliem08/gpuvitals/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/gpuvitals/actions/workflows/ci.yml)

> **A health report for a used GPU before you buy it.**

**Who it's for:** Buyers and sellers of secondhand GPUs, and the marketplaces in between.

**The problem:** Used GPUs, especially ex-mining cards, hide thermal, clock and memory problems that only show up after you've paid.

**What you get:** Grade an nvidia-smi stress capture from A to F with explained deductions and a fair-price multiplier, calibrated to the cards you have seen fail.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install gpuvitals-0.1.0-py3-none-any.whl
gpuvitals capture-cmd
gpuvitals report examples/capture.csv --hours 14000 --market-price 800
gpuvitals calibrate examples/fleet/labels.csv --captures examples/fleet --out gv-calibration.json
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
gpuvitals-web --port 8000          # then open http://127.0.0.1:8000
gpuvitals-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t gpuvitals . && docker run -p 8000:8000 -e API_KEYS=sk_... -v gpuvitals-data:/data gpuvitals
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `gpuvitals-web usage` prints calls per key for billing.

Endpoints: `POST /api/capture-cmd`, `POST /api/report`, `POST /api/calibrate`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Deploy and sell

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/eliem08/gpuvitals)

`render.yaml` (one click, above) and `fly.toml` (`fly launch --copy-config`) both run the Dockerfile with a persistent `/data` volume and a `/healthz` check.
To sell self-serve, set four variables and point a Stripe webhook at `https://<your-host>/billing/webhook` (events `checkout.session.completed` and `customer.subscription.deleted`):

| Variable | Example |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `STRIPE_PRICES` | `team=price_123,business=price_456` |
| `PUBLIC_URL` | `https://gpuvitals.example.com` |
| `PLAN_QUOTAS` (optional) | `team=10000,business=250000` successful calls per key per month |

Buyers pick a plan on `/pricing`, pay on Stripe Checkout and see their API key once on the success page. Cancelling the subscription revokes the key. A selling server always requires a key.

## Pricing

Monthly plans start with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Single report** | $9 per GPU | A-F grade; Itemised deductions; Fair-price estimate |
| **Seller** | $49 per month | Unlimited reports; Report IDs |
| **Marketplace** | $499 per month | API access; JSON output; Mining-wear deductions; Grading calibrated to your failure data |

To start a trial or buy a plan, [request access](https://github.com/eliem08/gpuvitals/issues/new?title=GPU%20Vitals%20trial&labels=sales).

Plan note: every plan runs the same software, and every API key unlocks all of it. Monthly call volumes are
enforced when `PLAN_QUOTAS` is set (see Deploy and sell); seat and agent limits are licence terms the code does
not enforce. Support, SLA and done-for-you items are services.

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

## Calibrate to the cards you have sold

The deduction points are starting values. Once you know which graded cards later failed or came back, fit the
grading to them:

```bash
gpuvitals calibrate labels.csv --captures ./captures --out calibration.json
gpuvitals report capture.csv --calibration calibration.json
```

`labels.csv` has a `capture` column (file name in `--captures`) and `failed` (yes/no), and optionally `hours`
and `mining`. You need at least 20 cards, with at least 5 failed and 5 healthy.

How the fit works and how you can check it:
- A logistic regression learns how much one point of each warning sign (running hot, low clocks, ECC errors and
  so on) raises the odds of failure in your cards.
- Each sign gets a multiplier relative to the average sign. A sign that did not predict failure gets 0 and is
  named. A sign seen on fewer than 3 cards keeps 1, because there is too little evidence to judge it.
- The command prints the ranking quality (AUC) of the built-in points and of the calibrated points, the latter
  cross-validated, and recommends the calibration only if it ranks better out of sample.
- It shows the failure rate in each grade.

`examples/fleet` holds 80 synthetic cards for trying the command, not real GPUs. In that fleet only memory
errors cause failures, so calibration learns to stop penalising hot and slow-clocked cards.

## Quickstart

```bash
pip install -e .
gpuvitals capture-cmd                    # run this on the seller's machine during a 10-min stress test
gpuvitals report capture.csv --hours 14000 --mining --market-price 1400
gpuvitals calibrate examples/fleet/labels.csv --out calibration.json   # fit the grading to known outcomes
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
