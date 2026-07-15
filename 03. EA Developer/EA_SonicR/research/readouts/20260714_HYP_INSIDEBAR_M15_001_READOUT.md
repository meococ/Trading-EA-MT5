# Readout — HYP-INSIDEBAR-M15-001 / EA_M15InsideBreak

Date: 2026-07-14  
State: `killed` (Model 0 screen; PF fail + cadence below floor)

## Run

| Field | Value |
|---|---|
| run_id | `20260714_001710` (sibling folder `20260714_001629` may be twin) |
| EA | `EA_M15InsideBreak` |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified) |
| History quality | 99% |
| Path | `02. AlphaFactory/runs/EA_M15InsideBreak/20260714_001710/` |

## Metrics (tester report)

| Metric | Value |
|---|---|
| Profit factor | **0.96** |
| Total trades | **308** |
| Net profit | **-329.99** |
| Expectancy | **-1.07** |
| Elapsed calendar weeks | ≈ 260.71 |
| Trades/week (elapsed) | 308 / 260.71 ≈ **1.18** |

## Verdict

- **Cadence:** **FAIL** prereg floor (1.18 < 1.5; also < GOAL 2.0). Seed sparsity not cured by a priori KZ densification.
- **Edge:** PF 0.96, negative expectancy/net → **KILL**.
- **Cost honesty:** research-proxy tester spread only.
- Ceremony: `includes_sha256` mismatch after report ready (known AlphaFactory closeout flake); artifacts retained.

## Banned rescue

Do **not** mine IB ATR thresholds, KZ hours, day skips, or H1 sparse sleeve from this readout. Independent next ID only.

## Next

Close this ID. Prefer independent non-IB mechanisms still open on backlog; SB weekend-flat remains the only research survivor near GOAL PF (cadence still short).
