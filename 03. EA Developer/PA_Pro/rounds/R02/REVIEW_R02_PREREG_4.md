# REVIEW_R02_PREREG_4 — adversarial review, pass 4 (post-D38; freeze decision)

Reviewer: neutral, fourth pass, deltas-only scope (D33–D38) plus the
D34 causal argument. Read `PREREG.md` D33–D38 + §3b E3 table + §6,
`FEASIBILITY.md` §19, `arrival_contrast.py` (E3_FEATURES, saturation
guard), `arrival_feas2.py` (cap_share_stale, zone_s_smd_diag),
`arrival_estimate.py` (bootstrap_e3). Probe: `_scratch/prereg_review3/
probe_e3.py` re-run under the new 9-feature model on a DESIGN slice
(2019–2020). Outcome-blind throughout; no outcome computed.

## SUMMARY

VERDICT: **FAIL — narrow.** The science is now honest and
self-consistent; what remains are two decision-rule holes that will be
exercised *after* outcomes exist. Both are one-to-three-sentence pins
(plus keeping bootstrap replicates). Fix those two and the document is
freeze-ready; nothing else in this review blocks.

D34 position (two sentences): I **concede** — `zone_S` contains
`s_rec`, a deterministic function of the treatment, so conditioning on
it conditions on a descendant of T (strips the effect, risks collider
paths through the score's other inputs); the Lead's causal direction is
correct. Residual caveat: `zone_S`'s *non-recency* components (zone
age, density, touch quality) are NOT treatment descendants and remain
uncontrolled — the bundled claim language (D36) already absorbs this,
so it is a DECLARE, not a blocker.

BLOCKERS:
- B1. BH is not executable as written: no p-value recipe exists in
  prereg or code; `bootstrap_*` returns only (2.5, 97.5) percentiles
  and discards replicates, so no p can even be computed post-hoc; and
  the family unit is inconsistent (E1 = cells×endpoints, E3 =
  "generators×endpoints" — a per-generator test needs a pooled-D
  bootstrap that does not exist). Pin: p recipe, family unit, retain
  replicates.
- B2. §6 winner rule still ranks "E1 gate-passers by `D_resid`" and
  never operationalizes D37(c): which D ranks an E3 candidate, and
  does an E3-claim generator count as FULLY-CONFIRMED for the +5.0pp
  benchmark are both undefined — a live fork in the headline rule.

DECLARE:
- D1. Under D37(a)'s <3-contributing-cells bar, NO E1 generator is
  claim-eligible on measured data (sd_base 2, fractal 2, line1 1,
  ref_levels 1 cells) and E3's claim path is line1_cluster only.
  State it; do not let "6 evaluable cells" read as 6 live claims.
- D2. D37(a) "minimum 2 cells" is dead text given <3 ineligible;
  ">= 4/6 DESIGN years" needs "within contributing cells" scope.
- D3. fractal_h1 GBPUSD E3 passes at exactly 0.100 — knife-edge;
  deterministic, but note it as marginal.
- D4. `since_near` is plausibly part-descendant of the treatment too;
  controlling it is the conservative choice — say so once.
- D5. The saturation guard (kept arms < 50 → fail) lives in §3b text
  but applies to all three experiments via shared `balance_report`;
  echo it in §6.

## 1. The D34 argument, resolved on the merits

DAG: T = `zone_since_touch`; S = `zone_S` = f(age, vol, density,
`s_rec`) with `s_rec = exp(-Δt/τ)` — a deterministic function of T,
so T → S. Conditioning on a descendant of the treatment biases the
contrast (it partialls T itself) and, because S also has other
parents (age, density, touch volume), opens T → S ← U → Y collider
paths. The size of the arm imbalance (0.64–4.23) is irrelevant to
that argument — the Lead is right that the objection must be causal,
and on causal terms exclusion is correct. Where the ruling is
*incomplete* rather than wrong: the non-`s_rec` inputs to S are
pre-treatment zone attributes that are legitimate confounders (zone
age correlates with staleness and plausibly with resolution), and
excluding S does not control them. `zone_touches` (D33) covers the
touch-quality part; zone age/birth is not in the feature set and is
the residual confound. Since D36's claim is explicitly bundled and
associational, the estimand is identified regardless — DECLARE the
uncontrolled zone-age channel, do not block on it.

## 2. D33/D35 verification — did they do what they claim?

Code confirmed line-by-line: `E3_FEATURES` is now the 9 declared
features (`arrival_contrast.py:73-75`); `zone_S` absent, reported via
`zone_s_smd_diag` (`arrival_feas2.py:146-154`); `cap_share_stale`
computed mechanically (`feas2:143-145`); saturation guard at
`balance_report` (`contrast:196-198`) — kept <50 → `gate_pass=False`.

Re-measured on the slice under the NEW 9-feature model: ref_levels
saturates (smd_post = NaN — propensity separates touched vs
never-touched arms perfectly, trim kills all kept events; matches
§19 "SAT"); line1 worsens 0.099→0.100 / 0.072→0.139 vs the old set —
the confounder control is doing real work, which is exactly why
§19's collapse (sd_base, kde, profile now fail; ref_levels excluded)
is credible rather than cosmetic.

D35 threshold honesty: measured `cap_share_stale` is bimodal —
{0.00–0.12} for line1/fractal/sd_base vs {0.63–1.00} for
kde/profile/ref_levels. ANY cut in (0.12, 0.63) produces the identical
partition; 0.50 sits mid-gap. Not tuned to a convenient set — the
measured margin is wide. Declared blind-fixed; acceptable.

## 3. The remaining bendable quantities

**B1 (BLOCKER) — the multiplicity gate has no implementable spec.**
"BH-FDR q <= 0.10 within each family" requires p-values. Nowhere does
the prereg define the p, and no code computes one: `bootstrap_*`
returns only the two percentiles and throws away `boots`. Post-freeze,
someone must invent: (a) the p recipe — sign-share over replicates
(`p = 2·min(P(D≤0), P(D≥0))`), normal approx on bootstrap SE, or CI
inversion — these disagree on borderline cells; (b) the family unit —
E1's text reads cells×endpoints (12 tests) while E3's reads
generators×endpoints, and a generator-level test requires a pooled-D
bootstrap over contributing cells that is not written; (c) retaining
replicates. Every one of those choices will be visible-adjacent to
outcomes. Pin all three, or drop BH to the CI rule and say so.

**B2 (BLOCKER) — the winner rule does not implement D37(c).** §6
still reads "rank E1 gate-passers by `D_resid`". D37(c) admits E3
candidates under the +5.0pp bar but never says: which D ranks an
E3-supported candidate (`D_recency`, a different quantity than
`D_resid`); whether an E3-claim generator counts as FULLY-CONFIRMED
for setting the +5.0pp benchmark (if it does not, and nothing else is
confirmed, D27's backstop already yields "no winner" — say so); or
whether an E3 claim with a null/adverse residual-E1 can still win.
Two sentences close it: name the ranking variable per experiment and
define FULLY-CONFIRMED membership.

**DECLARE items** (D1–D5 in SUMMARY): the single most important is
D1 — the pinned eligibility rule plus measured evaluability imply the
round's entire claim path is E3-line1_cluster (4 contributing cells,
needs >= 3 positive, CI>0, D>=5pp, BH, 1,000/arm pooled, 4/6 years).
E1 residual produces per-cell estimates only — no generator can
claim. That is an honest narrow scope; it just needs stating so the
results writeup cannot silently relax it.

## 4. Outcome-blindness and code-text match

Unchanged and verified again: `attach_touches`, `e3_arms`,
`resid_strength`, `bootstrap_*` read ≤ tp features only; nothing on
real data supplies `values`; `arrival_outcome.py` synthetic-tested
only. D33–D36 match their code line-for-line. The stale-arm
diagnostic (`cap_share_stale`) and `zone_s_smd_diag` are emitted per
cell as declared.

## 5. Verdict basis

Two freeze blockers, both in the decision-rule layer rather than the
design: the multiplicity gate cannot be executed deterministically
(B1), and the headline winner rule admits a candidate class it does
not define (B2). The design layer — three experiments, their
estimands, gates, stamps, and claim languages — is now honest and
pinned. Pin B1 and B2 and this passes.
