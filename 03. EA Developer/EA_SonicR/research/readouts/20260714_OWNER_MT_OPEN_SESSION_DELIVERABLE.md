# Owner MT-open session deliverable — 2026-07-14 ~00:40 ICT

Status: **GOAL unmet** / price-M15 shelf EMPTY / Real QFSI still Owner-only

Authority: Owner 2026-07-14 free MT backtest + self-direct to GOAL; GPT waived;
documented tester-`current` research-proxy cost for Model 0 screens (≠ confirmed).

## 1) MT5 / AlphaFactory runs (tonight)

| hypothesis_id | EA | run_id | path | PF | tpw | verdict |
|---|---|---|---|---|---|---|
| HYP-VOLEXP-M15-001 | EA_M15VolExpansion | 20260714_000432 | `02. AlphaFactory/runs/EA_M15VolExpansion/20260714_000432/` | 1.01 | ~2.84 | **KILL** |
| HYP-CHOP-TREND-M15-001 | EA_M15ChopTrend | 20260714_001121 | `.../EA_M15ChopTrend/20260714_001121/` | 1.08 | — | **FAIL_CLOSED** (family) |
| HYP-GOLDJPY-LEAD-M15-001 | EA_M15GoldJPYLead | 20260714_001343 | `.../EA_M15GoldJPYLead/20260714_001343/` | ~0.97 | — | **KILL** |
| HYP-INSIDEBAR-M15-001 | EA_M15InsideBreak | 20260714_001937 | `.../EA_M15InsideBreak/20260714_001937/` | 0.96 | ~1.18 | **KILL** |
| HYP-SB-WEEKEND-FLAT-001 | EA_SilverBullet | 20260714_002046 (ctrl) / 20260714_002505 (chall) | `.../EA_SilverBullet/` | 1.33 / **1.34** | ~1.99 | **PARK** |
| HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001 | EA_UsBillSlopeBasket | 20260714_001458 (ctrl) / 20260714_002655 (chall) | `.../EA_UsBillSlopeBasket/` | 1.05 / **1.03** | ~1.03 / ~0.90 | **KILL** |
| HYP-SPARK-ASIAN-M15-001 | EA_M15SparkAsian | 20260714_002614 | `.../EA_M15SparkAsian/20260714_002614/` | **1.31** | ~1.25 | **PARK** near-miss |
| prior | EA_M15TickVolImpulse | 20260713_235635 | `.../EA_M15TickVolImpulse/` | 1.00 | ~3.41 | **KILL** |
| prior | EA_M15HourOpenBreak | 20260713_234653 | `.../EA_M15HourOpenBreak/` | 0.94 | ~3.18 | **KILL** |

Cost label for all: **UNVERIFIED_TESTER_DEFAULT** / MetaQuotes-Demo research-proxy.
Missing commission/slippage ≠ 0. Not Real QFSI.

## 2) USBILL identity

- hypothesis_id: `HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001`
- prereg: `preregs/20260713_H_FX_USBILL_SLOPE_USD_BASKET_001_PREREG.md`
- EA: `03. EA Developer/EA_UsBillSlopeBasket/EA_UsBillSlopeBasket.mq5`
- Model 0 readout: `readouts/20260714_HYP_SR_FX_USBILL_SLOPE_USD_BASKET_001_MODEL0_READOUT.md`
- Offline probe survivor is **archival only**; Model 0 kill is authoritative.

## 3) Gate vs GOAL

| GOAL gate | Closest parked | Gap |
|---|---|---|
| PF > 1.30 after verified cost | SB 1.34 / Spark 1.31 (tester only) | **cost provenance** |
| 2–5 trades/elapsed week | SB ~1.99; Spark ~1.25 | SB −0.01; Spark −0.75 |
| cost stress x1.5/x2 | not promotion-grade | blocked |
| confirmed window / MC | not run | blocked |

## 4) Survivor nearest target

**`HYP-SB-WEEKEND-FLAT-001` / `20260714_002505`** — PF 1.34, ~1.99/wk.
Nearest dual-gate miss: cadence micro-short + **no Real cost**.
Spark is second (PF OK, cadence worse).

## 5) Next

| Who | Action |
|---|---|
| Agent | New independent thesis only (shelf EMPTY). No kill-list rescue. No GPT. |
| **Owner-only** | Login `FivePercentOnline-Real` + QFSI cost capture |

## 6) hot.md

Updated 2026-07-14 ~00:40 ICT: USBILL Model0 kill authoritative; shelf EMPTY;
SB/Spark park distances; Owner Real blocker explicit.
