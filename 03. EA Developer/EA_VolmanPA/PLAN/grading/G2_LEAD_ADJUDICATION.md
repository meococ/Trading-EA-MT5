# G2 — Lead adjudication (VPA-P2b)

Date: 2026-09-20 03:20 (UTC+7) · Lead: Claude · Pre-registered rule: `GRADING_PREREG.md` (SHA 1355630C…5020)

## Provenance
- LLM pass-1: `GRADES_LLM_PASS1.csv`. SHA256 `610E7E28…A7C9` verified to match the worker report. The grades were fixed before the Lead graded.
- Lead blind grades: `GRADES_LEAD_BLIND.csv`, written 03:19:15 with SHA256 `10b809e6…633c`, BEFORE opening GRADES_LLM_PASS1 or KEY_HIDDEN.
  - Grade set: 60 cases = the 10 worker-picked eyeball cases + 50 random (Python `random.Random(7).sample`) from the remaining 190.
  - Disclosure: the Lead saw only the LLM's AGGREGATE counts (SRS A+B 119/160) in the report summary before grading. The Lead never saw per-case LLM grades.
- Drawing QA: 10/10 eyeball snapshots are correct. The last bar is the decision bar, and the barrier, touch marks, EMA25 and entry line are consistent.

## Inter-rater agreement (60 cases)
| | raw agreement | Gwet AC1 |
|---|---|---|
| 3-class A/B/C | 41.7% | 0.16 |
| binary A/B vs C | 48.3% | **−0.03** |

The LLM grader is **not usable**. It graded 30 of the Lead's 44 C cases as A/B (confusion lead→llm: C→A 5, C→B 25). It is systematically lenient, and its A/B rate (74%) carries no information. Per the pre-registration, the **Lead grade is final**.

## Frequency estimate (Lead grades)
| group | n | A | A+B | p (Wilson 95%) | implied Volman-grade cadence/week (× 31.1) |
|---|---|---|---|---|---|
| SRS in-session raw breaks (all graded) | 47 | 4 | 13 | 0.277 [0.169, 0.418] | **8.6 [5.3, 13.0]** |
| SRS, random-selected only (excl. eyeball) | 40 | 3 | 11 | 0.275 [0.161, 0.428] | 8.6 [5.0, 13.3] |
| Detector executables (all graded) | 13 | 1 | 3 | 0.231 [0.082, 0.503] | — |
| Detector executables, random-selected only | 10 | 0 | 1 | 0.10 [0.02, 0.40] | — |

## Verdict under the pre-registered rule
- KILL requires the Wilson upper bound × 31.1 < 10. Here it is 13.0, so **no KILL**.
- DR1 requires the point estimate × 31.1 ≥ 10. Here it is 8.6, so **no DR1**.
- → **INCONCLUSIVE.** Resolving whether the upper bound falls below 10/week needs about 380 more Lead-graded SRS cases, assuming p ≈ 0.28.

## Diagnostic findings (usable for any revision)
1. **Current detector precision is poor.** Its executables are no more Volman-grade than random breaks (0.23 vs 0.28). The T2-derived AND-stack selects on the wrong things.
2. **The gates reject the good cases.** Of the 16 Lead A/B cases, 9 were rejected by `skip_no_pressure` and 4 by `skip_chop`. Only 3 reached "executable".
3. **Features the Lead used to separate A/B from C:**
   - trend alignment (EMA25 slope and price on the trend side);
   - a tight buildup/squeeze against the barrier (often EMA pressing price into the level);
   - ROOM of at least 2R to the nearest prior swing high/low or congestion;
   - no chop (barb wire, news spikes).
   The dominant C reasons were counter-trend breaks, chop, blocked room and chasing.
4. **ENTRY-SEMANTICS DEFECT.** The decision is taken at the close of the BREAK bar and the entry is placed 1 pip beyond it. This chases long break bars: in cases 004, 034 and 198 the entry sits 10–18 pips beyond the barrier and the stop lands inside the bar. Volman's entry is a stop order resting 1 pip beyond the signal (pre-break) bar, filled by the break itself. Any revision must fix this.
5. The GOAL cadence floor (10/week/symbol) sits **above** the point estimate of Volman-grade frequency on EURUSD M5 London+NY (≈ 8.6/week). Even a perfect detector is expected to fail the cadence gate unless the Owner amends it.

## Status
Lane paused at G2 = INCONCLUSIVE. The cadence question is escalated to the Owner. No further worker compute until the Owner decides.
