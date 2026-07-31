# TBBO SOURCE-QUALITY AND FEATURE PLAN - HYP-EURFXOFI-EURUSD-M1-007

Frozen on `2026-07-30` before reading any HYP006 TBBO payload and before any
EURUSD target return is opened.

## Purpose and dependency

HYP007 is an outcome-blind decode successor to HYP006. It may run only after
the HYP006 manifest reaches `DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED`, has no
`in_flight` request, and an independent verifier rehashes and fully decodes all
completed files. The final HYP006 manifest SHA256 must be appended to the
registry before the real HYP007 run.

Inputs stay fixed:

- Databento `GLBX.MDP3` / `tbbo` / `6E.v.0`, `stype_out=instrument_id`.
- Exact 15-second windows `[14:14:45,14:15:00) Europe/Berlin` on the 1,359
  HYP002 dates: TRAIN 630, VALIDATION 526, HOLDOUT 203, cutoff 2026-07-29.
- Raw source root on `D:` only. HYP007 may read split labels and pre-decision
  source records, but no EURUSD bar after 14:15, target return, trade outcome,
  economic metric, EA result or optimization output.

## Frozen feature transform

Databento TBBO `side` is used as the initiating side: `B`/Bid is a buy
aggressor, `A`/Ask is a sell aggressor and `N`/None is unclassified. For each
record with size `q`, signed aggressive volume is `+q`, `-q` or `0`
respectively. No tick-rule fallback or hindsight relabel is allowed.

One row is produced per selected date with these source-only fields:

1. Identity and quality: date, split, UTC start/end, file identity, record
   count, classified/unclassified counts and volume, first/last event time,
   source coverage span and terminal silence.
2. Full-window flow: buy/sell/unclassified volume, total volume,
   `flow_signed = buy_volume - sell_volume`, and
   `flow_imbalance = flow_signed / (buy_volume + sell_volume)` when classified
   volume is positive, otherwise null.
3. Frozen three-bin trajectory: the same counts/volume/imbalance for
   `[0,5)`, `[5,10)` and `[10,15)` seconds from the exact UTC start. Boundary
   timestamps belong to the later bin. A record outside `[start,end)` is fatal.
4. Trade-space context: first/last trade price, signed trade-price move,
   volume-weighted trade price, median and p95 contemporaneous spread in 6E
   ticks (`0.00005`), locked/crossed record counts, and median top-of-book size
   imbalance `(bid_size-ask_size)/(bid_size+ask_size)` where the denominator is
   positive.
5. Predeclared trajectory summaries:
   `flow_acceleration = imbalance_bin3 - imbalance_bin1` and
   `late_flow_share = classified_volume_bin3 / classified_volume_full`.

The source-empty dates remain explicit rows with null feature values; they may
not be silently dropped. Raw prices are normalized with the DBN Python API,
not by manually guessing fixed-point scale.

## Independent source gates

The run fails closed unless all conditions hold:

- exact 1,359 unique planned dates and split counts 630/526/203;
- exact manifest/file/empty union equals the planned request IDs;
- no `in_flight`, duplicate filename/request/date, missing file or extra DBN;
- every file byte length and SHA256 matches the final HYP006 manifest;
- every DBN fully decodes and its decoded record count matches the manifest;
- every record is TBBO trade-space data and falls inside its exact window;
- bid/ask/trade/size fields required by a metric are validated before use;
- no crossed book record (`bid > ask`); locked books are measured, not hidden;
- at least 99% of non-empty windows have classified buy/sell volume and at
  least 95% of total volume is side-classified. A miss is source-quality
  invalid, not evidence of no edge.

The receipt must disclose actual spend estimate from the live HYP006 quote,
downloaded compressed bytes, decoded records, source-empty windows, classified
volume ratio, locked/crossed counts, and every artifact SHA256.

## Frozen source dashboard

The real run must create the following source-only charts before outcomes open:

1. `01_coverage_by_year.png`: selected vs non-empty windows, decoded records
   and aggressive volume by year.
2. `02_quality_distributions.png`: record count, total volume, classified
   volume share and spread-tick distributions.
3. `03_signed_flow_by_year_split.png`: imbalance distribution by year and
   TRAIN/VALIDATION/HOLDOUT, without returns.
4. `04_within_window_trajectory.png`: buy/sell volume and imbalance across the
   frozen three 5-second bins.
5. `05_missingness_calendar.png`: selected/source-empty/usable coverage by
   calendar month.

A machine-readable `source_features.parquet`, `source_quality_summary.json`,
`artifact_manifest.json` and concise English readout are mandatory. Charts
must state population size and may not imply economic performance.

## Closed surfaces

HYP007 authorizes source validation and source-feature materialization only.
It does not authorize target-price joins, TRAIN economics, validation/holdout
returns, MQL5, Model 0, optimization, promotion, paper trading or live trading.
A fresh preregistered successor must consume the exact HYP007 feature/manifest
hashes and open TRAIN outcomes first.
