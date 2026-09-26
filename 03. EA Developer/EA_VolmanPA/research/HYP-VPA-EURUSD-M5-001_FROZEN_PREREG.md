# HYP-VPA-EURUSD-M5-001 — FROZEN PREREGISTRATION (v1)

Status: `FROZEN_PRE_OUTCOME / SCREENED / NO LIVE OR DEMO AUTHORITY`
Campaign: VPA (Bob Volman price-action, `EA_VolmanPA`)
Frozen at UTC: 2026-09-20T01:47Z
Owner: Mèo Cọc · Lead: Claude · Worker: OpenCode (em)
Authority: `01. GOAL/GOAL.md`, `05. Playbook/WORKFLOW.md`, Lead review v1
(`PLAN/RESEARCH_PLAN.md §J`). This document binds the hypothesis contract; any
market-logic change after this point requires a new revision ID and a new frozen
prereg, and after outcome exposure requires a new generation.

---

## 1. Identity and claim

| Trường | Giá trị |
|---|---|
| Hypothesis ID | `HYP-VPA-EURUSD-M5-001` |
| EA name (planned) | `EA_VolmanPA` |
| Symbol / TF | `EURUSD` / `M5` |
| Feature family | `eurusd-m5-volman-pattern-break-locked-barrier-buildup-stopentry-fixed2r` |
| Claim | Một favorable break của một **locked horizontal barrier** (được khoá từ bar đã xác nhận trước đó) có xác suất sống qua cost cao hơn hẳn random entry cùng geometry, khi có **pressure leg** và **buildup contraction** trước break; payoff cố định 2R. |
| Đây KHÔNG phải | faithful replication của Volman, không phải 70-tick FPAS, không phải intrabar discretionary method. Là "Volman-inspired causal M5 adaptation". |
| Reference definitions | `PLAN/FEATURE_SPEC.md` (bản hoá các token); nguồn lawful: official UPA excerpt (author-hosted) + các định nghĩa T2 P2 đã QC (`PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:43-213`). |

## 2. Market contract (frozen)

- Decision time: **close của bar M5 đã hoàn tất**; mọi state chỉ dùng bar `≤ t`.
- Data: MQ-Demo research plane, Bid OHLC, bar `suspect` bị loại (data plane —
  roll 00:00–00:15…).
- Clock: server = UTC + 2h/+3h (EU DST). Sessions trong **UTC**:
  **London primary = 05:00–11:00** (UK open 08:00 ±3h);
  **NY secondary = 11:30–17:30** (US open 14:30 ±3h).
- Không trade Friday sau **server 20:00**; daily flat **server 22:00**.
- Không giữ qua weekend; báo cáo `overnight`/`weekend` phải = 0.

## 3. Signal → order → exit (frozen)

1. **Signal bar** = bar đã đóng cuối cùng của setup (cùng chiều dự kiến, theo
   direction rule của FEATURE_SPEC 2.15).
2. **Stop-entry:** đặt buy-stop tại `high_signal + 1.0 pip` (long) / sell-stop
   tại `low_signal − 1.0 pip` (short). Hiệu lực **V = 3 bar** M5 kể từ bar kế
   signal bar; hết hạn → cancel. Hủy ngay nếu giá phá invalidation trước fill.
3. **Fill:** giá fill thực (tester/live). Nếu fill xa mức stop > 0.3×ATR → đóng
   ngay và log `SKIP_ENTRY_GAP_RECHECK` (không second-best).
4. **Bracket cố định:** SL = fill − **S = 8.0 pips**; TP = fill + **2S = 16.0
   pips** (b = 2.0). Không BE, không trailing, không partial, không manual exit
   trong baseline. Ngoại lệ an toàn duy nhất: news blackout flatten, daily flat,
   Friday flat, risk locks.
5. **Invalidation gốc** (dùng để hủy lệnh chưa khớp): biên buildup (low của
   buildup cụm cho long / high cho short) trừ/ cộng buffer nửa ATR — chi tiết
   khoá trong detector spec P2; không được thay đổi sau outcome.
6. **Risk:** 0.5%/trade; volume làm tròn xuống theo step; min-lot vượt budget →
   `SKIP_MIN_LOT_RISK_REJECT`. **Prop locks (dưới The5ers):** daily loss lock
   **4.0%** đo bằng `max(balance, equity)` tại server midnight; max-DD lock
   **8.0%**; 5%/10% chỉ là test case.

## 4. Setup definition (frozen ở mức contract; chi tiết số ở FEATURE_SPEC)

Baseline arm: **Pattern Break** = locked barrier (touch-cluster, T_min=2) +
pressure (4 thành phần) + buildup (7 điều kiện) + room ≥ 2.0R + close-break
confirmation + signal bar + stop-entry. Combi và Pullback reversal là revision
candidates, **không** thuộc baseline.

Không dùng: tick volume như order flow; ER/ATR-ratio gates; rolling range làm
barrier; session-open range; sweep/reclaim; FVG/OB/MSS.

## 5. Splits (frozen)

| Split | Window | Vai trò |
|---|---|---|
| DESIGN | 2016.01.01 → 2021.12.31 | calibration + detector grading + baseline |
| VALIDATION | 2022.01.01 → 2023.12.31 | kiểm tra lần đầu sau freeze |
| OOS | 2024.01.01 → 2025.06.30 | mở 1 lần |
| FINAL HOLDOUT | 2025.07.01 → 2026.09.15 | kín tới khi freeze config |

## 6. Random-entry baseline (bắt buộc — falsification chính)

- Nguồn: `PLAN/random_baseline/RANDOM_BASELINE.csv`, SHA256
  `FDF252ECB76F0AC999835587DD71BC4335A1C84D7E3043C578FBAD79EE9C2215`.
- 12,000 mẫu/cell, seed `20260920`, semantics khớp mục 3 (stop-entry 1 pip,
  V=3, fill trên M1, adverse-first, cost dịch vào fill, time-exit rules như mục 2).
- Cell primary (EURUSD London S=8, x1): random WR = **29.8%**, b_obs = **1.99**,
  **required lift tại x1 = +14.1pp** (`reqW(PF1.30) − baseline WR`, dùng payoff
  thực đo được), **x2 = +18.2pp**.

## 7. Acceptance / KILL (frozen)

**G3 chính (lift over matched random):** `lift = WR_setup − WR_random` trên cùng
symbol, session, direction, bracket, cost tier, cùng DESIGN window.
PASS yêu cầu: **95% CI lower bound của lift > 0** VÀ **point lift ≥ required
lift** (x1: +14.1pp; x2: +18.2pp). Không đạt → KILL (không hạ chuẩn).

Kèm theo (giữ nguyên như plan):
- cadence **10–40 lệnh/tuần/symbol** (hard);
- PF x1 **> 1.30**; x1.5 **≥ 1.25**; x2 **≥ 1.00**;
- gross PF ≥ 1.10; payoff thực `b ≥ 1.70` (tính lại reqW theo `b_obs`; `<1.55` → KILL);
- N ≥ 500 DESIGN; historical DD ≤ 6.0%; MC P95 ≤ 8.0%; history quality > 97%;
- overnight ≈ 0, weekend = 0.

**KILL rules bổ sung:** baseline + **tối đa 2 market-logic revision**; hết budget
→ KILL hẹp. Executable cadence < 10/tuần → dừng và báo Lead (không tự nới).
Engineering defect → ENGINEERING_FIX cùng revision.

## 8. Calibration / trial budget

- Primary geometry chốt: **S = 8, London primary, NY secondary** (quy tắc R_S,
  `COST_FEASIBILITY §3b.3`).
- Grid calibration tối đa **16 tổ hợp/cell**: `S ∈ {8,10}` × `V ∈ {2,3}` ×
  `Room_min ∈ {1.5,2.0}` × `T_min ∈ {2,3}`; chọn plateau, không lấy đỉnh.
- Tổng trial budget: baseline + 2 revision = 3 logic cell; DSR/PBO khi > 20 cell
  kinh tế.

## 9. Veto budget (được phép và bắt buộc log)

Room, session window, news blackout ±20 phút, Friday/daily flat, spread gate,
risk locks. Mọi veto phải có counter riêng; không có free-text skip.

## 10. Trạng thái và điều kiện mở outcome

- P2 census outcome-blind (chưa chạy tại thời điểm freeze này).
- Outcome (kinh tế) chỉ được mở sau khi: G1 engineering gate pass + G2
  detector-fidelity pass + task packet/cost manifest bind.
- Không đọc OOS/holdout trước freeze config.

## 11. ASSUMPTION (không được lặng lẽ nâng thành fact)

- Server offset EU DST +2/+3 áp cho MQ-Demo 2016–2021 (chưa verify broker rule
  từng năm; sensitivity ±1h chưa đo).
- `c_rt p90` từ sidecar 3–4 ngày tick đại diện cho cả 6 năm DESIGN.
- Bracket semantics trên Model 0 có fill ambiguity (đã biết; xử lý theo plan §F.3).
- Setup detector chưa tồn tại; census P2 là điều kiện dừng/đi tiếp, không phải
  outcome.
