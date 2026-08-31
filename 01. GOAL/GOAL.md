# GOAL — EA XAU + FX, từng sleeve tự pass

Trạng thái: **ACTIVE / UNMET**. Owner 2026-08-25: phát triển EA chạy XAU và
forex; tester → demo; loop research–code–backtest–log/chart và tự cải thiện
sau mỗi vòng. Main tự quyết cơ chế, TF, risk và thứ tự thử.

## Outcome

Một EA MT5 (tín hiệu + kỷ luật + risk) vận hành Strategy Tester rồi tài khoản
demo. Mỗi cặp **tự pass**, không pool P&L:

- PF > 1.30 sau phí (cost x1)
- khoảng **2–5 lệnh/tuần** trên đúng symbol
- né cửa tin tức
- không giữ qua tuần
- hạn chế overnight
- cấm overfitting

## Scope

Universe: `XAUUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`,
`AUDUSD`, `NZDUSD`. Mỗi symbol một setup riêng; không copy parameter.

Timeframe: `M5`, `M15`, `H1`, `H4`, `D1` theo cơ chế.

Native MT5 hợp lệ. Demo được phép. Live vốn chỉ Owner cấp. Spend/contact
USD 0 trừ Owner mở đúng object.

Host compile: `EA_SonicR_PVSRA`. Không compile `EA_SonicR` classic /
`00. Old File/`.

## Ngưỡng DONE (từng sleeve)

| Tiêu chí | Tối thiểu |
|---|---|
| Profit factor | > 1.30 sau cost x1 |
| Cadence | 2–5 lệnh/tuần trên đúng symbol |
| Cost stress | x1.5 PF ≥ 1.25; x2 PF ≥ 1.00 |
| History quality | Tester >97% |
| Evidence | 2016→cutoff khi broker có; nếu muộn hơn thì ghi broker-limited, vẫn chạy |
| Validation | Train độc lập; OOS/holdout kín đến khi freeze config |
| Risk | MC P95 DD trong budget đã preregister |
| Exposure | Overnight hạn chế theo contract; cấm weekend hold; né tin tức |
| Overfitting | Không salvage năm/giờ/subgroup; không đọc holdout rồi sửa; không tối ưu trước baseline đúng |

`engineering-valid` ≠ `economic-valid` ≠ `promotion-ready` ≠ `demo-ready`.

## Mandate

- KPI: thời gian tới baseline kinh tế hợp lệ từng cặp, rồi validation, rồi demo.
- Một cơ chế active. Baseline + tối đa hai market-logic revision rồi KILL hẹp.
- Sau mỗi vòng: forensic, rồi engineering-fix / revision / cơ chế mới.
- EUR Classic `001` không rerun. ITSM / Hybrid / v10 / archive không revive.
- Không append checkpoint vào file này.
