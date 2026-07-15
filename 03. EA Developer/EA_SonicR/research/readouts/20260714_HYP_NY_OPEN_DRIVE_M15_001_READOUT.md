# Readout — HYP-NY-OPEN-DRIVE-M15-001 / EA_M15NYOpenDrive

Date: 2026-07-14  
State: `parked` (Model 0 research near-miss; GOAL unmet)  
Process: `GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`

## Run

| Field | Value |
|---|---|
| run_id | `20260714_014224` |
| EA | `EA_M15NYOpenDrive` |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified) |
| Path | `02. AlphaFactory/runs/EA_M15NYOpenDrive/20260714_014224/` |
| report SHA256 | `8BD375F29291B5E58F0CCAA6FEE2CD8635329835BA97F02C54EBBE6AA9594429` |

## Metrics

| Metric | Value |
|---|---|
| Profit factor | **1.08** |
| Total trades | **292** |
| Total net profit | **+$5108.23** |
| Max equity DD | **~5.89%** |
| Elapsed calendar weeks | ≈ **260.71** |
| Trades/week (elapsed) | 292 / 260.71 ≈ **1.12** |

Cost: **UNVERIFIED_TESTER_DEFAULT** / Demo research-proxy. Missing ≠ 0.

## Verdict

- Kill floor: PF≥1.00, N≥80, tpw∈[1.0,6.0] → **pass**
- Park rule: PF ∈ [1.00, 1.30) → **PARK**
- GOAL unmet (PF 1.08 < 1.30; tpw 1.12 < 2.0)

## Banned rescue

Do not mine NY ORB hour/window, day filters, or buffer/body from this readout. Do not treat as LondonORB twin rescue.

## Ceremony

Known `includes_sha256` mismatch after report ready; artifacts retained.
