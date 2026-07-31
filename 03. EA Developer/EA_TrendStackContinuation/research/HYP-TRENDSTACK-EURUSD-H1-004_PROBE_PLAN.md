# HYP-TRENDSTACK-EURUSD-H1-004 — PROBE PLAN

Status: `FROZEN_PRE_OUTCOME_ENGINEERING_SUCCESSOR`

## 1. Identity and failure radius

- Hypothesis ID: `HYP-TRENDSTACK-EURUSD-H1-004`.
- EA identity: `EA_TrendStackContinuation`.
- Symbol / decision timeframe: `EURUSD / H1`.
- Parent: HYP-003 parked
  `PARK_ENGINEERING_INVALID_FOOTER_DIGEST_CONTRACT_MISMATCH_NO_MARKET_VERDICT`.
- Parent failure manifest SHA256:
  `DAEDFB436BD7FC636C7F791FB24084289DA41B1CD9ABE0446A6BC6BE892127E7`.

HYP-004 changes only the source-integrity contract: it replaces the undefined
HYP-003 footer digest with the exact Parquet byte-range definition frozen in
`DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002_PLAN.md`. The immutable raw file,
market mechanism, indicators, clocks, arms, dates, trials, execution proxy,
costs and economic gates do not change. HYP-003 packet/marker/terminal/stage and
all HYP-002 M1/quarantine artifacts are forbidden inputs.

No DESIGN price row, strategy outcome, PnL or economic metric existed when this
plan was frozen.

## 2. Accepted parent feature evidence

HYP-004 reuses without recomputation only:

- HYP-002 Stage-0 ledger SHA256
  `3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`;
- Stage-0 receipt SHA256
  `5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE`;
- decision manifest SHA256
  `D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA`;
- decision receipt SHA256
  `DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320`;
- packet-set SHA256
  `22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E`;
- DESIGN date-set SHA256
  `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`.

There are exactly `1,297` frozen DESIGN dates from `2016-01-04` through
`2020-12-31`, requiring exactly `466,920` M1 opens. The trusted projector must
again produce a physical DESIGN-only Stage-0 capability; no VALIDATION row,
identity, count, direction, path or statistic may reach the source builder or
later evaluator.

## 3. Frozen mechanism and indicators

- `M252 = sign(last valid daily close / close 252 valid UTC dates prior)`.
- `M6 = sign(close of closed 11:00 H1 / open of closed 06:00 H1)`.
- Decision: `12:00 UTC`, closed bars only.
- `ATR20`: MT5 simple average of the prior 20 closed H1 true ranges, shift 1.
- Arms: `CONTROL_M252_ONLY`, `CONTROL_M6_ONLY`, `CHALLENGER_STACK`,
  `NEGATIVE_DISAGREE`.
- Trials: exactly `4`; source engineering attempts add no economic trial.

DESIGN STACK evidence remains `661` (`263` LONG, `398` SHORT). Validation
feature evidence remains sealed. No threshold, sign, date, hour, direction,
arm, ATR, cost, stop or gate may change.

## 4. Source-only gate

The exact source authority is
`DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002_PLAN.md`. HYP-004 receives only
the accepted public DESIGN custody capability and physical DESIGN-only Stage-0
projection. It cannot read/enumerate the raw monolith, source parent, private
vault, parent failed stages, mixed Stage-0 ledger, VALIDATION or HOLDOUT.

For every frozen date require exactly 360 unique chronological UTC M1 opens
from `12:01` through `18:00` inclusive, one regular one-row-group shard, exact
server/UTC/offset round-trip, finite positive OHLC and valid OHLC geometry.
Require all 1,297 dates and exactly 466,920 rows. The known 2016-03-11 broker
gap receives no exception. No fill, interpolation, resample, dedupe, date drop,
merge, alternate source, retry widening or output reuse is legal.

Independent validation alone may emit
`SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET`. Source PASS is
engineering-valid only and grants no economics by itself.

## 5. Frozen conditional DESIGN economics

A later separate create-new packet may evaluate DESIGN only after source PASS:

- entry `12:01 UTC` M1 bid open;
- LONG/SHORT stop at `1.0 * ATR20` below/above entry;
- no take profit;
- stop scan through `17:59`; otherwise exit at `18:00` M1 bid open;
- one opportunity per UTC date, no overlap;
- frozen kill-only round-trip costs `1.50`, `2.25`, `3.00` pips;
- the HYP-002 V2 stop/gap/18:00/tie/R semantics remain exact.

The twelve challenger gates on DESIGN are:

1. cadence `2.0–5.0` trades per elapsed calendar week;
2. PF at 1.50 pips `> 1.30`;
3. PF at 2.25 pips `>= 1.25`;
4. PF at 3.00 pips `>= 1.00`;
5. mean net R at 1.50 pips `>= 0.08`;
6. total net R at 1.50 pips `> 0`;
7. positive net R at 1.50 pips in at least `4/5` DESIGN years;
8. DSR `>= 0.95` across the four frozen arms;
9. PF delta versus the better standalone control `>= 0.15` at 1.50 pips;
10. mean-net-R delta versus that control `>= 0.05`;
11. PF delta versus `NEGATIVE_DISAGREE >= 0.15`;
12. mean-net-R delta versus `NEGATIVE_DISAGREE >= 0.05`.

Drawdown and Monte Carlo remain dormant diagnostics in the proxy phase; they
are not pass/kill/promotion gates. No optimization, subgroup, calendar veto,
threshold rescue, parameter search, stop/target/BE change or post-outcome rule
change is allowed.

## 6. Routing

- Source/capability/completeness/identity/footer/schema/validation failure:
  park engineering-invalid with no market verdict and no same-ID retry.
- Any DESIGN economic gate failure: kill the exact HYP-004 candidate with no
  validation M1 and no post-hoc rescue.
- All DESIGN gates pass: DESIGN-only survivor; a separate preregistered
  validation source/economic phase is still required.

Nothing in this plan authorizes EA source, MQL5, Model 0, validation outcomes,
holdout, promotion, paper, live or deployment.
