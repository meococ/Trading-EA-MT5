# Deliverable — Discovery Wave3 offline probe (Model 0 blocked)

Date: 2026-07-14
Authority: Owner continue independent discovery; no MaxKZ densify; no QFSI stall
GPT: waived

## Blocker Model 0

`alpha.ps1 backtest` fail-closed: `Unrelated terminal64` (Owner Real login).
Agent did **not** kill Real. Contracts rebuilt + compile OK; Model 0 not run.

## Offline closed-bar probe (NOT Model 0)

Server observed: `FivePercentOnline-Real` login `26451822`. Window 2021–2025. RR=3 / risk 0.5%.
Receipt SHA: `A513F7AE6E4B584F991B546B9A9FFDA6D8C006E100331332C599EB5A2F6163A7`

| ID | N | PF | tpw | Exp$/t | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-H4-OUTSIDE-REV-001` | 31 | 0.800 | 0.12 | -56.64 | **KILL** |
| `HYP-H4-ENGULF-REV-001` | 217 | 1.290 | 0.83 | 77.75 | **KILL** |
| `HYP-H1-PIN-PDLEVEL-001` | 21 | 0.945 | 0.08 | -17.47 | **KILL** |

## vs GOAL

GOAL needs Model 0 + verified cost. Offline HIT only ranks for exclusive Model 0.
KILL/PARK below follow prereg gates on offline metrics (honest proxy).

## Next

1. Model 0 Wave3 **đã chạy** (`221328`/`221546`/`221912`) — all **KILL**;
   không re-queue. Offline probe chỉ xác nhận hướng kill.
2. Không densify MaxKZ/RR / Outside/Engulf/Pin; không mine giờ/ngày.
3. Tiếp structural offline object mới (V3+), không QFSI-wait.

JSON: `preflight/20260714_DISCOVERY_WAVE3_OFFLINE_PROBE.json`  
Auth closeout: `readouts/20260714_DISCOVERY_WAVE3_OUTSIDE_ENGULF_PIN_CLOSEOUT.md`
