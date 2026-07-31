# SOURCE QUOTE PLAN - HYP-EURFXOFI-EURUSD-M1-001

Frozen `2026-07-29`, before any CME 6E data purchase or order-book/outcome join.
This stage authorizes free Databento metadata quotes only. It does not reuse the
Owner's prior plan-specific USD ceiling and does not authorize a paid request.

## Fresh mechanism

The candidate changes the information set from retail close/VIX proxies to
primary CME Globex 6E depth immediately before the ECB fix. The intended future
signal is signed 10-level order-book/flow imbalance during the last 30 seconds
before `14:15 Europe/Berlin`, evaluated only on the 612 high-pressure dates
already selected by the frozen strict-lag rule in
`HYP-EURFXREV-EURUSD-M1-001`. Selection dates are reused without looking at or
filtering their post-fix outcomes.

Krohn, Mueller and Whelan attribute fix reversals to pre-fix order imbalance
and dealer inventory. CME 6E is a listed-futures proxy, not EBS cash-spot dealer
flow; any later claim must remain limited to that proxy.

## Frozen metadata request contract

- Dataset/schema/symbol: `GLBX.MDP3` / `mbp-10` / `6E.v.0`
- `stype_in=continuous`; cost mode `historical-streaming`
- Dates source ledger SHA256:
  `952E193FFC65D91B43E7F55EE970A65E904B2E9DD50A5E6469B9659EDFC28E45`
- Expected unique dates/requests: `612`
- For each date: `[14:14:30, 14:15:00)` in `Europe/Berlin`, converted to UTC
  with DST; exactly one 30-second request.
- Runtime: `02. AlphaFactory/runtime/python-databento/Scripts/python.exe` and
  `databento==0.54.0`.
- Remote allowlist: `metadata.get_cost`, `metadata.get_billable_size` only.
- Forbidden: `timeseries.get_range`, batch calls, download, target-return join,
  economic metric, MT5/MQL5, optimization, validation/holdout, paper/live.

The receipt must reconcile every request, total estimated USD and billable
bytes; counters must prove zero paid/timeseries calls and no API-key persistence.
Any missing quote, non-finite cost, negative size, date drift or output-root
collision fails closed.

## Decision

The free quote only sizes the next decision. A paid source acquisition requires
a fresh explicit Owner USD ceiling tied to the resulting quote/plan ID. Even a
source download would not authorize economics: an outcome-blind source-quality
stage must first prove coverage, causal feature construction and usable cadence.
