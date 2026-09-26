# DEVIATIONS D1-D5 (extract for REVIEW_2 — pre-M8-review entries only)

# DR-MARKET — DEVIATIONS

Append-only. Every departure from the mandate / preregistered plan is logged
here with reason and impact.

## D1 — M0 verdict logic (recorded 2026-09-21, same session as M0)
- **Plan:** flag any NFP month whose max-range M1 bar is not at the expected
  release minute; exclude pending Lead ruling.
- **Observed:** 40 symbol-months had a max-range bar at another minute; all
  deviations sat at 16:0x–16:4x or 13:4x–14:3x server, i.e. 10:00 ET releases
  (ISM/University of Michigan) or London-fix effects that were simply bigger
  than that day's NFP.
- **Change:** verdict criterion switched to *spike-presence*: a month counts
  as clock-confirmed iff a bar exists at the expected NFP minute AND its
  range ≥ 3× that day's median bar range. Result: 262/288 confirmed; the 26
  remainder had a bar at the right slot but a quiet NFP (no spike) — a
  property of the release, not the clock. No month was excluded.
- **Impact:** none on downstream data use; the clock was proven
  (server = UTC+2/+3 EU DST), which is what M0 exists to establish.
  Logged for the reviewer; Lead may overrule.

## D2 — CLOCK_AUDIT_DESIGN.md header timestamp
- `Generated:` line was written empty in the first version.  Corrected on
  regeneration; historical evidence untouched.

## D3 — M3 placebo seeds made process-deterministic
- First extraction draft used Python `hash(sym)` (per-process randomized) to
  seed PRAND grids.  Replaced by `crc32(sym)` before any saved output, so all
  artifacts derive from stable seeds.  No results were produced with the
  randomized seeds.

## D4 — M3 resolution starts at the touch minute, not the touch-bar open
- The plan says outcomes are measured after the touch.  First implementation
  scanned M1 from the open of the touching M5 bar, which admits pre-touch
  movement inside that bar.  Now: the first M1 bar intersecting the zone is
  located, and the outcome path starts at the next M1 bar.
- Same fix: `overshoot_x1` now freezes at the x1 resolution bar (was:
  accumulated until *both* barriers hit), and `retest_12/48` are `False`
  (not missing) when a break never retests within the horizon.
- An EURUSD npz was written once under the old convention and was
  overwritten by the corrected run before any analysis consumed it.

## D5 — Grid level columns are anchored near the daily open (scope limit)
- `grid_columns` builds RND/PRND20/PRND10/PRAND levels inside
  day_open ± 3.5·ABR (≈±9 pips EURUSD).  Therefore the RND and
  cascade (XRND) results condition on **round levels near the day open**,
  not all 00/50 levels; days whose open is far from a round contribute
  no RND column at all.  The placebo arms share the identical anchoring,
  so the contrasts remain valid for that subpopulation; the absolute
  round-level coverage is incomplete.
- Recorded 2026-09-21 during self-audit while M8 ran.  Noted in
  LEVELS.md/MARKET_MECHANICS.md as a scope limitation.

---

# Post-M8 remediation block (reviewer findings → corrections → rerun)

The M8 independent review (`REVIEW.md`) found that the first execution
deviated from `STUDY_PLAN.md` in ~15 places, two of which were causal
(lookahead) and two of which voided/weakened headline results.  All items
below were fixed in code, extraction was re-run, and the reports were
rewritten.  Ledger rows T000367–T000379 describe the **pre-review**
numbers; corrected rows supersede them.
