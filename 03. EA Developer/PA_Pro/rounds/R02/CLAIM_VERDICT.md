# R02 - CLAIM VERDICT: E3 / line1_cluster (the round's single claim path)

Lead, 2026-09-21 ~03:30Z. This is written after the independent reproduction matched bit for bit.
Every number below comes from `research/arrival/_scratch/r02_outcomes/E3__line1_cluster.json`
(sha256 `6b568b36...ee42b`, executor A, 02:21:00Z).

## Provenance

- The Lead reproduced this file independently: bit-exact MATCH at 03:22Z. All 20048 floats are
  identical, and only the 2 sequential trial ids differ.
- Freeze: FREEZE_v3 `f0462985...` and PREREG `6d6c751c...`. The runner's integrity check passed in
  both the execution and the reproduction.
- Out-of-tree records (claude.ai project):
  - `pa-pro-r02-execution-seal-v3.md` (seal);
  - `pa-pro-r02-reexec-witness.md` (method, fixed before the result);
  - `pa-pro-r02-reexec-result.md` (MATCH).
- The descriptive units (the other E3 generators, E1R, E1RAW and E2) are NOT covered here. They are
  reported in ROUND_REPORT only after their own reproduction.

## Numbers (D = recent-arm minus stale-arm resolution rate, in percentage points)

| endpoint | cell | D (pp) | 95% CI (pp) | p (one-sided) | n recent | n stale | cap_share_stale |
|---|---|---|---|---|---|---|---|
| bounce | EURUSD | +3.21 | [+0.74, +5.62] | 0.0056 | 6993 | 5333 | 0.047 |
| bounce | GBPUSD | -0.04 | [-2.58, +2.32] | 0.524 | 6677 | 5249 | 0.057 |
| bounce | AUDUSD | +1.81 | [-0.39, +3.97] | 0.058 | 8395 | 6024 | 0.040 |
| bounce | USDJPY | -0.78 | [-3.11, +1.55] | 0.757 | 7556 | 5806 | 0.049 |
| **bounce** | **pooled (4 cells)** | **+1.04** | **[-0.19, +2.16]** | **0.048** | 29621 | 22412 | |
| continuation | EURUSD | -0.76 | [-5.10, +3.85] | 0.627 | 6993 | 5333 | 0.047 |
| continuation | GBPUSD | -3.38 | [-7.83, +0.76] | 0.946 | 6677 | 5249 | 0.057 |
| continuation | AUDUSD | -1.81 | [-6.08, +2.55] | 0.789 | 8395 | 6024 | 0.040 |
| continuation | USDJPY | -2.54 | [-6.61, +2.08] | 0.847 | 7556 | 5806 | 0.049 |
| **continuation** | **pooled (4 cells)** | **-2.12** | **[-4.27, +0.13]** | **0.968** | 29621 | 22412 | |

B = 10000. The p recipe is `p = (1 + #{D_b <= 0}) / (B + 1)`, one-sided. Here "(B+1)" means
n_boot + 1 = 10001; `REVIEW_R02_PREREG_5.md` records that this is how the recipe is read.

## Gates (PREREG §6, "Gates for an E3 claim"; all must hold)

| gate | bounce | continuation |
|---|---|---|
| >= 3 contributing cells (D37a) | 4, eligible | 4, eligible |
| D >= +5.0pp | +1.04, **FAIL** | -2.12, **FAIL** |
| CI lower bound > 0 | -0.19, **FAIL** | -4.27, **FAIL** |
| D > 0 in >= 3/4 (rounded up) of contributing cells | 2/4, **FAIL** | 0/4, **FAIL** |
| >= 4/6 DESIGN years within contributing cells | not evaluated, moot | not evaluated, moot |
| BH q <= 0.10 within the E3 family | moot (depends on unreproduced E3 units) | moot |
| >= 1,000 resolved events per arm, pooled | pass | pass |
| cap_share_stale <= 0.50 | pass (max 0.057) | pass |
| Adverse check (D13): CI upper < 0 | +2.16, no | +0.13, no (narrowly) |

## Verdict (pre-declared language only)

- **E3 / line1_cluster x bounce: the gate is NOT passed.** The bundled contrast "arrivals at
  recently-tested levels resolve differently from arrivals at long-untested ones" is **not
  supported** at the pre-declared bar. Not "recency ADVERSE".
- **E3 / line1_cluster x continuation: the gate is NOT passed.** Not "recency ADVERSE", because the
  CI upper bound is +0.13pp.
- **Round:** R02 carries **no claim**. There is no FULLY-CONFIRMED candidate, so under the winner rule
  **no winner is declared** ("if no fully-confirmed candidate exists, no winner is declared from
  estimates alone"). E1 is descriptive only (D41a). E2 is flagging only, and every E2 number carries
  the D42 label.

## Descriptive reading (not a claim)

The pooled estimates point the way recency would suggest. Arrivals at recently-tested zones bounce
about 1pp more and continue through about 2pp less; continuation is negative in all four cells.
But the magnitudes, 1-2pp, are far below the 5pp economic bar pre-registered for a claim, and both
CIs include zero. Taken with FINDING 1 (zone vs empty is not identifiable) and FINDING 2 (strength is
mostly recency), R02 says this: **zone recency alone is not a tradable edge at the scale we
required.** Zones stay a context and filter layer. Setups must earn their keep in the economic screen
against matched random entry (Blueprint v2.0, charter addendum 3 item 4).

## Known limitations attached to this verdict

- **D40:** FREEZE v1 was VOID (post-freeze code edit). **D41:** v2 could not be executed (claim-path
  defects). **D42:** E2 cell weight uses `len(ia)`. That affects E2 only, not this unit.
- **R02-A1 (open):** the bundles were built with `GenSource.run()`, whose `_step_all` approximation may
  miss late reclaims (>48 bars) and gap-bar breaks that exact replay would catch. Two lanes found it
  independently. Its size is to be measured outcome-blind. It cannot turn this null into a claim
  without a new round.
- **Cosmetic, in sealed code:** `write_reports()` prints the header "Freeze: FREEZE_v2.json sha256
  ..." whatever freeze was executed. The sha it prints is the real one (v3). This is flagged, not
  fixed, because the code is sealed.
