# HYP-CME6E-RAWBREAK-BOOKTRANSITION-002 — DESIGN readout

Verdict: **KILL_DESIGN_BREAKBAR_BOOK_TRANSITION_NO_POSITIVE_EXPECTANCY**  
Epistemic layer: **engineering-valid / economic-invalid / not promotion-ready**  
Run ID: `CME6E_BREAKBAR_DESIGN_20260727_143049Z`  
Date: `2026-07-27`

## Executive decision

The clock correction was necessary for fidelity but did not recover an edge.
The fixed full-break-bar CME 6E book-transition score fails to separate the
raw first-close BREAK trades: its top half remains negative, is slightly worse
than the quality-eligible control, and is also worse than the bottom-score
negative control. Only integrity and cadence pass (`2/11`).

This is a valid economic kill of HYP-002's exact score/clock/entry identity.
HYP-001 remains independently killed for its stale pre-break feature. Neither
result proves that all CME microstructure is useless; together they close
displayed five-level imbalance filters around this unchanged raw-BREAK entry
surface unless a future object changes the market mechanism, decision surface
and validation population materially.

## Source and reconciliation

- Owner plan: `C57B0AF9...64A1D1C`, approved ceiling `USD 1.40`.
- Journal-estimated source cost: `USD 0.696219488984` (not invoice-verified).
- Source corpus: 561/561 paid nonempty DBN responses, four planned
  metadata-empty windows, 2,185,882 records, 59,883,285 compressed bytes.
- Source-only population: 565 identities; 516 quality-eligible.
- Frozen median: `-0.012342488801680875`.
- Challenger/control split: 258 / 516 / 258; challenger cadence
  `2.477366255144033/week`.
- Outcome access occurred only after prereg SHA
  `E0E7040E29EB2A37D11532293C298167D7C429618B38D722C9D1599AF799A894`
  was bound in registry row 261.
- All 565 position IDs, directions, break-bar-open clocks and actual
  next-bar-entry clocks reconciled. Holdout rows materialized: zero.
- Red-first tests: 5/5 targeted; 41/41 package.

## Economic result

| Arm | N | PF | Mean R | Net |
|---|---:|---:|---:|---:|
| Quality-eligible control | 516 | 0.792580 | -0.146109 | -716.51 |
| Top-50 transition challenger | 258 | 0.782315 | -0.155912 | -382.83 |
| Bottom-50 negative control | 258 | 0.803226 | -0.136306 | -333.68 |

The challenger has no relative lift:

- versus quality control: PF delta `-0.010265`, mean-R delta `-0.009803`;
- versus bottom-score control: PF delta `-0.020911`, mean-R delta `-0.019606`.

### Stability buckets

| Challenger bucket | N | PF | Mean R | Net |
|---|---:|---:|---:|---:|
| 2021 | 133 | 0.696827 | -0.225502 | -286.05 |
| 2022 | 125 | 0.881269 | -0.081869 | -96.78 |
| BUY | 133 | 0.680027 | -0.232682 | -297.86 |
| SELL | 125 | 0.897348 | -0.074228 | -84.97 |

Every frozen year and direction is negative. The less-negative 2022 and SELL
buckets are diagnostics, not permission for a post-hoc veto or subgroup rescue.

### Cost stress and deflation

The fixed extra round-trip cost stresses are `UNVERIFIED_PROXY`, not broker
cost truth:

| Additional pips | PF | Net |
|---:|---:|---:|
| 0.50 | 0.631779 | -734.13 |
| 1.50 | 0.418130 | -1,436.73 |
| 2.25 | 0.306215 | -1,963.68 |
| 3.00 | 0.222332 | -2,490.63 |

DSR across the exact three-arm trial universe is `0.030470619`, below the
frozen `0.95` floor.

## Frozen gate result

| # | Gate | Result |
|---:|---|---|
| 1 | Source/hash/identity/dual-clock integrity | PASS |
| 2 | Challenger N258 and cadence 2..5/week | PASS |
| 3 | Native PF >= 1.30 | FAIL |
| 4 | Native mean R >= +0.08 | FAIL |
| 5 | 1.5-pip stress PF >= 1.25 | FAIL |
| 6 | 2.25-pip stress PF >= 1.00 | FAIL |
| 7 | Both years PF > 1 and mean R > 0 | FAIL |
| 8 | BUY and SELL PF > 1 and mean R > 0 | FAIL |
| 9 | Lift versus quality control | FAIL |
| 10 | Lift versus bottom-score control | FAIL |
| 11 | DSR >= 0.95 | FAIL |

## Mechanism diagnosis and failure radius

The experiment distinguishes clock fidelity from alpha. The old feature was
indeed sampled too early, but the correct inference was “the intended
mechanism was untested,” not “moving the window will create edge.” Once the
full break bar is observed causally through the actual decision boundary, the
fixed transition score still ranks trades in the wrong direction and leaves
absolute expectancy negative.

The most defensible diagnosis is therefore:

1. the raw first-close BREAK entry surface has negative base expectancy;
2. displayed five-level 6E imbalance, whether stale pre-break or summarized
   across the completed break bar, does not discriminate continuation strongly
   enough to overcome that entry surface and costs;
3. the weakness is mechanism/decision-surface level, not merely a timestamp
   bug or a missing risk scaler.

Failure radius: raw first-close BREAK with unchanged entry/SL/TP/management
plus either HYP-001's pre-break five-level alignment score or HYP-002's frozen
full-break-bar transition score. Forbidden rescues include another percentile,
score weight, depth level count, persistence formula, source-quality exclusion,
year/direction/session veto, cost tier or management overlay on these opened
outcomes.

A legitimate successor needs a fresh population and a materially different
mechanism or decision surface, such as post-break absorption/replenishment
around a separately defined pullback entry. That is a new hypothesis and data
contract, not HYP-002 V2. It may require new paid data and therefore requires a
new Owner-approved source plan before acquisition.

## Evidence

- Frozen prereg:
  `research/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_PROBE_PLAN.md`
- Source-only receipt:
  `02. AlphaFactory/data/databento/cme_6e_breakbar_transition_design/book_transition_feature_receipt.json`
- Probe result:
  `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_DESIGN/probe_result.json`
- Reconciliation receipt:
  `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_DESIGN/reconciliation_receipt.json`
- Joined ledger:
  `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_DESIGN/joined_design_trades.csv`
- Trial log:
  `research/trials/trial_log.jsonl`

No chart/casebook, MQL5, Model 0, promotion, paper or live action is warranted:
the exact preregistered fatal economic gates already close this probe under the
Two-Speed fast-kill doctrine.
