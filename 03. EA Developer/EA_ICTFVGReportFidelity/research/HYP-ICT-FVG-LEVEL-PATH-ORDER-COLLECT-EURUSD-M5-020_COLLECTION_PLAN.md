# HYP-020 — frozen swept-level path-order collection

## Identity and boundary

- Hypothesis: `HYP-ICT-FVG-LEVEL-PATH-ORDER-COLLECT-EURUSD-M5-020`.
- Parent scaffold: terminal HYP-012 bounded three-bar confirmation as preserved
  by terminal HYP-018 source snapshot SHA-256
  `41536FFC43BE85B1250A627197BD63FED5C7D5C7CF87D8965163F5449EACDA40`.
- HYP-018 remains killed. HYP-019 was never opened. This successor is a new
  **zero-trade, outcome-blind data-acquisition/de-dup gate**, not a rescue and
  not an economic test.
- The new information object is event order around the setup's structural
  swept extreme across the live setup interval. It is not full-bar tick sign,
  imbalance magnitude, a spread filter, or an OHLC threshold.

Independent local-only Grok Build review selected this mechanism over
confirmation-bar extreme order and half-bar sign sequencing. Its response is
read-only evidence, not authority: `.context/grok_ictfvg_hyp020_path_order_20260719/run1/grok-response.json`,
SHA-256 `D1F77747E14E4854BD0166709F0EEE05B0F82E54932AFD2F0AD7DCC16DF78970`.

## Mechanism under test

For every HYP-012 setup, create one path state when the closed sweep/reclaim bar
is detected:

1. Direction `D` is `+1` long or `-1` short.
2. Structural level `L` is the actual sweep extreme: `sweep_low` for long and
   `sweep_high` for short. This preserves the parent stop anchor.
3. Interval is `[sweep_bar_close, confirmation_decision)`. The detection/new-bar
   tick at the sweep close belongs to the interval. The first tick of the bar
   after the confirmation bar never belongs to the confirmed setup.
4. A quote mid is valid only when bid/ask are finite and positive and
   `ask>=bid`; `mid=(bid+ask)/2`.
5. Directed side is favorable when `D*(mid-L)>0`, adverse when `<0`. Exact
   equality holds the prior side; if no prior side exists it remains undefined.
6. `first_favorable` is the first strict favorable tick. After that,
   `adverse_reentry_count` increments only on a strict transition
   `FAVORABLE -> ADVERSE`. Further adverse ticks do not increment until price
   first returns favorable.
7. At the unchanged closed-bar HYP-012 confirmation, label `CLEAN` when the path
   is defined and adverse-reentry count is zero; label `CHURN` when defined and
   the count is at least one; otherwise `UNDEFINED`.

The raw count is diagnostic only. There is no alternate count cutoff, latency,
tick-count, spread, year, session, direction or magnitude arm.

## Online state and ownership

- State is owned by each existing `SetupState` slot: level, start time, last
  tick time, current side, first-favorable flag/time, valid/invalid tick count
  and adverse-reentry count.
- Active setup indices are maintained separately so Model-0 does not scan all
  48 slots for every historical tick. Cleared slots are compacted before the
  next accumulation. A slot cannot share counters with another setup.
- On a new M5 bar: seal the old global HYP-018 bar profile; process the just
  closed M5 bar (which confirms/clears old setups and creates new sweeps); only
  then accumulate the current first tick into remaining/new HYP-020 setup
  paths. This ordering excludes the post-confirmation tick while including the
  first post-sweep tick.
- `OnInit` clears any path that cannot be reconstructed. There is no tick
  backfill, restart reconstruction or inference from bar OHLC.

## Frozen source delta

- Add only signal mode `5`, `SIGNAL_LEVEL_PATH_ORDER_COLLECTION`.
- Reuse HYP-012 sweep detection, duplicate suppression, timeout, close
  invalidation and confirmation rules exactly. Do not change stop, 2R target,
  management, sessions, risk, clock or Human Context calculations.
- Add one `LevelPath` telemetry sidecar and RunMeta counters. The existing
  TickInitiation sidecar may remain open but must contain zero data rows in mode
  5; HYP-018 sign is not evaluated.
- At confirmation write HumanContext + LevelPath, clear the setup and never call
  `TryOpenTrade` or any order path.
- `InpResearchAutoMode=false`, telemetry on, news off, magic `5600729`.

## One authorized collection run

- AlphaFactory portable FivePercent runtime on `D:` only.
- EURUSD M5, Model `0`, `2018.01.01` through `2026.07.19`.
- Exactly one tester collection after red-first tests, compile, exact-source
  non-repaint audit, fresh source→EX5→compile-log receipt and green registry.
- Preset: `presets/EURUSD_M5_HYP020_LEVEL_PATH_COLLECT.set`.
- Required sidecars: LifecycleTrades, HumanContext, TickInitiation, LevelPath
  and RunMeta, all identity-bound. Lifecycle and TickInitiation data rows must
  be zero.
- Parser allowlist: identity, model/history/tick counts, lifecycle/tick-init row
  counts, LevelPath fields, HumanContext decision identity and frozen RunMeta
  counters. Tester economics and all future labels are forbidden.

## Frozen pre-economic gates

All gates are required:

1. tests pass; compile `0/0`; exact-source non-repaint PASS;
2. exact source/receipt, Model `0`, history quality at least `99%`, contiguous
   monthly TKC coverage and nonzero tester ticks;
3. entries attempted/opened `0`; Lifecycle and TickInitiation data rows `0`;
4. unique event IDs; one HumanContext/LevelPath pair per confirmation; interval
   start equals sweep-bar close; last included tick is strictly before decision;
5. at least `99%` of confirmations have defined path labels;
6. CLEAN and CHURN each occur at least `2.0` per elapsed calendar week and each
   covers both directions, London/New-York and every calendar year;
7. CLEAN and CHURN shares are each at least `20%`, pooled and separately in
   `2018-2022` and `2023-YTD`;
8. deterministic parser replay reproduces the same result hash;
9. no economic or future-price field appears in the parser input allowlist or
   collection result.

Fail any gate → `KILL_AT_HYP020_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`. No
threshold, count cutoff, split, clock, session or label inversion may rescue
this ID.

## Only legal successor if every gate passes

A separate pre-economic HYP-021 may compare the unchanged HYP-012 control with
one `CLEAN`-only challenger using identical stop, 2R, management, sessions and
risk controls. It must freeze before reading any HYP-020-corresponding price
outcome and use one matched Model-0 pair. Historical cost provenance is still
failed, so even a survivor remains diagnostic and cannot be promoted, papered
or traded live until that independent blocker is resolved.

