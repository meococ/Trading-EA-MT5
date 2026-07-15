# Deliverable — QFSI 006 root-cause + 007 long accumulate relaunch

Date: 2026-07-15 ~08:42 ICT  
Authority: Owner CONTINUE — diagnose 006 early exit → robust long accumulate  
GPT: waived · Grok · no-Git · cost honesty absolute · Real protected · no `--execute`

## Verdict

**`REAL_ON__QFSI_006_ROOTCAUSED__007_LONG_LIVE__REBIND_HARNESS_ARMED__STOP_DATA_FRONTIER`.**

006 died early without auth drop. Local harness hardened. **007 long accumulate LIVE** on Real with watcher auto-restart. Gate still **STOP**. **No** `--execute`. GOAL unmet.

## 1) Root cause — QFSI 006 death

| Check | Result |
|---|---|
| Planned 4h complete? | No (~36 min of 240) |
| `session_end.json` / manifest? | Missing |
| Auth drop (`connected=0`)? | **No** — 0/1932 heartbeats |
| Server mismatch? | No at start (`FivePercentOnline-Real`) |
| Stderr available? | **No** — launched `DETACHED_PROCESS` + `DEVNULL` |

**Ruled out:** clean window complete, broker auth drop in heartbeats.

**Most likely:** capture Python exited mid-loop (uncaught exception / MT5 IPC contention from concurrent read-only probes / external kill) with crash reason discarded. Not a planned stop.

Post-mortem: `…/20260714_QFSI_REAL_006_ACCUMULATE/session_crash_inferred.json`

## 2) Local fixes applied

- `execution_data_qfsi_nolive_capture.py`: `session_crash.json`, `--max-ipc-retries 120`, tick soft-fail, progress marker
- `qfsi_007_long_accumulate_watcher.py`: 6h segments × 24h wall, auto-restart if Real OK, stdout/stderr logged, stall gate gated by `segment_started_at` (stale mtime bug fixed), stop-file kwarg fixed
- Bootstrap: `qfsi_007_breakaway_bootstrap.py`

## 3) Capture status — 007 LIVE

| Item | Value |
|---|---|
| Capture | `20260715_QFSI_REAL_007_LONG_ACCUMULATE` |
| Watcher PID | **48432** |
| Capture PID | **59040** |
| Real `terminal64` | **27096** (do not kill) |
| Server / login | `FivePercentOnline-Real` / `26451822` |
| Symbols | USDJPY → EURUSD → GBPUSD → XAUUSD |
| Mode | PASSIVE_READ_ONLY_NO_LIVE_ORDERS |

**Ops caution:** Do **not** recreate `preflight/20260715_QFSI_007_STOP.request` unless Owner wants halt (a Model0 pause file previously aborted relaunch). Avoid heavy concurrent `copy_ticks` on the same Real IPC.

## 4) How quote-days grow (honest)

Per `20260713_EXECUTION_DATA_ACQUISITION_CONTRACT_V1.md`:

- QFSI needs **≥90 elapsed calendar days** with **PASSIVE_HEARTBEAT** continuity (connected ≥95%, gap ≤60s).
- Harness currently shows **2/90** distinct UTC quote days (calendar rolled; still ≪90).
- **Historical `copy_ticks_range` without heartbeat = `BROKER_HISTORY_UNVERIFIED`** — discovery only, **not** lawful to clear the QFSI gate.
- This Real terminal only yields ~2 tick-history days; bulk multi-month `copy_ticks` hangs — cannot accelerate 90d that way.
- **Commission ≥30 / slip ≥100:** still need **Owner deal-export** (drop path below) + side-referenced fills. `MISSING` slip ≠ 0.

Owner drop: `02. AlphaFactory/evidence/execution/FivePercentOnline-Real/owner_deal_export_drop`

## 5) vs GOAL (VN parent)

GOAL cần PF>1.30 sau **cost thật đã xác minh**, stress x1.5/x2, cadence, confirmed suite.  
Cost provenance vẫn **PARTIAL**; full QFSI **STOP**; shelf RR2 `194548` partial ≠ confirmed. **Không tiến gần GOAL** cho đến khi quote-days + commission/slip đủ.

## 6) Rebind harness

- Armed; status `HARNESS_ARMED__GATE_STOP` (SHA `A72CFB81…2F11`)
- **`--execute` NOT run**

## Next auto

1. Keep Real PID 27096 + watcher 48432 / capture 59040  
2. Do not write 007 STOP unless Owner halt  
3. Owner deal-export → commission/slip  
4. `--execute` rebind **only** on GO  
5. No Wave8 / densify / COT / price twins  

Receipt SHA `5B5CB4A4045D697DAC7A270DBB5D58E68F85510B5DDFAD551456C75858C55D02`  
Path: `preflight/20260715_QFSI_006_DIAG_007_RELAUNCH_RECEIPT.json`
