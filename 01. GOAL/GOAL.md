# GOAL — Edge thực, kiểm chứng được

Trạng thái: **ACTIVE / UNMET** cho tới khi có ít nhất một symbol-sleeve đạt DONE. Một thử nghiệm thất bại, compile xanh hoặc workflow hoàn tất không phải DONE.

## Outcome

Tạo ít nhất một chiến lược scalping M5/M15 có expectancy dương sau chi phí thật, cadence đủ giao dịch, ổn định ngoài mẫu và có thể vận hành an toàn trên MT5.

Deliverable là một EA hoàn chỉnh ở mức deployment-readiness. Agent không tự
nhận mình là quant hay tự cấp quyền dùng vốn thật; thay vào đó phải làm việc
theo chuẩn của một quant trader chuyên nghiệp: luận điểm thị trường rõ, dữ liệu
point-in-time phù hợp, giả thuyết falsifiable, cost/risk thực tế và verdict dựa
trên bằng chứng. Owner giữ quyền quyết định funded paper/live deployment.

Universe bắt buộc khi claim cấp book: XAUUSD, BTCUSD, EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD và NZDUSD. Mỗi symbol được claim phải tự pass; không pooled kết quả để cứu symbol thua.

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
| Exposure | Hạn chế overnight; không giữ qua cuối tuần theo scalp contract |

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
  `2018-01-01` đến mốc dữ liệu mới nhất đã xác minh cho XAUUSD, BTCUSD, EURUSD,
  USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD và NZDUSD. Mỗi sleeve có verdict riêng;
  không pool P&L để cứu symbol thua và không gọi symbol chưa đủ history là PASS.
- `Cùng EA family` được hiểu là một deployable portfolio host với shared
  execution/risk engine; không ép một signal rule phổ quát lên FX, XAU và BTC.
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
- “Ưu tiên scalping” khóa decision/management ở M5/M15, thời gian giữ ngắn và
  không giữ cuối tuần; nó không đồng nghĩa với cadence `2–5/tuần`. Candidate mới
  phải preregister floor/cap theo cost, sample size, turnover và capacity của
  mechanism. Các hypothesis cũ vẫn giữ nguyên verdict theo contract đã đóng
  băng; thay đổi này không được dùng để cứu hoặc chạy lại một object đã terminal.

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
