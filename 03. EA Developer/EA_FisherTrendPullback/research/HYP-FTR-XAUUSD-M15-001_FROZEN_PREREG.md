# HYP-FTR-XAUUSD-M15-001 — Frozen untuned baseline

Status: `NOT_OPENED_DEDUP_STOP_NO_SOURCE_NO_OUTCOME`.

This draft is not authorized for implementation or baseline. A local-truth check immediately after writing it found the earlier `HYP-FTP-XAUUSD-M15-001` Fisher-extreme + EMA-trend object in the same package, already stopped before baseline for recursive gap-state defects and adjacency to prior extreme-oscillator/trend families. No FTR source, compile, MT5 run, report, outcome or economics was opened. Preserve this note only as evidence that the duplicate lane was rejected before consuming a trial.

## Market thesis

The Fisher Transform makes recent median-price extremes easier to identify by mapping a rolling normalized price into an unbounded oscillator. TradingView's indicator documentation describes it as a reversal/major-turn detector, warns that it emits many standalone signals, and recommends pairing it with trend analysis. This hypothesis therefore tests one atomic behavior: the first Fisher turn out of an extreme pullback, but only in the direction of a slow EMA100 trend.

This is a fresh mean-reversion-inside-trend mechanism. It is not a revision or filter rescue of KVO, Donchian, Supertrend, Aroon, MFI, Vortex, Ichimoku, compression breakout, sweep/retest or volume-flow objects.

## Frozen identity and data

- Hypothesis `HYP-FTR-XAUUSD-M15-001`; EA `EA_FisherTrendPullback`; variant `FISHER9_EXTREME_TURN_EMA100_TREND`.
- XAUUSD M15, Model 0, execution/fixed delay 0, 100,000 deposit, 1:100 leverage, current tester spread.
- TRAIN `[2018-01-01, 2023-01-01)`; validation `[2023-01-01, 2025-01-01)` and holdout `[2025-01-01, 2026-08-01)` remain sealed.
- One untuned baseline attempt. No parameter tournament, optimizer, session/news/day/direction selection or outcome-derived rule.

## Exact closed-bar indicator

For every completed M15 bar `t`, price is median `(high+low)/2`. Fisher length is exactly 9.

1. `lo_t`/`hi_t` are the min/max median prices over bars `t-8..t`.
2. If `hi_t==lo_t`, normalized raw input is zero; otherwise `raw_t = 2*((median_t-lo_t)/(hi_t-lo_t)-0.5)`.
3. `value_t = 0.33*raw_t + 0.67*value_{t-1}`, clamped to `[-0.999,0.999]`.
4. `fish_t = 0.5*ln((1+value_t)/(1-value_t)) + 0.5*fish_{t-1}`.
5. EMA100 uses completed closes, alpha `2/101`, seeded from the first prehistory close. Fisher state is initialized with value/fish zero once the first 9-bar window exists.

Full available native M15 prehistory is processed oldest-to-newest before TRAIN. Missing/nonfinite/inverted bars fail closed; no state reset or seeding at 2018.

## Exact signal

At completed bar `t`:

- LONG iff `fish_t > fish_{t-1}`, `fish_{t-1} <= fish_{t-2}`, `fish_{t-1} <= -1.0`, `close_t > EMA100_t`, and `EMA100_t > EMA100_{t-8}`.
- SHORT is exact inverse: `fish_t < fish_{t-1}`, `fish_{t-1} >= fish_{t-2}`, `fish_{t-1} >= +1.0`, `close_t < EMA100_t`, and `EMA100_t < EMA100_{t-8}`.
- Equality arms the turn but never emits without the current strict directional change. Simultaneous signals are invalid.
- Decision is bar `t` close; execution is only the exact next native M15 open `t+15m`. A gap consumes the signal.
- At most one accepted entry per broker-server date. No session or spread filter.

## Risk and lifecycle

- Market FOK, one owned position, no pending orders/pyramiding.
- LONG stop is the lowest low of `t-4..t` minus `0.20*ATR14_t`; SHORT is mirrored. Stop rounds outward to tick size and must satisfy side/stops/freeze geometry.
- TP exactly `1.50R`, rounded inward. No trailing, breakeven or partial exit.
- Time exit after 16 completed M15 bars; Friday 20:00 server/weekend/design-end flatten.
- Risk 0.25% equity via `OrderCalcProfit`, volume rounded down, margin checked.
- Daily-loss lock 3.5%; account peak-equity drawdown lock 8%. Locks block new entries but do not disable position management.
- Every ambiguous property, indicator, clock, request, inventory or close state fails closed.

## Baseline gates

Engineering first: compile 0/0, source tests, non-repaint PASS, HQ `>97%`, complete nontruncated journal, exact D0/preload proof, `runtime_failed=false`, summary/report reconciliation and no orphan inventory.

Then TRAIN requires PF `>1.30` after report commission/swap/spread, positive expectancy and net, cadence `2–5` completed positions per 260.857 elapsed weeks, each direction at least 30%, no calendar year above 30%, equity DD `<=8%`. A material miss kills this exact mechanism; no rescue tuning. Only a pass may open full x1/x1.5/x2 cost evidence and validation.

Research provenance: [TradingView Fisher Transform](https://www.tradingview.com/support/solutions/43000589141-fisher-transform/) is formula/behavior motivation only, never parity or acceptance evidence.
