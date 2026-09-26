# VPA-DR1 SPEC DRAFT — detector revision 1 (for Lead approval; DO NOT CODE)

Status: `DRAFT_FOR_LEAD_APPROVAL`. Derived from `PLAN/book/RULEBOOK.md`,
`PLAN/book/GAP_VS_SPEC.md` and `PLAN/grading/G2_LEAD_ADJUDICATION.md`.
Giữ nguyên hai cổng bất biến: **matched-random lift** (`COST_FEASIBILITY §3b`)
và **cost-geometry gate**. Geometry tham chiếu: EURUSD, S=8 pips, TP=16 (b=2.0),
London primary.

## 1. Entry semantics (fix bắt buộc)

1. Decision tại **close của signal bar `t_s`** (bar chủ chốt đóng tại/xuyên biên).
2. Đặt stop order: long `entry = high[t_s] + 1.0 pip`; short `entry = low[t_s] − 1.0 pip`.
3. Hiệu lực `V = 3` bar M5; hủy nếu (a) hết hạn, (b) giá phá invalidation
   (`buildup_low − 0.1×ATR` cho long) trước khi khớp, (c) vượt session.
4. Break bar chỉ là bar **kích hoạt**; không dùng nó để chọn mức vào.
5. Fill: như cũ (adverse cost tại fill; recheck gap >0.3×ATR → skip ngày).

## 2. Preconditions (closed-bar, causal)

| Gate | Công thức | Default | Range |
|---|---|---|---|
| Trend alignment | `trend_d = d*(EMA_t−EMA_{t−6})/ATR_t ≥ θ_slope` **và** `frac_side_d(10) ≥ 0.6` | θ_slope=0.10 | 0.05–0.20 |
| Barrier | touch-cluster từ pivot xác nhận: T_min≥2, eps=0.10×ATR, scan 17, **expiry 20** | như cũ, expiry 20 | 12–30 |
| Buildup (AND rút gọn) | (a) ≥2 close trong `[B−0.5A, B+0.1A]`; (b) ≥1 bar `|extreme−B| ≤ 0.10A`; (c) `overlap_mean ≥ 0.45`; (d) `contraction ≤ 0.85` | như bảng | a: band 0.35–0.65; c: 0.40–0.55; d: 0.75–0.95 |
| EMA-pressing squeeze (feature, cộng điểm) | `|EMA_t − B|/ATR_t ≤ 0.6` và ≥2 bar buildup có range chứa EMA | 0.6 | 0.4–0.9 |
| Chop veto | `overlap≥0.65 ∧ prog≤1/3 ∧ (doji ∨ bar>1.5×ATR)` trên 4 bar trước signal; miễn trừ nếu đang trong buildup sát barrier | như cũ, hẹp hơn | — |
| Room | khoảng tới **pivot xác nhận gần nhất phía trước** hoặc biên congestion, `room_r ≥ 2.0`; đo từ entry | 2.0 | 1.5–3.0 |
| Adverse magnet | nếu mức tròn hoặc pivot nằm trong `[entry − R, entry]` → skip | bật | — |
| Anti-chase | `entry − B ≤ 0.35×ATR`; `range(signal) ≤ 1.5×ATR`; `|entry − EMA| ≤ 1.5×ATR` | như bảng | 0.25–0.5 / 1.2–2.0 |
| Session | EU 07:00–11:00 UTC + US 13:30–16:30 UTC; trưa 11:00–13:30 UTC = veto mềm (telemetry baseline) | — | — |
| Cost | `rho = c/S ≤ 0.20` (giữ nguyên) | 0.20 | — |

## 3. Pressure / features (không còn là gate)

- Bốn thành phần pressure (Disp/ER/MeanCLV/EMASlope) **giữ làm feature** và
  **score**; chỉ gate tối thiểu: không có bar ngược mạnh (`d*CLV ≤ −0.5` và
  `range ≥ 1.5×ATR`) trong cửa sổ buildup.
- Các feature buildup còn lại (progression, counter-ratio, n, squeeze,
  round-grid room) đưa vào score nếu mở scoring; **baseline DR1 là rules-only**
  (không logistic) để giữ trial budget thấp.

## 4. Setup scope

- DR1 executable = **Pattern Break** (đúng sách) + **Combi** (strong bar + inside
  bar) như một biến thể ưu tiên. **PR và TFF không executable** trong DR1; PBP
  và TFF để revision/generation sau (prereg riêng).
- Không dùng pressure/buildup 7-điều-kiện làm AND; không dùng PR extension cũ.

## 5. Bracket & management

- Fixed bracket giữ nguyên: S=8, TP=16 (b=2.0), không BE/trailing/partial.
- Room-to-obstacle gate thay cho resistance exit thủ công.
- Safety flats giữ nguyên (news ±20', Friday 20:00 server, daily 22:00 server).

## 6. Trial budget & gates

- 1 logic cell mới (DR1) = baseline + tối đa 2 revision như GOAL.
- Calibration grid ≤ **16 tổ hợp**: `θ_slope ∈ {0.05,0.10}` × `band ∈ {0.35,0.5}`
  × `overlap ∈ {0.40,0.45}` × `expiry ∈ {12,20}`; chọn plateau.
- Giữ nguyên: matched-random lift gate (x1 ≥ +14.1pp với S=8; x2 ≥ +18.2pp),
  cadence 10–40/tuần (nếu <10 → flag `LOW_CADENCE`, Lead escalates), PF x1>1.30,
  x1.5≥1.25, x2≥1.00, gross PF≥1.10, b≥1.70, N≥500, DD≤6%, HQ>97%.
- Trước economic run: census outcome-blind trên DESIGN (executable/tuần) +
  detector-fidelity G2 với `GRADING_RUBRIC_V2` (2 grader + adjudication Lead).

## 7. Việc phải làm trước khi code

1. Lead duyệt spec này (và xác nhận phạm vi PB+Combi).
2. Viết prereg DR1 (`research/VPA-DR1_FROZEN_PREREG.md`) + registry row.
3. Cập nhật `vpa_core.py` theo mục 1–4; chạy lại tests + prefix invariance.
4. Census DESIGN; nếu executable ≥10/tuần → snapshots + grading V2 (2 grader)
   → nếu A/B ≥ gate → engineering gate → economic baseline.
