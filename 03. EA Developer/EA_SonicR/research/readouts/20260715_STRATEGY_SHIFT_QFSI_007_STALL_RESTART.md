# STRATEGY SHIFT — QFSI 007 stall diagnosis + restart

Date: 2026-07-15 ~13:05 ICT  
Status: `QFSI_007_STALL_ROOTCAUSED__RESTARTED_72H__COST_GATE_STILL_STOP`  
Authority: Owner STRATEGY SHIFT Track B (autonomous cost push)  
No invented spreads. No `--execute` rebind.

## Root cause (007 stall)

| Check | Result |
|---|---|
| Watcher PID 48432 / capture 59040 | **DEAD** at diagnosis (~13:01 ICT) |
| Real `terminal64` 27096 | **ALIVE** / connected `FivePercentOnline-Real` / login 26451822 |
| Stop file | Absent at diagnosis |
| Last successful heartbeats | ~2026-07-15T02:19:38Z (`hb≈9480`, `quotes≈6586`) then silent |
| Historic stderr killer | `TypeError: log() got multiple values for argument 'path'` when `log(..., path=stop_file)` collided with positional `path` |
| Silent mid-segment death | Watcher orphaned after 01:39Z relaunch (no `capture_exited` / `watcher_exit`); capture died ~40m later without auto-restart |

**Ruled out:** Owner policy block, auth drop at diagnosis, missing Real terminal.

**Not lawful accelerators:** historical `copy_ticks_range` without PASSIVE_HEARTBEAT (= `BROKER_HISTORY_UNVERIFIED`); inventing spreads; Owner deal-export still empty.

## Local fixes applied

1. `qfsi_007_long_accumulate_watcher.py`
   - Defensive `log()` strips/remaps kwargs `path`/`event` collision
   - Wall **72h** (was 24h)
   - Stall grace **300s** after launch before mtime stall checks
   - Watcher self-heartbeat JSON every poll
   - Max restarts 96
2. Relaunch via `qfsi_007_breakaway_bootstrap.py` (no stop file)

## Restart evidence

| Item | Value |
|---|---|
| Watcher PID | **75476** |
| Capture PID | **72320** |
| Real terminal | **27096** (do not kill) |
| Capture id | `20260715_QFSI_REAL_007_LONG_ACCUMULATE` (continue same dir) |
| Wall | 259200s (72h) |
| Mode | PASSIVE_READ_ONLY_NO_LIVE_ORDERS |

## Cost gate honesty

- Quote-days still ≪90 (calendar heartbeat continuity required).
- Commission/slip still need Owner deal-export drop (empty at restart).
- Rebind harness remains `HARNESS_ARMED__GATE_STOP` — **`--execute` NOT run**.
- Login is operational detail, **not** headline.

## Next

Keep Real + watcher + capture. Do not recreate STOP casually. Owner deal-export when available. Track A portfolio discovery continues offline without waiting for QFSI.
