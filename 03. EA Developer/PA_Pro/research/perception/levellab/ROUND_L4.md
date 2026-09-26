# ROUND L4 — grace period + final config (accepted lab config)

Config: L3 with `sess_grace_bars` — a superseded session extreme lives
24 bars (2h) to earn defences; only then dropped if still undefended.
Variant sweep: grace=48 bars (4h) beats grace=24 on every axis;
grace=72 saturates (identical). Looser lifecycle (live_abr 4,
approach 2.0, score 2.5) slightly worse.

**L4 miss audit** found 9/22 remaining LC misses were born at a price
1.5–3 p off golden — caused by mean-averaging merged origins (price
drift). Fix: on merge keep the **defended-edge price** (min for lows,
max for highs), not the mean. Also tracked in-tol touch prices to test
a `median` emit mode — slightly worse (0.562, oracle 0.688) because it
pulls off the defended edge; kept `edge`.

**Final config (L4c = L4 + grace48 + edge-price):** defences≥2,
approach≤1.75 ABR, score≥2.0, NMS ±3.0p, revive ≤96 bars,
sess_grace=48, pierce 2 closes, stale 60, price_mode=edge.

| ruler | LC recall | LC prec | LC trusted | MINI recall | MINI trusted |
|---|---|---|---|---|---|
| eval.py | 0.583 (28/48) | 0.035 | 0.700 | 0.531 | 0.552 |
| eval_v2 | 0.583 (28/48) | 0.035 | 0.700 | 0.548 | 0.571 |

Oracle: **LC 0.792, MINI 0.774** (target ≥0.70 — PASS).
Snapshot lens: LC hit 0.489, MINI 0.533; **live levels med 4.0–5.0 at
τ** (engine v1 live clutter med ≈12 objects total — PASS).
Born recall 0.583 ≥ 0.35 target — PASS (lab has no salience; production
will lose some to rate-limiting, flagged in LEVEL_INTEGRATION.md).

Round sweep (v2 LC recall / oracle / live@τ):

| cfg | recall | oracle | live |
|---|---|---|---|
| L1 default | .604 | .792 | ~9 |
| L2 strict (def3/sc3/app1.5) | .542 | .667 | 4-5 |
| L3 sess-drop | .479 | .771 | 4.0 |
| L4 grace24 | .521 | .771 | 4.0 |
| L4b grace48 (mean-merge) | .542 | .792 | 4.0 |
| L4c grace48 + edge-price | **.583** | **.792** | **5.0** |
| L4c grace72 | .583 (sat.) | .792 | 5.0 |
| L5 median-price | .562 | .688 | 4.0 |

Remaining gap vs charter gate 0.60: 9 near-misses at 1.9–2.6 p vs the
1.5 p repaired tol (right structure, price granularity), ~7 Tier-A/B
suspect labels, 2 born-too-late. The oracle 0.79 says the *proposal
side* is solved; price granularity on repaired goldens is the residual.
