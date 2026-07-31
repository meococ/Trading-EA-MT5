# DESIGN ECONOMICS OBSERVED-M1/M5 REPAIR PLAN V2 - HYP-ROUND-CASCADE-EURUSD-M5-005

Status: FROZEN PRE-AUTHORITY, PRE-OUTCOME on 2026-07-29. This V2 supersedes the unarmed V1 plan before any HYP005 registry authority, review receipt, run packet, public DESIGN read, trade outcome, metric, or market verdict. V1 remains an immutable prior draft at `HYP-ROUND-CASCADE-EURUSD-M5-005_DESIGN_ECONOMICS_PLAN.md`, SHA256 `4469859C890E64B0B899FAFA78B40D5D8D6E0B9831D18574AE0A382D2AB828D3`.

V1 was rejected in independent implementation review because selecting entry from complete M5 bars used future offsets `+1..+4` and could retroactively move entry, while M5-only stop inspection omitted observed M1 rows in incomplete bins and could miss adverse gap reopens. V2 changes only this pre-outcome execution/data contract. It does not change any source signal, arm, direction, threshold, session, ATR, stop distance, horizon count, cost, cadence denominator, DSR definition, economic gate, or verdict.

## 1. Identity and frozen parents

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-005`
- `parent_candidate`: `HYP-ROUND-CASCADE-EURUSD-M5-004`
- `source_signal_hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-002`
- `ea_name`: `EA_RoundNumberCascade`
- Symbol / decision timeframe: EURUSD M5 from immutable public DESIGN M1 BID bars.
- Parent attempt: `HYP004-DESIGN-ECON-001`.
- Parent started path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS/HYP004-DESIGN-ECON-001/attempt_started.json` / `46ADCB275482CD496D8C6DE6B1803FD735D9EC3E128D93F87540C47FFE80527F`.
- Parent terminal path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS/HYP004-DESIGN-ECON-001/attempt_terminal.json` / `899700298BA910A1FF4D29FD9B4B95144835BB10BF23FAFE537224A957F6AED5`.
- Parent status/reason: `ENGINEERING_INVALID_NO_MARKET_VERDICT` / `missing exact M1 entry window`; only `attempt_started.json` exists in its artifact chain.

## 2. Frozen source and producer boundary

- HYP002 source ledger path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl` / `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`.
- HYP002 source report/receipt/terminal SHA256: `E6AEE8603A922FB87497843A9302D8D24C90E000B154E61264EB8A290B3492D0`, `C52A47071F10E6DFE1EAEB8C2AAC899ED4B7C915E71AB932193A57130CBAF23A`, `2B2BD6F91EC77FCA824DF96AC6FB99C33911AB678415A055AFA5B8AAF4F849D4`.
- Fixed populations: `TRUE_0050=1229`, `SHIFTED_0025=1220`. Every source row must map exactly once and later produce exactly one trade. No drop, filter, replacement, re-selection, or signal-time mutation is permitted.
- DESIGN manifest/receipt SHA256: `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`, `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Public M1 source SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Collection plan/custodian SHA256: `F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382`, `5F575BD261F556AFBE11ECB740450DA75FAC3FBFEF1666084452D9E031BF3D8C`.
- Canonical DSR SHA256: `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`.

Every opened public DESIGN parquet shard keeps the exact HYP004 boundary: public DESIGN containment, exact manifest path/date/SHA/bytes/rows, one row group, exact ordered Arrow schema and no metadata, reviewed naive-Arrow UTC attachment without wall-clock shift, and strict JSONL/CSV/generic timestamp paths. No validation, holdout, or private data is authorized.

## 3. Timestamp-only market index and all-or-nothing mapping

Build one immutable index by streaming the already loaded `m1_by_time.values()` in its existing chronological order. The builder must reject a duplicate or any timestamp `<=` its predecessor; it must not sort away producer-order faults. It must not construct a second full M1 dictionary or a full candidate-start set. It may retain compact tuples of existing row references/timestamps, UTC-aligned observed entry timestamps, and complete-M5 start timestamps for binary search.

A complete observed M5 bar is a UTC-aligned bin whose start minute is divisible by five and whose five observed M1 timestamps are exactly offsets `0,1,2,3,4`. Incomplete bins are not synthesized, filled, or counted. Gaps between complete bars are permitted.

The all-or-nothing mapper uses timestamps only; it does not inspect open/high/low/close or calculate a return:

1. `planned_entry_time_utc` is the unchanged HYP002 availability timestamp.
2. Entry candidate is the first observed UTC-aligned M1 row at or after planned availability (`minute % 5 == 0`). Missing future rows at offsets `+1..+4` never changes or re-selects this entry.
3. Entry delay is `entry_time - planned_entry_time`. Negative delay, no aligned observed row, or delay greater than 60 calendar minutes is engineering-invalid. Exactly 60 minutes is accepted.
4. The exit clock is the first twelve complete observed M5 bars whose starts are `>= entry_time`. The entry bin counts only if it later proves complete. An incomplete entry bin remains part of stop surveillance but does not advance the twelve-bar exit clock.
5. Fewer than twelve complete bars is right-censored and engineering-invalid. Otherwise mapped exit-clock time is `twelfth_complete_bar_start + 5 minutes`.
6. All 1,229 TRUE and 1,220 SHIFTED signals must complete this mapping before any trade price, stop outcome, DSR, gate, or performance calculation is invoked. One mapping failure terminates `ENGINEERING_INVALID_NO_MARKET_VERDICT`; no signal is silently omitted and no economics success artifact is written.

## 4. Frozen broker-observed M1 execution proxy

Only after every signal is mapped may the evaluator inspect price values and simulate outcomes. This is a broker-observed M1 proxy, `UNVERIFIED_PROXY_KILL_ONLY`; it is not tick-exact and cannot by itself support promotion.

For each mapped signal:

1. Entry time is the mapped aligned M1 timestamp; entry BID is that observed row's open.
2. Stop distance remains exactly `atr20_pips * 0.0001`. Long stop is entry minus distance; short stop is entry plus distance. No TP, trailing, breakeven, partial, spread-field use, or discretionary exit is added.
3. Stop surveillance examines every observed M1 row with timestamp from entry inclusive through the last minute of the twelfth complete exit bar inclusive. Rows in incomplete M5 bins are never skipped. Missing intervals mean no broker observation and are never synthesized.
4. For the first observed row after any timestamp gap greater than one minute: LONG with `open <= stop` exits at the observed open; SHORT with `open >= stop` exits at the observed open. Gap-open precedence is adverse, so `gross_R` may be less than `-1`. The exit timestamp is that M1 row's start.
5. Otherwise a LONG row with `low <= stop` or SHORT row with `high >= stop` exits at the exact stop with adverse precedence. Because tick order inside M1 is unknown, the conservative recorded exit timestamp is that row's close (`row_start + 1 minute`).
6. If no stop occurs, exit BID is the close of the fifth M1 row in the twelfth complete bar, at `twelfth_complete_bar_start + 5 minutes`.
7. `gross_R = direction_sign * (exit_bid-entry_bid)/stop_distance`, except an exact stop touch is fixed at `-1`. Planned-entry year remains the frozen yearly bucket.
8. At most one position per arm remains mandatory using actual mapped entry and simulated exit times; equality at prior exit is allowed, strict overlap is engineering-invalid.

## 5. Frozen economics and verdicts

- DESIGN years: 2016-2020; elapsed weeks: `260.5714285714`.
- Round-trip costs: exactly `1.50`, `2.25`, `3.00` pips, `UNVERIFIED_PROXY_KILL_ONLY`.
- `cost_R = cost_pips / atr20_pips`; `net_R = gross_R - cost_R`.
- Drawdown and risk fraction remain chronological TRUE 1.50-pip net-R with `equity *= 1 + 0.0025 * net_R`.
- DSR remains TRUE and SHIFTED as exactly two trials, `n_trials=2`, `n_obs=1229`; cost tiers are not trials.

The eleven HYP004/V1 gates remain unchanged: cadence 2-5/week; TRUE PF thresholds `>1.30`, `>=1.25`, `>=1.00`; TRUE mean net R `>=0.08`; TRUE total net R `>0`; at least four positive DESIGN years; max DD `<=6%`; DSR `>=0.95`; TRUE-minus-SHIFTED PF `>=0.15`; TRUE-minus-SHIFTED mean net R `>=0.05`.

- Engineering-valid and all gates pass: `PASS_DESIGN_ECONOMICS_MAY_BUILD_EA` (DESIGN survivor only).
- Engineering-valid but any gate fails: `KILL_DESIGN_ECONOMICS_NO_EDGE`; no same-ID post-hoc rescue.
- Any input, order, mapping, completeness, population, overlap, or authority failure: `ENGINEERING_INVALID_NO_MARKET_VERDICT`; no economic claim.

## 6. One-use authority and prohibitions

- Plan: `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-005_DESIGN_ECONOMICS_PLAN_V2.md`.
- Evaluator: `03. EA Developer/EA_RoundNumberCascade/research/evaluate_round_cascade_005_design_economics.py`.
- Tests: `03. EA Developer/EA_RoundNumberCascade/research/tests/test_evaluate_round_cascade_005_design_economics.py`.
- Run packet: `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-005_DESIGN_ECONOMICS_RUN_PACKET.json`.
- Attempt ID/evidence root: `HYP005-DESIGN-ECON-001` / `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-005_DESIGN_ECONOMICS/HYP005-DESIGN-ECON-001`.
- Attempt limit is one. Evidence root must be absent and created atomically. No reuse, overwrite, deletion, or same-ID rerun.
- V2 grants no authority by itself. Independent review receipt, reviewed evaluator/test hashes, exact run packet, latest registry authority row, and armed sentinel must bind one another before execution.
- Forbidden: validation, holdout, private custody, monolithic source, MQL5, MT5, Model 0/4, optimization, network, paid calls, promotion, paper trading, and live trading.
