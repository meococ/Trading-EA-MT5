# CALIBRATION_V2 — LLM grader acceptance (VPA-B1 Phase 4)

Rule: acceptance to use an LLM grader at scale = **binary (A/B vs C) Gwet AC1 vs
Lead ≥ 0.60 for BOTH graders**. Graders saw only `GRADING_RUBRIC_V2.md` + the 60
snapshots; they did not see Lead grades or hidden keys.

## Provenance (hashes recorded BEFORE opening the Lead grades)
- `GRADES_V2_G1.csv` SHA256 `91F842E218884A5AB74FACDC5D025C50008100B6BFA70F389A6AFFE72BBF2BFD`
- `GRADES_V2_G2.csv` SHA256 `C1A7069223DBE6C73277EA7E851245E87E7BA67AC2618E65871175E957310784`
- Case set = the 60 `case_id` in `GRADES_LEAD_BLIND.csv` (extracted without reading grades).
- Process note: a first grader run used a wrong hand-built case list; those files are
  kept as `GRADES_V2_G1_wrongset.csv` / `GRADES_V2_G2_wrongset.csv` and are NOT used.

## Results (n=60, Lead grade = reference)
| pair | binary AC1 (A/B vs C) | binary raw | 3-class AC1 | 3-class raw |
|---|---|---|---|---|
| G1 vs Lead | **0.770** | 0.867 | 0.742 | 0.800 |
| G2 vs Lead | **0.606** | 0.783 | 0.667 | 0.750 |
| G1 vs G2 | 0.467 | 0.717 | 0.483 | 0.617 |

Correction (T-VPA-DR1, A5): the first emission omitted the Gwet 1/(K−1) factor in
`pe`; 3-class AC1 values were 0.636 / 0.502 / 0.206 and are now 0.742 / 0.667 /
0.483 (matches the Lead's independent recomputation). Binary AC1 uses K=2 so its
values are unchanged (0.770 / 0.606 / 0.467). Re-emitted
`CALIB_V2_RESULTS.txt`; `vpa_calibration_v2.py` fixed.

Aggregate A+B rates: Lead 26.7% (16/60) · G1 33.3% (20/60) · G2 41.7% (25/60).
The previous pass-1 grader (rubric v1) had binary AC1 **−0.03**; rubric V2 +
explicit severe-flaw list moved both graders to PASS.

## Verdict
**PASS — both graders clear binary AC1 ≥ 0.60.** An LLM grader using
`GRADING_RUBRIC_V2.md` may be used at scale, with the Lead retaining adjudication
on any subset. Notes:
- G2 sits close to the threshold (0.606); scale runs should use **two graders and
  require agreement** (G1-vs-G2 binary AC1 0.467 means disagreements are common
  enough that a single grader is not a precision instrument).
- 3-class agreement is weaker (0.50–0.64): the A-vs-B boundary is the noisy one;
  use A/B vs C for gating decisions and treat A/B separation as advisory.
- One rubric revision was allowed by the task; it was used (v1 → v2) and this is
  the only attempt possible against the Lead labels. No further rubric tuning
  against Lead grades is permitted.
