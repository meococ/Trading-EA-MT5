# GOAL — Deploy Sonic R, từng sleeve tự pass

Trạng thái: **ACTIVE / UNMET**. Owner 2026-08-16: Deploy Sonic R bằng vòng
nghiên cứu–code–backtest–log/chart liên tục. Main tự quyết tài liệu và hướng kỹ thuật.

Cơ chế active: cần object mới. EUR PULL-001 KILL `20260817_014610`
N=67 PF 0.85. EUR Classic 001 KILL. Vàng Classic/BAND KILL; PULL PARK
cadence. H4 PARK (QC xác nhận 0.06/tuần).

## Scope

Universe: `XAUUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`,
`AUDUSD`, `NZDUSD`, và `BTCUSD` (Owner mở). Mỗi symbol một setup riêng;
không copy parameter; không pool P&L.

Timeframe: `M15` mặc định Sonic; `H1` chỉ khi cặp buộc. Không weekend hold.

Native MT5 hợp lệ. Spend/contact USD 0 trừ Owner mở đúng object. Không live
vốn; paper/live chỉ Owner cấp.

## Outcome

Một EA Sonic R (indicator + kỷ luật + tín hiệu) vận hành tester→forward.
Mỗi cặp 1–3 lệnh/tuần, PF > 1.30 sau cost, cửa sổ 2016→nay khi lịch sử cho phép.

## Ngưỡng DONE (từng sleeve)

| Tiêu chí | Tối thiểu |
|---|---|
| Profit factor | > 1.30 sau cost x1 |
| Cadence | 1–3 lệnh/tuần trên đúng symbol |
| Cost stress | x1.5 PF ≥ 1.25; x2 PF ≥ 1.00 |
| History quality | Tester >97% |
| Evidence | 2016→cutoff khi broker có; nếu muộn hơn thì ghi broker-limited, vẫn chạy |
| Validation | Train độc lập; OOS/holdout kín đến khi freeze config |
| Risk | MC P95 DD trong budget đã preregister |
| Exposure | Overnight theo contract; cấm weekend hold |

`engineering-valid` ≠ `economic-valid` ≠ `promotion-ready`.

## Mandate

- KPI: thời gian tới baseline kinh tế hợp lệ từng cặp, rồi validation.
- Đội ngũ: Main quyết; QC phản biện mỗi compile/backtest; không salvage năm/giờ.
- EUR Classic `001` không rerun. ITSM / Hybrid / v10 / archive không revive.
- BTC là sleeve riêng, không lấy rule vàng/FX.
- Không append checkpoint vào file này.
