# HYP-RSF-EURUSD-M5-STATE-MODEL-012 — frozen preregistration

Frozen before any full-census run or discovery-label calculation.

## Owner authorization and failure radius

On 2026-08-08 the Owner explicitly instructed the Lead Quant to continue
researching, understanding, tuning and testing the five-indicator system until
an edge is found. This reopens research work but does not authorize paper/live
trading or a cosmetic parameter rescue of PATH-011.

The new object is a closed-bar state model. AIRD, VRC, MBB, TB SMC and QQE are
continuous/categorical features, not five simultaneous votes. Terminal RSF
entry clocks, Structural-Event-004, role-aware gating and PATH-011 remain
closed and are not renamed or rerun.

## Stage A — zero-trade census

- Symbol/timeframe: EURUSD M5.
- Discovery window: 2018-01-01 through 2022-12-31 only.
- Export one row per completed M5 bar after indicator warm-up.
- MQL output contains current/older OHLC and shift-1-or-older indicator state;
  it does not contain future prices, labels, selected direction or trades.
- Disable all entry modes. Expected orders/deals/trades: zero.
- Model 0 is mandatory. The existing Model-0 forensic windows are used only as
  an additional overlap sanity check, not as a replacement data source.

## Stage B — fixed discovery analysis

All labels and model selection stay inside 2018–2022. The candidate set is
fixed at six cells:

- forward horizons: 3, 6 and 12 completed M5 bars;
- model families: Ridge regression and shallow HistGradientBoosting regression;
- prediction target: signed next-open-to-horizon-close return divided by the
  decision-bar TB ATR;
- fixed features: AIRD posterior/confidence; VRC regime/direction/volatility;
  MBB normalized location/squeeze/release/setup flags; TB bias, normalized
  swing/zone distances and structure/sweep/displacement flags; QQE levels,
  slopes and primary-secondary spread; UTC hour/day cyclical terms;
- missing/non-finite rows are rejected, not imputed from future data.

Walk-forward folds train only on prior calendar years and test the next year.
Each test fold is purged/embargoed by the selected horizon. A deterministic
train-only score threshold targets 2–5 non-overlapping signals per elapsed
calendar week. Evaluation enters at next-bar open, exits at the frozen horizon
close and charges at least 1.5 times the observed decision spread as round-trip
cost. No year/session/direction may be removed after outcomes are seen.

Discovery survival requires all of:

1. at least three yearly test folds with 2–5 trades/week;
2. positive net normalized return and PF > 1.0 in every cadence-valid fold;
3. median yearly PF >= 1.20 and pooled PF >= 1.20 at x1.5 observed spread;
4. no single year contributes more than 40% of positive gross return;
5. the selected model/horizon is stable under adjacent train-only thresholds;
6. trial count includes all six cells and every threshold checked.

If no cell survives, Stage B closes without EA implementation. Any successor
must change the causal object rather than mine this readout.

## Stage C — still sealed

Only after a Stage-B survivor is frozen may one fixed model be encoded in the
EA and tested on 2023–2024 validation. The 2025-current holdout, cross-symbol
adaptation, optimization, paper, live and promotion lanes remain sealed.

