# Deliverable — QFSI accumulate + Model 0 RR2 parallel path

Date: 2026-07-14 ~21:10 ICT  
Process: no GPT; no kill Owner Real; no densify MaxKZ/RR

## Verdict

`MODEL0_RR2_HARD_BLOCKED__QFSI_ACCUMULATING__OFFLINE_RR2_ROBUST_PASS_DIAGNOSTIC`

## 1) Parallel Model 0 path?

**Không có path an toàn đã ship.**

| Check | Result |
|---|---|
| `alpha.ps1` `Assert-NoUnrelatedTerminal` | Fail-closed nếu còn bất kỳ `terminal64` không do runner sở hữu |
| Portable / terminal2 / `/config` riêng | **Chưa implement** trong runner |
| PHASE0 dedicated tester lane | Planned only (`PHASE0_HARDENING_PLAN.md` W2) |
| Owner Real PID | **37816** `C:\Program Files\MetaTrader 5\terminal64.exe` — agent **không** kill |

→ Model 0 RR2 **không chạy được** khi Owner giữ Real. `run_id` = **null**.

Receipt: `preflight/20260714_MODEL0_RR2_PARALLEL_BLOCKER.json`

### Owner action (1 dòng)

**Owner: đóng tạm terminal Real (hoặc cho phép cửa sổ exclusive tester) rồi bảo agent chạy Model 0 RR2 — alpha.ps1 chưa có portable song song an toàn; agent không kill Real.**

## 2) QFSI progress (Real login giữ nguyên)

| Capture | Status | Quotes | HB | Comm | Slip |
|---|---|---:|---:|---:|---:|
| `…_001` | ended PARTIAL | 1313 | 276 | 2 | 0 |
| `…_002` | ended PARTIAL | 421 | 440 | 0 | 0 |
| `…_003_CONTINUATION` | started, no session_end (superseded by 004) | — | — | 2 | 0 |
| `…_004_CONTINUATION` | **COMPLETE PARTIAL** (20min) | **2267** | **2296** | 2 EURUSD | 0 |

Full QFSI vẫn **`STOP_DATA_FRONTIER`**: 90d quotes / ≥30 commission/symbol / ≥100 slippage fills unmet. Passiveive capture **không** tạo slippage fills; missing slip ≠ 0. Sibling lane may keep `…_004_EXTENSION` running for longer accumulate — does not clear gates this session.

`COST_PROVENANCE_GAP` = **NARROWED_NOT_CLEARED**

## 3) Offline validation còn hợp lệ (không cần Model 0 mới)

RR2 `20260714_194221` + frozen Real P50 haircut `$2.308758/trade`:

| Metric | Value |
|---|---|
| PF x1 / x1.5 / x2 | **1.323 / 1.297 / 1.271** (GOAL cost-stress PASS diagnostic) |
| MC shuffle P95 DD | **~2.37%** (2000 sims; diagnostic-only) |
| Half-sample PF P50 | **~1.33** |
| Year PF (x1) | 2021–2025 all >1.17; conc ~0.23 |
| `promotion_eligible` | **false** |

Artifact: `preflight/20260714_RR2_REAL_P50_OFFLINE_ROBUSTNESS.json`  
SHA256 `06BAAD5FA56FF719492BA2856ECEC64C97D2C0A18132870CCF20E51058A4A4EF`

MaxKZ2 vẫn PARK/FAIL under same cost — **không densify**.

## 4) vs GOAL

| GOAL chiều | Trạng thái |
|---|---|
| PF>1.30 after verified cost | Research-proxy / partial-Real PASS on RR2 only — **not confirmed** |
| 2–5 trades/wk | RR2 ~2.01 OK research |
| Cost stress x1.5/x2 | RR2 PASS under partial Real P50 — full QFSI open |
| Confirmed / portfolio-sleeve | **Blocked** (contamination + cost provenance) |

## 5) hot.md

Updated this turn: Model 0 parallel = hard block; QFSI 004 accumulating; offline RR2 robust diagnostic landed; Owner action one-liner.
