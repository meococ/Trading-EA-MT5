# HYP-RSF-EURUSD-M5-PATH-011 — terminal result

Status: `KILLED_NEGATIVE_EXPECTANCY`

## Frozen test

- EURUSD M5, 2018-01-01 through 2022-12-31, Model 0, current spread, 100% history quality.
- Run: `02. AlphaFactory/runs/EA_RegimeStructureFusion/20260807_235223`.
- Exactly one economic development trial; no optimization and no OOS/holdout access.
- Source SHA256: `D1034E8497D7469F8E91C29BF1C9BC231379145970DF02F65912BC2418FD8561`.
- Engineering gates: compile 0 errors, 14/14 path contracts, non-repaint PASS, independent code review PASS with no P0-P2 findings.

## Economic result

| Metric | Value |
|---|---:|
| Trades | 738 |
| Profit factor | 0.7993 |
| Net profit | -5,252.63 USD |
| Max drawdown | 6.248% |
| Win rate | 26.42% |
| Expectancy | -7.12 USD/trade |
| Mean achieved R | -0.0856R |

Every development year was negative: 2018 PF 0.866, 2019 PF 0.822, 2020 PF
0.549, 2021 PF 0.552, and 2022 PF 0.967. Raw PF below 1.0, negative
expectancy, negative mean R, and zero positive years each independently fail the
frozen gate. OOS remains sealed.

## Native MT5 chart findings

The four additional Visual Tester cases were diagnostic and did not change any
threshold:

- C01 breakout long: `PATH_BASIS_QQE` reduced the target loss to about -0.41R.
- C03 breakout short: the symmetric rule reduced the target loss to about -0.66R.
- C05 trend long: the opposite TB event was causal but late; the frozen target
  still closed near -0.97R in a fast breakdown.
- C07 trend short: price hit the original stop in 6 minutes, before a new M5 bar
  could close. At entry the stop was 2.19 ATR, so this was not an ATR stop-floor
  defect. The actual contradiction was stale episode state: AIRD held Ranging at
  95.14%, VRC was Compression at volatility percentile 9, MBB squeeze score was
  19.44 with no release, while the stored structural arm still admitted a short.

The C07 contradiction is real, but it does not authorize another revalidation
rescue. The prior role-aware current-state mechanism already tested that family
and was terminal at 89 trades, PF 0.6791.

## Path action attribution

| Exit/action | Count | Mean R | Diagnostic conclusion |
|---|---:|---:|---|
| MBB basis + adverse QQE | 480 | -0.3326R | Cuts some losses but dominates the book and converts many eventual wins into losses |
| Opposite TB flip | 41 | -0.4024R | Worse than the matched parent by -0.0737R/trade |
| Break-even stop | 39 | -0.0464R | Helpful protection, insufficient to create edge |
| Native TP | 116 | +1.4705R | Original winners retained |
| Native SL | 57 | -1.0512R | Same-bar/fast failures remain unreachable to closed-bar management |
| Native max hold | 5 | +0.8233R | Unchanged control priority |

On the 519 exactly matched parent opportunities, entry time, direction, engine,
entry, SL, and TP all matched. Mean R improved from -0.1082R to -0.0721R, but
remained negative. Breakout-long and breakout-short worsened to -0.0792R and
-0.0917R; trend-long and trend-short improved to -0.1020R and -0.0199R but
neither became positive.

## Why the run contained 738 rather than 520 entries

This was not an early shadow-slot release. There were 519 exact parent matches,
one parent-only entry, and 219 PATH-only entries. Before the first extra entry
on 2020-09-03, both runs had closed 518 positions. The parent had cumulative net
-5,250.75 USD while PATH had -5,137.61 USD. That 113.14 USD difference kept the
PATH account just above the broker money-mode stop-out plus frozen equity-buffer
admission boundary, allowing later minimum-volume trades that the parent risk
gate rejected. The 219 extra entries were themselves negative: -0.1177R/trade,
R-profit-factor 0.665.

Therefore shadow occupancy preserved the original time slot, but a balance-
dependent risk gate made exact opportunity-count parity endogenous. This
contaminates a naive 520-versus-738 A/B comparison; it does not rescue the
hypothesis because the exact 519-trade matched cohort is also negative.

## Indicator-combination diagnosis

- Every matched entry already had QQE sign and TB bias aligned; those indicators
  supplied no remaining cross-sectional separation.
- Entries with MBB squeeze score below 20 and no release were especially weak
  (57 matched trades, parent mean -0.3496R; PATH mean -0.2560R).
- Removing that natural squeeze bucket still left the matched PATH cohort at
  -0.0494R/trade and R-profit-factor 0.856.
- AIRD/VRC directional agreement did not create edge; the semantically aligned
  conjunction remained negative.

The four indicators describe the episode but do not provide independent forward
information sufficient to overcome costs and failed continuation. Entry/path
threshold tuning, session deletion, route deletion, direction deletion, and
year selection are forbidden post-hoc rescues.

## Decision

- Engineering-valid: **yes**.
- Economic-valid: **no**.
- Promotion-ready: **no**.
- PATH-011: **KILL; no parameter rescue**.
- OOS/holdout: **not opened**.

This closes the indicator-fusion frontier for this mechanism family. A successor
requires a materially new, licensed point-in-time event/data contract and a
zero-trade semantics/cadence probe; another recombination of AIRD, VRC, MBB, TB,
or QQE is not admissible.

## Evidence

- Run manifest SHA256: `19A8BA88B140E1AAF88290FF2219432BB1100A3F22130E8E5A0A9596575AEFC8`
- Report SHA256: `ACD22536463F08E970E4EAD40C45FA0128C572596AF097CDBF8380E4D6B54BF0`
- Lifecycle SHA256: `95E15A5F636B7960FA30718E43B705B82830DD314AA8DE254C9E48803A06CE36`
- EntryContext SHA256: `3C6FA9B5498680AA5587EF7010063C27E212ED0C4E54641E842A5F8538889A6E`
- PathActions SHA256: `577CA07045429FADA666B0AB7844BD30E8E13E0BBDE0A5ECC5F4C6348B84A726`
- RunMeta SHA256: `09E4BA5F18C234F21778E9BE37976D703F0FCC18AF264976FC5A610F378B9058`
