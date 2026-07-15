# Readout — HYP-LONDON-ORB-M15-001 / EA_M15LondonORB

Date: 2026-07-14  
State: `parked` (Model 0 research near-miss; GOAL unmet)

## Run

| Field | Value |
|---|---|
| run_id | `20260714_011347` |
| EA | `EA_M15LondonORB` |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Overrides | _(defaults; empty CLI)_ |
| Spread | tester `current` (not broker-verified) |
| Path | `02. AlphaFactory/runs/EA_M15LondonORB/20260714_011347/` |
| Twin (non-authorizing race) | `20260714_005126` |

## Metrics

| Metric | Value |
|---|---|
| Profit factor | **1.17** |
| Total trades | **413** |
| Net profit | **+$1751.13** |
| Expectancy | **+$4.24** |
| Max equity DD | **~8.13%** |
| Elapsed calendar weeks | ≈ 260.71 |
| Trades/week (elapsed) | 413 / 260.71 ≈ **1.58** |

## Verdict vs frozen prereg

- **Kill screen:** PF ≥ 1.00, N ≥ 80, cadence ≈1.58 ∈ [1.0, 6.0] → **does not kill**.
- **Park rule:** PF ∈ [1.00, 1.30) → **park**.
- **GOAL:** PF **1.17 < 1.30** and cadence **1.58 < 2.0**; Demo cost only → **GOAL unmet**.

## Banned rescue

Do **not** mine 2021 year, Thursday PF, ORB hour window, buffer/body/range, or densify Fri from this readout.

## Ceremony

`alpha.ps1` closeout threw known `includes_sha256` mismatch after report ready; artifacts retained.

## Parallel Phase 0

Portfolio subset trade-series + honest `UNVERIFIED_TESTER_DEFAULT` cost manifests attached; still
`BLOCKED_NOT_READY_FOR_PREREG_FREEZE` (contamination + unverified cost). See
`readouts/20260714_HYP_PORTFOLIO_COMPOSE_001_PHASE0_ARTIFACT_ATTACH_READOUT.md`.

## Next

Park this ID. Need new independent thesis or Owner Real/QFSI for parked seeds. Do not retune London ORB parameters from this screen.
