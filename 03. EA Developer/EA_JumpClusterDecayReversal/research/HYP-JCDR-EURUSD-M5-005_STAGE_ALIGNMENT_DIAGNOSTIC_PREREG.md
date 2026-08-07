# HYP-JCDR-EURUSD-M5-005 — full-stage indicator alignment diagnostic

Status: `FROZEN_PRE_SOURCE_OUTCOME_BLIND_DIAGNOSTIC`

## 1. Purpose and epistemic boundary

HYP005 is a fresh data contract after terminal HYP004. It is not a parameter
rescue and it does not authorize an entry rule. HYP004 proved that the same-bar
`AIRD && QQE && energy` continuation conjunction was nearly disjoint, while its
routed-only CSV hid the pre-route state of 880 abstained events.

HYP005 preserves the JCDR event clock and exports one diagnostic row for every
raw event before any route or TB corridor filter. It may read only the just-
closed bar and older indicator buffers, causal structure levels, current spread
geometry and timestamp membership. It may not read availability/open price,
future OHLC, return, MFE/MAE, target/stop hit, win/loss, PnL, PF, drawdown,
expectancy, validation, holdout or private data. It may not place, modify or
close an order.

No HYP005 result can claim edge or authorize optimization. A PASS only permits
a separately preregistered economic hypothesis.

## 2. Data and clock identity

- Symbol/timeframe: broker-native `EURUSD`, `PERIOD_M5`.
- Research clock: raw FivePercentOnline-Real server timestamp; no UTC/session
  name is claimed.
- Inclusive analysis membership: closed bars from `2016.01.04 00:00` through
  `2020.12.31 23:55`.
- Tester envelope: `2016.01.04` through exclusive stop date `2021.01.01`, so
  the entire named analysis end date is observable.
- Model: MT5 Model 0, generated every tick from broker M1 history.
- Data vintage: available as of `2026-07-30T23:59:59Z`.
- History Quality strictly greater than `97%`, journal range covering the
  envelope and exactly one structured M5/M1/terminal/CopyTime proof.
- Exactly one diagnostic source run after build, compile, non-repaint audit and
  independent review. No same-ID second run or threshold change is allowed.

## 3. Frozen JCDR event clock

The HYP003/HYP004 event clock is unchanged: prior-48 median absolute M5 return,
`max(1.20 pip, 3.0 * scale)` jump, 15-bar cluster, at least three jumps, 80%
coherence, 4-pip displacement, ten-bar decay, three no-jump bars, retracement
`[0.25,1.00]`, exact 300-second continuity and first raw decision per broker
calendar date. The just-closed decision bar is shift 1; availability remains
the next M5 open timestamp and no price is read there.

## 4. One-row raw-event export

Every raw event emits exactly one `EVENT_DIAGNOSTIC` row, including invalid and
geometrically obstructed events. The row contains no selected entry direction,
trade arm or outcome.

### 4.1 JCDR and membership fields

- event ID, peak/decision/availability research-clock timestamps;
- analysis membership, research date/year/hour and cluster sign;
- jump count, coherence, anchor, extreme, signed displacement, scale,
  threshold, retracement and decision close;
- no availability price or later OHLC.

### 4.2 AIRD fields

- validity, held/raw regime, held confidence and raw probability;
- P(Bull), P(Bear), P(Range), P(HighVol);
- trend correlation, normalized momentum, volatility percentile, drift,
  confirmed-change flag and regime age;
- cluster-aligned and opposite trend probabilities derived only from the same
  closed snapshot.

### 4.3 VRC fields

- validity, Hurst, ADX, DI+/DI-, CHOP, ATR percentile, ATR, composite score,
  direction, regime, change flag, high/low-vol flags and component scores;
- age in closed bars since the latest regime-change flag, capped at 12 bars;
- cluster alignment as the product of cluster sign and VRC direction.

### 4.4 MBB fields

- DC validity, adaptive length, KER/KER percentile, regime, bandwidth,
  squeeze score/state, release and priority signal;
- squeeze age and release age, each scanned only over shifts `1..20`;
- priority-signal alignment with cluster sign.

### 4.5 QQE fields

- primary RSI, secondary RSI, composite state and zero-cross direction;
- primary/secondary cluster-aligned magnitudes;
- composite-change age and zero-cross age scanned only over shifts `1..12`.

### 4.6 TB SMC fields

- closed-bar validity, contract version, bias, structure event, sweep flags,
  void flags, displacement flags, confirmed swings, ATR, break level;
- cell/void age, displacement ratio, void/cell size in ATR, ready mask,
  nearest liquidity levels/availability flags;
- structure-event age and directional sweep ages scanned over shifts `1..20`;
- both counterfactual closed-bar geometries, independent of any selected route:
  long/short protected stop level and distance, long/short opposite-swing
  corridor, and `>=6 pip && >=1R` geometry flags.

Indicator scanning is bounded and causal. No shift 0 call is permitted.

## 5. Simultaneous source gates

All gates are fatal AND conditions:

1. History Quality `>97%`, journal bounds cover tester envelope and exactly one
   consistent series proof exists.
2. Zero trading orders/deals/positions and only the tester initial balance
   operation is permitted.
3. Exact first/last observed analysis dates: `2016.01.04` and `2020.12.31`.
4. At least `900` raw events and exactly one diagnostic row per raw event.
5. Maximum invalid-core-indicator row share `<=0.05`.
6. At least `900` rows contain finite AIRD probabilities, continuous VRC/MBB/
   QQE diagnostics or an explicit indicator-invalid mask; missing data may not
   silently become zero.
7. At least `850` rows contain valid TB contract v3 confirmed-swing geometry
   for both long and short counterfactual directions.
8. Maximum calendar-year raw-event share `<=0.30`.
9. Zero telemetry write failure, unaccounted indicator-read failure or TB ABI
   mismatch outside an explicitly recorded invalid mask.
10. Zero forbidden outcome/post-availability columns, price reads, performance
    metrics or economics.

These are diagnostic-population gates, not signal-quality or edge gates.

## 6. Frozen analysis plan after a PASS

Only descriptive outcome-blind analysis is allowed:

- joint and lagged occurrence tables for AIRD, QQE and energy states;
- route-stage funnel before and after each individual role;
- continuous alignment distributions, not threshold optimization;
- TB geometry availability by structural event/age;
- year and broker-hour strata for representativeness only, never selection.

The successor economic rule must be chosen from causal role logic and frozen
before outcome access. Pair/timezone/session optimization, if later justified,
must occur only inside purged training folds with the selected rule frozen before
OOS, CPCV/embargo, DSR trial accounting, WFA and native Visual Mode review.
