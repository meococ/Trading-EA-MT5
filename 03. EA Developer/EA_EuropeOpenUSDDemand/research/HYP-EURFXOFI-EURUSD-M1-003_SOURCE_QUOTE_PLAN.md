# SOURCE QUOTE PLAN - HYP-EURFXOFI-EURUSD-M1-003

Frozen on `2026-07-30` before any HYP003 Databento call. This source-only
successor consumes the outcome-blind 1,359-date ledger created by HYP002 and
authorizes one free metadata quote. It authorizes no paid request.

- Parent ledger SHA256:
  `EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF`
- Parent receipt SHA256:
  `002601D91057392BAD61B0868E235F5D76918F7C92FEFE98C231AC71547B6398`
- Population: 630 TRAIN (2016-2020), 526 VALIDATION (2021-2024), 203
  HOLDOUT (2025-2026-07-29), all target returns sealed.
- Dataset/schema/symbol: `GLBX.MDP3` / `mbp-10` / `6E.v.0`, continuous.
- Each request is exactly `[14:14:45,14:15:00) Europe/Berlin`, converted to
  UTC with IANA DST. The 15-second scientific floor may not be shortened.
- Allowlist: `metadata.get_cost`, `metadata.get_billable_size` only, through
  the D-side `databento==0.54.0` runtime.
- Required quote coverage: 1,359/1,359 unique windows. Missing, duplicate,
  negative/non-finite quote or hash drift fails closed.
- Owner ceiling: USD 2.25 total across HYP001-HYP003 successors, not per ID.
  This free quote does not spend it. If the quote exceeds USD 2.25, paid work
  stops. If it fits, a fresh paid-acquisition successor must still bind the
  exact receipt and live-requote all windows before its first charged call.

Forbidden: timeseries/batch/download calls, price/depth decoding, API-key
persistence, target-return access, economics, MQL5, Model 0, optimization,
validation/holdout economics, promotion, paper or live trading.
