# Design memo — MFE stall-cut + Asia→London state-machine

Date: 2026-07-15  
Lane: single; no-Git; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Problem

Post-pivot Track B killed vol-target and H4 regime. Best shelf remains RR2
`194548` (research PF~1.38 / ~2/wk; +$12 x1.5 ~1.01). Need architecture that
is **not** FRED exo, **not** BE@1R, **not** MaxKZ/RR densify.

## Rejected a priori

- BE@1R / trail-from-BE (falsified; PF collapse).
- New FRED series / exo densify.
- Densify Asia/London hours from Wave5–7 / MULTISYM readouts.
- Invent multi-month cost freeze / RR2 full rebind on diagnostic tick table.

## Design 1 — MFE stall-cut (`HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001`)

**Thesis:** RR2 give-back after partial favorable excursion destroys friction
expectancy. Cutting when MFE **stalls** (not when price merely tags 1R) should
harvest mid-path edge without BE scratch dynamics.

**Frozen ≠ BE@1R:**
| Item | Stall-cut | BE@1R (killed) |
|---|---|---|
| Arm | MFE ≥ **0.75R** | path reaches **1.0R** |
| Action | **hard close** at stall bar close | move SL → **entry**, wait |
| Stall | 6 M15 bars no new peak MFE **and** giveback ≥ 0.30R from peak | n/a |
| TP/SL | original TP/SL still active until stall | original TP; SL becomes BE |

## Design 2a — Asia continuation ATR-coil (INTAKE FAIL)

`HYP-USDJPY-H1-ASIA-COIL-LONDON-CONT-STATE-001`: Asia coil ≤0.60·ATR14(bar)
+ London continuation past Asia mid. **Empty** — multi-hour Asia range is
~2.5× 1-bar ATR at median; threshold unit-invalid. Documented; not densified.

## Design 2b — Asia pctl-coil London break state (intake replacement)

`HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001`

**Thesis:** Relative Asia compression (range ≤ p40 of prior 60 Asia days)
**ARMS** the day; London may **FIRE** on first close beyond Asia H/L; else
**EXPIRE**. State-machine monetizes coil→break without FRED/BE/RR densify.

**Frozen:** Asia 00–07 UTC; coil p40/60; London fire 07–12; RR=2; USDJPY H1;
SL = opposite Asia extreme ±0.10·ATR; one trade/day; hard EXPIRE.

**De-dup:** NZD Wave7 had no relative coil + used RR3; EUR/XAU were other
symbols / ATR-bar compress. This board freezes relative coil + EXPIRE a priori.

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold. No Real stall required.
