# HYP-ERAY-EURUSD-H1-001 — Frozen Source-Feasibility Preregistration

Status: `FROZEN_OUTCOME_BLIND_SOURCE_ONLY`

## Thesis and provenance

TradingView documents Bull Bear Power (Elder-Ray) with default EMA length 13:

- `BullPower_t = High_t - EMA13_t`
- `BearPower_t = Low_t - EMA13_t`

Reference: https://www.tradingview.com/support/solutions/43000717955-bull-bear-power/

This source screen tests a strict full-bar dominance relocation. A LONG event occurs only when the entire completed H1 bar moves from touching/below EMA13 to strictly above it. SHORT is the inverse. It is not an oscillator extreme, compression, channel breakout, Donchian rescue, Supertrend, MFI, Vortex, Ichimoku, RVI or Fisher object.

## Frozen identity and source

- Hypothesis: `HYP-ERAY-EURUSD-H1-001`
- Family: `elder-ray-ema13-full-bar-dominance-transition`
- Symbol/timeframe: FivePercent native `EURUSD` / `H1`
- Source: `EURUSD_H1_ALL_AVAILABLE_20260801.parquet`
- Source SHA256: `78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3`
- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- Read only rows with `time_utc < 2023-01-01T00:00:00Z`; use full available prehistory to seed EMA13.
- Score only `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`.
- Sole attempt: `ERAY001-SOURCE-ATTEMPT-001`.

## Exact formula and event

- Validate finite H/L/C, `High >= Low`, and `Low <= Close <= High` for every materialized row. Flat valid bars are allowed.
- EMA13 of Close: first value is the SMA of the first 13 valid closes; thereafter `EMA_t = (2/14)*Close_t + (12/14)*EMA_(t-1)`. Any invalid prehistory row fails the attempt; no row deletion/reset/interpolation.
- `BullPower_t = High_t - EMA_t`.
- `BearPower_t = Low_t - EMA_t`.

LONG raw event at completed H1 bar `t`:

- `BearPower_(t-1) <= 0`;
- `BearPower_t > 0`.

SHORT raw event:

- `BullPower_(t-1) >= 0`;
- `BullPower_t < 0`.

Current equality emits no event; prior equality may arm. LONG and SHORT conflict is forbidden and fail-closed. The decision is available only if the immediate next physical row has both `time_utc = t + 1 hour` and `source_epoch = source_epoch_t + 3600`. A raw event across a gap is counted and consumed but not persisted or queued. Never read next-row OHLC.

Ledger allowlist: hypothesis ID, source timestamp/epoch, decision timestamp/epoch, direction, prior/current EMA and prior/current relevant Bull/Bear Power only. No entry/exit price, post-event OHLC, return, trade, PF, PnL, cost, validation or holdout field.

## Source gates

All must pass:

- at least 25,000 scored H1 rows;
- feature coverage at least 99% after the 13-row EMA seed;
- exact-next coverage at least 97% of raw events;
- at least 500 executable events;
- pooled cadence 2.0–5.0 events per exact elapsed calendar week;
- LONG and SHORT each at least 30%;
- no decision-time UTC calendar year above 30% of events;
- each 2018–2022 calendar year cadence 1.25–6.50/week;
- zero direction conflicts and deterministic replay byte equality.

All annual concentration and cadence gates bucket events by `decision_time_utc`, not by the source bar year. Therefore a 23:00 UTC source bar whose executable decision is 00:00 UTC belongs to the new decision year.

Any failure parks this exact source mapping with no economic conclusion. No threshold, EMA length, timeframe, equality, gap, debounce, cooldown, session, direction or extra-filter rescue is permitted under the same ID.

Passing only authorizes a separately reviewed MQL5 implementation/parity stage. This attempt authorizes no post-event OHLC, economics, MT5, MQL5, optimization, validation, holdout, cost claim, promotion, paper or live trading.
