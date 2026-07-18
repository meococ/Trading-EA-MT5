# HYP-FVG-SCALP-CONFL-M5-EUR-001 de-dup readout

State: **KILL_AT_DEDUP_ILLEGAL_FVG_CONTINUATION_DENSIFY**  
Outcome opened: **no**  
Model 0 executed: **no**  
Promotion eligible: **no**

## Decision

The existing Path-C package is a valid closed-bar engineering scaffold, but it
does not define a materially independent trading mechanism. The first
meaningful economic run is rejected before price outcomes.

The preregistration itself makes no independence claim and identifies the same
expected failure as killed `HYP-H1-DISPLACE-FVG-CONT-001`. The primary object
remains a three-candle displacement/FVG followed by a partial fill or reclaim.
Changing the chart timeframe to M5 and stacking HTF bias, an order block,
premium/discount, liquidity sweep, session, and rejection score only densifies
filters around that dead object.

## Bound overlap

| FVGConfluence rule | Prior terminal family | De-dup verdict |
|---|---|---|
| Three-candle impulse FVG continuation | H1 displacement + FVG continuation | Same primary object |
| Entry at 40-60% gap depth/rejection | FVG-percent fill variants | Explicit densification |
| HTF BOS/OB/P-D/sweep/session score | Structural/ICT confluence filters | Filter stack, not new information |
| Partial 50% and BE at 1R | Killed BE/scale-out monetization boards | Same management family |
| Price-only EURUSD M5/H1 inputs | Existing structural price surface | No exogenous causal field |

The bound predecessor produced 247 trades, PF about 1.017 and 0.947 trades per
elapsed week; x1.5 PF was about 0.945. Both cadence and cost stress failed.
The archived research/red-team merge independently returned
`NO_LEGAL_CANDIDATE` / `KILL_RECOMMEND` before the Owner's build-only override.
That override authorized a scaffold and compile, not Model 0 or promotion.

## Current engineering verification

- Canonical source SHA256:
  `0279ADE492A104803CC7279CD5D3B99A6F57822779B91273AFD666F0C784757F`.
- AlphaFactory compile on 2026-07-16: `0 errors, 0 warnings`; EX5 66,660 bytes.
- EX5 SHA256:
  `DDDAF35E7AB8165413773B4790E3271E392690FCB99ADA3676D90DBD95754661`.
- Compile log SHA256:
  `68D9A8F02EFC17CA9B8C125981CFCF1FF9F464466D82C81E3384B010167D5C41`.
- Source non-repaint audit: `PASS_ENGINEERING_ONLY`; no explicit bar-zero
  decision reads, closed-bar ATR/FVG/HTF inputs, and `iTime(...,1)` new-bar
  gate. Evidence:
  `research/evidence/20260716_FVGCONFLUENCE_NONREPAINT_AUDIT.json`.

Compile success proves only that the scaffold builds. It does not supersede
the de-dup failure or create evidence toward the GOAL book.

## Verdict

Do not run an offline PnL probe, Strategy Tester, holdout, parameter search, or
optimization for this hypothesis. Do not rescue it by changing confluence,
FVG fill percentage, session, timeframe, RR, break-even, partial exit, symbol,
or year.

Reopening requires a materially different causal information set under a new
hypothesis—not another price-only FVG/ICT/SMC filter combination.
