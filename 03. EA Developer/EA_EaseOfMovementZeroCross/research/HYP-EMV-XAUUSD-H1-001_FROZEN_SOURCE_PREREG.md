# HYP-EMV-XAUUSD-H1-001 — Frozen source preregistration

Frozen: 2026-08-11 before source rows were opened.

## Thesis

Ease of Movement measures whether midpoint displacement is large relative to
the tick-volume needed to traverse the bar range. A zero-line transition in a
14-bar mean is a price/participation state change, materially different from
the closed entropy, variance-relocation, OBV-divergence, KVO, MFI and pure
range-polarity families.

## Exact causal mapping

On native completed XAUUSD H1 bars:

1. `HL2_t = (high_t + low_t) / 2`.
2. `raw_eom_t = (HL2_t - HL2_(t-1)) * (high_t - low_t) / tick_volume_t`.
3. `eom14_t = SMA(raw_eom_(t-13)..raw_eom_t)`.
4. LONG iff `eom14_(t-1) <= 0` and `eom14_t > 0`.
5. SHORT iff `eom14_(t-1) >= 0` and `eom14_t < 0`.
6. Equality arms but never emits. The first possible event is index 15. Flat
   range is valid and contributes zero; nonfinite prices, invalid OHLC, or
   nonpositive/nonfinite tick volume fail closed.
7. Decision is the next native row only when both `source_epoch` and UTC are
   exactly `t + 3600`; a raw gap event is consumed, not delayed.

Normal market closures do not reset the 14-bar rolling calculation; this is a
native-bar-count oscillator. No threshold, debounce, cooldown, session,
weekday, price filter, ATR filter, outcome or post-event price is permitted.

## Source contract

- Native FivePercent XAUUSD H1 Parquet only.
- Data path: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet`.
- Data SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`.
- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- Materialize only `time_utc < 2023-01-01T00:00:00Z`; score only
  `[2018-01-01, 2023-01-01)`.
- Source-only attempt: `EMV001-SOURCE-001`; exactly once; no MT5, trades,
  returns, PF, cost, validation or holdout.

## Frozen source gates

- design rows >= 25,000;
- feature coverage >= 99%;
- exact-next coverage >= 97%;
- executable events >= 500;
- pooled cadence 2–5/week;
- LONG and SHORT each >= 30%;
- maximum calendar-year share <= 30%;
- every calendar year cadence 1.25–6.5/week;
- zero conflicts and deterministic replay.

Any failed gate parks only this exact EMV14 zero-cross mapping. A pass permits
direct MQL5 formula build and one untuned baseline, not economics or promotion.
