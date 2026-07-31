# SOURCE-QUALITY PLAN - HYP-EURFXOFI-EURUSD-M1-009

Frozen on `2026-07-30` before reading any HYP006 TBBO payload and before any
EURUSD target return is opened. This is the corrected fresh successor to the
unrun HYP007 v1 build.

## Identity, exact source and one-shot boundary

- Attempt: `EURFXOFI009-SOURCE-QUALITY-001`, exactly once.
- Parent: terminal raw-acquisition HYP006 manifest SHA256
  `C2FA31D39970200DD05AF35A3E23BAE3941F1083BE870D77A4A24E4A709DF820`.
- Source root: HYP006 `EURFXOFI006-TBBO-SOURCE-001/`; DBN payloads are
  explicitly under its immutable `raw/` child, not at the root.
- Manifest truth: status `DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED`, 1,356
  unique DBN files, three source-empty windows, 1,100,083 compressed bytes,
  34,838 decoded records, no in-flight request.
- Exact selected population: 1,359 dates through 2026-07-29, split TRAIN 630,
  VALIDATION 526 and HOLDOUT 203.
- Dataset/schema/symbol: Databento `GLBX.MDP3` / `tbbo` / `6E.v.0` with exact
  `[14:14:45,14:15:00) Europe/Berlin` windows.

The evidence root must be absent before authorization:

`03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EURFXOFI-EURUSD-M1-009/EURFXOFI009-SOURCE-QUALITY-001/`

The run is local and source-only: zero network/paid calls, zero EURUSD target
returns, zero economics, zero MT5/MQL5/Model 0 and zero trading mutation.

## Frozen independent verification

Before feature output, the builder must independently:

1. rehash the final manifest and exact HYP002 date ledger;
2. reconcile all 1,359 request IDs and 630/526/203 split counts;
3. require the exact `raw/*.dbn.zst` filename set, zero partial/extra files;
4. recheck every file byte length and SHA256 against the manifest;
5. fully decode every DBN and match its record count;
6. require every event timestamp inside its exact end-exclusive window;
7. reject any non-TBBO trade action, invalid trade/quote field or crossed book.

Any miss is source/engineering invalid, not no-edge. No fallback path, schema,
date, timestamp, side classifier or partial adoption is allowed.

## Frozen feature transform

Databento TBBO `side` is the initiating side. `B`/Bid contributes `+size`,
`A`/Ask contributes `-size`, and `N`/None contributes zero signed volume and is
reported as unclassified. No tick-rule fallback or hindsight relabel is
allowed.

One row per selected date contains:

- identity/split/window/file/source-empty and record/coverage fields;
- buy, sell, unclassified, classified and total aggressive volume;
- `flow_signed = buy_volume - sell_volume` and
  `flow_imbalance = flow_signed / classified_volume` when positive;
- the same fields for fixed `[0,5)`, `[5,10)`, `[10,15)` second bins;
- first/last trade price, VWAP, move in 6E ticks (`0.00005`), median/p95
  contemporaneous spread, locked/crossed counts and median top-book size
  imbalance;
- `flow_acceleration = bin3_imbalance - bin1_imbalance` and
  `late_flow_share = bin3_classified_volume / full_classified_volume`.

Source-empty dates remain explicit rows with null feature values.

## Hard source-quality gates

- exact 1,359 rows and split counts 630/526/203;
- exact 1,356 rehashed/decoded files plus three explicit empty dates;
- zero crossed books and zero records outside their frozen windows;
- at least 99% of non-empty windows have classified buy/sell volume;
- at least 95% of total aggressive volume is side-classified;
- live estimated acquisition total remains USD2.117540538299 <= USD2.25;
- every output and chart is hash-bound and declares no outcome use.

## Mandatory artifacts and charts

Data output root:

`02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/HYP-EURFXOFI-EURUSD-M1-009/EURFXOFI009-SOURCE-QUALITY-001/`

Mandatory artifacts: `source_features.parquet`,
`source_quality_summary.json`, `artifact_manifest.json`, English readout and:

1. `01_coverage_by_year.png`;
2. `02_quality_distributions.png`;
3. `03_signed_flow_by_year_split.png`;
4. `04_within_window_trajectory.png`;
5. `05_missingness_calendar.png`.

The package-local evidence root must contain attempt-started, terminal and
artifact-binding receipts. Charts are source diagnostics only and may not
imply economic performance.

## Authority boundary

The disarmed builder/tests and an independent review receipt must be registry-
bound before source run authority opens. HYP009 completion can only hand exact
feature/summary/artifact hashes to a fresh TRAIN-economic successor. It cannot
authorize performance metrics, outcomes, validation/holdout returns, MQL5,
Model 0, optimization, promotion, paper or live trading.
