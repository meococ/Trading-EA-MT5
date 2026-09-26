# M2AI_REPORT — R76 §76.3 scoring of the delegated M2 pack and AI ceiling

EVAL-AUDIT, 2026-09-23. Scored against the sealed key
(`evalcheck/_owner_judge_key/m2_c3_key.json`, never leaves evalcheck).
Lead sees aggregates only. All results are **proxies** (M2-AI /
AI-ceiling); they do not replace the Owner's M2 (R76 §76.4).
Scripts: `_m2ai_score.py`, `_ceiling_ai_score.py`.

## (a) M2-AI per judge (102 items, rubric v1)

| metric | judge linh | judge B |
|---|---|---|
| precision yes/(yes+no) | 18/44 = .409 [.277, .556] | 19/46 = .413 [.283, .557] |
| precision yes/all (cant_tell = no) | 18/48 = .375 [.252, .516] (ct=4) | 19/48 = .396 [.270, .537] (ct=2) |
| golden sensitivity | 16/30 = .533 [.361, .698] | 8/30 = .267 [.142, .444] |
| negative specificity | 19/24 = .792 [.595, .908] | 22/24 = .917 [.742, .977] |
| engine_hit yes-rate (11) | 4/11 = .364 [.152, .646] | 3/11 = .273 [.097, .566] |
| engine_fp yes-rate (37) | 14/37 = .378 [.241, .539] | 16/37 = .432 [.287, .591] |

## (b) Judge validity (pre-registered gates: golden ≥ .60 AND neg ≥ .80)

- **linh: NOT credible** — golden .533 < .60; neg .792 < .80 (both miss narrowly).
- **judgeB: NOT credible** — golden .267 << .60 (neg .917 passes).

Both M2-AI precision numbers are therefore **uninformative** per the
pre-registered rule.  Note both judges say yes to engine false
positives at least as often as to engine hits (.36–.43 vs .27–.38):
rubric v1 gave no criterion that separates them — consistent with
R77 (no EMA/impulse/zombie criteria).

## (c) Inter-judge agreement (recomputed)

- agree 73/102; Cohen's κ = **0.446** (3-class), **0.513** (yes vs not-yes)
  — matches the Lead's reported 0.45 / 0.51.
- Both-yes items: 22 (engine 15, engine_hit only 2, golden 6, negative 1).
  Agreement does not track the key: judges jointly accept far more
  false positives than true hits.

## (d) AI-ceiling vs C-3 on the 10 ceiling panels

16 drawn objects (8 level, 7 box, 1 line), converted per §76.3d and
scored with `eval_v2.py` at each panel's τ; C-3 top-k on the same
panels for comparison.

| family | n goldens | AI hit | C-3 hit |
|---|---|---|---|
| box | 9 | 1/9 = .111 [.020, .435] | 2/9 = .222 [.063, .547] |
| level | 7 | 0/7 [.000, .354] | 0/7 [.000, .354] |
| line | 9 | 0/9 [.000, .299] | 0/9 [.000, .299] |
| bracket | 3 | 0/3 [.000, .561] | 2/3 = .667 [.208, .939] |
| **all** | **28** | **1/28 = .036 [.006, .177]** | **4/28 = .143 [.057, .315]** |

Per panel (AI / C-3 hits): 9.11a 0/1, 9.19a 0/0, 9.23c 1/0, 9.24c 0/1,
9.25b 0/0, 9.36b 0/1, 9.38a 0/0, 9.50a 0/0, 9.62a 0/0, 9.66c 0/5gold→1.

The AI-ceiling is a weak reference (Owner rejected 6/6 overlays):
at 3.6% golden agreement it measures nothing about the ceiling and
must not set any threshold.  Descriptive only, n = 10.

## (e) Owner's open judgments on p099–p102 (§77.4c)

Classes (key): p099 engine_fp(box), p100 **golden**(box),
p101 negative(price), p102 engine_fp(box).

- Owner answered "no" to all four in the open — correct on 3/4
  (both fps + the negative), but rejected **p100, a real golden box**.
- The four items leave the blind pack (now 98 items); his "no" is
  recorded as his answer for each.
- Judge linh on the same four: p099 yes (fp accepted), p100 no
  (golden rejected), p101 yes (negative accepted), p102 no — 1/4.

## Bottom line

M2-AI precision ≈ .41 under both judges but both fail the validity
gates → uninformative.  AI-ceiling = .036 golden agreement vs C-3's
.143 on the same panels.  Neither proxy constrains the Owner's M2;
his own judging session remains the metric of record.
