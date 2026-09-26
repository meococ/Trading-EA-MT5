# FEATURE_SPEC — VPA-P0: Concept → Quantified Feature

Status: `DRAFT_FOR_LEAD_REVIEW / PLANNING_ONLY`
Package: `03. EA Developer/EA_VolmanPA/`
Nguồn chính: official excerpts do tác giả tự host (lawful, đã đọc):
`upabook.wordpress.com/wp-content/uploads/2014/09/excerpts-upa.pdf` (UPA, M5)
và `infofpas.wordpress.com/wp-content/uploads/2011/10/excerpts-fpas-hr-27-11.pdf`
(FPAS, 70-tick — reference-only). Không dùng bản pirated. Mọi chỗ paraphrase,
không trích nguyên văn.

Quy ước: mọi "decision time" = **close của bar M5 đã hoàn tất**; mọi feature chỉ
dùng bar `≤ t`; không future pivot, không repaint, không intrabar reconstruction.
Toàn bộ tính incremental **O(1) hoặc O(k)** mỗi bar (k = số barrier active ≤ 8).

---

## 1. Semantics nền (frozen)

| Hạng mục | Định nghĩa | Ghi chú |
|---|---|---|
| Bar | M5 Bid OHLC đã đóng, thứ tự UTC tăng nghiêm ngặt | Không dùng Mid |
| ATR14 | Wilder, seed = mean 14 TR đầu | `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:25-28` (tái sử dụng) |
| EMA25 | Seed = mean 25 close đầu; hệ số 2/26 | `:30-31`. Volman dùng 25ema trên M5 (FPAS dùng 20ema trên 70-tick — không trộn) |
| CLV | `(2c-h-l)/(h-l)`, range=0 → 0 | `:33-35` |
| Warm-up | 50 bar liên tục sau reset mới được phát setup | `:37-38` |
| Gap | Cặp M5 hợp lệ = đúng 300s; thiếu bar bất thường → expire state + warm-up lại | `:314-328` |
| Round-number grid | `g = 10^round(log10(10 × median_train_ATR_in_price))`, làm tròn tick | `:215-223`; context-only |
| Buffer đơn vị | So sánh giá dùng nửa tick hoặc ngưỡng ATR ghi rõ | `:34-35` |

`ASSUMPTION:` bar M5 Bid + non-repaint là quy ước của repo (T2 P2 §1) và hợp với
quan điểm của tác giả rằng break của bar M5 là sự kiện khách quan còn vẽ line là
diễn giải cá nhân (paraphrase excerpt p.8-9), nhưng không phải bản sao nguyên
giao dịch của tác giả trên ProRealTime.

---

## 2. Bảng concept → feature

### 2.1 Bias / trend / "dominant pressure"

| | |
|---|---|
| **Tên** | Bias (xu hướng chủ đạo) |
| **Causal definition** | Tại bar `t` (closed): `trend_d = d × (EMA_t − EMA_{t−6}) / ATR_t`; `side_d = d × (close_t − EMA_t) / ATR_t`; `bias_d = 1` khi `trend_d ≥ +0.10` **và** `side_d ≥ −0.20`, else 0 |
| **Formula** | xem trên; `d=+1` long, `−1` short |
| **Params** | `slope_lookback=6` (range 5–10); `slope_min=0.10` (0.05–0.20); `side_min=−0.20` (−0.5–0.0) |
| **Units** | ATR-normalized |
| **Failure cases** | Sideway market: EMA slope ≈ 0 → bias 0 → không trade (đúng ý "skip"); trend mạnh nhưng giá extended xa EMA → `side_d` lớn nhưng vẫn bias 1, cần kèm distance filter (xem 2.15) |
| **Visual verify** | Kẻ EMA25; tô nền xanh khi `bias_long=1`, đỏ khi `bias_short=1`; mắt thường phải thấy "dominant pressure" khớp (excerpt p.13, p.26) |

### 2.2 EMA25 role (magnet + possession + distance)

| | |
|---|---|
| **Tên** | EMA25 magnet / possession |
| **Causal definition** | `possess_d(t)` = 3 bar liên tiếp close cùng phía EMA25; `touch_d(t)` = low (long) hoặc high (short) trong `[−0.10, +0.10]×ATR` quanh EMA; `dist_atr_d(t) = d × (close_t − EMA_t)/ATR_t` |
| **Formula** | trên |
| **Params** | `possession_bars=3` (2–5); `touch_tol=0.10` ATR (0.05–0.20); `max_dist_atr=1.5` (1.0–3.0) — dùng như telemetry baseline, veto ở revision nếu diagnosis ủng hộ |
| **Units** | ATR |
| **Failure cases** | EMA25 chỉ là trung bình và tự nó không phải hỗ trợ/kháng cự (paraphrase excerpt p.12-13) → không bao giờ được trade chỉ vì touch EMA (đây cũng là non-selectable diagnostic D2 của T2, charter `:171`) |
| **Visual verify** | Highlight các bar có touch EMA trong pullback; kiểm tra 40–60% depth kèm theo |

### 2.3 Horizontal barrier (floor/ceiling), double top/bottom

| | |
|---|---|
| **Tên** | Barrier (locked level) |
| **Causal definition** | Từ bar `l` (closed) làm mốc: quét `i=l−2..l−17`; nhận touch khi `abs(high_i − high_l) ≤ eps` (2% tick loại trừ), mỗi touch cách nhau ≥ 2 bar. `B = median(touch prices)`. Lock khi `touches ≥ T_min` **và** `close_l ≤ B + 0.05×A` (upper) hoặc `close_l ≥ B − 0.05×A` (lower), `A=ATR_l`. Barrier active `l+1..l+E`, expire tại `l+E+1` |
| **Formula** | tái sử dụng `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:43-76`, với 2 adapt: `T_min=2` (Volman dùng double top/bottom, excerpt p.7-8) và `B = median` (robust hơn last-touch) |
| **Params** | `eps=0.10×A` (0.05–0.15); `T_min=2` (2–4); `scan=17` bar (12–24); `E=12` bar (6–20); `dedupe_prox=0.10×A` |
| **Units** | giá / pips; ATR-normalized tolerance |
| **Failure cases** | (a) trend mạnh không có 2 touch cùng mức → không bao giờ lock → skip (chấp nhận); (b) barrier quá cũ đã bị phá một lần → tombstone, không relock tại chỗ (`:60-65`); (c) double-top giả khi 2 đỉnh nằm hai regime khác nhau → cần `cluster_span ≤ 20 bar` |
| **Visual verify** | Indicator vẽ `OBJ_HLINE` đúng mức B + số touch; vẽ label `t=2`; so mắt với "dotted line" trong excerpt p.8-10 |

**Break confirmation (dùng chung, reuse `P2 spec:69-70`):** close-break tại bar
`t` khi `d×(close_{t−1} − B) ≤ 0` **và** `d×(close_t − B) ≥ 0.05×ATR_t`. Đây là
điều kiện "vượt đủ xa" tính bằng close, không tính bằng wick; mọi setup loại
"pattern break" phải qua điều kiện này trước khi thành candidate.

### 2.4 Pressure

| | |
|---|---|
| **Tên** | Pressure (directional displacement) |
| **Causal definition** | 6-bar window kết thúc `u`: `Disp_d = d(close_u−close_{u−5})/ATR_u`; `ER_d = d(close_u−close_{u−5}) / Σ|Δclose|`; `MeanCLV_d = d×mean(CLV)`; `EMASlope_d = d(EMA_u−EMA_{u−5})/ATR_u`. `PRESSURE_d` khi `Disp ≥ 0.60 ∧ ER ≥ 0.55 ∧ MeanCLV ≥ 0.20 ∧ EMASlope ≥ 0.10` |
| **Formula** | `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:84-95` (reuse nguyên) |
| **Params** | cả 4 ngưỡng như trên; `pressure_duration` = số bar liên tiếp true, cap 12 |
| **Units** | dimensionless / ATR |
| **Failure cases** | `ER` denominator = 0 → pressure = false; OHLC "pressure" **không phải order flow** (`:95`; `PRO_TRADER_REPLACEMENT_E02_T2_P1_SOURCE_MATRIX.md:39`) |
| **Visual verify** | Tô đậm các bar pressure; mắt phải thấy chuỗi nến cùng màu, close gần cực, không overlap lộn xộn |

### 2.5 Buildup (pre-breakout tension)

| | |
|---|---|
| **Tên** | Buildup / box tension |
| **Causal definition** | Với trigger candidate tại `t`, chọn `n` lớn nhất trong 8..3 mà: (a) barrier lock ≤ `t−n−1` và có pressure trước đó; (b) mọi close buildup nằm trong `[−0.05, +0.35]×A_B` quanh B; (c) ≥2 high (long)/low (short) trong `0.10×A_B` của B; (d) `Contraction = median(TR_{t−n..t−1}) / median(TR_{t−n−12..t−n−1}) ≤ 0.75`; (e) `OverlapMean ≥ 0.50`; (f) `Progression ≥ 2/3`; (g) `CounterRatio ≤ 0.80` |
| **Formula** | `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:99-129` (reuse) |
| **Params** | `n` 3–8; các ngưỡng như trên; có thể nới ở revision có prereg |
| **Units** | ATR / ratio |
| **Failure cases** | (a) Contraction là **điều kiện dễ nhầm với ECRS compression** — task này phải chạy de-dup Jaccard với ECRS trigger (xem RESEARCH_PLAN §I); (b) buildup dài nhưng range to → "thin setup" (excerpt p.24-25) — chất lượng log riêng |
| **Visual verify** | Vẽ box quanh cluster buildup + ghi `n`, `Contraction`, `Overlap`; đối chiếu excerpt p.9-11 (box 10–11–13) |

### 2.6 Squeeze (bar bị kẹp giữa barrier và EMA25)

| | |
|---|---|
| **Tên** | Squeeze |
| **Causal definition** | Tồn tại cửa sổ ≥3 bar đóng, mỗi bar có range chứa đường EMA25, và khoảng cách `d×(B − EMA)` ≤ `1.0×ATR`; tính `squeeze_len` = số bar liên tiếp thỏa |
| **Formula** | mới (Volman-specific; mô tả cảnh giá bị kẹp giữa pattern line và đường trung bình — paraphrase excerpt p.13-14) |
| **Params** | `squeeze_min_len=3` (2–6); `band=1.0×ATR` (0.5–1.5) |
| **Units** | bar / ATR |
| **Failure cases** | EMA25 flat mọi lúc trong range hẹp → squeeze giả; yêu cầu `bias` cùng hướng hoặc đang pullback |
| **Visual verify** | Tô vùng squeeze; mắt thấy nến đan nhau giữa 2 biên |

### 2.7 Tease / false break (trap)

| | |
|---|---|
| **Tên** | False break / tease |
| **Causal definition** | Bar `t` có `high_t > B` (hoặc `low_t < B`) nhưng `close_t` đóng ngược lại phía trước barrier (`d×(close_t − B) ≤ 0`); ghi `false_break_side`, `false_break_age` |
| **Formula** | mới, nhưng khớp excerpt p.11-15 (bar 12/13 false low; bar 11 false break in squeeze) |
| **Params** | ngưỡng xuyên tối thiểu = 0.05×ATR; `age` cap 6 bar |
| **Units** | ATR / bar |
| **Failure cases** | Wicks dài do spread spike → false-break giả; loại bar `suspect` (roll) |
| **Visual verify** | Đánh dấu mũi tên tại wick false break; so mắt |

### 2.8 Barb wire (chop)

| | |
|---|---|
| **Tên** | Barb wire / chop |
| **Causal definition** | Trên 3–4 bar gần nhất: `OverlapMean ≥ 0.65` ∧ `Progression ≤ 1/3` ∧ tồn tại ≥1 bar có `body/range ≤ 0.35` (doji-ish, tail dài) |
| **Formula** | mới |
| **Caveat quan trọng** | **"Barb wire" là thuật ngữ của Al Brooks, không phải của Volman** (`brookstradingcourse.com/price-action-trading-terms-glossary`: trading range 3+ bar overlap, có doji). Volman mô tả cùng hiện tượng là squeeze/buildup lộn xộn và nói nên bỏ qua các break mơ hồ (paraphrase excerpt p.13-14, p.28-29). Feature này giữ như **chop veto** tương đương tinh thần đó, ghi rõ nguồn Brooks |
| **Params** | `overlap_min=0.65`; `prog_max=0.33`; `body_ratio_max=0.35`; lookback 4 (3–6) |
| **Units** | ratio |
| **Failure cases** | Veto quá tay làm rụng cadence → đo outcome-blind trước, chỉ veto khi census cho thấy đủ mẫu |
| **Visual verify** | Tô xám chuỗi bar bị coi là chop; phải khớp "lộn xộn, overlap nhiều" |

### 2.9 First break / second break (FPAS — reference-only)

| | |
|---|---|
| **Tên** | First break / Second break |
| **Nguồn** | FPAS chương 8–9 (70-tick): first break = phá barrier đầu tiên sau buildup; second break = phá đỉnh/đáy của pullback nhỏ sau first break. Official excerpt FPAS + mô tả cộng đồng (trade2win thread 153716) |
| **Quyết định phạm vi** | **KHÔNG đưa vào baseline M5.** Đây là concept của khung 70-tick; hợp đồng dữ liệu khác (`PRO_TRADER_REPLACEMENT_E02_T2_P1_SOURCE_MATRIX.md:20,37`). Chỉ dùng làm vocabulary/reference khi review chart |
| **Visual verify** | n/a trong P0 |

### 2.10 Pullback reversal

| | |
|---|---|
| **Tên** | Pullback reversal (PR) |
| **Causal definition** | Leg pressure kết thúc `k` (window `k−7..k`, `PRESSURE_d(k)`, `LegAmp ≥ 1.20×ATR_k`); correction `k+1..t−1` với `Depth ∈ [0.40, 0.60]`; `CorrER ∈ [0, 0.55]`; bar `t−1` không phá hướng; **Contact** qua `STRUCTURE` (barrier locked trước `k−7`, active tại contact) hoặc `EMA25` (bar span EMA ± 0.10 ATR); release `close_t ≥ high_{t−1} + 0.05 ATR_t` (long) + `CLV_t ≥ 0.50` |
| **Formula** | `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:152-182` (reuse), giữ nguyên **PBP exclusion** `:180-182` |
| **Params** | depth band 0.40–0.60 (cố định theo Volman excerpt p.21-22 "40/60 percent"); `m ∈ 2..6`; bội số leg 1.20 |
| **Units** | ratio / ATR |
| **Failure cases** | Nếu correction contact barrier **đã bị phá trước đó** → đó là PBP/SCC (family đã KILL) → `SKIP_PBP_EXCLUDED`; PR phải là pullback của leg chưa phá barrier |
| **Visual verify** | Đo depth bằng thước đo trên chart; đánh dấu điểm contact; kiểm tra release bar |

### 2.11 Pattern break combo (combi)

| | |
|---|---|
| **Tên** | Combi (pressure bar + inside bar + trigger) |
| **Causal definition** | Kế thừa A1; `p=t−2` pressure bar (`d(close−open) ≥ 0.35 ATR_p`, `d×CLV_p ≥ 0.50`); `q=t−1` inside (`high_q ≤ high_p + 0.5 tick`, `low_q ≥ low_p − 0.5 tick`, `(range_q/range_p) ≤ 0.75`); cả hai close trước barrier; `t` phá barrier |
| **Formula** | `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:133-148` (reuse) |
| **Params** | như trên |
| **Units** | ATR / ratio |
| **Failure cases** | Inside bar giả khi mother range = 0; same-bar entry (không được); hindsight chọn mother bar (cấm — thứ tự bar là bắt buộc) |
| **Visual verify** | Vẽ 2 hộp nhỏ quanh mother + inside; so với excerpt p.24-25 (combi ellipse) |

### 2.12 Range break (box break)

| | |
|---|---|
| **Tên** | Range/box break |
| **Causal definition** | Barrier ngang (2.3) + buildup (2.5) + close-break; **không** dùng rolling 12-bar high/low làm barrier (đó là ECRS surface) |
| **Params** | như 2.3/2.5 |
| **Failure cases** | Trùng ECRS nếu barrier = rolling range và có compression: bắt buộc chạy **de-dup** (RESEARCH_PLAN §I) |
| **Visual verify** | Box + break bar |

### 2.13 Round number / magnet

| | |
|---|---|
| **Tên** | Round-number magnet (adverse / target) |
| **Causal definition** | Grid `g` (frozen, §1); `room_round_r = d×(G−E)/r`, trong đó `G` = bội gần nhất phía trước; `adverse_magnet` = có mức tròn giữa entry và target |
| **Formula** | `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:215-223` |
| **Params** | grid deterministic; `adverse_magnet_lookahead = 2R` |
| **Units** | R |
| **Failure cases** | Grid đổi theo symbol là hand-pick — cấm (`:216-217`); baseline chỉ telemetry, không veto |
| **Visual verify** | Indicator vẽ các mức tròn mờ; review xem break có "chạy vào số tròn" không |

### 2.14 Room / opposing structure

| | |
|---|---|
| **Tên** | Room |
| **Causal definition** | `r = |E − I|` (I = invalidation); barrier đối diện gần nhất còn active phía trước entry (trừ barrier trigger); `Room_r = d×(Z−E)/r`; nếu không có → ∞ |
| **Formula** | `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:210-213` |
| **Params** | baseline: `Room_r ≥ 2.0` mới vào (khớp target 2R); range 1.5–3.0 |
| **Units** | R |
| **Failure cases** | Barrier đối diện nằm trong buildup → bị loại oan; cần tombstone policy đúng |
| **Visual verify** | Vẽ mũi tên "room" từ entry đến barrier đối diện |

### 2.15 Signal bar + entry (điểm khác biệt lớn nhất so với các family đã chết)

| | |
|---|---|
| **Tên** | Signal bar & stop-order entry |
| **Causal definition** | Sau close bar `t` (signal bar), nếu setup hợp lệ: đặt **buy-stop tại `high_t + buf`** (long) / **sell-stop tại `low_t − buf`** (short). Chỉ fire khi giá thực sự vượt (excerpt p.22-23). Hủy lệnh nếu giá phá invalidation trước khi khớp, hoặc quá `V` bar |
| **Direction rule** | Tác giả khuyến nghị không short dưới một bullish bar mạnh và không long trên một bearish bar mạnh (paraphrase excerpt p.23); default: signal bar phải cùng chiều hoặc là doji/inside |
| **Params** | `buf = 1.0 pip` (0–3); `V = 3 bar` (1–5); invalidation = buildup extreme ± buf |
| **Units** | pips / bar |
| **Failure cases** | (a) gap mở cửa vượt luôn stop → fill xấu (xử lý bằng recheck tại fill: nếu fill xa > 0.3×ATR → `SKIP_ENTRY_GAP_RECHECK`, hủy ngày — reuse `:206-208`); (b) **Model 0 fill ambiguity**: đường tick nội suy từ M1 — xem RESEARCH_PLAN §F.3 |
| **Visual verify** | Đánh dấu signal bar + đường stop; trade phải khớp chỗ mắt thấy "break thật" |

### 2.16 Bracket quản trị (stop/target)

| | |
|---|---|
| **Tên** | Fixed bracket 2R |
| **Causal definition** | SL = `S` pips từ giá fill, TP = `2S`; đặt ngay khi fill; **không** BE, không trailing, không partial, không manual exit trong baseline |
| **Params** | `S = 10` (range 8–16); `b = 2.0` cố định |
| **Units** | pips / R |
| **Failure cases** | News/VOL events cuốn qua cả 2 chiều: log `AMBIGUOUS_BAR`; Friday/news flat cắt lệnh → log riêng, tính vào stress `b` |
| **Visual verify** | Vẽ SL/TP lines; kiểm tra 100% lệnh có bracket ngay khi mở |

### 2.17 Manual exits / scratch (Volman ch.6) — telemetry-only

| | |
|---|---|
| **Tên** | News report exit / resistance exit / reversal exit |
| **Nguồn** | UPA chương 6 (excerpt p.26-29 có nhắc) |
| **Quyết định** | **Không code trong baseline** vì sẽ nén payoff `b` và phá cost geometry (COST_FEASIBILITY §5); chỉ log các mốc tương ứng (tin tức, barrier đối diện đến gần, powerbar ngược) để revision có cứng liệu |
| **ASSUMPTION** | Đây là adaptation có chủ ý: T2 charter cũng cấm manual/discretionary exit (`PRO_TRADER_REPLACEMENT_E02_T2_P0_CHARTER.json:193-201`) |

### 2.18 Breakdown / skip reasons (first-class)

Các trạng thái bắt buộc log: `SKIP_NO_BARRIER`, `SKIP_WARMUP`, `SKIP_DUPLICATE_BARRIER`,
`SKIP_NO_PRESSURE`, `SKIP_NO_BUILDUP`, `SKIP_CHOP`, `SKIP_ROOM`, `SKIP_COST`,
`SKIP_SPREAD`, `SKIP_NEWS`, `SKIP_FLAT`, `SKIP_DIRECTION_CONFLICT`,
`SKIP_ENTRY_GAP_RECHECK`, `SKIP_PBP_EXCLUDED`, `SKIP_MIN_LOT`.
Tái sử dụng tinh thần `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:119`
(AMBIGUOUS/SKIP) nhưng **không** dựng identity scheme phức tạp (bài học T2 P3).

---

## 3. Feature vector (chỉ dùng cho revision scoring — không baseline)

Reuse 23 feature của T2 P2 §9 rút gọn còn 12 cái có ý nghĩa Volman:

`touch_count`, `barrier_age`, `break_atr`, `pressure_mean`, `pressure_duration`,
`buildup_len`, `1−Contraction`, `OverlapMean`, `Progression`, `1−CounterRatio`,
`Room_r/4`, `rho`.

Chuẩn hóa: `z = (x−median)/(1.4826×MAD)` fit trên DESIGN only,
clip `[−5,5]` (`:282-285`). Không hyperparameter optimizer; logistic L2 λ=1
(`:286-293`). Chỉ mở khi có đủ điều kiện ở RESEARCH_PLAN §E.4.

---

## 4. Visual verification protocol (detector-fidelity)

Mỗi candidate khi xuất ra được kèm **snapshot 1 file PNG** vẽ:
bar chart + EMA25 + các barrier active (line + touch count) + box buildup +
signal bar (viền) + đường stop-entry + SL/TP + nhãn skip/accept lý do.

Tiêu chí mắt:
1. Barrier B phải "nhìn thấy được" (≥2 touch rõ).
2. Buildup nằm sát barrier, biên không bị xuyên nhiều.
3. Signal bar đóng cùng chiều dự kiến.
4. Giá phải có đường chạy tới target (room) không bị chặn giữa.
5. Nếu mắt thấy 1 trong 5 điều trên sai → grader đánh C.

Rubric A/B/C: xem RESEARCH_PLAN §E.3.
