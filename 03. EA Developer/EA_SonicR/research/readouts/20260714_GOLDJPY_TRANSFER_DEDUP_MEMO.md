# De-dup Memo — GoldJPYInverse transfer candidates — 2026-07-14

Status: `NO_NEW_ID_WITHOUT_FRESH_MECHANISM / FAIL_CLOSED_DEFAULT`

## Seed surface

STRATEGY_LOG `S673`–`S699` / `EA_GoldJPYInverse`: XAUUSD+ ATR move as
USDJPY M15 lead. Strongest configs are **Mon+Thu** and/or hour skips
(h16 LBMA). Baseline without day mining already dead:

| Seed | Config | Result |
|---|---|---|
| S671 | NYC all days, gold thresh 1.2 ATR | PF **1.05** DEAD |
| S673 | Mon+Thu NYC | PF 1.26 (day-mined) |
| S676 | Mon+Thu h15+h17 skip-h16 | PF 1.39 (day+hour mined) |
| S699 | Mon+Thu h17-only | PF 1.53 but sparse / below workspace bar |

## Decision

Renaming to a new `HYP-GOLDJPY-*` with “a priori Mon–Thu” is **not**
independent of the killed/day-mined GoldJPY family if the causal engine is
still gold-move → USDJPY. S671 already falsifies the no-day-filter surface.

**Denied** unless a genuinely new lag/contract (different exogenous gold
close source, different availability lag, or non-USDJPY book) is frozen
first. Do not Model 0 a cosmetic transfer tonight.

## Preferred remaining legal moves

1. Finish `HYP-SB-WEEKEND-FLAT-001` control→challenger Model 0.
2. USBILL Model 0 only as honest-cost research screen (cadence gap known).
3. New exogenous public archive not yet on disk (true FX forwards / licensed
   equity closes) — not twin of killed OIS/bond-diff.
