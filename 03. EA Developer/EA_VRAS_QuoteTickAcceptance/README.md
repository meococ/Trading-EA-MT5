# EA_VRAS_QuoteTickAcceptance

**Chỉ thu thập forward (collection-only)** — không phải EA sinh lời, không ready
live/promote, không có lệnh giao dịch.

## Mục đích

Lane `HYP-VRAS-EURUSD-M5-014`: quan sát quote tick nhân quả sau arm closed-bar
EURUSD M5 (H1 EMA200 + VWAP48). Ghi telemetry CSV để kiểm chứng kỹ thuật FSM
chấp nhận quote; **không** có `OrderSend` / SL / TP / sizing / PnL.

## Ranh giới

- `promotion_eligible` luôn `false`.
- Ngoài tester: `data_source=LIVE_QUOTES`. Trong tester: `SYNTHETIC_TESTER_TICKS`.
- Tick broker được chuẩn hóa về UTC bằng chênh lệch `TimeCurrent-TimeGMT`;
  clock không đơn điệu thì fail-closed.
- Không FILE_COMMON; CSV run-unique trong MQL5 Files local.
- Contract package: `telemetry_profile=none`, adapter so sánh generic.

## Nguồn

- Plan hiện hành: `research/HYP-VRAS-EURUSD-M5-014_FROZEN_UNIQUE_TICK_PLAN.md`
- HYP-012 đã park ở raw-clock contract; HYP-013 đã park ở duplicate-coordinate;
  cả hai không rerun. HYP-014 chỉ PASS feed plumbing và dừng ở data frontier.
- MQL5: `EA_VRAS_QuoteTickAcceptance.mq5`
- Reference Python: `research/quote_acceptance_reference.py`
- Tests: `tests/`

Owner/parent sở hữu compile, non-repaint audit và smoke; builder chỉ giao source
+ reference + contract tests.
