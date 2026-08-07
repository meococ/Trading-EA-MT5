# HYP-JCDR-EURUSD-M5-003 — outcome-blind indicator-routing feasibility

Status: `FROZEN_PRE_OUTCOME_ROUTER_CONTRACT`

## 1. Identity and scope

- Hypothesis: `HYP-JCDR-EURUSD-M5-003`
- Parent: `HYP-JCDR-EURUSD-M5-002`
- Package: `EA_JumpClusterDecayReversal`
- Symbol / decision timeframe: `EURUSD / M5`
- Window: `2016-01-04` through `2020-12-31`
- Data plane: native completed broker M5 bars from the dedicated AlphaFactory
  FivePercent portable MT5 only.
- Purpose: verify that a production-shaped, broker-native JCDR event surface
  can be reconstructed in MQL5 and enriched with the five already-built
  indicator contracts without destroying cadence or introducing lookahead.

This stage is strictly outcome blind. The EA is an exporter/probe: it may not
send, modify or close orders; calculate post-entry return, MFE, MAE, PnL,
profit factor, win rate or drawdown; select a session/year/direction; run an
optimizer; or open validation/holdout/private custody.

## 2. Frozen broker-native JCDR event surface

This is a fresh data/construction surface, not an event-identity replay of
HYP-JCDR-EURUSD-M5-002. The parent established only that the mechanism has a
usable population on exact-five public DESIGN bars. This successor changes to
native broker M5 because that is the deployable EA surface; no count or event
identity may be claimed across the two sources.

1. process only a newly opened native M5 bar and read OHLC from shift 1 or
   older; native timestamps are the canonical `RESEARCH_CLOCK`;
2. require consecutive completed bar opens exactly 300 seconds apart; any
   other interval, duplicate, missing bar, nonfinite OHLC or invalid OHLC
   ordering resets all formation and pending-cluster state;
3. closed M5 pip return from consecutive bars;
4. median absolute return over the prior 48 closed M5 returns, excluding the
   current return; for 48 sorted values the median is the arithmetic mean of
   zero-based ranks `23` and `24`;
5. jump threshold `max(1.20 pips, 3.0 * median_abs_return)`; the jump test,
   coherence, displacement and retracement boundaries use direct inclusive
   IEEE-double comparisons with no epsilon, pip rounding or later tolerance;
6. a 15-bar window ending on a jump, at least three jumps, at least 80 percent
   same sign, at least 4.0-pip signed displacement from the open of the first
   chronological jump bar in that window to the close of the window-ending
   cluster-peak bar; the anchor is that first jump-bar open and the frozen
   extreme is the maximum high of all 15 bars for an up cluster or minimum low
   of all 15 bars for a down cluster;
7. at most ten later closed bars, with the decision bar and its two prior bars
   non-jumps, retracement from frozen extreme toward anchor in `[0.25, 1.00]`;
8. a newer qualifying cluster replaces the pending cluster; gaps reset all
   formation state; only the first decision per `RESEARCH_CLOCK` calendar date
   is kept; no broker-to-UTC claim or transform is permitted in this probe;
9. true direction is opposite the cluster; follow-control direction is with
   the cluster; both are exported one-to-one.

The EA evaluates only after a new M5 bar opens. All event and indicator inputs
come from shift 1 or older. Availability is the open of the just-started M5
bar. The forming bar is forbidden.

## 3. Frozen role-aware router

The router uses vetoes and risk geometry, not majority voting. Indicator
defaults remain exactly those in the compiled workspace indicators; no input
is optimized.

All five handles use symbol `EURUSD`, timeframe `PERIOD_M5`, no explicit input
arguments and these exact paths:

- `AlphaFactory\\AI_Regime_Detection`
- `AlphaFactory\\Volatility_Regime_Classifier_QuantRegime`
- `AlphaFactory\\Modern_Bollinger_Bands_GBB`
- `AlphaFactory\\QQE_MOD`
- `AlphaFactory\\TB_Smart_Money_Concept_2026`

Every indicator therefore uses its file defaults and empty `InpEaContract`.
TB uses `TB_PROFILE_TV_2026_2_0`, effective swing length `5`,
both-swings-required and contract version `3.0`. Changing path, profile, input
order, timeframe, symbol or any default is a new contract.

### AIRD — state/risk permission only

- Buffers: valid `11`, held regime `12`, confidence `5` (percent).
- Reject when invalid.
- Reject any `HIGH VOLATILITY` held regime (`3`).
- Map an original up-cluster explicitly to continuation regime `0` (Bull) and
  an original down-cluster explicitly to continuation regime `1` (Bear).
- Reject that continuation state when confidence buffer `5` is at least
  `80.0` on its documented percent scale.
- This is an event-level risk-permission veto applied identically to both
  exported arms; it never rewrites either arm's direction.
- AIRD never supplies direction or an entry.

The 80-percent boundary is AIRD's existing high-confidence pane level. It is
not a value selected from JCDR outcomes.

### VRC — volatility/disorder veto only

- Buffers: Hurst `14`, Choppiness `18`, volatility percentile `19`, regime
  `23`, high-vol flag `26`, valid `31`.
- Reject when invalid, high-vol flag is `1`, regime is compression (`7`), or
  `CHOP >= 61.8` while `Hurst > 0.45`.
- A choppy bar is therefore permitted only when the classifier itself shows
  mean-reverting/anti-persistent behavior.
- VRC never supplies direction.

The two numeric boundaries reuse existing VRC defaults, but their joint
CHOP/Hurst veto is a prospectively frozen JCDR router composition; it is not
claimed to be a native VRC regime rule and cannot be changed after the probe.

### MBB — energy/location context only

- Buffers: basis `7`, regime `20`, squeeze state `23`, release `24`, valid
  dominant-cycle flag `16`.
- Reject unless dominant-cycle valid buffer `16 == 1`, basis `7` is finite and
  not `EMPTY_VALUE`,
  regime `20` is exactly `0` or `1`, and squeeze state `23` and release `24`
  are each exactly `0` or `1`. The `dc_valid` rejection is an intentional hard
  feasibility gate, not display state.
- Reject an active squeeze (`squeeze_state == 1`) unless the same closed bar is
  a release (`release == 1`).
- MBB S1/S2/S3 flags do not create or change the JCDR entry.

### QQE — original-momentum expansion veto only

- Buffers: composite state `8`, primary centered RSI `3`, secondary centered
  RSI `4`.
- Fail closed unless primary centered RSI `3` and secondary centered RSI `4`
  are finite, non-EMPTY usable values and composite state `8` is exactly
  `-1`, `0` or `+1`. Warm-up zero in buffer 8 cannot bypass unusable RSI.
- For an up-cluster / reversal-short candidate, reject composite state `+1`.
- For a down-cluster / reversal-long candidate, reject composite state `-1`.
- The QQE test is evaluated once from original cluster sign and its event-level
  result is copied identically to TRUE_REVERSAL and FOLLOW_CONTROL; QQE never
  inspects or rewrites arm direction.
- Neutral or already-opposed QQE is permission, not an entry.

### TB SMC — causal invalidation geometry only

- Buffers: confirmed swing high `13`, swing low `14`, closed-bar valid `26`,
  ATR `28`, contract version `43`.
- Require closed-bar valid `1`, contract version `3.0`, and confirmed swing
  high/low values finite, non-EMPTY and ordered `swing_low < swing_high`.
- The shared parent base distance is
  `max(6.0 pips, abs(cluster_extreme - anchor)/0.0001 + 0.50 pips)`.
- Let `decision_close` be the close of shift 1. No availability-bar OHLC may
  be read. Define the causal TB envelope as the maximum of the absolute pip
  distances from `decision_close` to `confirmed_swing_high + 0.50 pip` and to
  `confirmed_swing_low - 0.50 pip`.
- The final planned stop distance is `max(parent_base_distance,
  tb_envelope_distance)` and is identical for TRUE_REVERSAL and
  FOLLOW_CONTROL. It is a distance, not an arm-selected stop price.
- The `0.50-pip` padding is inherited JCDR parent geometry, not a TB default.
- TB BOS/MSS, sweep, void, cell, bias and liquidity-objective buffers are
  forbidden as entry or target selectors.

## 4. Export contract

For every raw JCDR decision, export only information known at availability:

- signal ID, decision/availability time, cluster sign, reversal/follow side;
- anchor, frozen extreme, retracement, robust scale and jump count/coherence;
- each indicator's causal shift-1 state and individual veto reason;
- raw and router-pass flags;
- base and TB-widened planned stop geometry;
- `RESEARCH_CLOCK` broker-native hour as a descriptive stratum only. No UTC
  normalization is authorized without separately verified historical
  server-offset metadata.

Forbidden fields include post-availability high/low/close, exit price, return,
MFE/MAE, outcome label, PnL, balance/equity and any performance statistic.

The probe must write a bounded JSONL/CSV artifact and a compact terminal
summary. Large terminal/tester logs are inspected only with
`02. AlphaFactory/tools/large_log_reader.py`.

## 5. One-shot feasibility gates

Exactly one valid full-window Model-0 probe is authorized after compile,
focused tests and independent review pass. All gates are frozen:

1. compile: zero errors and zero warnings;
2. non-repaint audit: all decisions on shift 1 or older and no forming-bar
   reads;
3. no trade API invocation and zero deals/orders;
4. all five indicator handles valid and contract checks pass;
5. raw decision count at least `500`;
6. router-pass reversal count at least `150`;
7. router-pass cadence, defined as router-pass reversal event count divided by
   frozen elapsed calendar weeks, at least `0.55` and at most `4.0`, where
   `elapsed_weeks = (2020-12-31 - 2016-01-04).days / 7`;
8. router-pass reversal long and reversal short counts each at least `40`;
9. maximum `RESEARCH_CLOCK` calendar-year router-pass reversal count divided
   by total router-pass reversal count at most `0.40`;
10. matched reversal/follow-control export is exactly one-to-one;
11. TB-widened median stop is at least `6.0 pips` and median frozen
    `1.50-pip / stop` ratio is at most `0.25`;
12. zero forbidden outcome fields and zero post-availability price reads.

All twelve gates are simultaneous fatal AND conditions. No active-week,
active-year, raw-row, arm-row, session or other denominator substitution is
allowed after compile.

PASS is `PASS_ROUTER_FEASIBILITY_FUTURE_ECONOMICS_PREREG_ONLY`. Failure is
terminal for this exact router. It is not a market no-edge verdict.

## 6. Future economics boundary

A PASS grants no edge claim. A fresh `HYP-JCDR-EURUSD-M5-004` preregistration
must bind the compiled EA/source hashes, development window, matched
reversal/follow-control arms, 1R and 60-minute exits, dynamic cost/slippage
tiers, trial count, immediate economic kill gates and sealed later windows
before any outcome is opened.

Timezone, session, weekday, year, direction and indicator-threshold selection
from this probe are forbidden. Their distributions are diagnostics only. Any
future pair-specific or timezone-specific change is a fresh hypothesis and
must be selected inside train folds then judged on purged/embargoed OOS folds.
