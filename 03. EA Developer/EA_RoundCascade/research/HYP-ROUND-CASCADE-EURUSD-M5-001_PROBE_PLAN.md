# PROBE PLAN — HYP-ROUND-CASCADE-EURUSD-M5-001

Status: **FROZEN SOURCE-ONLY STAGE-0 CONTRACT**. Frozen before any source scan, output artifact, economic outcome, MQL5 file, compile, MT5 launch, optimization, validation access, or holdout access for this implementation package.

This file defines a new implementation surface under `EA_RoundCascade`. It grants no run authority by itself. The scanner remains disarmed until the append-only registry contains an independently reviewed source-run authorization whose exact row SHA replaces the explicit `None` sentinel in the scanner. Any change after an outcome is observed requires a new hypothesis ID; any pre-outcome correction requires a versioned plan and a new reviewed registry transition.

## 1. Identity and falsifiable mechanism

- Hypothesis ID: `HYP-ROUND-CASCADE-EURUSD-M5-001`
- Package: `EA_RoundCascade`
- Symbol / decision timeframe: EURUSD M5, aggregated from public DESIGN M1 BID OHLC.
- Mechanism: stop-loss orders may cluster around absolute EURUSD round-number levels and create a short positive-feedback cascade after a completed M5 close crosses the level.
- Falsifier: the absolute `00/50` lattice must first pass source feasibility and, in a later separately authorized economic packet, must outperform the frozen 25-pip-shifted placebo lattice after conservative costs.
- No session, weekday, year, direction, volatility, news, trend, volume, regime, or discretionary filter is permitted.

## 2. De-duplication and failure radius

- Not Sweep Cascade Continuation: no fractal pivot, sweep, hold, retest, or structural price-level discovery is used. This object uses an exogenous absolute price lattice.
- Not XAU GoldRound: the symbol, pip scale, source contract, decision surface, placebo and risk geometry differ; no Gold-specific threshold is reused.
- Not TrendStack: no moving-average stack, polarity, H1 noon clock, or one-bar continuation target is used.
- Not EventVolOCO: no scheduled event clock, pending-order OCO, event box, or event-matched control is used.
- Mandatory adverse control: `SHIFTED_0025` is evaluated independently under the same source rules. It cannot be removed after results.
- Failure is terminal for this exact EURUSD/M5/lattice/threshold/ATR contract. No post-hoc rescue may alter session, day, year, direction, threshold, lattice offset, stop, horizon, cost, symbol, or timeframe under this ID.

## 3. Immutable source and split

- Public source root: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/`
- DESIGN manifest: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
- DESIGN manifest SHA256: `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
- DESIGN receipt: `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json`
- DESIGN receipt SHA256: `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`
- Embedded public M1 source SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Decision window: `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)`.
- Elapsed calendar weeks: `260.5714285714`.
- Public 2015 DESIGN rows, if and only if present in the exact reviewed manifest, may be read solely to warm up H1 ATR. They cannot create a signal, affect cadence, or enter any outcome computation.
- Validation, holdout, private custody, sealed roots, the monolithic 2015-now parquet, network sources, and paid sources remain prohibited.

## 4. Strict bar construction

- All timestamps are UTC and minute-aligned.
- A complete M5 bar contains exactly five unique M1 timestamps at offsets `0,1,2,3,4` minutes from an aligned five-minute boundary. Duplicate, missing, partial, filled, interpolated, or non-aligned bins are rejected.
- A signal may compare previous/current completed M5 bars only when their start timestamps are exactly five minutes apart.
- A complete H1 bar contains exactly 60 unique M1 timestamps at offsets `0..59` from an aligned UTC hour. Duplicate, missing, partial, filled, interpolated, or non-aligned H1 bins are rejected.
- Calendar gaps between complete ordered H1 trading bars are allowed; missing minutes inside a represented H1 bar are not.
- All OHLC values must be finite and ordered (`low <= open/close <= high`).

## 5. Frozen Stage-0 decision surface

- Pip: `0.0001`. Lattice comparisons use integer quote-point math (`0.00001`, ten points per pip) so fractional-pip quotes cannot be rounded across the frozen 1-pip/10-pip boundaries; levels and thresholds remain integer pips.
- Primary arm `TRUE_0050`: levels `L = k * 50 pips`.
- Placebo arm `SHIFTED_0025`: levels `L = 25 + k * 50 pips`.
- Long candidate:
  - previous completed M5 close `< L`; and
  - current completed M5 close is from `L + 1 pip` through `L + 10 pips`, inclusive.
- Short candidate is the exact mirror:
  - previous completed M5 close `> L`; and
  - current completed M5 close is from `L - 10 pips` through `L - 1 pip`, inclusive.
- Each arm independently keeps only its first eligible decision per UTC date. A TRUE decision does not suppress a SHIFTED decision and vice versa.
- No other filter or ranking is allowed.
- Planned entry timestamp may be declared as the next M5 timestamp. Stage-0 must not read or emit that bar's open or any future OHLC.

## 6. ATR20 source geometry

- Stop-distance proxy: one H1 ATR20.
- ATR20 is the arithmetic mean of 20 True Range values computed from the last 21 complete, ordered H1 trading bars whose starts are strictly before the decision hour.
- This is MT5-parity SMA True Range with shift 1: the in-progress decision-hour H1 bar is excluded.
- True Range for bar `i` is `max(high-low, abs(high-prev_close), abs(low-prev_close))`.
- Calendar/weekend gaps are allowed between trading bars. No synthetic bar or interpolation is allowed.
- Source geometry field: `1.5 pip / ATR20_pips`. Stage-0 may not calculate a realized stop hit or any later price path.

## 7. Stage-0 authority boundary

Stage-0 may read:

- authority files and exact hashes listed above;
- M1 OHLC through each completed signal decision bar;
- prior public M1 OHLC required to construct the 21 complete H1 ATR bars.

Stage-0 may emit only source identity, arm, direction, absolute level in integer pips, decision timestamp, planned next-M5 timestamp, ATR20 pips, source geometry ratio, quality counts, gate results, and zero-valued audit counters.

Stage-0 must not read or emit next/future OHLC, realized returns, PnL, trade results, PF, win rate, expectancy, MFE, MAE, stop/target outcomes, drawdown, validation/holdout data, MT5 results, or MQL5 artifacts.

## 8. Frozen source gates

Both arms must pass all gates:

| Gate | Frozen threshold |
|---|---:|
| Global strict M5 complete-bin ratio | `>= 0.99` |
| Signal ATR-complete ratio, each arm | `>= 0.99` |
| Signal count, each arm | `522..1302` inclusive |
| Cadence, each arm | `2.0..5.0` per 260.5714285714 elapsed weeks |
| Long share, each arm | `>= 0.25` |
| Short share, each arm | `>= 0.25` |
| Maximum single-year share, each arm | `<= 0.30` |
| Median `1.5 pip / ATR20_pips`, each arm | `<= 0.25` |

The only Stage-0 terminal outcomes are:

- `PASS_SOURCE_FEASIBILITY`; or
- `PARK_SOURCE_FEASIBILITY_FAILED`.

A failed gate is terminal source-only evidence for this exact object and must not be rescued under the same ID.

## 9. Later economics contract — frozen but not authorized

If and only if Stage-0 passes, a separate frozen packet and registry transition are required before any economic read:

- Enter at next M5 open; initial SL distance `1.0 * ATR20`; no TP, break-even, trailing, or partial exit.
- Time exit after 12 M5 bars / 60 minutes.
- Risk `0.25%` per position; portfolio DD ceiling `6%`.
- Cost stress `1.50 / 2.25 / 3.00` pips.
- Two DSR trials: TRUE and SHIFTED.
- Later tester contract: Model 0, only after separately reviewed authorization and fidelity validation.
- TRUE absolute gates: PF at 1.50 pips `> 1.30`; PF at 2.25 pips `>= 1.25`; PF at 3.00 pips `>= 1.00`; mean net R at 1.50 pips `>= 0.08`; total net R `> 0`; at least 4/5 positive years; DSR `>= 0.95`.
- TRUE relative gates versus SHIFTED at 1.50 pips: `delta PF >= 0.15` and `delta mean R >= 0.05`.

No item in this section grants economic, Model 0, MQL5, compile, MT5, optimization, promotion, paper, or live authority now.

## 10. Implementation and fail-closed controls

- Scanner: `03. EA Developer/EA_RoundCascade/research/scan_round_cascade_001_stage0.py`
- Focused tests: `03. EA Developer/EA_RoundCascade/research/tests/test_scan_round_cascade_001_stage0.py`
- Import must be inert.
- Production requires the explicit `--run-reviewed-stage0` switch.
- `REVIEWED_REGISTRY_ROW_SHA256` remains `None` until an independent reviewer verifies a registry row that authorizes source execution while keeping economics sealed.
- Authority bytes are read once, then the exact bytes are hashed/decoded; public shard path containment, forbidden custody tokens, symlink/reparse aliases, hardlinks, manifest byte/row counts, and per-shard hashes fail closed.
- Terminal output uses create-new semantics. Existing output is never reused or overwritten.
- This implementation task creates no registry row, run packet, output, evidence, project document update, MQL5 file, MT5 run, or economic result.
