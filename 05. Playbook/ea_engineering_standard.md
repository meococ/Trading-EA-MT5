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

## 2. Ownership và state machine

- Mọi order/position phải kiểm tra `symbol + magic + strategy identity`; không
  sửa/đóng lệnh ngoài quyền sở hữu.
- Khai báo rõ netting/hedging, max concurrent, same-symbol conflict và partial
  fill. Không giả định một ticket luôn bằng một position.
- State phải khôi phục được sau restart/recompile và xử lý event idempotent;
  không gửi lặp entry/close/partial/BE khi callback hoặc tick lặp.

## 3. Execution và broker geometry

- Dùng `CTrade` khi đủ; luôn kiểm retcode, order/deal ticket và broker response.
- Tôn trọng digits/point/tick size/tick value, min-max-step volume, stops/freeze,
  fill mode, session, trade mode, deviation và suffix symbol.
- Retry có giới hạn chỉ cho lỗi transient; không retry validation/margin/stops
  sai. Ghi timestamp UTC + server time và nêu contract DST/session.
- Sizing theo tiền ưu tiên `OrderCalcProfit/OrderCalcMargin`; normalize volume
  fail-closed. Không nới stop, grid, martingale, DCA hay average-down.

## 4. Risk hard gates

- Hard SL mặc định; risk/trade, daily loss, account DD, max concurrent, spread,
  session và emergency kill switch phải có contract rõ.
- Risk guard phải tính cả position/order đang mở và không reset sai sau restart.
- News guard bắt buộc fail-closed nếu lane yêu cầu calendar nhưng data thiếu.

## 5. Reproducibility và telemetry

- Compile/backtest qua AlphaFactory với hypothesis, symbol, TF, dates, Model và
  overrides tường minh; archive source không hợp lệ.
- Mọi run có ý nghĩa cần manifest, source/config/EX5/include hashes, task packet
  và receipt. Cost thiếu/0 không được diễn giải là zero cost.
- Package muốn chạy Model 0 nghiêm túc phải khai báo
  `ALPHAFACTORY_EA_CONTRACT.json` và emit lifecycle telemetry reconcile được với
  report; profile `none` không đủ cho research execution.
- Tối ưu hóa giảm log; control/forensics giữ evidence đầy đủ. `OnTester()` nếu có
  phải hướng tới robustness, không chỉ net profit.

## 6. Gate trước khi gọi “ready”

- Static + non-repaint audit xanh sau thay đổi signal/data.
- Test state/ownership/restart/partial-fill và broker geometry phù hợp.
- Compile có log 0 error và artifact mới.
- Matched control, cost, holdout/stability và validation vượt gate đã prereg.
- README, preset, repro/readout và giới hạn đã cập nhật.
- “Research pass” vẫn không đồng nghĩa deploy/live readiness.
