# DESIGN ECONOMICS PLAN — HYP-ROUND-CASCADE-EURUSD-M5-003

Status: FROZEN 2026-07-28 after HYP002 source-feasibility PASS and before any HYP003 post-entry OHLC read, return, trade, PnL, performance metric, `.mq5`, MT5, validation, holdout, optimization, network or paid request.

This is the DESIGN-economics child of `HYP-ROUND-CASCADE-EURUSD-M5-002`. It preserves the original HYP001/HYP002 mechanism, source split, signal ledger, stop, horizon, cost stresses and true-versus-shifted comparison. It is not a post-hoc rescue. Any later rule change requires a new hypothesis ID.

## 1. Identity and authority boundary

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-003`
- `parent_candidate`: `HYP-ROUND-CASCADE-EURUSD-M5-002`
- `ea_name`: `EA_RoundNumberCascade`
- Symbol / decision timeframe: EURUSD M5 from immutable public DESIGN M1 BID bars.
- Thesis: stops clustered near absolute `00/50` levels may cause a short-lived continuation cascade after a completed-bar crossing.
- Mandatory control: identical rule on the shifted 25-pip lattice.
- Current plan grants no run authority by itself. Exactly one DESIGN-economics attempt may run only after a reviewed evaluator, reviewed tests, a frozen run packet and a registry authority row are hash-bound.
- Forbidden: validation, holdout, private custody, monolithic source, `.mq5`, MT5, Model 0/4, optimization, network, paid calls, promotion, paper or live trading.

## 2. Frozen inputs

- HYP002 source ledger: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl`
- Ledger SHA256: `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`
- Source report SHA256: `E6AEE8603A922FB87497843A9302D8D24C90E000B154E61264EB8A290B3492D0`
- Source receipt SHA256: `C52A47071F10E6DFE1EAEB8C2AAC899ED4B7C915E71AB932193A57130CBAF23A`
- Source terminal SHA256: `2B2BD6F91EC77FCA824DF96AC6FB99C33911AB678415A055AFA5B8AAF4F849D4`
- Expected raw signals: `TRUE_0050=1229`, `SHIFTED_0025=1220`; every row must be consumed exactly once and no row may be reselected.
- DESIGN manifest: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
- DESIGN manifest SHA256: `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
- DESIGN receipt SHA256: `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`
- Public M1 source SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- DESIGN years: 2016–2020; elapsed calendar weeks: `260.5714285714`.
- Canonical DSR tool: `02. AlphaFactory/tools/research/dsr.py`, SHA256 `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`.

## 3. Exact path simulation

For each arm independently, sort the frozen HYP002 rows by `planned_entry_time_utc`. There is at most one open trade per arm. Any later signal strictly before the prior exit timestamp is an engineering-invalid overlap; equality is allowed. No signal is dropped, delayed or replaced.

For every signal:

1. Rebuild twelve complete, contiguous, UTC-aligned M5 bars from DESIGN M1 beginning exactly at `planned_entry_time_utc`. Each M5 bar requires offsets 0..4 with no missing, duplicate, fill, interpolation or partial bin. Entry bar plus the next eleven bars are mandatory.
2. Any missing/duplicate/non-contiguous required minute or any mismatch with the bound manifest/shard hash makes the entire attempt `ENGINEERING_INVALID_NO_MARKET_VERDICT`; selective exclusion is forbidden.
3. Entry BID is the open of the first projected M5 bar. Direction and `atr20_pips` come unchanged from the HYP002 ledger. Initial stop distance is exactly `atr20_pips * 0.0001`; long stop is entry minus distance and short stop is entry plus distance.
4. No TP, breakeven, trailing, partial, spread-field use or discretionary exit.
5. Inspect the twelve projected M5 bars in order. A long stops if `low <= stop`; a short stops if `high >= stop`. Stop touch has adverse precedence, including the twelfth bar, and exits at the exact stop for `gross_R=-1`.
6. If no stop touches, exit at the BID close of the twelfth M5 bar. `gross_R = direction_sign * (exit_bid - entry_bid) / stop_distance`, where long is `+1` and short is `-1`.
7. Exit timestamp is the end of the first stop-touch M5 bar or, for a time exit, `planned_entry_time_utc + 60 minutes`.

Exactly 1,229 TRUE and 1,220 SHIFTED trades must be produced. Any count change is engineering-invalid, not an economic result.

## 4. Costs, metrics and DSR semantics

- Round-trip cost stresses are exactly `1.50`, `2.25`, and `3.00` pips, status `UNVERIFIED_PROXY_KILL_ONLY`.
- `cost_R = round_trip_cost_pips / atr20_pips`; `net_R = gross_R - cost_R`.
- Profit factor uses positive net-R gains divided by absolute negative net-R losses. Status is `FINITE` when loss is positive, `NO_LOSS` with null value when gain is positive and loss is zero, and `NO_WIN_NO_LOSS` with null value when both are zero. `NO_LOSS` passes an absolute PF gate; `NO_WIN_NO_LOSS` fails. Relative PF uses explicit finite/positive-infinity/negative-infinity/undefined statuses; undefined and negative cases fail.
- Mean and total are arithmetic over every arm trade at the stated cost tier. Year totals use the fixed denominator `[2016,2017,2018,2019,2020]`; zero is not positive.
- Cadence is trade count divided by `260.5714285714`, never active weeks.
- Drawdown uses chronological TRUE 1.50-pip net-R with equity starting at 1.0 and `equity *= 1 + 0.0025 * net_R`; max peak-to-trough drawdown is reported in percent. A non-positive equity factor is engineering-invalid.
- DSR uses per-trade 1.50-pip net-R arrays. TRUE and SHIFTED are exactly two executed trials; cost tiers are not extra trials. Per-arm Sharpe is mean divided by sample standard deviation (`ddof=1`; zero deviation gives Sharpe 0). Trial variance is the sample variance of the two arm Sharpes. TRUE population skew and non-excess kurtosis feed the canonical DSR function with `n_trials=2` and `n_obs=1229`. A non-finite or out-of-range DSR is engineering-invalid.

## 5. Frozen gates

All eleven gates must pass:

| Gate | Threshold |
|---|---:|
| TRUE cadence | `2.0 <= x <= 5.0` per elapsed week |
| TRUE PF at 1.50 pips | `> 1.30` |
| TRUE PF at 2.25 pips | `>= 1.25` |
| TRUE PF at 3.00 pips | `>= 1.00` |
| TRUE mean net R at 1.50 pips | `>= 0.08` |
| TRUE total net R at 1.50 pips | `> 0` |
| TRUE positive DESIGN years at 1.50 pips | `>= 4 of 5` |
| TRUE max compounding DD at 0.25% risk, 1.50 pips | `<= 6.0%` |
| TRUE DSR at 1.50 pips across two trials | `>= 0.95` |
| TRUE PF minus SHIFTED PF at 1.50 pips | `>= 0.15` |
| TRUE mean net R minus SHIFTED mean net R at 1.50 pips | `>= 0.05` |

Verdicts:

- All engineering invariants and all eleven gates pass: `PASS_DESIGN_ECONOMICS_MAY_BUILD_EA` — DESIGN-only survivor; still not validation, deploy or live ready.
- Engineering valid but any economic gate fails: `KILL_DESIGN_ECONOMICS_NO_EDGE` for this exact object. No same-ID rescue by session, weekday, year, direction, threshold, lattice, stop, horizon, cost, symbol or timeframe.
- Any hash/schema/sealed-field/path/completeness/count/overlap failure: `ENGINEERING_INVALID_NO_MARKET_VERDICT`.

## 6. Required artifacts and one-use lifecycle

- Evaluator: `03. EA Developer/EA_RoundNumberCascade/research/evaluate_round_cascade_003_design_economics.py`
- Tests: `03. EA Developer/EA_RoundNumberCascade/research/tests/test_evaluate_round_cascade_003_design_economics.py`
- Run packet: `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-003_DESIGN_ECONOMICS_RUN_PACKET.json`
- Attempt ID: `HYP003-DESIGN-ECON-001`
- Create-new evidence root: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-003_DESIGN_ECONOMICS/HYP003-DESIGN-ECON-001`
- Required artifacts: `attempt_started.json`, `design_economics_trade_ledger.jsonl`, `design_arm_cost_metrics.json`, `design_yearly_metrics.json`, `design_drawdown_metrics.json`, `design_dsr_inputs.json`, `design_gate_report.json`, `design_economics_receipt.json`, `attempt_terminal.json`.
- The attempt limit is one. The evidence root must be absent before authority and created atomically. Any existing root blocks execution; no overwrite/reuse.
