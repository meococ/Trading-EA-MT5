# GOAL — Edge thực, kiểm chứng được

Trạng thái: **ACTIVE / UNMET** cho tới khi có ít nhất một symbol-sleeve đạt DONE.
Compile xanh, workflow xong, hay một frontier `NO_CANDIDATE` không phải DONE
và không biến cả goal thành `BLOCKED`.

Cơ chế active: **không** — `HYP-SONICR-CLASSIC-EURUSD-M15-001` KILL hẹp, train `20260816_205426` PF 0.94.
Không compile-from-archive. Không revive `EA_SonicR` v2 recovered / ITSM / HybridICT / Grok v10.
`HYP-H4-DONCHIAN-EURUSD-H4-001` KILL hẹp — train `20260816_151429` PF 0.89.
`HYP-H4-DONCHIAN-XAUUSD-H4-001` KILL hẹp — train `20260816_141128` PF 0.86.

## Scope

Universe: `XAUUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`,
`AUDUSD`, `NZDUSD`. BTC/crypto chỉ là lịch sử audit.

Timeframe: `M5`, `M15`, `H1`, `H4`, `D1` — chọn theo cơ chế, freeze trước
source/outcome. Không giữ qua cuối tuần. Overnight cần contract swap/cost/risk.

Native MT5 (OHLC, tick, Bid/Ask, spread, tick volume, symbol state) là nguồn
hợp lệ cho setup price-derived. Không bắt buộc source-intake/PIT ngoài MT5
chỉ để hợp thức hóa. External data chỉ khi cơ chế thật sự cần trường MT5 không có.

Spend/contact mặc định USD 0. Mọi purchase, trial, paid sample, credential hoặc
vendor contact chỉ được mở sau quyền Owner rõ ràng cho đúng object. Không live
vốn; paper/live chỉ Owner cấp.

## Outcome

Một EA XAU/Forex, expectancy dương sau cost thật, mẫu đủ ước lượng, ổn định
OOS, vận hành được trên MT5. Mỗi symbol tự pass; không pool P&L.

## Ngưỡng DONE

| Tiêu chí | Tối thiểu |
|---|---|
| Profit factor | > 1.30 sau cost x1 |
| Cadence | Freeze theo mechanism; đủ mẫu expectancy/DSR; không trần 5 lệnh/tuần mặc định |
| Cost stress | x1.5 PF ≥ 1.25; x2 PF ≥ 1.00 |
| History quality | Tester >97% |
| Evidence | 84 tháng / 7 năm khi lịch sử cho phép |
| Validation | Train và holdout độc lập; WFA, CPCV/PBO, DSR, Monte Carlo |
| Risk | MC P95 DD trong budget đã preregister |
| Exposure | Overnight theo contract; cấm weekend hold |

Một sleeve DONE khi đồng thời `engineering-valid`, `economic-valid`,
`promotion-ready`, và Owner quyết paper/live.

Stopping rules và vòng build: `05. Playbook/WORKFLOW.md`.

## Mandate ngắn

- KPI: thời gian tới baseline kinh tế chưa tối ưu, rồi validation.
- Ưu tiên indicator/hành vi chart hiểu được, không indicator-vote EA.
- Baseline thua: tối đa hai market-logic revision (ID mới, OOS kín) rồi KILL family hẹp.
- Reviewer 60 phút là advisory, không chặn compile. PASS/BLOCK chỉ khi Main đã ủy bước không hoàn nguyên.
- Grok/Deep Research là advisory. `NO_CANDIDATE` đóng đúng phạm vi đã tìm, không đóng goal.
- Claim cấp book: receipt 2018→latest từng symbol; multi-sleeve không phải edge.
- Không append checkpoint vào file này. Nhật ký: `INDEX.md` → GOAL checkpoint archive.
