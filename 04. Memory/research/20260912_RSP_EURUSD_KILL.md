# RSP EURUSD — KILL (2026-09-12)

Cell 12 of the era-2 governed screen. `HYP-RSP-EU-M5-001` / `EA_Rsp`.

## Run

- **Run ID:** `20260912_103123` (control, challenger, research-proxy cost tier)
- **Window:** 1999.01.01 → 2026.09.11, `verified_m1_asof`, `VERIFIED_M1_START`
- **Quality:** 99% | **Model:** 0 | Build 6192 isolate
- Second symbol: GBPUSD M5 RSI — real M1 coverage from 1999 verified.

## Result

| Metric | Value | Gate | Verdict |
|---|---|---|---|
| Trades | 21,940 | — | — |
| Cadence | 15.24/wk | 10–40 | PASS |
| Profit factor | 0.812 | >1.30 | FAIL |
| Net | −$7,843.28 | — | FAIL |
| Max DD | 78.6% | ≤20% | FAIL |
| Win rate | 41.2% | — | — |
| Cost PF x1.0 | 0.687 | — | FAIL |
| Cost PF x1.5 | 0.622 | ≥1.25 | FAIL |
| Cost PF x2.0 | 0.563 | ≥1.00 | FAIL |
| Non-repaint audit | PASS | PASS | PASS |
| Overnight/weekend | 0 / 0 | PASS | PASS |

## Analysis

First cross-symbol mechanism on the board and it changed nothing: EU−GB
RSI(14) spread zero-cross is still gross-negative (−0.36 expectancy).
Relative strength between two EUR/GBP legs sharing the USD driver is
mostly noise at M5 — the spread cross fires often enough for cadence but
the post-cross drift does not persist past a 1.5xATR stop + 1.5R target
structure.

## Verdict: KILL

Registry row appended (`killed`, run_ids=[20260912_103123]).

## Board state — 11 kills, 0 passes

Every EURUSD M5/M15 mechanism class tried is gross-negative under
measured MQ-Demo costs:

| Mechanism class | EA | Cost PF x1.0 |
|---|---|---|
| IBS continuation | EA_Ibsc | 0.68 |
| Camarilla fade | EA_CamarillaFade | 0.70 |
| H1 displacement | EA_HtfDisplacement | 0.76 |
| Liquidity sweep | EA_LiquiditySweep | 0.68 (+cadence 0.12/wk) |
| M15 range breakout | EA_M15br | 0.68 |
| Volume spike | EA_VolSpike | 0.72 (+cadence 9.8/wk) |
| Cross-symbol RSI spread | EA_Rsp | 0.69 |

The screen is converging on a structural finding, not a search failure:
**no intraday single-mechanism sleeve on EURUSD M5/M15 clears PF 1.30 at
this cost tier.** The remaining lever is a different holding contract
(swing/multi-day, which violates the current 10-40/wk cadence gate) or a
genuinely different information source (news-calendar, macro prints) —
both outside the frozen contract space. Recommend reporting the board to
Owner before burning more cells.
