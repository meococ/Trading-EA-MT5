# HYP-PVPR-EURUSD-M15-001 — Frozen source preregistration

Status: frozen before reading DESIGN rows or computing a signal count.

## Thesis and target

- Package: `EA_PriorDayVolumeProfileReentry`.
- Symbol/decision timeframe: EURUSD / native-clock M15 from FivePercent M1.
- Source window: `[2015-01-01, 2023-01-01)`; DESIGN is
  `[2016-01-04, 2023-01-01)`.
- Information mechanism: prior UTC trading day's tick-volume-at-price profile.
  A M15 bar that opens outside the prior 70% value area and closes back inside
  is an auction-failure event directed toward the prior point of control (POC).
- Volume Profile provenance:
  `https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/`.
  The exact local formula below is the only authority; TradingView is not an
  acceptance or parity surface.
- All inputs are native MT5/FivePercent OHLC and tick volume. No paid data or
  external feed is authorized.

This thesis is materially different from time-series oscillator crosses,
aggregate session activity, VWAP, compression breakouts, sweep/retest levels,
and opening-range momentum: the state variable is a prior-day distribution of
activity across discrete price bins, and the event is failed acceptance outside
that distribution.

## Exact prior-day profile

For target UTC date `D`, only Tuesday through Friday are eligible. The profile
date is exactly calendar date `D-1`; Monday is intentionally ineligible because
Sunday is not a complete UTC profile.

A profile date is valid only when:

- it contains at least 1,000 unique, increasing native M1 rows;
- its first row is no later than `00:15 UTC` and last row no earlier than
  `23:45 UTC`;
- every OHLC value is finite, strictly positive and geometrically valid;
- every tick volume is finite/nonnegative and total tick volume is positive.

For each profile M1 bar:

1. `typical = (high + low + close) / 3`;
2. pip bin index `b = floor(typical / 0.0001 + 0.5)`;
3. assign the whole M1 tick volume to bin `b`.

Missing price bins between the daily minimum and maximum are represented with
zero volume. POC is the maximum-volume bin; ties choose the bin closest to the
tick-volume-weighted mean bin, then the lower bin. The value area begins at POC
and expands one adjacent bin at a time until cumulative included volume is at
least 70% of total. At each step take the adjacent side with larger volume;
ties take the lower side. `VAL/VAH` are the lower/upper selected bin prices.

## Exact M15 event clock

- Aggregate native M1 rows by UTC 15-minute bucket using first open, maximum
  high, minimum low and last close. No price interpolation or synthetic row.
- Candidate source bars satisfy `07:00 <= bucket < 16:00 UTC` on eligible date.
- LONG iff source-bar open `< prior VAL` and close is inside `[VAL, VAH]`.
- SHORT iff source-bar open `> prior VAH` and close is inside `[VAL, VAH]`.
- Only the first candidate per eligible date is emitted; this is a structural
  one-auction-failure-per-day state, not a cooldown or quota learned from data.
- Signal is known only after the completed M15 source bar. It is executable only
  when the exact next M15 bucket exists at `source_bucket + 15m`; only the next
  timestamp is inspected. Decision/availability time is that next bucket.
- Source and decision dates must remain inside DESIGN. Decision-year is the
  reporting axis.

No session/weekday choice beyond the frozen Tue–Fri complete-prior-day contract,
no direction deletion, trend/volatility/oscillator filter, cooldown, second
entry, post-event OHLC, outcome, stop/target, holding period, sizing,
optimization, validation or holdout is authorized at source stage.

## Source gates

All gates must pass:

1. exactly one durable attempt and deterministic byte-identical replay;
2. source/prereg/analyzer/test hashes stable throughout the attempt;
3. DESIGN M1 rows `>= 1,500,000`;
4. valid-profile coverage across eligible Tue–Fri DESIGN dates `>= 95%`;
5. raw-event exact-next M15 coverage `>= 97%`;
6. executable events `>= 500`;
7. pooled cadence `2.0–5.0/week` over exact DESIGN elapsed weeks;
8. each direction share `>= 30%`;
9. maximum calendar-year share `<= 25%`;
10. each DESIGN year cadence `1.25–6.50/week`;
11. zero direction conflicts and exact source-only ledger.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_PRIOR_DAY_VOLUME_PROFILE_REENTRY`.
All pass gives `SCREENED_SOURCE_PASS_MQL5_BUILD_AUTHORIZED`, permitting one
separately reviewed MQL5 correctness/parity build and then one untuned baseline.

## Failure radius and no rescue

A PARK closes this exact EURUSD M15 prior-calendar-day profile, 1-pip typical-
price binning, 70% adjacent value area, tie rules, Tue–Fri contract, 07:00–16:00
window, first outside-open/inside-close event and exact-next mapping. Do not
change bin width, profile/value-area algorithm, completeness threshold, day or
session, symbol, direction, event limit or clock based on the source count.
