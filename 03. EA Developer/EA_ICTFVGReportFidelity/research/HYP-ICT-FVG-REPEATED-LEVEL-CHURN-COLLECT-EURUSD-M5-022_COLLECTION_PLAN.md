# HYP-022 — frozen repeated swept-level churn collection

## Identity and epistemic boundary

- Hypothesis: `HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022`.
- Parent scaffold: immutable terminal HYP-018 source SHA-256
  `41536FFC43BE85B1250A627197BD63FED5C7D5C7CF87D8965163F5449EACDA40`,
  retaining the exact HYP-012 sweep/reclaim and bounded three-bar confirmation.
- HYP-020 is killed pre-source because its 0-vs-any-recross bit is recoverable
  from OHLC extrema. HYP-022 changes the research object, not merely the ID:
  **multiplicity of repeated level re-entry**, which OHLC cannot recover.
- This is one zero-trade, outcome-blind data-acquisition/de-dup gate. It cannot
  establish edge, reopen any terminal parent, or authorize paper/live use.

Independent adversarial Grok review:
`.context/grok_ictfvg_hyp020_path_order_20260719/run2/grok-response.json`.
It must be hash-bound before source work and remains advisory only.

## Frozen measurement

For each existing HYP-012 setup:

1. `D=+1` long or `-1` short. Structural level `L` is `sweep_low` for long and
   `sweep_high` for short.
2. Interval is `[sweep_bar_close, confirmation_decision)`. On a new M5 bar the
   closed bar is processed before the new-bar tick is accumulated, so confirmed
   setups cannot consume the post-confirmation tick while newly detected sweep
   setups do consume their first post-sweep tick.
3. A valid quote has finite positive bid/ask and `ask>=bid`; `mid=(bid+ask)/2`.
4. Side is favorable when `D*(mid-L)>0`, adverse when `<0`; exact equality is
   sticky and undefined until the first strict side.
5. After the first favorable tick, increment `adverse_reentry_count` only on a
   strict `FAVORABLE -> ADVERSE` transition. Further adverse ticks cannot
   increment until at least one favorable tick occurs.
6. At the unchanged closed-bar confirmation:
   - `ORDERLY` when the path is defined and count is `0` or `1`;
   - `REPEATED_CHURN` when defined and count is at least `2`;
   - `UNDEFINED` otherwise.

No alternate count cut is legal. Raw count is telemetry for reconciliation, not
a grid. No latency, magnitude, tick-count, spread, clock, session, year or
direction threshold may be evaluated.

## Formal OHLC non-sufficiency

Long `L=100`; both paths have `O=101, H=110, L=99, C=109`:

- `101 -> 110 -> 99 -> 109`: count 1 → `ORDERLY`.
- `101 -> 99 -> 105 -> 99 -> 109`: count 2 → `REPEATED_CHURN`.

Red-first tests must encode this pair. A second regression must prove the killed
HYP-020 predicate (0 vs >=1) collapses to the OHLC pierce bit when the first mid
is favorable. Source build is forbidden until both tests fail on the parent and
pass on the child reference/state implementation.

## Online ownership and source delta

- Add only signal mode `5`, `SIGNAL_REPEATED_LEVEL_CHURN_COLLECTION`.
- Per `SetupState` slot store: stable slot ID, level, interval start, last update,
  current side, first-favorable flag/time, valid/invalid ticks and adverse
  re-entry count.
- Maintain a compact active-index list so Model-0 does not scan all 48 slots on
  every tick. Clear marks its slot inactive; the accumulator compacts stale
  indices before updates. Counters can never be shared between slots.
- Reuse HYP-012 setup creation, duplicate handling, day/three-bar timeout,
  close invalidation and confirmation without threshold changes.
- Add `LevelPath` CSV plus RunMeta counters. Existing TickInitiation CSV stays
  header-only in mode 5. At confirmation write HumanContext + LevelPath, clear
  setup and never call an order path.
- `OnInit` clears incomplete paths; never backfill ticks from OHLC.
- Version/identity, telemetry schema and exact mode-5 branch are the only legal
  source changes. Parent stop/2R/management/risk inputs remain dormant.

## One authorized collection run

- AlphaFactory portable FivePercent runtime on `D:`.
- EURUSD M5, Model `0`, `2018.01.01` through `2026.07.19`.
- `InpResearchAutoMode=false`, telemetry on, news off, magic `5600731`.
- Preset: `presets/EURUSD_M5_HYP022_REPEATED_CHURN_COLLECT.set`.
- Exactly one run after registry/prereg hashes, red-first tests, compile 0/0,
  exact-source non-repaint PASS and fresh source→EX5→compile-log receipt.
- Required sidecars: LifecycleTrades, HumanContext, TickInitiation, LevelPath,
  RunMeta. Lifecycle and TickInitiation must contain zero data rows.
- Parser may read only identity/history/tick counts, row counts, LevelPath
  fields, HumanContext decision identity and frozen RunMeta counters. Report
  economics, exits and all future price fields are forbidden.

## Frozen gates

All are required:

1. engineering tests pass; compile `0/0`; non-repaint PASS;
2. exact source/receipt, Model `0`, history quality at least `99%`, contiguous
   TKC coverage and nonzero tester ticks;
3. entries attempted/opened `0`; Lifecycle and TickInitiation data rows `0`;
4. unique event IDs; one HumanContext/LevelPath pair per confirmation; start
   equals sweep close; last update is strictly before decision;
5. defined path fraction at least `99%`;
6. ORDERLY and REPEATED_CHURN each occur at least `2.0` per elapsed calendar
   week and each covers both directions, London/New-York and every year;
7. both label shares are at least `20%`, pooled and separately in `2018-2022`
   and `2023-YTD`;
8. deterministic parser replay reproduces the same hash;
9. no economic/future field appears in the parser allowlist or result.

Fail any gate → `KILL_AT_HYP022_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`. No count
cut, latency, spread, time, session, direction, year or label inversion may
rescue the ID.

## Only legal successor if every gate passes

A separate pre-economic HYP-023 may compare unchanged HYP-012 control with one
frozen `ORDERLY`-only challenger under identical stop, 2R, management, sessions
and risk. One matched Model-0 pair only. Historical cost provenance remains
failed, so any survivor is diagnostic and not promotion/paper/live evidence.

