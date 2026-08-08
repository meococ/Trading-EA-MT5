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
./02. AlphaFactory/alpha.ps1 status
./02. AlphaFactory/alpha.ps1 compile "<EA>"
./02. AlphaFactory/alpha.ps1 backtest "<EA>" -Symbol <SYMBOL> -Period <TF> -HypothesisId <ID>
./02. AlphaFactory/alpha.ps1 analyze -Report <REPORT_PATH>
./02. AlphaFactory/alpha.ps1 validate-full -Report <REPORT_PATH>
```

Nếu CLI thay đổi, `alpha.ps1 help` và source hiện tại thắng ví dụ trong tài liệu.
