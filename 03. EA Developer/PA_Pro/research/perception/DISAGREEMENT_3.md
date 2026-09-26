# DISAGREEMENT_3 — B3 round 3: rate-slot ordering, candidate lifetime,
# and the dead-footprint grave

Date: 2026 (B3, third and final disagreement round).  Scope:
`salience.py` selection semantics only — no geometry changes this
round.  v1 metrics vs end of round 2:

| metric | r2 end | r3 | gate |
|---|---|---|---|
| BOX recall | 0.12 (13/111) | **0.16 (18/111)** | >=0.70 |
| PATTERN_LINE recall | 0.02 (2/186) | 0.03 (5/186) | >=0.50 |
| LEVEL_CARRIED recall | 0.04 (2/48) | 0.08 (4/48) | — |
| MINI_LEVEL recall | 0.03 (1/32) | 0.09 (3/32) | — |
| BRACKET recall | 0.02 | 0.01 | — |
| RANGE_OPEN recall | 0.25 | 0.25 | — |
| clutter median | 4.33 | **4.33** | <=1.5 |
| BOX born | 298 | 303 | — |
| re_anchor events | 739 | 755 | — |

## Experiments run (each full-evaluated on TUNE, keep/revert by numbers)

### A. `cand_ttl_bars` 24 -> 72 — REVERTED

Hypothesis: right-geometry candidates (48 of them in r2) sit in the
pool behind a spent rate slot and die on ttl before the 72-bar rate
window rolls.  Raising ttl to the window should let them compete.

Measured: BOX 13->10, PATTERN_LINE 4->2 — worse.  A deeper pool means
more competition per freed slot and stale candidates win on stale
evidence.  The bottleneck is not candidate lifetime.

### B. Rate-slot displacement (challenger refunds holder's ledger entry)
— REJECTED

Two variants measured:

- displace the most recent live same-kind holder when challenger wins
  by `hyst_margin` and holder passed `dwell_bars` or is dead/broke:
  BOX recall 0.22 (24) but born 723, clutter 5.67, re_anchor 1064.
- restrict holders to `dead|broke` only (slot recycled only when the
  structure's own lifecycle finished): BOX 0.24 (27), born 799,
  clutter 6.00.

The recall gain is bought with volume, not better selection — per-birth
hit rate stayed ~0.03 either way.  Mechanism: boxes die often
(post_break_window), and each refunded slot converts a death into a
re-birth, so births/window = cap + deaths-in-window — the ledger stops
measuring the golden statistic (births per window) and starts
measuring live structures per window.  Golden's ~1 box per panel is a
birth count; the honest accounting keeps the dead object's entry in
the ledger until it rolls out.

Final form: **no refund, no rate-slot displacement** — `rate_limited`
stays a pure rejection and the candidate waits in the pool.

### C. Band-grave persistence + same-bar close race — KEPT

Two real bugs found in the death/rebirth path:

1. `_grave_band` was populated at the END of the round.  `maintain`
   closes objects before `round()` runs, so a box that died on bar i
   left no shadow while bar i's births were processed — the canonical
   churn trace (9.1a: box dies 410min, next box born 410min) slipped
   through the same-bar seam.  Population moved to the TOP of
   `round()`, before candidate scoring.

2. Wide-band grave TTL was `cand_ttl_bars` (24 bars).  A congestion
   footprint outlives that by 5x — golden draws a box once per
   episode; the broken edge continues as LEVEL_CARRIED, not as a new
   box.  Wide footprints (band > ABR) now shadow the rest of the
   session.  The existing same-episode clause (`cand.t0 >=
   dead.t_right` -> not the same episode) still admits a genuinely new
   buildup in the band, so this is causal-safe: it only blocks
   candidates whose own buildup reuses bars from inside the dead
   object's drawn span.

Measured at constant volume (303 vs 298 born, clutter identical
4.33): BOX matched 13->**18**, PATTERN_LINE 2->5, LEVEL_CARRIED 2->4,
MINI_LEVEL 1->3.  Same ink, better aimed — the same-episode rebirths
that used to spend slots are gone and the freed slots land on
different (better) candidates.

## Funnel after round 3

- BOX: ~74/111 golden boxes still get a right-geometry proposal
  (unchanged — generation untouched this round); 18 match.  The
  remaining loss is `rate_limited` waits that are now permanent when
  the slot was spent on a same-episode predecessor that (correctly)
  refuses to die.
- The ledger is now honest: births per 72-bar window <= per-kind cap,
  and `outranked` events only come from budget-class displacement
  (unchanged DN_SALIENCE stage-4 rule).

## Still open (deferred to RT5 / future rounds)

- **PATTERN_LINE**: 5/186.  Expressibility ceiling is real — ~30% of
  golden lines have no confirmed-pivot pair within 6p of both
  endpoints even with named-bar anchors.  Selection among expressible
  ones remains weak.
- **BRACKET** 1/85, **CONTEXT_RANGE** 0/6, **SQUEEZE** 0/2: never
  investigated structurally this round; bracket needs its own funnel
  analysis (propose-rate vs selection).
- **Clutter 4.33 vs gate 1.5**: all remaining volume is spread across
  kinds (each at its measured per-kind cap); cutting further means
  cutting caps below golden p90, which trades recall for ink — not
  attempted.
- **Span offsets**: golden t0 precedes build_start ~10 min median;
  engine t0 = first contained close.  Untouched.
- LABEL_TF agreement on matched boxes: 0/6 — box TF label source
  still wrong even when geometry matches.
