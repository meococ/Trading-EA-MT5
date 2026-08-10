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
| Cadence | 2–5 executed trades/elapsed calendar week trên từng split của symbol được claim |
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
