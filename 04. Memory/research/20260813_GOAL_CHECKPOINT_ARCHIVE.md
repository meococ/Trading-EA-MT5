# ARCHIVE — GOAL checkpoints (frozen 2026-08-13)

Đây không phải GOAL sống. Luật đang sống: `01. GOAL/GOAL.md`.
File này giữ nhật ký checkpoint để tra cứu; không nạp vào always-on context.

---

# GOAL — Edge thực, kiểm chứng được (bản đầy đủ trước khi tách)

Trạng thái: **ACTIVE / UNMET** cho tới khi có ít nhất một symbol-sleeve đạt DONE. Một thử nghiệm thất bại, compile xanh hoặc workflow hoàn tất không phải DONE.

Một source frontier trả `NO_CANDIDATE` hoặc một mechanism bị KILL chỉ đóng phạm vi
đã kiểm tra; nó không tự chuyển toàn bộ GOAL sang `BLOCKED`. GOAL chỉ bị blocked
khi có blocker bên ngoài cụ thể ngăn mọi next action hợp lệ trong active scope.

## Owner scope lock — XAU/Forex only (2026-08-13)

- Active research, source discovery, hypothesis creation, MQL5 development,
  backtest, validation and promotion are limited to `XAUUSD`, `EURUSD`,
  `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD` and `NZDUSD`.
- `BTCUSD`, cryptocurrency data, hypotheses and EA sleeves are excluded from
  the active goal. Historical BTC artifacts remain audit history only and may
  not be revived, used as a candidate, or allowed to gate XAU/Forex progress.
- This scope lock overrides older book-universe wording below wherever it
  still includes BTC. Goal status remains `ACTIVE / UNMET` until at least one
  XAU/Forex sleeve is engineering-valid, economic-valid and promotion-ready.

## Owner goal reset — economic-first multi-horizon (2026-08-13)

- The deliverable is no longer required to be a scalper or to make every
  decision on M5/M15. The Lead may select `M5`, `M15`, `H1`, `H4` or `D1`
  before source/outcome access when that clock is justified by the causal
  mechanism, source publication frequency, sample adequacy and post-cost
  capacity.
- This reset overrides older normative M5/M15-only and H1-auto-reject language
  below. Historical M5/M15 checkpoint descriptions and terminal verdicts stay
  unchanged; changing timeframe does not revive a killed family or erase its
  trial debt.
- Positions may be held overnight only when the mechanism and swap/cost/risk
  contract are preregistered. No active sleeve may hold through the weekend.
- Slower official sources are admissible only with retainable point-in-time
  history, an equivalent live delivery contract, deterministic publication
  timing and a sign fixed before price outcomes. A slow clock is not permission
  to retime price-only breakout, trend or session families already closed.
- DONE thresholds for engineering validity, post-cost economics, sealed OOS,
  robustness, risk and Owner-only paper/live authority are unchanged.

## Outcome

Tạo ít nhất một chiến lược XAU/Forex trên khung thời gian được đóng băng theo cơ chế, có expectancy dương sau chi phí thật, cadence/mẫu đủ để ước lượng, ổn định ngoài mẫu và có thể vận hành an toàn trên MT5.

Deliverable là một EA hoàn chỉnh ở mức deployment-readiness. Agent không tự
nhận mình là quant hay tự cấp quyền dùng vốn thật; thay vào đó phải làm việc
theo chuẩn của một quant trader chuyên nghiệp: luận điểm thị trường rõ, dữ liệu
point-in-time phù hợp, giả thuyết falsifiable, cost/risk thực tế và verdict dựa
trên bằng chứng. Owner giữ quyền quyết định funded paper/live deployment.

Universe bắt buộc khi claim cấp book: XAUUSD, EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD và NZDUSD. Mỗi symbol được claim phải tự pass; không pooled kết quả để cứu symbol thua.

## Ngưỡng cốt lõi

| Tiêu chí | DONE tối thiểu |
|---|---|
| Profit factor | > 1.30 sau cost thật ở x1 |
| Cadence | Preregister theo mechanism; mỗi split phải đủ mẫu để ước lượng expectancy/DSR và không vượt capacity/cost, không có trần 5 lệnh/tuần mặc định |
| Cost stress | x1.5 PF ≥ 1.25; x2 PF ≥ 1.00 |
| History quality | MT5 Strategy Tester >97%; audit riêng coverage, clock, gaps, bid/ask và cost |
| Evidence window | 84 tháng / 14 nửa năm / 7 năm cho cấp confirmed khi lịch sử cho phép |
| Validation | Train và holdout tự pass độc lập; optimization-aware WFA, CPCV/PBO, DSR và Monte Carlo |
| Risk | Monte Carlo P95 drawdown nằm trong risk budget đã preregister |
| Exposure | Overnight chỉ theo contract đã preregister; tuyệt đối không giữ qua cuối tuần |

## DONE

Một symbol-sleeve chỉ DONE khi đồng thời:

- logic causal và implementation MQL5 là `engineering-valid`;
- expectancy sau cost, cadence và robustness là `economic-valid`;
- OOS/holdout, risk, execution, forensics và artifact đều `promotion-ready`;
- Owner quyết định riêng việc paper/live/deploy.

Chi tiết thực thi và stopping rules nằm duy nhất tại `05. Playbook/WORKFLOW.md`.

## Operating mandate của Owner (2026-08-09)

- Ưu tiên indicator có sẵn hoặc indicator chất lượng được nghiên cứu từ
  TradingView; phải hiểu cách indicator phản ánh hành vi chart trước khi biến
  thành logic EA. Không tạo thêm một indicator-vote EA chỉ để có code.
- Vòng lặp bắt buộc: research → prereg → backtest → kiểm định → phân tích →
  tinh chỉnh có giới hạn hoặc KILL exact hypothesis → independent sub-agent
  review → revision mới hay mechanism mới.
- PF thấp hoặc một hypothesis thất bại không được hủy GOAL. Failure phải được
  lưu artifact, giới hạn failure radius và chuyển thành thông tin cho vòng kế.
- Không sa đà setup: dùng AlphaFactory hiện hữu; chỉ sửa harness khi một gate
  bằng chứng bắt buộc fail-closed và không có đường chạy hợp lệ khác.
- Agent được toàn quyền chọn symbol, timeframe, indicator, logic, risk và thứ
  tự thử trong phạm vi vốn nghiên cứu; không được tự mở rộng sang funded live
  deployment hay làm yếu các ngưỡng DONE.

## Operating update của Owner (2026-08-11)

- Nguồn dữ liệu mặc định là MT5 demo/FivePercent hoặc server The5ers tương ứng
  với symbol được phát triển. Không mở lane mua dữ liệu chỉ để tìm ý tưởng; dữ
  liệu ngoài/trả phí chỉ được xem xét khi một cơ chế đã đóng băng thực sự cần
  trường dữ liệu mà MT5 không có và Owner cấp lại phạm vi chi tiêu rõ ràng.
- KPI điều hành là thời gian đến một baseline kinh tế chưa tối ưu, không phải số
  prereg, receipt, comparator hoặc engineering child. Dùng AlphaFactory hiện có
  và chỉ sửa harness khi đường chạy hợp lệ bị chặn bởi lỗi có bằng chứng.
- Main Agent tự gọi một sub-agent read-only sau khoảng 60 phút làm việc hữu ích
  hoặc sau một vòng nghiên cứu quan trọng để kiểm tra chệch hướng, setup detour,
  quyết định hậu nghiệm và lỗi lặp lại. Đây là review thủ công trong phiên làm
  việc, không phải scheduler và không phải gate dừng tiến độ.
- Đồng hồ review do Main Agent tự theo dõi theo thời gian làm việc thực tế;
  heartbeat/automation không được tính là đã review và không được thay việc gọi
  sub-agent ở checkpoint thật.
- Reviewer không sửa file, không chạy MT5, không đổi strategy và không tạo
  hypothesis. Main Agent tóm tắt nhận xét, áp dụng ít nhất một cải tiến cụ thể
  rồi tiếp tục vòng lặp đang làm.

## Goal lock — Deep Research đến EA có edge (2026-08-11)

- Goal không hoàn thành ở bước research, specification, compile, source gate hay
  một baseline có lãi. Chỉ EA có bằng chứng đồng thời `engineering-valid`,
  `economic-valid` và `promotion-ready` mới thỏa phần edge của goal.
- Trước khi đóng goal, cùng EA family phải có receipt backtest độc lập từ
  `2018-01-01` đến mốc dữ liệu mới nhất đã xác minh cho XAUUSD, EURUSD,
  USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD và NZDUSD. Mỗi sleeve có verdict riêng;
  không pool P&L để cứu symbol thua và không gọi symbol chưa đủ history là PASS.
- `Cùng EA family` được hiểu là một deployable portfolio host với shared
  execution/risk engine; không ép một signal rule phổ quát lên FX và XAU.
  Mỗi sleeve có thể dùng một information mechanism riêng, nhưng chỉ sleeve tự
  pass đầy đủ source/PIT, engineering, economics và promotion gates mới được
  kích hoạt. Kiến trúc multi-sleeve tự nó không phải edge và không cho phép pool
  P&L để che một sleeve thua.
- Drawdown theo giai đoạn được chấp nhận nếu cap đã preregister không bị vi phạm,
  expectancy sau cost vẫn dương và khả năng hồi phục được chứng minh bằng
  time-under-water, longest recovery và Monte Carlo thay vì chỉ nhìn net profit.
- Grok Deep Research là nguồn candidate/advisory. Main Agent phải audit nguồn,
  point-in-time semantics, data availability và de-dup theo information set +
  decision clock trước khi preregister. `NO_CANDIDATE` trung thực không được biến
  thành một EA ép buộc chỉ để giữ nhịp code.
- Khi candidate fail ở capability/source/economic gate, đóng đúng failure radius
  rồi bắt đầu vòng research mới với một information mechanism materially khác.
  Không neo vào tên indicator, triết lý campaign cũ hay subgroup vừa nhìn thấy.
- Timeframe là một phần của cơ chế và phải được đóng băng trước source/outcome;
  M5/M15, H1, H4 hoặc D1 đều hợp lệ khi publication clock, cost, sample size,
  turnover và capacity hỗ trợ. Không có cadence `2–5/tuần` mặc định. Các
  hypothesis cũ vẫn giữ nguyên verdict theo contract đã đóng băng; thay đổi này
  không được dùng để cứu hoặc chạy lại một object đã terminal.

## Checkpoint hiện tại — 2026-08-11

- Goal vẫn `ACTIVE / UNMET`; chưa có EA nào được promotion hoặc deploy.
- Baseline mới nhất `HYP-EIBB-XAUUSD-M15-001` đã đi thẳng source → MQL5 →
  compile/non-repaint → một Model-0 baseline. Source/runtime/report khớp đúng
  `1,287` events/trades, cadence `4.9337/week`, LONG/SHORT `664/623`, History
  Quality `99%` và DD `6.4196%`; engineering-valid.
- Economic verdict là KILL: PF sau spread/commission/swap chỉ `0.9189`,
  expectancy `-$3.3447/trade`, net `-$4,304.63`. Không dùng breakdown
  Wednesday/New York để cứu hậu nghiệm; validation/holdout vẫn khóa.
- Active lane kế tiếp phải đổi information mechanism, không đổi filter/session/
  stop/target của EIBB. Tiếp tục dùng native MT5 FivePercent/The5ers, ưu tiên
  source gate rẻ rồi một baseline chưa tối ưu; không mở lane mua data.
- Thử nghiệm `HYP-BWVR-BTCUSD-M5-002` bị vô hiệu hóa vì Main Agent hạ row-floor
  mà parent đã cấm rồi chạy source trước khi nhận verdict của reviewer đã được
  giao làm pre-source gate. Artifact được giữ để audit nhưng không được dùng
  làm source/economic evidence hay làm lý do mua data/chọn revision.
- Cải tiến bắt buộc: hourly/checkpoint reviewer vẫn là advisory và không làm
  dừng tiến độ; nhưng khi Main Agent đã giao reviewer một quyết định cụ thể
  trước irreversible attempt thì phải nhận verdict trước khi mở source/MT5.
  Trong thời gian chờ chỉ được làm công việc reversible như de-dup, code và test.
- Lane kế tiếp `HYP-FLI-EURUSD-M15-001` đã chứng minh quy trình sửa có tác dụng:
  reviewer chặn ba lỗi trước source, rồi sole attempt hoàn tất sạch. Exact
  Follow Line mặc định có `4,015` events, `11.0043/week`, ổn định
  `10.1625–11.9153/week` theo năm nên bị PARK trước MQL/economics. Không chỉnh
  tham số/cooldown/session để ép cadence; tiếp tục một information mechanism mới.
- `HYP-WTX-EURUSD-H1-001` được reviewer chặn trước source: đó vẫn là family
  single-oscillator extreme transition và còn lệch deliverable vì H1-only. Không
  có attempt/data/outcome nào được mở. Cải tiến áp dụng ngay là kiểm tra
  information-family de-dup + M5/M15 goal-fit trước khi viết analyzer.
- Prior-day volume-profile lane đã đi trọn source → MQL5 → baseline mà không
  mua data. HYP001 float-boundary PASS bị vô hiệu; HYP002 integer-point sửa đúng
  correctness, source/runtime khớp tuyệt đối `945` signals (`457/488`), compile
  `0E/0W`, non-repaint PASS và DQ `100%`.
- Sole baseline `20260811_164213` bị KILL kinh tế: `456` trades, PF sau report
  costs `0.71385`, expectancy `-$17.44/trade`, net `-$7,952.85`, executed
  cadence `1.2498/week`; native equity DD `$8,014.98` ≈ `8.01498%` cũng vượt
  nhẹ cap `8%`. Enhanced-summary DD `7.8564%` không thay thế native equity-DD
  gate. Không bỏ drawdown lock hay dùng breakdown giờ/thứ để cứu;
  validation/holdout vẫn khóa.
- Active lane kế tiếp phải đổi information mechanism, vẫn dùng MT5 demo/
  FivePercent/The5ers và phục vụ trực tiếp M5/M15. Ưu tiên một source gate ngắn
  rồi direct MQL5/baseline; không quay lại oscillator extreme, initial-balance,
  volume-profile, cross-asset residual hay các family đã terminal.
- Mass Index reversal-bulge được falsify ngay ở source gate, không qua MQL:
  `1,850` executable events (`944/906`), exact-next `99.946%`, nhưng cadence
  `5.06453/week` vượt trần và feature coverage chỉ `95.299%`. Exact 9/9/25,
  `>27 → <26.5` mapping bị PARK; không thêm cooldown/session hay đổi threshold.
  Row floor 190k là lỗi prereg không calendar-derived và sẽ không lặp lại.
- Independent review còn phát hiện MIRB trùng event-timing với package cũ
  `HYP-MASS-EURUSD-M15-001` (5.07346/week). Đây là de-dup miss của Main Agent.
  Cải tiến bắt buộc: trước lane kế tiếp phải search full EA tree theo alias,
  constants/formula và timing signature, đồng thời capacity-check metadata-only.
- Next active work is a pre-hypothesis capability/de-dup check for the built-in
  MT5 Economic Calendar: historical high-impact EUR/USD release timestamps plus
  frozen forecast/actual values, exported from the existing demo terminal and
  replayable as a static tester resource. It uses no paid data. A strategy ID is
  opened only if point-in-time semantics, 2016–2022 coverage and raw event
  cadence are all defensible; otherwise this lane stops before price outcomes.

## Deep Research checkpoint - 2026-08-11 (current)

- The Economic Calendar capability check stopped before hypothesis because the
  reviewed MetaQuotes contract does not prove an immutable historical
  release-time forecast/revision tape suitable for a 2018-latest PIT claim.
- Ten source-first Grok passes and local audits have produced no lawful active
  candidate. Server-midnight gap claims were retracted; dealer/temporary-impact,
  month-end equity hedging, Bid/Ask liquidity-shock decay and asymmetric
  best-quote withdrawal all failed their exact source/data/clock contract.
- Checkpoint 8 resolves the architecture as `MULTI_SLEEVE_REQUIRED`: one EA host
  may contain independent evidence-backed sleeves behind one risk engine, while
  a fake universal transfer is forbidden. FX, XAU and BTC all returned
  `REJECT_PRE_HYPOTHESIS_CAPABILITY`, so this clarification authorizes no code.
- A local historical-run opportunity audit also returned
  `NO_REVIVAL_CANDIDATE`: Cobra is source/PIT/trial-contaminated and its equity
  audit failed; LondonNY is a sparse USDJPY sleeve with 112 trades, a 674-day
  flat period, 16.1% weekend exits and failed cross-pair transfer.
- A fresh BitMEX realized-funding lane proved that free XBTUSD funding rows are
  available from 2018-latest, but was rejected before hypothesis: available
  funding/arbitrage studies do not establish a one-leg MT5 BTCUSD CFD direction
  surviving after the closed settlement bar and costs. The exact failure is
  evidence/venue translation, not source availability.
- A stablecoin mint/burn BTC lane was also rejected before hypothesis. Block
  timestamps exist, but cross-chain mint/treasury/release/migration identity is
  not a clean PIT liquidity shock and the literature conflicts; only one found
  source claims a 5-30 minute response, without the required independent exact
  replication after a closed M5/M15 bar and costs.
- Registry-lineage audit found no abandoned survivor: visible source-pass parent
  rows all lead to a terminal design/economic child or data-only object. Parent
  state must not be mistaken for an active candidate.
- No EA/indicator, analyzer, source-price scan or MT5 baseline is authorized from
  these passes. This protects the goal from a fabricated baseline; it does not
  mark the goal complete or blocked.
- The active loop returns to discovery with a materially new information object.
  Every candidate now needs a pre-hypothesis source-contract receipt before any
  numerical claim or MQL5 work. Detailed checkpoint:
  `04. Memory/research/20260811_GROK_DEEP_RESEARCH_LOOP_REVIEW.md`.

## Checkpoint 2026-08-12 — Event Aggressor Flow

- `HYP-EVENT-AGGFLOW-EURUSD-TICK-013` reached a complete engineering-valid
  DESIGN baseline after HYP012 passed source qualification. PRIMARY produced
  325 trades, base PF `1.7257`, x1.5 PF `1.5126`, x2 PF `1.3265`, both years
  positive and DD `0.96%`; exact sign-REVERSE produced PF `0.3471`.
- The mapping is nevertheless terminal: top 5% profit concentration was
  `32.4011%` versus the frozen `30%` maximum. Validation 2021-2022 remains
  sealed; no result-driven filter, timing, sizing, SL/TP or rerun is allowed.
- It also cannot satisfy DONE because its decision/management clock is
  tick-level `+15s → +75s`, not closed M5/M15. Independent review and Grok both
  returned `NO_SUCCESSOR` for retiming the same first-wave flow source.
- The next active work is an outcome-blind source-capability/de-dup check of
  official Binance BTCUSDT closed-M5 taker-buy volume archives as a genuinely
  new exchange trade-side information set. No BTC price outcome, hypothesis,
  MQL5 or MT5 run is authorized until free 2018-latest coverage, archive
  revision semantics, live/PIT equivalence and target BTCUSD venue translation
  are all defensible.
- That Binance capability check is now terminal before hypothesis as
  `NO_CANDIDATE_TARGET_HISTORY_GATE_FAIL`. The official source itself passed
  the basic availability/integrity surface: 103 consecutive monthly
  ZIP+CHECKSUM pairs from 2018-01 through 2026-07, valid boundary checksums,
  closed-M5 `v/V/n/x` semantics and documented archive-revision handling.
- The fatal blocker is the execution target. Native FivePercent BTCUSD M5 has
  only 7.46% / 23.63% / 23.67% / 59.75% of theoretical 24x7 bars in
  2018/2019/2020/2021, with every adjacent observed bar gapped in 2018-2020.
  It cannot support the mandatory independent 2018-latest receipt and a
  counts-only source run cannot repair missing target bars.
- No BTC outcome, threshold, hypothesis, EA, MQL5 or MT5 run was opened. This
  does not economically kill Binance taker flow; it closes only the mapping to
  the current incomplete FivePercent BTCUSD target. Detailed readout:
  `04. Memory/research/20260812_BINANCE_BTCUSDT_M5_SOURCE_CAPABILITY_READOUT.md`.
- The active loop returns to database-first discovery on symbols whose native
  M5/M15 target history can already satisfy the 2018-latest contract. Source
  capability and information-family de-dup remain mandatory before a new ID.
- The database-first reuse pass is now closed as `NO_REVIVAL_CANDIDATE`.
  `EA_VolCluster/20260621_192253` has no surviving MQL5 source, no real
  commission/slippage contract, comes from a 58-run/22-EA selection campaign,
  and its latest WFA OOS window fell to PF `0.78`. `EA_ShanghaiFixScalp` also
  has no surviving source or real-cost telemetry and passed only one of five
  OOS windows. Apparent open Round Cascade/JCDR source parents both lead to
  terminal economic children. No old PF row is authorized for rebuild,
  validation or promotion. Detailed readout:
  `04. Memory/research/20260812_RUN_CATALOG_NEAR_SURVIVOR_AUDIT.md`.
- Native target history is not the general frontier blocker. A timestamp-only
  audit found 2018-07/2026 M5 coverage of 639,404 EURUSD, 639,434 USDJPY,
  639,318 GBPUSD and 604,078 XAUUSD rows, all strictly increasing with zero
  duplicates; exact aligned M15 construction is 99.27%-99.73% complete.
- Same-symbol cross-provider discovery was de-duplicated and screened without
  opening prices. MetaQuotes-Demo fails firm-venue/PIT provenance. Dukascopy
  free DEMO fails train/serve identity because its historical data come from
  LIVE while realtime DEMO ticks are generated separately.
- The provisional TrueFX access request is retracted. Its current contact page
  limits Market Data to financial institutions, while live streams are priced
  at USD 4,950/month and USD 7,450/month. Free historical downloads do not
  provide an identical accessible live source for an individual MT5 sleeve.
  Current verdict is
  `NO_CANDIDATE_TRUEFX_INSTITUTION_ONLY_PAID_LIVE_AND_TRAIN_SERVE_IDENTITY_FAIL`;
  no registration, terms acceptance, download, hypothesis, EA or MT5 run is
  authorized. Detailed readout:
  `04. Memory/research/20260812_NATIVE_TARGET_AND_TRUEFX_SOURCE_FRONTIER.md`.
- Grok Build's `SonicR_MT5_QUALITY_v10.zip` was downloaded and reviewed as
  external source but not executed. It is H1/free-yfinance rather than the
  required closed M5/M15 2018-latest contract, omits the pipeline files needed
  to reproduce its WFA claims, and contains source-critical array, unfinished
  HTF/fail-open, account-deal binding and position-ticket defects. Verdict:
  `NOT_A_CANDIDATE_ENGINEERING_DONOR_ONLY`; no install, compile or backtest is
  authorized. Detailed audit:
  `04. Memory/research/20260812_GROK_SONICR_V10_LOCAL_AUDIT.md`.
- A metadata-only inventory of the native FivePercent Real tick store found a
  complete 103/103 monthly-file surface from 2018-01 through 2026-07 for
  EURUSD, GBPUSD and USDJPY, with no missing, zero-byte or sub-1-MiB file.
  No tick payload, price, return or outcome was read. Verdict:
  `SOURCE_CAPABILITY_PASS_METADATA_ONLY`. The active loop now de-duplicates a
  genuinely new tick-microstructure information family, then freezes a
  counts-only qualification contract before any hypothesis or price read.
  Detailed receipt:
  `04. Memory/research/20260812_NATIVE_REAL_TICK_CAPABILITY_INVENTORY.md`.
- `HYP-QPF-EURUSD-M1-002 / 20260812_202440` is terminal as
  `ENGINEERING_INVALID_CACHED_INPUT_NO_SOURCE_ATTEMPT`. AlphaFactory compiled
  cleanly, but its empty `[TesterInputs]` section allowed MT5 to load cached
  HYP001 input; the EA failed closed in `OnInit` with zero emitted buckets and
  zero orders. No tick payload, source metric, outcome or economics was read.
- The active source object is the fresh one-shot engineering reissue
  `HYP-QPF-EURUSD-M1-003`. It preserves the exact HYP002 observable set,
  EURUSD M1 source, completed-M5 buckets, `[2018-01-01,2026-08-01)` window and
  simultaneous source gates. Its only permitted delta is explicit tester
  binding for collection-only, hypothesis ID, symbol, period and bucket width.
  A failed valid source gate kills this exact object; only PASS may authorize a
  separately preregistered closed-M5/M15 child. No outcomes or economics are
  authorized in the source run.
- `HYP-QPF-EURUSD-M1-003 / 20260812_204240` is now terminal as
  `ENGINEERING_INVALID_MISSING_D0_PROOF_NO_SOURCE_VERDICT`. The exact explicit
  inputs worked and MT5 processed 207,698,274 ticks into 639,403 completed M5
  buckets at 99% History Quality with zero trades, but the source omitted the
  mandatory D0 series proof. AlphaFactory therefore stopped before binding the
  copied CSV into the completed manifest. Diagnostic-only results show the
  frozen one-sided-update gate far below 5% in every year, but this is not an
  official source verdict and the threshold may not be changed.
- The active one-shot `HYP-QPF-EURUSD-M1-004` may change only identity plus the
  fail-closed D0 series proof. Observable set, data, window, thresholds,
  denominator and explicit input bindings remain frozen. One valid run must
  return the official PASS/KILL source verdict; no same-ID rerun or rescue is
  allowed.
- `HYP-QPF-EURUSD-M1-004 / 20260812_205728` completed as an
  engineering-valid source run and returned the official verdict
  `KILL_QUOTE_PATH_FIDELITY_EXACT_EURUSD_METATICKS`. MT5 processed 207,698,274
  ticks into 639,403 completed M5 buckets at 99% History Quality, with a valid
  D0 proof, one manifest-bound CSV and zero trades. The frozen one-sided
  Bid/Ask update share was only 0.1921% pooled versus the 5% minimum, and every
  year 2018-2026 failed the same gate. All other source-quality gates passed.
- No threshold, denominator, year, symbol or Sonic filter rescue is allowed,
  and no economic child is authorized. The active loop returns to database-
  first de-dup of a materially distinct information family. Detailed readout:
  `04. Memory/research/20260812_QPF_HYP004_SOURCE_VERDICT.md`.
- The database-first pass and the same Grok Build session now agree on
  `NO_CANDIDATE_LOCAL_FRONTIER` for the existing OHLC/spread/tick-volume/
  Bid-Ask metatick information set. Historical catalog rows with attractive PF
  are not survivors: their source is missing/contaminated or their terminal
  OOS/cost child already failed. No new ID is minted from those rows.
- A read-only live capability check found that FivePercent currently broadcasts
  non-empty DOM-shaped books for EURUSD, GBPUSD, USDJPY, XAUUSD and BTCUSD
  (`SYMBOL_TICKS_BOOKDEPTH=16`). This does not open a candidate: MetaQuotes
  documents that DOM history is not stored and is unavailable in Strategy
  Tester, while the OTC book provenance is not proven firm L2. Verdict:
  `PASS_PROSPECTIVE_COLLECTION_ONLY_NO_CANDIDATE`; no EA/economics and no
  retrospective 2018-latest claim. Detailed receipt:
  `04. Memory/research/20260812_FIVEPERCENT_LIVE_DOM_CAPABILITY.md`.
- Counts-only inspection of the remaining native tick fields closed the local
  aggressor-tape possibility. On a current full UTC day, EURUSD, GBPUSD,
  USDJPY, XAUUSD and BTCUSD all had zero nonzero `last`, `volume`,
  `volume_real` and zero LAST/VOLUME/BUY/SELL flags; sampled EURUSD days in
  2018/2020/2022/2024 showed the same absence. The current local stream is
  quote-only for this purpose. Combined with terminal QPF, DOM-history absence
  and the already killed confirmatory HYP-EURFXMOM-005, the bounded verdict is
  `NO_CANDIDATE_LOCAL_FRONTIER`. The goal remains active but no new local ID,
  EA or economic run is authorized. Detailed receipt:
  `04. Memory/research/20260812_NATIVE_TICK_RAW_FIELD_FRONTIER.md`.
- `HYP-CME6E-OPT-PIN-EURUSD-M15-002` is terminal as
  `KILL_SOURCE_DESIGN_MONOTONIC_PARTIAL`. Its sole authorized normalized-OI
  acquisition stopped abruptly at `291/516` hash-bound payloads and may not be
  retried or resumed. The fail-only audit found `0/291` strict source-valid
  events and `291/291` events with unknown OI, already exceeding the frozen
  maximum of `25` invalid events for the `95%` gate. Even a perfect remaining
  `225` events could reach only `225` valid versus `491` required. No
  futures-reference price, outcome, economics, MQL5 or MT5 run was opened.
  The exact option-pin mapping may not be rescued through zero-fill, filters or
  timing changes. Detailed receipt:
  `04. Memory/research/20260812_CME6E_OPTION_PIN_HYP002_TERMINAL_SOURCE_VERDICT.md`.
- Grok Build independently confirmed the monotonic arithmetic and terminal
  source kill, then returned `NO_CANDIDATE` for the remaining zero-cost local
  source surface. Local artifacts remain authority. The goal stays active, but
  no new ID, EA or economic run is authorized until database-first discovery
  identifies a materially different source-capable information object.
- A fresh classic Dragon/Trend/PVA draft was rejected before hypothesis as
  `REJECT_PRE_SOURCE_DEDUP_FAIL`: it re-entered the already tested Sonic R
  geometry family and used broker quote-count `tick_volume`, not a new causal
  information source. No source scan, outcome, EA or MT5 run was opened.
- The archived USDJPY M15 `EA_ITSM` near-survivor was then audited directly
  from source snapshots, Model-0 reports and trade ledgers. Historical code is
  closed-bar and compiled cleanly, but the independent 2021-2025 baseline,
  strict-NY and strict-London mappings returned PF `1.1567`, `1.2210` and
  `1.1179`; London cadence is only `1.85/week`, and all have zero commission
  plus zero tester slippage.
- The selected T10/skip-H17 child reports PF `1.5778` but only `0.87/week`
  after a documented 14-run filter sweep. Its actual WFA has only `3/5`
  profitable OOS windows, 2024 PF is `1.0579`, top-5% trades contribute
  `70.1%` of profit, the longest flat is `495` days, and the cost proxy is not
  broker/data identity-bound. Verdict is `KILL_NO_REVIVAL`; Grok independently
  agreed. Detailed audit:
  `04. Memory/research/20260812_ITSM_SONIC_USDJPY_REVIVAL_AUDIT.md`.
- Git is explicitly outside the active goal path by Owner instruction. Git
  state, commit or push work must not gate research progress. The goal remains
  active at `NO_CANDIDATE_LOCAL_FRONTIER`; only a materially new, source-
  capable information object may open the next hypothesis.
- The post-ITSM frontier pass rejected three additional drafts before source
  purchase or outcome access. Combined CME 6E MBP-1 trades+BBO cannot choose
  continuation versus absorption from aggregate L1 without an outcome-selected
  direction; a USD-event ZT shock is non-unique cross-asset price momentum; and
  6E option contract flow lacks customer/dealer, open/close and delta identity.
  Grok returned `NO_CANDIDATE` on all three and Lead agreed. No hypothesis ID,
  data call, MQL5 or MT5 run was opened.
- The remaining relative-rate two-leg idea is not open on the zero-cost
  2019-2020 surface: CME EUR short-rate futures began only on 2022-10-31, ICE
  Euribor intraday data are commercial, and Eurex intraday files are fee-based.
  Do not replace the missing EUR leg with one-leg ZT or daily settlement.
- The runs catalog's apparent `EA_MultiAssetTSMOMD1V6/20260812_113422` PF near
  1.40 is not a survivor. Its authoritative failure artifact records native PF
  `0.4853467684`, net `-$7,708.23`, `0/4` positive years and a failed
  transition. Detailed checkpoint:
  `04. Memory/research/20260812_SONICR_POST_ITSM_FRONTIER_CLOSEOUT.md`.
- The previously discussed `USD 17.00` ceiling was an unsubmitted Databento
  estimate for CME 6E option definition/statistics data, not the relative-rate
  two-leg source. It is not an active authorization and must not be revived
  after the terminal normalized-OI source failure.
- A narrower closed-M5 TBBO absorption proxy also failed pre-hypothesis review:
  aggregate best-price size increases cannot be attributed to the executed
  queue without MBO/order identity; the sign remains fade-versus-continuation;
  and the five-to-fifteen-minute clock is not a queue-lifetime mechanism. Grok
  and Lead returned `NO_CANDIDATE`; no ID, counts run, outcome or code was
  opened.
- The final bounded Build-mode frontier pass also returned `NO_CANDIDATE`
  without code, spend or outcome access. An official-clock residual lacks two
  exact sources for a deterministic direction after the first closed M5 and
  into the next 5-30 minutes; CFTC COT/TFF is weekly; and post-print ZT/6E/ES
  mids are already-closed cross-asset momentum with a non-unique rates versus
  risk-off sign. No hypothesis, backtest or EA is authorized from this pass.
- `HYP-GC-OFI-INNOV-XAU-M5-003` then reached a terminal source-only verdict:
  `KILL_SOURCE_INTEGRITY_HYP003`. Its exact Q1-2019 GC readout found `49,989`
  duplicate event keys, `5,323` fatal-quality records, A/B aggressor volume
  share `0.9860960694566356` below the frozen `0.99` floor, and `12`
  conflicting definition records. No candidate predicate, XAUUSD outcome,
  economics, MQL5 or MT5 run was opened; the exact source contract cannot be
  rescued by dropping records or lowering thresholds.
- Five fresh post-GC research objects were closed before source spend or target
  access: completed-M5 6E/spot basis catch-up, 6E MBO order-ID queue behavior,
  the general adversarial XAU/FX frontier, common-USD flow across seven CME FX
  futures, and EIA WPSR CL aggressor flow into USDCAD. Their respective
  verdicts are `KILL_6E_SPOT_BASIS_FRONTIER`,
  `KILL_6E_MBO_ORDER_ID_FRONTIER`, `NO_CANDIDATE_XAU_FX_FRONTIER`,
  `KILL_COMMON_USD_FUTURES_FLOW_FRONTIER`, and
  `KILL_CL_FLOW_USDCAD_FRONTIER`. The goal remains active and unmet; no EA or
  economic run is authorized by these verdicts. Detailed receipt:
  `04. Memory/research/20260813_POST_GC_XAU_FX_FRONTIER_CLOSEOUT.md`.
- A sixth post-GC object, continuous non-event 6E signed-volume innovation
  normalized by prior same-UTC-slot flow, is also terminal as
  `KILL_CONTINUOUS_6E_FLOW_FRONTIER`. The source may be technically feasible,
  but no primary evidence supports continuation from a completed M5 bar into
  the following 15-minute EURUSD window after retail cost. Changing the
  normalization, neutral gap or z-threshold would be a parameter rescue, not a
  new causal mechanism; no source quote, purchase, outcome or code was opened.
- Public CME 6E block disclosure and a true on-book multi-level sweep-fade were
  separately reviewed and killed pre-source. Block reports have no initiator
  polarity, while sweep resiliency evidence is sub-M5 and trades-only cannot
  reconstruct uninterrupted depth consumption. Verdicts are
  `KILL_6E_BLOCK_FRONTIER` and `KILL_6E_SWEEP_REVERSAL_FRONTIER`; source spend
  and target outcomes remain zero.
- EBS Spot EURUSD primary-CLOB flow is closed as `KILL_EBS_SPOT_FRONTIER` under
  the current capital contract: research-grade historical/live-identical EBS
  Price/Deal tape requires commercial licensing and has no verifiable one-shot
  source pilot strictly below USD 10. A latest-row registry audit also found no
  unconsumed sub-USD-10 XAU/FX cell: the visible GC HYP002 and EURFXOFI
  001/004/005 rows are superseded by terminal child campaigns. No purchase was
  made.
- A tenth fresh `/deep-research-trading-meta5` residual-source pass returned
  `NO_CANDIDATE_XAU_FX_FRONTIER_V2`. Local primary-source audit confirmed the
  terminal boundary without accepting Grok's unsupported COMEX-history claim:
  COMEX stocks still lack a fixed primary-evidence 5-30 minute XAU sign, LBMA
  clearing is monthly, FX Link de-dups to spot/futures basis, and New York Fed
  primary-dealer statistics are prior-week aggregates. No ID, spend, target
  outcome, economics, MQL5 or MT5 run was opened. Receipt:
  `04. Memory/research/20260813_GROK_XAU_FX_FRONTIER_V2.md`.

## Active goal reset and source lane - 2026-08-13

- Owner reset the active mandate to autonomous XAU/Forex EA discovery and
  development. Grok Build is a bounded implementation/review worker; Main Agent
  owns decisions and local artifact verification. BTC, unapproved spend and Git
  work are outside the active research path and cannot gate progress.
- The goal remains `ACTIVE / UNMET`. A failed hypothesis or source lane closes
  only its exact failure radius; it does not stop discovery of a materially new
  information mechanism. No EA is currently economic-valid or promotion-ready.
- The native Economic Calendar historical export is not a reconstructable PIT
  tape. `CalendarValueLast`, currency-filtered `CalendarValueLast`, and
  `CalendarValueLastByEvent` all prime successfully but their post-prime delta
  request times out with `5401` on the actual FivePercent server. The per-event
  v1.4.1 run discovered and primed 1,051/1,051 definitions, then failed two
  post-prime calls with zero VALUE/idle proof. Exact verdict:
  `KILL_RUNTIME_CALENDAR_LAST_UNAVAILABLE_ON_SERVER`.
- A restart corruption in v1.4.0 was fixed and independently exercised in
  v1.4.1 (`events_loaded=1051`, no zero IDs), but correctness does not rescue the
  unavailable server delta path. Receipt:
  `03. EA Developer/EA_ProspectiveCalendarPIT/research/PROSPECTIVE_COLLECTION_DEPLOYMENT_RECEIPT.md`.
- The sole Calendar successor, v1.5.0 prospective future-occurrence History
  watcher, is terminal. It compiled with 0 errors/0 warnings and froze 506
  moderate/high events from 1,051 definitions, but its first two bounded
  `CalendarValueHistoryByEvent` calls returned `5401`. There were zero future
  occurrences, idle proofs, observations or mutations; auditor v4 failed.
  Verdict: `KILL_CALENDAR_LANE`. No further Calendar API revision is authorized.
- The overall goal remains `ACTIVE / UNMET`. The next admissible step is a
  database-first, materially different XAU/Forex information object. No
  hypothesis ID, EA, backtest or economic claim opens until that source object
  passes causal-sign, local-availability and de-dup gates.
- A lineage-aware database audit found 107 canonical MQ5 packages and 499
  indexed AlphaFactory run rows. The 16 packages without a same-name physical
  run are four non-strategy/source probes, five already-terminal exact strategy
  objects, and seven superseded engineering identities. Verdict:
  `NO_REVIVAL_CANDIDATE_FROM_UNRUN_SHELF`; receipt:
  `04. Memory/research/20260813_UNRUN_EA_SHELF_DATABASE_AUDIT.md`.
- Lead opened the zero-cost prospective DOM database lane for XAUUSD, EURUSD,
  GBPUSD and USDJPY. This is source collection only: no trade API, outcome,
  causal sign or edge claim. A bounded smoke must prove four subscriptions,
  nonempty books, monotonic receipts and durable readable output before passive
  accumulation may continue. Frozen contract:
  `03. EA Developer/EA_ProspectiveDOMTape/research/DOM_COLLECTION_PREREG.md`.
- DOM collector v1.0 was stopped as an engineering failure after five I/O
  errors, missing startup receipts, reused sequence IDs and JSON/CSV mismatch.
  A separately frozen v1.1 contract produced implementation v1.1.1: 10 static
  tests, AlphaFactory compile `0 errors/0 warnings`, two stopped live sessions,
  and a real restart that jumped snapshot/event high-water floors from 2,716 to
  10,001 without reuse.
- The final source auditor passed 5,172 JSON snapshots against 70,579 CSV level
  rows across all four symbols with zero empty/API/I/O/tick failures. This is
  `SOURCE_CAPABILITY_PASS`, not an edge.
- The outcome-blind payload audit then closed the exact source as
  `KILL_FIVEPERCENT_DOM_LADDER__NO_HYPOTHESIS_AUTHORITY`: 99.977330% of all
  displayed levels carried the same 100,000,000 volume, the outer ladder was
  fixed/symmetric, and the only remaining features reduce to quote geometry,
  finite level count or update intensity. Grok Build independently agreed.
  No hypothesis ID, target outcome, EA backtest or continuous collector was
  opened. Detailed verdict:
  `03. EA Developer/EA_ProspectiveDOMTape/research/DOM_SOURCE_CAPABILITY_AND_QUALITY_VERDICT.md`.
- Goal remains `ACTIVE / UNMET`. This failure radius is only the current
  FivePercent DOM ladder on XAUUSD/EURUSD/GBPUSD/USDJPY and its volume/OFI,
  level-count, spacing, shape and update-rate mappings; it is not a verdict on
  a materially different executable venue with real variable depth.
- Process correction: this attempt repeated the existing `FivePercent
  live-DOM size-identity guard` in `04. Memory/do_not_repeat_failures.md`, which
  had already found constant 100,000,000 sizes across eight symbols and
  explicitly prohibited building a collector from `MarketBookAdd` success
  alone. Run-catalog de-dup was insufficient. Every next prospective source
  must de-dup source API + venue + payload fields + intended mechanism against
  the failure catalog before preregistration or code.
- The immediate post-DOM bounded frontier pass returned
  `NO_CANDIDATE_LOCAL_ZERO_COST_FRONTIER`. The first unmet gate is source
  identity: no already-local zero-cost XAU/major-FX payload both supports a
  defensible 2018-latest historical/live contract and supplies a materially new
  signed closed-M5/M15 object outside the failure catalog. Grok Build returned
  the same scoped verdict without code, outcome access or spend. Receipt:
  `04. Memory/research/20260813_POST_DOM_LOCAL_ZERO_COST_FRONTIER.md`.
- The next bounded expansion rejected CPI/BLS/NFP before probing because it is
  a rebrand of the already-sealed principal-statistics/macro-surprise family.
  Grok Build then searched only external zero-cost official-primary sources and
  returned `NO_CANDIDATE_FREE_OFFICIAL_EXTERNAL_FRONTIER`: after all frozen
  families are removed, no inspected payload has a pre-declared signed impulse
  expected to survive to the first or second closed M5/M15 bar after retail
  costs. No source was downloaded and no spend, ID, code or outcome was opened.
- A fresh lineage check also found no lawful multi-sleeve rescue. The visible
  database partial passes retain their exact source/cost/OOS/transfer verdicts;
  `EA_EventAggressorFlow` is terminal/sub-M5 and the visible XAU compression
  break baseline has only 28 trades. Multi-sleeve remains architecture only and
  cannot pool P&L or revive a terminal family. Receipt:
  `04. Memory/research/20260813_FREE_OFFICIAL_EXTERNAL_AND_LINEAGE_FRONTIER.md`.
- The unfinished T2 VolmanCausalGrammar P3 lane was resumed only as an
  outcome-blind engineering blocker. A stage probe localized the prior timeout
  to O(n^2) ECRS rolling-array recomputation. The frozen mirror stayed
  unchanged; a cache-only successor passed old-vs-new trace/event parity and
  reduced the full cached ECRS path to minute scale.
- The sole separately locked full replay then failed closed at
  `pbp_identity_projection_full`: frozen `_ensure_unique` found 11 duplicate
  normalized PBP identities (10 BREAK_WINDOW, 1 TOMBSTONE_CONTACT). No packet
  was retained and no identity counts, Jaccard, D7/D8 verdict, economics or EA
  authority was exposed. Verdict:
  `TERMINAL_T2_P3_DUPLICATE_IDENTITY_POPULATION`.
- First/last selection, adding barrier provenance to the comparison key or
  deduplicating would change the frozen identity population. No second replay
  or key/count rescue is authorized. Detailed receipt:
  `04. Memory/research/20260813_T2_P3_ENGINEERING_CLOSEOUT.md`.
- Goal remains `ACTIVE / UNMET`, with no active market mechanism. The next
  admissible work must begin from a materially new source object or genuinely
  independent cure evidence. It must not relabel a closed zero-cost source,
  revive a terminal run from headline PF or turn this engineering receipt into
  an edge claim.
- The bounded post-T2 source pass then returned
  `NO_CANDIDATE_POST_T2_ZERO_COST_FRONTIER`. AlphaFactory/local manifests expose
  only the already-consumed FivePercent OHLC/spread/tick-volume, ForexFactory
  calendar, Kalshi macro and bound CME 6E classes; all five custom indicators,
  Sonic and their fusion/state families are closed. Grok Build independently
  reached the same scoped verdict. No hypothesis, code, MT5 run, outcome or
  spend opened. The first unmet gate is a zero-cost source with sealed 2018-now
  PIT history, matching live identity and a new inherently signed discrete
  2-5/week field. Receipt:
  `04. Memory/research/20260813_POST_T2_ZERO_COST_FRONTIER.md`.
- The follow-on local independent-cure audit returned
  `NO_REOPENABLE_ENGINEERING_BOUNDARY`. The 149 mechanically filtered
  leaf/pre-economic rows contained stale, superseded, capability-only or closed
  objects; every plausible implementation stop either has an economic successor
  or fails a frozen source/identity boundary. In particular, VRAS USDJPY HYP003
  already consumed Model 0 and was killed at PF 0.0 and 0.0115 trades/week; its
  lifecycle telemetry defect cannot rescue that verdict. Grok's matching answer
  was advisory because its sandbox lacked the local artifacts. No code, MT5 run,
  outcome or spend opened. Goal remains `ACTIVE / UNMET`; receipt:
  `04. Memory/research/20260813_ENGINEERING_BOUNDARY_REOPEN_AUDIT.md`.
- Cadence-governance reconciliation: the post-T2 `2-5/week` source receipt is
  scoped to its frozen search contract. Per the 2026-08-11 Owner update, a new
  mechanism has no default 2-5/week cap; it must preregister a defensible range
  from sample size, cost, turnover and capacity. This correction does not revive
  any old ID or manufacture a new information set. A bounded Grok mechanism
  rechallenge confirmed that removing the cap alone leaves the currently
  available OHLC/spread/tick-volume/Bid-Ask field frontier unchanged; no code,
  run, outcome or spend opened.

## Checkpoint 2026-08-13 — Ehlers Hilbert phase source clock

- `HYP-EHPR-EURUSD-M15-001` was stopped before source access because its
  analyzer filtered a UTC window through broker-server `source_epoch`.
  Engineering child `HYP-EHPR-EURUSD-M15-002` changed only the predicate to
  normalized `time_utc`; nine focused tests passed.
- The sole outcome-blind HYP002 source attempt passed all nine gates: 148,746
  complete derived M15 bars (99.8463% coverage), 120,991/124,011 usable DESIGN
  bars, 21,618 executable events, 82.9638 events/week, LONG/SHORT 10,809/10,809,
  exact-next 99.7140% and maximum year share 20.7235%. Post-event OHLC, returns,
  trades, PnL, MT5, validation and holdout counters remained zero.
- The exact HYP002 ID is terminal before MQL5 because it froze a 2–5 completed-
  trades/week contract. That interval was imposed by stale registry schema,
  contrary to this GOAL's mechanism-specific cadence rule. It is an
  administrative contract failure, not an economic or causal verdict on
  Hilbert phase; the same event definition may not be reopened merely to pick a
  new cadence after seeing counts.
- The schema is corrected prospectively to accept any strictly positive frozen
  cadence range while retaining `min <= max`; three focused tests pass. This
  does not revive HYP002 or authorize a build.
- Goal remains `ACTIVE / UNMET`; no mechanism is active. The next candidate
  must be materially fresh and freeze its own cadence from sample size, cost,
  turnover and capacity before source counts. Canonical correction:
  `04. Memory/research/20260813_EHPR_CADENCE_GOVERNANCE_CORRECTION.md`.

## Checkpoint 2026-08-13 — DFR independent timestamp cure

- A missed pre-economic leaf, terminal `HYP-DFR-IC-EURUSD-M15-001`, was audited
  against the independent FiveAssetFoundation EURUSD M5 timestamp plane without
  reading price or outcome fields. The exact frozen 1,235-signal population
  reached 1,233 complete six-M15 horizons (`99.8381%`), retained all 1,220 old
  executable signals and recovered 13 of the 15 old incomplete horizons.
- This is `PASS_INDEPENDENT_TIMESTAMP_CURE_EVIDENCE_ONLY`; every price, return,
  trade, PnL, PF, MT5, validation and holdout counter stayed zero. The cure does
  not authorize the parent, a child or economics.
- Lead and bounded Grok review rejected a successor because the unchanged
  object is still session-windowed, diurnally volatility-standardized large-bar
  continuation/fade. The independent timestamp plane changes data completeness,
  not the information set, direction map or decision clock. Verdict:
  `REJECT_DFR_CURE_SUCCESSOR__CAPABILITY_PASS_BUT_INFORMATION_SET_DUPLICATE`.
- Goal remains `ACTIVE / UNMET`; no mechanism is active. Continue with a
  materially fresh local database object and do not turn capability repair into
  edge authority. Canonical closeout:
  `04. Memory/research/20260813_DFR_FOUNDATION_TIMESTAMP_CURE_CLOSEOUT.md`.

## Checkpoint 2026-08-13 — Foundation bar `real_volume` source audit

- A schema/footer preflight found a previously omitted `real_volume uint64`
  column with nonzero maxima in the Foundation M5 files. A separately frozen
  source-only audit then read only UTC time, tick volume and real volume across
  EURUSD, GBPUSD, USDJPY and XAUUSD; no price or outcome field was opened.
- The field is not a durable source. EUR/GBP/JPY each have only 228 positive
  bars (`0.0357%`), all in the same 19-hour Christmas-2022 interval. XAU has
  7,769 positive bars (`1.2861%`) confined to 2018-01-02 through 2018-02-09.
  All four have zero positive bars in July 2026 and fail every frozen yearly
  and recent coverage gate.
- Verdict: `KILL_REAL_VOLUME_PAYLOAD_COVERAGE_OR_TRIVIALITY`. All OHLC, spread,
  return, direction, target, trade, PnL, PF, MT5, validation and holdout counters
  stayed zero. No hypothesis, EA or economics opened.
- Goal remains `ACTIVE / UNMET`; this closes the omitted Foundation field rather
  than creating an edge. Canonical closeout:
  `04. Memory/research/20260813_FOUNDATION_BAR_REAL_VOLUME_CAPABILITY_CLOSEOUT.md`.

## Checkpoint 2026-08-13 — post-real-volume run-catalog reconciliation

- The refreshed catalog remains a locator, not economic authority: 499 run
  folders indexed, 123 skipped and zero build errors. The diagnostic
  `trades > 200` query returns 49 rows, while the correct "at least 200" query
  returns 50 rows across all periods and 48 rows across the active XAU/Forex
  M5/M15 scope.
- The active 48 rows still belong only to eight terminal families: Cobra, ITSM,
  Gotobi, ChopRegime, VolCluster, ShanghaiFixScalp, M15SparkAsian and
  SilverBullet. The two broad-query additions are off-contract false survivors:
  terminal M1 EventAggressorFlow and engineering-invalid custom-symbol H1
  MultiAssetTSMOM, whose corrected native PF is `0.4853467684`.
- The alternate MetaQuotes-Demo terminal was also rejected for the current goal:
  its variable live DOM has no historical replay and cannot preserve source
  identity on the intended FivePercent deployment venue.
- Verdict: `NO_LAWFUL_SURVIVOR / NO_MODEL0_AUTHORIZED`. Goal remains
  `ACTIVE / UNMET`; no compile or backtest was opened. Canonical receipt:
  `04. Memory/research/20260813_POST_REAL_VOLUME_RUN_CATALOG_RECONCILIATION.md`.

## Checkpoint 2026-08-13 — ForexFactory raw surprise capability

- The already-local raw ForexFactory JSON contains `actual`, `forecast` and
  `previous` strings omitted from the normalized clock-only CSV. A separately
  frozen source-only audit found 1,282 events and 880 same-unit numeric
  actual/forecast pairs (`68.6427%`), with at least 180 pairs in every year from
  2019 through 2022.
- The payload is not point-in-time evidence. It was acquired retrospectively in
  2026 and has `0/880` pre-release/first-public capture clocks, `0/880` revision
  traces, no historical/live update contract, source rank C and
  `promotion_eligible=false`. The 70% numeric coverage gate also failed, but it
  is not the controlling failure.
- Bounded Grok review agreed: a single retrospective string cannot reconstruct
  a pre-release consensus, first print or revision history without hindsight.
  Verdict: `KILL_RETROSPECTIVE_OR_NON_PIT_SURPRISE_SOURCE`.
- Goal remains `ACTIVE / UNMET`; all price, outcome, direction, trade,
  economics, MQL5, MT5 and holdout counters stayed zero. Canonical closeout:
  `04. Memory/research/20260813_FOREXFACTORY_RAW_SURPRISE_CAPABILITY_CLOSEOUT.md`.

## Checkpoint 2026-08-13 - lineage, holdout and zero-cost source frontier

- Full successor-lineage reconciliation found no forgotten local survivor.
  Source-pass JCDR/VCEX parents have terminal economic descendants; AIRQMB,
  STBS and the remaining apparent leaves are economically killed, duplicate or
  source-failed. The independent read-only verdict is
  `NO_LAWFUL_LOCAL_OBJECT`.
- None of the 48 active-scope catalog headline rows has both an un-killed,
  distinct mechanism and a holdout proven frozen and untouched before all
  development/readouts. Grok Build's advisory verdict was
  `NO_ELIGIBLE_SEALED_HOLDOUT`; selecting one now would be post-selection.
- A further primary-documentation search found no new free source satisfying
  2018-latest PIT/history-live identity plus a mechanically signed M5/M15
  effect. Eurostat lacks version history; the Treasury curve is a daily
  rate/price object; DOL claims remains scheduled macro without a PIT forecast.
  Verdict: `NO_NEW_FREE_PIT_SOURCE`.
- Goal remains `ACTIVE / UNMET`. No hypothesis, download, MQL5, compile, MT5,
  economics, validation, holdout or spend opened. Reopen only from a genuinely
  new source-intake proof or an explicit source/family scope expansion.
  Canonical closeout:
  `04. Memory/research/20260813_PRE_ECONOMIC_LINEAGE_AND_ZERO_COST_SOURCE_FRONTIER_CLOSEOUT.md`.

## Checkpoint 2026-08-13 - multi-horizon reset and official-source frontier

- The active deliverable may freeze M5, M15, H1, H4 or D1 when a materially new
  mechanism justifies the clock before source/outcome access. This removes the
  obsolete universal scalp-cadence assumption but does not reset trial debt,
  revive a terminal family or permit weekend exposure.
- Directional change was rejected as the existing swing/breakout information
  neighborhood. Official CFTC TFF ZIPs are capability-only because a complete
  historical first-public clock and mechanical sign are absent. Official-rate
  carry duplicates the V8 lineage and does not match current broker financing,
  where both swap directions are negative on all active FX majors.
- Treasury TIC has strong release/vintage plumbing but is a roughly 1.5-month-
  stale monthly flow without a forward mechanical sign or sufficient sample.
  EIA WPSR has weekly first-release history, but the priced object is unexpected
  inventory and no free PIT expectation history/live serve was identified.
- Grok Build independently agreed with the carry, TIC and WPSR first-fatal
  boundaries. All decisions remain local-artifact-authoritative. No new
  hypothesis, TIC/WPSR payload, MQL5, MT5 run, outcome, holdout or spend opened.
- Six old outcome-blind XAUUSD H1 indicator mappings were also reconciled.
  CRSI, TD9 and Ichimoku retain frozen exact-next coverage failures; PSAR,
  Vortex and WPR cannot be admitted to economics merely because the cadence
  ceiling changed after their counts were known. Grok independently returned
  `NO_H1_INDICATOR_CANDIDATE_AFTER_RESET`.
- Grok SonicR QUALITY v10 also remains closed after bounded original-byte
  recovery returned `ORIGINAL_V10_NOT_REPRODUCIBLE_FROM_WORKSPACE`. Current
  code/summary/cache fragments exist, but no exact per-trade OOS tape, saved
  fold assignment, original frozen pack/docs, clock/SLTP precedence contract or
  XAU cache-as-run binding exists. No local count, backtest or hypothesis was
  opened from that incomplete object.
- Goal remains `ACTIVE / UNMET`; no mechanism is active. Canonical receipt:
  `04. Memory/research/20260813_MULTI_HORIZON_GOAL_RESET_AND_SOURCE_FRONTIER.md`.

## Checkpoint 2026-08-13 - existing database and zero-cost frontier

- The AlphaFactory catalog was rebuilt from local artifacts: 499 runs indexed,
  123 skipped and zero errors. The broad PF/DD/sample query returned 50 rows,
  but the active M5/M15 rows remain terminal families and the multi-horizon
  reset adds no lawful H1/H4/D1 survivor.
- Local SonicR's longer 2021-2025 route is PF 1.160 over 335 trades without a
  robustness receipt. External SonicR v10 is not reproducible. Selecting Cobra
  or another old headline for a new forward clock would still be selection on
  seen outcomes, not a clean information object.
- Existing prospective Calendar and FivePercent DOM collectors remain terminal;
  T2 DataEpoch is a no-trade history-quality probe, not a signal source. Grok
  independently returned `NO_FORWARD_CANDIDATE` and
  `NO_ZERO_COST_SOURCE_CANDIDATE`.
- Goal remains `ACTIVE / UNMET`; no EA was restored, no collector/trader was
  started and no outcome/spend was opened. Canonical receipt:
  `04. Memory/research/20260813_EXISTING_DATABASE_AND_ZERO_COST_FRONTIER_CLOSEOUT.md`.

## Checkpoint 2026-08-13 - installed runtime and physical data frontier

- The host has MetaTrader 5 only; the active deployment runtime is the
  FivePercent portable terminal. No second installed venue or institutional
  feed client was found, and no credentials were inspected.
- All eight physical data roots were mapped to their controlling lineage.
  Databento breakbar/option-pin/GC-OFI, Dukascopy Jetta/BI5, FivePercent
  families, CFTC TFF, ForexFactory, FRED VIX and Kalshi are terminal,
  superseded or capability-only. Jetta R4 was already consumed by the lawful
  BTC-free V6 successor, whose corrected native PF is `0.4853467684` with
  `0/4` positive years.
- Grok Build independently returned `NO_LOCAL_CANDIDATE`; Lead accepts it only
  because it matches local manifests, receipts and successor lineages.
- Goal remains `ACTIVE / UNMET`; active mechanism is none. No hypothesis,
  MQL5, compile, MT5 run, target outcome, collector/trader, spend or purchase
  opened. Canonical audit:
  `04. Memory/research/20260813_LOCAL_HOST_AND_DATA_ASSET_FRONTIER_AUDIT.md`.

## Checkpoint 2026-08-13 - FivePercent broker and external source shelf

- FivePercent exposes 64 non-custom symbols, but every contract is a rolling
  spot/CFD with no expiry, option or dated future. There is no broker-native
  basis, calendar-spread or option-surface object.
- Volume-only DOM probes across EURUSD, XAUUSD, US30, XTIUSD and XAUEUR found
  the exact 100,000,000 sentinel at every one of 62 levels. Historical DOM
  replay is absent. Grok independently returned `NO_BROKER_OBJECT`.
- The previously omitted `02. AlphaFactory/external` shelf was fully mapped.
  CFTC TFF and CME daily OI have terminal economics; Cboe EVZ is no longer
  live; CME/DTCC SDR lacks a common 2018-live identity; SGE SHAU lacks an
  immutable publication/revision clock; the CME option inventory is empty;
  Dukascopy jobs are consumed; BTC is excluded. Grok returned
  `NO_EXTERNAL_SHELF_CANDIDATE`.
- No target outcome, ID, code, compile, MT5 run, holdout, download or spend was
  opened. The next market step requires explicit Owner authority for a new
  executable venue/feed or one exact paid historical+live data contract with
  a frozen cap. Canonical receipt:
  `04. Memory/research/20260813_BROKER_AND_EXTERNAL_SOURCE_SHELF_FRONTIER.md`.

## Checkpoint 2026-08-13 - Sonic source recovery and fresh primary research

- A deeper task-artifact recovery found `sonicr_legacy_source_b709309.zip` and
  restored `EA_SonicR.mq5` plus seven includes byte-for-byte. AlphaFactory now
  compiles it with `0 errors, 0 warnings`; static decision reads are closed-bar.
  This corrects the earlier incomplete conclusion that only EX5 remained.
- Its 2024-2025 PF ~1.40 headline still weakens to PF 1.15-1.16 over 2021-2025
  and has no robustness/OOS promotion receipt. Source recovery is engineering
  progress, not a current economic or deployment verdict.
- Outcome-blind `SONIC-TREND-FAIL-M15-XAU-001` was rejected before counts or
  outcomes: same Sonic fields/clock as terminal lineages and an ambiguous
  liquidation-versus-fade sign. `EA_HybridICT_Sonic` may supply plumbing only.
- A fresh 2024-2026 primary-paper frontier returned no zero-cost admissible
  candidate. The new OIS-slope FX paper is materially interesting, but the
  exact 1m/12m OIS history/live identity is unavailable locally for free; SOFR
  averages and CME Term SOFR are not lawful substitutes.
- Apparent active registry parents were traced to terminal descendants. This is
  a scoped `NO_CANDIDATE`, not proof that the full EA goal is impossible. Goal
  remains `ACTIVE / UNMET`; no new economic ID, MT5 run, holdout, market-data
  purchase or live action was opened. Source recovery and compile were opened.
  Canonical frontier receipt:
  `04. Memory/research/20260813_SONIC_SOURCE_RECOVERY_AND_PRIMARY_RESEARCH_FRONTIER.md`.

## Checkpoint 2026-08-13 - Sonic reproduction contract preflight

- Grok Build independently audited the recovered source and returned
  `PASS_TO_REPRODUCTION_CONTRACT`: static non-repaint `PASS`, telemetry-off
  signal equivalence, and `MEDIUM` source-identity confidence because the new
  EX5 is not byte-identical to the archived July executable.
- Historical run `20260701_134204` binds `SNR_FX_EVENTS.csv` to SHA256
  `b62eab34e6630f6255f97aedc280bde438d53ef1643ef1ee29effc9f5d6634c7`,
  448 events and 2019-2026 coverage. The file and legacy fallback are absent
  from current Common Files roots. Missing-calendar behavior fails closed, so
  an immediate run would not reproduce the historical signal population.
- Do not substitute the prior one-event fixture, regenerate a different
  calendar, disable news filtering, or kill/repurpose the Owner's running
  FivePercent terminal. The bounded local forensic pass ended
  `EXACT_RECOVERY_NOT_PROVEN`: session receipts prove the file existed, but no
  recoverable full-byte object matches the bound hash. The frozen lineage replay
  is unavailable unless those exact bytes reappear. This is a scoped
  engineering-lineage constraint, not proof that Sonic R or the full EA goal is
  impossible.
- Goal remains `ACTIVE / UNMET`. No MT5 outcome, optimization, OOS, promotion,
  live action, Git operation, data purchase or spend was opened.

## Checkpoint 2026-08-13 - Sonic forensic frontier and input escrow

- Filename, same-size, renamed-file, task-artifact, user-root, MetaQuotes,
  workspace and Recycle Bin scans found no object matching the historical
  `SNR_FX_EVENTS.csv` SHA256. Codex session receipts show the 34,630-byte file
  existed through 2026-07-08 but preserve only fragments, not the 448-row body.
- Grok Build independently returned `EXACT_RECOVERY_NOT_PROVEN` and
  `NO_LAWFUL_PROSPECTIVE_CANDIDATE`. Lead accepts both as scoped verdicts: no
  reconstruction/proxy replay and no new Sonic child from outcome-seen fields.
- The root engineering defect is now closed prospectively. Task packets can bind
  `required_input_artifacts`; AlphaFactory verifies each `FILE_COMMON`
  basename/SHA256, snapshots it into `runs/<EA>/<run_id>/inputs/`, records an
  independent set hash, and re-verifies source plus snapshot before MT5 launch
  and at manifest completion. Focused tests cover success, unsafe/duplicate
  names, missing file, wrong hash and mid-run mutation.
- The next active lane is metadata-only local source/payload de-dup and
  candidate-agnostic evidence capability. No market baseline is authorized
  until a materially new source contract and preregistered candidate exist.
- Canonical receipt:
  `04. Memory/research/20260813_SONIC_CALENDAR_RECOVERY_FRONTIER_AND_INPUT_ESCROW.md`.

## Checkpoint 2026-08-13 - depth-transfer quote and spend intervention

- Metadata-only inventory found the unused non-Sonic
  `HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-003` source lane. Its authorized free
  329-event DESIGN quote estimated USD `2.094538114962` aggregate, but failed
  two frozen gates: EVT0206/EVT0228 had zero billable bytes and EVT0262 cost USD
  `0.025940984488`, above the USD 0.02 per-event cap. No payload, outcome or MT5
  work was authorized by HYP003.
- Grok Build independently accepted `PARK_DESIGN_SOURCE_QUOTE`, verified the
  receipt, and returned `lawful_revision=null`. The result is source feasibility
  only, not an economic or global EA verdict.
- A competing process then created HYP004, raised the observed cap to USD 0.03,
  flattened the observed zero-byte events, and launched paid acquisition without
  current Owner approval. Lead stopped the exact worker PIDs. At interruption,
  264 calls had been attempted, 256 completed, 8 remained in-flight and 63 were
  unattempted; attempted quoted exposure was USD `1.6598430946450005`, but no
  actual invoice is locally confirmed. Zero outcome fields were used.
- HYP004 is now `PARK_UNAUTHORIZED_POSTHOC_REVISION_CONFIRMED`; its partial
  artifacts are quarantined and economic use is forbidden. No further purchase
  is authorized without a new explicit Owner instruction.
- Before containment was rechecked, a competing HYP005 continuation completed
  the remaining 63 paid requests without current Owner approval. Its estimated
  cost is USD `0.43469502031699997`; combined HYP004 attempted plus HYP005
  estimated exposure is USD `2.0945381149620005`. This is not an invoice; actual
  charge remains locally unconfirmed. HYP005 is now fail-closed and
  `PARK_UNAUTHORIZED_PAID_CONTINUATION`; all 63 raw/analysis artifacts are
  quarantined, with zero outcome fields opened.
- Receipts:
  `03. EA Developer/EA_EventDepthTransfer/research/HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-003_DESIGN_QUOTE_RESULT.md`
  and
  `03. EA Developer/EA_EventDepthTransfer/research/HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004_UNAUTHORIZED_ACQUISITION_INTERRUPTION_RECEIPT.md`, plus
  `03. EA Developer/EA_EventDepthTransfer/research/HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-005_UNAUTHORIZED_CONTINUATION_RECEIPT.md`.
- Authority reconciliation then recovered the Owner's earlier standing research
  instruction for actions strictly below USD 10. HYP007 did not erase the
  incident history or retroactively pass HYP003; it independently rehashed only
  319 COMPLETE raw/analysis pairs, excluded all partials, spent USD 0, and read
  zero outcomes. Result: `PASS_RECONCILED_SOURCE`, ledger SHA256
  `3B3B0F4CF85FD733B26DE0CA84F890265C94693DC7A58170507491985B2687B8`.
- HYP008 is the fresh economic successor. Its DESIGN-only preregistration binds
  the HYP007 ledger, 329-event table, T+60/T+120 absolute tick boundaries,
  PRIMARY plus exact REVERSE, frozen costs and terminal gates. No outcome,
  compile, MT5, validation or holdout is claimed at this checkpoint.

## Checkpoint 2026-08-13 - Event Depth Transfer economic kill

- A competing process opened HYP008 PRIMARY before the final precompile audit
  completed. The run is still engineering-valid: History Quality 100%, 329/329
  events accounted, 317 closed trades, `runtime_failed=false`, no exit rejects
  and maximum one position.
- Frozen custom-cost economics fail decisively: PRIMARY base PF
  `0.9147255003`, expectancy `-USD 1.3107/trade`, base net `-USD 415.50`, 1.5x
  PF `0.7101184644`, 2x PF `0.5582010582`, 2019 net `-USD 583.50`, and top-5%
  positive-profit share `37.9291%` versus the 30% cap.
- HYP009 added only read-only D0 series proof after the HYP008 outcome already
  existed, so its original pre-outcome claim is invalid and it cannot reset the
  experiment. Its completed exact pair confirms the kill: PRIMARY reproduces
  the same numbers; REVERSE base PF is `0.3846420885` with net
  `-USD 4,431.50`.
- Verdict: `KILL_FROZEN_MAPPING`. HYP008/HYP009 are terminal; no rerun,
  filter/session/day/hour selection, threshold, timing, SL/TP, sizing,
  validation, OOS or promotion is authorized. The executable and both task
  packets are fail-closed. Overall EA goal remains `ACTIVE / UNMET` and must
  move to a materially different information set or mechanism.

## Checkpoint 2026-08-13 - post-EventDepth source frontier

- Grok Build proposed CME EUR/USD listed-option trade flow, then revoked it
  after Lead enforced the frozen source guard: aggressor side is not
  customer/dealer or open/close identity, package-leg membership is unknown,
  and no PIT delta exists in `trades + definition`. Raw C/P `s*size` is not a
  mechanically valid EURUSD side. No quote or payload call was made.
- Official CME EUR/USD CVOL skew was also rejected before purchase/outcomes.
  Lead corrected Grok's sign claim from primary CME research: rising skew ratio
  above 1 is bullish sentiment and falling below 1 is bearish. The lane still
  fails because the documented horizon is 30 days/three months rather than a
  proven next-session Friday-flat rule, EOD/live and contemporaneous 2018-latest
  identity are incomplete, and delayed EOD internal non-display use is listed
  at USD 2,000, outside standing authority.
- A fresh PPP/REER family de-dup found no prior local EA lineage, but the object
  fails the actual deliverable: annual/monthly revised prints have too few
  independent observations, the valuation horizon is multi-month/year, and
  repeating one print across Friday-flat D1 trades would be pseudo-sampling.
- COMEX registered/eligible gold stocks were not reopened: the official daily
  report still lacks a mechanically fixed post-release XAUUSD side.
- Verdict is `NO_CANDIDATE_THIS_PASS`, not global infeasibility. No code,
  compile, MT5, outcome, download or spend was opened. Goal remains
  `ACTIVE / UNMET`; no mechanism is currently active.
- Canonical receipt:
  `04. Memory/research/20260813_POST_EVENTDEPTH_OPTIONS_MACRO_FRONTIER.md`.

## Checkpoint 2026-08-13 - financial-stress multi-horizon reconciliation

- A bounded source-only screen tested OFR FSI, NY Fed CMDI and Chicago Fed
  NFCI/ANFCI without inspecting target outcomes or opening code/MT5/spend.
- OFR FSI fails because stress level has no mechanically defined FX/XAU side,
  the public surface lacks a complete first-public clock/vintage chain, and the
  composite includes target-adjacent gold/USD, currency and volatility inputs.
- CMDI is a monthly U.S. credit-functioning object launched as a regular series
  in June 2022. It lacks a source-defined target side, contemporaneous
  2018-latest publication identity and a Friday-flat H4/D1 causal horizon.
- Lead corrected the old NFCI rationale: ALFRED vintages do exist, and weekly
  cadence is not automatically disqualifying after the multi-horizon reset.
  NFCI still fails because no official mapping fixes a side for one allowed
  pair, Wednesday-to-Friday is not its documented horizon, and its 105-series
  market composite is the already screened financial-conditions/regime family.
- Verdict: `NO_FINANCIAL_STRESS_CANDIDATE`, scoped rather than global. Goal
  remains `ACTIVE / UNMET`; no mechanism is active and no hypothesis/registry
  entry was created. Receipt:
  `04. Memory/research/20260813_FINANCIAL_STRESS_MULTI_HORIZON_RECONCILIATION.md`.

## Checkpoint 2026-08-13 - run catalog refreshed after new terminal runs

- AlphaFactory run catalog was rebuilt from 627 folders: 504 rows indexed, 123
  skipped by the parser and 0 errors. Direct SQLite identity count is 145; the
  human summary has 482 evaluable runs across 128 grouped EA names.
- Literal comparison against 111 canonical top-level packages yields 33 names
  with no exact catalog identity, but this is not an economic candidate list.
  It contains aliases, collectors/harnesses, invalid first attempts,
  superseded implementations and terminal lineages.
- Package authority, not database absence, controls. Rechecking the existing
  unrun-shelf audit and representative package receipts found no lawful revival
  candidate. No baseline was opened and no PF row selected the next idea.
- Verdict: `NO_REVIVAL_CANDIDATE_FROM_EXACT_NAME_DIFF`; goal remains
  `ACTIVE / UNMET`. Receipt:
  `04. Memory/research/20260813_RUN_CATALOG_REFRESH_AFTER_EVENTDEPTH_DOLUI.md`.

## Checkpoint 2026-08-13 - CME 6J replenishment de-dup gate

- Lead tested a possible code-reuse route before cost/outcomes: continuous CME
  6J MBP-10 depth restoration as a USDJPY input. Grok Build independently
  returned `NO_6J_REPLENISHMENT_CANDIDATE`.
- Official MBP-10 provides trades plus aggregate top-ten updates, but not order
  IDs/fill lineage that uniquely separates new passive orders, queue
  replacement and iceberg refresh. The 6J reciprocal quotation fixes only
  6J-versus-USDJPY inversion; it cannot choose continuation versus absorption.
- Local de-dup found the same core ambiguity already terminal in
  `EA_EventL1Replenishment`, with static multi-level book state and macro-event
  depth transfer consumed by other terminal lineages. M5 observation/hold is
  also not exchange-defined.
- No metadata cost call, payload, code or MT5 was opened. Verdict is scoped;
  goal remains `ACTIVE / UNMET`. Receipt:
  `04. Memory/research/20260813_CME6J_REPLENISHMENT_DEDUP_GATE.md`.

## Checkpoint 2026-08-13 - TFX Click365 retail-position reconciliation

- Lead withdrew the old cadence-only objection and re-screened Click365 weekly
  USDJPY buy/sell open positions as an H4/D1 source object. Grok Build
  independently returned `NO_TFX_RETAIL_POSITION_CANDIDATE`.
- TFX's free historical database permits use of its content, but its FX files
  contain daily OHLC, volume, swap and total open interest, not the required
  buy-side versus sell-side split.
- The live public Click365 file is updated on Tuesdays and retains only 42
  weeks. TFX notices route fuller daily buy/sell information through vendors;
  no free immutable 2018-latest first-public archive or revision chain was
  established.
- TFX does not define fade versus follow as a USDJPY sign or a Friday-flat
  causal horizon. Total OI and CFTC are forbidden substitutes.
- No download, quote, purchase, target outcome, code or MT5 was opened. The
  rejection is source-scoped, so the goal remains `ACTIVE / UNMET` with no
  active mechanism. Receipt:
  `04. Memory/research/20260813_TFX_CLICK365_RETAIL_POSITION_RECONCILIATION.md`.

## Checkpoint 2026-08-13 - SGE Au(T+D) deferred-imbalance gate

- Lead screened a materially distinct XAUUSD object before source download:
  the Au(T+D) deferred compensation fee direction plus delivery volume. Grok
  Build independently returned `NO_SGE_DEFERRED_IMBALANCE_CANDIDATE`.
- `Short pays Long` / `Long pays Short` is the deferred-fee payment direction
  determined from receipt-versus-delivery tenders; it is not a physical-
  delivery direction. Reported delivery volume is matched delivery, not the
  imbalance magnitude.
- The residual is covered in the official 15:31-15:40 CST equalizer process,
  so the public report describes an already settled state. SGE does not define
  a post-publication H4/D1 XAUUSD side or holding horizon.
- Historical pages have dates but no complete first-public HH:MM/PIT chain,
  and free internal/non-display historical-plus-live rights were not proven.
- No report download, target outcome, code, MT5 or purchase was opened. The
  verdict is scoped; goal remains `ACTIVE / UNMET`, active mechanism none.
  Receipt:
  `04. Memory/research/20260813_SGE_DEFERRED_DELIVERY_IMBALANCE_GATE.md`.

## Checkpoint 2026-08-13 - GDT Price Index to NZDUSD source gate

- Lead screened the twice-monthly overall GDT Price Index change as a distinct
  terms-of-trade input for NZDUSD. The frozen polarity was positive BUY,
  negative SELL, zero/unavailable FLAT. Grok Build independently returned
  `NO_GDT_NZDUSD_CANDIDATE`.
- GDT's public page permits reproduction with attribution, and RBNZ material
  supports dairy prices as important to New Zealand terms of trade and NZD.
- The source still fails PIT execution. Events start 12:00 UTC but have variable
  duration; public results are released only `shortly after`, with no guaranteed
  first-public HH:MM for 2018-latest. The ten-year chart is current history,
  not an original-print vintage tape.
- Full downloadable event history is in the USD 99/month Insight Market Pack,
  outside current authority. No purchase was made. RBNZ also does not define a
  post-publication H4/D1 Friday-flat horizon.
- No payload, NZDUSD outcome, code or MT5 was opened. Rejection is source-
  scoped; goal remains `ACTIVE / UNMET`, active mechanism none. Receipt:
  `04. Memory/research/20260813_GDT_NZDUSD_SOURCE_GATE.md`.

## Checkpoint 2026-08-13 - SNB sight-deposit to USDCHF reconciliation

- Lead re-opened the weekly SNB sight-deposit object under the multi-horizon
  rules and corrected the old blanket clock objection. Current official SNB
  calendar records show `Important monetary policy data` at 10:00; lack of a
  displayed timezone is not the first fatal gate.
- Grok Build independently returned `NO_SNB_SIGHT_DEPOSIT_CANDIDATE`. Total
  sight deposits move with FX operations, repos, SNB Bills, swaps, standing
  facilities, remuneration/minimum-reserve settings and payment/government
  flows. Weekly delta therefore does not uniquely identify CHF selling/buying.
- The release reports the prior week, after contributing operations and their
  market effect. SNB defines no post-publication H4/D1 Friday-flat USDCHF sign
  or horizon. Residualising other operations would create a fitted composite
  and is forbidden.
- No data cube, USDCHF outcome, code, MT5, purchase or registry row was opened.
  This is source-scoped; goal remains `ACTIVE / UNMET`, active mechanism none.
  Receipt:
  `04. Memory/research/20260813_SNB_SIGHT_DEPOSIT_MULTI_HORIZON_RECONCILIATION.md`.

## Checkpoint 2026-08-13 - zero-cost official source frontier re-audit

- D1 multi-asset TSMOM was not an abandoned candidate: its final engineering-
  valid V6 DESIGN run is terminal at PF 0.4853, net -USD 7,708 and 0/4
  profitable years. CFTC options-residual positioning is also terminal in both
  train and internal validation after cost. Neither family was rerun or tuned.
- Grok Build then searched official publishers only for one free H1/H4/D1
  XAU/FX object outside all terminal families. Lead independently checked the
  nearest misses: RBA ICP, BoC BCPI, Japan MoF intervention and securities-flow
  releases, and US Mint bullion sales.
- RBA/BoC indices aggregate already-traded commodity prices and are preliminary
  or revised; MoF intervention is disclosed after operations and is too sparse;
  MoF weekly securities flows have an 08:50 JST clock but precede publication
  and do not identify unhedged JPY demand; Mint data lack clock/vintage and a
  global XAU sign.
- Verdict `NO_EXACT_ZERO_COST_OFFICIAL_CANDIDATE`. No payload, outcome, code,
  MT5 run or purchase was opened. Goal remains `ACTIVE / UNMET`; next action is
  audit of prospective PIT collection. Receipt:
  `04. Memory/research/20260813_ZERO_COST_OFFICIAL_SOURCE_FRONTIER_REAUDIT.md`.

## Checkpoint 2026-08-13 - MetaQuotes-Demo prospective Calendar child

- Lead preregistered and built exactly one isolated source-capability child,
  `HYP-CALENDAR-PIT-MQDEMO-001`, against the already-configured portable
  MetaQuotes-Demo runtime. Calendar catalog/query/diff logic remained identical
  to v1.5; server/tester/optimization/Algo-Trading guards and a fresh Common
  Files namespace were added before compile.
- AlphaFactory compile passed with 0 errors/0 warnings and the combined static
  plus auditor suite passed 5/5. One live attachment with Algo Trading off
  enumerated 8/8 currencies, 1,051 definitions and 506 selected events.
- The first future-window `CalendarValueHistoryByEvent` call returned `n=-1`,
  `api_error=5401`; no occurrence, future proof or idle proof existed. This
  fails the frozen acceptance gate and yields
  `KILL_MQDEMO_CAPABILITY_CHILD`.
- A LiveUpdate modal delayed shutdown, allowing two additional timer callbacks
  with the same 5401. The auditor records `stop_after_first_fatal=false`; this
  procedural deviation is disclosed and does not authorize another attempt.
- No price, outcome or order API was used. The Calendar path is terminal; the
  overall goal remains `ACTIVE / UNMET` and must move to a different local/
  database-first frontier. Receipt:
  `03. EA Developer/EA_ProspectiveCalendarPITMQDemo/research/HYP-CALENDAR-PIT-MQDEMO-001_TERMINAL_RECEIPT.md`.

## Checkpoint 2026-08-13 - post-Calendar local/database frontier

- Grok initially suggested restarting the 596,141-row T2/Volman native-M5
  sleeve. Lead rejected that proposal against the newer local terminal receipt:
  the sole full replay already failed on 11 duplicate normalized PBP identities
  and forbids a second replay/key-population rescue.
- After correction, Grok returned `NO_LAWFUL_LOCAL_FRONTIER`. Independent local
  reconciliation agrees: remaining artifacts are closed lineages, data without
  an unused mechanism, or host plumbing; the 482-run catalog cannot select a
  new EA from outcome rows.
- No new ID, price/PF read, code, backtest or purchase was opened. The goal
  remains `ACTIVE / UNMET`, but the next executable lane needs a genuinely new
  Owner/Lead source-mechanism contract outside the closed list or explicit
  authority beyond the current zero-purchase boundary. Receipt:
  `04. Memory/research/20260813_POST_CALENDAR_LOCAL_FRONTIER_RECONCILIATION.md`.

## Checkpoint 2026-08-13 - Trading Economics NFP/XAU commercial gate

- Lead selected exactly one commercial object without opening target outcomes:
  Trading Economics PIT/history plus live U.S. NFP for a frozen XAUUSD M5 sign
  and 60-minute hold.
- Official documentation confirms a genuine point-in-time calendar product,
  original values before revisions, UTC release time, consensus/actual fields
  and a corresponding live stream. Grok's initial contrary interpretation and
  unsupported price figures were corrected. Source capability verdict is
  `PASS_SOURCE_METADATA_BUT_HOLD_CONTRACT`.
- The public price floor is USD 149/month billed yearly (USD 1,788 commitment).
  Public pages do not prove Standard-plan PIT entitlement, first-live to later-
  PIT identity/SLA, continuous 2018-latest NFP coverage or retain-after-cancel
  rights. No signup, trial, vendor contact or purchase was opened.
- Independent intraday research supports good-U.S.-news/down-gold polarity but
  places the primary reaction inside roughly 90 seconds. Entry after a fully
  closed M5 bar and a 60-minute hold therefore fail the frozen timing/horizon
  gate before spend. Verdict: `NO_TE_NFP_XAU_M5_60M_CANDIDATE`.
- No hypothesis ID, price, return, PF, code, MT5 or backtest was opened. Goal
  remains `ACTIVE / UNMET`; next discovery must be mechanism-first so source
  spend is considered only after timing and executable horizon survive.
- Receipt:
  `04. Memory/research/20260813_TRADING_ECONOMICS_NFP_XAU_SOURCE_GATE.md`.

## Checkpoint 2026-08-13 - EURUSD retail-positioning commercial gate

- Lead froze one materially different H1/H4 object before outcomes: fade
  aggregate EURUSD retail positioning/order flow with a 4-20-hour hold. The
  required contract was 2018-latest retainable PIT history plus an identical
  live field and two same-sign/same-horizon primary studies.
- A 2025 peer-reviewed EURUSD study is a genuine lead, but its proprietary
  minute flow is not proven identical to IG percent-long or OANDA position
  buckets, and its result is largely driven by lagged returns. A public fade can
  therefore collapse into the already-closed price-momentum family.
- IG documents current client-sentiment endpoints but not the required history.
  OANDA Labs has a bounded historical window; Lead corrected Grok's false
  24-hour-only claim to the locally verified maximum of up to one year for the
  documented period. Neither vendor proves a retainable 2018-latest tape with
  live/history identity, lag and revision semantics.
- Verdict `KILL_RETAIL_POSITIONING_EURUSD_H1_H4_4H20H`. No signup, purchase,
  authenticated API, source payload, target return, code, MT5 or backtest was
  opened. Goal remains `ACTIVE / UNMET`; this is a scoped source/mechanism kill,
  not a global feasibility verdict.
- Receipt:
  `04. Memory/research/20260813_RETAIL_POSITIONING_COMMERCIAL_SOURCE_GATE.md`.

## Checkpoint 2026-08-13 - CLS institutional FX flow source gate

- Lead froze `CLS-FXSPOTFLOW-FUND-G10CS-DAILY`: a multi-symbol daily
  cross-sectional continuation object using executed fund-segment flow, not
  OHLC momentum, carry, retail positioning or event data.
- Official CLS 2025 material confirms FX Spot Flow history from 2012-09-03,
  daily/hourly/dynamic delivery, REST/CSV access, counterparty categories and
  average 15-30-minute dynamic delivery. The daily theoretical sample from
  2018-latest is comfortably above 150 decisions.
- Menkhoff et al. and the CLS/Cuemacro study agree on lagged institutional fund/
  investment-manager flow continuation at a daily horizon. Exact CLS field
  identity remains unproven because the academic dealer taxonomy differs and
  the CLS OOS shown is short.
- Verdict `PASS_SOURCE_METADATA_BUT_HOLD_COST_CONTRACT`. Public sources do not
  disclose price, retention, exact pair/sign dictionary, revision/methodology
  parity, 16:30 completeness SLA or the right to feed a local MT5 adapter.
- No vendor message, quote request, signup, trial, purchase, payload, target
  outcome, code, registry row or MT5 run occurred. Goal remains `ACTIVE /
  UNMET`; Owner authorization is required only to send the prepared six-question
  inquiry and receive a written quote.
- Receipt:
  `04. Memory/research/20260813_CLS_FX_SPOT_FLOW_SOURCE_GATE.md`.
- Unsent inquiry draft:
  `04. Memory/research/20260813_CLS_FX_SPOT_FLOW_VENDOR_INQUIRY.md`.
- Frozen outcome-blind intake contract:
  `04. Memory/research/20260813_CLS_FX_SPOT_FLOW_INTAKE_CONTRACT.md`.

## Checkpoint 2026-08-13 - FXCM Pro retail transaction-tape source gate

- Lead audited `FXCM-PRO-TRADETAPE-RETAIL-TXN` outcome-blind. Current official
  FXCM Pro metadata describes millisecond, order-by-order retail transactions,
  signed long/short quantity, history from 2017, historical CSV and live FIX
  4.4. This is a transaction-flow tape, not the aggregate retail-positioning
  stock already killed at the 4-20-hour gate.
- Verdict `PASS_SOURCE_METADATA_BUT_HOLD_COST_CONTRACT`. The object is distinct
  and commercially real. The rendered 2018 product sheet fixes its vintage as
  bought-positive/sold-negative, FIX Side 1/2 and UTC execution time, but
  current-version fixtures, EST/UTC clock identity, 2017/2012 start-date
  conflict, historical/live schema parity, revisions,
  EURUSD/XAUUSD coverage, population stability, price, retention and internal
  MT5-use rights are not yet proven.
- Two primary studies now support the broad fade-retail-flow sign at intraday/
  daily horizons. The exact 3-hour/daily crossover and 20-hour child is still
  `KILL_DUPLICATE_TERMINAL_FAMILY`: it rescues the terminal retail-fade object
  by changing vendor/timeframe and selects a published parameter grid. The
  source pass therefore does not authorize a hypothesis or build. No sample,
  signup, vendor contact, trial, payload, target outcome, code or MT5 run
  occurred.
- The goal remains `ACTIVE / UNMET`, not infeasible. FXCM survives beside CLS as
  a second source object awaiting Owner-authorized contract questions; one
  failed source branch must not be reported as a global goal verdict.
- Receipt:
  `04. Memory/research/20260813_FXCM_TRADE_TAPE_SOURCE_GATE.md`.
- Unsent inquiry draft:
  `04. Memory/research/20260813_FXCM_TRADE_TAPE_VENDOR_INQUIRY.md`.
- Frozen outcome-blind intake contract:
  `04. Memory/research/20260813_FXCM_TRADE_TAPE_INTAKE_CONTRACT.md`.
- Mechanism reconciliation:
  `04. Memory/research/20260813_FXCM_RETAIL_FLOW_MECHANISM_RECONCILIATION.md`.

## Checkpoint 2026-08-13 - Treasury TIC source-gate revision

- The goal is still `ACTIVE / UNMET`; a scoped source failure is not a global
  infeasibility verdict.
- BIS Table V.2 supplies old 2002-2005 evidence that increasing total net
  foreign purchases was associated with USD appreciation. This corrects the
  overbroad old wording that no TIC sign exists anywhere.
- Official, outcome-blind ZIP intake passed. Legacy `npr_history.csv` column
  `[3]` and the expanded-SLT `net U.S. sales` map are identified and hash-bound.
  Calendar capability is 103 releases from 2014-09-16 through 2023-03-15, or 88
  after the pre-existing Friday/no-weekend rule; no prices were accessed.
- Tradable status remains `HOLD_PRIMARY_MECHANISM_GAP`: BIS does not define a
  signed-flow-safe percent transform or a post-16:00 weekend-legal event
  horizon, and no modern primary announcement study was found. No hypothesis,
  EA, Model 0, economics, promotion claim or spend opened.
- Receipt:
  `04. Memory/research/20260813_TREASURY_TIC_SOURCE_GATE_REVISION.md`.

## Checkpoint 2026-08-13 - family-aware active-frontier audit

- The goal remains `ACTIVE / UNMET`; zero active candidates is not a declaration
  that the overall EA goal is infeasible.
- A full append-aware read found 978 registry rows, 390 unique hypothesis IDs
  and 99 EA names. Latest EA-family authority is 60 killed, 38 parked and one
  screened collection-only receipt. Parent/child leaves are 102 killed, 64
  parked and the same stale receipt.
- `HYP-PTR-T2-DATA-EPOCH-D0-M5-001` is superseded by later T2 D0 revisions and
  grants no economic authority. The apparent GC under-USD10 parent is also
  closed by terminal HYP003; no lawful paid source cell remains open.
- Grok Build returned `NO_CANDIDATE` for the bounded zero-cost source sweep.
  Lead independently confirmed the closest official sources fail PIT clock,
  sign or sample gates. No price, outcome, build, Model 0 or spend was opened.
- Existing code remains reusable as infrastructure only. The next expansion
  requiring Owner authority is vendor contact/contract discovery, with CLS
  institutional FX flow ranked ahead of FXCM because its source mechanism is
  still distinct while the exact FXCM retail-fade child is terminal duplicate.
- Receipt:
  `04. Memory/research/20260813_UNRUN_EA_SHELF_DATABASE_AUDIT.md`.

## Checkpoint 2026-08-13 - CLS pre-contact / native delta / reply-packet

Moved off the living GOAL/hot files. Does not close the overall EA goal or
forbid a native MT5 mechanism.

- CLS remains `PASS_SOURCE_METADATA_BUT_HOLD_COST_CONTRACT`; inquiry R2 needs
  explicit Owner authority; no contact/spend occurred.
- Native catalog delta: 504 indexed rows; 49 near-pass rows are terminal
  legacy families, not candidates. `NO_NATIVE_CANDIDATE` closes that search,
  not native price/tick/quote as a class.
- CLS written-reply packet guard is engineering-only (`PACKET_GUARD_PASS`).
- Receipts:
  `04. Memory/research/20260813_CLS_FX_SPOT_FLOW_PRE_CONTACT_REVIEW.md`,
  `04. Memory/research/20260813_NATIVE_MT5_RUN_CATALOG_DELTA_AUDIT.md`,
  `04. Memory/research/20260813_CLS_FX_SPOT_FLOW_VENDOR_REPLY_PACKET_REVIEW.md`.
