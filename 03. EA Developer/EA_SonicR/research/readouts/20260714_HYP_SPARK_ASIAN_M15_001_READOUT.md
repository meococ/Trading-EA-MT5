# Readout — HYP-SPARK-ASIAN-M15-001 / EA_M15SparkAsian

Date: 2026-07-14  
State: `parked` (Model 0 research survivor on edge; GOAL unmet on cadence)  
Process: `GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`

## Run

| Field | Value |
|---|---|
| run_id (authoritative) | `20260714_002821` |
| twin (same report SHA256) | `20260714_003314` (also `20260714_002614`) |
| report SHA256 | `7CAE7A9332B551FE58360E2B89022835F23E7706345ED2E7DC02F5122D80001A` |
| EA | `EA_M15SparkAsian` |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` (not broker-verified cost) |
| Seed | S111 Spark USDJPY+ PF~1.26 / ~71/yr; Tue–Wed a priori; weekend flat; risk 0.5% |

## Metrics (tester report + enhanced_summary)

| Metric | Value |
|---|---|
| Profit factor | **1.31** |
| Total trades | **325** |
| Total net profit | **+$1099.38** |
| Expectancy | **+$3.38** / trade |
| Max equity DD | **~3.2%** |
| Win rate | 56.0% |
| Elapsed calendar weeks | 1825/7 ≈ **260.71** |
| Trades/week (elapsed) | 325 / 260.71 ≈ **1.25** |

Session split (analysis): Europe 157 / PF 1.19; NY 168 / PF 1.46. Weekdays: Tue 168 / Wed 157 only (seed-faithful).

## Verdict

- **Edge:** PF 1.31 clears the research PF>1.30 screen under tester `current` spread. Net positive, low DD, expectancy positive. **Not** an edge kill.
- **Cadence:** **1.25/week** fails GOAL 2–5 and sits under the preferred ≥1.5/week historical bar. Seed-faithful Tue–Wed density is structural; Mon–Thu expansion is **banned** (S223 destructive; prereg lock).
- **Cost honesty:** missing/zero broker commission/slippage provenance; do not treat this PF as verified after-cost Real QFSI.
- **Ceremony:** `alpha.ps1` closeout may throw known `includes_sha256` mismatch after report ready; artifacts under `02. AlphaFactory/runs/EA_M15SparkAsian/` remain usable.
- **Disposition:** **PARK** as research survivor / cadence-limited. GOAL unmet. Do **not** mine hour/day/buffer/body from this readout (analysis flagged hour 11 as post-hoc weakness only).

## Independence note

Not Carry, HourOpen, VolExp, ChopTrend, GoldJPYLead, InsideBar, or TickVol rescue. Asian-range → LDN/NY breakout with D1 EMA50; closed-bar[1]; weekend flat.

## Next (allowed)

1. Keep `HYP-SPARK-ASIAN-M15-001` parked — no Mon–Thu / hour rescue child from this readout.
2. **Next local near-miss (≥1.5/wk historical preferred):** price-M15 denser dual-filter books from STRATEGY_LOG that cleared PF~1.2+ and ≥~1.5/wk are largely exhausted tonight (Chop/VolExp/TickVol/HourOpen/GoldJPY/InsideBar closed; SB parked at ~1.99/wk). Closest remaining denser-adjacent independent seed: **S639 / EA_VolCluster baseline** (PF~1.21, 417t Mon+Wed+Thu ≈1.0/wk — still under 1.5) already transferred and killed as VolExp. Prefer **USBILL** research Model 0 with honest Demo/tester cost label (cadence ~1/wk) or a new independent family only with fresh de-dup — not Spark day expansion.
