# RESEARCH_PLAN — EA_VolmanPA (VPA-P0)

Status: `PLAN_DRAFT / PLANNING_ONLY — NO EA CODE, NO MT5, NO ECONOMIC AUTHORITY`
Task: VPA-P0 (Lead, 2026-09-20) · Package sẽ tạo: `03. EA Developer/EA_VolmanPA/`
Authority chain: Owner request → `01. GOAL/GOAL.md` → `AGENTS.md` →
`05. Playbook/WORKFLOW.md` → tài liệu này (draft).
Tài liệu kèm: `PLAN/FEATURE_SPEC.md` (concept→feature), `PLAN/COST_FEASIBILITY.md`
(cổng chi phí, số đo).

---

## A. Tóm tắt điều hành và logic GO / NO-GO

### A.1 Mục tiêu

Biến phương pháp price-action của Bob Volman (khung 5 phút, sách *Understanding
Price Action* 2014) thành một EA MT5 **scalping có kỷ luật** đạt hợp đồng GOAL:
PF > 1.30 sau cost x1, stress x1.5 ≥ 1.25 / x2 ≥ 1.00, **10–40 lệnh/tuần/symbol**,
né tin, không giữ weekend (`01. GOAL/GOAL.md:17-22,43-47`). Package mới sạch dưới
`03. EA Developer/`, tái dùng `_Shared/Execution/AF_ExecutionKernel.mqh`
(`GOAL:34-37`).

### A.2 Vì sao kế hoạch này khác các family đã chết

Repo đã đo được một "định luật nghịch": family nào cũng chết ở **tight geometry**
— hot cache ghi trực tiếp "mọi family đã chết đều tight-geometry — đây là lý do
cấu trúc, không phải param" (`04. Memory/hot.md:63-66`). Toán học đằng sau:
với stop 8 pip, payoff thực 1.0586R và cost 1.5/2.25/3.0 pip, PF>1.30/x1.5/x2 đòi
WR **63.9%/67.3%/66.8%** trong khi trần WR đo được của toàn repo là **47.151%**
(N=3,703; `02. AlphaFactory/STRATEGY_LOG.md:5441-5444`;
`04. Memory/research/20260726_REDTEAM_FULL_REPO_REVIEW.md:218-226`).

REDTEAM kết luận: **trục binding là payoff, không phải entry** — nâng payoff từ
1.0586R lên 2.0R kéo required WR xuống ~46%, "about 1 point short instead of 20";
nhưng "45 of 84 IDs searched entry variants, only 3 of 84 ever varied exit/payoff
geometry" (`REDTEAM:228`). LAB_MAP xác nhận: không mechanism nào trên feed này
đạt hợp đồng GOAL, density có lời ~0.3–3 event/tuần/symbol tại PF 1.2–1.6
(`04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:72-84`).

Một cạm bẫy nữa đã trả giá và trực tiếp đe dọa kế hoạch này: **probe-vs-governed
gap** — probe Stage-0 book entry tại close của signal bar, còn governed fill tại
open bar kế; edge +6.28p của một probe từng bốc hơi hoàn toàn khi vào governed
(PF 0.825), và mọi edge đo ở granularity bar-close phải được discount
~(spread RT + adverse gap) trước khi tin (`04. Memory/hot.md:134-139`). Hệ quả
thiết kế: census P2 **không được báo edge**, chỉ báo cadence/geometry; mọi kết
luận payoff phải chờ fill semantics của EA (stop order) và được verify lại.

**Volman UPA là biểu diễn gần như tinh khiết của trục payoff chưa khai thác:**
entry bằng **stop order ngay khi giá phá signal bar**, bracket cố định **10 pip
stop / 20 pip target** (tác giả đề xuất đúng bracket này và nói nó làm việc tốt
trên khung 5 phút hoạt động bình thường — official excerpt UPA, p.22).
Không BE, không trailing, không partial, không manual exit ở baseline.
Nếu cost geometry đứng được (§D), đây là cấu trúc payoff **2.0R** — thứ repo
chưa từng chạy governed.

Kế hoạch này **không hứa** PASS. Nó hứa: (1) falsify rẻ và sạch nếu không có
edge; (2) nếu thất bại, thất bại với thông tin định lượng về trục payoff; (3)
không lặp lại cái chết của T2 (O(n²) replay, identity scheme, governance nặng).

### A.3 Tiền lệ T2 — học để không lặp

Prior attempt "T2 Volman Causal Price-Action Grammar" (EURUSD M5) đạt P3 rồi chết
ở ENGINEERING, chưa từng đọc market outcome:

- Full replay 596,141 bar **timeout 3,600s** không packet; benchmark 50,000 bar
  deterministic chỉ 8.86s (`04. Memory/research/20260813_T2_P3_ENGINEERING_CLOSEOUT.md:17-18`).
- Root cause: **O(n²)** — `ecrs_prefix` tính lại ATR-SMA20 và tick-volume-SMA20
  cho toàn series tại mỗi signal index (`:28-34`).
- Sau khi sửa cache, full replay chạy 165.68s nhưng fail tại
  `pbp_identity_projection_full`: **11 duplicate normalized T2 PBP identities**
  (`:45-59`).
- Kết quả cuối: `TERMINAL_T2_P3_DUPLICATE_IDENTITY_POPULATION`, không có
  economic result, không packet (`:5,60-65`).
- Hệ thống governance: charter + source matrix + P2 spec + data epoch + 45
  economic cells + 9 diagnostics + identity locks (`PRO_TRADER_REPLACEMENT_E02_T2_P0_CHARTER.json`).

**REUSE (định nghĩa, không copy code):**
- Bộ phương trình barrier/pressure/buildup/combi/pullback-reversal đã được viết
  và QC trước outcome: `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:43-213`
  → dùng làm *định nghĩa tham chiếu* trong `PLAN/FEATURE_SPEC.md`.
- Ý tưởng deterministic fixture + prefix invariance (`P2 spec:345-366`).
- Danh sách non-claim/adaptation (`P1 matrix:32-46`): vẽ line là diễn giải cá
  nhân còn bar break mới là sự kiện khách quan; pressure OHLC **không phải**
  order flow.
- Cổng material-difference với ECRS/PBP (`P0 charter:46-51`).
- Cost unit + cửa sổ risk 0.60–1.40 ATR (`P2 spec:192-213`) — tham chiếu.

**AVOID (đã trả giá, cấm lặp):**
- Không replay toàn series O(n²); mọi feature incremental O(1)/O(k) + benchmark.
- Không dựng identity scheme (SHA256 barrier id + normalized overlap fields +
  uniqueness guard). Dùng log CSV với `(side, level, lock_bar_idx, setup_type)`;
  de-dup bằng so timestamp với family đã chết.
- Không governance nhiều tầng (charter/P0..P12/45 cells/9 symbols/2 rater×1080
  windows). Một symbol trước, 1 primary arm, tối đa 2 revision.
- Không claim "faithful replication" 70-tick; không custom tick bars (xem §B.1).
- Không mở "zero-cost source frontier" mới; không revive Sonic/ITS/MZMS/…

### A.4 Logic GO / NO-GO (cổng rút gọn)

```
G0 De-dup + prereg     ──fail──> KILL (trùng family đã chết / không freeze được)
G1 Cost-geometry gate  ──fail──> KILL hoặc BLOCKED (COST_FEASIBILITY.md)
G2 Detector census     ──fail──> KILL (không đủ cadence outcome-blind)
G3 Detector fidelity   ──fail──> revise detector (engineering) hoặc KILL nếu 2 lần fail
G4 Engineering gate    ──fail──> ENGINEERING_FIX (không đổi market logic)
G5 Economic baseline   ──fail──> MARKET_REVISION (tối đa 2) → hết budget = KILL
G6 Forensic + Validation (chỉ survivor)
```

Quy tắc cứng: baseline + **tối đa 2 market-logic revision** rồi KILL hẹp
(`GOAL:58`, `WORKFLOW:14-16`). OOS/final holdout **luôn kín** tới khi freeze
config (`WORKFLOW:16`).

---

## B. Concept → quantified feature

Bảng đầy đủ (18 concept, công thức, params, failure, cách verify mắt) nằm ở
`PLAN/FEATURE_SPEC.md`. Tóm tắt ở đây.

### B.1 Quyết định timeframe: M5 (UPA) là primary — KHÔNG custom tick bars

| Lựa chọn | Quyết định | Lý do |
|---|---|---|
| **M5 (UPA 2014)** | **PRIMARY** | Đúng khung của sách thứ hai; khớp universe TF native MT5 (`GOAL:29`); data M1→M5 dày 2010–2026 trong repo; prior T2 đã freeze M5 là primary (`P1 matrix:36`) |
| 70-tick (FPAS 2011) | **REFERENCE-ONLY** | "requires the ordered broker tick stream. M1 OHLC or generated tick interpolation cannot substantiate the original method" (`campaign:393-395`); tick cache thật chỉ có 202609 (`20260916_COST_PLANE_AUDIT.md:57-65`) |
| Custom tick bars (100/240-tick) | **KHÔNG** trong P0–P5 | (a) ngoài scope TF native; (b) đòi tick-bar engine song song Python+MQL5 — đúng loại engineering scope đã giết T2; (c) real-tick coverage chưa chứng minh được 2016→nay. Chỉ xét lại như generation riêng **sau khi** M5 pass economic gate |
| M15/H1/H4/D1 | không dùng | Volman UPA là M5; mở rộng TF là rescue không có cơ sở |

`ASSUMPTION:` tác giả nói nguyên lý price action dùng được ở mọi time frame và
mọi thị trường (excerpt p.6), nên M5 hợp lệ về nguyên lý, nhưng ta vẫn chỉ claim
"Volman-inspired" như T2 (`campaign:395-396`).

### B.2 Bảng tóm tắt 18 concept

| # | Concept | Feature chính | Đơn vị | Baseline dùng làm gì |
|---|---|---|---|---|
| 1 | Bias / dominant pressure | `bias_d` = EMA25 slope + side | ATR | Filter hướng |
| 2 | EMA25 magnet | `possess`, `touch`, `dist_atr` | ATR | Context + possession |
| 3 | Horizontal barrier / double top | Locked level, touch count | pips | **Điều kiện chính** |
| 4 | Pressure | Disp/ER/MeanCLV/EMASlope | ATR | Setup core |
| 5 | Buildup | Contraction/Overlap/Progression/CounterRatio | ratio | **Setup core** |
| 6 | Squeeze | bar kẹp EMA-barrier | bar | Context |
| 7 | Tease / false break | wick vượt, close ngược | ATR | Context (trap) |
| 8 | Barb wire (Brooks) | chop = overlap+doji+no-progression | ratio | Veto mềm (đo trước) |
| 9 | First/second break | FPAS 70-tick | — | Reference-only |
| 10 | Pullback reversal | Depth 40–60% + contact + release | ratio/ATR | Setup phụ (revision) |
| 11 | Combi | pressure bar + inside bar | ATR | Setup phụ (revision) |
| 12 | Range break | barrier + buildup + close-break | pips | Setup core |
| 13 | Round number | grid deterministic | R | Telemetry |
| 14 | Room | `Room_r ≥ 2.0` | R | Veto (giữ payoff) |
| 15 | Signal bar + stop entry | high/low + 1 pip | pips | **Execution core** |
| 16 | Bracket 10/20 | SL=S, TP=2S | pips | **Payoff core** |
| 17 | Manual exits (ch.6) | news/resistance/reversal exit | — | Telemetry-only baseline |
| 18 | Skip enums | first-class log | — | Bắt buộc |

### B.3 "Cái gì để TRAIN/CALIBRATE" ở tầng concept

- **Không train** ở baseline: mọi ngưỡng lấy từ sách (25ema, 40–60%, 10/20,
  "1 pip beyond signal bar") hoặc từ T2 P2 đã freeze trước outcome.
- **Calibrate** (DESIGN only, bounded): 4 tham số vận hành — `S` (stop pips),
  `V` (số bar hiệu lực lệnh), `Room_min`, `overlap/contraction` tolerance —
  trên lưới prereg (xem §E.5).
- **Học (ML)**: không cho baseline; điều kiện mở ở §E.4.

---

## C. "Kẻ line" algorithms — incremental, repaint-free, deterministic

Nguyên tắc từ chính Volman: line là diễn giải cá nhân, nên chỉ riêng việc giá
xuyên qua line không phải tín hiệu tốt; ngược lại, break của một bar M5 là sự
kiện khách quan, và bar càng nằm ở vị trí quan trọng thì break càng có sức nặng
(paraphrase excerpt p.8-9). Vì vậy: **line/barrier là bộ nhớ hướng của context;
trigger luôn là bar break.**

### C.1 Pipeline mỗi bar (O(1)/O(k))

```
new closed bar t
  ├─ update EMA25, ATR14                     O(1)
  ├─ update pivot ring buffer (confirm lag L) O(1)
  ├─ update barrier engine (test/expire/lock) O(k), k ≤ 8 active
  ├─ update buildup/squeeze window stats      O(1) incremental sums
  ├─ if candidate at t: emit signal/skip row  O(k)
  └─ (EA) manage stop-order validity, bracket O(1)
```

### C.2 EMA bias — O(1)

`EMA25_t` incremental. Slope 6 bar = `EMA_t − EMA_{t−6}` (ring buffer 7 giá
trị). `bias_d` như FEATURE_SPEC 2.1. Không repaint vì chỉ dùng bar đã đóng.

### C.3 Causal swing pivots — O(1), không repaint

- Đỉnh tại `i` được **xác nhận** tại bar `i+L` khi `high_i` là max của
  `[i−L, i+L]`; `L=2` default (range 1–4).
- Ring buffer 64 pivot đã xác nhận `(bar_idx, price, kind)`. Pivot chưa xác
  nhận **không** được dùng.
- Không dùng zigzag/CopyRates lookahead. Test prefix invariance bắt buộc (§C.7).

### C.4 Barrier engine — O(k), k ≤ 8

Bám theo `P2 spec §2` nhưng đơn giản hóa:

1. Ứng viên: từ mỗi pivot xác nhận, quét ngược `scan=17` bar tìm touch
   (|Δgiá| ≤ `eps=0.10×ATR`), mỗi touch cách nhau ≥2 bar.
2. `B = median(touch prices)`; lock khi `touches ≥ T_min=2` và close bar lock
   chưa phá (`close_l ≤ B+0.05A` upper / `≥ B−0.05A` lower).
3. Active `l+1..l+E`, `E=12`; hết hạn → tombstone `(side, B, lock_idx, exp_idx)`
   giữ 48 bar cho audit + PBP exclusion. **Không merge, không recenter.**
4. Dedupe: nếu barrier mới trùng barrier active cùng phía (`|B_new−B_act| ≤
   0.10×ATR` hoặc chia sẻ ≥2 touch timestamp) → `SKIP_DUPLICATE_BARRIER`.
   Ties khi phá: chọn barrier gần `close_{t−1}` nhất; nếu nhiều barrier bị phá
   cùng close → **chỉ barrier gần nhất tạo candidate**, các barrier kia bị
   consume (`P2 spec:72-76`) — chặn densification.
5. Tại mọi lúc ≤8 active barrier (ring cố định). Không cấp phát động trong
   OnTick.

### C.5 Pattern line / trendline — CONTEXT-ONLY (không trigger)

- Đường chéo nối các pivot đỉnh (cho bear) hoặc đáy (cho bull), **chỉ cho phép
  slope ≤ 0 cho bull setup và ≥ 0 cho bear setup** — theo chỉ dẫn của tác giả:
  line cho phe bull nên nằm ngang hoặc dốc xuống qua các đỉnh giảm dần, không
  bao giờ dốc lên; phe bear làm ngược lại (paraphrase excerpt p.8).
- Cập nhật chỉ khi có pivot xác nhận mới **cải thiện fit** (min squared
  distance) và giữ nguyên dấu slope; tối đa 2 pivot do đó là đường thẳng xác
  định, không fitting động.
- Dùng làm: (a) telemetry "line perforated trước/sau bar break"; (b) context
  cho squeeze (bar kẹp giữa line và EMA). **Không bao giờ là trigger** — đây
  cũng là điều P1 matrix đã chốt (`P1 matrix:38`).

### C.6 Round-number grid — O(1)

Grid deterministic theo `P2 spec:215-223` (không hand-pick per symbol). Context
+ "adverse magnet" telemetry; baseline không veto.

### C.7 Determinism & prefix-invariance (bắt buộc, học từ T2)

- Mọi state chỉ phụ thuộc bar `≤ t`. Test: chạy trên prefix `[0..t]` và trên
  full history, assert mọi barrier/signal/skip `≤ t` giống nhau byte-level.
- Log quyết định có `decision_asof`, `bar_utc`, inputs tóm tắt.
- Không random, không thời gian hệ thống trong logic; `GetTickCount` chỉ dùng
  cho telemetry/benchmark.
- Deterministic replay trong tester phải byte-identical (signal log SHA).

### C.8 Performance budget (bài học O(n²) T2)

- Toàn bộ pass trên 600k bar M5 phải chạy **< 60 giây** ở Python reference và
  **không** làm chậm tester (MQL5 chỉ O(1)/O(k), không CopyRates lịch sử dài
  trong OnTick).
- Benchmark gate: 50,000 bar prefix < 5s (Python), full DESIGN (2016–2021) <
  60s; nếu vượt → engineering fix trước khi đi tiếp (không được "đợi").

---

## D. Cổng khả thi cost-geometry (chạy TRƯỚC khi code setup)

Số liệu đầy đủ + cách tính + ngưỡng KILL: `PLAN/COST_FEASIBILITY.md`.
Tóm tắt:

| Symbol | Verdict | Stop range viable (b=2.0) | Ghi chú |
|---|---|---|---|
| EURUSD | **PASS** | 8–40 pips | Ứng viên Phase-1; S=10 → reqW 42.9% (x1) |
| GBPUSD | PASS | 10–40 | Witness symbol |
| USDJPY | PASS (sát) | 12–40 | S=10 → 44.3% > ngưỡng → chỉ S≥12 |
| USDCHF | PASS | 10–40 | Witness symbol |
| USDCAD / AUDUSD / NZDUSD | **BLOCKED** | — | Chưa có spread đo → cấm economic run |
| XAUUSD | **FAIL** (research plane) | — | c_rt p90 = 8.03p; kể cả S=40 cần 46.5% WR > ngưỡng 44% |

- Ngưỡng KILL: `reqW(PF1.30, x1) > 44.0%` hoặc `reqW(PF1.00, x2) > 42.0%` →
  không khả thi. Số 44% đặt dưới trần đo được 47.151% đúng 3.15 điểm
  (`STRATEGY_LOG.md:5441-5444`).
- **Stress b-compression**: ở `b = 1.7R` không stop nào còn margin → baseline
  bắt buộc **không** cắt payoff (no BE/trailing/partial/manual exit). Đây là
  điểm dễ bị vi phạm nhất khi code; phải có test.
- Việc còn lại trước economic run: đo cost 3 symbol BLOCKED; đo per-session
  spread; đo commission deploy-venue; chốt server-clock offset.

---

## E. TRAIN / CALIBRATE — và cách không overfit

### E.1 Nguyên tắc

Rules-first (GOAL: "không đơn giản hóa nhưng cũng không phức tạp hóa",
`GOAL:8-10`). Baseline là luật tường minh; calibration chỉ vặn các tham số vận
hành đã khai báo, **chỉ trên DESIGN**, chọn **plateau** không chọn đỉnh
(`WORKFLOW:112-118`).

### E.2 Calibration trên DESIGN (thủ tục)

1. Lưới prereg tối đa **24 tổ hợp**/cell: `S ∈ {10,12,16}` × `V ∈ {2,3}` ×
   `Room_min ∈ {1.5,2.0}` × `T_min ∈ {2,3}` (đóng băng trước khi chạy).
2. Mỗi tổ hợp = 1 run riêng, log đầy đủ; chọn **vùng plateau** (PF biến thiên
   < 0.10 giữa các neighbors), không lấy max.
3. Mọi trial đếm vào trial debt; nếu số cell kinh tế > 20 → tính DSR/PBO
   (`WORKFLOW:117`).
4. Không dùng validation/OOS/holdout trong bước này.

### E.3 Dataset gán nhãn (detector fidelity) — cách làm

**Lấy mẫu:** từ census outcome-blind trên DESIGN (P2), rút `N=300` detection
ngẫu nhiên seed cố định `20260920`, phân tầng theo setup type × session, tối đa
1/ngày/type để tránh cluster.

**Snapshot:** mỗi case 1 PNG 120 bar trước + 40 bar sau (che outcome sau quyết
định) + dump JSON feature tại `decision_asof`.

**Rubric (chấm A/B/C):**

| Grade | Nghĩa | Điều kiện |
|---|---|---|
| **A** | Volman-grade, sẽ vào lệnh | Barrier nhìn thấy được (≥2 touch rõ); buildup sát barrier; signal bar đúng chiều; room ≥2R không bị chặn; hướng khớp bias |
| **B** | Biên, có thể vào | Thiếu 1 tiêu chí phụ (ví dụ buildup mỏng, room 1.5–2R, EMA hơi xa) nhưng không phản thesis |
| **C** | Không nên vào | ≥2 tiêu chí sai, hoặc 1 lỗi nặng: không có barrier thực, break ngược buildup, adverse magnet chặn giữa, entry vào "false break" rõ ràng, setup trùng family đã chết |

**Người chấm:** (1) worker LLM subagent chấm pass-1 theo rubric + feature dump;
(2) Lead (Claude) adjudicate toàn bộ C và mọi bất đồng; (3) Owner spot-check 30
case ngẫu nhiên. Metric: precision A+B ≥ 80% (Wilson 95% LB ≥ 72%), agreement
LLM-vs-Lead ≥ 0.70 (Gwet AC1). `ASSUMPTION:` T2 charter yêu cầu 2 independent
raters (`P0 charter:230-231`); kế hoạch này thay bằng 1 LLM + Lead +
Owner-spot-check vì chi phí — Lead/Owner quyết.

**Recall spot-check:** 20 session đầy đủ (10 London, 10 NY) được Lead đọc tay
trên chart sạch; đếm setup A-grade bị detector bỏ sót; yêu cầu recall ≥ 70%;
mọi false-negative phải phân loại (thiếu barrier / thiếu buildup / rule defect).

### E.4 ML — có justified không?

**Baseline: KHÔNG.** Lý do: (a) GOAL rules-first; (b) T2 P0 charter tự cấm
hyperparameter optimizer và yêu cầu một fitting duy nhất
(`P0 charter:155-158`); (c) repo đã chứng minh ML gate trên entry yếu
(HYP-ICT-FVG-PROB-RANK PF<1, AUC 0.4879 — `do_not_repeat_failures.md:519-534`).

**Điều kiện mở ML (chỉ như revision, có prereg riêng):**
1. Rules baseline có **gross edge** rõ và payoff `b ≥ 1.7` giữ được.
2. WR thấp hơn `reqW` ≤ 3 điểm (biên, không phải hụt 20 điểm).
3. Trên 300 case đã chấm, ≥2 feature đơn biến có AUC ≥ 0.55 với nhãn A-vs-C.
4. Dùng đúng 1 logistic L2 λ=1, 12 feature (§FEATURE_SPEC 3), fit DESIGN only,
   không search.
Không đạt 4 điều kiện trên → không ML.

### E.5 Data split + trial budget

| Split | Khoảng | Vai trò |
|---|---|---|
| **DESIGN** | 2016-01-01 → 2021-12-31 (6 năm, ~313 tuần) | Calibration + detector grading + economic baseline |
| **VALIDATION** | 2022-01-01 → 2023-12-31 (2 năm) | Kiểm tra lần đầu sau freeze |
| **OOS** | 2024-01-01 → 2025-06-30 (1.5 năm) | Mở 1 lần |
| **FINAL HOLDOUT** | 2025-07-01 → 2026-09-15 (cutoff) | Kín tới khi freeze config |

`ASSUMPTION:` broker (MQ-Demo/FivePercent) phục vụ được các cửa sổ này; parquet
M1 cache 2010–2026 đã có cho 8 symbol.

**Trial budget:** baseline + 2 revision = **3 logic cell/symbol**. Mỗi cell ≤
24 tổ hợp calibration (E.2). Tổng ≤ 72 economic run/symbol; DSR tính với N =
số run thực tế. Không mở rộng multi-symbol (Option B của REDTEAM) trước khi
EURUSD có baseline.

---

## F. Kiến trúc MQL5 — `03. EA Developer/EA_VolmanPA/`

### F.1 Layout package (theo pattern packages sạch hiện có)

```
EA_VolmanPA/
├─ EA_VolmanPA.mq5                  # EA chính (self-contained logic + kernel)
├─ VP_VolmanPA_Chart.mq5            # companion indicator (forensic)
├─ ALPHAFACTORY_EA_CONTRACT.json    # bắt buộc cho ea_research_loop (ea_contract.ps1:42,75)
├─ Include/
│  ├─ VP_Types.mqh                  # enum, struct, skip reasons
│  ├─ VP_Features.mqh               # EMA/ATR/pressure/buildup (O(1)/O(k))
│  ├─ VP_Barrier.mqh                # barrier engine + tombstones
│  ├─ VP_Setup.mqh                  # detectors: pattern-break, combi, PR
│  ├─ VP_Session.mqh                # clock, session, news, Friday flat
│  ├─ VP_Risk.mqh                   # sizing, daily/DD locks (5%/10%), min-lot
│  ├─ VP_Execution.mqh              # stop-order lifecycle qua kernel
│  └─ VP_Telemetry.mqh              # journal chain + counters
├─ README.md
└─ research/
   ├─ CONTRACT.md                   # frozen spec của lần chạy
   ├─ HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md
   ├─ evidence/                     # cost manifests + sidecars
   └─ preflight/HYP-VPA-EURUSD-M5-001/task_packet.json
```

Tái dùng: `_Shared/Execution/AF_ExecutionKernel.mqh` (BẮT BUỘC theo `GOAL:34-37`;
include như `EA_LiquiditySweep.mq5:22-23`), `_Shared/Telemetry/AF_LifecycleTelemetry.mqh`,
`_Shared/MarketData/AF_TickCursor.mqh`. **Copy pattern, không copy code** từ
EA_LiquiditySweep/EA_SessionDrive (dead logic không được di truyền; chỉ mượn
khuôn `OnInit/OnTick/OnTradeTransaction`, clock/news/locks — đã kiểm chứng hoạt
động ở `LSW_Session.mqh:82-177`, `LSW_Risk.mqh:194-257`).

### F.2 Modules

| Module | Trách nhiệm | Nguồn tham chiếu |
|---|---|---|
| `VP_Features` | EMA25, ATR14, pressure, buildup stats, CLV, dist | FEATURE_SPEC 2.1–2.8 |
| `VP_Barrier` | pivot ring → touch cluster → lock/expire/tombstone/dedupe | §C.4 |
| `VP_Setup` | Pattern-break (A1), Combi (A2), Pullback reversal (A3); PBP exclusion; room; chop veto. **Arbitration:** khi nhiều setup cùng lúc — ưu tiên Combi > Pattern-break > Pullback-reversal; ngược hướng → `SKIP_DIRECTION_CONFLICT`; cooldown K bar sau khi lệnh đóng (K=1 default); tối đa 1 vị thế mở/symbol | FEATURE_SPEC 2.5–2.12 |
| `VP_Session` | server→UTC, London/NY window, lunch flag, news blackout, Friday/daily flat | `LSW_Session.mqh` pattern |
| `VP_Risk` | sizing money-per-lot most-conservative, min-lot reject, daily 5% / max 10% (The5ers High Stakes), streak lock, restart-safe state | `LSW_Risk.mqh` + `SNR_Discipline.mqh:35-68` cho persistence |
| `VP_Execution` | stop-order placement/cancel/expire; fill recheck; SL/TP bracket; bracket integrity test | `AF_ExecutionKernel.mqh` |
| `VP_Telemetry` | chain signal→request→order→deal→position→exit + counters + skip enum | `LSW_Telemetry.mqh:1-11` pattern + `_Shared` lifecycle CSV |
| companion indicator | vẽ barrier lines + touch count + buildup box + squeeze + signal arrows + SL/TP + HUD skip counters | pattern `SNR_SRLevels.mq5:19-79` + boxes `SMC_Order_Block_Detector.mq5:88-186` |

### F.3 Execution semantics (điểm rủi ro cao nhất)

1. Tại close signal bar `t` (trong `OnTick` khi `iTime(_Symbol,PERIOD_M5,0)`
   đổi — pattern `EA_LiquiditySweep.mq5:784-792`): nếu setup hợp lệ và không
   bị risk/session/news veto → gửi **buy-stop/sell-stop** với `V` bar hiệu lực.
2. Khi fill: `OrderCheck` trước send (kernel tự làm, `AF_ExecutionKernel.mqh:335-373`);
   đặt SL/TP theo `S` cố định từ **giá fill thực**; nếu fill xa quá
   `0.3×ATR` so với mức stop → close ngay và log `SKIP_ENTRY_GAP_RECHECK`
   (tinh thần `P2 spec:206-208`).
3. **Model 0 fill ambiguity:** tester generated-tick path nội suy từ M1 —
   entry stop có thể khớp ở giá khác live. Bắt buộc:
   - đếm `ambiguous_fill` (bar M1 chứa cả mức entry lẫn mức SL);
   - chạy stress "adverse-first" trên các bar ambiguous (offline probe);
   - cross-check real-tick (Model 4) trên cửa sổ có tick thật + reconcile demo
     forward trước promotion (`WORKFLOW:138-141`).
   Đây là điều kiện "tester-live parity" của `WORKFLOW:66-67`; không đạt →
   chỉ được claim diagnostic, không promotion.
4. Không manual exit, không BE, không trailing, không partial. Ngoại lệ duy
   nhất: news blackout flatten, Friday flat, daily/DD lock (là safety, phải log
   và được stress như nhóm làm xấu `b`).
5. **Probe-vs-governed discipline:** mọi Python probe/fill model phải dùng đúng
   fill semantics của EA (stop fill tại mức stop + adverse, không book tại
   close bar) và discount `spread_rt + adverse_gap` trước khi báo bất kỳ edge
   nào (`04. Memory/hot.md:134-139`). Nếu probe và governed lệch > 20% số lệnh
   hoặc > 0.15R expectancy → dừng, điều tra parity trước khi đọc economics.
6. Prop-firm locks: **daily 5% / max 10%** (The5ers High Stakes) — hiện shelf
   dùng 2%/10% (`EA_LiquiditySweep.mq5:78-79`); EA_VolmanPA set 5%/10% theo
   task, có test cho cả hai mức.

### F.4 Performance & tính đúng

- Mọi feature incremental; ring buffers cố định; không `CopyRates` dài trong
  `OnTick`; không cấp phát động trong hot path.
- Barrier engine ≤8 active + ≤16 tombstone.
- Không dùng `tick_volume` như order flow (`P1 matrix:39`; `P2 spec:95`).
- Test suite (§F.6) chạy bằng `alpha.ps1 compile` + script test riêng; không
  thêm governance layer.

### F.5 Companion indicator (forensic chart)

`VP_VolmanPA_Chart.mq5` — object overlay, không buffer:
- barrier active/tombstone: `OBJ_HLINE` + label touch count + side color;
- buildup/squeeze box: `OBJ_RECTANGLE`;
- signal: arrow + label `PB/COMBI/PR`;
- stop-entry line + SL/TP lines khi có lệnh (đọc từ EA qua GlobalVariables
  hoặc vẽ từ log — chọn cách đơn giản: indicator tự tính lại cùng engine,
  không đọc state EA);
- HUD đếm skip lý do (góc phải-trên theo lesson `AGENTS.md` HUD LTF = trái-trên;
  tuân thủ để không đè giá);
- xóa prefix `VP_` trước khi vẽ lại (lesson `SNR_SRLevels.mq5:21-30`).

### F.6 Test plan

| Nhóm | Test | Gate |
|---|---|---|
| Unit | ATR/EMA parity với MT5 indicator; pressure/buildup fixtures | pass 100% |
| Prefix invariance | thêm suffix future → mọi state/signal ≤ t không đổi | byte-identical |
| Non-repaint | audit tool của AlphaFactory (`alpha.ps1 validate-full` chạy `audit_mql5_nonrepaint.py`) | pass |
| Sizing/geometry | volume step/min-lot/stops-level/freeze-level; reject logic | pass |
| Risk locks | daily 5% / DD 10% / Friday flat / news / restart persistence | pass |
| Bracket integrity | 100% lệnh có SL+TP ngay sau fill; không lệnh nào bị sửa bracket | pass |
| Deterministic rerun | cùng input → signal log SHA bằng nhau | pass |
| Reconcile | signal→request→order→deal→position→exit counts khớp log/report | 100% |
| Visual | 20 lệnh đại diện xem trong Visual Tester/chart thật | reviewed |

---

## G. ACCEPTANCE (nghiệm thu) theo phase

Mỗi cổng phải để lại **file bằng chứng** cụ thể; không có file = chưa pass.

### G0 — De-dup + prereg (trước mọi thứ)

| Mục | Yêu cầu | File bằng chứng |
|---|---|---|
| De-dup | Overlap trigger (outcome-blind) với SCC/ECRS/LSWEEP/SDRIVE/VRAS < 50% | `PLAN/DE_DUP_CHECK.md` |
| Prereg | Freeze: symbol/TF/decision time/entry/exit/risk/split/trials/KILL | `research/HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md` (SHA ghi vào registry row) |
| Registry | Row `state=screened` trong `04. Memory/research/CANDIDATE_REGISTRY.jsonl` | diff registry |
| Cost | Manifest bind cho symbol chạy | `research/evidence/COST_SOURCE_MANIFEST.json` |

### G1 — Engineering gate (theo `WORKFLOW:69-80`)

1. `alpha.ps1 compile "EA_VolmanPA"` → log mới `0 errors, 0 warnings` + EX5 mới.
2. Focused tests §F.6 pass.
3. Lookahead/repaint audit pass; warm-up fail-closed.
4. Deterministic rerun (khi mechanism cần).
5. Visual Tester 20 lệnh.
6. Reconcile signal/trade counts.
**Fail → ENGINEERING_FIX, không đổi market logic (`WORKFLOW:80`).**

### G2 — Detector-fidelity gate (mới, chống "ảo giác code")

| Metric | Ngưỡng | Bằng chứng |
|---|---|---|
| Precision A+B | ≥ 80% trên N=300 (Wilson LB ≥ 72%) | `PLAN/grading/G2_scores_<seed>.csv` |
| Recall (spot-check) | ≥ 70% trên 20 session | `PLAN/grading/G2_recall.md` |
| Agreement LLM-vs-Lead | Gwet AC1 ≥ 0.70 giữa pass-1 (worker LLM) và pass-2 (Lead, blind) | `G2_agreement.json` |
| Owner spot-check | 30 case; không có ≥3 case "C rõ ràng" bị chấm A | `G2_owner_spotcheck.md` |
| **Executable** cadence census | candidates/tuần **sau mọi veto** (room, session, news, Friday, risk, cost): ≥30/tuần = PASS; 10–29 = INSUFFICIENT (Lead quyết, không tự nới); <10 = KILL | `PLAN/CENSUS_<sym>.csv` |

Snapshot semantics (Lead decision #4): mỗi PNG **kết thúc tại bar quyết định**,
**zero bar sau đó**; EMA25/barrier/buildup/signal/stop-entry chỉ vẽ từ dữ liệu
`≤ t`. Bar hậu quyết định chỉ dùng cho forensics về sau và lưu **riêng** ở
`research/forensics/`, không bao giờ lẫn vào tập grading.

Fail lần 1 → sửa detector (engineering). Fail lần 2 → KILL detector hiện tại
(đây là capability, không phải market verdict).

### G3 — Economic gate (baseline trên DESIGN, `WORKFLOW:82-95`)

**Metric falsification CHÍNH (Lead decision #1 — lift over matched random):**
`lift = WR_setup − WR_random_matched`, trong đó random-matched = same symbol,
same session window, direction, bracket (S, 2S, cùng V/buffer), cùng cost tier,
cùng cửa sổ DESIGN; baseline lấy từ `PLAN/random_baseline/RANDOM_BASELINE.csv`
(12,000 mẫu/cell, seed 20260920). **PASS yêu cầu: 95% CI lower bound của lift
> 0 VÀ point lift ≥ required lift** (reqW − WR_random) của đúng cell; nếu không
→ **KILL** (không market-revision để hạ chuẩn).

| Chỉ tiêu | Ngưỡng | Căn cứ |
|---|---|---|
| **Lift tại x1** | 95% CI LB > 0 **và** point ≥ required lift (EURUSD London S=8: **+14.1pp**) | `COST_FEASIBILITY §3b` |
| **Lift tại x2** | 95% CI LB > 0 **và** point ≥ required lift (EURUSD London S=8: **+18.2pp**) | nt |
| Cadence | 10–40 trades/tuần/symbol (hard gate; <10 → báo Lead, không tự nới) | `GOAL:18,44` |
| PF x1 | > 1.30 | `GOAL:43` |
| PF x1.5 / x2 | ≥ 1.25 / ≥ 1.00 | `GOAL:45` |
| Gross PF (trước cost) | ≥ 1.10 (nếu < → KILL vì không có gross edge) | falsification floor |
| Payoff thực `b` | ≥ 1.70 (nếu < → tính lại reqW theo `b_obs`; <1.55 → KILL) | `COST_FEASIBILITY §5` |
| Sample | N ≥ 500 trades DESIGN | suy ra từ cadence × 313 tuần |
| DD | historical ≤ 6.0%; MC P95 ≤ 8.0% | reuse budget T2 (`P0 charter:247-248`) |
| Exposure | overnight ≈ 0, weekend = 0 | `GOAL:20-21` |
| History quality | > 97% | `GOAL:46` |

Geometry mặc định của G3 (chốt ở §3b.3): **EURUSD, S = 8 pips, TP = 16 pips,
V = 3 bar, buffer = 1.0 pip, London primary (UK open ±3h), NY secondary**; x1
dùng c_rt p90 EURUSD = 1.0 pip (research plane). Deploy-venue cost chỉ là dòng
sensitivity, không thay gate.

Cộng thêm đọc bắt buộc theo thứ tự `WORKFLOW:86-92`: run quality → parity/cadence
→ chart winner/loser/DD → gross vs cost → PF/net/DD → long/short + year stability.

**Kiểm tra probe-vs-governed trước khi tin PF:** đối chiếu signal set của Python
census với signal log của EA trên cùng cửa sổ; lệch > 20% số lệnh hoặc > 0.15R
expectancy → engineering/parity fix trước khi đọc kinh tế
(`04. Memory/hot.md:134-139`).

### G4 — Forensic chart review

- ≥50 lệnh/revision (survivor: 100) có snapshot decision-time + anatomy.
- Mỗi lệnh phân loại: `thesis-consistent` / `implementation-artifact` /
  `no-thesis`. Yêu cầu ≥70% thesis-consistent.
- Nếu đa số loser là `no-thesis` → đó là detector defect → engineering fix
  (không tính vào 2 revision market logic).
- File: `research/forensics/<run_id>/cases.md` + PNG.

### G5 — Validation (chỉ survivor, `WORKFLOW:125-141`)

WFA 5 cửa sổ (≥3 dương), VALIDATION PF ≥ 1.15 cùng hướng, OOS 1 lần, FINAL
HOLDOUT 1 lần sau freeze, cost x1/x1.5/x2, MC 1000 trade-order + execution
degradation, CPCV/PBO/DSR khi trials > 20, parameter sensitivity, regime/year
stability, native equity DD/time-under-water. Sau đó (chỉ khi Lead/Owner mở):
forward demo + reconcile (`WORKFLOW:155-166`).

---

## H. Phase plan, sub-agent roles, loop, kill rules, effort

### H.1 Phase table

| Phase | Mục tiêu | Output | Gate / KILL | Effort |
|---|---|---|---|---|
| **P0** | Chốt plan + de-dup + prereg + registry | `PLAN/*`, prereg, registry row | G0 | 0.5 session |
| **P1** | Cost-geometry gate | `COST_FEASIBILITY.md`, manifests | G1-cost: KILL nếu reqW > ngưỡng hoặc BLOCKED | 0.5 |
| **P2** | Python reference detector + census + fixtures + snapshots | `lab/volman_pa/*.py`, census CSV, 300 PNG | invariance tests + census ≥ 30/tuần | 2–3 |
| **P3** | Grading + fidelity gate | scores/recall/agreement | G2 | 1 |
| **P4** | MQL5 build + indicator + tests | package + EX5 + logs | G1 eng | 3–5 |
| **P5** | Baseline economics DESIGN + forensics | run dir + report + cases | G3 | 1–1.5 |
| **P6** | Revision 1 (và 2 nếu cần) | prereg mới + run + verdict | `WORKFLOW §6` | 1–2 mỗi revision |
| **P7** | Validation survivor | `validate-full` artifacts | G5 | 2–3 |

Time-to-baseline (KPI `GOAL:55`): **~8–10 session** từ khi bắt đầu P0.
(Đơn vị: 1 session ≈ một ca worker tập trung 2–4 giờ.)

### H.2 Sub-agent roles (prompt phải nhồi cứng)

| Role | Việc | Ràng buộc prompt bắt buộc |
|---|---|---|
| `researcher` | Source/URL, concept table, de-dup table | Không tải PDF pirated; chỉ official excerpts + public summaries; paraphrase |
| `feature-engineer` | Python detector, fixtures, census, snapshots | cwd cố định; read-only với repo ngoài package; prefix-invariance tests |
| `mql5-builder` | EA + indicator + tests | Không `mt5__trade_*`; không worktree; compile `alpha.ps1`; không sửa ngoài `EA_VolmanPA/` |
| `backtest-runner` | Chạy `ea_research_loop.ps1`/`alpha.ps1 backtest`, analyze | Không launch/kill MT5 tay; packet bind cost manifest; `-Execute` chỉ khi plan `execution_allowed=true` |
| `forensic-reviewer` | Chấm A/B/C, trade anatomy | Nhận snapshot + feature dump; blind với outcome (che phần sau decision) |
| `auditor` | Adversarial: lookahead, log reconcile, de-dup, trial budget | Được quyền FAIL mọi gate; báo cáo riêng |

### H.3 Loop thiết kế (research → draft → self-critique → revise)

1. Mỗi phase: research (đọc nguồn/repo) → draft artifact → **self-critique
   checklist** (lookahead? cost? de-dup? payoff? sample?) → revise → gate.
2. Sub-agent độc lập phản biện (auditor) trước khi gate được công nhận PASS.
3. Sau mỗi vòng: giữ artifact, cập nhật **một** verdict, chọn ngay bước hợp lệ
   tiếp theo (`WORKFLOW:174-176`).
4. Không dừng để xin phép giữa các bước nằm trong plan đã được Lead duyệt
   (bài học `do_not_repeat_failures.md:1513-1546`).

### H.4 Stop / kill rules tổng

| Tình huống | Hành động |
|---|---|
| Cost gate fail (reqW > ngưỡng hoặc BLOCKED) | KILL geometry đó; chỉ mở lại bằng measurement mới |
| Census < 10/tuần raw | KILL mechanism (structural, không thêm filter để densify — bài học ECRS `do_not_repeat_failures.md:328-359`) |
| Census 10–29/tuần raw | `INSUFFICIENT`; báo Lead quyết (không tự nới band) |
| Detector fidelity fail 2 lần | KILL detector hiện tại |
| Gross PF < 1.10 tại baseline | KILL (không có gross edge) |
| PF x1 ≤ 1.30 nhưng gross > 1.10 và behavior đúng thesis | MARKET_REVISION (tối đa 2), mỗi revision prereg mới |
| Hết 2 revision | KILL hẹp + closeout theo `WORKFLOW §6` |
| Engineering defect | ENGINEERING_FIX cùng revision |
| Bất kỳ thay đổi OOS/holdout trước freeze | Invalid — báo Lead |

---

## I. Risks, open questions, 3 việc đầu tiên

### I.1 Risk table

| # | Risk | Mức | Giảm thiểu |
|---|---|---|---|
| 1 | Model-0 fill ambiguity cho stop-order entry | **Cao** | Đếm ambiguous fill + stress adverse-first + Model 4 cross-check + demo forward trước promotion (§F.3) |
| 2 | Cost proxy là RESEARCH_PROXY, promotion_eligible=false; commission deploy-venue chưa đo | Cao | P1 đo; giữ verdict kinh tế là research-only tới khi verified (`WORKFLOW:250-252`) |
| 3 | Cadence Volman thấp hơn 10/tuần/symbol (sách dạy chọn lọc và nói phần lớn thời gian không có trade nào gần đáng vào — paraphrase excerpt p.21) | **Cao** | Census outcome-blind tại P2 quyết định trước khi build; không nới gate sau outcome |
| 4 | `b` bị nén bởi news/Friday flat hoặc fill xấu → required WR vọt lên | Cao | Theo dõi `b` như KPI bậc 1; log riêng nhóm bị cắt |
| 5 | Nghi vấn đạo văn/trùng lặp với family đã chết (đặc biệt SCC PBP và ECRS compression) | Trung | De-dup outcome-blind + PBP exclusion cứng (§FEATURE_SPEC 2.10) |
| 6 | Overfitting qua lưới calibration 24 tổ hợp | Trung | Plateau, trial budget, DSR khi >20 cell, holdout kín |
| 7 | Repo-wide prior "không mechanism nào pass hợp đồng GOAL" (LAB_MAP) | **Cao** | Chấp nhận; mục tiêu là falsification sạch theo trục payoff mới; nếu fail → ghi closeout có thông tin |
| 8 | Copyright — không dùng bản pirated, không reproduce text | Trung | Chỉ official excerpts + paraphrase; cite URL |
| 9 | Bar `suspect` (roll 00:00–00:15, USDJPY packed) làm bẩn signal | Trung | Loại bar `suspect` khỏi census/economics như data_plane; log |

### I.2 Open questions cho Lead

1. **Venue của economic claim là gì?** MQ-Demo (research plane, cost proxy) hay
   FivePercentOnline-Real (deploy plane, cost đo được nhưng data khác)? Task có
   nhắc The5ers High Stakes (5%/10%) nhưng repo chưa có manifest trên venue đó.
2. **Cadence band**: nếu census cho 6–9 lệnh/tuần/symbol với detector
   Volman-grade thật, Lead muốn (a) KILL theo đúng GOAL 10–40, hay (b) xin
   Owner amendment band (như LAB_MAP gợi ý "low-frequency sleeve")? Tôi không
   tự nới.
   `ASSUMPTION:` tôi giữ 10–40 là gate cứng trong plan này.
3. **XAUUSD**: chấp nhận loại khỏi Phase 1 (cost FAIL trên research plane) hay
   muốn đo cost deploy-venue trước để quyết?
4. **Grading**: 1 LLM grader + Lead adjudicate + Owner spot-check 30 có được
   chấp nhận thay cho "two independent raters" của T2 charter không?
5. **Base code**: xác nhận "copy pattern, không copy code" từ
   EA_LiquiditySweep/EA_SessionDrive — hay Lead muốn dùng thẳng `Include` của
   LSW làm shared lib?

### I.3 3 việc cụ thể đề nghị Lead giao tiếp theo

1. **P0+registry**: viết `HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md`, thêm registry
   row `screened`, chạy de-dup outcome-blind vs SCC/ECRS/LSWEEP/SDRIVE (việc
   này mở khóa task packet cho mọi run sau).
2. **P2 census**: build Python incremental detector + fixtures + prefix tests,
   chạy census DESIGN EURUSD (và GBPUSD witness), xuất `CENSUS_*.csv` + 300
   snapshot PNG — đây là bước **quyết định sống/chết** sớm nhất và rẻ nhất.
3. **P1 cost bổ sung**: đo spread/slippage USDCAD/AUDUSD/NZDUSD + per-session
   London/NY cho 4 symbol PASS, và commission deploy-venue — để cổng chi phí
   có đủ dữ liệu cho mọi symbol trong GOAL universe.

---

## J. Lead review v1 — decisions & changes (2026-09-20)

### J.1 Critical flaw fixed: lift over random, not a borrowed ceiling

Bản v1 so `reqW` với "trần 47.151%" của repo — **sai phương pháp**: con số đó đo
trên geometry ~1:1.06/stop 8 pip của một family khác nên không transfer sang
bracket 1:2. Baseline đúng là **random entry cùng geometry**: driftless ≈
`S/(S+T) ≈ 33%`. Hệ quả: cổng được viết lại thành **required lift over random**
và được đo thật trong `PLAN/COST_FEASIBILITY.md §3b` (12,000 mẫu/cell).
Kết quả chính cho primary cell EURUSD London S=8: baseline random WR = 29.8%,
b_obs = 1.99, **required lift tại x1 = +14.1pp, tại x2 = +18.2pp**; prior repo
families cho ~0 lift (47.151% measured vs 48.58% zero-edge tại b≈1.06 —
`REDTEAM:218-226`).

### J.2 Các quyết định binding của Lead (ghi nguyên trạng)

1. **Venue:** tín hiệu + backtest trên **MQ-Demo research plane** (long
   history); economic gate dùng **cost research-plane conservative (c_rt p90,
   EURUSD 1.0 pip)**; cost deploy-venue (FivePercentOnline-Real) chỉ là dòng
   sensitivity. Promotion sau này vẫn cần đo deploy-venue.
2. **Cadence:** **10–40 lệnh/tuần/symbol là hard gate.** Nếu executable cadence
   <10 → báo cáo, **không tự nới**; Lead escalate Owner.
3. **XAUUSD:** loại khỏi Phase 1–5; chỉ revisit trong task riêng sau khi đo được
   deploy-venue cost.
4. **Grading:** (a) worker LLM chấm pass-1 cả 300 case; (b) **Lead chấm độc lập,
   blind, một subset stratified 100 case**, Gwet AC1 giữa hai pass; (c) Owner
   spot-check 30 case. **Snapshot kết thúc đúng tại bar quyết định, zero bar
   sau đó**; bar hậu quyết định chỉ để forensics, lưu riêng.
5. **Base code:** chỉ **copy pattern**, include duy nhất `_Shared/*`; **không**
   include header của LSW/SDRIVE.
6. **Prop risk (dưới giới hạn The5ers):** daily loss lock **4.0%** (so với 5%)
   đo theo cách The5ers — `max(balance, equity)` tại server midnight; max-DD
   lock **8%** (so với 10%); risk mặc định **0.5%/trade**. Giữ 5%/10% chỉ như
   test case.
7. **Concurrency:** agent khác đang ghi `02. AlphaFactory/lab/*`,
   `04. Memory/hot.md`, `04. Memory/research/*` — **không được sửa**. Mọi code
   và data mới nằm dưới `03. EA Developer/EA_VolmanPA/` (v.d. `research/lab/`).
   Ngoại lệ duy nhất: **đọc lại `CANDIDATE_REGISTRY.jsonl` ngay trước khi append
   đúng MỘT dòng**, không bao giờ rewrite. Không commit.

### J.3 Thay đổi kéo theo trong plan

- **G2:** cadence dùng **executable candidates/week** (sau room/session/news/
  Friday/risk/cost vetoes), không dùng raw; snapshot semantics theo J.2.4;
  agreement metric là Gwet AC1 giữa pass-1 (LLM) và pass-2 (Lead, blind 100 case).
- **G3:** thêm PRIMARY metric lift-matched-random (95% CI LB > 0 và point lift ≥
  required lift, nếu không → KILL); PF gates giữ nguyên; geometry mặc định chốt
  **EURUSD S=8, London primary** theo quy tắc R_S ở `COST_FEASIBILITY §3b.3`.
- **P0 đã cập nhật:** prereg và registry dùng geometry S=8/London; calibration
  grid đổi từ `S ∈ {10,12,16}` thành `S ∈ {8,10}` (primary 8) + các trục V,
  room, T_min như cũ.

### J.4 P2 outcome (2026-09-20) — census outcome-blind kích hoạt STOP RULE

Detector `research/lab/vpa_core.py` (incremental O(1)/O(k), 21/21 tests PASS,
prefix-invariance PASS cả synthetic lẫn real 4,000 bar, benchmark full DESIGN
EURUSD 6.2s < 60s). Census DESIGN 2016–2021 (314 tuần):

| | EURUSD /week | GBPUSD /week |
|---|---|---|
| raw breaks (barrier lock + close-break) | 62.99 | 63.5 |
| **EXECUTABLE pattern break** | **0.035** | 0.019 |
| EXECUTABLE pullback reversal | 0.162 | 0.137 |
| **EXECUTABLE total** | **0.197** | **0.156** |

Funnel EURUSD: 19,778 raw breaks → −10,000 ngoài session → −931 bias → −2,326
chop → −5,979 no-pressure → **542 tới cổng buildup** → −531 no-buildup → 11
executable. Trần trước-buildup = 1.73/tuần, tức **cấu trúc dưới sàn 10/tuần**
chứ không phải chỉ do cổng cuối.

Theo stop rule của Lead ("executable census < 10/week → finish census + summary,
skip snapshots, report"): **STOP đã kích hoạt — bỏ qua snapshots/grading/economic
run**. Báo cáo P2 gửi Lead để quyết định: (a) KILL lane M5 EURUSD theo định nghĩa
đã freeze, hay (b) mở một detector revision mới (prereg riêng) nới đúng các
ngưỡng đang chặn + **bắt buộc qua G2 grading** trước khi tin bất kỳ số nào.
Không tự nới trong tài liệu này.

---

## Phụ lục 1 — De-dup sơ bộ (đã chốt ở G0: xem `PLAN/DE_DUP_CHECK.md`)

| Family đã KILL | Object | Khác biệt của VPA | Cách kiểm |
|---|---|---|---|
| SCC `HYP-SCC-EURUSD-M5-001` | pivot N=2 → BREAK → HOLD → first-passage RETEST continuation | VPA **không** retest entry; vào bằng stop ngay khi phá signal bar; có pressure+buildup bắt buộc; stop bracket cố định 2R | Jaccard timestamp trigger trên DESIGN (cấm >50% trùng) |
| ECRS `HYP-ECRS-EURUSD-M5-001/002` | ER10 shift + ATR compression + rolling 12-bar range break + tick-vol surge + EMA20 + session | VPA cấm dùng ER/ATR-ratio/tick-vol/session làm gate; barrier = touch cluster từ pivot (không phải rolling range); Contraction chỉ là 1 trong 7 điều kiện buildup | Kiểm tra forbidden-reconstruction list + overlap |
| VRAS `HYP-VRAS-EURUSD-M5-*` | Session-VWAP + gap + continuation | Không VWAP, không gap logic | Code review |
| LSWEEP `HYP-LSWEEP-XAU/EUR-M5-001` | session extreme sweep–reclaim | Không sweep; barrier level khác bản chất | Overlap timestamp |
| SDRIVE `HYP-SDRIVE-GBP/JPY-M5-001` | session open range breakout | Không dùng session open range; London window nhưng không ORB | Overlap timestamp |
| MZMS MACD/RSI/ADX | indicator oscillator | Không dùng các indicator này | Code review |
| ICT/FVG/OB/MSS/PO3/KLR | displacement+MSS+FVG+retest | Không dùng | Code review |

## Phụ lục 2 — Citation index (file:line đã đọc)

- `01. GOAL/GOAL.md:8-10,17-22,26-29,34-37,39-51,53,55-58`
- `05. Playbook/WORKFLOW.md:9-16,20-27,38-52,54-68,69-80,82-95,97-108,110-123,125-141,183-215`
- `04. Memory/research/20260813_T2_P3_ENGINEERING_CLOSEOUT.md:5,17-18,28-34,45-59,60-65,79-93`
- `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P1_SOURCE_MATRIX.md:19-25,32-46,48-63`
- `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P0_CHARTER.json:8,23-25,46-51,67-71,109-123,155-158,171,183-201,208-238`
- `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md:25-38,43-76,84-95,99-129,133-148,152-182,192-223,225-242,246-299,345-366`
- `04. Memory/research/PRO_TRADER_REPLACEMENT_CAMPAIGN.md:293-312,340-348,350-389,391-409`
- `04. Memory/do_not_repeat_failures.md:326,1737-1759,1912-1924,1513-1546`
- `04. Memory/research/20260726_REDTEAM_FULL_REPO_REVIEW.md:214-236`
- `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:72-84,16-18`
- `04. Memory/research/20260916_COST_PLANE_AUDIT.md:27-56`
- `04. Memory/research/20260918_DAY_BOUNDARY_MARKET_PHYSICS.md:66,75-79`
- `04. Memory/hot.md:63-66`
- `02. AlphaFactory/STRATEGY_LOG.md:5441-5444`
- Official Volman excerpts (lawful, author-hosted): UPA excerpt p.6,8-14,20-29;
  FPAS excerpt (structure ch.8-9 First/Second Break)
