# HYP-LOMX-DESIGN-M5-002 Frozen Outcome-Blind Probe Plan

Status before execution: `FROZEN_PRE_IMPLEMENTATION_NO_OUTCOME`

## Question

Do the two atomic decision surfaces proposed by the Owner have enough
decision-time candidate density and stable geometry on each planned symbol to
justify MQL5 economic experiments, without reading any trade outcome?

This probe is not a backtest and cannot establish edge.

## Frozen identity

- Hypothesis: `HYP-LOMX-DESIGN-M5-002`
- Package: `EA_LOMX_MultiAssetMomentum`
- Symbols/cells: `EURUSD` and `XAUUSD`, evaluated separately.
- Timeframe: native closed `M5` broker Bid bars.
- Window: `[2016-01-04 00:00:00Z, 2025-01-01 00:00:00Z)`.
- Dataset manifest:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`.
- EURUSD M5 SHA256:
  `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8`.
- XAUUSD M5 SHA256:
  `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`.
- Primary clock: existing `time_utc`; rows with null/ambiguous UTC are rejected.
- Trial accounting: four atomic cells plus two per-symbol combined-density
  summaries. No parameter variants are allowed.

## Shared rules

- Every feature uses bars closed no later than decision bar 1.
- Asian range is the exact same UTC date `[00:00,06:00)` and requires all 72
  M5 bars. Trading decisions are `[07:00,16:00)` UTC.
- ATR14 is Wilder/MT5-equivalent true range, shifted to the decision bar.
- Tick volume is a broker activity proxy, not aggressor volume, CVD or VPIN.
- Prior-20 volume mean/std excludes the decision bar.
- A candidate is timestamped at the close of signal bar 1. Decision-close is
  used only for initial geometry; no later price is loaded as an outcome.
- Long and short rules are symmetric.

## Arm A: `ASIAN_RANGE_SWEEP_RECLAIM`

- Long: `low1 < asian_low - 0.30*ATR14`, `close1 > asian_low`, and
  `volume1 > prior20_mean + 1.50*prior20_population_std`.
- Short: symmetric around `asian_high`.
- Stop: beyond the signal extreme by `0.20*ATR14`.
- TP1: Asian midpoint; it must be favorable relative to decision close.
- TP2: opposite Asian boundary and must provide at least `1.50R` from decision
  close. A geometry-invalid setup is rejected before the final count.

## Arm B: `BAR_RANGE_COMPRESSION_BREAKOUT`

The plan's ambiguous `BW` is frozen as candle high-low range, not Bollinger
bandwidth and not the separate T2 Volman grammar.

- `range2 < 0.70 * mean(range3..range52)`.
- Buildup box is exactly bars 2..16, excluding breakout bar 1.
- Long: `close1 > box_high + 0.20*ATR14` and
  `volume1 > prior20_mean`; short is symmetric.
- Stop: opposite box edge plus `0.10*ATR14`.
- Target geometry: fixed `2.00R`.

## Combined-density accounting

Both arms remain separate. For the diagnostic combined stream, same-symbol
same-bar collisions count once with sweep priority. Opposing same-bar signals
are invalid. There is no position/hold simulation, so this is candidate cadence,
not executed-trade cadence.

## Frozen gates

Per atomic cell:

- at least 400 final candidates;
- at least 1.00 final candidate per elapsed calendar week;
- each direction at least 20% of final candidates;
- no single UTC calendar year above 25% of final candidates;
- finite positive ATR and initial risk for every final candidate.

Per symbol combined stream:

- `2.00 <= deconflicted candidates/week <= 5.00`;
- at least 90% of active trading dates have a complete 72-bar Asian range.

Full-plan P0 passes only if all four atomic cells and both combined summaries
pass. Individual passing cells may be retained as fresh symbol-specific ideas
if the full dual-engine plan fails; they receive new IDs and may not inherit a
pooled result.

## Forbidden reads and rescue

The scanner must not load or compute future return, exit, MFE, MAE, win/loss,
PnL, PF, drawdown, trade simulation, validation or holdout selection. It may
not tune thresholds, session, direction, year, symbol, stop or target after the
result. A failure closes this exact design matrix; a successor needs a material
information/decision-surface change and a fresh plan.
