VERDICT: **FAIL**

## SUMMARY

Adversarial pre-freeze review of `rounds/R02/PREREG.md` (draft, unfrozen; no
outcome computed anywhere — verified, see §3). The grid design is the right
shape and honestly documented, but FOUR MAJOR holes stand, three of them
measured on DESIGN data this review (`_scratch/prereg_review/probe_arms.py`,
EURUSD first 40k M5, all pre-event features only). All three bias in the SAME
direction as the R01 F1 artifact (control arm enriched for further-into-the-move
/ fresher episodes → −D_bounce, +D_cont), i.e. R02 as written can reproduce a
spurious negative-D or an inflated continuation gap and nobody could tell.

The numbers that matter (EURUSD slice; line1 / ref_levels / sd_base):

- Treated events whose overlapping zone was touched by a bar in `[t-24,t-1]`
  (retest-in-progress, invisible to the band-level `since_touch` co-primary):
  **55.7% / 24.9% / 31.1%** — vs control live-zone touch 7.7% / 2.1% / 1.2%.
- Median |band mid − day-open anchor| / A(t): **T 1.26 / 1.02 / 1.27 ATR vs
  C 2.69 / 2.04 / 1.75 ATR** — unmatched; not in either stratum key.
- CONTROL events with a live-but-UNARMED zone overlapping the band:
  **22.2% / 6.7% / 3.8%**. CONTROL events that were TREATED at bar t−1
  (zone broke on the arrival bar itself): **14.9% / 3.2% / 2.0%**.
- Estimator module `arrival_estimate.py` does not exist; the prose spec leaves
  ω_s, symbol-in-key, hour-bucket width, `D_top`, multi-zone strength and
  "monotone" undefined — every one is a post-outcome degree of freedom.
- No adverse-direction verdict language; R01's actual outcome was D −5..−7pp,
  which under this text is neither a PASS nor the declared FAIL.

Prereg sentences that must change (minimal form; §2 gives full text):

1. §5 stratum keys: add an `anchor-distance decile` (|mid−anchor|/A(t)) to
   BOTH keys; the supT≥0.90 floor is re-measured under the final key.
2. §3 ARMS: evaluate arms on the armed set at bar **t−1**, and CONTROL
   additionally requires no LIVE zone (armed or not) within `margin·w_p`.
3. D3: add a FRESH-TO-ZONE clause — the co-primary sign/half-magnitude rule
   must also hold on treated events whose overlapping zone was untouched in
   `[t-24,t-1]`; the excluded share is reported per generator.
4. §5/§6: pin ω_s = n_T,s/N_T, symbol inside the stratum key (or the exact
   per-symbol pooling rule), hour bucket = `utc_min//240`, `D_top` defined,
   multi-zone strength = max, "monotone" = non-decreasing, resolved-floor
   scope, and add the adverse-direction verdict line.

Fixes are cheap now (a few harness lines + re-measured supT) and fatal later.
Do not freeze until 1-4 land and the supT tables are regenerated under the
final key — `line1_cluster` may lose even its primary floor.

---

## 1. Findings

| ID | sev | where | defect | evidence | fix |
|---|---|---|---|---|---|
| R02-F1 | **MAJOR** | PREREG §3/D3 → `arrival_common.arrival_events` + `tag_arms` | The treated arm is systematically fresher *to the zone* than the band-freshness rule records. A zone overlapping G is typically wider than G (u_g vs 0.75·u_g grid width); bars in `[t-24,t-1]` may touch the zone's overhang without touching G. The event fires "fresh to the band" while price is mid-retest of the actual structure. Band-level `since_touch` — the whole basis of the D3 co-primary that is supposed to separate recency from structure — cannot see this. A structure claim can pass the co-primary while driven by zone-level recency the key never measured. | Measured: treated events with ≥1 bar in `[t-24,t-1]` intersecting the overlapping armed zone: line1 **55.7%**, sd_base **31.1%**, ref_levels **24.9%**. Controls with any live-zone touch: 7.7/1.2/2.1%. Same sign as R01 F1 (hover/retest vs fresh arrival). | Add to D3 (FRESH-TO-ZONE clause): a "zones matter" claim requires the same sign and ≥ half magnitude when the treated arm is restricted to events where **no armed zone overlapping G was intersected by any bar in `[t-24,t-1]`**; share of treated events failing this reported per generator. Controls need no change — they have no zone by construction. |
| R02-F2 | **MAJOR** | PREREG §3 GRID + §5 stratum key | The grid is anchored at the day open, so a band's position is not random: zones arm near price → treated bands cluster near the anchor, control events require price to travel further out. The stratum key (side × approach-decile × ATR-decile × hour) does not contain distance-from-anchor; `approach_atr` (24-bar excursion) is related but not equal — a slow-drift day reaches a far band with modest 24-bar travel. Control arrivals are systematically further into the day's displacement — a trend-day enrichment, the same episode-type asymmetry that sank R01, surviving through the anchor. | Measured medians |mid−anchor|/A(t): T **1.26/1.02/1.27** vs C **2.69/2.04/1.75** ATR (line1/ref/sd); p10 T 0.12-0.22 vs C 0.40-1.04. FEASIBILITY §3's own `pos_r5` p90 gap (0.92 vs 1.03) is the same symptom. | Add `anchor-distance decile` (|mid_G − anchor|/A(t), pooled T+C per (gen,symbol)) to BOTH stratum keys; re-measure supT/supC and re-apply the 0.90 floor under the final key; declare line1's status under the new key before freeze. |
| R02-F3 | **MAJOR** | `arrival_common.tag_arms` + `phys_source.armed_views_from` → `common.arm_zones` | Two defects in the arm definition. (a) CONTROL = "no ARMED zone within margin" — but broken/deduped/capped zones are live yet unarmed, so the control arm contains bands sitting on dead structure (structure that already failed — adversely selected). (b) Arms are evaluated at bar t (state replayed *through* the event bar); a zone that breaks on the arrival bar itself is unarmed at t, so the most break-y treated episodes leak into CONTROL. | Measured: (a) live-but-unarmed zone overlaps band on **22.2%** of line1 controls (6.7/3.8% others). (b) **14.9%** of line1 controls were treated at t−1 (3.2/2.0% others). Both push break-continuation into the control arm — same sign as F1. | Rewrite §3 ARMS: "Arms are evaluated on the armed set at bar **t−1**. CONTROL iff no LIVE zone of g (armed or not) lies within margin·w_p of G." Re-measure arm counts and supT — the control pool shrinks, support must be re-checked. (If the Lead prefers the armed-set estimand, the minimal honest version still needs (b) fixed at t−1 and the live-unarmed overlap share reported per arm with a declared consequence.) |
| R02-F4 | **MAJOR** | PREREG D5/§6; `arrival_estimate.py` unwritten | The estimator exists only as prose, and the prose leaves post-outcome degrees of freedom: (i) ω_s "treated share of stratum s" reads both as n_T,s/N_T (correct ATT) and as n_T,s/(n_T,s+n_C,s) (not ATT); (ii) symbol is absent from the stratum key — pooled cross-symbol strata vs per-symbol strata + pooled headline are different estimands, undeclared; (iii) "hour bucket" granularity undefined (code uses utc_min//240 — the text never says so; a 1h reading ×4 the cells); (iv) `D_top` used in D6/D7 winner rules is never defined; (v) multi-zone overlap → which zone's strength feeds the tercile; (vi) "monotone" strict vs non-decreasing; (vii) "≥1,000 resolved events per arm" — resolved=BOUNCE|BREAK? pooled across symbols? | Code read: `stratify` key is (side, approach_decile, atr_decile, hour_bucket) with no symbol — fine per (gen,symbol) calls, but nothing pins the cross-symbol estimand. | Pin every item in the prereg text, e.g.: "ω_s = n_T,s/N_T over support strata; strata are computed within each symbol; headline D = treated-share-weighted mean of the four per-symbol Ds, each reported; hour bucket = utc_min//240 (six 4h buckets); D_top = the same stratified ATT restricted to top-strength-tercile treated events and their in-stratum controls; event strength = MAX strength over armed zones overlapping G; monotone = non-decreasing across terciles; resolved = BOUNCE or BREAK, pooled across symbols." |
| R02-F5 | MODERATE | PREREG §1 failure language | No verdict language for a significant NEGATIVE D. R01's actual answer was D ≈ −5..−7pp — the single most likely shape of an R02 surprise — and under the frozen text it is neither a "zones matter" PASS nor the declared FAIL ("no measurable difference"). An unscripted post-outcome decision on the most likely surprise is exactly how R01's interpretation drifted. | R01 ROUND_REPORT §4/§5 numbers. | Add: "A significant negative D (CI upper bound < 0) is a finding — 'zones ADVERSE' — reported symmetrically with the positive gate; it is not a PASS and not a null." |
| R02-F6 | MODERATE | D5/§6 bootstrap | Day-cluster bootstrap misses cross-day dependence: zones persist for days (`break_keep_bars`=192 + multi-day lives), so events on different days at the same persistent zone are correlated across clusters. CIs will read slightly narrow. | `common.py` zone lifecycle; zones live ≫ 1 day. | Pre-declare a week-cluster CI as a robustness rerun (report alongside; no gate on it). |
| R02-F7 | MINOR | §3 ARMS treated rule | TREATED = "any overlap" mixes a 1-tick clip with full coverage — treated is a diluted arm; if the effect scales with coverage, D is attenuated toward 0. Consistent estimand, weak measurement. | w_p = 0.75·median zone width ⇒ typical overlap partial. | Declare a secondary: treated split by coverage fraction of G (overlap width / w_p), reported with CIs, never gated. |
| R02-F8 | MINOR | D3 co-primary rule | The co-primary runs on a different common-support set (fine key) than the primary, so "same sign with ≥ half magnitude" compares D across two different supported populations — the estimand shifts between the two numbers being compared. Declared implicitly, never stated. | D3 text; supT vs supT_fine tables differ materially. | Add one sentence: "The co-primary estimate uses its own fine-key common-support set; the comparison to the primary D is a point-estimate rule (`D_fine ≥ 0.5·D_primary`, same sign) across differing support, declared as such." Same for D8: "holds under prevclose" must mean the same sign+half-magnitude rule — say so. |
| R02-F9 | INFO | §3 GRID / `armed_width_atr` | u_g is a full-sample median — a design constant, technically non-causal (same for both arms, harmless to the contrast, but it is a full-sample quantity and should be declared as a design constant). | `arrival_common.armed_width_atr` strides the whole sample. | One clause in §3: "u_g is a fixed design constant per (generator, symbol) measured once over the whole DESIGN window." |
| R02-F10 | INFO | `arrival_events` side rule | `skip_side` is unreachable (c[t−1] strictly inside G ⇒ bar t−1 intersects G ⇒ freshness already rejected). Harmless dead branch; confirms the event rule was transcribed correctly. | Code read + event counters (`skip_side` never fires in probe). | None needed; leave as documentation. |

**Ranking by expected size (sign = direction of bias vs the zone claim):**
F1 (zone recency, −D_bounce/+D_cont, largest: a quarter to a half of treated),
F2 (anchor distance, −D_bounce/+D_cont, ~1-1.4 ATR median gap),
F3 (control contamination + arm timing, −D_bounce/+D_cont, up to ~22%/15% of
line1 controls), F5 (verdict hole, fires only on the most likely surprise),
F4 (estimator ambiguity, size = whatever a borderline D needs), F6-F8 small.

## 2. What the prereg gets RIGHT (checked, stands)

- §0 "deviations and decisions" exists and is specific — the R01 F6 defect is
  fixed in form: every spec choice carries its forcing measurement.
- Estimand in one sentence, falsifier, failure language, per-generator
  underpowered declarations (line1 co-primary; kde_swing THIN SUPPORT), freeze
  bundle definition, FREEZE_ADDENDUM policy — all present.
- Common-support restriction is declared inside the estimand sentence and the
  dropped share is required to be reported — estimand-shift is honest.
- Co-primary is confirmatory-only (cannot create a claim), T/X/C and NONE-share
  are ungated secondaries — multiplicity family of 12 is coherent under BH.
- Gates, floors, margins, tie-breaks, doubled bar, thin-support flag are all
  numeric and pre-committed; the supT floor inputs are already measured, so
  they cannot be argued about after outcomes.
- Harness parity to the prereg text: grid formula, event rule (strict 24-bar
  freshness, ≥1·A(t) away-close, side from c[t−1]), arm margins, feature set,
  `armed_views_cached` (the R01 parity-certified path, imported read-only) —
  all match. Verified line-by-line.

## 3. Outcome-blindness — verified, not trusted

Read `arrival_common.py`, `arrival_run.py`, `arrival_freeze.py`,
`arrival_outcome.py`, `arrival_sens.py`, `tests/test_arrival.py` in full.
Every feature is a function of bars ≤ t (freshness window `[t-24,t-1]`, r5
window `[t-1440,t-1]`, armed state replayed to t, grid from the day-open bar).
No bounce/break/continuation/NONE column exists in the extraction path;
`arrival_outcome.py` is a thin map onto the frozen `phys_resolve` and is
imported only by the synthetic unit tests. The resolver tests run on synthetic
bars only. My own probe recomputed the event/arm pipeline on real DESIGN data
and touched no outcome. CLEAN.

## 4. Method and scope of this review

One python process, `OMP_NUM_THREADS=4`, BelowNormal, DESIGN split only,
EURUSD first 40,000 M5 bars; script `PA_Pro/_scratch/prereg_review/probe_arms.py`
(pre-event features only: anchor distance, live-zone overlap, arm-at-t−1
flips, zone-overhang touches). The slice covers ~142 days; the measured gaps
are large enough that the sign is not in doubt, but all numbers should be
re-measured at full scale when the harness changes land. Read-only everywhere
except this file and the scratch script; no git state touched.

## 5. Recommendation

FAIL now, cheap: land fixes 1-4 (F1 FRESH-TO-ZONE clause; F2 anchor-distance
in both keys; F3 arms-at-t−1 + live-zone control; F4 estimator spec pins +
adverse-direction line), regenerate the §3 arm tables and supT/supC under the
final key, re-apply the 0.90 floor and re-issue for review. `line1_cluster`
should be expected to degrade further under the new key — decide its status
from the re-measured table, not by argument.
