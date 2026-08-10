# HYP-BKSR-XAUUSD-M15-002 — frozen H1 squeeze-release / next-H1-open source gate

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

## Why this revision exists

`HYP-BKSR-XAUUSD-M5-001` produced 757 raw H1 squeeze-release events and a target-like 2.8023 executable events/week, but only 96.5654% of raw events mapped to an exact native-M5 clock row versus the frozen 97% gate. No next-bar price, trade, return, PnL or PF was read. The FivePercent foundation has no native XAUUSD M15 parquet asset.

This fresh revision changes only availability mapping: an event is available at the exact next native H1 open. A future EA may be hosted on M15, but must process the event once at that H1 boundary. This is an execution-clock thesis, not a threshold, session, direction, cooldown, stop or outcome rescue. Counts from HYP001 cannot be reused.

## Identity and sealed scope

- Hypothesis: `HYP-BKSR-XAUUSD-M15-002`
- Family: `h1-bollinger20x2-inside-keltner20x1p5-first-release-next-h1-open`
- Intended host timeframe after source pass: M15
- Signal and availability source: native XAUUSD H1
- Source inception: `2004-06-11T04:00:00Z`
- Source materialized only for `time_utc < 2023-01-01T00:00:00Z`
- Source scoring window: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation, holdout, post-event prices and all economic fields remain unopened.
- Sole source attempt: `BKSR002-SOURCE-ATTEMPT-001`

## Exact indicator formula

Use every observed native H1 bar from inception without synthetic bars. Finite bars with `high >= low` and `low <= close <= high` are valid, including flat bars.

- Bollinger basis: arithmetic mean of the last 20 closes.
- Bollinger deviation: population standard deviation over the same 20 closes.
- Bollinger bands: basis ± `2.0 * deviation`.
- Keltner basis: EMA20 of close, SMA-seeded at index 19, then `EMA_t = EMA_(t-1) + (2/21)*(close_t-EMA_(t-1))`.
- True range: `high-low` at inception; later `max(high-low, abs(high-prev_close), abs(low-prev_close))`.
- ATR20: Wilder RMA, SMA-seeded from the first 20 TR values, then `(19*prior+TR)/20`.
- Keltner bands: EMA20 ± `1.5 * ATR20`.
- Squeeze is on only when BB lower is strictly above KC lower and BB upper is strictly below KC upper.

## Exact event state machine

- A squeeze cluster begins on the first squeeze-on bar and continues through consecutive squeeze-on bars.
- Only the first completed H1 bar after an active cluster that is squeeze-off is the release bar; the cluster is consumed immediately.
- LONG iff release close is strictly above its current BB basis.
- SHORT iff release close is strictly below its current BB basis.
- Equality consumes the cluster without an event.
- Invalid/unusable indicator state resets the cluster and emits nothing.

## Exact next-H1 availability

For release bar at row `t`, decision availability is the next physical H1 row `t+1`. The raw event is executable only when all are true:

- `time_utc[t+1] == time_utc[t] + 3600 seconds`;
- `source_epoch[t+1] == source_epoch[t] + 3600`;
- availability is still `< 2023-01-01T00:00:00Z`.

Only next-row timestamps/epochs may be read. No OHLC from `t+1` or later is permitted. A gap event is consumed, never queued.

## Frozen source and gates

- Manifest: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`
- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD H1: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet`
- H1 SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- Formula dependency: `analyze_bksr_h1_m5_source.py` SHA256 `CC393F09795346901353DE120D6C9B94E94078AF4EFFC260E4DC43E1E86F8164`.

All gates must pass together:

- design H1 rows >= 25,000;
- feature coverage >= 99%;
- raw-event exact-next-H1 coverage >= 97%;
- executable events >= 500;
- pooled cadence 2–5 events/elapsed calendar week;
- each direction >= 30%;
- maximum calendar-year share <= 30%;
- each calendar year cadence 1.25–6.50/week;
- zero direction conflicts, deterministic replay, exact outcome-blind ledger and immutable one-shot receipt.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_BBKC_NEXT_H1_OPEN`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_BUILD_AUTHORIZED` and permits only a fresh MQL5 correctness/build child followed by one untuned baseline.

Forbidden before source pass: MQL5 creation, MT5 run, entry/exit/risk optimization, session or direction filters, parameter changes, post-event OHLC, trades, returns, PF, validation, holdout, paper or live deployment.

