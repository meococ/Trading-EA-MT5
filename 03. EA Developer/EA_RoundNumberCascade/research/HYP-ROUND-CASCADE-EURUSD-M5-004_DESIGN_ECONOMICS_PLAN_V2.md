# DESIGN ECONOMICS ENGINEERING-REPAIR PLAN V2 - HYP-ROUND-CASCADE-EURUSD-M5-004

Status: FROZEN PRE-OUTCOME on 2026-07-28. This V2 supersedes the unregistered V1 plan before any HYP004 post-entry shard read, trade simulation, return, PnL, performance metric, MQL5 file, MT5 launch, validation/holdout access, network call, or paid request. V2 narrows and makes executable the parquet timestamp contract; it does not change the market mechanism or any economic rule.

## 1. Identity and failure radius

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-004`
- `parent_candidate`: `HYP-ROUND-CASCADE-EURUSD-M5-003`
- `source_signal_hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-002`
- `ea_name`: `EA_RoundNumberCascade`
- Symbol / decision timeframe: EURUSD M5 from immutable public DESIGN M1 BID bars.
- HYP003 consumed its one authorized attempt and stopped `ENGINEERING_INVALID_NO_MARKET_VERDICT` before any signal-window projection, trade, or economic metric because its generic timestamp parser rejected the producer's intentionally timezone-naive Arrow `time_utc` values.
- Parent started path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-003_DESIGN_ECONOMICS/HYP003-DESIGN-ECON-001/attempt_started.json` / `5756A85BDEDDC64289187CFB07FF918C197DD38AFF8B965B8B92332E5A3F6A22`.
- Parent terminal path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-003_DESIGN_ECONOMICS/HYP003-DESIGN-ECON-001/attempt_terminal.json` / `2A7780D984AC7626C14E0D95560C71E323CBD0083D569CD0141748C7EB149A22`.
- HYP004 changes only the exact public splitvault parquet decoder. Signal identity, true/placebo lattices, ATR, entry, stop, horizon, costs, cadence denominator, DSR semantics, gates, verdicts, and all sealed authorities are unchanged.

## 2. Frozen source and producer contract

- HYP002 source ledger path/SHA: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl` / `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`.
- HYP002 source report/receipt/terminal SHA256: `E6AEE8603A922FB87497843A9302D8D24C90E000B154E61264EB8A290B3492D0`, `C52A47071F10E6DFE1EAEB8C2AAC899ED4B7C915E71AB932193A57130CBAF23A`, `2B2BD6F91EC77FCA824DF96AC6FB99C33911AB678415A055AFA5B8AAF4F849D4`.
- Expected signals: `TRUE_0050=1229`, `SHIFTED_0025=1220`; every row is consumed exactly once. No drop, delay, replacement, or re-selection.
- DESIGN manifest path/SHA: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl` / `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`.
- DESIGN receipt path/SHA: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json` / `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Public M1 source SHA: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Collection plan path/SHA: `03. EA Developer/EA_TrendStackContinuation/research/DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002_PLAN.md` / `F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382`.
- Custodian producer path/SHA: `03. EA Developer/EA_TrendStackContinuation/research/splitvault_002_custodian.py` / `5F575BD261F556AFBE11ECB740450DA75FAC3FBFEF1666084452D9E031BF3D8C`.
- Canonical DSR path/SHA: `02. AlphaFactory/tools/research/dsr.py` / `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`.

The exact full Arrow schema required for every opened public DESIGN shard is, in order and with no timezone metadata:

1. `time_server: timestamp[ns]`
2. `time_utc: timestamp[ns]`
3. `utc_offset_h: int8`
4. `open: double`
5. `high: double`
6. `low: double`
7. `close: double`
8. `tick_volume: uint64`
9. `spread: int32`
10. `real_volume: uint64`

Each opened parquet shard must have exactly one row group. Any schema order/type/time-unit/timezone/metadata drift, extra or missing field, or row-group mismatch is `ENGINEERING_INVALID_NO_MARKET_VERDICT`.

## 3. Exact timestamp repair

1. The generic `parse_utc` remains strict: every naive datetime or string is rejected.
2. `validate_m1_row` remains strict and never infers UTC.
3. JSONL and CSV M1 branches remain strict; naive timestamps in them are rejected.
4. Only after a parquet payload has passed the exact manifest SHA/byte count, exact full Arrow schema, one-row-group check, and public `DESIGN` path containment may its naive `time_utc` value be converted with `value.replace(tzinfo=timezone.utc)`.
5. The conversion attaches UTC without changing the wall-clock fields. `astimezone()` on a naive value is forbidden. A timezone-aware parquet timestamp, a non-`ns` unit, or any non-datetime value is rejected.
6. The normalized row then passes the same strict `validate_m1_row` OHLC/timestamp checks as every other row.
7. Tests must demonstrate that `2016-01-05 00:00:00` becomes exactly `2016-01-05T00:00:00Z`, JSONL/CSV/signal naive inputs still fail, aware/wrong-unit/schema-drift parquet fails, and aware-vs-repaired-naive price simulation is identical.

## 4. Frozen path simulation

For each arm independently, sort the HYP002 ledger by `planned_entry_time_utc`. At most one trade may be open per arm; a later signal strictly before the prior exit is engineering-invalid and equality is allowed.

For every signal:

1. Rebuild exactly twelve complete contiguous UTC-aligned M5 bars from the 60 manifest-bound DESIGN M1 minutes beginning at `planned_entry_time_utc`.
2. Entry BID is the first projected M5 open.
3. Stop distance is exactly `atr20_pips * 0.0001`; long stop is entry minus distance and short stop is entry plus distance.
4. No TP, breakeven, trailing, partial, spread-field use, discretionary exit, or parameter change.
5. Inspect bars in order. Long stops when `low <= stop`; short stops when `high >= stop`. Stop touch has adverse precedence, including the twelfth bar, and returns exact `gross_R=-1`.
6. Otherwise exit at the twelfth M5 BID close at `planned_entry_time_utc + 60 minutes`; `gross_R = direction_sign * (exit_bid-entry_bid)/stop_distance`.
7. Exactly 1,229 TRUE and 1,220 SHIFTED trades must result. Any count/completeness/overlap failure is engineering-invalid, not an economic verdict.

## 5. Costs, metrics, and all-or-nothing gates

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

- All engineering invariants and all gates pass: `PASS_DESIGN_ECONOMICS_MAY_BUILD_EA` (DESIGN survivor only).
- Engineering valid but any gate fails: `KILL_DESIGN_ECONOMICS_NO_EDGE` for this exact object; no same-ID rescue by session, weekday, year, direction, threshold, lattice, stop, horizon, cost, symbol, or timeframe.
- Any engineering invariant fails: `ENGINEERING_INVALID_NO_MARKET_VERDICT`.

## 6. One-use authority and artifacts

- Evaluator: `03. EA Developer/EA_RoundNumberCascade/research/evaluate_round_cascade_004_design_economics.py`.
- Tests: `03. EA Developer/EA_RoundNumberCascade/research/tests/test_evaluate_round_cascade_004_design_economics.py`.
- Run packet: `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS_RUN_PACKET.json`.
- Attempt ID: `HYP004-DESIGN-ECON-001`.
- Fresh evidence root: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS/HYP004-DESIGN-ECON-001`.
- Required success artifacts: `attempt_started.json`, `design_economics_trade_ledger.jsonl`, `design_arm_cost_metrics.json`, `design_yearly_metrics.json`, `design_drawdown_metrics.json`, `design_dsr_inputs.json`, `design_gate_report.json`, `design_economics_receipt.json`, `attempt_terminal.json`.
- The attempt limit is one. Evidence root must be absent before authority and created atomically. No overwrite, deletion, reuse, or same-ID rerun.
- Plan alone grants no run authority. A reviewed evaluator/test hash pair, independent review receipt, exact run packet, and latest registry authority row must bind one another before the sentinel is armed.
- Forbidden throughout HYP004: validation, holdout, private custody, monolithic source, MQL5, MT5, Model 0/4, optimization, network, paid calls, promotion, paper trading, and live trading.
