# TRAIN ECONOMIC PROBE PLAN — HYP-EURFXIMM-EURUSD-M1-002

Frozen on `2026-07-30` before any 14:15-to-14:20 EURUSD target access. This is
the exact implementation-only successor to HYP-EURFXIMM-EURUSD-M1-001, parked
pre-run with zero evidence and zero target/economic access because its terminal
printer requested a legacy arm key after JSON reload. Parent plan SHA256:
`705063A0A39B31E8DB7EAC2F49531A50BE855B6A91061738D499AC43316D8329`.

Every market, data, timing, cost, control and gate rule from that parent plan is
incorporated unchanged:

- TRAIN `2016-2020` only; validation `2021-2024` and holdout `2025-current`
  sealed.
- Exact HYP002 strict-lag pressure-selected 630-date source ledger SHA256
  `EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF`.
- Exact HYP013 `ts_recv` CME 6E final-15-second `flow_signed` feature SHA256
  `EB26ABA7B294BF6F3408D97E9D8B5A1E1ABDD5A5BB5A66842CEEA63E4D7DF13C`;
  summary SHA256 `14FAC1FB640D449AA08A93C3603CDDDB46F1DFC81229F0A6EAC6DB2CEC6FFE2C`;
  artifact-manifest SHA256
  `8C008C0C929F6A9BF03248DB9D68C5FF5692D74CEA7B24845E42310C2C0B8258`.
- Completed-Bid EURUSD M1 target parquet SHA256
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`;
  manifest SHA256 `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`.
- Primary: `sign(flow_signed)` continuation. Signal ends 14:15:00
  Europe/Berlin; enter completed 14:15 close observable 14:16; exit completed
  14:20 close observable 14:21. One trade/date; source-empty or zero-flow is no
  trade; only `2017-09-28` may lack target boundaries; exact expected N=608.
- Controls: exact flow reversal, price-pressure continuation and price-pressure
  reversal on the same target population.
- Fixed round-trip costs: 1.50/2.25/3.00 pips. No stop, target, intrabar path,
  sizing, time, threshold, magnitude, calendar, news or regime filter.
- Exactly 20 DSR trials: 16 prior x1 arms including all HYP016 arms plus these
  four. Sign-flip: 10,000 permutations, seed 20260730.
- Structural gates: exact 630/608 population, exact one-date missing allowlist,
  2-5 trades/elapsed week, >=25% each direction and exact frozen rule.
- Economic gates, all required: PF x1>=1.30, x1.5>=1.25, x2>=1.00; x1
  expectancy>0; >=4/5 positive years; every leave-one-year-out PF>1; one-sided
  p<=0.05; DSR>=0.95; max positive-year contribution<=35%.

The only implementation delta is a HYP002 wrapper that prints the public
`flow_continuation_primary` terminal key directly after artifact creation. One
attempt only: `EURFXIMM002-TRAIN-ECON-001`. PASS opens only the right to
preregister a fresh sequential validation ID. Any economic-gate failure is
`KILL_TRAIN_IMMEDIATE_FLOW_CONTINUATION_HOLDOUT_REMAINS_SEALED`. No horizon
grid, post-hoc rescue, validation/holdout, MQL5, MT5, Model 0, optimization,
promotion, paper or live authority.
