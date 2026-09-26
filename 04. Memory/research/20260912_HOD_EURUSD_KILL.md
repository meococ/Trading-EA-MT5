# HOD EURUSD — KILL (2026-09-12)

Cell 13 of the era-2 governed screen. `HYP-HOD-EU-M5-001` / `EA_Hod`.

## Runs

- **`20260912_104000`** — completed through cost artifact; audit FAIL on
  `iOpen(...,sh)` where `sh` was an `iBarShift` result guarded by
  `sh<0` (not `<1`) AND the auditor's `allowed_guarded_shift_param` rule
  only covered CopyBuffer/CopyRates, not bar functions (`iOpen`/`iClose`)
  or extreme functions.
- **`20260912_104259`** — rerun after (a) EA guard tightened to `sh<1`
  (semantics unchanged: the :00 bar is always shift>=2 at decision time)
  and (b) auditor extended so `allowed_guarded_shift_param` also covers
  `BAR_FUNCTIONS` and `EXTREME_FUNCTIONS` with a generalized arg index.
  Audit PASS; 13/13 regression tests green.

## Result (run 104259)

- Window 1999.01.01 → 2026.09.11, `verified_m1_asof`, `VERIFIED_M1_START`,
  quality 99%, Model 0, Build 6192 isolate.
- Trades 13,806 (~9.6/wk — below 10 floor), PF 0.827, net −$6,374,
  DD 64.0%, WR 41.3%.
- Cost PF: x1.0 0.681 / x1.5 0.615 / x2.0 0.555.

## Verdict: KILL

Time-anchored hourly momentum does not persist on EURUSD M5 — the :10-bar
direction of an hour is mostly noise by the time it can be entered. Every
weekday/hour bucket is PF<0.9; no subgroup survives (per weakness report —
but no salvage attempted per frozen contract).

## Board state — 12 kills, 0 passes

| Class | EA | EURUSD cost PF x1.0 |
|---|---|---|
| IBS continuation | Ibsc | 0.68 |
| Camarilla fade | CamarillaFade | 0.70 |
| H1 displacement | HtfDisplacement | 0.76 |
| Liquidity sweep | LiquiditySweep | 0.68 |
| M15 breakout | M15br | 0.68 |
| Volume spike | VolSpike | 0.72 |
| Cross-symbol RSI spread | Rsp | 0.69 |
| Hour-open drive | Hod | 0.68 |

Plus XAU (5 kills): CRSI-R2, AMA, VwapFade, HourDrift, GbbSqueeze.

## Auditor improvement (durable)

`audit_mql5_nonrepaint.py` now applies `allowed_guarded_shift_param` to
BAR_FUNCTIONS (`iOpen`/`iClose`/`iHigh`/`iLow`/…) and EXTREME_FUNCTIONS
(`iHighest`/`iLowest`/…) with a generalized arg index — previously only
COPY_FUNCTIONS were covered. Guarded local identifiers (not just params)
are proven by a dominating `if(param<1) return` in the enclosing function.

## Remaining untested EURUSD classes

H4/H1 EMA pullback (H4pb/H1pb — trend-pullback), FVG continuation,
Choppiness regime filter, ~20 MA/oscillator single-family variants
(expected weakest class). Every mechanism so far lands at cost PF
~0.65-0.76 — the board is falsifying the M5/M15 intraday contract space
itself, not individual strategies. The honest scientific answer is close
to "no single-mechanism intraday scalp sleeve clears the gates at
MQ-Demo costs". Recommend a board-level report to Owner before spending
more cells on lookalike variants.
