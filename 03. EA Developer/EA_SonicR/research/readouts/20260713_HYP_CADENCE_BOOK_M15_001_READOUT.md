# Readout — HYP-CADENCE-BOOK-M15-001 / EA_M15HourOpenBreak

Date: 2026-07-13  
State: `killed` (Model 0 screen; PF fail; cadence structurally OK)

## Run

| Field | Value |
|---|---|
| run_id | `20260713_234653` |
| EA | `EA_M15HourOpenBreak` |
| Symbol / TF | EURUSD M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified cost) |
| History quality | 99% |
| Bars / ticks | 124208 / 97115124 |

## Metrics (tester report, Vietnamese labels)

| Metric | Value |
|---|---|
| Profit factor (`Hệ số lợi nhuận`) | **0.94** |
| Total trades (`Tổng số giao dịch`) | **829** |
| Net profit | **-1445.39** |
| Gross profit / gross loss | 21389.98 / -22835.37 |
| Max equity DD | 21.85% |
| Win rate | 39.81% |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 829 / 260.71 ≈ **3.18** |

## Verdict

- **Cadence:** inside GOAL band 2–5/week (3.18). Mechanism density is viable.
- **Edge:** PF 0.94 < 1.00 and < GOAL 1.30 → **KILL**. Negative expectancy after tester friction.
- **Cost honesty:** missing/zero broker commission/slippage provenance; do not treat this PF as verified after-cost. Even so, the book loses under tester defaults.
- **Ceremony blocker:** `alpha.ps1` closeout failed after report ready on `includes_sha256` mismatch (`0878535C…` recorded vs `5F918C44…` recomputed). Artifacts under `02. AlphaFactory/runs/EA_M15HourOpenBreak/20260713_234653/` remain usable for screen readout. Stale unrelated `terminal64` PID was stopped once to unblock Assert-NoUnrelatedTerminal.

## Independence note

Near-miss seed was S678 H1OpenBreak (PF~1.21 USDJPY M5). This EURUSD M15 closed-bar transfer preserved cadence but **did not** transfer edge. Not a V2–V8 lock-list member; not a post-hoc rescue of carry.

## Next (allowed)

1. Close `HYP-CADENCE-BOOK-M15-001` as killed — do **not** mine hour/day/CI/buffer from this readout.
2. Next candidate must be a **new** hypothesis ID (independent mechanism or a priori child with frozen param budget), still targeting 2–5/week structural cadence.
3. Optional engineering: fix include-set hash stability in `Complete-RunManifest` so future screens close cleanly.
