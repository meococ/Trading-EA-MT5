# Prereg — HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001

Date: 2026-07-15  
State on freeze: `preregistered` / `PROBE_SURVIVOR`  
Authority: Owner monetization rebuild; offline envelope survivor; EXO_FRED_DISPLACE_SPAM_PAUSED

## Identity

- Hypothesis ID: `HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001`
- Parent: `HYP-SB-MAXKZ2-RR2-FRICTION-001` (frozen shelf `20260714_194548`)
- Class: cost-resilient **ATR trailing monetization** (not entry densify)
- De-dup: `readouts/20260715_ATRTRAIL_TICKPROXY_DEDUP_CLEARANCE.md`
- Offline: `preflight/20260715_ATRTRAIL_TICKPROXY_OFFLINE_PROBES.json`
- Receipt: `1626718918088C2ED1EB1F24DD879BDB0ADA48338DADDACBB80E042923855B3B`

## Thesis

Fixed-RR RR2 dies under +$12 x1.5. Scale-out / timebox / vol-regime-R killed.
BE@1R and MFE stall-cut killed. ATR trail that **arms after favorable excursion**
and ratchets SL by k×ATR **without BE clamp** should cut giveback on losers that
printed MFE≫arm while preserving 2R TP path when trail does not bind.

Offline authority was MFE-envelope proxy (tick path unavailable). Offline PF is
**not** deploy-grade — Model 0 native path is the confirmation gate.

## Locked Design (a priori)

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY M15 entries (RR2 donor) |
| Donor run | `20260714_194548` overrides unchanged except trail inputs |
| Arm | `InpTrailActivateR = 0.75` (MFE / profit ≥ 0.75R) |
| Trail | `InpUseTrail=1`, `InpTrailATR_Mul=1.5` |
| BE clamp | `InpTrailBE=0` (**≠ BE@1R**) |
| Stall timer | off (**≠ MFE stall-cut**) |
| TP | original RR2 TP kept (`InpTP_RR_LDN=2.0`, `InpTP_RR_NY=2.0`) |
| Window | 2021.01.01–2025.12.31 |
| Model | **0 only** |

## Model 0 overrides (exact)

```
InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;InpUseWeekendFlat=1;InpUseTrail=1;InpTrailActivateR=0.75;InpTrailATR_Mul=1.5;InpTrailBE=0;InpPartialClose=0
```

Implementation note (2026-07-15 native prep): `EA_SilverBullet_v2` trail now
updates **every tick** using **closed M15 ATR14** (`g_hATR_M15`), Bid/Ask − k×ATR
with favorable-only ratchet (`≈ peak − k·ATR` under tick updates).
`InpTrailBE=0` → never clamp to entry. Offline MFE-envelope remains the probe
gate only — Model 0 native path is confirmation.

## Kill / Park / HIT (Model 0)

| Gate | Rule |
|---|---|
| KILL | N&lt;80 OR tpw∉[1.5,6] OR PF≤1.20 OR +$12 x1.5 PF&lt;1.15 OR no lift vs RR2 baseline x1.5 |
| HIT (research) | clears joint bar on Model 0 native path |
| GOAL | research HIT alone ≠ GOAL; need research-grade cost rebind |

## Banned

- Densify arm / k / BE flag from readout
- Revive BE@1R / MFE stall / scale-out / timebox / vol-regime-R
- Kill Real/QFSI accumulate to force this run
- Claim tick fidelity or deploy from offline envelope PF

## Terminal policy

Model 0 **authorized** but **queued** while QFSI Real accumulate is live
(`do_not_kill`). Run when terminal free or Owner scopes Demo lane.
