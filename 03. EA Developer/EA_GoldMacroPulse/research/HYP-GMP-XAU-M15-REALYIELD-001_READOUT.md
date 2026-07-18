# HYP-GMP-XAU-M15-REALYIELD-001 — Readout

Verdict: **KILL_AT_OFFLINE_PROBE**. No EA source, compile, Strategy Tester run,
holdout access, live execution or promotion authority was created.

## Frozen experiment

- XAUUSD M15, 2022-01-01 through 2024-12-31; 2025+ remained untouched.
- Challenger: the first later XAU trading day after an official DFII10 shock of
  at least 5 bp, traded opposite the real-yield move at 14:30 UTC.
- Matched control: the same dates, entry, ATR stop, target, hold and cost, with
  direction from the prior completed 24-hour XAU return.
- Management: ATR(14) from the prior bar, 1.5 ATR stop, 1.5R target, 26-bar
  maximum hold, stop first on same-bar ambiguity.
- Cost screen: 82 broker points per trade. Commission and slippage were not
  available, so the screen could never authorize promotion.

The first execution stopped before producing an outcome because the matched
control lacked a warm-up guard on the first eligible date. The implementation
was corrected to skip signals with fewer than 97 prior M15 bars, regression
tests remained 4/4 green, and the unchanged frozen strategy was then evaluated
once. This was an implementation retry, not a parameter rerun.

## Result

| Metric | Momentum control | Real-yield challenger | Frozen gate |
|---|---:|---:|---:|
| Trades | 270 | 270 | — |
| Elapsed-week cadence | 1.726 | 1.726 | 2.0–5.0 |
| PF after spread proxy | 0.606 | 0.684 | challenger >=1.35 |
| Net R | -83.098 | -63.098 | >0 and >= control |
| Expectancy | -0.308R | -0.234R | >=0.10R |
| DD at 0.25%/R | 22.19% | 16.87% | <=8% |
| Positive train years | 0/3 | 0/3 | >=2/3 |
| PF advantage | — | +0.0779 | >=+0.10 |

The challenger had a small pre-cost directional advantage: gross PF 1.061 and
+9.571R versus control gross PF 0.937 and -10.429R. That advantage was too thin
for M15 XAU execution. The frozen spread proxy consumed 72.669R in either arm
(median 0.256R per trade), leaving the challenger negative in 2022, 2023 and
2024. It failed cadence, PF, expectancy, drawdown, positive-year, net-positive
and matched-control-separation gates.

## Diagnosis and decision

The official real-rate mechanism may explain part of gold's broad direction,
but this preregistered next-session M15 implementation does not create a
cost-tolerant scalping edge. The result is not close enough to justify source
code: even before commission and slippage, gross PF was only 1.061.

Do not rescue this ID by changing the 5 bp threshold, entry hour, direction,
ATR multiple, target, hold, year, subgroup or cost. Any future lane requires a
materially different information set and a new preregistration before outcome
access; it must not be presented as a continuation of this hypothesis.

## Evidence and provenance

- Probe: `research/evidence/20260716_HYP_GMP_XAU_M15_REALYIELD_001_PROBE.json`
  — SHA256 `7A8A32C7E3CFA870A66669F0E26EC10F0E2C114C51F3297D786AF6B7E38AA07C`.
- Frozen prereg SHA256:
  `74C30D3EF8431671C33A1D6DF1201B0E0568408F458B8677D1195A281E20A95E`.
- Final probe script SHA256:
  `03BD239D11C0C47684A520C6B8753F33AD283320E5343C901F8AB2897A235EC7`.
- DFII10 snapshot SHA256:
  `C22544C463731D9EE153B5C87D53FCE2B45DF606841263E9F40E833071A0ADED`.
- Terminal data path recorded in the probe:
  `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable`.
- C-drive tester storage was metadata-identical before and after; no file was
  deleted because this run created no C-side tester data.
- External sources: Federal Reserve H.15, FRED DFII10, and the Chicago Fed
  Letter “What Drives Gold Prices?”. Browser ChatGPT Deep Research was attempted
  first but no controllable browser backend was available, so provenance is a
  disclosed primary-source web fallback rather than GPT-5.6 Sol output.
