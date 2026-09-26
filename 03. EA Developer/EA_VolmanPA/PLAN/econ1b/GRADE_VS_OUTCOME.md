# GRADE_VS_OUTCOME - VPA-ECON-1b diagnostic (DESIGN 2016-2021)

Question: does the Volman grade (the 'pro eye': A/B = tradeable, C = pass) predict the OUTCOME of the case when it is traded by the frozen ECON-1 model?
This is exploratory (ECON-1b); it does NOT change the ECON-1 verdict.

## 0. Method

Every labelled case is simulated with the frozen ECON-1 engine imported unchanged (`vpa_econ1_sim.simulate_entries`, `vpa_econ1_costs` scenarios, the same prereg order model: stop order 1 pip beyond the signal-bar extreme, V=3 M5 bars, invalidation cancel, S=8 / TP=16, SL-first inside an M1 bar, Friday/daily flats and the session-end cancel). Costs: **x1 = 1.0 pip** (primary) and **gross = 0.0** (sanity). Only DESIGN 2016-2021 data is loaded.

Engine SHA256 (must match the ECON-1 prereg):

| artifact | SHA256 | matches ECON-1 |
|---|---|---|
| research/lab/vpa_econ1_sim.py | `87D3C73507666B58AAA0553D1A3F6FE0EF03EDFB645D012C59080A2E23E33930` | yes |
| research/lab/vpa_econ1_costs.py | `4B9F0EC330A2003935276876BEF952D1CBCE045F6E54E0EF5F4C01B72532F274` | yes |
| research/lab/vpa_dr1.py | `73497484E2C26EDF44DAE5F1D574C56BBF40BBBFE8192A05AD38B4D782A781E0` | yes |
| research/lab/vpa_data.py | `E0DEC3808AF7D2BD730C1A6185D6E850B306459DDFC00DDD8AA776A909D7212F` | yes |
| research/lab/vpa_econ1_random.py | `07719AF87CB35298B2D990B8339E6883488537E258AC6FB879C08EC19A210A99` | yes |

`vpa_random_baseline.py` (loader/session helper) `2BF11A5BFF9E071070B940C16384A34063164A887C9C66CA17D1732855668A9F`, `vpa_core.py` (v1 records) `B6B72B987738C7B4DEA1043CB4DA539006F43CFE1D13991538F0766E0E507478`, `vpa_econ1_run.py` (helper reuse) `D2F67BA533DAA9700631097A8338E3FD549947325D0638601CEB1006EED83614`.

Frame: 2016-01-04T00:20:00Z -> 2021-12-31T22:55:00Z (440040 M5 bars, 2208641 M1 bars).

## 1. Labelled cases and mapping

- Set 1 (DR3 grading): 180/180 mapped to DR3 records; label = G1/G2/G3 majority (same rule as `vpa_fidelity_dr3.py`, cross-checked against `FIDELITY_DR3.csv`); signal bar = `signal_idx`, invalidation = the record's own `invalidation` (the exact ECON-1 input; the DR3-rule derivation reproduces it 180/180).
- Set 2 (DR3 Lead spot-check): 20/20 Lead-graded cases, all inside set 1.
- Set 3 (v1 Lead blind): 60/60 accounted for - 49 pattern_break cases mapped to the LAST BAR THAT TOUCHED THE BARRIER BEFORE THE BREAK (the DR3 signal-bar definition; scanned from the break bar with the barrier's own lock-time tolerance `barrier_eps_atr*ATR`), 11 pullback_reversal cases mapped to the release bar (v1 has no barrier there; the bar the snapshot/grade is anchored on); 0 unmapped. Invalidation: the DR3 rule at the mapped signal bar (20 derivable, 40 none -> no cancel, exactly as ECON-1 behaves when a record has no invalidation).

- Cross-check against the ECON-1 run itself: every x1 fill of the 120 set-1 accepted cases reproduces its `PLAN/econ1/TRADES_DESIGN.csv` row (reason + r) exactly, and no non-filled set-1 accepted case has a row there (62 matched, 58 absent; the file holds 2436 ECON-1 fills in total).

Grade counts: set 1 majority {'B': 57, 'C': 80, 'A': 43}; set 2 Lead {'C': 14, 'A': 2, 'B': 4}; set 3 Lead {'C': 44, 'A': 5, 'B': 11}.

### Headline

A/B minus C win rate (x1): pooled Lead sets -25.00pp CI [-47.65, +7.42] (N=12 WR=25.00% PF=0.667 vs N=34 WR=50.00% PF=1.761); set 1 -2.96pp CI [-21.46, +15.65] (N=50 WR=34.00% PF=1.030 vs N=46 WR=36.96% PF=0.993). Every comparison in this diagnostic sits at or below zero: the A/B grades do not show the higher win rate. The rule's classification is in section 5.

## 2. Grade A/B vs grade C - fills, win rate, PF (x1)

| comparison | grade weight (A/B / C) | A/B fills | C fills | dWR (A/B - C) | 95% CI (Newcombe) | rule |
|---|---|---|---|---|---|---|
| set 1 - DR3, majority of G1/G2/G3 | 100 / 80 (of 180) | N=50 WR=34.00% PF=1.030 | N=46 WR=36.96% PF=0.993 | -2.96pp | [-21.46, +15.65] | INCONCLUSIVE |
| set 2 - DR3 spot-check, Lead grades | 6 / 14 (of 20) | N=3 WR=33.33% PF=1.000 | N=7 WR=42.86% PF=0.662 | -9.52pp | [-51.59, +43.75] | INCONCLUSIVE |
| set 3 - v1 blind, Lead grades (anchor B) | 16 / 44 (of 60) | N=9 WR=22.22% PF=0.571 | N=27 WR=51.85% PF=2.119 | -29.63pp | [-53.20, +7.47] | NO |
| pooled Lead (sets 2+3, anchor B) | 22 / 58 (of 80) | N=12 WR=25.00% PF=0.667 | N=34 WR=50.00% PF=1.761 | -25.00pp | [-47.65, +7.42] | NO |

Matched-random reference line (ECON-1 x1): WR **29.94%** (N=42257; `RANDOM_MATCHED.csv` recomputation: 29.92%, 25 rows round to r=0.000000 at 6 dp).

Gross (no cost) robustness:

| comparison | A/B fills | C fills | dWR | 95% CI | rule (informative) |
|---|---|---|---|---|---|
| set 1 - DR3, majority of G1/G2/G3 | N=50 WR=36.00% PF=1.141 | N=46 WR=45.65% PF=1.492 | -9.65pp | [-28.13, +9.69] | INCONCLUSIVE |
| set 2 - DR3 spot-check, Lead grades | N=3 WR=33.33% PF=1.000 | N=7 WR=42.86% PF=0.725 | -9.52pp | [-51.59, +43.75] | INCONCLUSIVE |
| set 3 - v1 blind, Lead grades (anchor B) | N=9 WR=22.22% PF=0.571 | N=27 WR=55.56% PF=2.524 | -33.33pp | [-56.51, +3.95] | NO |
| pooled Lead (sets 2+3, anchor B) | N=12 WR=25.00% PF=0.667 | N=34 WR=52.94% PF=2.049 | -27.94pp | [-50.37, +4.61] | NO |

Fill-status mix (x1; the non-fills are cases where the stop order never traded through in its V=3-bar window, was cancelled by the invalidation, or was Friday-vetoed):

| comparison | group | FILLED | CANCELLED | EXPIRED | VETO_FRIDAY | fill rate |
|---|---|---|---|---|---|---|
| set 1 - DR3, majority of G1/G2/G3 | A/B | 50 | 6 | 44 | 0 | 50.0% (100 cases) |
| set 1 - DR3, majority of G1/G2/G3 | C | 46 | 3 | 31 | 0 | 57.5% (80 cases) |
| set 2 - DR3 spot-check, Lead grades | A/B | 3 | 0 | 3 | 0 | 50.0% (6 cases) |
| set 2 - DR3 spot-check, Lead grades | C | 7 | 1 | 6 | 0 | 50.0% (14 cases) |
| set 3 - v1 blind, Lead grades (anchor B) | A/B | 9 | 2 | 5 | 0 | 56.2% (16 cases) |
| set 3 - v1 blind, Lead grades (anchor B) | C | 27 | 3 | 14 | 0 | 61.4% (44 cases) |
| pooled Lead (sets 2+3, anchor B) | A/B | 12 | 2 | 8 | 0 | 54.5% (22 cases) |
| pooled Lead (sets 2+3, anchor B) | C | 34 | 4 | 20 | 0 | 58.6% (58 cases) |

### Sensitivity: set-3 signal-bar choice (x1)

For the v1 cases the signal bar is not given by the v1 record (its `bar_idx` is the break bar). Three anchors are computed and all pass through the same order model:

- **B (primary)**: the last bar that touched the barrier before the break, scanned back from the break bar with the barrier's own lock-time tolerance (`barrier_eps_atr*ATR`) - the DR3 definition (`vpa_dr1.py:288-291`) and what the task prescribes. Gap to the break: median 3 M5 bars (1-12).
- **A**: the barrier's lock pivot - the frozen DR3 code's proxy, because the v1 touch list is recorded at lock time only (`tch[-1] == lock_idx`). Here the V=3 order window often expires before the break.
- **C**: the v1 break/decision bar itself - the bar the graded snapshot ends on.

| set-3 anchor | grade weight (A/B / C) | A/B fills | C fills | dWR | 95% CI | rule |
|---|---|---|---|---|---|---|
| set 3, anchor A (barrier lock pivot) | 16 / 44 (of 60) | N=5 WR=40.00% PF=1.333 | N=9 WR=55.56% PF=2.447 | -15.56pp | [-53.65, +31.33] | INCONCLUSIVE |
| set 3 - v1 blind, Lead grades (anchor B) | 16 / 44 (of 60) | N=9 WR=22.22% PF=0.571 | N=27 WR=51.85% PF=2.119 | -29.63pp | [-53.20, +7.47] | NO |
| set 3, anchor C (v1 break bar) | 16 / 44 (of 60) | N=8 WR=12.50% PF=0.321 | N=27 WR=55.56% PF=2.484 | -43.06pp | [-62.79, -3.95] | NO |
| pooled Lead, anchor A (lock pivot) | 22 / 58 (of 80) | N=8 WR=37.50% PF=1.200 | N=16 WR=50.00% PF=1.466 | -12.50pp | [-44.92, +26.27] | INCONCLUSIVE |
| pooled Lead (sets 2+3, anchor B) | 22 / 58 (of 80) | N=12 WR=25.00% PF=0.667 | N=34 WR=50.00% PF=1.761 | -25.00pp | [-47.65, +7.42] | NO |
| pooled Lead, anchor C (break bar) | 22 / 58 (of 80) | N=11 WR=18.18% PF=0.486 | N=34 WR=52.94% PF=2.007 | -34.76pp | [-55.10, -1.09] | NO |

## 3. Set 1 detail (x1)

| grade | cases | fills | fill rate | WR | PF |
|---|---|---|---|---|---|
| A | 43 | 18 | 41.9% | 44.44% | 1.600 |
| B | 57 | 32 | 56.1% | 28.12% | 0.783 |
| C | 80 | 46 | 57.5% | 36.96% | 0.993 |

Fidelity inside DR3 (accepted cases only, x1): A/B fills 43 WR 37.21% PF 1.185 vs C fills 19 WR 47.37% PF 1.465 -> dWR -10.16pp CI [-34.71, +14.83] (INCONCLUSIVE).

## 4. Power note

With these sample sizes (x1 fills) the smallest A/B vs C win-rate difference detectable at 80% power (two-sided alpha 0.05, reference p = the observed C win rate):

| comparison | n A/B fills | n C fills | p_ref (C WR) | MDD @80% power | observed CI half-width |
|---|---|---|---|---|---|
| set 1 - DR3, majority of G1/G2/G3 | 50 | 46 | 37.0% | 27.5pp | 18.6pp |
| pooled Lead (sets 2+3, anchor B) | 12 | 34 | 50.0% | 36.6pp | 27.5pp |

So a true effect smaller than roughly the MDD above cannot be separated from noise with these labelled samples; the CI, not the point estimate, carries the information.

## 5. Verdict

Rule (task ECON-1b): YES if A/B - C >= +8pp with CI lower bound > 0 in the pooled Lead-labelled sets (2+3) or in set 1; NO if the CI upper bound < +8pp; otherwise INCONCLUSIVE.

- Set 1 (majority): dWR -2.96pp CI [-21.46, +15.65] -> **INCONCLUSIVE**
- Set 2 (Lead, DR3 spot-check): dWR -9.52pp CI [-51.59, +43.75] -> INCONCLUSIVE
- Set 3 (Lead, v1; anchor B): dWR -29.63pp CI [-53.20, +7.47] -> NO
- Pooled Lead (2+3; anchor B): dWR -25.00pp CI [-47.65, +7.42] -> **NO**
- Sensitivity anchors (rule values): A: set 3 INCONCLUSIVE, pooled INCONCLUSIVE; C: set 3 NO, pooled NO

Rule reading used here: the task's bullets name two comparisons (the pooled Lead sets 2+3, and set 1). Evaluated in order - a YES in either comparison wins; otherwise a NO in either comparison (CI upper bound < +8pp) gives NO; otherwise INCONCLUSIVE. Under this reading the NO comes from the pooled Lead-labelled sets (CI upper +7.42pp < +8pp); set 1 alone is INCONCLUSIVE (CI upper +15.65pp). If the rule were instead read as 'NO only when BOTH comparisons exclude +8pp', the verdict would be INCONCLUSIVE on the strength of set 1's wide interval - the substantive read-out below is unchanged either way.

**Grade predicts outcome: NO**

Substance (independent of the rule reading): in every comparison of this diagnostic the A/B point estimate is at or below the C point estimate, and no comparison shows A/B winning more, so the data provide no support for 'A/B setups win more'. The pooled Lead-labelled fills (n=12 A/B vs n=34 C) exclude a +8pp A/B advantage; the set-1 sample is too small (n=50 vs 46 fills, MDD ~28pp) to exclude it on its own.

## 6. Deviations & assumptions

1. Set 1 uses the DR3 grading cases' own labels (G1/G2/G3 majority) and the DR3 record invalidation - bit-identical to the ECON-1 entry definition.
2. Set 3 signal bar (primary, anchor B): for pattern_break v1 cases, the last bar that touched the barrier before the break - the DR3 definition - scanned back from the v1 break bar with the barrier's own lock-time tolerance (`barrier_eps_atr * ATR`, the same eps that accepted the barrier's touches at lock). The frozen DR3/v1 detectors record touches only at lock time, so anchors A (lock pivot = the code-literal `tch[-1]`) and C (the break bar, i.e. the graded snapshot's last bar) are reported as labelled sensitivities. The 11 pullback_reversal cases (no barrier) use the release bar in all anchors.
3. Set 3 invalidation: derived by the DR3 rule (`_buildup_dr1` at the mapped signal bar, extreme +/-0.10xATR). On set 1 this derivation reproduces the ECON-1 `invalidation` 180/180 (0 mismatches), so it is the ECON-1 rule; when no DR3 buildup window exists there is no cancel (as in ECON-1 for records without invalidation).
4. Grades for set 3 come from the Lead's v1 blind grading (`GRADES_LEAD_BLIND.csv`), assigned on the chart ending at the v1 break/decision bar, while the simulated entry uses the mapped signal bar; the same anchor applies to set 1 (snapshot ends at the trigger bar).
5. This is a diagnostic on a sample of 240 cases; it is not a new strategy run and it does not modify any parameter, code, or verdict of ECON-1.
6. The ECON-1 cost/exit semantics (incl. the inherited Thursday/'FRIDAY' quirk) are unchanged and identical for A/B and C, so the comparison is internally consistent.
7. `RANDOM_MATCHED.csv` stores `r` rounded to 6 dp; recomputing its win rate from the file gives 29.92% while the ECON-1 run itself recorded 29.94% (`ECON1_METRICS.json`) - 25 tiny-r rows round to exactly 0.000000. The reference line quotes the ECON-1 run value.
8. Each trade's `r` is rounded to 6 dp before aggregation (the engine's fill/exit semantics are untouched), so every number printed here - including PF - is exactly reproducible from `CASES_OUTCOMES.csv`. No fill in this sample has 0 < |r| < 1e-6, so no win/loss classification changes; the reviewers' first pass flagged two PF cells whose 3rd decimal differed by one unit from the CSV-based recomputation, and this rounding removes that discrepancy.

## 7. Reproduction

`python "03. EA Developer/EA_VolmanPA/PLAN/econ1b/econ1b_run.py"` prints every number into `RUN_LOG.txt` and writes `CASES_OUTCOMES.csv` (one row per case: labels, mapping, signal-bar anchors, fill status, exit reason, R for x1 and gross + the A/C anchor outcomes) and `EVIDENCE.json` (all group results, hashes, power).
