# Readout — HYP-TICKVOL-IMPULSE-M15-001 / EA_M15TickVolImpulse

Date: 2026-07-13  
State: `killed` (Model 0 screen; PF fail / no edge; cadence structurally OK)

## Run

| Field | Value |
|---|---|
| run_id | `20260713_235635` |
| EA | `EA_M15TickVolImpulse` |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified cost) |
| History quality | 99% |
| Bars | 124212 |

## Metrics (tester report, Vietnamese labels)

| Metric | Value |
|---|---|
| Profit factor (`Hệ số lợi nhuận`) | **1.00** |
| Total trades (`Tổng số giao dịch`) | **890** |
| Total net profit (`Tổng lợi nhuận ròng`) | **-109.56** |
| Gross profit (`Lợi nhuận ròng`) / gross loss (`Mức lỗ ròng`) | 27203.83 / -27313.39 |
| Expectancy (`Mức lợi nhuận mong muốn`) | **-0.12** |
| Max equity DD | 23.41% |
| Win rate | 40.79% (363/890) |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 890 / 260.71 ≈ **3.41** |

## Verdict

- **Cadence:** inside GOAL band 2–5/week (3.41). Density viable after removing S679 day/hour mining.
- **Edge:** PF 1.00 (breakeven/slight loss), negative expectancy, net −$109.56 → **KILL**. Does not approach GOAL PF > 1.30.
- **Cost honesty:** missing/zero broker commission/slippage provenance; do not treat this PF as verified after-cost. Even under tester defaults the book has no edge.
- **Ceremony blocker:** `alpha.ps1` closeout threw `includes_sha256` mismatch after report ready (same class as cadence-book). Artifacts under `02. AlphaFactory/runs/EA_M15TickVolImpulse/20260713_235635/` remain usable for screen readout. Unrelated `terminal64` was stopped to unblock Assert-NoUnrelatedTerminal.

## Independence note

Near-miss seed was S679 TickVolAccel (PF~1.25 USDJPY+ Europe Mon+Thu). This a priori Mon–Thu / `[08,17)` / weekend-flat transfer preserved cadence but **did not** preserve edge. Not hour-open-break, not carry, not fix/session Gotobi, not Sonic Classic rescue. Do **not** mine VolMult / BodyATR / CI / hours / days from this readout.

## Next (allowed)

1. Close `HYP-TICKVOL-IMPULSE-M15-001` as killed.
2. **Single next ID proposal:** `HYP-CHOP-TREND-M15-001` / `EA_M15ChopTrend` — independent transfer of STRATEGY_LOG `S630 / EA_ChopRegime` near-miss (PF~1.26, high N, WFA 5/5) with a priori no Mon/Wed/Thu day mining and Goal cadence window. Not a rescue of TickVolImpulse or cadence-book.
