# HYP-CME6E-RAWBREAK-BOOKSTATE-001 — terminal DESIGN readout

Date: 2026-07-27  
Verdict: `KILL_DESIGN_BOOK_ALIGNMENT_NO_POSITIVE_EXPECTANCY`  
Evidence class: `VALID_OFFLINE_DESIGN_ECONOMIC_PROBE_UNVERIFIED_PROXY_COSTS_OOS_SEALED`

## Decision

The frozen direction-aligned five-level CME 6E MBP-10 book score does not
separate profitable EURUSD raw first-close BREAK decisions in DESIGN
2019-2020. The exact challenger passes only integrity and cadence: 2/11 frozen
gates. It is materially worse than both the complete quality-eligible control
and the bottom-score negative control.

This is a valid economic kill of this exact score, quality contract, threshold
and decision surface. It is not an engineering invalidation and not a claim
that all futures-book mechanisms lack edge. No threshold, weight, lookback,
level-count, subgroup, direction, year, cost or management rescue is legal
under this hypothesis.

## Owner-bounded acquisition

- Approved plan ID:
  `1825DC77A35F2794051BD83E5A35ED87C8952049FB08B47BEA1AF34E1802D98F`.
- Owner ceiling: USD 0.68 for this plan; combined session ceiling: USD 1.00.
- Live API estimate for this plan: USD 0.339879676699.
- Prior bounded source estimate: USD 0.254399180414.
- Combined API estimate: USD 0.594278857113, below both ceilings.
- These are Databento API estimates, not independently verified invoice
  charges.
- Raw DESIGN validation: 541 paid responses, 529 nonempty, 12 complete
  source-empty, six metadata-empty, 353,598 decoded records and 9,893,465
  compressed bytes.
- OOS 2021-2022 was not quoted, downloaded, decoded, feature-extracted or
  outcome-joined.

## Frozen source-only selection

The score and quality surface were frozen before the first outcome join in
`HYP-CME6E-RAWBREAK-BOOKSTATE-001_PROBE_PLAN.md` SHA
`A1862A7173DA5AC063E0C2E23A872B69EB2966DB76EFE462D141C3177ED5E578`.

- All DESIGN raw BREAK decisions: 547.
- Quality-eligible control: 459.
- Outcome-blind median score threshold: `-0.005025602742083225`.
- Challenger, score greater than or equal to the median: 230.
- Bottom-score negative control: 229.
- Exact trial universe: three arms; no grid or alternate percentile.

The mechanism had a legitimate prior, but not a promise of transferability:
Cont, Kukanov and Stoikov found short-horizon price changes related to order-flow
imbalance in their market sample (<https://arxiv.org/abs/1011.6402>), while
Databento's MBP data represents aggregated displayed depth
(<https://databento.com/microstructure/mbp>). CME 6E displayed depth is not the
broker EURUSD executable book.

## Economics

| Arm | N | Cadence/week | Native PF | Mean R | Net USD |
|---|---:|---:|---:|---:|---:|
| Quality-eligible control | 459 | 4.401370 | 0.606449 | -0.293427 | -1,319.56 |
| Top-50% score challenger | 230 | 2.205479 | 0.527529 | -0.365156 | -822.70 |
| Bottom-50% negative control | 229 | 2.195890 | 0.691715 | -0.221385 | -496.86 |

The challenger loses relative to the quality control by `-0.078920` PF and
`-0.071729R`, and loses relative to the negative control by `-0.164186` PF and
`-0.143771R`. The ranking is therefore adverse, not merely too weak.

### Challenger stability checks

| Bucket | N | PF | Mean R |
|---|---:|---:|---:|
| 2019 | 114 | 0.469920 | -0.420647 |
| 2020 | 116 | 0.587568 | -0.310623 |
| BUY | 118 | 0.604009 | -0.286093 |
| SELL | 112 | 0.455148 | -0.448456 |

Both years and both directions are negative. The challenger DSR is
`0.000001795` across the exact three-arm trial universe, below the frozen 0.95
gate.

### Additional cost diagnostics

These fixed stresses are `UNVERIFIED_PROXY`, not broker cost truth.

| Additional round-trip pips | PF | Net USD |
|---:|---:|---:|
| 0.5 | 0.414908 | -1,163.25 |
| 1.5 | 0.260191 | -1,844.35 |
| 2.25 | 0.182109 | -2,355.18 |
| 3.0 | 0.129323 | -2,866.00 |

## Gate result

PASS: hash/identity/reconciliation/OOS integrity; N=230 and cadence within
2-5/week.

FAIL: native PF, native mean R, 1.5-pip stress PF, 2.25-pip stress PF,
year stability, direction stability, lift versus quality control, lift versus
bottom-score negative control and DSR. Total: 2/11 PASS.

## Reconciliation and artifacts

- Source feature CSV SHA:
  `7BE51A64CB282DD5F11719B97206173F3A0D9D37A212A043B1AC5D45ACFC8BAD`.
- Frozen parent control ledger SHA:
  `07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9`.
- Probe script SHA:
  `6D02E153BE745F5202D2010C1494670821A97D22A4F704C85D8E4D1C649B688D`.
- Joined DESIGN ledger SHA:
  `A28B47392E295C6D6296E4C7CC851C226C2F3060673014B37959F12407AC99B2`.
- Probe result SHA:
  `DD54DD94B8EE4E008807C41AA622219607B3930000724EC4F4845E333B797782`.
- Reconciliation receipt SHA:
  `C23F67C73C61AD74400B53D7955A41B6FD60DBD461E2521B3074368D05044F9B`.
- Trial log SHA:
  `780E4287D3FF02F340695D03C56D39B73B3D02EA6DA6058BC254DBD0946F3193`.
- Reconciliation: 547 source rows = 547 DESIGN outcomes materialized; exact
  clock and direction matches; 0 OOS rows materialized; three trials executed.
- Independent PowerShell recomputation reproduced all three arm counts, PF,
  mean R, net, year buckets and direction buckets.
- Package regression tests: 22/22 PASS.

## Authority after closeout

- No MQL5 source or EA was built; engineering-valid ends at the offline probe.
- Economic-valid verdict for this exact DESIGN object: KILL.
- Promotion/deploy-ready: no.
- OOS, Model 0, paper and live remain unauthorized.
- A future candidate must use a materially new mechanism/data contract/decision
  surface, a fresh hypothesis ID and a new outcome-blind preregistration; it
  cannot reuse this score with a tuned cutoff.
