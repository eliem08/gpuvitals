# gpu-carfax

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
