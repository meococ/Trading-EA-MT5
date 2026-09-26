# FVG + H4PB EURUSD — KILLs (2026-09-12)

Cells 14 and 15 of the era-2 governed screen.

## EA_FVG — `HYP-FVG-EU-M15-001`, run `20260912_120321`

- EURUSD M15, 1999.01.01→2026.09.11, `VERIFIED_M1_START`, quality 99%, Model 0.
- 29,370 trades (~20.3/wk PASS), PF **0.776**, net **−$9,259**, DD **92.6%**,
  WR 31.0%.
- Cost PF x1.0 **0.686** / x1.5 0.627 / x2.0 0.574.
- Non-repaint PASS. Overnight gate failed (M15 holds to 8 bars can cross 20:00
  within session rules — exposure audit found crossings).
- **Verdict: KILL.** Price-void continuation is gross-negative.

## EA_H4pb — `HYP-H4PB-EU-M5-001`, run `20260912_115954`

- EURUSD M5, same window/class, quality 99%.
- 1,251 trades (**0.87/wk — FAIL**), PF **0.929** (best gross on the board),
  net **−$383**, DD **6.6%**, WR 43.8%.
- Cost PF x1.0 **0.765** / x1.5 0.694 / x2.0 0.629.
- Non-repaint PASS, Monte Carlo p95 PASS, overnight/weekend PASS.
- **Verdict: KILL.** H4-EMA50 reclaim is structurally too rare (one signal per
  H4-EMA cross; ~1/wk) and still negative after costs — the cleanest DD on the
  board but cannot meet the scalping cadence contract.

## Board state — 14 kills, 0 passes (15 hypotheses)

EURUSD cells now cover: fade (IBS/Camarilla/sweep), breakout (M15br),
momentum (H1 displacement), volume (VolSpike), cross-symbol (Rsp),
temporal (Hod), pullback (H4pb), imbalance (FVG). All gross-negative.

**Falsification conclusion:** at MQ-Demo economics (spread ~0.1 pip,
$7/lot commission bound), the M5/M15 intraday single-mechanism contract
space on EURUSD is falsified — no tested class reaches cost PF ≥ 1.0, let
alone the 1.30 promotion bar. The only cells near break-even (H4pb 0.93
gross, GbbSqueeze ~1.00) are structurally sub-cadence.

## What remains genuinely untried

- Other symbols' sleeves (GBPUSD/USDJPY) — needs new cost evidence; same
  broker cost structure makes a different outcome unlikely but is a
  legitimate separate falsification domain.
- Swing/multi-day holding contracts — violates the 10-40/wk cadence gate;
  requires Owner renegotiation of the contract space.
- The ~50 remaining fleet variants are MA/oscillator same-family
  reparameterizations — low information value after 14 kills.

Recommendation: board-level report to Owner before further cells.
