# HYP-024 — frozen time-weighted swept-level resilience collection

## Identity and epistemic boundary

- Hypothesis: `HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024`.
- Parent implementation: immutable terminal HYP-022 source SHA-256
  `5FF5F8600362C95DAC66C2F1450A2B82D4E1B202F98679B9BE0C52C71039410C`,
  retaining the exact HYP-012 sweep/reclaim and bounded three-bar confirmation.
- HYP-020 is terminal because its any-recross bit is OHLC-recoverable. HYP-022
  is terminal because repeated churn was only 10.2985% and 1.4776/elapsed week.
  HYP-024 changes the research object to **elapsed-time dominance on each side of
  the swept level after first favorable quote**. It does not alter either kill.
- This is one zero-trade, outcome-blind data-acquisition/de-dup gate. It cannot
  establish edge, authorize economics, reopen a terminal parent, or authorize
  paper/live use.

Independent advisory review:
`.context/grok_ictfvg_hyp024_time_resilience_20260720/run1/grok-response.json`,
SHA-256 `1EAB64FB3F7E5A5955B53CE3B0FC70E2A25868511ED234615E6931F9070FD98C`.

## Research basis, not an edge claim

- Obizhaeva and Wang model supply/demand as an intertemporal object whose
  resilience matters for market impact and execution
  ([NBER Working Paper 11444](https://www.nber.org/papers/w11444)).
- Cont, Stoikov and Talreja model continuous-time order-book dynamics and
  conditional short-horizon price events
  ([Operations Research](https://pubsonline.informs.org/doi/abs/10.1287/opre.1090.0780)).
- FX order flow can contain information, while its price effect may be transitory
  or persistent; this motivates measuring persistence but does not validate this
  retail quote proxy
  ([BIS Working Paper 405](https://www.bis.org/publ/work405.htm)).
- MQL5 exposes quote update time in milliseconds as `MqlTick.time_msc`
  ([MQL5 MqlTick reference](https://www.mql5.com/en/docs/constants/structures/mqltick)).

The EA observes retail broker bid/ask quote-mid, not signed institutional flow or
full depth. `resilience` is therefore a frozen operational proxy only.

## Frozen measurement

For each unchanged HYP-012 setup:

1. `D=+1` long or `-1` short. Structural level `L` is `sweep_low` for long and
   `sweep_high` for short.
2. Interval is `[sweep_bar_close, confirmation_decision)`. The closed
   confirmation bar must be processed before the first new-bar tick is
   accumulated, while a newly detected sweep may consume its first post-sweep
   tick after closed-bar processing.
3. A valid quote has finite positive bid/ask and `ask>=bid`; `mid=(bid+ask)/2`.
   `time_msc` must be positive and monotone non-decreasing inside the setup.
4. Side is favorable when `D*(mid-L)>0`, adverse when `<0`. Exact equality is
   a valid observation that retains the prior side.
5. Time before the first strict favorable quote is discarded. At the first
   favorable quote, set `last_valid_msc=time_msc`, side favorable and begin the
   observed horizon.
6. On every later valid quote, first assign
   `dt=max(0,time_msc-last_valid_msc)` to the previous side, update the side
   from the new mid (equality sticky), then set `last_valid_msc=time_msc`.
   Same-millisecond transitions change side but add zero duration.
7. An invalid quote increments invalid telemetry but changes neither side nor
   `last_valid_msc`. The next valid quote or seal therefore carries the last
   valid side over the gap. `max_gap_ms` is diagnostic only.
8. At unchanged closed-bar confirmation, set
   `decision_msc=1000*(confirmation_bar.time+PeriodSeconds(PERIOD_M5))` and
   assign only the tail `[last_valid_msc,decision_msc)` to the last side.
9. Label:
   - `FAVORABLE_DOMINANT` when `favorable_ms>adverse_ms`;
   - `ADVERSE_DOMINANT` when `adverse_ms>favorable_ms`;
   - `UNDEFINED` for tie, never-favorable, invalid identity or zero observed
     duration.

No millisecond-difference threshold, gap cut, tick-count floor, latency,
magnitude, spread, clock, session, year or direction filter is legal. Raw
durations and `max_gap_ms` are reconciliation telemetry, not a grid.

## Formal OHLC and prior-feature non-sufficiency

Long `L=100`, decision horizon `[0,10]`. Both paths have the same ordered prices,
same OHLC and one favorable-to-adverse transition:

- A: `(0,101),(1,99),(9,109)` -> favorable `2`, adverse `8` ->
  `ADVERSE_DOMINANT`.
- B: `(0,101),(8,99),(9,109)` -> favorable `9`, adverse `1` ->
  `FAVORABLE_DOMINANT`.

Thus OHLC, ordered prices, HYP-020 any-recross and HYP-022 transition count are
all insufficient to reconstruct the label. Red-first tests must encode this
pair before source build authority.

## Online ownership and source delta

- Add only signal mode `6`, `SIGNAL_TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION`.
- Add setup-owned resilience state and a compact active-slot registry separate
  from the terminal mode-5 state. Never share counters between setup slots.
- Store millisecond times in `long`: start, first favorable, last valid,
  favorable duration, adverse duration and maximum gap.
- Reuse HYP-012 setup creation, duplicate handling, day/three-bar timeout,
  close invalidation and confirmation without threshold changes.
- Add `LevelResilience` CSV plus RunMeta counters. At confirmation write
  HumanContext + LevelResilience, clear the setup and never call an order path.
  Lifecycle, TickInitiation and LevelPath remain header-only in mode 6.
- `OnInit` clears incomplete state; never reconstruct tick paths from OHLC.
- Version/identity, mode-6 state/telemetry and exact no-trade branch are the
  only legal changes. Parent risk, stop, target and management inputs stay dormant.

## One authorized collection run

- AlphaFactory portable FivePercent runtime on `D:`.
- EURUSD M5, Model `0`, `2018.01.01` through `2026.07.19`.
- `InpResearchAutoMode=false`, telemetry on, news off, magic `5600733`.
- Preset: `presets/EURUSD_M5_HYP024_TIME_RESILIENCE_COLLECT.set`.
- Exactly one run after registry/prereg hashes, red-first tests, compile `0/0`,
  exact-source non-repaint PASS and fresh source-to-EX5-to-compile-log receipt.
- Required sidecars: LifecycleTrades, HumanContext, TickInitiation, LevelPath,
  LevelResilience and RunMeta. All trade sidecars and non-mode sidecars must
  contain zero data rows.
- Parser may read only identity/history/tick counts, row counts,
  LevelResilience frozen fields, HumanContext decision identity and frozen
  RunMeta counters. Report economics, exits and all future-price fields are
  forbidden.

## Frozen gates

All are required:

1. engineering tests pass; full regression passes; compile `0/0`; non-repaint PASS;
2. exact source/receipt, Model `0`, history quality at least `99%`, contiguous
   TKC coverage and nonzero tester ticks;
3. entries attempted/opened `0`; Lifecycle, TickInitiation and LevelPath data
   rows `0`;
4. unique event IDs; one HumanContext/LevelResilience pair per confirmation;
   start equals sweep close; `last_valid_msc<decision_msc`; no post-decision tick;
5. defined path fraction at least `99%`;
6. FAVORABLE_DOMINANT and ADVERSE_DOMINANT each occur at least `2.0` per elapsed
   calendar week and cover both directions, London/New-York and every year;
7. both label shares are at least `20%`, pooled and separately in `2018-2022`
   and `2023-YTD`;
8. duration reconciliation is exact for every defined row:
   `favorable_ms+adverse_ms=decision_msc-first_favorable_msc`;
9. deterministic parser replay reproduces the same hash;
10. no economic/future field appears in the parser allowlist or result.

Fail any gate -> `KILL_AT_HYP024_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`. No
duration threshold, gap filter, tick floor, count predicate, label inversion,
session, direction, year or repeated run may rescue the ID.

## Only legal successor if every gate passes

A separate pre-economic HYP-025 may compare unchanged HYP-012 control with one
frozen natural dwell-policy challenger under identical stop, 2R, management,
sessions and risk. Which label is the challenger must be justified before any
outcome access, not chosen from profitability. Historical cost provenance
remains failed, so any survivor is diagnostic and not promotion/paper/live evidence.

