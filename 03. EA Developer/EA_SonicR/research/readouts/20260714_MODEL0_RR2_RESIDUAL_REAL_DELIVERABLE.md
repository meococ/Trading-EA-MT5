# Deliverable — Model 0 RR2 sau Owner clear Real (re-verify)

Date: 2026-07-14 ~22:10 ICT  
Process: no GPT; no densify; no kill Owner Real

## Verdict

`MODEL0_RR2_NOT_RUN__RESIDUAL_REAL_TERMINAL64_STILL_ALIVE`

## 1) Terminal check

| Field | Value |
|---|---|
| Owner claim | Đã tắt hẳn MT5 Real (~22:08) |
| Observed | **còn** `terminal64` PID **41396** |
| Path | `C:\Program Files\MetaTrader 5\terminal64.exe` |
| Server | `FivePercentOnline-Real` |
| Login | **26451822** |
| StartTime | **2026-07-14 22:08:20** (cùng phút Owner báo đóng) |
| Responding / WS | **true** / ~336 MB |
| Prior blocked PIDs | 37816 → 6596 → **41396** |
| Kill? | **Không** — không phải zombie |

Receipt: `preflight/20260714_MODEL0_RR2_RESIDUAL_TERMINAL.json`

## 2) Model 0 RR2

| Field | Value |
|---|---|
| Hypothesis | `HYP-SB-MAXKZ2-RR2-FRICTION-001` |
| New `run_id` | **null** (không launch alpha.ps1) |
| Baseline on disk | `20260714_194221` / twin `20260714_194548` |
| Real cost frozen | P50 **~$2.3088**/trade (QFSI reprice receipt) — sẵn sàng haircut sau khi run mới land |

## 3) vs GOAL (chưa có run mới)

Không có metrics mới. Baseline + offline Real P50 vẫn là evidence cũ (stress PASS diagnostic; not confirmed / not GOAL).

## 4) Owner action (1 dòng)

**Đóng hẳn cửa sổ MT5 Real (PID 41396 / login 26451822) tới khi `Get-Process terminal64` = 0, rồi bảo agent chạy lại Model 0 RR2.**

## 5) hot.md?

Updated: residual Real blocker PID 41396; Model0 RR2 `run_id=null` this attempt.
