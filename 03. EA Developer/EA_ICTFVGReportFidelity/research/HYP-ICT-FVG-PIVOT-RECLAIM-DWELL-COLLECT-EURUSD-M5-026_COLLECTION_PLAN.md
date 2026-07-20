# HYP-026 — frozen swept-pivot reclaim dwell collection

## Identity and epistemic boundary

- Hypothesis: `HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026`.
- Parent implementation: immutable terminal HYP-024 source SHA-256
  `3BC2130CE8F84AF44C6D3EFEC0639A7B461907A096A6AE90636479E6BB40E77B`.
- HYP-024 remains terminal. Its sweep-extreme dwell label was mechanically
  near-tautological under the unchanged confirmation/invalidation filter.
  HYP-025 was not opened.
- HYP-026 asks one different structural question: after a closed sweep/reclaim,
  does quote mid spend more time on the reclaimed or re-accepted side of the
  **exact pivot breached by the sweep bar**? It changes neither the HYP-012
  scaffold nor any terminal verdict.
- This is one zero-trade, outcome-blind data-acquisition/de-dup gate. It cannot
  establish edge or authorize economics, paper/live use or promotion.

Independent post-HYP-024 adversarial review:
`.context/grok_ictfvg_hyp024_postrun_20260720/run1/grok-response.json`, SHA-256
`20D8254D63AC0899ECF55DB513DAC7F2FDF42C0B3BB17A54C61C7FB2BAE3D474`.

## Structural basis, not an edge claim

- The pivot is already computed point-in-time by `FindLatestM5Pivots` and is the
  exact level used by `DetectSweep` to require a breach and closed reclaim.
- For a short, `pivot_high < sweep_high`; quote mid can trade in
  `(pivot_high, sweep_high)` without triggering the unchanged close-at-extreme
  invalidation. For a long, the symmetric interval is
  `(sweep_low, pivot_low)`.
- Therefore dwell around the pivot is not forced by the confirmation scaffold.
  A setup may spend most of its observed time on the adverse side of the pivot,
  remain inside the sweep extreme, and then close through the opposite sweep
  extreme to confirm.
- Market-resilience and quote-time references remain the primary sources frozen
  in HYP-024: Obizhaeva and Wang (NBER 11444), Cont, Stoikov and Talreja
  (Operations Research), BIS Working Paper 405 and the MQL5 `MqlTick.time_msc`
  reference. They motivate measurement only; retail broker quote-mid is not
  signed institutional flow or full depth.

## Frozen measurement

For every unchanged HYP-012 setup:

1. `D=+1` long or `-1` short. `L_pivot` is exactly `pivot_low` for the long
   breach/reclaim and `pivot_high` for the short breach/reclaim, taken from the
   same `FindLatestM5Pivots` call used by `DetectSweep`. Store it at setup
   creation; never recompute it later.
2. Keep `sweep_low`/`sweep_high` unchanged for timeout, invalidation,
   confirmation and dormant risk geometry. They are not the measured level.
3. Interval, quote validity, monotone `time_msc`, equality-sticky behavior,
   invalid-quote behavior, prior-side duration carry, same-millisecond behavior
   and decision-tail seal are byte-semantically identical to HYP-024.
4. Time before the first strict favorable quote is discarded. At first
   favorable, begin the observed horizon. This anchor is deliberately unchanged
   so level geometry is the only measurement change.
5. Favorable means `D*(mid-L_pivot)>0`; adverse means `<0`.
6. Label:
   - `FAVORABLE_DOMINANT` iff `favorable_ms>adverse_ms`;
   - `ADVERSE_DOMINANT` iff `adverse_ms>favorable_ms`;
   - `UNDEFINED` for tie, never-favorable, invalid interval identity or zero
     observed duration.

No millisecond-difference threshold, gap cut, tick-count floor, magnitude,
spread, session, year, direction or HTF-context filter is legal.

## Formal non-tautology and OHLC non-sufficiency

### Same scaffold can produce either label around the pivot

Short example: `pivot_high=100`, `sweep_high=102`, `sweep_low=98`. Quote mid may
spend most of the window at `101` (adverse to pivot but still below the sweep
extreme), then a valid closed confirmation can finish below `98`. This is
`ADVERSE_DOMINANT` without violating the unchanged close-at-`102` invalidation.
The same path is favorable relative to HYP-024's wick tip, proving the geometry
is materially different.

### Identical OHLC cannot reconstruct duration dominance

Long `L_pivot=100`, decision horizon `[0,10]`, identical ordered prices and
identical OHLC:

- A: `(0,101),(1,99),(9,109)` -> favorable `2`, adverse `8` ->
  `ADVERSE_DOMINANT`.
- B: `(0,101),(8,99),(9,109)` -> favorable `9`, adverse `1` ->
  `FAVORABLE_DOMINANT`.

Only timestamps differ. Red-first tests must encode both the legal adverse
inside-wick path and this timestamp flip before source authority.

## Online ownership and legal source delta

- Add only signal mode `7`,
  `SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION`, identity v1.27/HYP-026 and one
  setup field `swept_pivot_level`.
- Extend `AddSweepSetup` so `DetectSweep` passes the exact pivot used in the
  breach predicate. Other signal modes retain their existing behavior.
- Reuse the setup-owned HYP-024 resilience accumulator and active-slot registry
  because signal modes are mutually exclusive; for mode 7 only, initialize
  `resilience_level=swept_pivot_level`. Do not change clock arithmetic.
- LevelResilience and HumanContext are the only nonempty decision ledgers.
  Lifecycle, TickInitiation and LevelPath remain header-only; no order path may
  execute. RunMeta must expose mode 7, exact identity and zero order counters.
- `OnInit` clears incomplete state; no tick path is reconstructed from OHLC.

## One authorized collection run

- AlphaFactory portable FivePercent runtime on `D:`.
- EURUSD M5, Model `0`, `2018.01.01` through `2026.07.19`.
- `InpResearchAutoMode=false`, telemetry on, news off, magic `5600734`.
- Preset: `presets/EURUSD_M5_HYP026_PIVOT_RECLAIM_DWELL_COLLECT.set`.
- Exactly one run after registry/prereg hash freeze, red-first tests, full
  regression, compile `0/0`, exact-source non-repaint PASS and fresh
  source-to-EX5-to-compile-log receipt.
- Parser may read only identity/history/tick counts, LevelResilience frozen
  fields, HumanContext decision identity, sidecar row counts and frozen RunMeta
  counters. Report economics, exits and future-price fields are forbidden.

## Frozen gates

All are required:

1. engineering and red-first contracts pass; compile `0/0`; non-repaint PASS;
2. exact source/receipt, Model `0`, history quality at least `99%`, contiguous
   TKC coverage and nonzero tester ticks;
3. entries attempted/opened `0`; Lifecycle, TickInitiation and LevelPath data
   rows `0`;
4. unique event IDs; one HumanContext/LevelResilience pair per confirmation;
   stored pivot equals the exact point-in-time sweep predicate level; pivot lies
   strictly inside the corresponding sweep extreme; no post-decision tick;
5. defined path fraction at least `99%`;
6. both natural labels occur at least `2.0` per elapsed calendar week and cover
   both directions, London/New-York and every year;
7. both label shares are at least `20%`, pooled and separately in `2018-2022`
   and `2023-YTD`;
8. exact duration identity for every defined row:
   `favorable_ms+adverse_ms=decision_msc-first_favorable_msc`;
9. deterministic parser replay reproduces the identical result hash;
10. no economic/future field appears in the parser allowlist or result.

Fail any gate -> `KILL_AT_HYP026_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`. No
level migration, threshold, gap/tick filter, label inversion, subgroup, repeat
run or economic HYP-027 may rescue this family.

## Only legal successor if every gate passes

A separate HYP-027 may be frozen before outcome access to compare unchanged
HYP-012 control with one natural pivot-dwell policy under identical entry,
stop, 2R, management, sessions and risk. The accepted label must be justified
structurally before any PnL read. Historical same-broker cost provenance remains
failed, so even a survivor is diagnostic and not promotion/paper/live evidence.
