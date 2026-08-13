# HYP-PVPR-EURUSD-M15-002 — economic failure

Verdict: `KILL_BASE_PF_EXPECTANCY_CADENCE_AND_EQUITY_DD_FAIL`.

## Engineering evidence

- Source HYP002 passed at 945 events, LONG/SHORT `457/488`, source cadence
  `2.5900548/week` and exact-next coverage `100%`.
- MQL5 source SHA256 `16FD5FB21509DE6CB3B51422A20A1B038990DE27D5A6675989E4783A8EB0AC56`;
  compile `0 errors / 0 warnings`; non-repaint V3 PASS.
- AlphaFactory run `20260811_164213`, EURUSD M15 Model 0, native current
  spread, USD 100,000 and leverage 1:100.
- DQ passed: History Quality `100%`, 198,837 bars, 197,193,858 ticks and
  untruncated journal.
- Runtime emitted exactly 945 unique signals with duplicate multiplicity two
  from tester/agent journal collection. Every signal timestamp, direction and
  integer point field matched the source ledger: zero parity errors.
- Runtime summary: raw `945`, LONG/SHORT `457/488`, entries `456`, risk-lock
  skips `489`, entry/geometry rejects `0/0`, runtime failure false and no open
  position at deinit. The source-to-entry reduction is the frozen safety lock,
  not an implementation mismatch.

## Economic evidence

- Closed trades: `456` (`216` LONG / `240` SHORT).
- Executed cadence: `1.2498042/week` over the frozen design interval — FAIL.
- Profit factor after report costs: `0.7138492` — FAIL versus `>1.30`.
- Expectancy: `-$17.4405/trade`; net profit `-$7,952.85` — FAIL.
- Win rate `35.7456%`; gross profit/loss `$19,839.66 / -$27,792.51`.
- Commission `-$1,833.40`; swap `$0.00`.
- Native Strategy Tester equity drawdown was `$8,014.98`, approximately
  `8.01498%` of the USD 100,000 initial deposit — FAIL versus `<=8%`.
  AlphaFactory's enhanced-summary `7.8564%` is a closed-trade/balance-derived
  drawdown and does not replace the native equity-DD promotion gate.
- Calendar-year counts `135/127/129/65` for 2016–2019; later signals were
  consumed by the frozen drawdown lock. Max-year share `29.6053%` and both
  direction shares pass.

## Failure radius

Kill only the exact prior-day M1 tick-volume profile / first M15 value-area
reentry with integer-point boundaries, one-bin structural stop, 1.50R target,
16-bar hold and frozen safety locks. Do not rescue by removing the drawdown
lock, filtering weekday/session/year/direction, changing profile bins/value
area, altering stop/target/hold/risk, or reading the breakdown as a selector.

Cost stress, optimization, validation, OOS, holdout and paper/live remain
closed. This failure does not cancel the overall EA goal; the next lane must use
a materially different information mechanism.

## Bound run artifacts

- Manifest SHA256 `4D9A52AAE5B8724783C6A4C0B187D2DE493D938EB50FE2F6B88CD355E3EF5E39`.
- Report SHA256 `C49A6CE9CB090D0A922E29B4F067A0FC00F8A2579E7B368AE114E112BA99210C`.
- Journal SHA256 `41D5D34E953593FDF8AF9F3731A377113CD233C1335F309AF6F7C10C22D0DB0C`.
- Enhanced summary SHA256 `F9616DAD9A78AC7492FB842D95AAB77FFD0BD1D3665597C5F501962D548E18DD`.
