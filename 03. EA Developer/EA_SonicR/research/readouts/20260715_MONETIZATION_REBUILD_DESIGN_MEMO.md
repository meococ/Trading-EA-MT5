# Design memo — monetization rebuild (post-greenfield)

Date: 2026-07-15
Lane: single; no-Git; offline-first
Authority: Owner authorized rebuild (“đập đi xây lại”); free Model 0 for survivors

## Problem

Public price+exo greenfield exhausted. Fixed-RR scalp RR2 `194548` dies under +$12 x1.5.
Need monetization architectures that change **how** winners are cashed — not denser entries.

## Rejected a priori (killed / banned)

- BE@1R / trail-from-BE
- MFE stall-cut hard-close
- Vol-target ATR risk sizing / H4 regime-align gate
- FRED/XS/LNY/Asia densify
- Free +3R upgrade without path proof

## Methodology

**Outcome-faithful transforms on tester PnL/risk_usd** (risk_usd ≈ |pnl| on losers).

OHLC M15 path rebuild for scale-out/ATR/volregime is **VOIDED** as decision evidence:
false SL inflation (~444 vs ~300 real losers) — same bias class as MFE stall path board.
ATR-trail remains a design candidate only after tick-path or Model 0 native path.

## Design 1 — Scale-out (`HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001`)

Take 50% at +1.0R; remainder to +2.0R → TP winners monetize at **1.5R**.

## Design 2 — Time-box scalp lock (`HYP-RR2-EXIT-TIMEBOX-SCALPLOCK-2H-001`)

If hold ≤2h: keep. If hold >2h and realized R≥1: lock **1.0R** at box
(conservative hybrid; optimistic extend-to-3R forbidden without path).

## Design 3 — Vol-regime R multiple (`HYP-RR2-VOLREGIME-RMULT-H1ATR-001`)

H1 ATR%ile → TP 1.5 / 2.0 / 3.0R. On original ~2R TP hits: earlier 1.5R applied;
3R **not** credited without path proof (keep 2R).

## Model 0 policy

Only `PROBE_SURVIVOR`. Else withhold.

