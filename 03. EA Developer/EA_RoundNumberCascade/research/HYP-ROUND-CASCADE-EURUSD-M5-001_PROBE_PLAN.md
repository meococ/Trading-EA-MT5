# PROBE PLAN — HYP-ROUND-CASCADE-EURUSD-M5-001

Status: FROZEN 2026-07-28, before any source scan, trade outcome, PnL, validation, holdout, `.mq5`, MT5 or optimization run for this object.

This plan is immutable after its SHA256 is bound into `04. Memory/research/CANDIDATE_REGISTRY.jsonl`. Any pre-outcome amendment must become `_V2.md` and be bound in a later transition. A post-outcome change is a new `hypothesis_id`.

## 1. Identity

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-001`
- `ea_name`: `EA_RoundNumberCascade`
- Current authority: research-only source probe. No `.mq5`, compile, MT5, Model 0, Model 4, validation, holdout, promotion, paper or live authority.
- Symbol / timeframe: EURUSD M5 decisions built from immutable public DESIGN EURUSD M1 BID bars.
- Thesis: stop-loss orders cluster near round numbers and can create short-lived positive-feedback cascades after price crosses `00/50` EURUSD levels.
- Primary sources:
  - NY Fed Staff Report 125, `Currency Orders and Exchange-Rate Dynamics`, reports round-number clustering and that stop-loss orders tend to intensify trends: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf
  - NY Fed Staff Report 150, `Stop-Loss Orders and Price Cascades in Currency Markets`, studies rapid self-reinforcing currency price movements from stop-loss orders: https://www.newyorkfed.org/research/staff_reports/sr150.html

## 2. De-dup / failure radius

- Not TrendStack HYP007: this object does not use M252/M6, H1 12:00 one-bar horizon, trend-stack polarity, or the HYP007 stop proxy.
- Not EventVolOCO HYP001: this object does not use a scheduled news clock, OCO pending orders, matched event controls, or ForexFactory rank-C source.
- Not SweepCascadeContinuation: this object does not require fractal pivot break/hold/retest; the trigger is an exogenous absolute price lattice.
- Not ICT/FVG or fakeout/rejection family: no FVG, OB, premium/discount, pivot dwell, sweep-reclaim, or close-back-inside rejection is used.
- Adverse prior: round-number and OHLC-only ideas have failed in adjacent symbols/settings. This candidate is allowed only because EURUSD `00/50` stop-cascade vs shifted-placebo is a materially different source/control object with primary market-microstructure prior.

## 3. Data and split

- Source root: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public`
- DESIGN manifest: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
- DESIGN manifest SHA256: `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
- DESIGN receipt: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json`
- DESIGN receipt SHA256: `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`
- Public M1 source SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- DESIGN window: 2016-01-04 through 2020-12-31, elapsed 260.571428571 weeks.
- Validation/holdout: SEALED. The source scanner must not open validation or holdout directories, raw private custody, or the 2015-now monolithic parquet.
- Known unusable cost source: historical `spread` field is not trusted as true cost; later economics must use stress costs.

## 4. Frozen source-only decision surface

- Aggregate only complete, contiguous, UTC-aligned five-minute M1 groups into M5 bars. No fill, interpolation, dedup, or partial-bin use.
- `pip = 0.0001`.
- True lattice: `L = k * 0.0050`, representing EURUSD `00/50`.
- Shifted placebo lattice: `L_control = 0.0025 + k * 0.0050`.
- Long signal on a completed M5 bar:
  - previous completed M5 close `< L`;
  - current completed M5 close is in `[L + 1 pip, L + 10 pips]`.
- Short signal is the mirror:
  - previous completed M5 close `> L`;
  - current completed M5 close is in `[L - 10 pips, L - 1 pip]`.
- Enter on the next M5 open later, if the source gate survives. Stage-0 may emit only the planned entry timestamp, not entry/open price.
- Stop geometry for feasibility only: H1 ATR20, MT5-style SMA of True Range, shifted one completed H1 bar before the decision bar. Initial stop distance = `1.0 * ATR20`.
- Future economic exit, if later authorized: no TP, BE, trailing or partial; time exit 12 completed M5 bars / 60 minutes; one open trade max; 0.25% risk/trade; 6% DD ceiling.
- Stage-0 signal throttling: for each arm (`TRUE_0050`, `SHIFTED_0025`) keep only the first eligible signal per UTC date.

## 5. Source-only gates

All gates are required for Stage-0 PASS:

| Gate | Threshold |
|---|---:|
| DESIGN manifest and receipt SHA match | exact |
| Validation/holdout/private paths opened | 0 |
| Post-entry OHLC/returns/PnL/trades emitted | 0 |
| M5 complete-bin ratio | >= 0.99 |
| TRUE signal cadence | 2.0 to 5.0 per elapsed week |
| SHIFTED signal cadence | 2.0 to 5.0 per elapsed week |
| TRUE long share and short share | each >= 0.25 |
| SHIFTED long share and short share | each >= 0.25 |
| TRUE max single-year share | <= 0.30 |
| SHIFTED max single-year share | <= 0.30 |
| TRUE median `1.5 pip / stop_pips` | <= 0.25 |
| SHIFTED median `1.5 pip / stop_pips` | <= 0.25 |

Any failure is `PARK_SOURCE_FEASIBILITY_FAILED` or `KILL_SOURCE_GATE_FAILED` for this exact source/control object. Do not rescue by changing session, weekday, year, direction, threshold, lattice offset, stop multiple, time horizon, cost assumption, symbol or timeframe under this ID.

## 6. Later economics contract, if source gate passes

Later DESIGN economics require a separate frozen run packet and registry transition before any outcome read:

- Arms/trials: `TRUE_0050` and `SHIFTED_0025`; both count in DSR/trial accounting.
- Round-trip cost stress: 1.50 / 2.25 / 3.00 pips, explicitly `UNVERIFIED_PROXY`.
- Required for TRUE arm: PF at 1.50 pips `> 1.30`, PF at 2.25 pips `>= 1.25`, PF at 3.00 pips `>= 1.00`, mean net R at 1.50 pips `>= 0.08`, total net R `> 0`, positive years at least 4 of 5, DSR `>= 0.95`.
- Required relative edge vs shifted placebo at 1.50 pips: `delta_pf >= 0.15` and `delta_mean_r >= 0.05`.
- Failure of either absolute or placebo-relative economics is terminal for this exact object.

## 7. Artifacts

- Source scanner: `03. EA Developer/EA_RoundNumberCascade/research/build_round_cascade_001_source.py`
- Tests: `03. EA Developer/EA_RoundNumberCascade/research/tests/test_build_round_cascade_001_source.py`
- Source evidence root: `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-001_SOURCE_FEASIBILITY/HYP001-SOURCE-PREFLIGHT-001`
- Required source artifacts: `attempt_started.json`, `round_cascade_source_report.json`, `round_cascade_source_ledger.jsonl`, `source_feasibility_receipt.json`, `attempt_terminal.json`.
- Registry: one pre-run probe row with this plan SHA; one terminal/pass row after source scan.
- Closeout: update `04. Memory/hot.md`; update `04. Memory/do_not_repeat_failures.md` only if source/economic gate terminally parks/kills the object.
