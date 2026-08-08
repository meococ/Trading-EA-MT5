# HYP-RSF-EURUSD-M5-STATE-MODEL-012 — result

## Verdict

`KILL_NO_STABLE_DISCOVERY_EDGE`

The five-indicator engine is engineering-valid as a closed-bar state census,
but simultaneous indicator state does not predict EURUSD M5 returns strongly
enough to survive observed costs. Validation from 2023 onward remains sealed.

## Census evidence

- AlphaFactory run: `20260808_004517`.
- Model 0, EURUSD M5, tester envelope 2018-01-01 to 2023-01-01.
- History quality: 100%; 372,914 bars; 105,949,201 ticks.
- Census rows: 372,913; no duplicate timestamp and no missing cell.
- Indicator readiness: 372,914/372,914 closed bars.
- Entries/final closes: 0/0; lifecycle sidecar is header-only.
- AlphaFactory's enhanced economic analyzer returned `No trades found in
  report` after the valid zero-trade tester run. The report and all required
  sidecars were already copied; no rerun was performed.

The new census matches all 738 PATH-011 entry snapshots exactly across the 29
shared current-contract fields. The older 13-window forensic replay matches 46
non-QQE fields but not QQE because it predates the corrected group-string ABI.
The old QQE columns are excluded from modeling; the current census is the
authoritative five-indicator state source.

## Preregistered discovery

Six cells were evaluated: Ridge and shallow HistGradientBoosting at 3, 6 and
12 M5 bars. There were 24 expanding-year model fits and 72 train-threshold/test
fold evaluations. Every trade paid the observed spread times
`1.5 + 0.15 * (1 + VRC volatility percentile / 100)`.

No cell survived. The best cell was Ridge/12 bars:

- 767 primary-threshold trades across 2019–2022;
- cadence valid in all four yearly folds;
- pooled PF 0.755372;
- median yearly PF 0.749508;
- pooled net -215.697287 normalized ATR-R;
- adjacent cadence thresholds PF 0.766212 and 0.838943.

All six cells had pooled PF below 0.76. This is a broad rejection, not a near
miss worth parameter rescue.

## Interpretation

Permutation diagnostics show tiny predictive contribution relative to target
variance. Time, AIRD and VRC rank above TB, QQE and MBB, but none converts into
positive net expectancy. This kills only the simultaneous-state forecasting
surface. A separately preregistered state-transition event clock is the next
bounded test; it may not use 2023+ or tune rules from this readout.

## Bound artifacts

- Census SHA256: `2E24166F486D7073C4E98C452290372E4604D2C566BAD822F4FDC38E0E46D2BB`
- RunMeta SHA256: `40357F6289D48918101A033749CE2F71C741A1B4834F917549AE1C0C9ED6810E`
- Report SHA256: `61AAA6343976159A90F34EBAD06028D34BFBF7CB7B05F9D7B832B1E1928F49D4`
- Run manifest SHA256: `FB9F28B896B3BE222DF7727113F623FCE66786520256BC46C3DA3C8A917F7AFF`
- Discovery results SHA256: `73516A7582FAE1D39911FB2F8CC73F9450E25657F832A58C872A52E5C0D45DEF`
- Walk-forward folds SHA256: `FF1719CC430B09D4F3E326004D7E4889DF5E2590FB0A9B139C43B4567D1BD5D6`
- Feature diagnostics SHA256: `0522E3EE0E9C1650488EBFFABF45B70DBED49986720ED0571CE257BD7D70B64F`

