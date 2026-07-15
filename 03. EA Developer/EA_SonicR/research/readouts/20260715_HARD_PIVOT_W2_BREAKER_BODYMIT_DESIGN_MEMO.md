# Design — HARD PIVOT W2 breaker + body-mitigation

Date: 2026-07-15
Freeze: `20260715_HARD_PIVOT_W2_BREAKER_BODYMIT_UNIVERSE_FREEZE.md` sha=11D25A7AFB478C6F…

## 1 `HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001`
Confirmed swing L=3 → closed BOS (body≥0.25*ATR)
 → arm BOS-bar BODY as breaker; later wick+accept close → CONT next open.
Session UTC[7,17); RR=2.0 hold≤12.
Why: structural location after BOS with accept-delay (thick edge lesson);
 FX3 cadence from swing BOS — ≠ auction outer-quartile; ≠ FVG gap.

## 2 `HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001`
Arm SB displacement; zone = disp **BODY** (not FVG); no arm fill;
 later wick-into-body + close accept → next M15 open.
USDJPY M15; KZ LDN(11, 12)/NY(16, 18); MaxKZ=2; RR=2.0.
Why: keep accept-delay thick $/trade lesson from FVG near-miss;
 change location class to raise cadence — NOT FVG densify.
