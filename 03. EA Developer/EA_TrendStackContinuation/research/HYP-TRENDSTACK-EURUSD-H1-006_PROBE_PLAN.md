# HYP-TRENDSTACK-EURUSD-H1-006 — PROBE PLAN

Status: `FROZEN_IDEA_PRE_OUTCOME_MATERIALLY_NEW_H1_EXECUTION`

## 1. Identity, parent and novelty

- Hypothesis ID: `HYP-TRENDSTACK-EURUSD-H1-006`.
- EA identity: `EA_TrendStackContinuation`; symbol/timeframe `EURUSD / H1`.
- Parent HYP-005 is parked
  `PARK_PREREG_INVALID_BEFORE_SOURCE_NO_MARKET_VERDICT`, registry row 280 SHA256
  `3459C7AF9B0A5DFE8A2321CA56BCB550616B48D742C6FB5450F311FC40B6AB0D`,
  failure manifest SHA256
  `4141AE86C6BD58270DA1D833252E3738C13B0BF298636A998E61DF2C4A4715B0`.

HYP-006 is the corrected fresh-ID H1 object. It preserves no HYP-005 execution
authority. It reuses only accepted pre-decision HYP-002 feature evidence and
freezes a materially new H1 OHLC execution surface before any post-decision
price or economic result. HYP-001 through HYP-005 remain terminal under their
exact contracts.

No DESIGN post-decision H1 row, PnL, return or performance metric was opened
before this freeze.

## 2. Exact signal and controls

- A valid prior UTC date has finite positive unique H1 OHLC, at least 20
  distinct H1 UTC opens, and daily close equal to its latest H1 close.
- At 06:00 on decision date `d`, require 253 valid daily closes strictly before
  `d` and freeze
  `M252 = sign(valid_closes[-1] / valid_closes[-253] - 1)`.
- Require the six closed H1 bars with UTC opens 06:00 through 11:00 and freeze
  `M6 = sign(close_11:00 / open_06:00 - 1)` at 12:00.
- Equality in either ratio is no signal. Directions are exactly `+1` LONG and
  `-1` SHORT; no zero-direction trade is legal.
- `ATR20` is the simple average of True Range over the prior 20 closed H1 bars
  through the 11:00 bar, equivalent to MT5 `iATR(PERIOD_H1,20)` shift 1 at the
  12:00 decision. Wilder ATR is forbidden.
- `CONTROL_M252_ONLY`: every feature-complete base date, direction M252.
- `CONTROL_M6_ONLY`: every feature-complete nonzero-M6 date, direction M6.
- `CHALLENGER_STACK`: only `M252 == M6`, direction M252.
- `NEGATIVE_DISAGREE`: only `M252 != M6`, direction M6.
- Exactly four arms and `n_trials=4`; costs are not trials.

Accepted immutable feature evidence:

- Stage-0 ledger SHA256
  `3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`;
- receipt SHA256
  `5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE`;
- decision manifest SHA256
  `D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA`;
- decision receipt SHA256
  `DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320`;
- packet-set SHA256
  `22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E`;
- DESIGN date-set SHA256
  `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`.

DESIGN has `1,297` dates and `661` STACK opportunities (`263` LONG, `398`
SHORT). Validation feature evidence and every validation/holdout outcome remain
sealed.

## 3. Market mechanism and adverse prior

Slow information diffusion and persistent positioning can create time-series
momentum; same-day continuation may select days when that state is active. The
claim is incremental: alignment should improve both standalone legs and the
opposite-direction disagreement control after costs. Single-pair intraday FX
technical returns are fragile and cost-sensitive, so the prior is adverse.

- https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- https://biblio.ugent.be/publication/8060014
- https://biblio.ugent.be/publication/7190535

These sources motivate the mechanism only; they do not validate this object.

## 4. Frozen H1 execution object

- DESIGN: `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)`, exactly `1,824`
  elapsed calendar days / `260.571428571` weeks.
- Source authority:
  `DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002_PLAN.md`.
- Every execution OHLC is a closed BID H1 bar under the hash-bound FivePercent
  manifest. Entry is the BID open of the H1 bar at exactly `12:00 UTC`, after
  the 11:00 bar has closed.
- Initial stop distance is exactly `1.0 * ATR20`; LONG stop `entry - ATR20`,
  SHORT stop `entry + ATR20`; no take profit.
- Scan H1 bars opened 12:00 through 17:00. On the entry bar, a low/high touch
  exits at the exact stop. On later bars, an adverse open at or beyond the stop
  exits at that bar open; otherwise a low/high touch exits at the exact stop.
- If untouched, exit at the 18:00 BID open. Do not use 18:00 high/low. An 18:00
  open beyond the stop remains `TIME_EXIT_1800` at that open.
- One barrier, no TP, no intrabar SL/TP ordering ambiguity; one opportunity/day,
  no overlap and no overnight/weekend carry.
- Require exactly one valid H1 row at every UTC open 12:00 through 18:00. Any
  missing/duplicate row or join mismatch is engineering invalid; never drop the
  opportunity.

For direction `+1/-1`, EURUSD pip size is exactly `0.0001`:

```text
gross_R = direction * (exit_bid - entry_bid) / ATR20
stop_pips = ATR20 / 0.0001
net_R = gross_R - round_trip_cost_pips / stop_pips
```

Fixed round-trip cost tiers are `1.50`, `2.25`, `3.00` pips, unverified and
kill-only. They are not trials. The source spread column is not cost truth.

## 5. Exact metrics and twelve DESIGN gates

For each arm/cost tier, PF gains are the sum of positive net R and PF losses are
the absolute sum of negative net R. If loss is zero and gain positive, emit
`{status:NO_LOSS,value:null}`; that status passes an absolute PF threshold. If
both are zero, emit `{status:NO_WIN_NO_LOSS,value:null}` and fail PF. Otherwise
emit `{status:FINITE,value:gains/losses}`. JSON NaN/Infinity is forbidden.

All gates apply to `CHALLENGER_STACK` on DESIGN:

1. completed cadence `2.0..5.0` per `260.571428571` elapsed weeks;
2. PF at 1.50 pips `> 1.30`;
3. PF at 2.25 pips `>= 1.25`;
4. PF at 3.00 pips `>= 1.00`;
5. mean net R at 1.50 pips `>= 0.08`;
6. total net R at 1.50 pips `> 0`;
7. positive 1.50-pip net R in at least `4/5` DESIGN years;
8. DSR at 1.50 pips `>= 0.95` across exactly four arms;
9. STACK PF delta versus better standalone PF `>= 0.15`;
10. STACK mean-R delta versus better standalone mean-R `>= 0.05`;
11. STACK PF delta versus DISAGREE PF `>= 0.15`;
12. STACK mean-R delta versus DISAGREE mean-R `>= 0.05`.

For each relative metric, the better standalone is the separate maximum of M252
and M6 for that metric. PF delta statuses are exact: challenger NO_LOSS versus
finite/undefined is positive infinity and passes; both NO_LOSS delta is zero;
comparator NO_LOSS is negative infinity and fails; any other undefined delta
fails. Serialize infinity cases as explicit statuses, never numeric Infinity.

DSR uses canonical `02. AlphaFactory/tools/research/dsr.py` SHA256
`A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`,
per-trade 1.50-pip returns, four arm Sharpe ratios, sample variance across those
Sharpe ratios, `n_trials=4`, challenger skew and non-excess kurtosis. Emit a
common 1,824-day UTC book with no-trade days as zero.

DD and Monte Carlo are dormant diagnostics only in this H1 proxy phase. The
registry acceptance-contract DD/Monte-Carlo fields are retained for schema
compatibility but cannot pass, kill, promote or alter this verdict.

## 6. Sequential authority and falsification

Source tools/tests and a one-shot source run require a later legal registry
`idea -> probe` transition, independent review and a canonical reviewed packet.
Source PASS grants only a separate create-new DESIGN economic packet. Economics
must not be combined with collection/source construction.

- Source/custody/projection/schema/completeness/validator failure: park
  engineering-invalid, no market verdict, no same-ID retry.
- Any absolute/relative/yearly/DSR DESIGN gate failure: kill HYP-006; do not open
  validation outcomes and do not rescue.
- All gates PASS: `PROBE_SURVIVOR_DESIGN_ONLY`; preregister a separate validation
  H1 outcome/economic phase. HOLDOUT remains sealed.

No optimization, polarity flip, alternate lookback/hour/ATR/entry/stop/exit,
weekday/year/regime filter, threshold change, BE/TP, output reuse or post-outcome
rule change is legal. Nothing here authorizes EA, MQL5, Model 0, validation
outcomes, HOLDOUT, promotion, paper, live or deployment.
