# HYP-JCDR-EURUSD-M5-006 — untuned Model-0 baseline result

Verdict: **KILL_BASE_PF_RAW_EDGE_AND_EQUITY_DD_FAIL_NO_REVISION**

## Scope

- EA: `EA_JCDR_PureReversal`
- Run: `20260810_153404`
- Symbol/timeframe: `EURUSD / M5`
- Tester window: `2016.01.04-2021.01.01`
- Model/execution/delay: `0 / 0 / 0`
- Deposit/leverage/spread: `100000 USD / 1:100 / current`
- Exactly one untuned baseline; no optimization, filter, alternative exit or same-ID retry.

## Artifact identity

- Frozen source SHA256: `383C582060C0332BD1A73E24316E619C125462D54046FD30CCC0AF56E7B49869`
- Prereg SHA256: `BB718FDE5F3E15BB2A6B84A2D38C8138AA10265635ED8781BD159D44D2488495`
- Execution receipt SHA256: `02331145743BA94797FE55AFF0483464AD4B242A0BF62FA9C8DA94FCBD050A43`
- Run manifest SHA256: `E78787B36D942EB2EB1BB440E7F7AD0CCCF4CF3707435A0171C5B85AFBE8092A`
- Report SHA256: `596D33C2B404A56A92BBFA0C345CEBE4FEF0C902F0011B6EC3D840323A6E84D2`
- Enhanced summary SHA256: `5982DFBE6F682D55D051281DBE2B2E1901064C7DAC34CCF8A5D9CC70EEE65B2F`
- Executed EX5 snapshot SHA256: `81FA40AFDBF1A78C48239E344E40A576C767DD359309B8389C7BFEC258094DED`
- Compile log SHA256: `A1801122E7C85EA835DBFBF73B58D395C3C4746A8CDC8AA4584ADC68E50EA492` (`0 errors, 0 warnings`)
- Non-repaint audit SHA256: `E5E84561B6880DDAB079E2C7124F52BF226BF71FC4F1B907F48849FDA0A0C73E` (`PASS`)

Manifest, source snapshot, executed EX5 and tester EX5 identities reconcile. The native report covers the frozen window with `100%` History Quality, `372360` bars and `118146836` ticks.

## Economic readout

| Metric | Result | Frozen gate | Verdict |
|---|---:|---:|---|
| Trades | 562 | — | observed |
| Cadence | 2.1568/week | 2–5/week | PASS |
| PF after report costs | 0.763972 | >1.30 | FAIL |
| Net profit | -$7,888.77 | positive | FAIL |
| Expectancy | -$14.04/trade | positive | FAIL |
| Balance DD | 7.89% | <=8% | PASS narrowly |
| Equity DD | 8.02% | <=8% | FAIL |
| BUY | 277 trades, PF 0.784556, net -$3,409.46 | viable | FAIL |
| SELL | 285 trades, PF 0.745462, net -$4,479.31 | viable | FAIL |

The result also loses before commission and swap: price-only net is `-$4,716.86` and price-only PF is `0.851207`. Commission is `-$3,106.76`; swap is `-$65.15`. Dynamic slippage is not observed in this run, but adding it cannot turn a price-only losing mechanism into a pass.

Year breakdown:

- 2016: 189 trades, PF `0.598433`, net `-$4,814.61`.
- 2017: 186 trades, PF `1.072469`, net `+$725.38`.
- 2018: 187 trades, PF `0.667408`, net `-$3,799.54`.
- 2019–2020: zero new entries after the permanent account-drawdown latch was reached intratrade. The report's maximum equity drawdown is `8.02%`.

Exit structure explains the market failure:

- 477 time exits: PF `1.0415`, net `+$737.30` — approximately noise/breakeven before additional slippage.
- 63 stop losses: `-$15,617.93`.
- 20 profit targets: `+$7,036.14`.
- Among terminal SL/TP outcomes, only `20/83 = 24.1%` reached the 1.5R target; the approximate breakeven hit rate before costs is 40%.

The cluster-decay signal therefore does not produce sufficiently strong or persistent reversal. This is not a parameter-near-miss.

## Independent review

Two read-only independent reviewers returned `PASS_KILL`:

- Economic gate reviewer reconciled run identity, report costs, cadence, sides and years and found no lawful post-hoc rescue.
- Implementation/evidence reviewer independently reconstructed PF and confirmed the 2018 stop in activity is the intended permanent equity-drawdown latch, not truncated tester coverage or a parser defect.

## Decision

Kill only the exact frozen pure JCDR reversal baseline. Do not run x1.5/x2 stress, WFA, optimization, OOS or holdout because the pre-cost mechanism is already losing. Do not add session, weekday, direction, stop/target or threshold filters from this readout. The broader goal remains active and must move to a genuinely different market mechanism.
