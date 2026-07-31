# HYP-TRENDSTACK-EURUSD-H1-005 — PROBE PLAN

Status: `FROZEN_PRE_OUTCOME_MATERIALLY_NEW_EXECUTION_SURFACE`

## 1. Identity and failure radius

- Hypothesis ID: `HYP-TRENDSTACK-EURUSD-H1-005`.
- EA identity: `EA_TrendStackContinuation`.
- Symbol / decision timeframe: `EURUSD / H1`.
- Parent: HYP-004 parked
  `PARK_ENGINEERING_INVALID_AFTER_VALID_CUSTODY_BEFORE_DESIGN_SOURCE_ACCEPTANCE_NO_MARKET_VERDICT`.
- Parent registry row: `277`, row SHA256
  `E01166D8952722B69BAF6C9AC72B95D374BDC365F5189A390AE9D77900211ED9`.
- Parent failure manifest SHA256:
  `51E87178ABA98F9C848D7EAA0501197F44C9356E9B023FD4AB52A414354C0461`.

HYP-005 is not a same-object HYP-004 repair. It freezes a materially new H1
execution surface before any strategy outcome was opened. The M252 × M6 signal
and four controls are retained, but the economic object changes from a 12:01 M1
entry with a complete M1 stop path to a 12:00 H1-open entry with a single-stop
H1 OHLC path. This avoids repeating the already-proven FivePercent M1 source
fatal gate at 2016-03-11; it does not fill, drop, reinterpret or rescue that M1
run. HYP-001 through HYP-004 remain terminal under their exact contracts.

No DESIGN post-decision H1 row, strategy return, PnL or performance metric was
opened when this plan was frozen.

## 2. Accepted feature evidence

HYP-005 reuses without recomputation only the physically sealed HYP-002
pre-decision feature evidence:

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
- frozen DESIGN date-set SHA256
  `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`.

DESIGN contains exactly `1,297` feature-complete dates and `661` aligned STACK
opportunities (`263` LONG, `398` SHORT). VALIDATION feature evidence stays
sealed from outcomes; HOLDOUT remains fully sealed.

## 3. Mechanism and indicators

- Market prior: slow information diffusion and persistent positioning may
  create time-series momentum; same-day continuation may select days when that
  state is active. This is a prior, not proof for EURUSD H1.
- `M252 = sign(last valid daily close / close 252 valid UTC dates prior)`.
- `M6 = sign(close of closed 11:00 H1 / open of closed 06:00 H1)`.
- Decision: `12:00 UTC`, after the 11:00 H1 bar closes; closed bars only.
- `ATR20`: MT5 simple average of the prior 20 closed H1 true ranges, shift 1;
  Wilder ATR is forbidden.
- Arms: `CONTROL_M252_ONLY`, `CONTROL_M6_ONLY`, `CHALLENGER_STACK`,
  `NEGATIVE_DISAGREE`.
- Trials: exactly `4`; cost tiers and engineering attempts are not trials.

Primary adverse/supporting priors remain:

- https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- https://biblio.ugent.be/publication/8060014
- https://biblio.ugent.be/publication/7190535

## 4. Frozen H1 economic object

- DESIGN window: `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)`;
  `1,824` elapsed calendar days / `260.571428571` weeks.
- Entry: bid open of the H1 bar at exactly `12:00 UTC`.
- Initial stop distance: exactly `1.0 × ATR20` frozen at decision.
- LONG stop: `entry - ATR20`; SHORT stop: `entry + ATR20`; no take profit.
- Scan H1 bars with UTC opens `12:00` through `17:00` in chronological order.
  If a bar opens beyond the stop, exit at that adverse open. Otherwise a
  low/high stop touch exits at the exact stop. A single stop and no target means
  no same-bar target/stop ordering ambiguity.
- If no stop occurs, exit at the bid open of the `18:00` H1 bar.
- One opportunity per UTC date, no overlap, no overnight/weekend carry.
- Require exact unique H1 opens `12:00..18:00`; a missing row is engineering
  invalid and cannot be silently excluded.
- Gross R: `direction × (exit_bid - entry_bid) / ATR20`.
- Net R subtracts `round_trip_cost_pips / initial_stop_pips`.
- Frozen kill-only all-in round-trip costs: `1.50`, `2.25`, `3.00` pips;
  missing cost is never zero.

The H1 OHLC path is a kill-only research proxy. It does not establish ask-side
fills, slippage, stop/freeze levels, tick ordering, margin or deploy fidelity.
A survivor still requires MQL5 parity and Model-0 evidence under a separate
authorized packet.

## 5. DESIGN gates — all required

1. challenger cadence `2.0..5.0` trades per elapsed calendar week;
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

Drawdown and Monte Carlo remain diagnostics only in this first proxy phase.
There is no optimizer, parameter grid, polarity flip, subgroup/calendar veto,
threshold rescue, alternate ATR, stop/target/BE change or sequential retuning.

## 6. Source and sequential routing

The exact source authority is
`DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-001_PLAN.md`. A source attempt may run
only after red-first tools/tests, independent review and a fresh canonical
one-shot packet. Source PASS is engineering-valid only; DESIGN economics require
a separate frozen packet and fresh evaluator authority.

- Source/custody/projection/completeness/validation failure: park HYP-005
  engineering-invalid, no market verdict, no same-ID retry.
- Any DESIGN economic gate failure: kill the exact HYP-005 H1 object; do not
  open VALIDATION outcomes and do not rescue.
- All DESIGN gates pass: DESIGN-only survivor; preregister a separate H1
  VALIDATION source/economic phase. HOLDOUT remains sealed.

Nothing here authorizes EA source, MQL5, Model 0, validation outcomes, holdout,
promotion, paper, live or deployment.
