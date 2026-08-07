# HYP-JCDR-EURUSD-M5-004 — role-aware mode-router source preregistration

Status: `FROZEN_PRE_OUTCOME_FIXED_WINDOW_SOURCE_CONTRACT`

## 1. Scope and epistemic boundary

HYP-004 is a fresh decision surface after terminal HYP-003. It does not change
the JCDR event clock to rescue a failed threshold. It changes the composition
of the already-built indicators from overlapping fatal AND gates to distinct
economic roles.

This stage is outcome blind. It may inspect only closed-bar event formation,
closed-bar indicator buffers, causal structure levels, timestamp membership,
current spread geometry and planned stop/corridor distances. It may not send,
modify or close an order; read post-availability OHLC; calculate return,
MFE/MAE, win/loss, PnL, PF, drawdown or expectancy; choose a session/year from
performance; optimize; or open validation/holdout/private data.

The invalid HYP-003 telemetry is used only to identify a composition failure
and freeze this successor before a new run. Its 49% History Quality cannot
prove HYP-004 feasibility or market edge.

## 2. Fixed data identity

- Symbol/timeframe: broker-native `EURUSD`, `PERIOD_M5`.
- Research clock: FivePercentOnline-Real server timestamp. No UTC label or
  historical timezone conversion is claimed.
- Tester range and analysis range: `2016.01.04` through `2020.12.31`.
- Tester model: Model 0, generated every tick from the broker's M1 history.
- Data vintage: FivePercentOnline-Real epoch available as of
  `2026-07-30T23:59:59Z`.
- Fixed-window History Quality must be strictly greater than `97%`.
- Journal history bounds must cover both requested dates and contain exactly
  one structured M5/M1/CopyTime series-proof record.
- Coverage starts when the first observed M5 bar date is `2016.01.04` and ends
  when the last observed M5 bar date is `2020.12.31`. A nonexistent holiday
  `23:55` bar is not required.
- One source-feasibility run is authorized after source build, compile,
  non-repaint audit and independent review. No second run or same-ID numeric
  rescue is allowed.

## 3. Frozen JCDR event clock

The HYP-003 broker-native event clock is unchanged:

- prior scale: median absolute closed-bar return over the prior 48 M5 bars,
  excluding the current bar;
- jump: `abs(return) >= max(1.20 pips, 3.0 * prior_scale)`;
- cluster: 15 M5 bars, at least three jumps, at least 80% sign coherence and
  at least 4.0-pip signed displacement;
- decay: ten bars after peak, three consecutive no-jump bars and retracement
  in `[0.25, 1.00]`;
- first decision per broker research-clock date;
- gaps other than exactly 300 seconds reset state;
- decision uses the just-closed bar; availability is the next M5 open.

JCDR remains the sole event clock. No indicator may manufacture an event.

## 4. Frozen role-aware router

All indicator values are read at shift 1. Any read/ABI/validity failure in
AIRD, VRC, MBB, QQE or TB SMC is a fatal event-level abstention.

### 4.1 Regime and energy state

- `unreleased_squeeze = MBB.squeeze == 1 && MBB.release != 1`.
- `vrc_disorder = VRC.chop >= 61.8 && VRC.hurst > 0.45`.
- `vrc_high_or_compression = VRC.high_vol == 1 || VRC.regime == 7`.
- An unreleased squeeze always abstains. Compression is not interpreted as a
  reversal entry; it requires a later causal release.

### 4.2 Momentum agreement

- `aird_follow = AIRD.regime` equals the cluster-sign trend state and AIRD
  confidence is at least its existing 80% high-confidence reference.
- `qqe_follow = QQE.composite` equals the dominant cluster sign.
- AIRD and QQE never create the event and never hard-veto separately. They are
  used jointly to select the continuation route.

### 4.3 Route priority

After validity and unreleased-squeeze checks:

1. Select `FOLLOW_CONTROL` when
   `aird_follow && qqe_follow && (VRC.high_vol || MBB.regime == TREND || MBB.release)`.
2. Otherwise select `TRUE_REVERSAL` when VRC is neither high-volatility,
   compression nor disorder, and MBB is not in an unreleased squeeze.
3. Otherwise abstain as `REGIME_CONFLICT`.

`FOLLOW_CONTROL` follows the dominant jump-cluster sign. `TRUE_REVERSAL` is
opposite it. Route priority is frozen exactly in that order.

### 4.4 TB SMC directional geometry

TB SMC has no entry, route or target authority. With the selected primary
direction and the decision close:

- long protected stop level is
  `min(cluster_anchor, cluster_extreme, confirmed_swing_low) - 0.50 pip`;
- short protected stop level is
  `max(cluster_anchor, cluster_extreme, confirmed_swing_high) + 0.50 pip`;
- planned stop distance is the absolute decision-close distance to that level
  and must be at least 6.0 pips;
- the causal corridor is decision close to the opposite confirmed swing in
  the selected direction and must be at least `1.0 * planned_stop_distance`.

The future matched inverse-control arm, if separately authorized, must use the
same event-level pip stop distance as the primary route. This isolates route
direction instead of giving the control a different risk budget.

## 5. Export contract

Exactly two adjacent rows are exported for every routed event:

- `ROLE_PRIMARY`: selected direction;
- `INVERSE_CONTROL`: opposite direction;

Both rows share signal ID, decision/availability timestamps, route label,
indicator snapshot, planned stop distance, corridor distance and cost/stop
ratio. Descriptive `RESEARCH_CLOCK` year/hour are emitted but cannot filter
this run.

Forbidden columns include availability/open price, post-availability OHLC,
entry/exit price, target hit, stop hit, return, MFE/MAE, outcome, PnL, balance,
equity, PF, drawdown and expectancy.

## 6. Simultaneous one-shot gates

All gates are fatal AND conditions:

1. fixed-window History Quality `>97%` with journal bounds and exact one series
   proof;
2. zero trade/order APIs, zero trading orders/deals and only the tester's
   initial balance operation permitted;
3. exact requested first/last observed M5 dates;
4. zero indicator-read or ABI/contract failures outside explicitly recorded
   event-level invalidity;
5. at least `500` raw JCDR events;
6. at least `180` routed events after the frozen role and corridor rules;
7. routed cadence in `[0.70, 2.00]` per all `260.43` elapsed calendar weeks;
8. at least `80` `ROLE_PRIMARY` long and `80` short events;
9. at least `80` selected reversal routes and `80` continuation routes;
10. maximum calendar-year routed share at most `0.30`;
11. exactly one `ROLE_PRIMARY` and one `INVERSE_CONTROL` row per routed signal;
12. median planned stop at least `6.0 pips` and median frozen
    `1.50-pip / stop` ratio at most `0.25`;
13. zero forbidden outcome fields and zero post-availability price reads.

The route-count thresholds are population-health gates, not market-edge
claims. HYP-003's outcome-blind diagnostic suggested 239 pre-corridor routed
events (127 reversal, 112 continuation), but HYP-004 receives no PASS credit
from that invalid data-quality run.

## 7. Session and pair-specific optimization boundary

No hour/session filter is allowed in HYP-004. If this source stage passes, a
fresh economic hypothesis must preserve broker research-clock strata and
evaluate pair-specific session choices only inside purged training folds.
The selected session must then be frozen before OOS/holdout. No server-hour to
UTC/London/New-York name mapping is allowed without verified historical offset
and DST metadata.

## 8. Future economics boundary

A PASS authorizes only a new preregistration. The future economic contract must
freeze before outcomes:

- matched role-primary versus inverse-control runs;
- 1R target and 60-minute maximum hold inherited from HYP-002;
- real spread/commission plus preregistered dynamic slippage stress;
- trial count for DSR, purged/embargoed CPCV, WFA and sealed OOS;
- immediate kill gates and visual replay sampling of wins, losses and extreme
  adverse cases using native MT5 charts with the real indicator stack.

No source PASS can authorize optimization, promotion, paper or live trading.
