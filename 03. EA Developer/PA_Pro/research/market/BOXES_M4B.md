> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**

# M4b — shifted-edge placebo (P-SHIFT) — DESIGN 2016–2021

Addendum `STUDY_PLAN_ADDENDUM_M4B.md` prereg T000392.  Arm OUT:
fake edges g~U[0.5,2]*ABR beyond real edges (fake pokes); Arm IN: interior level lo+u*h, u~U[0.2,0.8] (fake breaks).
D = matched-strata contrast; B=2000; BH q=0.10 over 5 tests.

Caveat: OUT-arm fake pokes can only occur during excursions >= g*ABR beyond the real edge (the parent box dies at its own break), i.e. deeper-wick episodes than the average real poke.  Strata control side/time/ABR/height/depth but not that episode-level selection — treat the sign of D as directional.

## counts (acceptance: >=500 pooled, >=30/symbol/arm)

| sym | SPK pokes | SBRK breaks |
|---|---|---|
| EURUSD | 1001 | 5820 |
| GBPUSD | 722 | 5286 |
| USDJPY | 888 | 5583 |
| AUDUSD | 889 | 6034 |

## descriptive rates

| sym | P(reach opp) real | plac | P(conv) real | plac | race24 real | plac |
|---|---|---|---|---|---|---|
| EURUSD | 0.226 | 0.381 | 0.336 | 0.260 | 0.850 | 0.838 |
| GBPUSD | 0.214 | 0.381 | 0.355 | 0.206 | 0.820 | 0.804 |
| USDJPY | 0.196 | 0.336 | 0.350 | 0.251 | 0.853 | 0.827 |
| AUDUSD | 0.207 | 0.366 | 0.349 | 0.240 | 0.845 | 0.831 |

## F-Xb — formal tests (BH q=0.10)

| test | D | CI | p | q | n_real | n_plac | stable |
|---|---|---|---|---|---|---|---|
| race24 | 0.0114 | 0.0044–0.0170 | 0.0030 | 0.0075 | 37199 | 22572 | YES |
| fb(0,1] | -0.0741 | -0.1221–-0.0266 | 0.0010 | 0.0050 | 17404 | 2146 | no |
| fb(1,2] | 0.0789 | -0.4286–0.5754 | 0.7516 | 1.0000 | 3865 | 688 | no |
| fb(2,3] | nan | nan–nan | nan | 1.0000 | 674 | 218 | no |
| fb(3,5] | nan | nan–nan | nan | 1.0000 | 386 | 151 | no |

descriptive fwd-move D (ABR):

| metric | D |
|---|---|
| fwd6_desc | -0.0270 |
| fwd12_desc | -0.0991 |
| fwd24_desc | -0.1121 |
| fwd48_desc | -0.1565 |
