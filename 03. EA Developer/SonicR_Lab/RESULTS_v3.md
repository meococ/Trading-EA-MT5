# RESULTS_v3.md - ROUND 2C: CROSS-SYMBOL REPLICATION OF THE FROZEN RULES

Lead brief 23/09 20:20Z. Question: do the round-2B/A1 findings replicate
on 10 symbols they were never fitted on? No parameter changed; DESIGN
window only; VALIDATION and HOLDOUT of all 12 symbols unread
(test_holdout_guard.py, 3/3).

PREREG_V3.md sha256 =
2f5232ebb29fa53d9b0e06bc8aaee0293c7357bd60197263a20e3f8faa91f77f
frozen 2026-09-23T20:33:45Z, BEFORE the first basket P/L file
(~20:33:50Z). Census was outcome-blind; W4d Q recomputed per symbol
from each symbol's own F0_J census (runs/q_w4d_2c.json).

## 1. Basket data checks (BASKET.md, out/basket_checks.csv)

All 10 symbols: 100% DESIGN-week coverage -> none dropped. Suspect
share ~1.1% everywhere. Roll windows discovered from suspect clustering:
23:59-00:2x server (GBPJPY/AUDJPY 00:00-00:16/17). The same rollover
artifact as EUR/XAU: per-day max-range inside the roll window vs the
two adjacent quiet windows - median 19.1x-27.7x, P99 56.7x-103.9x;
max |open-prev close| median 33x-68x. The feed defect is systematic
across the basket, so H1 (skip suspect) remains the validity harness.

Costs applied as written: Lead ECN-like round-trip pips (1.2-2.6 by
symbol) decomposed into the harness model; E1b +2.0p ask side
(GBPJPY +3.0p) inside each discovered window.

## 2. Census (outcome-blind, out/census_2c.csv)

Signals/week per symbol is strikingly uniform across the basket:
F0_J ~1.9-2.2, F2_NH_b ~6.4-7.1, F5_S2 ~0.55-0.87, F5_S3 ~0.12-0.26.
Basket sums: F0_J ~20.4/wk, F2_NH_b ~68.7/wk, F5_S2 ~7.2/wk,
F5_S3 ~1.7/wk. E2 removals tiny on FX (0-14 per symbol, vs hundreds on
XAU). Q(a20) per symbol: -0.0028 to -0.0074 (same sign and magnitude
as EUR/XAU's -0.0063/-0.0054).

## 3. R1 - essence replication: FAIL on both harnesses

Per-symbol Spearman(S, r_x1) on F0_J trades; Stouffer z weighted by
sqrt(n):

| harness | Stouffer z | p (one-sided) | rho>0 count (n>=100) |
|---------|-----------|---------------|----------------------|
| H0 | 0.65 | 0.258 | 6/10 |
| H1 | 0.15 | 0.442 | 5/10 |

Every basket rho sits between -0.061 and +0.056 (vs EUR 0.084-0.103,
XAU 0.104 on EUR/XAU runs). The confluence dose-response does NOT
replicate: on never-fitted symbols S is information-free. The EUR/XAU
result was likely best-of-N luck (the 2B essence had p~0.004-0.02 on
exactly the two symbols the elements were developed on).

## 4. R2 - config replication: none meet the gate; F2_NH_b closest

True pooled basket PF_R = sum(posR)/sum(|negR|) over all basket trades:

| cfg | pooled x1 H0 | pooled x1 H1 | x15 H1 | >1.00 count H1 | R2 verdict |
|-----|-------------|-------------|--------|----------------|-----------|
| F0_J | 0.804 | 0.892 | ~0.85 | 2/10 | FAIL |
| F2_NH_b | 1.049 | 1.063 | 1.018 | 9/10 | FAIL (x1<1.10) |
| F5_S2 | 0.949 | 0.998 | ~0.95 | 6/10 | FAIL |
| F5_S3 | 0.893 | 0.931 | ~0.90 | 3/10 | FAIL |

F2_NH_b meets two of three sub-criteria (x15>=1.00 on H1; >1.00 on
9/10 symbols) but pooled x1 = 1.049/1.063 < 1.10 -> R2 not met.

## 5. R3 - luck check: F2_NH_b passes, the rest fail

Pooled basket PF_R vs pooled random-entry null (20 seeds/symbol,
bootstrap pooling, 2000 draws):

| cfg | pooled H1 | pct of pooled null | verdict |
|-----|-----------|--------------------|---------|
| F0_J | 0.892 | 39 | FAIL (inside null) |
| F2_NH_b | 1.063 | 100 | PASS (H0 also 100) |
| F5_S2 | 0.998 | 79 | FAIL |
| F5_S3 | 0.931 | 41 | FAIL |

Pooled null p95 ~0.95-0.97 for the high-count configs (F0_J/F2_NH_b;
F5_S3's sparse null reaches ~1.15-1.55) - across 10 symbols and ~14k
trades the luck envelope collapses to ~1.0; F2_NH_b's 1.06 clears it
completely. The signal's directional edge is REAL on the basket, just
smaller than the replication gate.

## 6. Per-symbol table (PF_R x1, H0 / H1)

| symbol | F0_J | F2_NH_b | F5_S2 | F5_S3 |
|--------|------|---------|-------|-------|
| GBPUSD | 0.99/1.07 | 1.24/1.22 | 1.24/1.26 | 1.38/1.35 |
| USDJPY | 0.98/1.09 | 1.13/1.17 | 0.91/1.01 | 1.04/1.23 |
| AUDUSD | 0.66/0.73 | 0.97/1.01 | 0.55/0.56 | 0.76/0.79 |
| NZDUSD | 0.70/0.77 | 1.08/1.03 | 0.83/0.87 | 0.76/0.81 |
| USDCAD | 0.76/0.85 | 0.82/1.00 | 1.15/1.19 | 1.14/1.18 |
| USDCHF | 0.80/0.89 | 1.12/1.14 | 0.91/1.04 | 0.60/0.67 |
| EURJPY | 0.85/0.94 | 1.16/1.08 | 0.99/1.00 | 0.92/0.93 |
| GBPJPY | 0.82/0.89 | 0.98/0.93 | 0.98/1.04 | 0.91/0.98 |
| EURGBP | 0.72/0.79 | 1.09/1.01 | 0.86/0.94 | 0.48/0.48 |
| AUDJPY | 0.81/0.93 | 1.01/1.05 | 0.98/1.01 | 0.89/0.91 |

## 7. Portfolio view (reporting only; 12 symbols, TAH account rules)

Account cap: <=5 new trades/calendar week + <=3 open positions,
first-come by fill time. PF_R x1 / MC DD P95 (200 reorderings):

| cfg | harness | uncapped n, tr/wk, PF_R, DD | capped n, tr/wk, PF_R, DD, posY |
|-----|---------|----------------------------|---------------------------------|
| F0_J | H0 | 6972, 13.3/wk, 0.80, 768R | 2606, 4.99/wk, 0.86, 214R, 18% |
| F0_J | H1 | 6831, 13.1/wk, 0.89, 421R | 2606, 4.99/wk, 0.90, 167R, 27% |
| F2_NH_b | H0 | 15736, 30.1/wk, 1.05, 358R | 2619, 5.01/wk, **1.17**, 59R, 73% |
| F2_NH_b | H1 | 14326, 27.4/wk, 1.06, 167R | 2619, 5.01/wk, **1.11**, 81R, 64% |
| F5_S2 | H0 | 2570, 4.9/wk, 0.97, 168R | 2090, 4.00/wk, 1.03, 107R, 64% |
| F5_S2 | H1 | 2540, 4.9/wk, 1.04, 113R | 2075, 3.97/wk, 1.07, 92R, 64% |
| F5_S3 | H0 | 641, 1.2/wk, 0.98, 71R | 639, 1.23/wk, 0.98, 68R, 45% |
| F5_S3 | H1 | 639, 1.2/wk, 1.03, 58R | 637, 1.22/wk, 1.04, 65R, 55% |

Notable: the account cap IMPROVES F2_NH_b (1.05->1.17 H0): the first
~5 fills per week carry most of the edge; later fills dilute it.
5.0 trades/week per account, positive years 64-73%, DD P95 59-81R
(still over a 30R budget).

## 8. Honest reading

- **Replicated**: the F2_NH_b *mechanism* (Nhat Hoai continuation with
  big-swing stops) - 9/10 symbols PF_R>1 on H1, pooled 1.05-1.06, and
  beating the pooled null at the 100th percentile on BOTH harnesses.
  That is real Sonic-style behaviour, not data artifact. But its size
  is ~1.06, not the ~1.19 seen on EURUSD - the EUR result was the top
  of the cross-symbol distribution.
- **Did NOT replicate**: the confluence dose-response (R1 dead on both
  harnesses - basket rho ~0 vs EUR/XAU ~0.08-0.10), F5_S2/F5_S3
  (XAUUSD's 1.38-1.64 was symbol-specific - mostly gold microstructure,
  not the element score), and F0_J economics (<1 pooled everywhere).
- **Implication**: the 2B essence signal was EUR/XAU luck after 100
  cells, exactly the failure mode best-of-N predicted. What survives
  replication is the plain F2_NH_b continuation setup at modest PF.
- **Account reality**: even pooled across 12 symbols, F2_NH_b capped
  at 5/wk gives PF_R 1.11-1.17 with DD P95 59-81R - better than any
  single-symbol run but still short of the round-2 promotion bar
  (1.20) and the drawdown budget.

## 9. What this says for next steps

1. F2_NH_b is the only surviving family; the basket view suggests its
   edge is in the FIRST few fills per week (cap improved PF 1.05->1.17).
   A preregistered "top-of-week quality filter" (e.g. take only setups
   with the widest clean risk or strongest prior momentum when >5
   signals queue) is a legitimate round-3 question - the mechanism is
   measured, not tuned.
2. Exit redesign stays the second lever (median loser runs +0.6R) now
   with 12-symbol evidence behind it.
3. The confluence/PV/W4 element line should be retired as stated - on
   never-fitted symbols it carried no information.
