# ROUND L8 — V8b: the budget mechanism simulated (paired A/B, one code state)

`levels_lab.py` gained the live-budget gate (`_budget_ok`): when the live
pool for a type is full, a challenger births only if it beats the weakest
live member on `live_score = n_def − dist_abr + 1.0·ret24` (ret24 = a
defence touch within 24 bars); the loser closes `superseded` and can
revive. All numbers below are the same engine build, three param sets,
198 TUNE panels, eval_v2 `50e11fd5`.

| config | LC v2 recall | LC trusted | MINI v2 | snapshot LC | live@τ (med) | born/panel (med) |
|---|---|---|---|---|---|---|
| uncapped (accepted) | **0.729** (35/48) | 0.825 | **0.677** | 0.596 | 6 | ~14 |
| budget 3 LC + 2 MINI | **0.729** (35/48) | 0.825 | 0.645 | 0.596 | ~5–6 | ~11 |
| budget 2 LC + 1 MINI | 0.667 (32/48) | 0.750 | 0.548 | 0.553 | ~4 | ~9 |

Engine baseline for reference: LC 0.146, MINI 0.065.

## Reading

1. **The budget costs almost nothing in born recall at 3+2** (0.729 =
   uncapped) and only −0.06 LC at 2+1. Reason: evicted levels revive on
   re-approach, and born recall counts any birth overlapping the golden
   span — budget churn is cheap ink, not lost coverage.
2. What the budget actually controls is **simultaneous live ink**:
   live@τ 6 → ~4 at 2+1, born stream 14 → ~9/panel. That is the
   author's-budget dimension the V8 matched-ink test measured (recall@k
   at τ), and where lab beat prod/naive under CV (ROUND_L7).
3. Snapshot-lens LC holds at 0.596 with 3+2 and dips to 0.553 at 2+1 —
   consistent with the recall@k tables (k3 ≈ .42, k2 ≈ .33 on the live
   pool).
4. `suppressed_budget` events are logged in cand_log, so the funnel can
   tell family-internal suppression from salience rejection.
5. Caveat for integration: the simulated budget uses the lab ranker at
   birth time; at τ a level's live_score drifts (n_def accrues touches).
   The mechanism matches the recall@k analysis because the ranker is
   re-evaluated live — no hidden look-ahead.

## Where the budget hurts (2+1 vs uncapped, per-golden diff)

8 goldens lost, 1 gained. Loss mechanisms:

- **True suppression** (slot full at approach time, no later birth in
  span): ~4–5 — e.g. `9.66c` LC @12395.1 (uncapped born bar ~184; under
  budget no LC ever freed a slot), `9.66a` MINI ×2, `9.21b`.
- **Edge/reprice drift** (a different challenger won the band once
  eviction changed competition order; birth price moved 2–4p out of
  tol): ~3 — `9.52a` (born 12928.6 vs golden 12931.6; uncapped held
  12932.5), `9.57b`.
- Gained: `9.59a` — eviction freed the slot for a better-timed birth.

Suppression volume: `suppressed_budget` events = **23 588 / 198 panels
(~119/panel)** — the trigger re-fires every bar while the pool is full,
so the family is heavily self-throttled (this is salience pressure the
production stream never has to see). Of those, 453 sat inside a golden
span+tol but only ~5 cost a match — the rest were redundant re-attempts
on already-covered goldens.

Reading: the −0.06 LC / −0.13 MINI cost at 2+1 is concentrated in
*busy* panels where >2 defended origins compete. That is the intended
trade — the author's ink is 2 objects, so a panel with 5 live defended
levels is precisely what the author would not draw.

## Config delta

```jsonc
"level_max_live": 2,   // or 3 — see table; NOT 1 (CV k=1: lab loses)
"mini_max_live": 1,    // or 2
"ret24_bars": 24,
```

No other change vs the accepted config. Tests `test_levels_lab.py`
4/4 pass — two new known-answer tests cover the gate: a stronger
challenger must evict the weakest incumbent (`superseded` event), a
weaker one must be suppressed with `suppressed_budget` logged and no
ink spent. Budget is off by default (cap 0).
