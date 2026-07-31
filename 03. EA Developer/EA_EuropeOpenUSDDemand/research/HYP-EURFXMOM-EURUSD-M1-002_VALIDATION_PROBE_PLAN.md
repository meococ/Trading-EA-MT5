# VALIDATION PROBE PLAN - HYP-EURFXMOM-EURUSD-M1-002

Frozen on `2026-07-30` after HYP-EURFXMOM-EURUSD-M1-001 was parked before
sentinel arming, evidence creation or validation access because its final
armed-state test binding required an append-only fresh ID. HYP001 opened zero
2021-2024 or holdout outcomes. HYP002 preserves its mechanism, population,
entry, exit, costs, gates and charts exactly. The economic lineage begins after
HYP016 completed its one-shot 2016-2020 TRAIN evaluation. HYP016 killed its final-15-second CME 6E flow-reversal primary, but
the separately preregistered `PRESSURE_CONTINUATION_CONTROL` returned PF x1
`4.31516762664312`, x1 expectancy `7.383881578947443` pips and positive x1 PnL
in all five TRAIN years. Those TRAIN outcomes are discovery evidence only and
cannot be reused as confirmation. This new mechanism ID freezes the control as
the primary before any 2021-2024 target return is opened.

Discovery evidence is bound to HYP016 terminal SHA
`3E351BA4C03C2E08312D9D0CF099610DC847BCCF9A90B1401476C8EE36FB3BD2`
and trade-ledger SHA
`B46A3A3B18F354F2F5F72D74E59C909BDBCCE4F66E0752C98AF6E84C8A05BDF0`.

## Mechanism and falsifiable claim

A sufficiently large directional EURUSD move from the early European session
into the ECB reference-rate observation window may persist after 14:15 Europe/
Berlin because information and inventory adjustment are not completed at the
fix. On previously unseen 2021-2024 data, continuing the sign of the completed
07:59-to-14:14 move through 15:59 must remain profitable after fixed round-turn
costs. The final CME 6E flow feature is not used by this mechanism.

## Frozen population and information boundary

- Confirmation split: `2021-01-01` through `2024-12-31` only.
- Holdout: `2025-01-01` onward remains return-sealed.
- Signal-date ledger: HYP002 `signal_dates.jsonl`, SHA
  `EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF`.
- Exact validation population in that outcome-blind ledger: 526 selected dates,
  from `2021-01-04` through `2024-12-27`.
- Eligibility is unchanged: absolute EURUSD 07:59-to-14:14 completed-Bid move
  at least the strict-lag median absolute move of the prior 60 complete
  weekdays, minimum 40 observations. The current day is excluded from its own
  threshold.
- Primary direction: `sign(close_14:14 - close_07:59)`.
- Decision and entry proxy: completed 14:14 Europe/Berlin Bid close, observable
  at 14:15. Exit: completed 15:59 Bid close, observable at 16:00.
- One trade per selected weekday. No stop, target, trailing, magnitude bucket,
  weekday/month filter or flow threshold.
- Target source: `EURUSD_M1_2015_now.parquet`, SHA
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`;
  manifest SHA
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`.
  The evaluator must project only `time_utc` and `close`, filter before loading
  to the 2021-2024 validation interval, and fail if any loaded timestamp leaves
  that interval.
- All 526 selected validation dates must have both exact target boundaries.
  Any missing or duplicate boundary is fatal engineering/data invalidity, not
  a no-edge result.

## Frozen arms, costs and gates

Exactly two arms are allowed:

1. `PRESSURE_CONTINUATION_PRIMARY`: direction with pre-fix pressure.
2. `PRESSURE_REVERSAL_CONTROL`: exact opposite direction.

Both use fixed round-turn cost x1/x1.5/x2 = `1.50/2.25/3.00` pips. Cost fields
are never interpreted as actual zero. The primary must pass every gate:

- exact 526 trades and cadence between 2 and 3 trades per elapsed calendar week;
- both LONG and SHORT share at least 25%;
- PF x1 >= 1.30, PF x1.5 >= 1.25 and PF x2 >= 1.00;
- x1 expectancy > 0 pips;
- at least 3 of 4 calendar years positive at x1;
- leave-one-year-out PF x1 > 1.00 for every omitted year;
- one-sided sign-flip p <= 0.05 on primary x1 net PnL with 10,000 draws and
  seed `20260730`;
- deflated Sharpe probability >= 0.95 using the already frozen 16-arm HYP016
  discovery universe and its variance of Sharpe trials;
- no single year contributes more than 35% of total positive x1 PnL.

The evaluator must render cumulative gross/x1/x1.5/x2 PnL with x1 drawdown,
annual PF/expectancy/PnL, discovery-versus-validation and reverse-control
comparison, monthly stability, and direction/return/funnel distributions. No
chart may create a new trading rule.

## Decision and authority

Any gate failure kills exactly this price-pressure continuation mechanism on
the 2021-2024 validation contract. No threshold, time, cost, exit, calendar or
direction rescue is allowed from the readout. A full PASS may authorize only a
fresh 2025-current holdout/source successor. It does not authorize MQL5, MT5,
Model 0, optimization, promotion, paper or live trading. This plan alone grants
no run authority; exact evaluator/test/receipt hashes and an absent one-shot
evidence root must be recorded in the candidate registry first.

