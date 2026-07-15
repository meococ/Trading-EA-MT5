# HYP-HIS-SL-SIGATR-M15-EUR-001 — Prereg

**Status:** Owner-authorized new SL contract (post DIAG plumbing pass).  
**Not** densify from DIAG's 3 Friday trades.  
**Parents:** DIAG `HYP-HIS-DIAG-GATECOUNT-M15-EUR-001`; empty `HYP-HYBRID-ICT-SONIC-M15-EURGBP-001`.

| Field | Frozen |
|---|---|
| hypothesis_id | `HYP-HIS-SL-SIGATR-M15-EUR-001` |
| package | `EA_HybridICT_Sonic` |
| symbol / TF | EURUSD M15 |
| window | 2020.01.01 → 2026.07.15 |
| model / role | 0 / control |
| deposit | 100000 |

## Thesis (one sentence)

Keep Hybrid **entry** confluence (H4 bias + NearLevel + Wave + Dragon trigger + PVSRA); change **SL** to signal-bar extreme ± **1.0×ATR** only — H4 FVG/OB/liq and Dragon±40 are **not** used for stop distance.

## Why legal (a priori)

- Offline A: Dragon±40 vs MaxSl → 0 fills.
- DIAG B: level SL still MaxSl-fails 1505/1508; only 3 fills.
- New mechanism = **separate risk sizing from structure objects** (report: customize SL/TP per contract). ATR multiple frozen at 1.0 — not fit from the 3-trade sample.

## Frozen inputs (decision surface)

| Input | Value |
|---|---|
| `InpUseLevelSl` | **false** |
| `InpSlAtrMult` | **1.0** |
| `InpUseDragonSlFloor` | **false** |
| `InpMaxSlAtrMult` | 2.5 (safety; with 1.0× should rarely trip) |
| `InpTargetRR` | 2.5 |
| Entry filters | Wave ON, PVSRA 1.5× ON, MACD OFF, spread≤4, ATR regime 0.7–3.0 |

## Kill gates

| Gate | Kill if |
|---|---|
| Cadence | elapsed tpw < 1.0 on full window (still thin book warning if <2) |
| Edge | PF x1 < 1.30 after declared tester friction honesty note |
| Stress | x1.5 PF < 1.25 (if cost artifact absent → report UNVERIFIED, no promote) |
| Concentration | >50% trades in one weekday → park (document; not auto-veto densify) |
| Sample | N < 30 → insufficient for research pass (DIAG-scale only) |

## Forbidden

- Tune `InpSlAtrMult` from this run's readout
- Dragon period 30–38 sweep
- Post-hoc hour/day veto from readout
- Claim live / GOAL from single control
