# REVIEW_R02_PREREG_3 — adversarial review, pass 3 (post-D32, E1 inversion + E3)

Reviewer: neutral, third pass. Read `PREREG.md` (D15–D32, §1–§8),
`FINDING_1_*`, `FINDING_2_*`, `FEASIBILITY.md` §16–18, `ASK_LEAD.md`,
all of `research/arrival/` incl. `e3_arms`, `attach_touches`,
`resid_strength`, `bootstrap_resid`, `bootstrap_e3`, and the E3
feasibility output `research/arrival/_scratch/e3_feas.jsonl`.
Outcome-blind throughout; probe in `_scratch/prereg_review3/probe_e3.py`
measured pre-event features only on a DESIGN slice (2019–2020).

## SUMMARY

VERDICT: **FAIL** — third pass. The architecture is now close to honest,
but two defects are outcome-facing and one claim sentence over-reads
its estimand. Fixes are sentence-level; no measurement needs redoing.

Q2 (is the E1 restructure honest or salvage): honest, and this can now
be argued rather than asserted. The raw contrast failed the zone-recency
sub-gate in 24/24 cells and was demoted to descriptive; the claim moved
to the residual estimand, evaluable in 6 cells selected by a mechanical
pre-declared rule (balance + recency gate on residual arms), all fixed
before any outcome exists. A motivated-reasoning move would have
loosened the gates or widened the claimable set — this one did the
opposite: 18 cells lost claim eligibility and FINDING_2 is published as
a negative result. What the restructure cannot do is make the residual
estimand mean more than it does: a positive licenses only "the part of
`zone_S` orthogonal to {8 propensity features, zone_touches,
zone_since_touch, zone_fresh} ranks outcomes" — never "strength
predicts outcomes" unqualified, and never a causal read. Run it —
it is cheap, and its null is informative — but see F1 below: as
written, its claim gate may be structurally unsatisfiable.

Exact prereg sentences that must change (detail below):

1. §6 E1 gate: "`D_resid > 0` in >= 3/4 core symbols and >= 4/6 DESIGN
   years" — ambiguous against D29(d) scope; under the literal reading
   no generator can ever pass (max contributing cells = 2 < 3).
2. §6 E3 gate: "`D > 0` in >= 3/4 core symbols and >= 4/6 DESIGN
   years" — same defect (profile_va, ref_levels are evaluable on 2/4).
3. §1 E3 question + §6 E3 claim: "does RECENCY itself carry
   information" — the arms also differ on `zone_S` (measured SMD
   0.52–4.32) and `zone_touches` (0.34–1.36) by construction; the
   sentence must say the contrast is bundled.
4. §3b E3 / D32: the stale arm's SINCE_CAP share is undeclared —
   ref_levels' stale arm is 100% never-touched zones (measured); that
   cell's estimand is "validated vs never-validated", not
   "recent vs stale".
5. §6 winner rule: "rank E1 gate-passers by `D` (top-vs-bot)" — `D`
   is now `D_resid`, and the rule is silent on whether an E3 claim
   interacts with winner eligibility.
6. §6 E3 gate: ">= 1,000 resolved events per arm" — pooled or per
   cell is unspecified (E1's clause says "pooled across symbols";
   E3's does not).

## 1. E3 — is the contrast well posed?

E3 splits armed-overlap treated events on `zone_since_touch` terciles
(`e3_arms`, `arrival_contrast.py:250`): RECENT = `s <= q33`, STALE =
`s >= q67` (cap mass included by `>=`), mid descriptive. Propensity and
gate on `E3_FEATURES` (7 covariates, no recency variable). Feasibility
(e3_feas.jsonl): trim shares 0.00–0.03, arms ~1:1, 4 generators
evaluable 4/4. The estimator mechanics are correct and the bootstrap
(`bootstrap_e3`) refits bounds and propensity inside every replicate.

**F1 — the arms differ on more than recency, and the gate cannot see
it.** Measured on the slice (raw arm SMDs; the E3 weights move these
little because the model has no term for them):

- `zone_S`: SMD **0.52** (line1 EUR), **0.61** (line1 GBP), **4.32**
  (ref_levels EUR), **4.14** (ref_levels GBP). `s_rec =
  exp(-dt/tau)` is a score component — recently-touched zones score
  higher *by construction*. An E3 positive cannot be separated from
  "the score ranks outcomes" — which is E1's question wearing a
  different axis.
- `zone_touches`: SMD 0.34–1.36 (recent zones carry 15–22 touches,
  stale 0–15).
- `since_near` (band recency — controlled in E1/E2, removed here):
  raw SMD 0.13–0.61. Exclusion is defensible (it is partly a
  descendant of the treatment) but its imbalance is unreported.
- `zone_fresh` share: 0.00–0.36 vs 0.79–1.00 — mechanical (a touch in
  the window sets both `zone_since_touch < 24` and `zone_fresh=False`).

None of these is in `E3_FEATURES` and none is gated. That is partly
correct — you cannot control `zone_S` without partialling out part of
the treatment — but the claim sentence is then wrong. "Does recency
itself carry information" reads as recency-in-isolation; what is
identified is the *bundled* recent-vs-stale contrast (recency + score +
touch history). Required fix (sentence 3): state that `zone_S` and
`zone_touches` are consequences/components of the treatment,
deliberately uncontrolled, and that their arm SMDs are reported as
diagnostics, never gated. Also add `since_near` to the reported
diagnostics.

**F2 — the stale arm is not the same object across generators.**
`zone_since_touch` is capped at 1440 with never-touched → cap. For
ref_levels, `q67 = 1440` and the stale arm is **100% cap mass**
(measured: cap_s = 1.00 both symbols) — i.e. the contrast there is
"touched recently-ish vs NEVER touched", a different estimand from
line1's "touched <=1 bar ago vs untouched >=51 bars". Cross-generator
E3 cells wear one label for different questions. Fix (sentence 4):
report the stale arm's SINCE_CAP share per cell; stamp cells where it
dominates (say >50%) `STALE≈NEVER-TOUCHED` — an evaluable contrast,
but quote it as validated-vs-never-validated, not recency.

**The arm-boundary fix is principled, and was also convenient — both
are now declared.** `s >= q67` vs E1's `s > q67`: without the
inclusive bound the ref_levels stale arm would be empty and the cell
non-evaluable. The semantics (cap = "at least 1440 bars or never" =
the stalest possible value) justify it; D32 states it. Acceptable —
but it is exactly why F2's stamp is needed.

**Survivorship is declared correctly**: arms are drawn from the
armed-overlap set (a recently-touched zone that broke is unarmed and
excluded), so RECENT = "touched and held" — that is the estimand and
it is a real trading-relevant contrast. Zone age is entangled with
staleness (a 2-bar-old never-touched zone sits in stale next to a
500-bar-untouched one) — covered by the F2 diagnostic; a split of
stale by never-touched vs long-ago is a reasonable declared
descriptive but not required.

## 2. The E1 restructure — honest or salvage?

Covered in SUMMARY. Additional detail: the residual contrast's 24/24
balance is still mechanical (orthogonality by construction), and the
prereg says so (D23) — good. The non-mechanical part is the residual
arms' own recency sub-gate: it uses *weighted* SMDs under the residual
propensity, and the arm label is nonlinear in the residual, so it is
not vacuous — 6/24 pass is real information, not a tautology. The
selection of the 6 cells is by pre-declared mechanical rule, before
outcomes — legitimate use of feasibility data.

What a positive licenses, stated tightly for the results writeup:
"in this cell, the component of `zone_S` orthogonal to the pinned
covariate set is associated with the conditional outcome in the
ranked direction." It does NOT license "strength predicts outcomes",
"the scoring layer is causal", or anything about economics. The claim
sentence in §6 ("residual strength ranks carry information") is close
to this — keep it, and do not let it drift at writeup time.

Should the round run E1 at all? Yes — the pipeline is shared and a
positive in the 6 cells is the only claimable strength evidence left.
But F3 below may make it unclaimable as written.

## 3. Do the findings hold together?

F1 (binary contrast non-identifiable by construction — positivity
fails because zones are caused by history) and F2 (the strength score
is a recency proxy on this data, R² up to 0.898) are both honest
negatives with measured evidence, not rhetoric. E3 is the right
remaining *measurable* question: it tests the recency axis head-on
with real overlap, and it is the contrast the trading system actually
faces ("fade fresh retests vs fade stale levels").

The fourth thing nobody has proposed: **E3 × zone_S interaction** —
does the recent-vs-stale gap survive inside strength terciles? It
would separate "recency" from "the score's recency component" without
residualizing the treatment. Cheap (descriptive stratification of the
same events), worth one declared line; NOT required for freeze. What
is NOT worth adding: a within-zone matched design — zone identity does
not give repeated arrivals at controlled recency on this data, and
proposing it would restart the support problem that killed the binary
contrast.

## 4. Remaining degrees of freedom

**F3 (outcome-facing, must pin):** the ">= 3/4 core symbols" clause
in both the E1 and E3 gates collides with D29(d) scope ("a cell that
fails the balance gate contributes no D_sym and is outside the
claim's scope"). Read literally — D > 0 in >= 3 of 4 *core symbols* —
no E1 generator can ever claim (max contributing cells is 2:
sd_base EUR+GBP; fractal AUD+JPY; line1 GBP alone; ref_levels JPY
alone), and E3's profile_va/ref_levels (evaluable 2/4) are dead on
arrival. Read the D29(d) way — >= 3/4 of *contributing* cells — a
2-cell generator needs both cells positive, which is satisfiable. Two
readings, different verdicts, decided after outcomes are visible =
the exact hole this review exists to close. Pin: "`D_sym > 0` in
>= 3/4 (rounded up) of the generator's contributing symbol-cells,
minimum 2 contributing cells required for the claim" — or, if the
intent is stricter, declare that a generator with < 3 contributing
cells is ineligible for a claim outright. Same edit in both gates.
The ">= 4/6 DESIGN years" clause needs the same scope ("within
contributing cells").

**F4:** E3's ">= 1,000 resolved events per arm" — per cell or pooled?
E1's clause says "per arm per generator pooled across symbols"; E3's
does not. Pin identically.

**F5:** winner rule still reads "rank E1 gate-passers by `D`
(top-vs-bot)" — the claim-bearing `D` is now `D_resid`; and the rule
never says whether an E3 claim enters winner eligibility (it should
not — E3 is per-generator recency, not a scoring-ranking claim). One
sentence.

**Checked and clean:** E3 mid tercile descriptive-only; degenerate
bounds → NON-EVALUABLE declared; bootstrap refits bounds + arms +
propensity (bootstrap_e3:309–319); day-cluster declared, week rerun
non-gated; E3 arm A = recent declared; adverse direction symmetric
("recency ADVERSE"); E2 alphabetical arm A (D29b); E2-CONTRADICTED
mechanics (D29c); RECENCY-UNSEPARATED/DOMINATED/THIN-RESIDUAL strings
verbatim (D29e); threshold provenance honest (D26 — set after
feasibility, retained because one-directional); winner eligibility
+5.0pp rule (D27); multiplicity = three declared BH families, E3 =
evaluable generator-cells × 2 endpoints.

## 5. Harness verification

- `e3_arms` matches D32 exactly: `s <= q33` recent, `s >= q67` stale
  (inclusive — cap mass lands in stale), degenerate `q33 >= q67` →
  non-evaluable (`arrival_contrast.py:250–272`).
- `attach_touches` sets `zone_since_touch = min(tp - last_touch,
  1440)`, never-touched → 1440, `tp = bar_idx - 1` — strictly
  pre-event (`arrival_contrast.py:275–295`); `zone_zid` = argmax-S
  armed zone at tp, consistent with E1/E2's zone definition
  (`arrival_common.py:277`).
- `bootstrap_e3` refits quantile bounds, rebuilds arms, refits the
  propensity on `E3_FEATURES` per replicate (`arrival_estimate.py:
  290–325`); `bootstrap_resid` refits OLS + bounds + arms +
  propensity (253–287) — D29(a) honored in code.
- No outcome is computed anywhere pre-freeze: `feas2` emits arms,
  bounds, balance, recency SMDs only; `att_weighted`/`bootstrap_*`
  take a `values` argument that nothing supplies on real data;
  `arrival_outcome.py` is imported read-only and runs only in
  synthetic tests (24 tests incl. `test_e3_arms_*`,
  `test_e3_balance_uses_no_recency_features` — the no-recency
  feature set is unit-tested).
- One inconsistency vs the frozen text, already covered by F2:
  `e3_feas.jsonl` shows ref_levels stale arm ≈ all cap mass; the
  prereg does not yet say what that means for the estimand.

## 6. What would make this a PASS

Apply the six sentence-level fixes in SUMMARY (all are declarations —
none require new measurement beyond the cap-share diagnostic, which
is already computable from frozen quantities). After that the round
is: E1 residual in 6 stamped cells, E2 flagging-only in 7 pairs,
E3 as the honest bundled recency contrast with per-cell semantics
declared — a defensible, narrow, outcome-blind program. The cheap
version of this review would PASS it now on the strength of the
honest negatives; the strict version FAILs on F3 because it is a
live post-outcome fork in the claim gates.
