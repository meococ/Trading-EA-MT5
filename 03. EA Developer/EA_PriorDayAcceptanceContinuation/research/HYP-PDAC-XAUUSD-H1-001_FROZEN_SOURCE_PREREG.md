# HYP-PDAC-XAUUSD-H1-001 — frozen source-feasibility preregistration

Status: `FROZEN_BEFORE_SOURCE_DATA_OPEN`

## Market thesis

A first hourly break of the preceding broker trading-day range is often only a
liquidity probe. Two consecutive completed H1 closes outside that range, with
the second close extending in the breakout direction, represent acceptance of
a new daily price area. The proposed economic child would trade continuation
from the exact next H1 open.

This is a threshold-free, multi-day price-acceptance mechanism. It is not the
terminal New York 08:15 opening drive, a fixed-session breakout, a failed
auction/reclaim, a generic indicator crossover, or a change to a prior exit.

## Frozen source mapping

- Source: native FivePercent XAUUSD H1 fully closed Bid bars from
  `DATA-FIVEPERCENT-5ASSET-MULTITF-004`.
- Exact file:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet`.
- Exact source SHA256:
  `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`.
- Design window on the primary server axis: `[2018-01-01 00:00,
  2023-01-01 00:00)`; elapsed weeks are exactly `1826 / 7`.
- A broker trading day is one `time_server` calendar date containing native H1
  bars. Its reference day is the immediately preceding nonempty trading date.
- A reference day is usable only when it has 20–24 finite, geometrically valid,
  positive-tick-volume H1 bars.
- For a current day D, bars `t-2`, `t-1`, `t` must be on D and source-contiguous
  at exactly one hour.
- LONG raw event at completed bar t iff:
  `close[t-2] <= prior_high`, `close[t-1] > prior_high`,
  `close[t] > prior_high`, and `close[t] > close[t-1]`.
- SHORT is the exact inverse around `prior_low` with strict lower closes.
- Only the chronologically first raw event per current broker date is consumed;
  later same-date events are ignored. Equality never signals.
- Decision time is completed t. Execution feasibility inspects only the next
  row timestamp and requires `source_epoch[next] = source_epoch[t] + 3600`.
  No next-bar OHLC, outcome, return, cost, MFE/MAE or PF may be read.

## Frozen source gates

- Source rows in the half-open design window: at least 25,000.
- Exact-next coverage of raw events: at least 97%.
- Executable events: at least 500.
- Pooled cadence: 2–5 events per elapsed calendar week.
- LONG and SHORT each at least 30%.
- No decision year above 30% of executable events.
- Each of 2018–2022: 1.25–6.5 executable events/week.
- Zero simultaneous-direction conflicts.

Any failed gate parks this exact mapping before MQL5 implementation. No period,
threshold, session, cooldown, debounce, direction or timeframe rescue is
allowed after the count. A pass authorizes only a fresh implementation review;
it does not establish economic edge.
