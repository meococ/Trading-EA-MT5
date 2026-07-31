# DESIGN ECONOMICS REPAIR PLAN — HYP-ROUND-CASCADE-EURUSD-M5-004

Status: FROZEN before any HYP004 post-entry OHLC completion, trade simulation, return, PnL, performance metric, `.mq5`, MT5, validation, holdout, optimization, network or paid request.

This is a narrow engineering-repair child of `HYP-ROUND-CASCADE-EURUSD-M5-003`. HYP003 consumed its single authorized attempt and stopped `ENGINEERING_INVALID_NO_MARKET_VERDICT` before economic metrics because the public DESIGN parquet `time_utc` column was materialized by pyarrow as timezone-naive pandas timestamps. HYP004 freezes the documented decoding rule for that dataset field only.

## 1. Identity and authority boundary

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-004`
- `parent_candidate`: `HYP-ROUND-CASCADE-EURUSD-M5-003`
- `ea_name`: `EA_RoundNumberCascade`
- Symbol / decision timeframe: EURUSD M5 from immutable public DESIGN M1 BID bars.
- Thesis, signal identity, true lattice, shifted placebo lattice, ATR source, stop, horizon, costs, cadence denominator, DSR and all gates are unchanged from HYP003.
- Repair delta: a parquet M1 `time_utc` value with no timezone is interpreted as UTC only when it is read from the hash-bound public splitvault_002 DESIGN M1 shards. Source signal ledger timestamps remain strict timezone-aware UTC strings; no other timestamp relaxation is authorized.
- Current plan grants no run authority by itself. Exactly one DESIGN-economics attempt may run only after a reviewed evaluator, reviewed tests, a frozen run packet and a registry authority row are hash-bound.
- Forbidden: validation, holdout, private custody, monolithic source, `.mq5`, MT5, Model 0/4, optimization, network, paid calls, promotion, paper or live trading.

## 2. Frozen inputs

- Parent HYP003 terminal: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-003_DESIGN_ECONOMICS/HYP003-DESIGN-ECON-001/attempt_terminal.json`
- Parent HYP003 terminal verdict: `ENGINEERING_INVALID_NO_MARKET_VERDICT`
- Parent exact failure radius: evaluator decoding of public DESIGN parquet `time_utc` only; failure before any signal-window projection, trade or economic metric.
- HYP002 source ledger: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl`
- HYP002 ledger SHA256: `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`
- Expected raw signals: `TRUE_0050=1229`, `SHIFTED_0025=1220`; every row must be consumed exactly once and no row may be reselected.
- DESIGN manifest: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
- DESIGN manifest SHA256: `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
- DESIGN receipt SHA256: `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`
- Public M1 source SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- DESIGN years: 2016–2020; elapsed calendar weeks: `260.5714285714`.
- Canonical DSR tool: `02. AlphaFactory/tools/research/dsr.py`, SHA256 `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`.

## 3. Exact path simulation

HYP004 uses the exact HYP003 path simulation contract:

1. For each arm independently, sort frozen HYP002 rows by `planned_entry_time_utc`; at most one open trade per arm; no signal drop, delay or replacement.
2. Rebuild twelve complete, contiguous, UTC-aligned M5 bars from DESIGN M1 beginning exactly at `planned_entry_time_utc`; every M5 bar requires offsets 0..4.
3. Entry BID is first M5 open. Stop distance is `atr20_pips * 0.0001`. No TP, breakeven, trailing, partial, spread-field use or discretionary exit.
4. Long stop if `low <= stop`; short stop if `high >= stop`; stop touch has adverse precedence including the twelfth bar.
5. If no stop touches, exit at BID close of the twelfth M5 bar.
6. Exactly 1,229 TRUE and 1,220 SHIFTED trades must be produced. Any count change is engineering-invalid.

## 4. Costs, metrics, DSR and gates

All HYP003 economics remain frozen:

- Cost stresses: `1.50`, `2.25`, `3.00` pips, status `UNVERIFIED_PROXY_KILL_ONLY`.
- Risk fraction for drawdown: `0.0025`.
- DSR: TRUE and SHIFTED are exactly two executed trials; `n_trials=2`; `n_obs=1229`.
- Gates: TRUE cadence 2–5/week; TRUE PF >1.30 at 1.50 pips; TRUE PF >=1.25 at 2.25 pips; TRUE PF >=1.00 at 3.00 pips; TRUE mean net R >=0.08; TRUE total net R >0; >=4/5 positive years; max compounding DD <=6%; DSR >=0.95; TRUE minus SHIFTED PF >=0.15; TRUE minus SHIFTED mean net R >=0.05.

Verdicts:

- All engineering invariants and all eleven gates pass: `PASS_DESIGN_ECONOMICS_MAY_BUILD_EA`.
- Engineering valid but any economic gate fails: `KILL_DESIGN_ECONOMICS_NO_EDGE` for this exact HYP004 object. No same-ID rescue by session, weekday, year, direction, threshold, lattice, stop, horizon, cost, symbol or timeframe.
- Any hash/schema/sealed-field/path/completeness/count/overlap failure: `ENGINEERING_INVALID_NO_MARKET_VERDICT`.

## 5. Required artifacts and one-use lifecycle

- Evaluator: `03. EA Developer/EA_RoundNumberCascade/research/evaluate_round_cascade_004_design_economics.py`
- Tests: `03. EA Developer/EA_RoundNumberCascade/research/tests/test_evaluate_round_cascade_004_design_economics.py`
- Run packet: `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS_RUN_PACKET.json`
- Attempt ID: `HYP004-DESIGN-ECON-001`
- Create-new evidence root: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS/HYP004-DESIGN-ECON-001`
- Required artifacts: `attempt_started.json`, `design_economics_trade_ledger.jsonl`, `design_arm_cost_metrics.json`, `design_yearly_metrics.json`, `design_drawdown_metrics.json`, `design_dsr_inputs.json`, `design_gate_report.json`, `design_economics_receipt.json`, `attempt_terminal.json`.
- The attempt limit is one. The evidence root must be absent before authority and created atomically. Any existing root blocks execution; no overwrite/reuse.
