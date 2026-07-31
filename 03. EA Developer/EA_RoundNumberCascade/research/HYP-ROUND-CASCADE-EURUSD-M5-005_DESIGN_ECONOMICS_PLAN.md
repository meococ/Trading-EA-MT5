# DESIGN ECONOMICS OBSERVED-M5 REPAIR PLAN - HYP-ROUND-CASCADE-EURUSD-M5-005

Status: FROZEN PRE-OUTCOME on 2026-07-29. This is a fresh hypothesis ID for one pre-outcome data/execution-contract repair. HYP004 opened public DESIGN shards but stopped engineering-invalid before it emitted any complete trade population, return, PnL, performance metric, or market verdict. HYP005 does not rescue or tune a market result.

## 1. Identity and failure radius

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-005`
- `parent_candidate`: `HYP-ROUND-CASCADE-EURUSD-M5-004`
- `source_signal_hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-002`
- `ea_name`: `EA_RoundNumberCascade`
- Symbol / decision timeframe: EURUSD M5 from immutable public DESIGN M1 BID bars.
- Parent attempt: `HYP004-DESIGN-ECON-001`.
- Parent started path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS/HYP004-DESIGN-ECON-001/attempt_started.json` / `46ADCB275482CD496D8C6DE6B1803FD735D9EC3E128D93F87540C47FFE80527F`.
- Parent terminal path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS/HYP004-DESIGN-ECON-001/attempt_terminal.json` / `899700298BA910A1FF4D29FD9B4B95144835BB10BF23FAFE537224A957F6AED5`.
- Parent terminal status/reason: `ENGINEERING_INVALID_NO_MARKET_VERDICT` / `missing exact M1 entry window`. Its artifact chain contains only `attempt_started.json`; no trade ledger or metric artifact exists.
- HYP005 changes only the projection contract from sixty contiguous calendar M1 minutes to twelve complete observed UTC-aligned M5 bars. Signal identity, TRUE/placebo lattices, direction, ATR, stop, costs, cadence denominator, DSR semantics, gates, verdicts, and all sealed authorities remain unchanged.

## 2. Frozen source and producer contract

- HYP002 source ledger path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl` / `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`.
- HYP002 source report/receipt/terminal SHA256: `E6AEE8603A922FB87497843A9302D8D24C90E000B154E61264EB8A290B3492D0`, `C52A47071F10E6DFE1EAEB8C2AAC899ED4B7C915E71AB932193A57130CBAF23A`, `2B2BD6F91EC77FCA824DF96AC6FB99C33911AB678415A055AFA5B8AAF4F849D4`.
- Fixed source populations: `TRUE_0050=1229`, `SHIFTED_0025=1220`. Every ledger row must map exactly once and produce exactly one trade. No drop, replacement, re-selection, signal-time shift, or filtering is permitted.
- DESIGN manifest path/SHA: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl` / `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`.
- DESIGN receipt path/SHA: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json` / `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Public M1 source SHA: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Collection plan path/SHA: `03. EA Developer/EA_TrendStackContinuation/research/DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002_PLAN.md` / `F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382`.
- Custodian producer path/SHA: `03. EA Developer/EA_TrendStackContinuation/research/splitvault_002_custodian.py` / `5F575BD261F556AFBE11ECB740450DA75FAC3FBFEF1666084452D9E031BF3D8C`.
- Canonical DSR path/SHA: `02. AlphaFactory/tools/research/dsr.py` / `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`.

Each opened public DESIGN parquet shard must retain the exact HYP004 producer boundary: one row group, exact ordered Arrow schema (`time_server timestamp[ns]`, `time_utc timestamp[ns]`, `utc_offset_h int8`, OHLC `double`, `tick_volume uint64`, `spread int32`, `real_volume uint64`), no schema metadata, exact manifest path/date/SHA/bytes/rows, and the reviewed naive-Arrow-UTC attachment with no wall-clock shift. JSONL/CSV and generic timestamp paths remain strict and never infer UTC.

## 3. Frozen observed-M5 mapping contract

Build the observed market index once, before signal simulation:

1. Validate and sort every opened M1 row by UTC timestamp; duplicates and non-increasing rows are engineering-invalid.
2. A complete observed M5 bar exists only for a UTC-aligned bin whose minute is divisible by five and that has exactly the five M1 timestamps at offsets `0,1,2,3,4`. Its open/high/low/close are first open, maximum high, minimum low, and fifth close.
3. Incomplete bins are excluded from the observed-M5 index. Gaps between otherwise complete M5 bars are allowed. No gap is filled, synthesized, interpolated, or forward-filled.
4. The index and its timestamps are computed once. Signal mapping uses binary search; it must not rescan the full M1 or M5 population per signal.

For each fixed source signal:

1. `planned_entry_time_utc` is the unchanged availability timestamp from the HYP002 ledger.
2. Entry maps to the first complete observed M5 bar whose start is at or after that timestamp.
3. Entry delay is `observed_bar_start - planned_entry_time_utc` in calendar time. Negative delay, delay greater than 60 minutes, or no eligible bar is engineering-invalid.
4. The horizon is exactly twelve complete observed M5 bars by chronological index, including the entry bar. Fewer than twelve remaining bars is right-censored and engineering-invalid.
5. Entry BID is the first observed bar open. A non-stop exit is the twelfth observed bar close at `twelfth_bar_start + 5 minutes`; it is not forced to `planned_entry_time + 60 minutes` when gaps occur.
6. Stop distance is exactly `atr20_pips * 0.0001`; long stop is entry minus distance and short stop is entry plus distance.
7. Inspect all twelve bars in order. Long stops when `low <= stop`; short stops when `high >= stop`. Stop touch keeps adverse precedence, including on the twelfth bar, and returns exact `gross_R=-1`.
8. Otherwise `gross_R = direction_sign * (exit_bid-entry_bid)/stop_distance`.

Mapping is an all-or-nothing engineering gate before economics: exactly 1,229 TRUE and 1,220 SHIFTED signals must map and produce trades. If any signal is delayed more than 60 minutes, has fewer than twelve observed bars, overlaps a prior open trade in its arm, or otherwise fails mapping, the attempt terminates `ENGINEERING_INVALID_NO_MARKET_VERDICT` before `evaluate_gates`, DSR, performance metrics, or any success economics artifact. No signal may be silently dropped even if an aggregate mapping rate would exceed 99%.

## 4. Frozen economics and gates

- DESIGN years: 2016-2020; elapsed calendar weeks: `260.5714285714`.
- Round-trip cost stresses: exactly `1.50`, `2.25`, and `3.00` pips, `UNVERIFIED_PROXY_KILL_ONLY`.
- `cost_R = cost_pips / atr20_pips`; `net_R = gross_R - cost_R`.
- Drawdown: chronological TRUE 1.50-pip net-R, equity starts 1.0, `equity *= 1 + 0.0025 * net_R`.
- DSR: per-trade 1.50-pip net-R, TRUE and SHIFTED are exactly two trials, `n_trials=2`, `n_obs=1229`; cost tiers are not extra trials.

All eleven gates must pass:

1. TRUE cadence `2.0 <= x <= 5.0` per elapsed week.
2. TRUE PF at 1.50 pips `> 1.30`.
3. TRUE PF at 2.25 pips `>= 1.25`.
4. TRUE PF at 3.00 pips `>= 1.00`.
5. TRUE mean net R at 1.50 pips `>= 0.08`.
6. TRUE total net R at 1.50 pips `> 0`.
7. TRUE positive DESIGN years at 1.50 pips `>= 4 of 5`.
8. TRUE max compounding DD `<= 6.0%`.
9. TRUE DSR at 1.50 pips `>= 0.95`.
10. TRUE PF minus SHIFTED PF at 1.50 pips `>= 0.15`.
11. TRUE mean net R minus SHIFTED mean net R at 1.50 pips `>= 0.05`.

Verdicts:

- Engineering-valid and all gates pass: `PASS_DESIGN_ECONOMICS_MAY_BUILD_EA` (DESIGN survivor only).
- Engineering-valid but any gate fails: `KILL_DESIGN_ECONOMICS_NO_EDGE` for this exact object; no same-ID rescue by session, weekday, year, direction, threshold, lattice, stop, horizon, cost, symbol, or timeframe.
- Any engineering/mapping invariant fails: `ENGINEERING_INVALID_NO_MARKET_VERDICT`; no economic claim.

## 5. One-use authority and prohibitions

- Evaluator: `03. EA Developer/EA_RoundNumberCascade/research/evaluate_round_cascade_005_design_economics.py`.
- Tests: `03. EA Developer/EA_RoundNumberCascade/research/tests/test_evaluate_round_cascade_005_design_economics.py`.
- Run packet: `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-005_DESIGN_ECONOMICS_RUN_PACKET.json`.
- Attempt ID: `HYP005-DESIGN-ECON-001`.
- Fresh evidence root: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-005_DESIGN_ECONOMICS/HYP005-DESIGN-ECON-001`.
- Required success artifacts remain: `attempt_started.json`, `design_economics_trade_ledger.jsonl`, `design_arm_cost_metrics.json`, `design_yearly_metrics.json`, `design_drawdown_metrics.json`, `design_dsr_inputs.json`, `design_gate_report.json`, `design_economics_receipt.json`, `attempt_terminal.json`.
- The attempt limit is one. Evidence root must be absent before authority and created atomically. No overwrite, deletion, reuse, or same-ID rerun.
- Plan alone grants no run authority. A reviewed evaluator/test hash pair, independent review receipt, exact run packet, and latest registry authority row must bind one another before the sentinel is armed.
- Forbidden throughout HYP005: validation, holdout, private custody, monolithic source, MQL5, MT5, Model 0/4, optimization, network, paid calls, promotion, paper trading, and live trading.
