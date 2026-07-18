# Market Data Shelf

Canonical location for market data used in backtests, training, probes and EA
development. Layout: `data/<broker>/<symbol>/` with a `manifest.json`
(schema `market_data_manifest.v1`: files, bytes, SHA256, coverage, clock
model, acquisition-evidence pointer) per dataset.

Rules:

- Working datasets live HERE on `D:` — never on `C:` alongside the MT5
  installation, never in `FILE_COMMON`, never inside an EA package.
- Every dataset is hash-bound by its manifest; consumers verify SHA256, not
  path history.
- Server-time columns convert to UTC via
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py` (or the
  equivalent verified model for another broker). Store both `time_server` and
  `time_utc`.
- Broker-reported historical spread columns are not cost evidence.
- This directory is gitignored (large binaries); the manifests make contents
  reproducible and verifiable.
