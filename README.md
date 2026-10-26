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

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
gpuvitals-web --port 8000          # then open http://127.0.0.1:8000
gpuvitals-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t gpuvitals . && docker run -p 8000:8000 -e API_KEYS=sk_... -v gpuvitals-data:/data gpuvitals
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `gpuvitals-web usage` prints calls per key for billing.

Endpoints: `POST /api/capture-cmd`, `POST /api/report`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
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

Buyers pick a plan on `/pricing`, pay on Stripe Checkout and see their API key once on the success page. Cancelling the subscription revokes the key. A selling server always requires a key.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Single report** | $9 per GPU | A-F grade; Itemised deductions; Fair-price estimate |
| **Seller** | $49 per month | Unlimited reports; Shareable report IDs; Listing badge |
| **Marketplace** | $499 per month | API access; Bulk grading; Fraud checks |

To start a trial or buy a plan, [request access](https://github.com/eliem08/gpuvitals/issues/new?title=GPU%20Vitals%20trial&labels=sales).

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
