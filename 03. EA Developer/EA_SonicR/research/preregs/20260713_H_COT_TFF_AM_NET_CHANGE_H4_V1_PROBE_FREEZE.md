# Probe Design Freeze — COT TFF Asset-Manager Net Change H4 V1

Status: `FROZEN_PRE_RESULT / INDEPENDENT_EXOGENOUS`  
Date: 2026-07-13

## Independence

Uses delayed CFTC TFF **positioning** (Asset Manager net), not spot rank, not
money-market Δcarry events, not carry-level strip, not DGS2−DFR wedge.

## Frozen constants

| Constant | Value |
|---|---|
| Contracts | EURO FX → EURUSD; BRITISH POUND → GBPUSD; JAPANESE YEN → USDJPY (sign flipped) |
| State | Asset_Mgr Long − Short (All) |
| Trigger | weekly report when \|Δ net\| / max(OI,1) ≥ 0.02 (2% of OI) |
| available_at | Report_Date + 3 calendar days (Tue as-of → Fri publish conservative) |
| Entry | first H4 with date > available_at |
| Direction | sign(Δ net); USDJPY uses −sign(Δ net JPY) |
| HOLD_BARS | 18 H4 (~3 days) |
| Weekend flat | Friday hour >= 16 UTC |
| Cost A/B | 1.5 / 3.0 pip |
| Train/holdout | 2018–2022 / 2023–2025 |
| Control | same event times; direction = sign(20 H4 return) |

## Train gates

trades>=80; 1.2<=tpw<=5.0; PF_a>=1.10; beat control; expectancy_a>0.
