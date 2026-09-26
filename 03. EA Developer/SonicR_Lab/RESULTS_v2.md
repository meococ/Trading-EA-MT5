# RESULTS_v2 - Round 2 corrected (errata E1-E3) + Round 2B

Written 2026-09-23. Builds on RESULTS.md (as-registered record, kept
untouched). Two harness versions are reported for every config:
- H0 = E1b (roll spread stress) + E2 (executability floor) + E3 (PF_R),
  suspect bars tradable.
- H1 = H0 + E1 (suspect M1 bars cannot trigger or price anything;
  Lead addendum A1, 19:17Z).

PREREG_V2.md frozen 19:14:04Z sha256=3e92207100399e7662fa5691c174c163f5c73b34ea8a636839212c0e6feb9bd7
(before any 2B P/L), amended 19:33Z with the A1 dual-harness selection
rule -> new file sha256=0226143d1e763a1955531c58d279fcfa51f6a721787d3c2185039a527735c7fd.
LEAD_NOTE_4.md sha256=b15654a19e0b9a9ff3171bbe35b11fad11a65adca45bda3b92457d2c0f9f8906 (verified).

## 1. E1 diagnostic (D1 rerun - the corrected measurement)

The 19:06Z median-range test (suspect/clean M1 range ratio inside the
roll window: EUR 0.86, XAU 1.19) was the WRONG statistic - a fabricated
burst is a few extreme bars inside ~15 roll minutes/day, hidden by a
median. The corrected diagnostic (DATA.md, `runs/diag_roll_v2.py`):

- Exits per 1000 trade-minutes inside roll window vs outside: ~6x-208x
  more concentrated across ALL 25 configs (e.g. EURUSD F0_J 253.5 vs
  2.14; EURUSD F2_NH_b 37.7 vs 0.53; XAUUSD F5_S3 32.3 vs 0.54).
- Per-day extremes: max M1 range inside roll window vs adjacent quiet
  windows -> median ratio 30.9 (EUR) / 37.9 (XAU), P90 63/86, P99
  116/176; max |open-prev_close| median ratio 71/69.
- Jump-and-revert: >0.5 x ATR14 away from pre-roll close inside the
  window, back within 0.2 x ATR14 30 min later: 25.7% of EURUSD days,
  18.1% of XAUUSD days.
- Conclusion: roll-window M1 bars are fabricated price paths. E1
  applied; H0/H1 both reported.

## 2. Errata applied to every config (not only winners)

- E1 (H1 only): suspect bars skipped for pending fills and SL/TP hits;
  first clean bar after a suspect run resolves gaps per the Lead's
  rules; Friday flatten on suspect -> first clean open.
- E1b: roll spread stress on the ask side of every fill/exit inside
  EUR 23:55-00:15 / XAU 00:55-01:20 server (+2p / +20p).
- E2: orders with (pending_px - SL)*dir < max(3 x cost, 0.15 x ATR14)
  skipped; removal counts in census (e.g. XAUUSD F2_NH_a 759/4142,
  F3_LUCY_a 6866/10964, F3_LUCY_b 5507/8622, F4_BAI14 665/9254).
- E3: PF_R primary; pip PF co-reported; control percentile on PF_R.
- sl_big_swing root fix (E0, previous section in RESULTS.md).
- pending_px exported on every trade row (distinct from entry fill).

## 3. Round-2 DESIGN - D1 as-registered vs corrected (H0 / H1)

| cfg | sym | D1 PF(pips) | n H0 | PF pips H0 | PF_R H0 | PF_R x1.5 H0 | n H1 | PF pips H1 | PF_R H1 | tr/wk H0 | E2 rej |
|-----|-----|------------|------|-----------|---------|--------------|------|-----------|---------|----------|--------|
| F0_J | EUR | 0.90 | 598 | 0.873 | 0.892 | 0.864 | 585 | 0.927 | 0.939 | 1.14 | 0 |
| F1_W2whq | EUR | 0.92 | 132 | 0.892 | 0.903 | 0.878 | 132 | 0.993 | 0.996 | 0.25 | 0 |
| F1_W2swing | EUR | 1.08 | 99 | 1.042 | 0.970 | 0.941 | 99 | 1.075 | 1.005 | 0.19 | 0 |
| F1_W3 | EUR | 1.06 | 270 | 1.031 | 1.079 | 1.045 | 267 | 1.147 | 1.194 | 0.52 | 0 |
| F1_W4a | EUR | 1.20 | 18 | 1.167 | 0.991 | 0.962 | 18 | 1.205 | 1.026 | 0.03 | 0 |
| F1_R1b | EUR | 0.94 | 593 | 0.912 | 0.899 | 0.870 | 580 | 0.938 | 0.934 | 1.13 | 3 |
| F1_R2a | EUR | 0.95 | 442 | 0.930 | 0.999 | 0.975 | 433 | 0.968 | 1.057 | 0.85 | 0 |
| F1_R2b | EUR | 0.79 | 199 | 0.760 | 0.822 | 0.793 | 198 | 0.882 | 0.933 | 0.38 | 0 |
| F1_PV | EUR | 0.97 | 13 | 0.944 | 0.736 | 0.716 | 13 | 0.968 | 0.765 | 0.03 | 0 |
| F2_NH_a | EUR | 1.07 | 1862 | 1.038 | 1.038 | 0.998 | 1750 | 1.013 | 1.032 | 3.56 | 0 |
| F2_NH_b | EUR | 1.147 | 1291 | 1.113 | 1.172 | 1.142 | 1173 | 1.136 | 1.192 | 2.47 | 13 |
| F3_LUCY_a | EUR | 0.86 | 4204 | 0.850 | 0.842 | 0.767 | 4198 | 0.878 | 0.859 | 8.04 | 18 |
| F3_LUCY_b | EUR | 0.75 | 2757 | 0.730 | 0.717 | 0.668 | 2706 | 0.772 | 0.760 | 5.27 | 17 |
| F4_BAI14 | EUR | 0.97 | 2895 | 0.949 | 0.922 | 0.883 | 2731 | 0.999 | 0.964 | 5.54 | 0 |
| F0_J | XAU | 0.79 | 646 | 0.702 | 0.701 | 0.609 | 639 | 0.844 | 0.835 | 1.24 | 2 |
| F1_W2whq | XAU | 0.88 | 221 | 0.796 | 0.812 | 0.717 | 220 | 0.901 | 0.937 | 0.42 | 1 |
| F1_W2swing | XAU | 0.57 | 64 | 0.479 | 0.525 | 0.458 | 64 | 0.610 | 0.702 | 0.12 | 0 |
| F1_W3 | XAU | 0.70 | 309 | 0.611 | 0.582 | 0.506 | 308 | 0.718 | 0.694 | 0.59 | 0 |
| F1_W4a | XAU | 1.49 | 22 | 1.426 | 1.369 | 1.182 | 22 | 1.423 | 1.344 | 0.04 | 0 |
| F1_R1b | XAU | 0.87 | 628 | 0.755 | 0.736 | 0.644 | 623 | 0.938 | 0.898 | 1.20 | 3 |
| F1_R2a | XAU | 0.95 | 485 | 0.827 | 0.827 | 0.764 | 471 | 0.989 | 1.010 | 0.93 | 2 |
| F1_R2b | XAU | 0.71 | 102 | 0.635 | 0.685 | 0.582 | 102 | 0.825 | 0.849 | 0.20 | 1 |
| F1_PV | XAU | 0.61 | 17 | 0.433 | 0.389 | 0.330 | 17 | 0.611 | 0.587 | 0.03 | 0 |
| F2_NH_a | XAU | 0.81 | 1798 | 0.725 | 0.681 | 0.615 | 1694 | 0.789 | 0.749 | 3.44 | 759 |
| F2_NH_b | XAU | 1.053 | 1434 | 0.902 | 0.926 | 0.861 | 1274 | 0.982 | 0.974 | 2.74 | 42 |
| F3_LUCY_a | XAU | 0.64 | 2273 | 0.694 | 0.704 | 0.582 | 2264 | 0.732 | 0.737 | 4.35 | 6866 |
| F3_LUCY_b | XAU | 0.60 | 1583 | 0.582 | 0.573 | 0.500 | 1563 | 0.663 | 0.661 | 3.03 | 5507 |
| F4_BAI14 | XAU | 0.82 | 2970 | 0.750 | 0.723 | 0.635 | 2831 | 0.857 | 0.821 | 5.68 | 665 |

(F1_W4b, F1_FULL, F1_FULL_RE: zero signals - kept, flagged.)

Daily-flat-23:50 secondary column (not selection): material on XAU
F2_NH_b (PF_R 0.926 -> 1.038 flat on H0; 0.974 -> 1.043 on H1) - the
rollover artifact is what the flat removes; becomes a preregistered
round-3 variant. EUR F2_NH_b flat is neutral (1.172 -> 1.172).

## 4. Round-2 controls (dual harness, PF_R percentile, tiered seeds)

SEE out/controls_summary_h.csv - table in section 6 next to selection.

## 5. Round 2B

### 5a. Census (outcome-blind; Q computed here, before any 2B P/L)

Q (W4d) = median dir*angle20 over F0_J DESIGN signals:
EURUSD -0.006340, XAUUSD -0.005364 (runs/q_w4d.json). Negative: the
median J signal fires while the 20-bar Dragon slopes against it.

| cfg | EUR n (sig/wk) | XAU n (sig/wk) | E2 removed EUR/XAU |
|-----|----------------|----------------|---------------------|
| F1_W4c | 467 (0.89) | 459 (0.88) | 0 / 1 |
| F1_W4d | 538 (1.03) | 521 (1.00) | 0 / 1 |
| F1_PV2a | 261 (0.50) | 348 (0.67) | 0 / 0 |
| F1_PV2b | 317 (0.61) | 435 (0.83) | 0 / 1 |
| F5_S2 | 337 (0.64) | 437 (0.84) | 0 / 1 |
| F5_S3 | 74 (0.14) | 126 (0.24) | 0 / 0 |
| F5_S2_EXT | 371 (0.71) | 491 (0.94) | 0 / 2 |
| F5_S3_EXT | 90 (0.17) | 147 (0.28) | 0 / 0 |

### 5b. 2B DESIGN (H0 / H1)

| cfg | sym | n H0 | PF_R H0 | PF pips H0 | n H1 | PF_R H1 | PF pips H1 |
|-----|-----|------|---------|------------|------|---------|------------|
| F1_W4c | EUR | 289 | 0.977 | 0.927 | 287 | 1.074 | 1.024 |
| F1_W4d | EUR | 328 | 0.917 | 0.874 | 325 | 0.997 | 0.951 |
| F1_PV2a | EUR | 149 | 0.905 | 0.949 | 149 | 0.966 | 1.007 |
| F1_PV2b | EUR | 201 | 0.719 | 0.746 | 199 | 0.758 | 0.787 |
| F5_S2 | EUR | 209 | 0.962 | 0.914 | 206 | 0.979 | 0.919 |
| F5_S3 | EUR | 47 | 1.170 | 1.221 | 47 | 1.215 | 1.264 |
| F5_S2_EXT | EUR | 229 | 0.981 | 0.896 | 226 | 1.015 | 0.912 |
| F5_S3_EXT | EUR | 59 | 1.073 | 1.015 | 59 | 1.115 | 1.051 |
| F1_W4c | XAU | 296 | 0.835 | 0.823 | 294 | 0.981 | 0.992 |
| F1_W4d | XAU | 326 | 0.807 | 0.818 | 322 | 0.940 | 0.986 |
| F1_PV2a | XAU | 241 | 0.937 | 0.946 | 240 | 1.076 | 1.127 |
| F1_PV2b | XAU | 287 | 0.722 | 0.767 | 286 | 0.860 | 0.915 |
| F5_S2 | XAU | 270 | 1.149 | 1.106 | 269 | 1.375 | 1.304 |
| F5_S3 | XAU | 76 | 1.404 | 1.294 | 76 | 1.642 | 1.488 |
| F5_S2_EXT | XAU | 297 | 1.108 | 1.072 | 294 | 1.315 | 1.258 |
| F5_S3_EXT | XAU | 87 | 1.364 | 1.252 | 87 | 1.586 | 1.435 |

E1-on raises the 2B numbers too (same roll-window exits voided). But the
S>=3 variants run 0.14-0.28 trades/wk - below the 1/wk gate - and S>=2
runs 0.5-0.9/wk.

### 5c. Essence test (confluence S on F0_J trades, J exits)

H0 Spearman (S vs trade R): EUR rho=0.084 p=0.020; XAU rho=0.104
p=0.004; POOLED rho=0.077 p=0.003.
H1 Spearman: EUR rho=0.091 p=0.014; XAU rho=0.092 p=0.010; POOLED
rho=0.068 p=0.009.

S buckets, expectancy R (H0 / H1):

| S | EUR exp_r H0->H1 | XAU exp_r H0->H1 |
|---|------------------|------------------|
| 0 | -0.310 / -0.321 | -0.304 / -0.138 |
| 1 | -0.012 / +0.020 | -0.277 / -0.192 |
| 2 | -0.111 / -0.077 | -0.014 / +0.044 |
| 3 | +0.255 / +0.284 | -0.146 / -0.092 |
| 4 | +1.305 / +1.335 (n=3) | -0.107 / -0.064 (n=12) |

Single elements (H1, with vs without, exp_r):
- w2any: EUR +0.039 vs -0.063; XAU -0.056 vs -0.092.
- w3: EUR +0.082 vs -0.114; XAU -0.121 vs -0.042 (mixed).
- w4c: EUR +0.045 vs -0.092; XAU -0.023 vs -0.119.
- pv2a: EUR -0.027 vs -0.032; XAU +0.033 vs -0.137 (helps XAU).
- pv2b: EUR -0.134 vs +0.014; XAU -0.080 vs -0.077 (hurts).

Verdict: weak positive dose-response (Spearman significant on both
symbols/harnesses) driven by the EUR S=3 bucket; XAU does not confirm
monotone response (S3/S4 negative). Confluence adds SOME information
but not enough to clear the economics gates at viable cadence.

## 6. Selection (D5 on BOTH harnesses + both metrics) - NONE ADVANCE

Rule (A1): on BOTH H0 and H1 - PF_R x1 >= 1.20 AND pip PF x1 >= 1.20
AND PF_R x1.5 >= 1.05 AND pip PF x1.5 >= 1.05 AND >= 1 trade/wk AND
positive P/L in >= 60% of years AND control percentile >= 95.

| closest cells | PF_R H0/H1 | pip PF H0/H1 | pct H0/H1 | tr/wk | why it fails |
|---------------|-----------|--------------|-----------|-------|--------------|
| XAUUSD F5_S3 | 1.40 / 1.64 | 1.29 / 1.49 | 99 / 99 | 0.15 | cadence 0.15 << 1; pos-years 4/10 |
| XAUUSD F5_S3_EXT | 1.36 / 1.59 | 1.25 / 1.44 | 98 / 97 | 0.17 | cadence |
| XAUUSD F5_S2 | 1.15 / 1.38 | 1.11 / 1.30 | 100 / 100 | 0.51 | cadence + PF<1.20 on H0 |
| EURUSD F2_NH_b | 1.17 / 1.19 | 1.11 / 1.14 | 100 / 100 | 2.5 | PF < 1.20; pos-years 6-7/11 |
| EURUSD F1_W3 | 1.08 / 1.19 | 1.03 / 1.15 | 98 / 98 | 0.52 | PF < 1.20 + cadence |
| XAUUSD F1_PV2a | 0.94 / 1.08 | 0.95 / 1.13 | 99 / 98 | 0.46 | PF + cadence |

runs/selection.json = {"selected": []} frozen 19:47Z. VALIDATION not
run - nothing to read. HOLDOUT sealed throughout.

Read of the evidence: XAUUSD F5_S3 is real-looking (PF_R 1.4-1.6 at the
97-99th percentile on BOTH harnesses, deflated z=2.6) but it is ~7
trades/year over 11 years - inside the regime where one trade per year
decides the verdict (2010 and 2016 contribute 0). It is a hypothesis
for a bigger sample, not a promotion.

## 7. VALIDATION

NOT READ - no config passed selection. HOLDOUT sealed (loader-level
guard; no allow_holdout=True anywhere in the lane).

## 8. Tie zones (LEAD_NOTE_3 addendum)

Mixed high+low zone formations (sum(dir)=0, labelled support):
EURUSD 7 of 5,769 distinct zones; XAUUSD 26 of 5,830. Rare (<0.5%) -
noted for the round-3 design question (whether a mixed cluster should
be a flip zone), no action this round.

## 9. Multiple testing / deflated Sharpe / MC DD

Best-of-N null (10,000 bootstrap draws of max PF_R across cells):
- all cells with trades (88 of 100): p50=2.09, p95=2.89, max=3.27 -
  driven by low-count configs; any single PF_R under ~2.9 is inside
  the luck envelope at this trial count.
- >=1 trade/wk subset (28 cells): p50=1.06, p95=1.15, max=1.15 -
  for the viable-cadence population, a PF_R of ~1.15 is already the
  best-of-N expectation. XAUUSD F5_S2 H1 (1.375) exceeds it but fails
  cadence; nothing in the viable subset does.

Deflated Sharpe (z vs own null, deflated by sqrt(88)):
XAUUSD F5_S2 H1 z=3.37 defl 0.36; EURUSD F2_NH_b H0 z=3.53 defl 0.38;
XAUUSD F5_S3 H1 z=2.57 defl 0.27. Positive but small - consistent with
"real but sub-gate".

MC DD P95 (200 bootstrap reorderings, r_x1):
- XAUUSD F5_S3: H1 16.1R / H0 18.7R (within 30R budget)
- XAUUSD F5_S2: H1 27.5R / H0 35.5R
- EURUSD F1_W3: H1 20.5R / H0 23.5R
- EURUSD F2_NH_b: H1 54.5R / H0 61.4R (over budget)

## 10. Honest verdict per family

- **F0_J / F1 ladder**: breakeven-to-negative on both harnesses; the
  element ladder stays the evidence that elements carry information
  (W3 +0.19 PF_R on EUR H1 vs base) but not at a passing PF.
- **F2 Nhat Hoai**: control-beating on both symbols (pct 100 EUR, 90-100
  XAU) and PF_R ~1.17-1.19 EUR / 0.93-0.97 XAU. The rollover artifact
  was net-negative for it (H1 improves EUR to 1.19); still below the
  1.20 gate and pos-years ~25%.
- **F3/F4**: dead on costs; E2 removed the worst micro-stops and the
  families remain <1 on both harnesses.
- **2B W4/PV singles**: no single element clears economics (all <1.10).
- **F5 confluence**: the interesting family - monotone-ish dose-response
  on EUR essence (S0 -0.32 -> S3 +0.28, Spearman p=0.014-0.020) and the
  only cells above PF_R 1.3, but cadence 0.15-0.5/wk means the result
  is carried by tens of trades.

## 11. Next approaches (2-3, cheapest first - needs NEW prereg)

1. **S>=2 confluence on a wider base (the dose-response path)**: S is
   the only measured monotone element score. A round-3 variant that
   relaxes ONE gate (e.g. drop pv2a from S or score>=2 with extended
   session + R2a target variants) to reach >=1/wk, then re-test. The
   evidence says confluence is where information lives; the current
   S>=3 is simply too rare to evaluate.
2. **F2_NH_b exits (still the cheapest)**: unchanged from round 2 -
   the family beats controls on both harnesses and symbols; median
   loser runs +0.6R before dying. A break-even/time-stop amendment on
   the SAME signal stream is one prereg line.
3. **Daily flat 23:50 as a preregistered variant** (the secondary
   column paid for itself as evidence): XAUUSD F2_NH_b PF_R 0.97 ->
   1.04 with the flat on H1; F5_S3_EXT XAU 1.59 -> 1.67. If any family is
   re-run, register flat2350 from the start - it directly targets the
   measured rollover artifact.

NOT recommended: more PVSRA gating (pv2b hurt both symbols), more W4
angle tightening (cadence already fatal), or reading VALIDATION on
hope.
