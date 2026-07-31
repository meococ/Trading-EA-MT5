# HYP-VRAS-EURUSD-M5-013 — Frozen UTC-normalized collection successor

## Identity and sole change

- Fresh ID: `HYP-VRAS-EURUSD-M5-013`.
- Administrative parent: HYP-012, parked after its only read-only feed smoke
  proved raw broker tick epoch was mislabeled UTC by +10,800 seconds.
- HYP-012 opened no arm, acceptance outcome, trade, PnL or return.
- Package remains `EA_VRAS_QuoteTickAcceptance`, EURUSD M5, collection-only.
- Every HYP-012 arm and acceptance rule is unchanged: H1 EMA200 shift 1,
  rolling completed-M5 VWAP48, 60/30 pre-arm spreads, 30–120 seconds,
  20 quotes, 12 price changes, 0.60 directional imbalance, one-arm-spread net
  expansion, current spread <= median, max spread ratio 1.50, max gap 15 seconds
  and strict frozen-VWAP no-touch/recross.
- The sole mechanism/data change is explicit broker-server-to-UTC clock
  normalization plus absolute capture-clock validation.
- No orders, account-history reads, SL/TP, sizing, PnL, optimization, economic
  backtest, Model-0 performance claim, promotion or live trading is authorized.

HYP-012's frozen plan remains normative for the signal/FSM/telemetry fields;
this file replaces only hypothesis identity and clock semantics.

## MQL5 clock contract

For every `MqlTick`:

1. read raw broker `tick.time_msc`;
2. compute `server_utc_offset_ms = (TimeCurrent() - TimeGMT()) * 1000`;
3. compute `utc_time_msc = tick.time_msc - server_utc_offset_ms`;
4. use normalized UTC milliseconds for deduplication, arm age, interquote gaps,
   `event_time_msc`, `arm_time_msc` and ISO-8601 `event_time_utc`;
5. fail closed if normalized time is non-positive or non-monotonic;
6. tester offset is expected to be zero; data source remains explicitly
   `SYNTHETIC_TESTER_TICKS` and has no economic authority.

The constant offset cancels within an active <=120-second arm. If the terminal
offset changes, normalized time must remain strictly monotonic or the arm ends
`REJECT_INVALID_QUOTE`.

## Python broker-feed clock contract

The first fresh EURUSD quote freezes one capture offset:

1. `delta_ms = raw_tick_time_msc - receipt_utc_time_msc`;
2. `offset_ms = round(delta_ms / 900000) * 900000` (15-minute timezone grid);
3. require `abs(delta_ms - offset_ms) <= 30000`, otherwise abort before writing
   quote rows;
4. require `abs(offset_ms) <= 14 hours`;
5. write normalized `time_msc = raw_time_msc - offset_ms` and derive
   `time_utc` from normalized milliseconds;
6. record `observed_tick_clock_offset_seconds` in session and manifest metadata;
7. `--skip-account-history` remains mandatory for HYP-013 smoke/collection.

The bundle validator must fail if the final normalized quote timestamp is more
than 1,000 ms in the future relative to manifest `created_at_utc`.

## Engineering gates

1. Frozen HYP-012 FSM tests plus UTC clock fixtures pass.
2. Static source has no trade APIs, account-history reads or shared-files flag.
3. Canonical compile 0 errors / 0 warnings.
4. Exact-source non-repaint PASS; causal post-arm ticks remain intentional.
5. One corrected, EURUSD-only, quote-only, read-only broker smoke of exactly
   120 seconds is authorized. No cron or unattended continuation.
6. Smoke must show exact server match, normalized quote timestamps not future
   to manifest, monotonic unique rows, valid bid/ask, hash/row reconciliation,
   account history skipped and safety receipt 0 orders / 0 positions.
7. Smoke can prove only collection plumbing. `STOP_DATA_FRONTIER` is expected
   until a separately authorized forward corpus reaches its elapsed-time gate.

## Outcome boundary

No historical 2018-present backtest can validate causal quote imbalance without
the original chronological bid/ask feed. No PnL join is allowed under HYP-013.
A future economic matched pair requires a fresh preregistration after a forward
corpus exists; DD blocking must remain bypassed only as an explicitly measured
tester diagnostic, as requested by the Owner.

