# Design memo — tick-path ATR-trail monetization (proxy)

Date: 2026-07-15
Lane: single; no-Git; offline-first
Authority: Owner R&D continue; monetization rebuild authorized

## Problem

Fixed-RR RR2 `194548` dies under +$12 x1.5. Scale-out / timebox /
vol-regime-R killed. OHLC M15 ATR-trail path **voided** (false SL
inflation). Named open class: **ATR trailing monetization**.

## Tick availability

Full tick bid/ask path for tester window **unavailable** (QFSI shallow;
`copy_ticks_range` multi-month hang). Proxies used; do not claim tick fidelity.

## Rejected a priori

- BE@1R / trail-from-BE clamp
- MFE stall-cut hard-close
- Scale-out / timebox / vol-regime-R densify
- Voided M15 OHLC path rebuild as authority
- FRED / XS / LNY / Asia densify

## Design 1 — MFE envelope arm0.75 k1.5 (`HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001`)

Authority method. MFE from M1 extrema in hold; ATR14(M15) closed at/before
entry; arm MFE≥0.75R; trail_floor = MFE − 1.5×ATR/R. Bind only if
realized_R < trail_floor. Never clamp to entry. No stall timer.

## Design 2 — MFE envelope arm1.0 k2.0 (`HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001`)

Same envelope; frozen alternate arm≥1.0R, k=2.0. Still ≠ BE:
trail is peak−k·ATR, not SL→entry.

## Design 3 — M1 path arm0.75 k1.5 (`HYP-RR2-EXIT-ATRTRAIL-M1PATH-ARM075-K15-001`)

M1 OHLC walk + dual-touch defer-to-original. **Labeled ≠ tick.**
Joint-scored with explicit limitations; do not overclaim.

## Model 0 policy

Only `PROBE_SURVIVOR`. Else withhold.

## Post-probe audit

Envelope survivors passed joint bar. Audit shows lift concentrated in
rescues of losers that already printed MFE≫arm (peak-then-exit). M1 path
diagnostic KILL understates the same thesis due to false early SL.
**Model 0 native ATR-trail is mandatory** before any promote; do not treat
offline envelope PF as tick-faithful or deploy-grade.
