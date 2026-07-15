# Forwards / signed-flow offline probes — 2026-07-14

Status: `OFFLINE_ALL_KILL / NO_MODEL0`
Receipt SHA256: `4424AED1C66A93A3CE7C3F8248F1F7E5A7BB7BCAD065A3FE3FF4A0309A468225`

## Objects

| ID | N | PF | tpw | x1.5 | lift | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-RR2-NYFED-PD-GS-NETFLOW-GATE-001` | 284 | 1.5726 | 1.0887 | 1.1485 | 0.1351 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-RR2-MMF-RETAIL-INFLOW-GATE-001` | 514 | 1.3739 | 1.9704 | 1.0115 | -0.0019 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-RR2-JPY-CME6J-FWDBASIS-ZGATE-001` | 193 | 1.333 | 0.7399 | 0.9877 | -0.0257 | **KILLED_AT_OFFLINE_PROBE** |

## Model 0

Withheld

## Acquire blockers (attempted)

- **Stooq jf.f/ef.f**: JS_bot_challenge
- **Yahoo v7 download 6J=F**: empty_or_crumb; recovered via chart v8 API
- **BoC Valet FX forwards**: no_public_FX_forward_group; daily spot only

## Panels

- `nyfed_pd_ust_net_pos_w1_v1.csv` `946CE197290BE86FADACE548D98BCB0F879D51C8738A00381235BDDAD83981D5`
- `fred_retail_mmf_wow_w1_v1.csv` `5D25FE3A46C0A12D538570E36C118255A06FB5CBA51992496520898E215ADEFC`
- `jpy_cme6j_spot_fwd_basis_d1_v1.csv` `631F7AE8631A02AB7F6B4B3427ACFE8728A02185A7394B917F43EC829697CDB8`
