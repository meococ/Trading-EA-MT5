# HYP-RSF-EURUSD-M5-SEQUENCE-002 — terminal result

Status: `KILLED_NEGATIVE_EXPECTANCY`

## Frozen test

- EURUSD M5, 2018-01-01 through 2022-12-31, Model 0.
- Run: `02. AlphaFactory/runs/EA_RegimeStructureFusion/20260807_044549`.
- One economic trial; no optimization trial.
- Mechanism: MBB arm followed by one-to-three-bar confirmation of context,
  TB structure, QQE reacceleration, location and runway.

## Result

| Metric | Value |
|---|---:|
| Trades | 48 |
| Profit factor | 0.5519 |
| Net profit | -2,531.44 USD |
| Max drawdown | 3.121% |
| Win rate | 31.2% |
| Expectancy | -52.74 USD/trade |

The raw PF is below 1.0, so the preregistered immediate-kill rule applies before
cost stress or any parameter search. The report-bound cost builder also rejected
the research-proxy spread file after MT5 completed because row 2 lies outside the
run window; that infrastructure failure cannot rescue a raw losing result.

## Funnel diagnosis

- 2,660 setups armed; only 48 confirmed (1.8%).
- 2,124 expired and 488 were cancelled.
- Main rejection counts: timing 2,841; location 1,504; structure 1,225;
  risk 684; context 450; runway 153.
- Trend short alone was positive (17 trades, +325.09, PF 1.22), but selecting it
  after viewing the result would be post-hoc route rescue and is forbidden.
- Year results were unstable: 2018 positive, 2019–2022 negative.

The temporal AND-chain reduced frequency without creating edge. It still asks
four differently lagged indicators to vote on one bar rather than assigning
each component a distinct causal role. Any successor must be a new mechanism
under a fresh hypothesis, not a threshold or route tweak under this ID.

## Evidence hashes

- Source: `E67BD97BDA6443D08D1317E66ED432C6E4CA3FD163AA7C149F9264CDB74E9C1F`
- Report: `95BE7D0CA9284821FCFC88E34B1A9C913E9E7847EFCDAF6E6D2CEE89C9FDC272`
- Run manifest: `86AEB550FF0D82C070F59DA023A7C79BDED51FD4857BA2D0D74865A22EBA5828`
- Lifecycle: `3919181570F46F22A0D2DE5A51FB16CA88F49FBAB9EE9CD82DB419D1173D5D27`
- Run meta: `4B3B6325D2D4D7EBD5264D3334FEABB06E7F5AFDEBABA6C5B6D382E823F2C462`

Engineering-valid: yes. Economic-valid: no. Promotion-ready: no.
