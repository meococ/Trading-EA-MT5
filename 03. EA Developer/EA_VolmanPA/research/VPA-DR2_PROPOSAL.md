# VPA-DR2_PROPOSAL — vì sao DR1 mù, và DR2 nên là gì

Task: T-VPA-DR1-DIAG. Status: PARTIAL (DR1 không đạt cadence; bằng chứng đầy đủ,
quyết định đi tiếp hay dừng thuộc Lead/Owner — xem §5).
Bằng chứng gốc: `PLAN/diag_dr1/RECALL_TRACE.csv` + `RECALL_SUMMARY.md` (DR1),
`RECALL_TRACE_DR2C.csv` + `DISCRIMINATION_DR2C.md` (DR2c),
`DR2_VARIANTS.csv|md`, `snapshots/` (20 PNG + INDEX.csv).
Set 60 case đã BURNED (E3): mọi con số recall ở đây là chẩn đoán, không phải
fidelity. Không có trường outcome nào (E4).

## 0. TL;DR

1. DR1 không mù vì "thị trường không có setup" — nó mù vì **định nghĩa signal
   bar sai** và **session window bị thu hẹp** so với universe mà Lead đã chấm.
   Sửa 2 lỗi này: A/B được evaluate từ **4/16 → 15/16** (C: 19/44 → 34/44).
2. Sau khi sửa, **toàn bộ tường còn lại là các gate**, và chúng không có sức
   phân biệt: chỉ `trend` tách được A/B khỏi C (fail 13% A/B vs 71% C). `buildup`
   (73% A/B fail), `chop` (33% vs 12%), `anti_chase` (27% vs 9%) fail A/B **nhiều
   hơn** C → đang bị động phá recall.
3. AND-stack hiện tại, dù nới hết mức có nguyên tắc (DR2c/d), chỉ còn **4 exec /
   6 năm = 0.013/tuần** — cách xa bar 3/tuần của D2.
4. **Bound quan trọng**: chỉ giữ `trend` + `direction`, tắt phần còn lại →
   **5,528 exec = 17.7/tuần**, trong đó 10/16 A/B và 8/44 C lọt (tỷ lệ A/B trong
   số case lọt của set burned = 10/18 ≈ 55%, so với base rate 27% của set) →
   cadence đủ, precision chưa đủ; đây là hướng DR3 (score-based) chứ không phải
   một variant AND-stack.
5. Đề xuất: **DR2c là base bắt buộc** (sửa recall, giữ nguyên triết lý AND);
   nhưng **không variant AND-stack nào đạt 3/tuần** → nếu Lead không muốn đổi
   sang score-based/DR3 thì áp dụng stop rule D2 và đóng lane VPA.

## 1. Recall trace — 60 case Lead đã chấm

| category | tất cả | Lead A/B (16) | Lead C (44) |
|---|---|---|---|
| (i) không có barrier khớp | 11 | 1 | 10 |
| (ii) không có signal eval | 26 | **11** | 15 |
| (iii) evaluated nhưng fail | 23 | 4 | 19 |
| (iv) executable | 0 | 0 | 0 |

DR1: 11/16 A/B **không bao giờ được evaluate**. Trong 11 case đó, 9 case bị
"barrier consumed as missed break **tại đúng case bar**" — bar phá vỡ đóng vượt
B+0.25A, còn bar trước đó đóng chưa tới B−0.05A → cửa sổ signal `[B−0.05A,
B+0.25A]` không khớp **cả hai bar**.

## 2. Ba khiếm khuyết gốc (bằng chứng + book cite)

### D1. Signal bar: sai bar, không phải sai ngưỡng (lỗi nặng nhất)

Book (tr. 88, 95): signal bar là **bar cuối trước trigger**, entry là stop order
**1 pip qua đỉnh/đáy signal bar**; breakout bar (bar phá biên) là bar **kích hoạt**
stop đó, không phải bar để đo "đóng tại biên". DR1 lại đòi **close của bar eval**
nằm trong `[B−0.05A, B+0.25A]` — một proxy khác hẳn.

Số đo (case_003, short, B=1.154745, A=4.10 pip — `snapshots/ab_case_003.png`):

| bar | close | (B−close)/pip | /A |
|---|---|---|---|
| t−3 | 1.15517 | −4.15 | −1.06 |
| t−2 | 1.15531 | −5.55 | −1.41 |
| t−1 | 1.15503 | −2.75 | −0.69 |
| **t (break)** | 1.15455 | **+1.95** | **+0.48** |

Bar t−1 **touch** barrier (low chạm 1.1547, có trong `touches`) nhưng close cách
2.75 pip (−0.69A) → DR1 loại; bar t đóng +1.95 pip (vượt 0.25A) → DR1 gọi là
"missed break" và **consume barrier**. Trong khi đó entry đúng của book = low(t−1)
− 1 pip ≈ 1.15465, chỉ 1 pip qua biên → hoàn toàn hợp lệ.

**Sửa (DR2c)**: signal bar = **bar cuối cùng đã touch barrier** trước bar phá vỡ
(danh sách `touches` của barrier); entry = extreme(signal) ± 1 pip; gate tính tại
signal bar, session tính tại bar phá vỡ (bar vào lệnh). Không nới ngưỡng nào —
chỉ đổi **bar được đo**. Kết quả: A/B (ii) 11 → 0.

### D2. Session window bị thu hẹp so với universe đã chấm

Lead chấm trên snapshot của detector v1 (`vpa_core.py`): london = 05:00–11:00
UTC, ny = 11:30–17:30 UTC. DR1 (prereg) thu còn eu 07:00–11:00, us 13:30–16:30.
Hệ quả: **9/16 case A/B nằm ngoài cửa sổ DR1 nhưng trong cửa sổ v1** (05:05,
05:25, 06:05, 06:15, 12:30, 12:40, 16:40, 17:05, 17:25 UTC) → bị loại bằng cấu
trúc, không phải bằng judgement.

Đây là **mismatch hệ đo**, không phải bằng chứng Lead sai: trace recall chỉ có
nghĩa khi so trên cùng universe. Sửa (DR2a): khôi phục cửa sổ v1. Lưu ý book
(tr. 227, 273) khuyên tránh trưa EU 12:00–14:00 và NY 18:00–20:00 **giờ CET** —
sau khi recall ổn, có thể cắt lại dead-zone như một quyết định riêng (khi đó
session chỉ còn fail 1/15 A/B và 1/34 C → gần như không ràng buộc).

### D3. Các gate còn lại không phân biệt được A/B vs C

`DISCRIMINATION_DR2C.md` (evaluated: A/B 15, C 34):

| gate | fail A/B | fail C | gap (C−AB) | đọc |
|---|---|---|---|---|
| trend | 2/15 (13%) | 24/34 (71%) | **+0.573** | gate duy nhất có signal |
| direction | 3/15 (20%) | 10/34 (29%) | +0.094 | yếu |
| room | 4/15 (27%) | 12/34 (35%) | +0.086 | yếu |
| adverse | 4/15 (27%) | 11/34 (32%) | +0.057 | yếu |
| session | 1/15 (7%) | 1/34 (3%) | −0.037 | nhiễu |
| buildup | 11/15 (73%) | 22/34 (65%) | −0.086 | **hại recall** |
| anti_chase | 4/15 (27%) | 3/34 (9%) | −0.178 | **hại recall** |
| chop | 5/15 (33%) | 4/34 (12%) | −0.216 | **hại recall** |

Book để buildup "đủ dày/hài hòa" ở mức **discretionary** (tr. 103, 223; RULEBOOK
§8.1) — AND-4 điều kiện là phát minh của DR1, không phải luật book. Tương tự
`chop` bản DR1 là bản "narrowed" tự chế. `anti_chase` (0.35A + buffer) không có
trong book dưới dạng ngưỡng; book chỉ nói không đuổi giá xa (tr. 95).

## 3. Census các variant (DESIGN, 6 năm; base rate A/B trong set = 27%)

| variant | thay đổi | exec | /tuần | A/B eval | A/B exec | C exec |
|---|---|---|---|---|---|---|
| DR1 | — | 1 | 0.0032 | 4/16 | 0 | 0 |
| V1 | signal_atr 0.05→0.50 | 1 | 0.0032 | 11/16 | 0 | 0 |
| V2 | +room_sig/PDH | 1 | 0.0032 | 11/16 | 0 | 0 |
| V3 | +buildup 2-of-4 | 2 | 0.0064 | 11/16 | 0 | 0 |
| DR2a | +v1 sessions | 3 | 0.0096 | 11/16 | 0 | 0 |
| DR2b | +room_sig/PDH | 3 | 0.0096 | 11/16 | 0 | 0 |
| **DR2c** | **+signal_prev_bar** | 4 | 0.0128 | **15/16** | 0 | 0 |
| DR2d | DR2c + buildup 2-of-4 | 4 | 0.0128 | 15/16 | 0 | 0 |
| DR2e (bound) | chỉ trend+direction | **5,528** | **17.7** | 15/16 | **10** | **8** |

Funnel DR2c (first-fail, `DR2_VARIANTS.md`): session 43,365 → trend 17,918 →
room 4,024 → buildup 3,663 → direction 4,415 → chop 1,650 → anti 102 → adverse 8;
4 exec. **Không gate nào một mình là nút thắt — nút thắt là phép AND của 8 gate
mỗi cái pass 20–90%.**

DR2e cho thấy trần của detection layer + trend: 17.7/tuần. Precision trên set
(burned, stratified) 10/18 ≈ 55% A/B — hơn base rate 27% nhưng chưa đủ để gọi là edge;
muốn precision cao phải **thay AND-stack bằng score** (DR3), và validate trên
case mới (E3 cấm dùng lại 60 case này để chọn/thẩm định).

## 4. Đề xuất DR2 (đúng nghĩa "revision")

| # | thay đổi | vì sao | book cite |
|---|---|---|---|
| 1 | signal bar = bar cuối touch barrier; entry = extreme ±1 pip; gate tại signal bar, session tại trigger bar | đúng định nghĩa book; sửa D1 | tr. 88, 95 |
| 2 | session = v1 universe (05:00–11:00 / 11:30–17:30 UTC) cho **đo lường**; dead-zone (trưa EU, tối NY) cắt riêng sau | sửa mismatch hệ đo D2 | tr. 227, 273 |
| 3 | room: chỉ tính obstacle "significant" (pivot ±5 bar, barrier ≥2 touch, PDH/PDL, lưới 00/50) | loại pivot nhiễu; giữ luật <14 pip profit → bỏ | tr. 167, 43 |
| 4 | buildup: 2-of-4 thay vì AND-4 (nếu giữ dạng ngưỡng) | book để discretionary; AND-4 là tự chế | tr. 103, 223 |
| 5 | **bỏ hard-AND cho chop/anti_chase**, chuyển thành score (DR3) | chúng fail A/B nhiều hơn C (D3) | tr. 95 (không đuổi giá) |

DR2c = (1)+(2)+(3); DR2d = +（4). Cả hai vẫn 0.013/tuần → **không đạt D2 bar**.
Muốn có cadence phải làm (5) = DR3 score-based, thiết kế mới + prereg mới +
case mới; DR2e là bound tham chiếu (17.7/tuần, 10/18 ≈ 55% A/B trên set burned).

## 5. Quyết định cần Lead/Owner chọn

- **(A) Đóng lane VPA theo stop rule D2** (không variant AND-stack nào đạt
  3/tuần; VPA tiếp tục ngốn budget mà trần precision của bound chỉ 10/18 ≈ 55% trên set
  burned). DR2c vẫn nên merge như bản sửa recall để đóng sổ đúng.
- **(B) Mở DR3 score-based** (trend làm trục chính, room/buildup/chop thành
  feature có trọng số; prereg mới; case mới ngoài 60 case burned; target cadence
  ~5–15/tuần, đo precision trên case mới). Cần Owner duyệt budget.

Em nghiêng về **(B) chỉ khi Owner muốn tiếp tục lane này**; nếu không, (A) là
kết luận trung thực của toàn bộ chuỗi VPA-P0→DR1-DIAG.

## 6. Hạn chế / điều chưa chắc

- n(A/B)=16, n(C)=44 — mọi tỷ lệ phần trăm trên đây có CI rộng (vd 10/16 ≈ 63%
  ± 24%). Các kết luận định tính (gate nào fail A/B nhiều hơn C) vững hơn các con
  số tuyệt đối.
- Set burned (E3): không dùng để chọn variant "đẹp" — chỉ để chẩn đoán.
- DR2e là **bound kỹ thuật** (tắt gate bằng knob), không phải cấu hình đề xuất:
  nó chứng minh cadence nằm ở đâu, không chứng minh precision.
- Không có outcome/PnL nào được tính (E4) — "precision" ở đây là tỷ lệ Lead A/B.

## 7. Artifact

- `research/lab/vpa_trace.py` — gate-level trace dùng chung code path với detector
  (`test_trace_equals_detector` trong `test_vpa_dr1.py`, 45/45 PASS).
- `research/lab/vpa_recall_dr1.py` → `PLAN/diag_dr1/RECALL_TRACE.csv|RECALL_SUMMARY.md`
  (DR1 default config — nguồn của bảng §1).
- `research/lab/vpa_dr2_discrimination.py` → `PLAN/diag_dr1/RECALL_TRACE_DR2C.csv`
  (per-case, DR2c config — nguồn của bảng §2/D3) + `DISCRIMINATION_DR2C.md`.
- `research/lab/vpa_dr2_variants.py` → `PLAN/diag_dr1/DR2_VARIANTS.csv|md`.
- `research/lab/vpa_diag_snapshots.py` → `PLAN/diag_dr1/snapshots/` (10 A/B +
  10 missed-break + INDEX.csv; **INDEX.csv và PNG dùng config DR2a** — cột
  `category`/`fail_set` trong INDEX **không** so trực tiếp được với
  `RECALL_TRACE.csv` (DR1); cột `barrier` là `dr1_barrier` đã lock, không phải
  `barrier_level` của KEY).
- Knob DR2 trong `vpa_dr1.py`: `signal_prev_bar`, `room_significant_only`,
  `room_include_pdh`, `buildup_min_conditions`, `pivot_sig_lag` (default = DR1
  nguyên trạng; 45/45 test PASS, records/exec/counters không đổi).
