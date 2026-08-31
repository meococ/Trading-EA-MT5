# WORKFLOW — Build EA có edge

Workflow này tối ưu cho một mục tiêu: biến một luận điểm giao dịch thành EA MT5
được kiểm chứng nhanh, trung thực và có khả năng triển khai. Artifact chỉ có giá
trị khi giúp code đúng, falsify nhanh hoặc chứng minh edge.

## 0. Operating contract

- Active universe: theo `01. GOAL/GOAL.md`.
- Timeframe: M5/M15/H1/H4/D1, chọn theo cơ chế; không giữ qua cuối tuần.
- Sản phẩm/acceptance: MQL5, MT5 Strategy Tester và AlphaFactory.
- Native MT5 data là hợp lệ. External data không phải điều kiện mặc định.
- Mỗi thời điểm chỉ một market mechanism active.
- Mỗi mechanism có tối đa baseline + hai market-logic revisions trước khi phải
  KILL hoặc vượt qua opportunity-cost review.
- OOS/final holdout luôn kín cho tới khi config được freeze.

## 1. Chọn cơ chế như trader

Trong một lát làm việc ngắn, chọn một setup có đủ:

- hành vi thị trường cụ thể: ai bị ép giao dịch, mất cân bằng nào tồn tại, hoặc
  trạng thái giá/volatility/liquidity nào tạo payoff bất đối xứng;
- điều kiện vào/thoát có thể code chính xác;
- holding horizon đủ dài so với complete execution cost;
- cadence và sample dự kiến đủ để đánh giá;
- failure condition rõ.

Được phép dùng price action, market structure, session behavior, indicator,
volatility/regime, tick/quote behavior hoặc external information. Không cần dựng
causal source ngoài MT5 chỉ để hợp thức hóa một setup price-derived.

Không dành nhiều vòng chỉ để tìm “candidate hoàn hảo”. Nếu một cơ chế hợp lý có
thể falsify rẻ bằng MT5, ưu tiên code và baseline.

## 2. Freeze minimal spec

Trước khi xem outcome, ghi một contract ngắn:

- hypothesis/revision ID;
- symbol, timeframe, broker/server clock và data range;
- exact decision time; closed-bar hoặc intrabar/tick semantics;
- entry, exit, stop/target/trailing/time exit;
- position sizing, exposure và safety locks;
- spread, commission, slippage và swap;
- train, validation, OOS, final holdout;
- parameters/ranges được phép nghiên cứu và tổng trial budget;
- điều kiện KILL/PASS.

Nếu dùng `FILE_COMMON`, bind basename + SHA256 và escrow vào run. Nếu dùng external
data, bind PIT/revision/live-equivalence. Nếu chỉ dùng MT5 native, không mở dự án
source-governance riêng.

## 3. Build production EA

EA baseline phải hoàn chỉnh, không phải signal demo:

- signal, entry, exit và position lifecycle;
- risk sizing theo tick size/value, volume step và currency conversion;
- stops/freeze/filling/market-hours/broker geometry;
- daily/weekly risk locks, Friday flat và restart-safe state;
- log nối signal → request → order → deal → position → exit;
- summary counters cho signal, risk skip, geometry reject, entry/exit reject;
- cùng source và logic cho tester, forward và live.

Closed bar là mặc định an toàn, không phải luật tuyệt đối. Intrabar/tick được phép
khi decision state causal, model/data phù hợp và tester-live parity được chứng minh.

## 4. Engineering gate

Trước khi đọc economics:

1. Compile qua `alpha.ps1`: log mới `0 errors, 0 warnings`, EX5 mới.
2. Chạy focused tests cho signal state, sizing, geometry, restart và risk locks.
3. Audit lookahead/repaint và warm-up/fail-closed behavior.
4. Chạy deterministic rerun khi mechanism cần.
5. Dùng Visual Tester/MT5 chart để kiểm tra trực tiếp một tập lệnh đại diện.
6. Reconcile source/signal/entry/trade/exit counts với log và report.

Chỉ sửa engineering defect dưới cùng revision. Không đổi market logic ở bước này.

## 5. Baseline chưa tối ưu

Chạy một baseline trên DESIGN/train đã khóa bằng Model 0 và realistic broker cost.
Đọc theo thứ tự:

1. run/data/history quality và runtime failures;
2. signal → trade parity, rejects và cadence;
3. chart của winner, loser, drawdown và recovery;
4. gross versus spread/commission/slippage/swap;
5. PF, expectancy, net, native equity DD;
6. long/short, year/period stability và concentration.

Không dừng ở một summary JSON. Lead phải phân tích chart và log như trader để biết
setup sai vì implementation, entry timing, exit geometry, cost hay thesis.

## 6. Revision có giới hạn

Baseline fail có ba hướng:

- `ENGINEERING_FIX`: implementation sai; sửa cùng revision và rerun hợp lệ.
- `MARKET_REVISION`: thesis vẫn hợp lý nhưng chart/log chỉ ra một defect cụ thể;
  tạo ID mới, freeze thay đổi trước run, giữ OOS kín.
- `KILL`: gross edge không tồn tại, cost geometry vô lý, behavior trái thesis,
  hoặc hai revision đã tiêu hết budget.

Được phép học từ diagnosis để thiết kế revision mới. Không được chọn subgroup thắng,
xóa năm thua, đảo direction tùy tiện, hay dùng OOS/holdout làm dữ liệu thiết kế.

## 7. Optimization đúng cách

Chỉ mở khi implementation đúng và baseline/revision cho thấy thesis còn giá trị.

- Tối ưu parameter đã khai báo trong fixed trial budget.
- Tìm plateau/region ổn định, không lấy đỉnh PF đơn lẻ.
- Mỗi symbol có profile riêng; không ép một bộ số chung.
- Tính toàn bộ trial debt và dùng DSR/PBO khi selection pressure đáng kể.
- Stress neighboring parameters, spread, commission, slippage, delay và session.
- Freeze config trước khi mở OOS.

Một raw baseline PF dưới ngưỡng không bắt buộc KILL nếu bounded research đã được
preregister và gross/cost/behavior còn hỗ trợ thesis. Nhưng không được tối ưu một
mapping không có gross information chỉ để tìm may mắn.

## 8. Validation (survivor)

Chỉ sau khi PF+cadence hứa hẹn. Không chạy `validate-full`, WFA, CPCV hay
`delivery` sau mọi backtest. Config freeze phải vượt:

- walk-forward theo thời gian;
- OOS và final holdout chưa dùng trong thiết kế;
- dynamic cost stress: x1, x1.5, x2;
- Monte Carlo trade order và execution degradation;
- CPCV/PBO/DSR khi phù hợp;
- parameter sensitivity và regime/year stability;
- native equity DD, time-under-water và recovery;
- capacity/correlation khi ghép nhiều sleeves.

Core economic target theo GOAL: PF >1.30 sau cost x1; x1.5 PF ≥1.25; x2 PF ≥1.00,
expectancy dương, đủ mẫu và risk nằm trong budget. Một exception chỉ được Owner
thay đổi trước holdout, không được nới sau kết quả.

## 9. Full-history và cross-symbol

Trước DONE:

- backtest 2016→nay khi broker có lịch sử (theo GOAL); muộn hơn thì ghi broker-limited;
- mỗi sleeve có report và verdict riêng;
- symbol không đủ history phải ghi `INACTIVE_NO_CAPABILITY`, không gọi PASS;
- không pool P&L để che sleeve thua;
- portfolio host chỉ kích hoạt sleeve tự pass engineering, economics và promotion.

Không bắt buộc một signal rule thắng trên mọi symbol. Một host có thể dùng nhiều
sleeves/cơ chế, nhưng mỗi sleeve phải tự chứng minh edge.

## 10. Forward và promotion

Chạy EA freeze trên demo/forward với cùng source/config. Reconcile signal time,
entry, spread/slippage, rejection, stop/target và P&L với backtest assumptions.

Trạng thái duy nhất được báo:

- `engineering-valid`: implementation đúng;
- `economic-valid`: expectancy/robustness sau cost đạt;
- `promotion-ready`: OOS/forward/risk/execution đạt;
- `live`: chỉ Owner cấp quyền.

## Nhịp làm việc

- Market work trước documentation. Viết contract ngắn trước run và result ngắn sau run.
- Không tạo thêm parser, comparator, source census hoặc governance child nếu chúng
  không mở khóa trực tiếp compile, baseline hoặc validation.
- Không dùng `NO_CANDIDATE`, dirty worktree, pending review hay thiếu tài liệu làm
  lý do đứng yên khi vẫn có một cơ chế MT5 hợp lệ để build/falsify.
- Sau mỗi vòng: giữ artifact, cập nhật đúng một verdict, rồi ngay lập tức chọn
  revision hợp lệ hoặc mechanism mới.

## Lệnh chuẩn

Mặc định: compile → backtest → analyze. Trade charts fail-open nếu harness đã có.
`validate-full` / `delivery` / WFA / CPCV chỉ khi survivor.

```powershell
& "./02. AlphaFactory/alpha.ps1" status
& "./02. AlphaFactory/alpha.ps1" compile "<EA>"
& "./02. AlphaFactory/alpha.ps1" backtest "<EA>" -Symbol <SYMBOL> -Period <TF> -HypothesisId <ID>
& "./02. AlphaFactory/alpha.ps1" analyze -Report "<REPORT_PATH>"
```

Survivor: `validate-full` / `delivery` — xem `alpha.ps1 help`.
Nếu CLI thay đổi, `alpha.ps1 help` thắng ví dụ trong tài liệu.
