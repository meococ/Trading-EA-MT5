# DE_DUP_CHECK — HYP-VPA-EURUSD-M5-001 (outcome-blind)

Status: `DEFINITION_LEVEL_PASS / QUANTITATIVE_OVERLAP_DEFERRED_TO_P2`
Ngày: 2026-09-20 · Người làm: OpenCode (em) · Chưa đọc bất kỳ outcome nào.
Nguyên tắc: cổng material-difference của T2 P0 (`P0 charter:46-51`): nếu >50%
trigger identity trùng family đã chết và phần còn lại không quy được về
provenance khác biệt → **KILL trước build**.

---

## 1. Kiểm kê evidence hiện có (audit thật, không suy diễn)

| Family | Package hiện tại | Trigger-timestamp evidence | Kết luận khả dụng |
|---|---|---|---|
| SCC `HYP-SCC-EURUSD-M5-001` | Chỉ còn archive: `00. Old File/EA_Archive/EA_SweepCascadeContinuation/` (source snapshots `.mq5` cho các HYP-SCC-…-002/003/004) | **Không có** CSV/ledger trigger trong repo sống; chỉ readout narrative | **Không thể** overlap số → so định nghĩa + source snapshot |
| ECRS `HYP-ECRS-EURUSD-M5-001/002` | Package đã bị xoá (không thấy cả trong archive) | Chỉ readout `04. Memory/research/20260722_ECRS_DEDUP_READOUT.md`, `20260723_ECRS_002_DEDUP_READOUT.md` | **Không thể** overlap số → so định nghĩa |
| VRAS `HYP-VRAS-EURUSD-M5-*` | Không còn package sống | Readout trong `do_not_repeat_failures.md:325-345` | So định nghĩa |
| LSWEEP `HYP-LSWEEP-EUR-M5-001` | `03. EA Developer/EA_LiquiditySweep/` sống; chạy killed `20260912_*` có **LifecycleTrades CSV + source snapshot** | Có lifecycle (executed, đã outcome) — **không phải full signal set**; journal delta có thể chứa signal nhưng chưa xác minh | Overlap số **hoãn sang P2** (khi detector VPA tồn tại để so); hiện so code-level từ `LSW_Signal.mqh` snapshot |
| SDRIVE `HYP-SDRIVE-GBP/JPY-M5-001` | `03. EA Developer/EA_SessionDrive/` sống; lifecycle CSV + `SD_Signal.mqh` snapshot | nt | nt |
| MZMS MACD/RSI/ADX | Không dùng indicator này | — | Loại bằng code review |
| ICT/FVG/OB/MSS/PO3/KLR | Không dùng token nào | — | Loại bằng code review |

## 2. So sánh định nghĩa/code-level (nguồn thật đã đọc)

| Family | Trigger gốc | VPA baseline | Khác biệt material | Kết luận |
|---|---|---|---|---|
| SCC | `HYP-SCC-EURUSD-M5-001`: confirmed N=2 pivot → **first close-break** → HOLD ngoài barrier → **first-passage RETEST** continuation; mỗi ngày 1 arm; stop complex-extreme +0.25×ATR14 | Locked touch-cluster barrier → pressure → buildup → **stop-entry ngay khi phá signal bar**; **không** retest, **không** HOLD gate, bracket cố định 2R | Không cùng decision surface: VPA vào lệnh trên break, SCC vào trên retest sau khi break giữ; VPA yêu cầu buildup/pressure, SCC không | Không trùng object |
| ECRS | ER10 shift 0.28→0.38 ∧ ATR14 ≤ 0.70×SMA20 ∧ 12-bar range break ∧ 1.7× tick-volume surge ∧ EMA20 bias ∧ London–NY | Cấm ER/ATR-ratio/tick-vol/session gates; barrier = touch cluster từ pivot (không phải rolling 12-bar); Contraction chỉ 1 trong 7 điều kiện buildup | Forbidden-reconstruction list của T2 P0:46-48 được giữ nguyên; không dùng bất kỳ gate nào của ECRS | Không trùng |
| VRAS | Session-VWAP ± gap seven-gap + continuation | Không VWAP, không gap | — | Không trùng |
| LSWEEP | `LSW_Signal.mqh:3-5`: "bounded excursion beyond a reference level that closes back" (sweep–reclaim), pen ∈ [min,max]×ATR, one per level | Không sweep; không reclaim; không yêu cầu excursion ngoài level | Khác cơ chế vào lệnh hoàn toàn (reversal sau sweep vs continuation break có buildup) | Không trùng |
| SDRIVE | `SD_Signal.mqh:3-9`: session opening-drive FSM, OR range ∈ [or_min, or_max]×ATR, drive continuation sau OR break | Không opening-range, không session-open anchor; setup có thể ở bất kỳ bar nào trong session | Khác anchor và khác trigger | Không trùng |
| MZMS | MACD histogram extrema + RSI/ADX filter | Không indicator oscillator | — | Không trùng |
| ICT/FVG | displacement+MSS+FVG+retest, sweep-confirmation | Không | — | Không trùng |

## 3. Kiểm tra số lượng trigger (deferred, có giao thức chốt trước)

Khi detector P2 (`research/lab/`) tồn tại, trước mọi economic run **phải chạy**:

1. Sinh trigger timestamp VPA (bar quyết định, side) trên **DESIGN EURUSD
   2016–2021**, outcome-blind.
2. Tái tạo trigger của các family còn đủ định nghĩa:
   - LSWEEP: re-implement đúng `LSW_Signal.mqh` semantics trên bar M5 Bid (không
     cần EA);
   - SCC: re-implement đúng mô tả `20260725_SCC_DEDUP_READOUT.md` (N=2 pivot,
     first close-break, 12-bar contest);
   - ECRS: dùng đúng forbidden conjunction của `ECRS DEDUP readout`.
3. Tính Jaccard trên **tập bar-quyết-định** (cùng bar index + cùng side) và
   overlap rate = `|VPA ∩ dead| / |VPA|`.
4. **Ngưỡng chốt:** overlap > **50%** → KILL trước build; 20–50% → phải chứng
   minh phần dư đến từ locked-barrier provenance + pressure/buildup (log
   attribution), nếu không → KILL; < 20% → PASS.
5. Kết quả ghi `PLAN/DE_DUP_QUANT_<date>.md` kèm hash input.

Hiện trạng: **CHƯA CHẠY** — detector chưa tồn tại (P2 đang triển khai). Đây là
điều kiện hoàn tất G0 trước economic run, đã ghi vào prereg §10.

## 4. Kết luận v1

- Không có family nào trùng **định nghĩa** với VPA pattern-break; bảng Phụ lục 1
  của `RESEARCH_PLAN.md` vẫn đúng.
- Không thể làm overlap số hôm nay vì (a) detector VPA chưa có, (b) SCC/ECRS
  không còn trigger evidence sống. Đã ghi rõ là `DEFINITION_LEVEL_PASS`,
  `QUANTITATIVE: NOT RUN`.
- Không có cơ sở để tuyên bố đã de-dup xong; chỉ tuyên bố đã chuyển cổng này
  thành điều kiện bắt buộc trước economic run với ngưỡng 50%/20% ở trên.

## 5. Addendum P2 (2026-09-20) — quantitative check mooted by the cadence stop

Detector VPA giờ đã tồn tại (`research/lab/vpa_core.py`) nhưng census
outcome-blind chỉ cho **62 executable candidates / 6 năm EURUSD** (0.197/tuần):
pattern-break 11, pullback reversal 51. Theo stop rule của Lead, lane dừng
trước snapshots/grading/economic run. Ở quy mô 62 candidate, bài toán ">50%
trigger trùng family đã chết" không còn là rủi ro thực tế (kể cả trùng hết cũng
không tạo ra economic cell nào để chạy). Quantitative overlap vì vậy **không
chạy** trong trạng thái này; nếu Lead mở một detector revision mới, §3 là giao
thức bắt buộc trước economic run.
