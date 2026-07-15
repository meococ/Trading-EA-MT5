# Multi-option teardown/rebuild campaign — coordinator closeout

Date: 2026-07-14 evening  
Authority: Owner Vietnamese — *"tinh chỉnh, thử nghiệm nhiều option... có thể sẵn sàng đập đi xây lại"*  
Cost grade: **research-proxy / `UNVERIFIED_TESTER_DEFAULT` only** — not confirmed

## Campaign verdict vs GOAL

| Question | Answer |
|---|---|
| Any `HIT_RESEARCH_BAR`? | **YES** — `HYP-SB-MAXKZ2-DENSITY-002` / run `20260714_192304` (twin `192515`) |
| Confirmed / GOAL done? | **NO** — Demo tester cost; no Real QFSI; no cost-stress/holdout suite |
| Best sleeve (research-proxy) | SB MaxKZ2: **PF 1.33 / 546 / tpw 2.0942 / net +8123** |
| Prior best near-miss still relevant | SB A1 `002505` PF 1.34 / tpw 1.9945 (cadence miss) |

## Option matrix results

| Option | run_id | PF | trades | tpw | decision |
|---|---|---:|---:|---:|---|
| `HYP-SB-MAXHOLD-A2-001` | `20260714_191628` | 1.334 | 521 | 1.9983 | PARK (null vs A1) |
| `HYP-SB-NYPM-KZ-001` | `20260714_192419` | 1.27 | 635 | 2.4356 | PARK (cadence OK, PF<1.30) |
| `HYP-SB-MAXKZ2-DENSITY-002` | `20260714_192304` (twin `192515`) | **1.33** | 546 | **2.0942** | **HIT_RESEARCH_BAR** |
| `HYP-SPARK-ASIAN-GBPUSD-001` | `20260714_191507` | 1.07 | 432 | 1.657 | PARK |
| `HYP-ITSM-NYONLY-STRICTALIGN-002` | `20260714_191845` | 1.22 | 540 | 2.071 | PARK (PF lift insufficient) |
| `HYP-ITSM-LONDON-ONLY-STRICTALIGN-002` | `20260714_192116` | 1.12 | 482 | 1.849 | PARK |
| `HYP-H1-LOWVOL-DONCHIAN-MR-001` | `20260714_191727` | 0.40 | 13 | 0.05 | **KILL** (teardown falsified) |
| `HYP-SPARK-CAPACITY-3PD-001` | `20260714_193732` | 1.37 | 327 | 1.254 | PARK (PF OK; cadence still <2 — null densify vs parent ~1.25/wk) |

Elapsed weeks denominator: **260.7143** (same as SB A1 readout).

## Torn down / rebuilt

| Action | Detail |
|---|---|
| **Built** | `EA_H1LowVolDonchianMR` (greenfield H1 low-vol Donchian fade) |
| **Killed after Model 0** | Same EA — PF 0.40 / N=13; retain folder as evidence |
| **Override-only children** | SB MaxHold / NYPM / MaxKZ2; ITSM NY-only & London-only StrictAlign; Spark GBPUSD |
| **Not rewritten** | `EA_SilverBullet_v2` / `EA_ITSM` / `EA_M15SparkAsian` source logic unchanged |

## Integrity notes

- All options used new child `hypothesis_id` + frozen short prereg before Model 0.
- No Friday-cutoff mining; no Spark Mon–Thu densify; no T10 ITSM rescue.
- Tester cost ≠ Real; missing cost ≠ 0.
- ≥5 new Model 0 runs shipped tonight → storage inventory dry-run required (no destructive cleanup).

## Owner-physical next (blocks confirmed)

1. Login `FivePercentOnline-Real` + QFSI capture.
2. Reprice **MaxKZ2 `192304`** (twin `192515`) and parked A1 `002505` under verified cost.
3. Only then consider cost-stress / holdout / promotion path.

## Files (campaign)

- Option matrix: `readouts/20260714_TEAM_REFINE_REBUILD_OPTION_MATRIX_V1.md`
- This closeout: `readouts/20260714_MULTI_OPTION_TEARDOWN_REBUILD_CAMPAIGN_CLOSEOUT.md`
- Per-option readouts under `readouts/20260714_HYP_*_READOUT.md` for IDs above
- Living truth: `04. Project Control/ai/hot.md`
