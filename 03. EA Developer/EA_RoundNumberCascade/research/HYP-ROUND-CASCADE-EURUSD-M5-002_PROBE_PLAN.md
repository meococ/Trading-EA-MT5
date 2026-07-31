# PROBE PLAN — HYP-ROUND-CASCADE-EURUSD-M5-002

Status: FROZEN 2026-07-28 after the engineering-invalid HYP001 source attempt and before any HYP002 source shard read, signal report, trade outcome, PnL, validation, holdout, `.mq5`, MT5, optimization or economic run.

This is a child engineering repair of `HYP-ROUND-CASCADE-EURUSD-M5-001`, not a post-hoc signal rescue. HYP001 produced only `attempt_started.json` and an engineering-failure terminal; it emitted no signal ledger/report, return, trade or economic result. This plan may not change the mechanism, gates, symbol, timeframe, direction rules, lattice, ATR, session, year, horizon or cost contract.

## 1. Identity and authority

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-002`
- `parent_candidate`: `HYP-ROUND-CASCADE-EURUSD-M5-001`
- `ea_name`: `EA_RoundNumberCascade`
- Symbol/timeframe: EURUSD M5 decisions from immutable public DESIGN EURUSD M1 BID bars.
- Authority: exactly one outcome-blind source-feasibility attempt after independent implementation review. No economics, validation, holdout, private custody, network, paid call, `.mq5`, MT5, Model 0/4, optimization, promotion, paper or live authority.
- Primary mechanism prior remains NY Fed Staff Reports 125 and 150: stop-loss orders cluster near round numbers and may create short-lived positive-feedback cascades after price crosses `00/50` levels.

## 2. Frozen data contract

- Source root: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public`
- DESIGN manifest SHA256: `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
- DESIGN receipt SHA256: `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`
- Public M1 source SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- DESIGN: 2016-01-04 through 2020-12-31; elapsed 260.571428571 weeks.
- Validation/holdout/private/monolithic source remain sealed.

### Only authorized engineering repair

Parquet stores price as binary floating point, so a legal 5-digit quote such as `1.08187` can decode as `1.0818699999999999`. Convert price to quote points by selecting the nearest integer only when the distance is at most `0.000001` quote points, equivalent to `0.00000000001` price. A larger deviation is fatal. Thus `1.0818699999999999` is the same legal 5-digit quote, while an actual half-point input such as `1.100095` remains rejected. No signal boundary is widened.

## 3. Frozen decision surface

- Aggregate only complete, contiguous, UTC-aligned M1 offsets 0..4 into M5 bars. No fill, interpolation, dedup or partial bin.
- `pip=0.0001`; true lattice `L=k*0.0050`; placebo lattice `L=0.0025+k*0.0050`.
- Long: previous completed M5 close `< L` and current completed close in `[L+1 pip,L+10 pips]`. Short is the exact mirror.
- Completed bar bucket is `decision_bar_start_utc`; signal availability and planned next-open entry timestamp are bucket +5 minutes. Keep first eligible signal per availability UTC date per arm.
- Stop feasibility: H1 ATR20, MT5-style SMA(True Range), shift one completed H1 bar relative to decision-bar start; calendar gaps allowed. Stop distance `1.0*ATR20`.
- Stage-0 may emit only signal-as-of fields and planned entry timestamp, never post-entry price/OHLC, return, trade, PnL or performance.

## 4. Source-only gates

All are required: exact authority hashes; forbidden access/outcome counters zero; M5 complete-bin ratio `>=0.99`; per-arm cadence `2.0..5.0` per elapsed week; per-arm long and short share each `>=0.25`; per-arm max single-year share `<=0.30`; per-arm median `1.5 pip / stop_pips <=0.25`. ATR-completeness and raw count may be reported only as diagnostics, not extra gates.

Failure is `PARK_SOURCE_FEASIBILITY_FAILED` for this exact source/control object. Do not rescue by changing session, weekday, year, direction, threshold, lattice offset, stop, horizon, cost, symbol or timeframe.

## 5. Later economics only if source PASS

A separate frozen packet/registry transition is required. TRUE and SHIFTED are both DSR trials. Cost stress: 1.50/2.25/3.00 pips. TRUE requires PF `>1.30 / >=1.25 / >=1.00`, mean net R at 1.50 pips `>=0.08`, total net R `>0`, at least 4/5 positive years, DSR `>=0.95`; relative to placebo at 1.50 pips require `delta_pf>=0.15` and `delta_mean_r>=0.05`. No later authority is granted by this plan.

## 6. Artifacts

- Builder: `03. EA Developer/EA_RoundNumberCascade/research/build_round_cascade_002_source.py`
- Tests: `03. EA Developer/EA_RoundNumberCascade/research/tests/test_build_round_cascade_002_source.py`
- Attempt: `HYP002-SOURCE-PREFLIGHT-001`
- Evidence root: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001`
- Required create-new artifacts: `attempt_started.json`, `round_cascade_source_report.json`, `round_cascade_source_ledger.jsonl`, `source_feasibility_receipt.json`, `attempt_terminal.json`.
