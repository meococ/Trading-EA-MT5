# Deliverable VN — Discovery offline ngoài V1–V6 (V8)

Cập nhật: 2026-07-14 · Agent: Grok 4.5 High Fast · GPT cấm · No-Git

## Verdict

**`FAIL_CLOSED / OFFLINE_V8_ALL_KILL / NO_MODEL0`.**  
Net-new ngoài kill shelf = **2/2 KILL** (EURGBP→EURUSD lead; AUD overlap fail-fade).  
H1–H3 coil/retest/dayfade đã bị parallel V7 kill trước — V8 chỉ confirm, không tính thesis mới. Không densify; không spam twin.

## Objects thử

| # | hypothesis_id | Vai trò | HIT/KILL |
|---|---|---|---|
| 1–3 | MONO / BROKEN-LEVEL / FORMING-DAY | Confirm V7 coil lane (đã KILL) | **KILL** lại (x1.5 &lt;1.25; Real~$2.31 không cứu) |
| 4 | `HYP-EURGBP-H1-LEAD-EURUSD-H1-001` | **Net-new** cross-lead ≠ GBPJPY | **KILL** PF 0.92 / 0.79/wk |
| 5 | `HYP-AUDUSD-H1-OVERLAP-FAIL-FADE-001` | **Net-new** fail-fade ≠ EUR continue-break | **KILL** N=1 starve |

Cùng đêm (context, không reopen): JPY-cross catch-up offline KILL; RR2 fresh Model 0 `231750` **PARK_MISS** PF 1.156 + Real P50 FAIL; V7 multi-sym ALL KILL; Wave3 0/3 KILL.

## Cost proxy

- +$12×1.5 (Demo friction): không object nào ≥1.25.
- Real P50 ~$2.31 (partial, not QFSI): mono/retest ~1.06/1.03 — vẫn miss GOAL stress; lead/dayfade &lt;1.

## Gap GOAL

| Chiều | Gap |
|---|---|
| PF&gt;1.30 sau cost thật | Không survivor; `231750` PF 1.156 + Real P50 FAIL |
| 2–5/wk | Không book đạt dual gate |
| Cost stress | Full QFSI vẫn `STOP_DATA_FRONTIER` |
| Confirmed 84m | Không mở |

## Surface BLOCKED (agent-executable)

Price V1–V8 / Wave3–5 / SB-Spark-ITSM densify / exogenous carry-COT-bond-OIS-VIX / SOFR−SONIA twin / Phase-0 freeze — **EMPTY hoặc cấm**.

## Files

- `readouts/20260714_STRUCTURAL_V8_DEDUP_CLEARANCE.md`
- `preflight/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V8.{py,json}` + readout MD
- Closeout: `readouts/20260714_STRUCTURAL_REBUILD_V8_SESSION_CLOSEOUT.md`
- SHA: `A44893E0210258DC01F54097B2D0D4F3EDE27D19F715C2179CAB1F92865565CF`

## Next tối ưu

1. Giữ Real quote accumulate + QFSI hygiene (không stall discovery vì full 90d; cũng không pretend cost đã clear).
2. Owner-sourced data mới (forward / flow / PIT) trước khi mint exogenous ID.
3. Không densify RR/MaxKZ/`231750`; không twin spam price-pattern thêm nếu không có mechanism memo mới.
