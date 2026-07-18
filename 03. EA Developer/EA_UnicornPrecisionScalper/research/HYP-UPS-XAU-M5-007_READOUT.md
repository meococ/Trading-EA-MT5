# HYP-UPS-XAU-M5-007 readout — FVG midpoint limit feasibility

## Verdict

**KILL_AT_FILL_FEASIBILITY_PROBE. No source change and no Strategy Tester run.**

The report-prior execution change cannot retain the frozen cadence floor. Of
251 unchanged event-anchored candidates, only 115 touched the FVG arithmetic
midpoint within the next three closed M5 bars. Fill rate was 45.82% and filled
cadence was 1.1103 per elapsed week, versus the required 82.5% and 2.0/week.
Only 28 short limits filled, below the frozen minimum of 30.

| Frozen gate | Required | Observed | Result |
|---|---:|---:|---|
| Parent candidates | 251 | 251 | PASS |
| Fill rate | >=82.5% | 45.82% | FAIL |
| Filled cadence | 2.0–5.0/week | 1.1103/week | FAIL |
| Active fill months | >=20 | 24 | PASS |
| Long fills | >=30 | 87 | PASS |
| Short fills | >=30 | 28 | FAIL |

The remaining 136 candidates expired. No PnL, stop/target outcome, MFE, MAE or
forward return was calculated. Extending expiry, moving the price away from CE
or adding a market fallback after seeing this result would revive the killed
hypothesis post hoc.

## Root-cause analysis of the completed market-entry EAs

1. **No gross edge before realistic execution cost.** The four-bar control
   produced only +0.890R gross over 138 trades (+0.0064R/trade). The
   event-anchored successor produced -13.859R gross over 130 trades.
2. **Market execution is too expensive for such a thin edge.** On the four-bar
   control, the frozen research proxy deducted 1.247R commission and 22.678R
   slippage, taking the result to -23.036R and PF 0.688. This proxy is
   deliberately non-promotable, but it demonstrates that a near-zero gross
   edge has no cost budget.
3. **The nominal 2.5R target is not the realized payoff.** The control had 50
   stop outcomes (-50.225R), only 11 target outcomes (+27.573R), 65 max-hold
   exits (+23.644R gross) and 12 breakeven-zone exits (-0.102R gross). Average
   report win/loss was about 1.49, not 2.5; 39.86% wins is therefore essentially
   breakeven before additional latency cost.
4. **Direction is asymmetric but cannot be mined.** Control BUY was +12.602R
   gross and SELL -11.712R gross; after the same proxy both directions were
   negative. HYP-006 was gross-negative in both directions. Removing shorts
   after reading this split is forbidden and would not repair BUY after cost.
5. **Regime consistency is absent.** The control lost in 58.3% of months, had a
   negative median trade, a 716-day equity-high drought and a 0/7 robustness
   score. HYP-006 hit the 5.5% account-DD guard by March 2025 and stopped taking
   new risk; its MC P95 DD was 7.118%.
6. **The implemented detector is a skeleton, not the full discretionary memo.**
   It approximates breaker overlap with an opposite candle body, has no
   explicit MSS/BOS close state, FVG freshness/fill-ratio state or labeled
   micro-confirmation, and the completed variants entered at market. The memo
   itself recommends alert-first/semi-auto until those subjective quality
   labels are validated.

## Improvement boundary

The attempted execution improvement is now falsified before code. The legal
next development step is not another threshold or entry-policy variant. It is
an alert-first labeling program with 100–200 independently reviewed setup
labels and reject reasons, followed by a fresh causal hypothesis on a new
window. Explicit MSS/FVG/retest recombinations must also de-duplicate against
the already killed PO3/KLR family. No current Unicorn hypothesis is eligible
for live execution or automatic promotion.

## Evidence

- Probe: `research/evidence/20260716_HYP_UPS_XAU_M5_007_FILL_PROBE.json`
- Frozen prereg: `research/HYP-UPS-XAU-M5-007_FROZEN_PREREG.md`
- Probe source: `research/probe_unicorn_midpoint_limit_fill.py`
- Storage before/after:
  `research/evidence/HYP-UPS-XAU-M5-007_STORAGE_BEFORE.json` and
  `research/evidence/HYP-UPS-XAU-M5-007_STORAGE_AFTER.json`
- Four-bar run: `02. AlphaFactory/runs/EA_UnicornPrecisionScalperControl/20260716_140224/`
- Event-anchored run: `02. AlphaFactory/runs/EA_UnicornPrecisionScalper/20260716_141244/`

The probe used the workflow-owned FivePercent portable terminal on D. C-side
MetaQuotes file count and byte total were unchanged before/after (6,302 files,
30,718,761,465 bytes); no C cleanup was required.

