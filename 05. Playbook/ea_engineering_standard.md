# Chuẩn Engineering EA

Cập nhật: 2026-07-16. Golden path đầy đủ: `ea_golden_path.md`.

## 1. Kiến trúc và data contract

- Tách signal, risk, execution, ownership/state và telemetry; strategy thay được
  mà không làm yếu risk/execution.
- Module signal chỉ tiêu thụ context bar đã đóng. `CopyRates/CopyBuffer` cho
  quyết định phải bắt đầu từ `shift >= 1`; `iTime(...,0)` chỉ dùng gate bar mới.
- Không có ngoại lệ live-bar cho signal. Tick chỉ phục vụ quote, gửi lệnh và
  quản trị position đã tồn tại.
- Guard insufficient bars, stale handle, buffer rỗng và alignment MTF.
- Tách rõ lifecycle `formation candidate → retest/response → entry-ready`.
  Confirmation hậu formation không được suy ngay tại close tạo FVG/zone.

## 2. Ownership và state machine

- Mọi order/position phải kiểm tra `symbol + magic + strategy identity`; không
  sửa/đóng lệnh ngoài quyền sở hữu.
- Khai báo rõ netting/hedging, max concurrent, same-symbol conflict và partial
  fill. Không giả định một ticket luôn bằng một position.
- State phải khôi phục được sau restart/recompile và xử lý event idempotent;
  không gửi lặp entry/close/partial/BE khi callback hoặc tick lặp.
- `PositionsTotal/OrdersTotal/HistoryDealsTotal` không chứng minh traversal đã
  thành công. Ticket bằng 0 hoặc select lỗi ở bất kỳ record nào phải làm scan
  fail-closed; không được diễn giải thành “không có exposure/history”.

## 3. Execution và broker geometry

- Dùng `CTrade` khi đủ; luôn kiểm retcode, order/deal ticket và broker response.
- Tôn trọng digits/point/tick size/tick value, min-max-step volume, stops/freeze,
  fill mode, session, trade mode, deviation và suffix symbol.
- Retry có giới hạn chỉ cho lỗi transient; không retry validation/margin/stops
  sai. Ghi timestamp UTC + server time và nêu contract DST/session.
- Sizing theo tiền ưu tiên `OrderCalcProfit/OrderCalcMargin`; normalize volume
  fail-closed. Không nới stop, grid, martingale, DCA hay average-down.
- Tách spread gate khỏi order deviation: spread kiểm chi phí thị trường hiện
  tại, deviation chỉ là slippage budget đã khai báo.
- Sau fill phải tính lại money-risk từ entry/SL/volume thật cộng execution cost.
  Nếu vượt budget đã đóng băng, quản trị/đóng khẩn ngay trong event hiện tại,
  không chờ tick sau và không giữ risk ước lượng pre-send làm sự thật.

## 4. Risk hard gates

- Hard SL mặc định; risk/trade, daily loss, account DD, max concurrent, spread,
  session và emergency kill switch phải có contract rõ.
- Risk guard phải tính cả position/order đang mở và không reset sai sau restart.
- News guard bắt buộc fail-closed nếu lane yêu cầu calendar nhưng data thiếu.
- Một persistence branch chỉ được tuyên bố bảo vệ restart khi execution authority
  thật sự có thể đi vào branch đó và có runtime test. Branch non-tester nằm sau
  contract tester-only phải được ghi rõ `dormant`, không tính là protection.

## 5. Reproducibility và telemetry

- Compile/backtest qua AlphaFactory với hypothesis, symbol, TF, dates, Model và
  overrides tường minh; archive source không hợp lệ.
- Mọi run có ý nghĩa cần manifest, source/config/EX5/include hashes, task packet
  và receipt. Cost thiếu/0 không được diễn giải là zero cost.
- Tester override phải serialize theo type: numeric/bool dùng optimization
  tuple, MQL5 `input string` dùng plain `key=value`. Sidecar thiếu sau report
  ready vẫn là run invalid; kiểm tester log/OnInit trước khi sửa EA.
- Với casebook/telemetry dùng cho label, exact source SHA và contract id phải
  hiện diện trong manifest + meta + từng row; header phải đủ taxonomy đã freeze.
  Analyzer/extractor phải version cùng schema và fail khi thiếu/mismatch.
- Package muốn chạy Model 0 nghiêm túc phải khai báo
  `ALPHAFACTORY_EA_CONTRACT.json` và emit lifecycle telemetry reconcile được với
  report; profile `none` không đủ cho research execution.
- Tối ưu hóa giảm log; control/forensics giữ evidence đầy đủ. `OnTester()` nếu có
  nên ưu tiên robustness hơn net profit đơn thuần; khai tiêu chí robustness trong readout/plan.
- Collector/alert-first phải default non-mutating; nếu có execution kernel thì
  mutation chỉ được mở theo authority tường minh và không được lẫn vào profile
  thu data. Casebook row/meta bind source SHA, schema/contract, event id, input
  identity, server+UTC cutoff; label và outcome để blank trong source corpus.
- Mọi bridge/extractor MTF phải dùng đúng broker server-time axis, normalize
  offset đã bind và test rằng bar cuối đóng không muộn hơn decision cutoff.

## 6. Gate trước khi gọi “ready”

- Static + non-repaint audit xanh sau thay đổi signal/data.
- Matrix requirement→code không còn hard gate `missing|contradictory` nếu claim
  là full-memo test; nếu còn thì chỉ được gọi đúng tên proxy/alert kernel.
- Test state/ownership/restart/partial-fill và broker geometry phù hợp.
- Compile có log 0 error và artifact mới.
- Matched control, cost, holdout/stability và validation vượt gate đã prereg.
- README, preset, repro/readout và giới hạn đã cập nhật.
- “Research pass” vẫn không đồng nghĩa deploy/live readiness.
- Zero-trade data acquisition chỉ được gọi ready cho collection contract; WR,
  PF, expectancy và promotion đều không xác định/không được phép.
