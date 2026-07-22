# Frozen preregistration - HYP-VRAS-EURUSD-M5-002

Status: FROZEN PRE-OUTCOME on 2026-07-22.

## Causal identity

HYP-002 is the mechanical execution successor to terminal HYP-001. It changes
only `OrderCheck()` handling for entry and safety exit: boolean `true` is a
successful preflight, while DONE/PLACED validation remains exclusively on
`OrderSend()` results. It also adds rejected-check diagnostics. No signal,
threshold, session, cost, risk, news, target, stop or data rule changes.

## Frozen contract

- `EURUSD / M5 / MT5 Model 0`, 2019.01.03-2022.12.31; 2023+ sealed.
- Primary tick-volume Welford VWAP/SD, London-local anchor and M15 bias.
- ADX(14) enter 25 / exit 19 / dwell 6; warmup 15; SD floor 0.30 ATR.
- Range RSI >25 / <75, 2SD bands; Trend confirmed five-bar AVWAP and 1.80R.
- Risk 0.25%; max spread 1.20 pip; K=8 target/cost; max 3 trades/day;
  daily loss 1.50%; account DD 6%; 20-bar maximum hold; news +/-45 minutes.
- Broker winter UTC+2 following US DST; independent EU/US local sessions.
- Magic 5600742; hypothesis ID `HYP-VRAS-EURUSD-M5-002`.
- Deposit 100,000 USD, leverage 1:100, spread=`current`, lifecycle-v3.
- Cost and news provenance remain diagnostic-only; `promotion_eligible=false`.

## Acceptance and terminal rules

- Tests pass; compile 0/0; exact-source non-repaint audit has zero findings;
  report/lifecycle/runmeta reconcile exactly.
- Minimum 350 trades, 2-5 trades per elapsed calendar week, diagnostic PF >=
  1.30 and max DD <=6%. These metrics cannot promote the EA while cost/news
  provenance is unverified.
- HYP-001 signal/cost rejection counts are context only and cannot be used to
  loosen any filter. No optimizer, sensitivity arm, post-result tuning or
  second HYP-002 run is authorized.
