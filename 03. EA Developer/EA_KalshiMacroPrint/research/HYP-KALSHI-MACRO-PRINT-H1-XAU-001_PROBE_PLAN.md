# HYP-KALSHI-MACRO-PRINT-H1-XAU-001 — PROBE_PLAN (frozen prereg)

**Status:** FROZEN pre-outcome  
**Hypothesis:** HYP-KALSHI-MACRO-PRINT-H1-XAU-001  
**Package:** EA_KalshiMacroPrint (research only; no .mq5)  
**Source plan:** .context/cron_20260718_0211/PLAN.md  
**Parent source feasibility:** .context/cron_20260718_0122/ PLAN SHA 1b3e6f758b9a234880a9225189dcb770165d838c8f262c75a4b693c7faecd035  
**Economics allowlist:** .context/cron_20260718_0211/ECONOMICS_ALLOWLIST.json  
**Semantic map:** .context/cron_20260718_0211/SEMANTIC_ORIENTATION_MAP.json  
**xau_outcomes_read_before_freeze:** false  

This file is a byte-for-byte copy of PLAN §4 decision surface (plus this header). Do not change gates, cost, control, thinning, join, or windows under this hypothesis ID.

---

## 4. PROBE_PLAN — copy this section into the package research file

Grok must copy this section, without changing the decision surface, to:

`03. EA Developer/EA_KalshiMacroPrint/research/HYP-KALSHI-MACRO-PRINT-H1-XAU-001_PROBE_PLAN.md`

Then compute its SHA-256 before either registry row is appended and before any XAU outcome is read.

### 4.1 Status and scope

- Hypothesis: `HYP-KALSHI-MACRO-PRINT-H1-XAU-001`
- Package: `EA_KalshiMacroPrint` (research package only; no `.mq5`)
- Symbol/timeframe: `XAUUSD H1`
- Feature family: `regulated-prediction-market-macro-probability-print-flow`
- Model: `1`, offline Python/parquet kill-or-park screen only
- Source start: `2021-07-26T00:00:00Z`, the honest Kalshi public-beta floor
- Train: event/entry timestamps `2021-07-26T00:00:00Z` through `2023-12-31T23:59:59.999999Z`
- Internal validation: `2024-01-01T00:00:00Z` through `2024-12-31T23:59:59.999999Z`
- Holdout: `2025-01-01T00:00:00Z` onward, `SEALED`; load/read/use exactly zero holdout bars and zero holdout trades
- Outcome data: D-portable XAUUSD H1 only, with source path, broker, timezone conversion, row count, min/max UTC, and SHA recorded
- Cost status: `UNVERIFIED_PROXY`, never “real” or zero

### 4.2 PIT and data integrity contract

1. Acquire the complete available Kalshi trade/definition archive for the frozen series over 2021-07-26 through 2024-12-31. Samples alone are insufficient for an economic result.
2. Every trade requires non-empty `trade_id`, `ticker`, positive finite `count_fp`, finite `yes_price_dollars` in `[0,1]`, `taker_side` in `{yes,no}`, and RFC3339 `created_time` ending in `Z`.
3. Deduplicate only exact `(trade_id, ticker, created_time)` identities. Conflicting duplicates fail the source gate. Preserve raw responses, cursors, retrieval UTC, endpoint, and SHA.
4. Resolve market/event/series identities exactly from retained definitions. Never use a present-day `updated_time` as the historical trade availability clock.
5. The only availability time is the public trade `created_time`. Market definitions needed for interpretation must be proven available no later than the trade or the trade is excluded before outcome join; material missing-definition rates fail the source gate.
6. XAU bars must have UTC open and close times. Broker/server-to-UTC conversion must be documented and deterministic. Duplicate, non-monotone, or invalid OHLC bars fail closed.
7. The loader must apply a hard upper predicate of `2024-12-31T23:59:59.999999Z` and report `holdout_bars_loaded=0`, `holdout_trades_loaded=0`. No 2025+ metric, chart, count, or peek is permitted.
8. XAU history before 2021-07-26 may be loaded only for the minimum ATR(14) warm-up and may not generate a trade or metric.

### 4.3 Frozen signal construction

For each market ticker, sort prints by `created_time`, then `trade_id`. Group prints sharing the same `(event_ticker, market_ticker, created_time)` into a market micro-batch. Let:

- `p_b` be the `count_fp`-weighted average `yes_price_dollars` of the current micro-batch;
- `p_prev` be the weighted average YES price of the last strictly earlier micro-batch in the same market;
- `q_b` be the sum of `count_fp` in the current micro-batch;
- `market_flow = yes_xau_sign * q_b * (p_b - p_prev)`.

The first micro-batch in a market has no prior price and is structurally ineligible. No magnitude, price, size, liquidity, popularity, or confidence threshold is allowed.

At each exact `created_time`, aggregate eligible `market_flow` values by `event_ticker`; then sum all event scores at that timestamp. If the sum is exactly zero, it has no direction and emits no signal. This exact-zero rule is part of the sign definition, not a tunable threshold.

Thinning is permanently `MAX_ONE_PER_UTC_WEEKDAY`:

- consider only Monday–Friday by the event's UTC `created_time` date;
- within each UTC date, choose the earliest timestamp with a non-zero aggregate score;
- break an exact timestamp tie by sorted `event_ticker`, then sorted `market_ticker`, then sorted `trade_id` solely for reproducible aggregation;
- ignore every later candidate that UTC date;
- direction is LONG XAUUSD when aggregate score `>0`, SHORT when `<0`.

This rule uses no outcome, return, value threshold, hour/session veto, or after-the-fact series preference. Report raw prints, eligible batches, non-zero timestamps, thinned source events, empty elapsed weeks, and source events per elapsed calendar week.

### 4.4 Closed-bar join and execution

For a retained source event at `created_time=t`:

1. Define `join_bar` as the earliest H1 bar with `bar_close_utc > t`. Equality is forbidden: a bar whose close equals `t` is not eligible.
2. The join bar must be fully completed and addressed as `shift>=1` when any XAU field is read.
3. Enter only at the open of the immediately following H1 bar. Thus no price from the join bar is used before it is closed.
4. If the market is closed or an H1 bar is absent, use the next valid completed-bar/next-open sequence; do not synthesize a bar or backdate the event.
5. Apply a fixed 12-completed-H1-bar refractory window from each accepted entry. Any later source event whose planned entry falls inside that window is skipped in both challenger and control. This is outcome-independent and guarantees at most one 0.5%-risk position at a time.
6. Split assignment uses entry time. Reset state at the train/validation boundary; no position may cross the boundary. Force-close at the final available bar inside a split and label `SPLIT_END`.

No day, hour, news, spread, volatility, trend, or regime filter is allowed.

### 4.5 Entry, exit, sizing, and bar ambiguity

- Challenger direction: frozen Kalshi aggregate-score sign.
- ATR: Wilder ATR(14) from completed H1 bars through the join bar only.
- Initial stop: `1.5 * ATR(14)` from the raw entry price.
- Target: `2.0R`, where `1R` is the initial raw stop distance.
- Time stop: exit at the close of the 12th completed H1 bar after entry if neither price exit occurred.
- Risk: `0.50%` of current closed equity per trade, maximum; no open-risk stacking.
- Position policy: one position, no add-on, partial, break-even move, trailing stop, martingale, grid, recovery, or pyramiding.
- If stop and target are both touched inside one H1 bar, book the stop first.
- If an adverse gap opens beyond the stop, fill at the worse bar open. If a favorable gap opens beyond the target, fill at the target, not the better open.
- Missing ATR or invalid OHLC makes that planned entry ineligible in both arms and is counted explicitly.

### 4.6 Cost contract

Use XAUUSD price units, with `1 point = 0.01` price units. Frozen round-trip proxy:

- x1: `82 points RT = 0.82` XAU price units total;
- x1.5: `123 points RT = 1.23` price units total;
- x2: `164 points RT = 1.64` price units total.

Apply half of the selected RT cost adversely at entry and half at exit. The proxy is intended to cover spread, commission, and slippage together but is `UNVERIFIED_PROXY`; do not call it observed/real cost. If the source symbol's point scale is not 0.01, normalize through price units and record the conversion rather than silently changing the economic cost. Report gross and each cost level separately. A missing or zero cost application invalidates the run.

### 4.7 Matched control

Use exactly the same retained Kalshi event timestamps, join bars, entry bars, refractory skips, ATR geometry, exits, risk, split handling, and cost levels. Replace only direction:

- control LONG when `close(join_bar) >= close(previous completed H1 bar)`;
- control SHORT otherwise.

The equality rule is deliberately LONG to preserve an identical schedule without a post-result choice. The control may not add a filter. Both arms must have identical planned-entry identities and counts; any mismatch invalidates the comparison.

### 4.8 Metrics and fixed gates

Elapsed-week denominators are calendar duration divided by 7, including weeks with zero events; never use active weeks. Compute train and validation separately, then combined for diagnostics. Profit factor with zero gross loss is undefined, not infinity and not a pass. Zero trades has no WR/PF/expectancy.

All of the following are conjunctive hard gates:

1. Data/PIT/allowlist/semantic-map/hash assertions all pass; World rows included = 0; holdout rows loaded = 0.
2. Thinned source cadence is between `2.0` and `5.0` events per elapsed calendar week in train and validation separately.
3. Executed paired-trade cadence is between `2.0` and `5.0` trades per elapsed calendar week in train and validation separately.
4. Minimum paired N: train `>=250`, validation `>=100`, combined `>=350`; also train has `>=75` LONG and `>=75` SHORT, validation `>=30` LONG and `>=30` SHORT.
5. Challenger gross PF `>=1.35` in train and validation.
6. Challenger PF at x1 cost `>=1.30` in train and validation.
7. Challenger PF at x1.5 cost `>=1.25` in train and validation.
8. Challenger PF at x2 cost `>=1.00` in train and validation.
9. Challenger expectancy at x1 `>=+0.05R/trade` in train and validation.
10. Maximum closed-equity drawdown at x1 `<=8.0%` in train, validation, and combined reconstruction.
11. Net x1 result is positive in at least 3 of the 4 entry years `2021(partial), 2022, 2023, 2024`, and 2024 validation itself is positive.
12. Challenger beats matched control in both train and validation by `PF_x1 difference >=+0.10` and `net_R_x1 difference >=+5.0R`.
13. No single entry year contributes more than 50% of positive combined x1 gross profit.
14. A fixed-seed (`20260718`) 10,000-path moving-block bootstrap of the paired challenger trade sequence, block length 5 trades, has x1 P95 maximum drawdown `<=8.0%`. Preserve the algorithm/version and raw summary. This is a tail diagnostic, not permission to resample parameters.

The registry `acceptance_contract` remains the GOAL-level floor: PF `1.30`, cadence `2–5`, DD `<=8%`, x1.5 PF `>=1.25`, x2 PF `>=1.00`, MC P95 DD `<=8%`. Passing an unverified cost proxy does not satisfy real-cost promotion.

### 4.9 Decision rule

- All gates pass: `SURVIVE_OFFLINE_ECONOMIC_PROBE`. Leave registry state `probe`; write evidence and a readout. Do not write `.mq5` or run Model 0 in this tick. A separate Owner-scoped preregistration must decide whether verified cost acquisition and Model 0 are justified.
- Any structural source, PIT, semantic, cadence, N, economics, control-margin, concentration, or tail gate fails after a valid run: append terminal state `killed`, verdict `KILL_AT_OFFLINE_PROBE`, preserve the failure packet, and stop.
- A genuinely transient/external acquisition blocker or inability to freeze the semantic map before any XAU outcome is read: append `parked` only under the PARK rules in section 7 and stop without performance metrics.

No failed gate may be repaired by changing the allowlist, semantic sign, signal aggregation, cost, session, weekday, ATR, RR, time stop, control, year selection, or threshold under this hypothesis ID.
