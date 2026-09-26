# GRADING_PREREG — VPA-P2b (frozen BEFORE any grade is generated)

Status: `FROZEN_PRE_GRADING / NO OUTCOME / NO MT5`
Ngày: 2026-09-20 · Người viết: OpenCode (em) · Lead: Claude · Owner: Mèo Cọc
Authority: Lead decision VPA-P2b (2026-09-20), `RESEARCH_PLAN.md §E.3` (rubric),
`PLAN/CENSUS_SUMMARY.md` (frame counts). Tài liệu này **không được sửa sau khi
grade đầu tiên được tạo**.

## 1. Câu hỏi

Detector T2-derived chỉ giữ 62/9,778 in-session raw breaks. Đó là thông tin về
**mechanization**, không phải về việc setup Volman-grade có tồn tại đủ cadence
hay không. Câu hỏi bị falsify: **tỷ lệ A/B-grade (theo mắt người chấm thuần
chart) trong tập in-session raw breaks là bao nhiêu, và nó có đủ cho sàn
10 lệnh/tuần không?**

## 2. Khung lấy mẫu (frozen)

| Nhóm | Frame | N | Ghi chú |
|---|---|---|---|
| `srs` | 9,778 in-session raw breaks = (19,778 raw − 10,000 skip_session) EURUSD M5 DESIGN 2016–2021 | **160** | SRS không thay thế; seed `20260920` |
| `exec` | 62 executable candidates (11 pattern-break + 51 pullback reversal) | **40** | SRS không thay thế; dùng cho detector precision |

- Đơn vị đếm: 314 tuần theo `PLAN/CENSUS_SUMMARY.md` → in-session break rate
  = 9,778 / 314 = **31.14/tuần** (Lead ghi ≈31.1; dùng 31.14 trong mọi phép tính
  dưới đây).
- Mẫu không phụ thuộc outcome; không PnL; không MT5; chỉ detector outcome-blind.

## 3. Snapshot (blinding)

- 1 PNG/case: **120 bar M5 kết thúc đúng tại bar quyết định (break bar), 0 bar
  sau đó**. Vẽ: EMA25, barrier bị phá + touch marks, các barrier active khác
  (mảnh), bar break highlight, stop-entry line cách 1 pip.
- **Không** in funnel stage, skip reason, detector verdict, setup type, ngày,
  hay bất kỳ thứ gì outcome-related lên ảnh hay tên file. Tên file trung tính
  `case_001.png … case_200.png`, thứ tự đã shuffle ngẫu nhiên (seed 20260920).
- `PLAN/grading/INDEX_BLIND.csv`: `case_id, symbol, decision_utc, side, entry, stop`.
- `PLAN/grading/KEY_HIDDEN.csv`: `case_id → sample_group, funnel stage, features`.
  **Không mở trong lúc chấm.** Grade chỉ được tạo từ PNG + rubric (không đọc
  INDEX_BLIND cho pass-1 của worker).

## 4. Rubric (nguyên văn từ RESEARCH_PLAN §E.3)

| Grade | Nghĩa | Điều kiện |
|---|---|---|
| **A** | Volman-grade, sẽ vào lệnh | Barrier nhìn thấy được (≥2 touch rõ); buildup sát barrier; signal bar đúng chiều; room ≥2R không bị chặn; hướng khớp bias |
| **B** | Biên, có thể vào | Thiếu 1 tiêu chí phụ (buildup mỏng, room 1.5–2R, EMA hơi xa) nhưng không phản thesis |
| **C** | Không nên vào | ≥2 tiêu chí sai, hoặc 1 lỗi nặng: không có barrier thực; break ngược buildup; adverse magnet chặn giữa; false break rõ; trùng family đã chết |

Pass-1: grader LLM (sub-agent độc lập), chỉ thấy ảnh + rubric này.
Pass-2: Lead chấm độc lập một subset blind. **Lead-adjudicated grade là final.**

## 5. Decision rule (pre-registered, không được đổi sau khi thấy grade)

Gọi `p = (số A + số B) / 160` trên nhóm `srs`, `n=160`.

1. **KILL** nếu `Wilson95_upper(p, 160) × 31.14 < 10.0` lệnh/tuần
   → M5 EURUSD Volman bị KILL theo cadence của GOAL; Lead escalate câu hỏi
   cadence lên Owner.
2. **DR1 JUSTIFIED** nếu `p × 31.14 ≥ 10.0` lệnh/tuần
   → cho phép detector revision **VPA-DR1**, và DR1 **chỉ được** nhắm vào các
   feature phân tách A/B vs C, xác định bằng cross-tab `grade × funnel exit
   stage`. Cấm nới filter để kiếm cadence.
3. **INCONCLUSIVE** nếu ở giữa → báo cáo kèm cỡ mẫu cần để phân giải
   (`N*` nhỏ nhất sao cho Wilson upper của tỷ lệ A/B quan sát được < 0.3211),
   và không mở DR1/KILL.

Ghi chú số học: sàn 10/tuần ⇔ `p* = 10/31.14 = 0.3211`.

## 6. Phân tích (sau khi grade đóng băng)

- A/B/C rate + Wilson 95% CI cho từng nhóm (`srs`, `exec`); riêng PB-only trong
  `exec` như thông tin phụ (n nhỏ).
- Cadence suy ra: `p̂ × 31.14` với CI (biến đổi từ Wilson CI của `p`).
- Cross-tab `grade × funnel stage` (dùng KEY_HIDDEN) — cổng nào giết nhiều A/B
  nhất.
- Verdict sơ bộ theo §5, đánh dấu **PENDING LEAD ADJUDICATION**.
- Ghi vào `PLAN/grading/G2_FREQUENCY_ESTIMATE.md`.

## 7. Bằng chứng bất biến

- File này phải tồn tại **trước** file grade đầu tiên; SHA256 ghi trong báo cáo.
- `GRADES_LLM_PASS1.csv` SHA256 ghi trong báo cáo để Lead chứng minh grade đã
  cố định trước khi Lead chấm pass-2.
- Không case nào có outcome/PnL được tính ở bất kỳ bước nào.
