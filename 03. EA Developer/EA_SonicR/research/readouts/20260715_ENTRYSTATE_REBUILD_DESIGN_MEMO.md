# Design memo — entry-state / book / independent sleeve

Date: 2026-07-15
Lane: single; offline-first; after ATR-trail Model0 BOTH KILL

## Problem

RR2 exit-path family exhausted on Model 0 authority (BE@1R / MFE stall / ATR-trail native). Offline envelope invalidated. Need highest-EV path that raises post-friction expectancy **without** exit spam or FRED/LNY/XS densify.

## Design 1 — Impulse body/ATR entry gate

`HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001`

**Thesis:** SB FVG entries after limp M15 bars are noise; require closed-bar impulse confirmation (body/ATR≥0.55, direction-aligned) to lift average R after flat friction.

## Design 2 — Drop thin-risk book rule

`HYP-RR2-BOOK-DROP-THINRISK-P25-001`

**Thesis:** Flat +$12 round-turn dominates legs with small risk_usd. Hard-drop ≤p25 risk (no rescale) removes friction traps. ≠ vol-target (which kept all trades and rescaled).

## Design 3 — Asia PD-close magnet fade sleeve

`HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001`

**Thesis:** Extensions away from prior D1 close in Asia mean-revert toward the magnet before London; independent of SB FVG stack.

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold.
