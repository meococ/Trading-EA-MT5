# Design — Round 22 AC / ATR-exp / FX3-risksync

Date: 2026-07-15
Freeze: `20260715_GREENFIELD_R22_AC_ATREXP_RISKSYNC_UNIVERSE_FREEZE.md` sha=77E558AD57F671F1…

## Mandate
Break lead-clone local optimum (R16–R20: cadence OK, PF@$12 fail).
FORBIDDEN: commodity/equity→FX leads; USD-implied densify; R10–R21 densify.

## 1 `HYP-FX3-H1-LAG1AC-REGIME-BODY-CONT-001`
Rolling 24-bar lag-1 return Pearson AC ≥0.15 AND |body|≥0.55×ATR
→ CONT FX3; SL=1.45 RR=2.0.
Why: statistical persistence regime of own returns — not path-ER, not VR
(variance scaling), not cross-asset lead.

## 2 `HYP-GBPUSD-H1-ATREXP-BURST-CONT-001`
ATR(14)/ATR(56)≥1.25 AND |body|≥0.6×ATR AND close
outer 30% → CONT; SL=1.45 RR=2.0.
Why: volatility *expansion* + conviction — opposite of Parkinson compress;
≠ Donch channel break; ≠ two-bar accel.

## 3 `HYP-AUDUSD-H1-FX3-RISKSYNC-CONT-001`
Same-bar EURUSD+GBPUSD+USDJPY risk-sync (|leg|≥0.35×ATR; JPY risk-on =
USDJPY↓) → AUDUSD CONT; SL=1.45 RR=2.0.
Why: FX-complex co-movement same bar — economically related to risk-on AUD
but **not** lagged XTI/XAU/US30 lead (the local optimum to break).
