# HYP-ECRS-EURUSD-M5-002 — Stage-0 v2 Readout (TERMINAL: PARK, no outcome read)

Date: 2026-07-23 (UTC)
Lane: `EA_ECRS_CompressionReleaseScalper` — EURUSD M5, ECRS re-scope with the
tick-volume surge gate REMOVED (Owner-approved Option A, 2026-07-23).
Parent: `HYP-ECRS-EURUSD-M5-001` (parked 2026-07-22, same package).
De-dup/legality memo: `04. Memory/research/20260723_ECRS_002_DEDUP_READOUT.md`
(pre-declared cadence gate: pooled 2019-2022 eligible-entry rate >= 1.0/week
before any freeze, else park like 001).

## Verdict

`PARK_STAGE0_CADENCE_INFEASIBLE_NO_OUTCOME_READ`

Removing the volume gate raised frequency only 3.75x: **30 eligible entries /
208.71 elapsed weeks = 0.1437/week** — still 7x below the pre-declared
>= 1.0/week floor and 14-35x below the GOAL band (2-5/week). 209 calendar
weeks contain 182 with zero entries; max 2 in any week. As with 001, **no
trade outcome, PnL, forward return, or excursion was ever computed** (chain
verified: `c1..c8` contains no volume term; only forward reads are entry-bar
time/open/spread).

## Evidence (hash-bound)

| Artifact | Path (relative to `research/`) | SHA256 |
|---|---|---|
| Stage-0 v2 scanner | `preflight/stage0_scan_v2.py` | `A456D7723A2CC484F53733731B53A6E52C296541CE1105F3B6A37FABD96B98B3` |
| Funnel v2 JSON | `preflight/stage0_funnel_v2.json` | `70B9083230E5EF3E1A2B7CCEE9B262295AF3A50F9F7E65F106FCE6013A202B10` |
| Candidate cases CSV (30, with `tickvol_ratio` diagnostic) | `preflight/stage0_candidate_cases_v2.csv` | `B928808E77409337AD806FBCBAFDC9F4DC345C9585654EDFE97B63A469C51A74` |
| Rendered asof manifest (30 PNG, cutoff enforced) | `preflight/cases_asof_v2/cases_manifest.json` | `EF410E878F56224D965452367B8B374FEC8E4ED1DDAFC82277C8EE728BE08546` |
| Derived M5 parquet | reused byte-identical from 001 (`A2DDF0D4...89053532`) | — |

Input M1 parquet + news CSV: same manifest-matched SHAs as 001's readout.
Seal receipt: `holdout_bars_loaded=0`, last bar 2022-12-30 21:59 UTC.

## Funnel (pooled 2019-2022, no volume gate)

```
n_bars 298,483
G1  ER shift                        15,780
G2  + ATR compression (t-1)          1,092
G3  + 12-bar range breakout            462
G5  + EMA20 bias alignment             434   (2.08/week, all hours)
G6  + session 07:00-16:30 UTC           39   <- dominant cut, -91%
G7  + news blackout +/-45min            39
G8  + spread 0<sp<=0.8 pip              30   (10 long / 20 short)
```

Internal consistency proof: finals that would also pass the old 1.7x volume
gate = 8 = exactly 001's final count. Weakened 1.2x line = 11 (also
infeasible). Per-year finals 2019-2022: 12/6/4/8.

## Mechanism findings (frequency-plane, outcome-blind)

1. **The volume gate was not the binding constraint.** The core joint
   ER-shift ∧ compression ∧ breakout ∧ bias produces only 434 events in 4
   years (2.08/week) across ALL hours. The London-NY session keeps 9% of
   them. That product (~0.19/week) is the family's structural ceiling for
   any in-session object; no peripheral gate softening changes it.
2. **The report's volume narrative does not describe its own core:** median
   `tickvol_ratio` of the 30 finals is 0.846 — 19/30 in-session
   release events fire on BELOW-baseline tick volume.
3. Off-session concentration persists without the volume gate (23:00 UTC
   peak 68, 17:00 55 of 434) — it is a property of the compression/release
   core near rollover, not an artifact of the volume baseline.
4. With the larger population the fail-closed spread gate now binds (39->30
   removed 9), consistent with the 29.3% zero-spread rate in-session.

## Radius

- CLOSES: `HYP-ECRS-EURUSD-M5-002` (no-volume-gate ECRS object, EURUSD M5,
  London-NY session) as cadence-infeasible. Terminal; ID never revived.
- FAMILY FRONTIER (both memos' forbidden-rescue lists now exhausted for
  in-session EURUSD M5 at report thresholds): the remaining legal openings
  are (a) an OFF-session ECRS object (22:00-00:00 UTC habitat) — new ID,
  adverse rollover-cost prior, contradicts the report's session thesis; or
  (b) materially different core thresholds/geometry — but ER-pair/ATR-ratio/
  lookback retunes are pre-listed as forbidden rescues in both memos, so any
  such proposal must argue a genuinely different mechanism, not a knob turn.
- DOES NOT CLOSE: economic edge (never measured, 0 outcomes read across the
  entire family); other symbols (untested; same joint-rarity logic likely).

## Session provenance

v2 scanner built/run by an Opus 4.8 sub-agent; parent verified: gate-chain
code (no volume term in `c1..c8`, same 4 allowed `shift(-1)` reads), funnel
consistency vs v1 (identical shared prefixes 15,780/1,092/462; 1.7x
reference line reproduces 001's final count of 8), seal receipt, and visual
inspection of rendered asof cases.
