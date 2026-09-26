# FIDELITY_DR3 — accepted vs rejected (blind, 180 cases, F5)

Hash-before-unblind: `HASHES_BEFORE_UNBLIND.txt` (G1 5bef16c7…, G2 7df3c09a…, written before this join). G3 graded the 60 disagreements only (21/21/18); no-majority 3-way splits: 4 (median fallback, documented).

Sample: 120 accepted + 60 rejected (trend 51, integrity 9), 30/year 2016-2021, all bars outside ±50 of the 60 burned cases (E3). No outcomes (F7).

| count | accepted | rejected | A/B share acc | A/B share rej | diff | 95% CI | gate |
|---|---|---|---|---|---|---|---|
| dual | 53/78 | 5/42 | 67.9% | 11.9% | +56.0pp | [+38.9, +67.5]pp | PASS |
| majority | 84/120 | 16/60 | 70.0% | 26.7% | +43.3pp | [+28.2, +55.4]pp | PASS |

F5 gate: diff >= +15pp AND CI lower > 0 AND A/B share(accepted, majority) >= 40%.

## Leniency caveat (F5)

Both graders are LLMs with the known leniency: they see only 120 bars ending at the decision bar, they cannot know the outcome, and the rubric's 'A' bar is high. The dual-agreement count (both graders identical) is the stricter measure; the majority count includes G3's tie-breaks. The difference and CI are the discriminative evidence, not the absolute A/B levels.
