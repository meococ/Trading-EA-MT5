# TRAIN ECONOMIC PROBE PLAN — HYP-EURFXIMM-EURUSD-M1-001

Frozen on `2026-07-30` before reading any EURUSD 14:15-to-14:20 TRAIN target.
This is a fresh target-horizon mechanism, not a rescue of HYP016 or
HYP-EURFXMOM-005. Those hypotheses tested a 105-minute post-fix holding period;
this object tests whether final-15-second CME 6E aggressive flow has lagged
short-horizon price impact after a conservative one-completed-M1 execution lag.

## Mechanism and independent anchor

- Cont, Kukanov and Stoikov, *The Price Impact of Order Book Events* (2014):
  short-interval price changes are primarily related to order-flow imbalance.
  Source: `https://arxiv.org/abs/1011.6402`.
- Ito and Hashimoto, *Price Impacts of Deals and Predictability of the Exchange
  Rate Movements* (NBER w12682): FX order flow predicts the next one and five
  minutes, while significance disappears at 30 minutes. Source:
  `https://www.nber.org/papers/w12682`.

The anchor was recorded before the target was opened. It supports one primary
five-minute continuation horizon; it does not authorize a horizon grid.

## Frozen data and split

- Symbol/target: FivePercent completed-Bid `EURUSD M1` closes.
- TRAIN only: `2016-01-01` through `2020-12-31`.
- Source feature: HYP013 final-15-second CME 6E TBBO `flow_signed`, indexed by
  `ts_recv`, SHA256
  `EB26ABA7B294BF6F3408D97E9D8B5A1E1ABDD5A5BB5A66842CEEA63E4D7DF13C`.
- Source summary SHA256:
  `14FAC1FB640D449AA08A93C3603CDDDB46F1DFC81229F0A6EAC6DB2CEC6FFE2C`.
- Source artifact-manifest SHA256:
  `8C008C0C929F6A9BF03248DB9D68C5FF5692D74CEA7B24845E42310C2C0B8258`.
- Frozen high-pressure date ledger SHA256:
  `EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF`.
- Target parquet SHA256:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`.
- Target manifest SHA256:
  `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`.
- Validation `2021-2024` and holdout `2025-current` remain sealed. The
  evaluator must filter the parquet to TRAIN before target projection.

## Frozen population, signal and timing

1. Start with exactly the 630 HYP002 TRAIN dates selected outcome-blind by
   absolute 07:59-to-14:14 Europe/Berlin price pressure at least the strict-lag
   median of the prior 60 complete weekdays with minimum 40 observations.
2. Source-empty or zero/undefined `flow_signed` dates are explicit no-trades.
3. The previously documented target-unavailable date `2017-09-28` is the only
   allowed missing target date. Any other missing entry/exit boundary is fatal.
4. Signal direction is `sign(flow_signed)`; positive CME EUR flow buys EURUSD,
   negative flow sells EURUSD.
5. Signal window ends at `14:15:00 Europe/Berlin`. To enforce closed-bar and
   latency discipline, entry is the completed `14:15` M1 close, observable at
   `14:16`; exit is the completed `14:20` M1 close, observable at `14:21`.
6. One trade per eligible date. No stop, take-profit, intrabar path, sizing,
   calendar, news, weekday, month, year, regime, magnitude or spread filter.
7. Expected executable population is exactly 608 trades: 630 selected dates,
   seven source-empty dates, fourteen additional zero-flow dates, and the one
   frozen target-unavailable date. Population mismatch is engineering-invalid,
   not no-edge.

## Predeclared arms, costs and trials

Four arms use the same raw five-minute return:

1. `flow_continuation_primary = sign(flow_signed)`.
2. `flow_reversal_control = -sign(flow_signed)`.
3. `pressure_continuation_control = sign(pre_fix_pressure_pips)`.
4. `pressure_reversal_control = -sign(pre_fix_pressure_pips)`.

Round-trip costs are fixed at `1.50`, `2.25` and `3.00` pips (`x1`, `x1.5`,
`x2`). DSR uses the 16 already tried x1 arms (the six historical matched pairs
plus all four HYP016 arms) and these four new arms: exactly 20 trials. The
primary one-sided sign-flip test uses 10,000 permutations and seed `20260730`.

## Frozen gates

Structural gates, all required:

- exact 630-date source population and exactly 608 trades;
- only `2017-09-28` missing the target boundaries;
- cadence between 2 and 5 trades per elapsed calendar week;
- LONG and SHORT each at least 25%;
- exact signal, entry, exit and cost rule.

Economic gates, all required:

- primary PF `x1 >= 1.30`, `x1.5 >= 1.25`, `x2 >= 1.00`;
- primary expectancy at x1 greater than zero;
- at least four of five TRAIN years positive at x1;
- every leave-one-year-out x1 PF greater than 1;
- one-sided sign-flip `p <= 0.05` on primary gross PnL;
- DSR probability `>= 0.95` across the frozen 20-arm universe;
- no single positive year contributes more than 35% of positive x1 PnL.

PASS authorizes only a fresh sequential validation ID; it does not open
validation or holdout. Any structural failure is engineering-invalid. Any
economic-gate failure is
`KILL_TRAIN_IMMEDIATE_FLOW_CONTINUATION_HOLDOUT_REMAINS_SEALED`.

## Evidence and prohibitions

One attempt only: `EURFXIMM001-TRAIN-ECON-001`. It must emit an attempt marker,
trade ledger, run log, log triage, terminal JSON, hash-bound manifest and five
charts: equity/drawdown, annual performance, four-arm comparison, flow-decile
diagnostic and distributions/funnel.

No horizon grid; no 1/2/3/10/15/30-minute follow-up chosen from this readout;
no threshold, magnitude, clock, cost, direction, calendar or regime rescue; no
validation/holdout, MQL5, MT5, Model 0, optimization, promotion, paper or live
authority under this ID.
