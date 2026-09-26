# HYP-VPA-EURUSD-M5-001 · REVISION DR1 — FROZEN PREREGISTRATION

Status: `FROZEN_PRE_OUTCOME / OUTCOME-BLIND CENSUS AND FIDELITY ONLY`
Campaign: VPA · Hypothesis: `HYP-VPA-EURUSD-M5-001` (registry state stays `probe`, D3)
Revision: `DR1` (detector revision; new frozen prereg per `WORKFLOW §6` — a
market-logic revision gets a new ID/file before any run; the registry row is not
touched because the hypothesis has not left `probe` and no state transition is legal
from `probe` except screened/parked/killed, none of which applies yet — D3).
Frozen at UTC: 2026-09-20 · Owner: Mèo Cọc · Lead: Claude · Worker: OpenCode
Authority: `LEAD_DECISIONS_DR1.md` (D1–D6, saved verbatim), `RULEBOOK.md`,
`GAP_VS_SPEC.md`, `VPA-DR1_SPEC_DRAFT.md`, `COST_FEASIBILITY.md`.
This task is outcome-blind (D6): no fills-to-exit, no PnL, no WR, no MFE/MAE.

## 1. Claim and scope

Một cú phá vỡ mô hình (Pattern Break, book tr. 87–110) hoặc biến thể entry-timing
Combi (tr. 124–140) là Volman-grade khi: barrier khoá trước đó, buildup nén sát
biên, signal bar đóng tại/qua biên **theo hướng lệnh**, entry là **stop order
1 pip qua signal bar**, thuận áp lực chủ đạo, room ≥2R, không chop, không đuổi.
DR1 chỉ executable **Pattern Break** và **Combi-trong-PB-context**. PR và TFF
**không** thuộc DR1.

## 2. Market contract

- EURUSD, M5 Bid, closed-bar; decision tại **close của signal bar**.
- Server clock = UTC+2/+3 (EU DST) như data plane; session theo **UTC**:
  **EU 07:00–11:00** (420–660 phút), **US 13:30–16:30** (810–990 phút).
- Geometry: **S=8 pips, TP=16 (b=2.0)**, entry buffer 1.0 pip, order valid V=3 bar.
- Không BE/trailing/partial/manual exit trong baseline; safety flats như cũ
  (news, Friday 20:00 server, daily 22:00 server) — không thuộc census này.

## 3. Entry semantics (D1a, book tr. 88, 95)

1. **Signal bar** `t_s`: bar đóng cửa **tại hoặc qua** barrier theo hướng lệnh
   (`d*(close − B) ≥ −0.05×ATR`), đóng cửa **theo hướng lệnh** (bearish cho short,
   bullish cho long; doji `|close−open| ≤ 0.10×range` được phép).
2. Anti-chase của signal: nếu `d*(close − B) > 0.25×ATR` (bar đã đi quá xa biên)
   → barrier bị coi là **missed break**, log `skip_missed_break`, không vào.
3. **Entry** = stop order: long `high[t_s] + 1.0 pip`, short `low[t_s] − 1.0 pip`;
   hiệu lực **V=3 bar**; hủy nếu giá phá invalidation
   (`buildup_low − 0.10×ATR` long / `buildup_high + 0.10×ATR` short) trước khi khớp.
4. Fill/adverse-cost semantics giữ nguyên spec (không tính trong task này).
5. Barrier chỉ sinh candidate khi **chưa** bị consume; executable đầu tiên consume
   barrier. Rejection không consume (bar sau có thể là signal bar hợp lệ).

## 4. Gates (thứ tự funnel cố định)

| # | Gate | Công thức | Default |
|---|---|---|---|
| G0 | warmup | `t ≥ 50` | 50 |
| G1 | session | EU 07:00–11:00 ∪ US 13:30–16:30 UTC | — |
| G2 | direction | long: `close>open` hoặc doji; short: `close<open` hoặc doji | doji ≤0.10×range |
| G3 | trend | `d*(EMA_t−EMA_{t−6})/ATR_t ≥ θ_slope` **và** `frac_side_d(10) ≥ 0.6` | θ=0.10 (grid {0.0,0.10}, D1c) |
| G4 | buildup (AND 4) | n∈[3,10] lớn nhất: (a) ≥2 close `d*(B−c)∈[−0.10A,+0.50A]`; (b) ≥1 `|extreme−B|≤0.10A`; (c) overlap≥0.45; (d) contraction≤0.85 | band 0.5, overlap 0.45 |
| G5 | chop | overlap≥0.65 ∧ prog≤1/3 ∧ (doji ∨ bar>1.5×ATR) trên 4 bar trước signal; **miễn trừ nếu G4 pass** | — |
| G6 | room | `room_r ≥ 2.0` từ entry tới pivot xác nhận/barrier active/mức tròn gần nhất phía trước | 2.0 (D1d) |
| G7 | adverse magnet | pivot low trong `(entry−0.5R, entry)` (long) hoặc mức tròn trong `(entry−R, entry)` → skip | 0.5R |
| G8 | anti-chase | `entry−B ≤ 0.35A`; `range(signal) ≤ 1.5A`; `|entry−EMA| ≤ 1.5A` | — |
| G9 | cost | `rho = c/S ≤ 0.20` | 0.125 |
| G10 | combi (classification) | signal bar là inside bar của strong bar `t−1` (strong: `d*(c−o) ≥ 0.35A`, `d*CLV ≥ 0.50`; inside: chứa trong t−1, `range_t/range_{t−1} ≤ 0.75`) → setup=combi, ngược lại pattern_break | — |

Feature (không gate): EMA-pressing squeeze (`|EMA−B| ≤ 0.6A` và ≥2 bar buildup có
range chứa EMA); pressure 4 thành phần (giữ làm feature/score).

### D1d rationale cho 2.0R (bắt buộc ghi)

Book tr. 167: bỏ lệnh nếu vật cản chỉ để lại **<14 pip lợi nhuận tính từ entry**;
với target 20 pip, ngưỡng book-literal = 14/20 = **0.7×target = 1.4R**. Nhưng luật
này gắn với **resistance exit thủ công**: nếu vật cản ở 1.4R, sách thoát tại vật
cản (14 pip) thay vì để giá chạy tới 20. DR1 **không có manual exit** (bracket
cố định, b=2.0), nên vật cản ở 1.4R sẽ chặn target 2R → phải yêu cầu room đủ cho
target: **room_r ≥ 2.0** là bản thay thế hợp lý (bảo toàn kỳ vọng +2R).

## 5. Cadence rule (D2) — DESIGN 2016-01-01 → 2021-12-31

- ≥10 executable/tuần: normal.
- 3 đến <10: flag `LOW_CADENCE`, tiếp tục fidelity grading; **không** economic
  run; Lead escalates Owner.
- <3: STOP sau census; báo rejection funnel + recommendation.

## 6. Splits (không đổi)

DESIGN 2016–2021 (census + grading) · VALIDATION 2022–2023 · OOS 2024–2025.06 ·
FINAL HOLDOUT 2025.07–2026.09 (kín). Task này chỉ DESIGN.

## 7. Trial budget

- DR1 = **1 logic cell**. Grid calibration tối đa **16 tổ hợp**:
  `θ_slope∈{0.0,0.10}` × `band∈{0.35,0.5}` × `overlap∈{0.40,0.45}` × `expiry∈{12,20}`.
- **Task này chỉ chạy defaults** (θ=0.10, band 0.5, overlap 0.45, expiry 20); không grid.
- Economic gates giữ nguyên (`GOAL` + `COST_FEASIBILITY`): matched-random lift
  (x1 ≥ +14.1pp với S=8; x2 ≥ +18.2pp, 95% CI LB > 0), cadence 10–40/tuần,
  PF x1>1.30, x1.5≥1.25, x2≥1.00, gross PF≥1.10, b≥1.70, N≥500, DD≤6%,
  MC P95≤8%, HQ>97%.

## 8. Grading (D5) — chỉ khi cadence ≥3/tuần

- 120 case stratified-random theo năm từ tập executable DESIGN; snapshot 120 bar
  **kết thúc tại signal bar**, 0 bar sau.
- G1/G2 mù với `GRADING_RUBRIC_V2`; hash trước khi so; bất đồng → G3 majority.
- Precision A/B báo cả **dual-agreement** và **majority**, kèm Wilson 95% CI.
- Caveat lạm phát: grader lenient hơn Lead (A+B 33–42% vs 27%).
- Lead spot-check 20 case: 10 agreed-A/B, 5 disagreement, 5 agreed-C;
  `LEAD_SPOTCHECK_INDEX.csv` chỉ có case_id + path, không grade/key.
- **D4**: 60 case Lead-labelled (P2b) là fixed drift-check set; không dùng để
  tune/select detector.

## 9. KILL / STOP

- Cadence <3/tuần → STOP (STATUS PARTIAL).
- Không implement được causal như spec → STATUS BLOCKED + clause cụ thể.
- Không outcome nào được tính trong task này (D6).
