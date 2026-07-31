# MBP-1 SOURCE QUOTE PLAN - HYP-EURFXOFI-EURUSD-M1-004

Frozen on `2026-07-30` before any HYP004 vendor call. HYP003 closed only the
15-second MBP-10 geometry because its USD5.045364 quote exceeded the Owner's
USD2.25 total ceiling. No paid or price-data call occurred.

HYP004 changes the source information surface from ten-level depth to best-bid
and best-ask price/size updates (`mbp-1`). This supports causal top-of-book OFI
from signed queue changes, a narrower and materially cheaper mechanism rather
than a threshold rescue. It does not claim full-depth or EBS dealer flow.

- Parent signal ledger SHA256:
  `EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF`
- Population: 1,359 dates; TRAIN/VALIDATION/HOLDOUT = 630/526/203; all target
  outcomes remain sealed.
- Databento: `GLBX.MDP3`, schema `mbp-1`, continuous `6E.v.0`.
- Exact window per date: `[14:14:45,14:15:00) Europe/Berlin` using IANA DST.
- Free allowlist: `metadata.get_cost`, `metadata.get_billable_size` only.
- Required coverage: 1,359/1,359; duplicate, missing, negative/non-finite or
  hash drift fails closed.
- The Owner ceiling stays USD2.25 total across all successors. This quote is
  free. Paid acquisition requires a fresh successor bound to its exact receipt
  plus a live re-quote no greater than USD2.25.

Forbidden: MBP-10 fallback, window shortening, timeseries/batch/download,
price/depth decode, API-key persistence, outcome join, economics, MQL5,
Model 0, optimization, promotion, paper or live trading.
