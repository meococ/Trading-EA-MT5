# WORKFLOW — Phát triển một EA có trách nhiệm

Đây là workflow chung duy nhất. Mục tiêu là tạo một EA vận hành đúng và có edge được kiểm chứng, không phải hoàn thành nhiều thủ tục.

## Nguyên tắc cố định

- Chỉ dùng MQL5, MT5 Strategy Tester và `02. AlphaFactory/alpha.ps1`. Không dùng TradingView làm bằng chứng, parity hay acceptance.
- Một source EA phải phục vụ backtest, forward test và live; không viết logic riêng để làm đẹp backtest.
- Mỗi kết quả phải truy được source, parameters, symbol, timeframe, dữ liệu, broker, timezone, cost và MT5 build.
- Backtest tốt chỉ là bằng chứng quá khứ. Không gọi là edge trước khi vượt qua OOS, cost stress và forward test.
- Mỗi symbol được phát triển bằng profile riêng vì spread, volatility, session và hành vi giá khác nhau. Kết quả gộp không được che một symbol thua.

## 1. Chốt chiến lược trước khi code

Viết một specification ngắn, đủ để người khác code lại mà không phải đoán:

- setup vào lệnh, thoát lệnh, stop, target và quản lý vị thế;
- vai trò chính xác của từng indicator hoặc price-action condition;
- symbol, timeframe, broker, giờ server, quy đổi UTC/DST và session được phép;
- risk, spread, commission, slippage và giới hạn vận hành;
- vùng train, validation, OOS và final holdout;
- tham số nào được tối ưu, range, số trial và tiêu chí chọn;
- điều gì chứng minh setup sai.

Sau khi bắt đầu xem kết quả, mọi thay đổi logic phải thành revision mới. Không sửa ngược specification để hợp thức hóa một backtest.

## 2. Code đầy đủ đúng specification

EA đầu tiên phải là chiến lược hoàn chỉnh, không phải bản demo thiếu chức năng:

- entry, exit, risk, execution và lifecycle management đầy đủ;
- signal chỉ dùng thông tin có sẵn tại decision time; mặc định closed bar;
- warm-up thiếu, indicator lỗi hoặc dữ liệu thiếu thì không giao dịch;
- xử lý đúng tick size, tick value, volume step, stops level, freeze level và filling mode;
- log nối được signal → request → order → deal → position → exit reason;
- mỗi setup có tag; mỗi lệnh lưu indicator state, session và regime tại lúc ra quyết định.

## 3. Xác minh EA làm đúng điều đã viết

Trước khi đánh giá lợi nhuận:

1. Compile 0 error; warning phải được xử lý hoặc giải thích.
2. Chạy test logic, state recovery, risk sizing và broker geometry liên quan.
3. Audit lookahead/repaint và kiểm tra indicator ở nhiều mức warm-up.
4. Chạy lại cùng source/config/data để xác nhận kết quả tái lập.
5. Mở MT5 Visual Tester và kiểm tra trực tiếp signal, entry, SL/TP, exit và indicator trên chart.
6. Đối chiếu trade count, P&L và exit reason giữa report, deals và EA log.

Nếu EA chưa thực hiện đúng specification thì chỉ được sửa engineering; chưa được kết luận chiến lược thắng hay thua.

## 4. Baseline và phân tích từng giao dịch

Chạy baseline trên vùng train đã chốt, chưa tối ưu. Sau đó:

- xem mẫu lệnh thắng/thua, long/short và các session trên MT5 Visual Tester;
- phân tích theo setup tag, exit reason, symbol, giờ, volatility và regime;
- tìm nguyên nhân: signal, timing, structure, stop/target, cost hay execution;
- so sánh hành vi thực tế với giả thuyết ban đầu.

Kết quả có ba hướng: sửa lỗi implementation; thiết kế revision chiến lược mới; hoặc đưa setup hợp lý sang tối ưu. Quan sát sau backtest là đầu vào cho revision tiếp theo, không phải filter được phép gắn ngay vào kết quả cũ.

## 5. Tối ưu riêng từng symbol mà không overfit

- Mỗi symbol có parameter profile và timezone/session map riêng; không ép một bộ số dùng chung.
- Chỉ tối ưu các tham số đã khai báo và có ý nghĩa thị trường.
- Tối ưu trên train; validation, OOS và final holdout vẫn niêm phong.
- Chọn vùng tham số ổn định và lân cận cùng tốt, không chọn một đỉnh PF đơn lẻ.
- Ghi lại toàn bộ trial count, kể cả thử nghiệm thất bại.
- Kiểm tra độ bền khi dịch session, spread, slippage và tham số lân cận.
- Sau khi chọn profile, đóng băng config trước khi mở OOS.

## 6. Validation ngoài mẫu

Profile đóng băng phải được kiểm tra bằng:

- walk-forward với train/test theo thứ tự thời gian;
- OOS và final holdout chưa dùng để thiết kế;
- dynamic cost stress cho spread/commission/slippage;
- Monte Carlo trên thứ tự trade và execution degradation;
- breakdown theo năm, tháng, session, direction và regime;
- stability của vùng tham số, cadence và drawdown;
- DSR/PBO/CPCV khi số tham số và trial đủ lớn để cần kiểm soát selection bias.

Một symbol chỉ đạt nếu tự có expectancy dương sau cost và không phụ thuộc vào một giai đoạn, session hoặc bộ tham số mong manh.

## 7. Forward test và release

Chạy EA đóng băng trên demo/forward bằng cùng source và profile đã validate. Đối chiếu signal time, entry price, slippage, rejection, stop/target và P&L với giả định backtest.

Chỉ báo một trong ba trạng thái:

1. `engineering-valid`: EA thực hiện đúng specification.
2. `economic-valid`: edge còn dương ngoài mẫu sau cost.
3. `promotion-ready`: forward test, risk và execution đều đạt; Owner mới quyết định live.

## Bộ bằng chứng của mỗi run

Mỗi run giữ cùng một bundle: run ID, source hash, parameter file, data range/source, symbol properties, timezone map, MT5 build, report, deals, log, visual casebook và verdict. Bundle là nguồn sự thật; `hot.md` chỉ là con trỏ ngắn.

## Lệnh chuẩn

```powershell
./02. AlphaFactory/alpha.ps1 context
./02. AlphaFactory/alpha.ps1 status
./02. AlphaFactory/alpha.ps1 compile "<EA>"
./02. AlphaFactory/alpha.ps1 backtest "<EA>" -Symbol <SYMBOL> -Period <TF> -HypothesisId <ID>
./02. AlphaFactory/alpha.ps1 analyze -Report <REPORT_PATH>
./02. AlphaFactory/alpha.ps1 validate-full -Report <REPORT_PATH>
```

Nếu CLI thay đổi, `alpha.ps1 help` và source hiện tại thắng ví dụ trong tài liệu.

## Anti-setup guardrail

- Correctness và evidence integrity là gate, nhưng số hypothesis engineering không được coi là tiến bộ kinh tế.
- Sau source pass, đường mặc định là direct MQL5 parity rồi một baseline chưa tối ưu. Comparator/governance-only child chỉ được mở khi nó thực sự mở khóa evidence không thể thu lại rẻ hơn.
- Sau ba engineering revisions của cùng mechanism kể từ source pass, phải có opportunity-cost review độc lập trước revision tiếp theo.
- Nếu diagnostic cho thấy mechanism rất xa ngưỡng mà không có thesis causal mới, đóng exact lane; không cứu bằng filter, threshold, session hay parser/harness expansion.
- Mọi status update phải gắn nhãn rõ: `source/formula`, `implementation`, `economic evidence`, `validation` hoặc `governance only`.

## Vòng lặp Deep Research → EA → verdict

Mỗi vòng chỉ có một market mechanism active và đi theo thứ tự này:

Một deliverable có thể là một EA portfolio host với shared execution/risk engine
và các sleeve theo asset class. Không yêu cầu một signal rule phổ quát phải được
ép qua FX, XAU và BTC. Tuy nhiên mỗi sleeve vẫn là một hypothesis độc lập, phải
tự pass toàn bộ source/PIT, cost, engineering, economic và promotion gates; host
architecture hoặc pooled P&L không phải bằng chứng edge.

1. Dùng Deep Research hoặc nguồn sơ cấp để tìm một information mechanism mới;
   yêu cầu causal story, dữ liệu point-in-time, decision clock M5/M15, cost risk,
   falsifier và nguồn trực tiếp. Cho phép kết quả `NO_CANDIDATE`.
2. Main Agent audit nguồn và de-dup toàn cây EA theo alias, công thức, constants,
   default periods và event-timing signature. Grok không có authority mở lane.
3. Nếu data contract chưa chắc chắn, chỉ mở capability check không đọc outcome.
   Nếu contract fail, dừng lane trước hypothesis/source price scan.
4. Khi capability pass, đóng băng hypothesis ID, specification, population gate,
   symbol/timeframe, cost, train/validation/OOS/holdout, risk budget và cadence
   contract phù hợp mechanism. Không áp trần `5 lệnh/tuần` mặc định cho scalp.
5. Code đầy đủ EA/indicator thật sự cần thiết; chạy focused tests, compile 0/0,
   non-repaint, deterministic rerun, Visual Tester và log/parity checks.
6. Chạy đúng một baseline chưa tối ưu. Đọc manifest/DQ → summary/parity → PF,
   expectancy, executed cadence, native equity DD và direction/year gates.
7. Nếu baseline fail mà implementation đúng, KILL exact hypothesis. Mọi đổi market
   logic, session, threshold, direction, stop/target hay sizing là revision mới và
   quay lại bước 1/4; không vá vào readout cũ.
8. Chỉ baseline pass mới mở cost stress, optimization đã preregister, WFA,
   CPCV/PBO, DSR, Monte Carlo, OOS/holdout và cross-symbol falsification ở đúng
   phạm vi mà causal contract claim transfer; không ép transfer giả giữa asset
   classes chỉ để giữ một universal rule.
9. Trước khi đóng goal, tạo full-universe receipt 2018→latest cho XAUUSD, BTCUSD
   và bảy FX majors/liquid crosses đã khóa trong `01. GOAL/GOAL.md`; mỗi sleeve
   được verdict độc lập và không pool kết quả. Receipt có thể ghi FAIL,
   INACTIVE_NO_CAPABILITY hoặc PASS theo đúng bằng chứng; chỉ sleeve PASS mới
   được kích hoạt trong host.

Một vòng `NO_CANDIDATE`, source KILL hoặc economic KILL là thông tin nghiên cứu,
không phải DONE và cũng không phải lý do hạ goal. Vòng kế tiếp phải đổi information
mechanism, không chỉ đổi tên indicator hoặc điều chỉnh filter của family vừa fail.

## Nhịp làm việc và review chống chệch hướng

- Mặc định dùng dữ liệu native của MT5 demo/FivePercent/The5ers. Không chuyển
  sang nguồn trả phí khi một cơ chế dùng OHLC, tick volume, Bid/Ask, spread và
  commission có thể được kiểm tra trực tiếp trong Strategy Tester.
- Sau khi chọn một cơ chế materially fresh, giới hạn phần chọn/de-dup ở một lát
  làm việc ngắn, viết prereg đủ dùng và đi thẳng qua focused test → compile →
  non-repaint → baseline chưa tối ưu. Không biến source screen thành một dự án
  hạ tầng riêng nếu MT5 có thể falsify cơ chế rẻ hơn.
- Main Agent tự tính thời gian làm việc hữu ích. Sau khoảng 60 phút, hoặc trước
  engineering revision thứ ba của cùng cơ chế, gọi một sub-agent read-only để
  đối chiếu PF >1.30 sau phí, cadence đã preregister, sample adequacy,
  engineering/economic/promotion gates; chỉ ra setup detour, post-hoc decision
  và lỗi lặp lại.
- Review thủ công này không chạy theo lịch và không tự động ngắt công việc.
  Reviewer không sửa file, chạy MT5, đổi strategy hay tạo hypothesis. Main Agent
  chọn 1–3 hành động rút ngắn đường tới baseline/validation, áp dụng ít nhất một
  hành động ngay trong lát làm việc kế tiếp rồi tiếp tục.
- Hourly/checkpoint review mặc định là advisory, không phải ceremony. Tuy nhiên,
  nếu Main Agent đã giao reviewer nhiệm vụ đưa verdict trước một source scan,
  compile/run hay attempt one-shot cụ thể, attempt đó chưa được mở cho tới khi
  verdict quay lại. Trong lúc chờ vẫn tiếp tục de-dup, viết code và chạy unit
  test không tiêu attempt; không được vượt reviewer rồi hợp thức hóa sau.
- Ngay trước mỗi baseline, chạy preflight ngắn cho D0/journal schema và đối
  chiếu source counters với runtime counters dự kiến. Đây là kiểm tra sẵn sàng,
  không phải lý do mở thêm comparator hay governance child.
- Summary của EA phải có counter trực tiếp cho các signal bị chặn bởi risk
  lock/account lock và geometry/broker rejection. Mục tiêu là giải thích ngay
  chênh lệch `source → entry → trade`, không phải dựng thêm parser sau run.
- Cadence ở source chỉ là build gate. Cadence kinh tế phải tính trên các vị thế
  đã đóng sau toàn bộ safety/risk/geometry gate đã đóng băng. Nếu các gate đó
  làm cadence rơi dưới floor hoặc vượt cap/capacity đã preregister, không được
  bỏ hoặc nới chúng để cứu baseline; đóng exact hypothesis và chuyển sang
  information mechanism mới.
- Khi baseline thất bại, chỉ sửa implementation defect dưới cùng hypothesis.
  Mọi thay đổi market logic, session, direction, threshold, stop/target hoặc
  sizing sau readout phải thành revision/hypothesis mới và được đánh giá theo
  opportunity cost; không được dùng review như lý do cứu hậu nghiệm.
- Khi source counters, runtime counters và report trade count đã khớp nhưng PF
  hoặc expectancy fail, coi đó là economic KILL ngay. Không chạy thêm subgroup,
  visual casebook, optimizer hay cost stress để tìm một lát cắt thắng; dành ngân
  sách đó cho một information mechanism mới.
- Sau mỗi baseline, đọc theo thứ tự cố định: manifest/DQ → EA summary/parity →
  bảng gate PF, expectancy, cadence, DD, direction/year. Chỉ khi toàn bộ baseline
  gate pass mới mở breakdown weekday/session/regime. Thứ tự này ngăn diagnostic
  tự động biến thành filter hậu nghiệm.
- Risk gate dùng native Strategy Tester equity drawdown. Drawdown tái dựng từ
  closed trades hoặc balance trong enhanced summary chỉ là diagnostic; không
  được dùng thay native equity DD khi verdict nằm sát ngưỡng.

### Contract-equivalence trước source scan

- Trước analyzer/source-price scan, tạo một pre-hypothesis source-contract receipt
  nhỏ, ghi đúng URL/artifact, field cần dùng, PIT timestamp/revision semantics,
  công thức và quote/sign convention đầy đủ, availability trên MT5/FivePercent,
  cùng chữ ký de-dup toàn cây. Thiếu bất kỳ mục nào thì trả `NO_CANDIDATE` hoặc
  capability reject; không mở numerical claim, analyzer hay MQL5 để bù evidence.
- Trước khi viết analyzer, phải hoàn thành hai câu hỏi nhị phân: information set
  có materially khác failure family hiện hữu không, và decision/execution clock
  có trực tiếp phục vụ M5/M15 deliverable không. Nếu một câu trả lời là không,
  PARK ở prereg; không dùng code hay đổi timeframe để hợp thức hóa sau.
- Cơ chế phải trực tiếp phục vụ deliverable scalping M5/M15; lane H1-only bị
  loại trước code dù source density có thể đẹp.
- De-dup không dừng ở registry/failure catalog hay tên indicator hiển thị. Phải
  search toàn bộ `03. EA Developer` theo hypothesis aliases, formula constants,
  default periods/thresholds và event-timing signature; một đổi tên/seed/window
  không tạo information mechanism mới.
- Trước khi đóng băng row/coverage gates, dùng metadata-only capacity check để
  tính attainable DESIGN rows và aggregation completeness. Không đặt floor tùy
  ý theo tổng source rows có preload.
- Population gate phải dùng cùng timeframe, Friday/session exclusion,
  exact-next clock, deterministic cooldown/overlap và mọi eligibility không
  phụ thuộc outcome của EA dự kiến.
- Nếu source population và execution population không tương đương, dừng trước
  compile/MT5; không dùng engineering child để sửa một mismatch có thể phát
  hiện bằng checklist này.
