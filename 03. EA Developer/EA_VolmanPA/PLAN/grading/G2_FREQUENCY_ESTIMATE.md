# G2_FREQUENCY_ESTIMATE — VPA-P2b (pre-registered analysis)

Status: `PENDING LEAD ADJUDICATION` · Rule: `PLAN/GRADING_PREREG.md` (SHA256 `1355630CB1C7C28E398E734C1DBCE3FA988D19BE5BA3B9C4EA205168EFD95020`) · pass-1 grades: `GRADES_LLM_PASS1.csv` (SHA256 `610E7E28AA2B1C7F25551727F7BBE9B69D571547FD958A4C105CC5FB6A49A7C9`).

All numbers below are derived from blind pass-1 grades joined with the hidden key AFTER grading. No outcome, no PnL, no MT5. The Lead-adjudicated grade is final; this is a preliminary verdict.

## 1. Sample sizes and rates

- SRS group (in-session raw breaks): n=160 · A=28 B=91 C=41 · p(A+B)=0.744 · Wilson 95% CI [0.671, 0.805]
- Executable group: n=40 · A=2 B=24 C=14 · p(A+B)=0.650 · Wilson 95% CI [0.495, 0.779]

Frame rate: 9,776 in-session breaks / 314 weeks = **31.13/week**. GOAL floor 10/week requires p* = 10/31.13 = **0.3212**.

## 2. Implied A+B cadence

- point: 0.744 x 31.13 = **23.16/week** (CI 20.89 to 25.07)

## 3. Cross-tab grade x funnel stage (SRS)

| funnel stage | n | A | B | C | A+B rate |
|---|---|---|---|---|---|
| executable | 0 | 0 | 0 | 0 | 0.00 |
| skip_no_buildup | 7 | 2 | 4 | 1 | 0.86 |
| skip_no_pressure | 95 | 21 | 54 | 20 | 0.79 |
| skip_chop | 42 | 5 | 28 | 9 | 0.79 |
| skip_bias | 16 | 0 | 5 | 11 | 0.31 |

By session (SRS):

| session | n | A+B | rate |
|---|---|---|---|
| london | 73 | 55 | 0.75 |
| ny | 87 | 64 | 0.74 |

By side (SRS):

| side | n | A+B | rate |
|---|---|---|---|
| 1 | 73 | 53 | 0.73 |
| -1 | 87 | 66 | 0.76 |

Executable group by setup (detector precision proxy):

| setup | n | A | B | C | A+B rate |
|---|---|---|---|---|---|
| pullback_reversal | 33 | 0 | 19 | 14 | 0.58 |
| pattern_break | 7 | 2 | 5 | 0 | 1.00 |

## 4. Preliminary verdict (PENDING LEAD ADJUDICATION)

**VPA-DR1 JUSTIFIED (pre-registered)** — point 0.744 x 31.13 = 23.2/week >= 10.

Pre-registered boundaries: KILL if Wilson-upper x 31.13 < 10/week; DR1 if point x 31.13 >= 10/week; otherwise INCONCLUSIVE with N*. The drawing constraint excluded 2 early in-session breaks without 120 bars of history (9,778 -> 9,776; the prereg's 31.14 becomes 31.13; the decision boundaries are unchanged at 0.03% scale).

Notes: (a) pass-1 is the worker-LLM grading; the Lead's independent blind subset is the adjudicating grade; (b) the executable-group rate is a precision proxy for the current detector, not a cadence; (c) no case's future bars were drawn or consulted.

## 5. Provenance and drawing QA

- Pass-1 grading sessions (each grader saw only PNGs + the rubric, 6 parallel workers):
  `ses_f44d91a4cffeffvMuVQC51AehZ` (34), `ses_f44d918dbffeyjXvMJVmAO4Cbh` (34),
  `ses_f44d91799ffeoez6cW3Uep9bfH` (33), `ses_f44d91668ffewZPWLfUP8OM1Kl` (33),
  `ses_f44d9152effeki5Vd4pBhtPr3j` (33), `ses_f44d913e0ffe1UT3n2m2q7gVMS` (33).
- `GRADES_LLM_PASS1_RAW.txt` -> `GRADES_LLM_PASS1.csv`; 200 unique case ids, grades in {A,B,C},
  100% coverage of case_001..case_200.
- Drawing QA (`DRAW_QA.csv`): 200/200 cases have `ok_last_is_decision=1`, `ok_no_future=1`,
  `n_bars=120`; `first_drawn = decision_bar_idx - 119` for every case.
- Blinding: `KEY_HIDDEN.csv` was opened only after `GRADES_LLM_PASS1.csv` was written and hashed;
  the grader prompts contained no funnel/skip/outcome information and no access to INDEX/KEY files.
- What the cross-tab says for DR1 (preliminary): the strongest discriminative gate in this sample is
  `skip_bias` (A+B 31% vs sample 74%) while `skip_no_pressure` (79% A+B, n=95) and `skip_chop`
  (79% A+B, n=42) reject mostly human-tradeable cases; `skip_no_buildup` rejected 7 sampled cases of
  which 6 were A/B. Executable precision: pattern-break 7/7 A+B, pullback-reversal 19/33 A+B.
  DR1 should therefore target the discriminating features rather than widening the AND-stack.