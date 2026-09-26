# RECALL_SUMMARY — DR1 vs the Lead's eye (60 BURNED cases, E3)

Source: `RECALL_TRACE.csv` (one row per case, full gate values). No outcome fields (E4). Set burned: no selection/fidelity use (E3).

## 1. Categories (i)-(iv)

| category | all | Lead A/B (16) | Lead C (44) |
|---|---|---|---|
| (i) no barrier locked nearby | 11 | 1 | 10 |
| (ii) no signal eval | 26 | 11 | 15 |
| (iii) evaluated but failed | 23 | 4 | 19 |
| (iv) executable | 0 | 0 | 0 |

Reasons for (ii):

- case_003 (A): barrier consumed as missed break at t=428328
- case_004 (C): barrier consumed as missed break at t=43174
- case_008 (C): barrier consumed as missed break at t=396088
- case_020 (B): barrier consumed as missed break at t=140441
- case_021 (B): barrier consumed as missed break at t=56131
- case_022 (C): barrier consumed as missed break at t=142971
- case_028 (C): no close inside [B-0.05A, B+0.25A] within +/-12 bars (signal-bar definition/window/session)
- case_029 (C): barrier consumed as missed break at t=186743
- case_034 (C): barrier consumed as missed break at t=19641
- case_065 (B): barrier consumed as missed break at t=174580
- case_067 (A): barrier consumed as missed break at t=72716
- case_085 (B): barrier consumed as missed break at t=1927
- case_093 (C): barrier consumed as missed break at t=101101
- case_104 (C): barrier consumed as missed break at t=424107
- case_106 (C): barrier consumed as missed break at t=105571
- case_112 (C): barrier consumed as missed break at t=100905
- case_118 (B): barrier consumed as missed break at t=337431
- case_119 (C): barrier consumed as missed break at t=296931
- case_148 (C): barrier expired before the case bar
- case_153 (B): barrier consumed as missed break at t=357857
- case_154 (B): barrier consumed as missed break at t=435763
- case_155 (C): barrier consumed as missed break at t=173792
- case_160 (A): no close inside [B-0.05A, B+0.25A] within +/-12 bars (signal-bar definition/window/session)
- case_178 (B): barrier consumed as missed break at t=154220
- case_191 (C): barrier consumed as missed break at t=287572
- case_198 (C): barrier expired before the case bar

## 2. Discrimination table (evaluated cases only)

A gate that fails most A/B cases is mis-specified; one that fails C much more than A/B is a good discriminator; equal failure is noise.

| gate | fail A/B | rate A/B | fail C | rate C | rate gap (C-AB) |
|---|---|---|---|---|---|
| warmup | 0/4 | 0.0 | 0/19 | 0.0 | 0.0 |
| session | 2/4 | 0.5 | 10/19 | 0.526 | 0.026000000000000023 |
| direction | 1/4 | 0.25 | 3/19 | 0.158 | -0.092 |
| trend | 0/4 | 0.0 | 14/19 | 0.737 | 0.737 |
| chop | 1/4 | 0.25 | 1/19 | 0.053 | -0.197 |
| buildup | 2/4 | 0.5 | 12/19 | 0.632 | 0.132 |
| room | 2/4 | 0.5 | 7/19 | 0.368 | -0.132 |
| adverse | 2/4 | 0.5 | 6/19 | 0.316 | -0.184 |
| anti_chase | 2/4 | 0.5 | 2/19 | 0.105 | -0.395 |
| cost | 0/4 | 0.0 | 0/19 | 0.0 | 0.0 |

## 3. Reading

- Lead A/B cases with an evaluation: 4/16; Lead C: 19/44.
- A/B lost before evaluation: (i) 1, (ii) 11.
- C lost before evaluation: (i) 10, (ii) 15.
