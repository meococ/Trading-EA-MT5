# Readout — HYP-VOLEXP-M15-001 / EA_M15VolExpansion

Date: 2026-07-14  
State: `killed` (Model 0 screen; PF fail / no GOAL edge; cadence structurally OK)

## Authority / routing note

Owner free-MT5 backtest (2026-07-14) authorized compile/Model 0 without per-run approval.
`HYP-CHOP-TREND-M15-001` was **fail-closed at intake** as ChopRegime `KILL_FAMILY` twin
(`readouts/20260714_HYP_CHOP_TREND_M15_001_DEDUP_FAIL_CLOSED.md`). This ID is the
already-contracted independent next (`S639` VolCluster RV-expansion; no CI).

## Run

| Field | Value |
|---|---|
| run_id | `20260714_000432` (authoritative; report byte-identical to sibling `20260714_000211`) |
| EA | `EA_M15VolExpansion` |
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
| Profit factor (`Hệ số lợi nhuận`) | **1.01** |
| Total trades (`Tổng số giao dịch`) | **741** |
| Total net profit (`Tổng lợi nhuận ròng`) | **+126.50** |
| Expectancy (`Mức lợi nhuận mong muốn`) | **0.17** |
| Max balance DD | 14.36% |
| Win rate | 40.76% (302/741) |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 741 / 260.71 ≈ **2.84** |

Artifacts: `02. AlphaFactory/runs/EA_M15VolExpansion/20260714_000432/`  
Parsed: `analysis/parsed_metrics_probe.json`

## Verdict

- **Cadence:** inside GOAL band 2–5/week (2.84). Density viable after a priori Mon–Thu / weekend-flat transfer.
- **Edge:** PF 1.01 ≈ breakeven → **KILL**. Does not approach GOAL PF > 1.30 after tester friction.
- **Cost honesty:** missing/zero broker commission/slippage provenance; do not treat this PF as verified after-cost. Even under tester defaults the book has no meaningful edge.
- **Ceremony blocker:** `alpha.ps1` closeout threw `includes_sha256` mismatch after report ready (same class as cadence-book / TickVolImpulse). Artifacts remain usable for screen readout.

## Independence note

Near-miss seed was S639 VolCluster (PF~1.21 with day mining). This a priori Mon–Thu / `[08,17)` / weekend-flat / no-CI transfer preserved cadence but **did not** preserve edge. Not hour-open-break, not TickVolImpulse, not ChopRegime EMA-cross. Do **not** mine RV thresholds / body bars / hours / days from this readout.

## Next (allowed)

1. Close `HYP-VOLEXP-M15-001` as killed.
2. Do **not** open `HYP-CHOP-TREND-M15-001` (fail-closed twin of ChopRegime `KILL_FAMILY`).
3. Do not retune USBILL survivor; Model 0 still needs Owner login `FivePercentOnline-Real` + QFSI (shortest path to confirmed exogenous sleeve).
4. Next price-M15 ID must be a **new independent** mechanism (not VolCluster/Chop/HourOpen/TickVol rescue).
