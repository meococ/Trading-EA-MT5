# Impact-per-Pressure Proxy Probe — Coordinator Readout

Date: 2026-07-13  
Verdict: `KILL_AT_OFFLINE_PROBE`  
Research state: `CLOSED BEFORE REGISTRY / PREREG / EA CODE`

## Decision

Kill `Impact-per-Pressure Continuation` as proposed by Deep Research V5. Do not
tune, rescue, register, preregister, implement, compile, or backtest this
candidate. The single frozen proxy probe failed six gates by very large margins
and showed no pre-cost edge.

`Round-Number Release Persistence` remains `KILL_AT_INTAKE_DUPLICATE` against
the failed `S558 / EA_GoldRound` family. Neither V5 candidate authorizes an EA.

## Execution identity and safety

- Source: read-only MT5 Python tick API, current `MetaQuotes-Demo` login.
- Terminal connected: `true`; terminal trade allowed: `false`.
- Probe safety receipt: `orders_sent=0`, `positions_opened=0`,
  `live_trading_authorized=false`.
- No MQL5 source was created or edited. MetaEditor and Strategy Tester were not
  invoked.
- The wrong-broker allowance was falsification-only. A pass would not have
  satisfied FivePercentOnline-Real provenance; the observed failure closes the
  candidate without needing a target-broker rerun.

## Data coverage

The read-only API returned every requested calendar month from December 2017
through December 2025 for both symbols:

| Symbol | Months | Quote ticks | M15 bars | Eligible bars | Empty months |
|---|---:|---:|---:|---:|---:|
| EURUSD | 97 | 191,822,569 | 200,752 | 126,037 | 0 |
| GBPUSD | 97 | 237,880,820 | 200,736 | 141,305 | 0 |

Monthly bar counts were 1,880–2,208 and all MT5 month calls returned `Success`.
This is adequate for a research-only falsification result. It is not a claim
that MetaQuotes-Demo costs or quotes represent FivePercentOnline-Real.

## Frozen result

The return-z control threshold was selected once on train at
`2.0975609756099023`, matching exactly `50,058` primary train signals with
`50,058` control train signals.

### Primary candidate

| Split | Trades | Trades/week | Gross PF | PF stress B | Expectancy stress B | Net stress B |
|---|---:|---:|---:|---:|---:|---:|
| Train 2018–2022 | 46,936 | 179.93 | 0.588 | 0.350 | -2.213 pips | -103,876.075 pips |
| Holdout 2023–2025 | 27,242 | 173.99 | 0.619 | 0.340 | -2.011 pips | -54,773.650 pips |
| Pooled | 74,178 | 177.70 | 0.598 | 0.346 | -2.139 pips | -158,649.725 pips |

Gross expectancy was already negative before the frozen cost stress:
`-1.013`, `-0.811`, and `-0.939` pips/trade on train, holdout, and pooled.
The result is therefore not a merely cost-sensitive near miss.

Primary holdout exit counts were `16,596 stop`, `4,278 target`, `3,276
time_stop`, `2,671 both_hit_adverse_first`, and `421 opposite_signal`.

### Matched return control

The holdout return control produced `27,655` trades, PF stress B `0.404`, and
expectancy stress B `-1.985` pips/trade. It also failed absolutely, but its PF
was higher than the candidate's `0.340`. The candidate therefore failed the
identity test: the proposed price-path statistic did not add useful information
over a matched close-to-close return shock.

## Gate readout

Passed: data coverage and minimum sample only.

Failed:

- cadence: `177.70/week`, versus frozen `2.0–5.5/week`;
- PF stress B: holdout `0.340`, pooled `0.346`;
- holdout expectancy: `-2.011 pips/trade`;
- pooled max drawdown: `75,075.96R` under the frozen stop normalization;
- concentration: every year/symbol/side positive-PnL bucket was empty under
  stress B, so the required concentration ratios were undefined;
- matched control: candidate did not strictly beat control on all holdout
  metrics.

## Interpretation

The cited academic evidence concerns signed transactions or participant order
flow. The MT5 formula used `sign(mid-price change)`, which is derived from the
same price path it tries to predict. The empirical result confirms the source
audit warning: this implementation behaves as an extremely frequent
directional-efficiency/momentum transform, not a distinct order-flow edge.

The failure must not be repaired by changing `k`, `c`, `Nmin`, stop/target,
holding time, symbol, side, hour, weekday, or cost. Any such change after this
readout would be post-hoc rescue of a closed candidate.

## Evidence

- Probe summary:
  `preflight/v5_ipp/20260713_IPP_PROXY_PROBE_V1/summary.json`, SHA256
  `F77E62A8B9B3D8D269E7D2447AC90DAEFE5C19F521F2A6564A990E3E96C0FF87`.
- Producer:
  `02. AlphaFactory/tools/impact_pressure_probe.py`, SHA256
  `ADC18F5A795C103D89459DCF9ECF4828BF203249B144D9B1FB0982C902FAA6FB`.
- EURUSD features SHA256
  `A83F05E9542C99E7CC106084EFE643E61314624EF5B88B966F0973D88B133981`.
- GBPUSD features SHA256
  `282B7315292F68DD4CB81BCF5ABE48CF4EC0CF39FE9F3DE1DA66ABB073F1A030`.
- Primary trades SHA256
  `FA4E7E210402305B5D8D04B6B460379FA5F0C6758D8FD52D409E1339903763D2`.
- Return-control trades SHA256
  `10DD71B30A061921EEF24E575E73FC35C4F92C1BD54751B561208C027DD8D37A`.
- Runner stderr is empty; SHA256
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- Focused tests: `6 passed`; test source SHA256
  `5E0078008389DAD7871AD3C6390ED406006412CE0A40709E372ABBB0E7865E56`.

## Next research action

Start a new Deep Research cycle from the separate V6 failure packet. GPT may
propose a genuinely independent hypothesis or return `NO LEGAL CANDIDATE`. It
may not tune or rescue either V5 candidate. Any new candidate still requires
de-duplication and one cheap frozen probe before a registry row, preregistration,
or EA build.
