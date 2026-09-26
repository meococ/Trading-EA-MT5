# ROUND L7 — V8: selection at the author's budget (R17 §17.2)

Ruling-14 compliant: all deltas below are paired A/B at one code state
(`budget_r1.json`, harness `levellab/select_budget.py`, engine `ef06f265`,
lab proposer at the accepted config of `LEVEL_INTEGRATION.md` v1).

## Setup

Three proposers evaluated on the same 198 TUNE panels:

| stream | what it is | births/panel (med) | live@τ (med) |
|---|---|---|---|
| `lab` | defended-origin lab proposer (all born objects incl. killed) | **14.0** | **6.0** |
| `prod` | production `levels.py` proposal stream, rate caps removed (first-geometry-per-price dedup, `rep.*` + `broken_line_edge`) | **32.0** | 2.0 |
| `naive` | θ-pivot-only baseline (`sess_origins=0`, `MINI_BY_AGE=0`, `min_score=0`) | 11.0 | 10.0 |

Labels: matched births per golden via `oracle_stats`. Trusted subset = 40 LC /
28 MINI. CIs = Wilson 95%.

## Recall@k — top-k levels live at τ (LC all | trusted)

| ranker | lab k1 / k2 / k3 | prod k1 / k2 / k3 | naive k1 / k2 / k3 |
|---|---|---|---|
| birth_score | .167 / .271 / .417 | .146 / .208 / .208 | .083 / .188 / .292 |
| dist | .146 / .229 / .271 | .146 / .167 / .188 | .188 / .250 / .312 |
| ndef | .188 / .250 / .354 | .125 / .167 / .167 | .188 / .271 / .354 |
| age | .167 / .312 / .438 | .125 / .167 / .167 | .083 / .167 / .208 |
| cls | .188 / .271 / .375 | .104 / .188 / .208 | .021 / .167 / .292 |
| **ret24** | **.188 / .333 / .417** | .146 / .208 / .208 | **.208 / .292 / .354** |
| barrier | .125 / .250 / .333 | .146 / .208 / .208 | .146 / .208 / .271 |
| combo | .125 / .312 / .375 | .125 / .167 / .167 | .188 / .292 / .312 |

MINI (all) — best @k2: lab ret24 **.387**, prod ndef/age/ret24/barrier .194,
naive dist .194 (@k3 .419).

## Birth caps (cumulative births per panel)

| cap | lab LC | prod LC | naive LC | lab MINI | naive MINI |
|---|---|---|---|---|---|
| 1 | .042 | .000 | .104 | .000 | .097 |
| 2 | .062 | .000 | .167 | .032 | .129 |
| 3 | .188 | .000 | .208 | .129 | .161 |
| 5 | .271 | .000 | **.417** | .194 | .258 |

prod cap = 0 at every cap: its earliest births are early-day proposals far from
any golden at τ — chronological caps are meaningless for a stream that proposes
continuously. naive cap-5 .417 shows the first ~5 defended pivots of the day
carry real information — but note naive's live@τ is 10 (it never retires), so
its "budget" cost is hidden in live count, not births.

## Day-level 5-fold CV (choose ranker on 4 folds, score on 5th)

| metric | lab | prod | naive |
|---|---|---|---|
| LC@1 | 0.107 | **0.171** | 0.127 |
| **LC@2** | **0.267** | 0.208 | 0.203 |
| MINI@2 | **0.264** | 0.082 | 0.137 |

LC@2 chosen rankers: lab ret24×3+age×2; prod birth_score×5; naive mixed.
Fold scores LC@2: lab .10/.33/.00/.40/.50, prod .20/.17/.22/.20/.25,
naive .20/.17/.00/.40/.25 — high day-level variance (~10 goldens/fold).

**Integration condition (mandate §4): lab beats both prod and naive at
k = 2 under CV** (0.267 vs 0.208/0.203), and on MINI@2 (0.264 vs
0.082/0.137). **Caveat: at k = 1 lab LOSES to prod** (0.107 vs 0.171) —
a single-slot budget would make the production stream better; the lab
edge needs ≥ 2 live slots to exist. The k = 2..3 regime is the one the
author's ink actually occupies (~2 objects/panel).

## ret_24 standalone re-measurement (REQ-L2 evidence)

`ret24_measure.py` on my own collection (12 179 level-type candidates, funnel
labels, per-price dedup): **AUC 0.606 overall; folds .612 / .651 / .702 /
.526 / .558 — 2 of 5 folds below 0.60.** Honest verdict: borderline — ret24 is
the CV-chosen ranker and helps ranking inside the live pool, but as a lone
proposal-level separator it does NOT clear the every-fold-≥0.60 bar.

## Cross-family dedup (LC, combo ranker)

lab: k2 .271 vs .312 without dedup; prod: k2 .146 vs .167; naive: k2 .208 vs
.292. Dedup against live BOX edges / line prices **hurts** slightly — near a
real barrier the families duplicate because the level is real, not because the
ink is redundant.

## Reading

1. The lab proposer wins the budget test it was designed for: at author's
   ink (k≤2 live), ret24 ranking recovers .333 LC vs prod's .208.
2. But its raw stream is still inky: 14 births/panel → the live budget is what
   converts coverage into usable recall. A ≤2-live budget is mandatory in the
   integration proposal.
3. naive's cap-5 .417 warns that defended pivots alone cover a lot — the lab
   edge is in *when* it births (approach) and *how* it ranks, not in the origin
   universe alone.
4. ret24 = "birth happened within 24 bars of a same-direction touch" is the
   single most useful ranker — consistent with HANDOFF §3 — but not a clean
   per-fold AUC pass.
