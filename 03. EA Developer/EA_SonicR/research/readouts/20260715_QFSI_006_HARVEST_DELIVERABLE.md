# Deliverable — QFSI 006 harvest after ETA watch

Date: 2026-07-15 ~03:00 ICT  
Authority: Owner CONTINUE — harvest 006 / rebind only on GO  
GPT: waived · Grok · no-Git · cost honesty absolute · Real protected

## Verdict

**`REAL_ON__QFSI_006_EARLY_EXIT__REBIND_HARNESS_ARMED__STOP_DATA_FRONTIER`.**

006 did **not** complete a clean 4h window. Last write ~**01:09 ICT**; PID 62392 gone by ~**02:58 ICT**; no `session_end.json` / manifest. Gate still **STOP**. **No** `--execute` rebind. GOAL unmet. Demo/partial PF ≠ confirmed.

Status receipt SHA `0A19C5D48DDE302763E7A8B34483FD0A411506CC50B6BBF3A6609451618B6C28`  
Path: `preflight/20260715_QFSI_006_HARVEST_STATUS_RECEIPT.json`

## 1) Real (do not kill)

| Item | Value |
|---|---|
| Server | `FivePercentOnline-Real` |
| terminal64 | PID **15444** ALIVE |
| 006 PID | **62392** EXITED early |
| Orders | 0 (passive read-only) |

## 2) 006 rows (this capture only)

| Symbol | Quotes | HB | Comm unique | Slip |
|---|---:|---:|---:|---:|
| USDJPY | 1286 | 1932 | 0 | 0 |
| EURUSD | 1028 | 1932 | 2 | 0 |
| GBPUSD | 1510 | 1932 | 0 | 0 |
| XAUUSD | 1929 | 1932 | 0 | 0 |

## 3) Aggregate frontier (all QFSI captures) — unchanged gate

| Gate | Now | Need | Remaining |
|---|---:|---:|---:|
| Quote distinct UTC days | **1** (2026-07-14) | 90 | **~89 calendar days** |
| Commission unique EURUSD | **2** | ≥30 | **28** (USDJPY/GBP/XAU still 0) |
| Slippage fills / symbol | **0** | ≥100 | **100** — MISSING ≠ 0 |

Honest: a 4h window (even if clean) **cannot** clear 90 calendar quote-days. Early exit did not change the frontier.

## 4) What changed after 006

- Quote days: **unchanged** 1/90
- Commission / slip: **unchanged**
- Gate: still `STOP_DATA_FRONTIER`
- Partial shelf RR2 `194548` 1.316/1.286/1.257: **not** confirmed-grade
- Owner deal-export drop: **0** new files → no ingest

## 5) Rebind harness

- Armed: `02. AlphaFactory/tools/qfsi_rr2_fullcost_rebind_harness.py`
- Status check: `HARNESS_ARMED__GATE_STOP` (receipt SHA `B903DE69AEB3DFE3A9F00E00D620EACDD92B0138983297FBE33753359ADCFF8B`)
- **`--execute` NOT run** (gate ≠ GO)

## 6) vs GOAL (VN parent)

GOAL cần PF>1.30 sau **cost thật đã xác minh**, x1.5≥1.25, x2≥1.00, cadence 2–5/tuần, confirmed suite.  
Sau 006: cost provenance vẫn **PARTIAL**; full QFSI **STOP**; không gì tiến gần confirmed. Shelf partial ≠ GOAL.

## Next auto

1. Keep Real (PID 15444) — không kill.
2. Long accumulate lại khi an toàn (không Wave8 spam / densify / COT revive / price twins).
3. Owner deal-export → commission/slip (MISSING ≠ 0).
4. `--execute` rebind **chỉ** khi harness gate = GO.
