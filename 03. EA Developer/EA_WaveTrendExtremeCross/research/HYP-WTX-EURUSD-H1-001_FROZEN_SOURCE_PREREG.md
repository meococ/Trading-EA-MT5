# HYP-WTX-EURUSD-H1-001 — Frozen source preregistration

Status: frozen before source scan and before any post-event price or economic read.

## Thesis and scope

- Symbol/timeframe: native FivePercent `EURUSD H1` completed Bid bars.
- Source window: `[2015-01-01, 2023-01-01)`; 2015 is indicator warm-up only.
- DESIGN window: `[2016-01-04, 2023-01-01)`.
- Mechanism: default WaveTrend extreme cross, inspired by the open-source
  TradingView WaveTrend Oscillator by LazyBear:
  `https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/`.
- This local formula is the authority. TradingView is provenance only and is
  not an acceptance or parity surface.
- Native MT5/FivePercent/The5ers data is sufficient for this lane. No paid data
  request or acquisition is authorized.

## Exact formula

For completed H1 bar `t`:

1. `ap_t = (high_t + low_t + close_t) / 3`.
2. `esa_t = EMA10(ap)_t`.
3. `d_t = EMA10(abs(ap_t - esa_t))_t`.
4. `ci_t = (ap_t - esa_t) / (0.015 * d_t)` when `d_t > 0`; otherwise invalid.
5. `wt1_t = EMA21(ci)_t`.
6. `wt2_t = SMA4(wt1)_t` over four finite consecutive indicator values.

Each EMA seeds from the first finite input value and then uses
`alpha=2/(period+1)` recursively. Gaps in the native H1 calendar do not reset
the formula; bars remain ordered by native bar count. Invalid/nonfinite source
geometry fails closed.

Events are emitted only on completed bars:

- LONG iff `wt1[t-1] <= wt2[t-1]`, `wt1[t] > wt2[t]`, and `wt1[t] < -60`.
- SHORT iff `wt1[t-1] >= wt2[t-1]`, `wt1[t] < wt2[t]`, and `wt1[t] > +60`.
- Equality arms but never emits. A bar cannot emit both directions.
- The first exact next native H1 bar must exist at `t+1h`; only its timestamp is
  inspected. No next-bar OHLC is read. The decision and availability timestamps
  are separate ledger fields.

There is no session, weekday, cooldown, quota, trend filter, volatility filter,
direction deletion, outcome, SL/TP, holding period, risk sizing, optimization or
parameter search in the source stage.

## De-duplication and informing evidence

Repository search found no prior WaveTrend signal object. This is materially
different from STC double-stochastic MACD, QQE, Connors RSI, MFI, Vortex,
Follow Line, compression breakout, sweep/retest and fixed zero-cross objects:
direction comes from a two-stage channel-index oscillator crossover occurring
inside its own extreme region.

Informing evidence is limited to source-clock failures: default Follow Line was
over-frequency, TD9 and BB/KC squeeze releases failed exact-next coverage, and
Mass Index marginally exceeded the pooled cadence ceiling. No WaveTrend count,
post-event price, return, PnL or PF informed this mapping.

## Frozen source gates

All gates must pass:

1. exactly one claimed attempt and deterministic byte-identical replay;
2. native source SHA and prereg/analyzer/test hashes remain stable;
3. DESIGN rows `>= 40,000`;
4. finite WaveTrend coverage `>= 99%` after the first 40 DESIGN bars;
5. raw-event exact-next coverage `>= 97%`;
6. executable events `>= 500`;
7. pooled cadence `2.0–5.0` events per elapsed calendar week;
8. each direction share `>= 30%`;
9. maximum calendar-year share `<= 25%`;
10. every DESIGN calendar year cadence `1.25–6.50/week`;
11. zero direction conflicts and exact source-only ledger schema.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_WAVETREND_EXTREME_CROSS`.
All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_BUILD_AUTHORIZED`, permitting
only a separately reviewed MQL5 correctness/parity child. Economics remains
unauthorized until that build passes.

## Failure radius

A PARK closes only exact EURUSD H1 WaveTrend `10/21/4`, constant `0.015`,
thresholds `-60/+60`, current-WT1 strict extreme cross, first-finite EMA seed,
and exact-next mapping. It may not be rescued by parameter, threshold, symbol,
timeframe, seed, session, direction, cooldown or execution changes.
