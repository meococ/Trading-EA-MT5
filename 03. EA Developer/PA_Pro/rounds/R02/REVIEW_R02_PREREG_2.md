VERDICT: **FAIL**

## SUMMARY

Second pre-freeze review of `rounds/R02/PREREG.md` (D15-D23). The pivot is
structurally the right move — FINDING_1 is honest, both-arms-are-zone-arrivals
restores overlap, and the measured improvements to the arm semantics (t-1,
live-zone control, anchor_dist) are real and verified in code. But the
confirmatory architecture the round now rests on does not measure the channel
it claims to control, one covariate is missing entirely, and several decision
rules are still writable after outcomes. Measured on a EURUSD 40k-bar DESIGN
slice (`_scratch/prereg_review2/probe2.py`, all pre-event features):

- **The recency gate measures the wrong variable.** `since_near` is the
  interval `[mid - w_p/2, mid + w_p/2]` = `[glo, ghi]` — the band itself,
  floored at >= 24 bars by the freshness rule. It cannot see the dominant
  channel: in-window retests of the (wider) ZONE. Measured `zone_fresh` share,
  top vs bottom `zone_S` tercile arm: line1 **0.233 vs 0.614**, fractal_h1
  **0.396 vs 0.880**, kde_swing **0.369 vs 0.711**, sd_base **0.395 vs
  0.968**. The top arm is 2-3x "retest in progress" — F1 alive inside E1.
- **The residual confirmatory does not remove recency.** The OLS regressor
  set is the 7 propensity features + `zone_touches` — no zone recency
  (last_touch Δt, zone_fresh). Measured on residual tercile arms: zone_fresh
  still **0.29 vs 0.52** (line1), **0.45 vs 0.84** (fractal), **0.51 vs
  0.86** (sd_base). A same-sign residual result licenses only "beyond
  linear-in-these-8-regressors", not the D21 claim "beyond recency".
- **`side` is in neither the propensity model nor the balance gate** —
  measured arm imbalance: line1 0.535/0.465, fractal 0.543/0.431, sd_base
  0.484/0.645 (SMD ~0.14-0.32 — several cells would fail the 0.10 gate if
  side were a feature).
- Threshold provenance (attack Q2): **0.90 is inert** (max R2 0.545 — the
  guard never binds, harmless). **0.05 is load-bearing** — it alone stamps
  kde_swing RECENCY-UNSEPARATED 0/4 and splits sd_base 2/4; chosen after
  blind measurements existed. The available principle ("half the general
  gate") is plausible and the direction is conservative — it denies claims
  rather than creating them — but the text must say the principle AND note
  it gates a variable blind to the real channel.
- Undetermined still: the monotone gate's quantity under the weighted
  estimator (mid tercile has no defined weight); whether the residual
  OLS/tercile bounds/propensity are refit inside bootstrap replicates; the
  E2->E1 "support or downgrade" mechanics; winner eligibility of
  RECENCY-DOMINATED cells (D7 superseded — a recency-proxy generator can now
  win outright); "every symbol-cell contributing to the claim" scope;
  E2 arm-A ordering ("first" -> pin alphabetical).

Prereg sentences that must change (full text in §2):

1. D21 regressor set: add the argmax zone's own recency — `zone_last_touch`
   (bars since the zone's last touch at tp, capped at SINCE_CAP) and
   `zone_fresh` — to the OLS, so "the part recency cannot explain" is true.
2. D20: the 0.05 claim sub-gate applies to a ZONE-recency feature
   (zone_fresh share / zone_last_touch SMD), in ADDITION to since_near;
   state the 0.05 = half-the-general-gate principle.
3. §6 propensity feature set + balance gate: add `side` (or at minimum to
   the SMD gate).
4. §6: pin the monotone check (e.g. `m_bot <= m_mid <= m_top` on arm means
   under the same fitted model), residual-bootstrap refit rule, E2 downgrade
   mechanics, RECENCY-DOMINATED winner eligibility, claim-cell scope, and
   E2 arm-A = alphabetically first.

PASS withheld: F1-F3 are cheap to fix (2 features + sentences + one
re-measurement) and fatal post-freeze.

---

## 1. Findings

| ID | sev | where | defect | evidence | fix |
|---|---|---|---|---|---|
| R2-F1 | **MAJOR** | D11/D20, `arrival_common.py:163-164` | The "symmetric recency" covariate `since_near` is the interval `[mid - w_p/2, mid + w_p/2]` — which IS `[glo, ghi]`, the band itself (verified: equals `since_touch` up to float boundary ties). It is floored at >= 24 bars by the freshness rule and structurally cannot see the dominant recency channel — in-window retests of the overlapping zone, which is wider than the band by construction (w_p = 0.75*u_g). The D20 0.05 claim-gate therefore certifies band recency while the actual confound is zone recency. | Measured zone_fresh share by E1 arm (top/bot tercile): line1 0.233/0.614, fractal 0.396/0.880, kde 0.369/0.711, sd_base 0.395/0.968. The score mechanically loads recency (s_rec = exp decay of last_touch is a score component), so top-tercile selection IS a recency selection — the exact F1 channel the confirmatory exists to bound. | Make the 0.05 sub-gate apply to a zone-recency feature that can see the channel: |SMD| <= 0.05 on `zone_fresh` share AND on `zone_last_touch` (bars since argmax zone's last touch at tp, capped 1440) — in addition to since_near. All computable at tp for both E1 arms (both are treated events — zone features exist in both arms). |
| R2-F2 | **MAJOR** | D21, `arrival_contrast.resid_strength` | The residual-strength confirmatory is circular as specified: its verdict language claims the residual is "the part of the score recency cannot explain", but the regressor set contains no zone recency — only `zone_touches` (a count) and the floored band recency. The residual demonstrably retains the confound. A same-sign residual result is therefore consistent with pure recency, and "RECENCY-DOMINATED" vs confirmed is decided by a regression blind to the variable it adjudicates. Additionally the OLS is linear — the s_rec component is exponential in last_touch, so even a correct variable would only be removed linearly; acceptable only once the variable is actually in the set. | Measured on residual-tercile arms: zone_fresh rtop/rbot = 0.289/0.519 (line1), 0.449/0.835 (fractal), 0.391/0.742 (kde), 0.508/0.863 (sd_base) — the imbalance survives residualization almost intact. R2 0.34-0.42 (attenuation guard inert). | Add `zone_last_touch` and `zone_fresh` (argmax zone, at tp) to the residual OLS regressor set; keep zone_touches. Re-measure residual-arm zone_fresh balance — if it still fails, the confirmatory is honest about what it cannot separate. |
| R2-F3 | **MAJOR** | D18/§6, `arrival_contrast.FEATURES` | `side` (+1/-1 arrival direction) is absent from the propensity features AND from the balance gate — the only place side was ever controlled is the exact-strata key, now demoted to a robustness view. Arrival direction changes which barrier is near vs far mechanically; direction mix is materially imbalanced between arms. | Measured side=+1 share top/bot: line1 0.535/0.465 (SMD ~0.14), fractal 0.543/0.431 (~0.22), sd_base 0.484/0.645 (~0.32 — would fail the 0.10 gate were it checked), kde 0.493/0.498. | Add `side` to FEATURES (it is binary and cheap) — or minimally to the balance gate as an eighth checked covariate. Re-run the balance table; expect some cells to flip. |
| R2-F4 | **MAJOR** | §6 gates | The monotonicity gate's quantity is undefined under the weighted estimator: "dose-response monotone non-decreasing across bot -> mid -> top" — but the propensity model is fit on top-vs-bot only; the mid tercile is "excluded from the contrast" and has no defined weight or mean. Three pairwise Ds? Arm means? Under whose weights? Each reading gives a different gate. | `balance_report`/`att_weighted` take (idx_a, idx_b) pairs only; no three-arm path exists; the mid arm enters the check by a sentence that has no estimator behind it. | Pin it, e.g.: "monotone = m_bot <= m_mid <= m_top where m_k is the propensity-weighted resolved-rate of tercile arm k under the model fit on that cell's top-vs-bot arms (mid events are scored by the same model and weighted w=e/(1-e) against the pooled other two terciles)" — or declare the check on unweighted arm means. Either is fine; silence is not. |
| R2-F5 | MODERATE | D20 threshold | 0.05 was fixed after the blind balance numbers existed and is load-bearing: it alone stamps kde_swing RECENCY-UNSEPARATED on 4/4 and splits sd_base to 2/4 (measured margins: max pass 0.058, min fail 0.069 — any threshold in [0.05,0.068] gives the same partition; 0.08 would give kde 2/4). The "half the general gate" principle is plausible and the bias direction is conservative (denies claims, never creates), so this is not a manufactured pass — but the provenance should be owned, and per F1 it gates the wrong variable anyway. | FEASIBILITY §14 table; margins computed from it. | Add to D20: "0.05 = half the general balance gate, fixed after blind measurement; the measured margin (0.058 max passing / 0.069 min failing) is reported here so the threshold's leverage is visible." |
| R2-F6 | MODERATE | §6 winner rule + D21 | Winner eligibility of downgraded cells is undefined: D7's doubled bar is superseded because "no unconfirmable case remains", but RECENCY-DOMINATED is still a state — and the text says the generator "is still carried forward on the primary". Under the winner rule as written, a generator whose score is a recency proxy can be declared the round's winner outright — the exact outcome the doubled bar existed to prevent. | D21 supersession sentence vs §6 winner rule; no eligibility clause for stamped generators. | Pin: "a RECENCY-DOMINATED or RECENCY-UNSEPARATED generator is reported with its stamp and is NOT eligible for winner or tie-set membership" — or the intended rule, verbatim. |
| R2-F7 | MODERATE | §6 multiplicity | "E2 can support or downgrade an E1 claim" has no mechanics — no rule maps an E2 result onto an E1 verdict. Undeclared discretion at the exact point where a secondary result could be argued to rescue a primary. | §6 multiplicity paragraph. | Pin: either "E2 is descriptive and never modifies an E1 verdict" or the exact downgrade rule with quantities. |
| R2-F8 | MINOR | §6 claim scope | "since_near <= 0.05 in every symbol-cell contributing to the claim" — does a failing cell disqualify the pooled claim or get excluded from it (with the pooled D recomputed)? sd_base's fate turns on the answer. | D20 wording; ASK_LEAD implies per-cell claims exist. | Pin: "a cell failing the recency sub-gate is excluded from the claim AND from its pooled D" or the intended reading. |
| R2-F9 | MINOR | §6 estimator | Bootstrap refit scope for the residual confirmatory is undeclared: the propensity refit is pinned for the ATT, but the residual OLS and residual tercile bounds are a second fitted object — refit per replicate or frozen at observed values changes the CI. | `bootstrap_weighted` refits the propensity; nothing states the residual regression's bootstrap treatment. | Pin: "the residual regression, residual tercile bounds, and propensity are all refit inside every replicate" (or fixed — declare which). |
| R2-F10 | MINOR | §6/D17 | E2 arm-A ordering: "the pair's first generator" — code uses alphabetical (`arrival_feas2`); the text should say so. Residual confirmatory scope: applies to E1 only — say it. Minor pins, one line each. | feas2 docstring vs §6. | Two clauses. |
| R2-F11 | MINOR | D17 E2 arms | "Not marked by h" is a stronger exclusion when h is the wider/coarser generator (its live zones cover more price space) — arm composition asymmetry the propensity cannot see; inherent to the estimand, worth one declared sentence. | E2 arm definitions; u_atr ranges 0.25-0.65. | One sentence in D17 acknowledging the asymmetry is part of the estimand. |
| R2-F12 | INFO | D19 | The dropped fresh-restricted confirmatory is honestly recorded — but note for the record that its mechanical failure is the same measurement as F1 here: restricting to zone_fresh starves the TOP arm (they're the stale ones). Consistent. | zone_fresh shares above vs D19's 23/24. | None. |
| R2-F13 | INFO | D23 guard asymmetry | The R2>=0.90 attenuation guard protects the NULL direction only; nothing protects a POSITIVE residual result from un-residualized confounding (the F2 hole). Covered once F2's regressor fix lands; worth one clause stating the guard is one-sided by design. | D23 text. | One clause. |

## 2. Answers to the attack questions

**Q1 — residual confirmatory: sound or circular?** Circular as specified —
not because residualization is wrong (the shape is a legitimate confirmatory
and the R-squared attenuation guard is a genuinely good idea), but because the
regressor set omits the variable it adjudicates. `zone_S ~ 7 features +
zone_touches` leaves the residual 2-3x imbalanced on zone_fresh (measured);
a same-sign residual result licenses "beyond linear-in-these-regressors",
not "beyond recency". One added regressor pair (`zone_last_touch`,
`zone_fresh`) makes the claim true. The 0.90 guard is the right guard in the
right direction (protects nulls); arbitrary as a number but inert at measured
R2 0.30-0.55 and honestly pre-committed.

**Q2 — 0.05 and 0.90 reverse-engineered?** 0.90: no — it binds on nobody
(max R2 0.545); inert pre-commitment. 0.05: load-bearing and chosen after
the numbers existed; it alone decides kde's stamp and sd_base's 2/4. The
honest read: "half the general gate" is an available principle, the measured
margin is printed next to the threshold, and the bias direction is
conservative (denies claims). I cannot exclude reverse-engineering, but
whatever its origin it does not manufacture a positive result — the larger
defect is that it gates the wrong variable (F1). Require the principle
sentence; the number itself may stand.

**Q3 — still undetermined:** the monotone-gate quantity (F4 — no estimator
behind the sentence), residual bootstrap refit scope (F9), E2->E1 downgrade
mechanics (F7), stamped-generator winner eligibility (F6), claim-cell scope
(F8), E2 arm ordering + residual scope (F10).

**Q4 — is E1 meaningful?** Yes as an estimand: "does the score's ranking
carry outcome information" is the question the trading system asks, and the
within-generator design keeps both arms zone arrivals. A PASS economically
means the score is usable for ranking/filtering. But a PASS is currently
producible by non-score content: measured, the top arm carries 2-3x the
in-window retest share (zone_fresh), plus a 5-16pp side imbalance — so a
positive E1 can be a recency/touch-count artifact, and the machinery meant
to rule that out (D20 sub-gate, D21 residual) measures the wrong variables.
A FAIL is cleanly interpretable ("the ranking carries nothing") and would be
informative — the asymmetry of interpretability is the design's current
weakness. E2 is meaningful as a secondary; its pair failures are honestly
structural.

**Q5 — confounds left:** (i) zone recency — the big one, measured (F1/F2);
(ii) side (F3); (iii) E2 asymmetric "not-marked" exclusion by generator
width (F11, inherent); (iv) `cover` not a covariate — treated-band geometry
varies with which part of the zone overlaps G; score-adjacent, declared
secondary already; (v) cross-day zone persistence — handled by the declared
week-cluster rerun.

**Q6 — outcome-blindness:** verified. `arrival_common`, `arrival_contrast`,
`arrival_estimate`, `arrival_feas2`, `arrival_freeze`, `arrival_run` read in
full: all features <= t (arms at tp=t-1, state replayed through tp,
zone_touches via `state_at(z,tp)`, grids from the day-open bar). No outcome
column exists outside `arrival_outcome.py` (thin map to the frozen R01
resolver, invoked only by synthetic tests; 19-test suite present).
`live_overlap_tables` uses only <= tp liveness (end_idx truncation is
backward-safe). CLEAN.

## 3. What the revision got right

- FINDING_1 is the correct read of the support collapse and is published as
  a result, not buried — this is exactly what R01 lacked.
- t-1 labelling, live-zone control, anchor_dist in the key: verified in
  code, matching my round-1 fixes in substance.
- Balance-as-gate before freeze, UNDERPOWERED-BY-CONSTRUCTION declarations,
  propensity refit inside bootstrap, week-cluster rerun, winsorize/trim pins,
  per-symbol cells + pinned pooling — all present and pinned.
- The balance gate *measured before freeze* with the values printed next to
  the thresholds is the right disclosure pattern (and is what lets me see
  that 0.05 is load-bearing).

## 4. Scope

One python process, OMP_NUM_THREADS=4, BelowNormal, DESIGN slice EURUSD
first 40,000 M5 bars, pre-event features only; no outcome computed anywhere.
Script: `PA_Pro/_scratch/prereg_review2/probe2.py`. Numbers are slice-scale;
signs are not in doubt (gaps of 2-3x / 5-16pp), but all should be re-measured
at full scale when the fixes land.
