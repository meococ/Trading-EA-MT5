# HYP-TRENDSTACK-EURUSD-H1-007 - PROBE PLAN

Status: `FROZEN_IDEA_PRE_SOURCE_PRE_ECONOMICS_FRESH_SINGLE_BAR_EXECUTION`

## 1. Identity, parent, and adverse prior

- Hypothesis ID: `HYP-TRENDSTACK-EURUSD-H1-007`.
- EA identity: `EA_TrendStackContinuation`; symbol/timeframe `EURUSD / H1`.
- Parent HYP006 is terminal `PARK_SOURCE_COMPLETENESS_FAILED_NO_MARKET_VERDICT`
  at registry row 283. Its failure manifest SHA256 is
  `6BA20A96C29FE0F6D2317A53B5E7B0893719EC1840FC3344C49461B62EF1548C`.
- HYP006 required every H1 open from 12:00 through 18:00 UTC. Its outcome-blind
  timestamp audit found that exact object incomplete on three selected dates.
  No HYP006 economic result was opened.

HYP007 is a fresh, same-family, materially different execution/data object. It
tests only the single 12:00 UTC H1 bar. The choice was made after a timestamp-
only DESIGN audit established that 12:00 exists exactly once on all 1,297
selected dates. No HYP007 OHLC, return, PnL, performance metric, VALIDATION, or
HOLDOUT payload was opened before this freeze. This provenance creates a high
post-hoc selection risk and an adverse prior; timestamp completeness is not
evidence of edge.

HYP006 may not be retried. Its partial stage, failed 12:00..18:00 projection,
raw H1 monolith, and any sealed payload are forbidden HYP007 runtime inputs.

## 2. Mechanism and immutable pre-decision features

The hypothesis is that slow information diffusion and persistent positioning
can create time-series momentum, while same-session alignment of long-horizon
and six-hour momentum selects continuation states. The incremental claim is
that alignment should beat both standalone legs and the opposite-direction
disagreement control after fixed costs. The one-bar horizon changes the payoff
distribution and execution risk but does not create a new alpha feature.

Reuse the accepted HYP002/HYP006 pre-decision definitions unchanged:

- `M252 = sign(valid_closes[-1] / valid_closes[-253] - 1)` using 253 valid
  daily closes strictly before the decision date.
- `M6 = sign(close_11:00 / open_06:00 - 1)` using six closed H1 bars from 06:00
  through 11:00 UTC.
- Equality is no signal.
- `ATR20` is the simple average True Range over the prior 20 closed H1 bars
  through 11:00, equivalent to MT5 `iATR(PERIOD_H1,20)` shift 1 at 12:00.
  Wilder ATR is forbidden.

Accepted immutable feature evidence:

- Stage-0 ledger SHA256
  `3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`;
- Stage-0 receipt SHA256
  `5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE`;
- decision manifest SHA256
  `D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA`;
- decision receipt SHA256
  `DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320`;
- packet-set SHA256
  `22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E`;
- exact 1,297-date selection manifest SHA256
  `D99C21ED2611A70D9F225170997EAADDD6567827B69759A1DFA9EA7F73C7A135`;
- DESIGN date-set SHA256
  `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`.

No source-projection tool receives feature, direction, arm, ATR, or economic
fields. Features join only in a separate evaluator after source projection PASS
and a separately reviewed economic packet.

## 3. Frozen arms and counts

Exactly four arms and `n_trials=4`; costs are not trials:

- `CONTROL_M252_ONLY`: 1,297 rows, direction M252.
- `CONTROL_M6_ONLY`: 1,292 nonzero-M6 rows, direction M6.
- `CHALLENGER_STACK`: 661 agreement rows, direction M252.
- `NEGATIVE_DISAGREE`: 631 disagreement rows, direction M6.
- Total arm rows: exactly 3,881.

There is at most one opportunity per `arm x UTC date`. Any identity, count,
feature join, or direction mismatch is engineering invalid before economics.

## 4. Frozen source projection contract

The source phase is governed by
`HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V1.json`.

- Reuse only immutable public DESIGN custody from collection
  `DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002`.
- Bind public receipt SHA256
  `623328512F0CB77B52B155F6CD314EA2B47DAC40636A7714BD38167BEA807B13`
  and public manifest SHA256
  `DA513911B01B1C4232611225C77A4F22E9E3C89E719EE530923BD574D06451E5`.
- Read exactly the 1,297 selected public DESIGN shards once each and exactly one
  valid BID H1 row at `12:00 UTC` from each shard.
- Do not read any of 258 unselected public DESIGN shards.
- Do not fill, drop, interpolate, resample, deduplicate, replace dates, or use
  the three HYP006-bad dates differently.
- HYP007 attempt-local raw source opens must be zero. Historical custody records
  the one original raw-source open separately.
- Sealed VALIDATION/HOLDOUT, HYP006 partial stage, HYP006 completed output, M1
  artifacts, features, and economics are fail-closed denied.
- Any missing or duplicate 12:00 row, schema mismatch, hash mismatch, access
  count mismatch, unsafe filesystem identity, or publish conflict parks HYP007
  engineering-invalid with no market verdict.

Source PASS means only `ENGINEERING_VALID_SOURCE_PROJECTION`. It does not grant
economics, validation, MQL5, Model 0, promotion, paper, live, or deployment.

## 5. Frozen single-bar execution

DESIGN is `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)`, exactly 1,824 elapsed
calendar days or `260.571428571` weeks.

- Decision occurs after the 11:00 UTC H1 bar closes.
- Entry is the BID open of the 12:00 UTC H1 bar.
- Stop distance is exactly `1.0 * ATR20`; LONG stop `entry - ATR20`, SHORT stop
  `entry + ATR20`; no take profit or trailing stop.
- LONG exits at the exact stop if `low_12 <= stop`; otherwise at 12:00 BID close.
- SHORT exits at the exact stop if `high_12 >= stop`; otherwise at 12:00 BID close.
- Equality is a stop touch. Stop precedence is deterministic. No later bar is
  inspected, so there is no same-bar SL/TP ordering ambiguity.

For direction `+1/-1`, EURUSD pip size is exactly `0.0001`:

```text
gross_R = direction * (exit_bid - entry_bid) / ATR20
stop_pips = ATR20 / 0.0001
net_R = gross_R - round_trip_cost_pips / stop_pips
```

Fixed round-trip cost tiers are `1.50`, `2.25`, and `3.00` pips, unverified and
kill-only. The public spread field is not cost truth.

## 6. Exact metrics and twelve DESIGN gates

The HYP006 metric edge cases and DSR method remain unchanged. PF uses positive
net-R gains and absolute negative net-R losses. `NO_LOSS` passes an absolute PF
threshold; `NO_WIN_NO_LOSS` fails. JSON NaN and Infinity are forbidden. Relative
PF infinity cases use explicit statuses.

DSR uses `02. AlphaFactory/tools/research/dsr.py` SHA256
`A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`,
per-trade 1.50-pip returns, exactly four arm Sharpes, challenger skew and
non-excess kurtosis, and a common 1,824-day UTC book with no-trade days as zero.

All gates apply to `CHALLENGER_STACK` on DESIGN. The thresholds deliberately
remain as strict as HYP006; the new horizon does not receive relaxed gates:

1. completed cadence `2.0..5.0` per 260.571428571 elapsed weeks;
2. PF at 1.50 pips `> 1.30`;
3. PF at 2.25 pips `>= 1.25`;
4. PF at 3.00 pips `>= 1.00`;
5. mean net R at 1.50 pips `>= 0.08`;
6. total net R at 1.50 pips `> 0`;
7. positive 1.50-pip net R in at least `4/5` DESIGN years;
8. DSR at 1.50 pips `>= 0.95` across exactly four arms;
9. STACK 1.50-pip PF minus better standalone 1.50-pip PF `>= 0.15`;
10. STACK 1.50-pip mean net R minus better standalone mean net R `>= 0.05`;
11. STACK 1.50-pip PF minus DISAGREE 1.50-pip PF `>= 0.15`;
12. STACK 1.50-pip mean net R minus DISAGREE 1.50-pip mean net R `>= 0.05`.

The better standalone is the separate maximum of M252 and M6 for the exact
metric. DD and Monte Carlo remain dormant diagnostics only in this DESIGN proxy;
registry DD/Monte-Carlo fields are schema-compatible promotion envelopes, not
probe pass gates.

## 7. Sequential authority and falsification

1. Freeze this plan, source contract, and registry idea row.
2. Independent review must pass before `idea -> probe` and source tool build.
3. Build/test source projection without opening public shard payloads.
4. Independently review exact tool/test/packet hashes.
5. Run at most one reviewed source-projection attempt.
6. After source PASS, freeze and independently review a separate economic packet.
7. Run DESIGN economics once. Any gate failure kills HYP007 and keeps validation
   sealed. All gates passing yields only `PROBE_SURVIVOR_DESIGN_ONLY`.

No optimization, polarity flip, alternate feature, hour, horizon, stop multiple,
ATR, cost, date set, source, filter, threshold, TP, BE, output reuse, same-ID
retry, or post-result amendment is legal. Nothing here authorizes EA source,
MQL5, Model 0, VALIDATION, HOLDOUT, promotion, paper, live, or deployment.

