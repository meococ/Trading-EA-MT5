# GAP_VS_SPEC — sách UPA vs FEATURE_SPEC / vpa_core / G2 adjudication

Mục đích: liệt kê cái **sai, thiếu, quá chặt** của detector hiện tại so với sách,
kèm fix cụ thể. Nguồn: `UPA_SYNTHESIS.md`, `RULEBOOK.md`,
`PLAN/FEATURE_SPEC.md`, `research/lab/vpa_core.py`, `PLAN/grading/G2_LEAD_ADJUDICATION.md`.

## 1. Sai (phải sửa)

| # | Hiện tại | Sách | Fix |
|---|---|---|---|
| 1 | **Entry**: quyết định tại close của BREAK bar rồi đặt stop 1 pip ngoài break bar (`_eval_pattern_break`: `entry_level = h[t] ± buf`) → đuổi bar dài; entry có thể cách barrier 10–18 pip (Lead: cases 004/034/198) | Entry là stop order 1 pip qua **signal bar** (bar trước break), cú phá vỡ tự kích hoạt (tr. 95) | Đặt lệnh tại close signal bar `t_s`; `entry = high[t_s]+1pip`; break bar chỉ là bar kích hoạt; hủy nếu chưa khớp trong V bar hoặc phá invalidation |
| 2 | Bias gate chỉ `bias != -d` (rất yếu) | Thuận áp lực chủ đạo là điều kiện #1; EMA25 còn hướng → cấm ngược (tr. 101, 227) | `trend_d ≥ 0.10×ATR` (EMA slope 6 bar) **và** tỷ lệ bar đóng phía thuận ≥60%/10 bar **và** cấu trúc HH/HL (long) |
| 3 | Room đo bằng **active barriers** cùng phía (thường = inf vì barrier đã consume) | Room là khoảng tới **đỉnh/đáy trước hoặc cụm giằng co** kế tiếp, ≥2R; cộng nam châm ngược tới stop (tr. 155, 167) | Đo room tới pivot xác nhận gần nhất phía trước + biên congestion + mức tròn; room gate 2.0R; nam châm ngược trong [entry−R, entry] → skip |
| 4 | Không có anti-chase | Không đuổi; stop phải nằm trong hộp; entry xa EMA25/beyond biên nhiều là skip (tr. 103, 118, 234) | `entry_level − B ≤ 0.35×ATR`; `range(signal) ≤ 1.5×ATR`; `|entry−EMA| ≤ 1.5×ATR` |
| 5 | Chop veto quá rộng (overlap ≥0.65 & prog ≤1/3 & doji) bắt cả buildup tốt (Lead: 4/16 A/B bị skip_chop) | Chop/barb wire là chuỗi bar chồng lấn rối + bar dài bất thường; buildup nén chặt thì **không** phải chop (tr. 126, 234) | Chop chỉ khi overlap≥0.65 **và** prog≤1/3 **và** (doji **hoặc** ≥1 bar >1.5×ATR); miễn trừ nếu đang trong buildup sát barrier |

## 2. Thiếu (cần thêm)

| # | Thiếu gì | Sách | Fix cho DR1 |
|---|---|---|---|
| 6 | **EMA-pressing squeeze** (EMA25 ép giá vào biên) — feature Lead dùng nhiều | Squeeze = bar nhỏ kẹt giữa trendline/biên và EMA25 (tr. 57, 90) | Feature: khoảng cách `|EMA−B|/ATR ≤ 0.6` và ≥2 bar có range chứa EMA trong cửa sổ buildup |
| 7 | **Trendline mô hình** (không chỉ ngang) | Pattern có thể là trendline/flag, không chỉ hộp (tr. 90, 109) | Optional: fit trendline từ 2 pivot xác nhận, slope ≤0 cho bull (≥0 cho bear); dùng làm context, không trigger |
| 8 | **PBP, TFF** chưa có detector; PBC mới một phần | 5 setup cốt lõi (tr. 233) | DR1: giữ PB làm baseline; PBP/TFF vào revision có prereg riêng; không trộn |
| 9 | **Resistance/news/reversal exit** không có (baseline cấm) | 3 kỹ thuật thoát (tr. 162–175); "vật cản chỉ để lại <14 pip lợi nhuận từ entry → bỏ" (tr. 167) | Giữ baseline fixed bracket; thêm **room-to-obstacle gate** (đã có ở #3) để không cần thoát giữa; các exit thủ công = revision |
| 10 | **Round-number magnet** chỉ telemetry | 00/50 hút giá; 40–60 đáng chú ý (tr. 43–45, 417) | Adverse-magnet gate: nếu mức tròn nằm giữa entry và target trong 2R → hạ grade/skip |
| 11 | **Low-vol adaptation** | target 8–10, stop 5–8, lưới 20 (tr. 413–419) | Config profile riêng khi ATR session < ngưỡng; không đổi nguyên tắc |
| 12 | **Session windows** hiện tại London 05:00–11:00 / NY 11:30–17:30 UTC | EU mở 08:00, UK 09:00, US 15:30 CET (= 07:00/08:00/14:30 UTC); tránh trưa 12:00–14:00 CET (tr. 48, 414) | DR1: EU 07:00–11:00 UTC + US 13:30–16:30 UTC; cửa sổ trưa 11:00–13:30 UTC = telemetry/veto mềm |

## 3. Quá chặt (AND-stack giết A/B)

| # | Gate | Vấn đề (Lead G2) | Fix |
|---|---|---|---|
| 13 | **Pressure** (4 thành phần, cửa sổ 6 bar, dur≥2) | 9/16 A/B bị `skip_no_pressure`; pressure không phải điều kiện sách nêu cho PB (sách nói buildup, không nói ER/CLV) | Hạ pressure thành **feature/score**, không phải gate; giữ tối thiểu "không có bar ngược mạnh trong buildup" |
| 14 | **Buildup 7 điều kiện AND** (inside/contraction/overlap/progression/counter/touches) | 531/542 bị chặn; `buildup_fail_inside`=3180 — band `[B−0.35A, B+0.05A]` quá hẹp cho 3–8 bar | DR1: AND rút còn 4: (a) ≥2 close trong `[B−0.5A, B+0.1A]`; (b) ≥1 chạm `|high−B|≤0.1A`; (c) overlap ≥0.45; (d) contraction ≤0.85. Các điều kiện còn lại → score |
| 15 | **Buildup n tối đa 8, chọn n lớn nhất** | Sách gợi ý ≥4 bar nhưng "không cứng nhắc" (tr. 103, 223) | Cho phép n ∈ [3,10]; ưu tiên n lớn nhất **đạt tối thiểu**, không đòi mọi điều kiện |
| 16 | **Barrier T_min=2, scan 17, expiry 12** | Sách: hộp qua "nhiều lần chạm", cập nhật khi có đỉnh/đáy giả (tr. 51, 76); không giới hạn 12 bar cứng | Expiry 12 → 20 bar; cho phép re-lock tại chỗ sau tombstone nếu ≥2 chạm mới |
| 17 | **PR detector (bản mở rộng của worker)** | Lead: precision thấp (19/33 A+B) | DR1 không dùng PR làm executable; chỉ giữ như diagnostic; nếu làm lại phải đúng sách: sóng hồi **đầu tiên**, chạm EMA25, 40–60%, chờ phá vỡ thứ hai |

## 4. Đối chiếu nhanh với FEATURE_SPEC

- `FEATURE_SPEC §2.15` (signal bar + stop entry) **đúng sách** nhưng `vpa_core`
  implement sai (dùng break bar) → sửa code theo spec, không đổi spec.
- `FEATURE_SPEC §2.5` (buildup 7 điều kiện) là bản adapt từ T2, **quá chặt** so
  với sách; DR1 hạ như mục #14 và ghi rõ là adaptation.
- `FEATURE_SPEC §2.1` (bias) quá yếu so với nguyên tắc EMA25 có hướng (tr. 227);
  nâng theo mục #2.
- `FEATURE_SPEC §2.13` (round number) giữ telemetry → nâng thành adverse-magnet
  gate (mục #10) vì sách dùng nam châm như điều kiện chọn lệnh.
- `FEATURE_SPEC §2.17` (manual exits telemetry-only) giữ nguyên cho baseline;
  ghi chú rằng sách coi đây là kỹ năng chính (tr. 162–175) → ứng viên revision.

## 5. Kết luận

Detector hiện tại lệch sách ở **entry semantics** (nặng nhất), **trend alignment**
và **room**; đồng thời quá chặt ở **pressure/buildup** và quá rộng ở **chop**.
Các fix 1–17 là đầu vào trực tiếp cho `research/VPA-DR1_SPEC_DRAFT.md`.
