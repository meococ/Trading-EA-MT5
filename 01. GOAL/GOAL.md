# GOAL — Edge thực, kiểm chứng được

Trạng thái: **ACTIVE / UNMET** cho tới khi có ít nhất một symbol-sleeve đạt DONE. Một thử nghiệm thất bại, compile xanh hoặc workflow hoàn tất không phải DONE.

## Outcome

Tạo ít nhất một chiến lược scalping M5/M15 có expectancy dương sau chi phí thật, cadence đủ giao dịch, ổn định ngoài mẫu và có thể vận hành an toàn trên MT5.

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
