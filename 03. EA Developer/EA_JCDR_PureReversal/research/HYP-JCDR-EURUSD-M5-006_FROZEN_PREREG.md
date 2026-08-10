# HYP-JCDR-EURUSD-M5-006 - frozen pure JCDR reversal baseline

Frozen before MQL5 implementation, compilation or any outcome-bearing run.

## Thesis and lineage

The mechanism is a single atomic jump-cluster exhaustion thesis: a coherent cluster of unusually large M5 returns displaces price, then three consecutive non-jump bars and a 25%-100% retracement confirm decay. The baseline trades mean reversion opposite the cluster direction. It does not reuse the terminal HYP003-HYP005 same-bar indicator router and has no AIRD/VRC/MBB/QQE/TB votes or thresholds.

Outcome-blind lineage:

- `HYP-JCDR-EURUSD-M5-002` passed all 11 source gates with 902 executable events and 3.4635/week.
- The native MT5 HYP005 diagnostic observed 934 raw JCDR events and 3.5844/week with zero trades/outcomes.
- HYP003-HYP005 killed only their exact multi-indicator routing/composition contracts, not the raw JCDR event clock.

## Frozen signal

- Symbol/timeframe: `EURUSD / M5`.
- Closed bars only; process once at each new M5 open.
- Price scale at bar `t`: median absolute pip return of exactly the prior 48 valid M5 returns, excluding `t`.
- Jump at `t`: `abs(return_t) >= max(1.20 pips, 3.0 * scale_t)`.
- Cluster: trailing 15 completed M5 bars, at least 3 jumps, at least 80% same-sign coherence, and at least 4.0 pips signed displacement from the first jump bar open to the final cluster bar close.
- A newly completed cluster replaces any pending cluster and emits no trade on that bar.
- Decay window: next 10 completed M5 bars; require the latest 3 bars to be valid non-jumps.
- Retracement: `(extreme - close)/abs(extreme-anchor)` after an up cluster, symmetric after a down cluster; require `[0.25,1.00]` inclusive.
- First executable decision per broker-server calendar date only. Equality boundaries qualify exactly as written.
- Gaps other than exactly 300 seconds, invalid OHLC or invalid required scale reset formation and pending state.
- SHORT after an up cluster; LONG after a down cluster.
- Entry: first available market tick at the next M5 open after the completed decision bar. No retry after a rejected signal.

## Frozen exits and risk

- Stop distance: `max(6.0 pips, abs(cluster_extreme-cluster_anchor)/pip + 0.50 pips)` from the executable entry, outward-normalized to tick size.
- Take profit: exactly `1.50R` from executable entry after stop normalization.
- Time exit: close after 12 completed M5 bars (60 minutes) if neither SL nor TP closed the position.
- One owned EURUSD position, no pyramiding, no partial close, no break-even and no trailing stop.
- Requested risk: `0.25%` of equity, sized downward to broker volume step with `OrderCalcProfit`; invalid geometry, stops/freeze, margin, volume or order checks skip the signal fail-closed.
- Daily loss lock `3.5%`, account drawdown lock `8%`, maximum one entry per source day, and no weekend hold. Friday entry is blocked and any owned position is flattened from `20:00` broker-server time. These are capital-safety controls, not signal filters.

## Frozen baseline contract

- Tester envelope: `2016.01.04-2021.01.01`; scoring and entry decisions use completed M5 bars in `[2016.01.04 00:00, 2021.01.01 00:00)` broker-server time. The extra terminal boundary lets MT5 expose and flatten the final 2020 bar without authorizing a 2021 signal. Model 0, execution mode 0, delay 0, current spread, deposit `100000 USD`, leverage `1:100`.
- Exactly one untuned baseline; no optimization, session/direction filter, parameter sweep, alternative TP/SL or same-ID retry.
- Cost evidence must include report spread/commission plus the repository's frozen EURUSD research slippage proxy. If dynamic slippage cannot be proven, the result is engineering-only and cannot pass economics.
- Baseline gates: PF `>1.30` after x1 costs; cadence `2-5/week`; max DD `<=8%`; x1.5-cost PF `>=1.25`; x2-cost PF `>=1.00`; both directions represented; no year above 35% of trades.
- Only a baseline passing those gates may open sensitivity, Monte Carlo, WFA/OOS or holdout.
