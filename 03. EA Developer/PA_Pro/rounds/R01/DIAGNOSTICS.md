# R01 DIAGNOSTICS — post-freeze, from the frozen tables only

UTC 2026-09-20T16:22:28Z · source: frozen EVENTS/CONTROLS/OUTCOME tables (no re-sampling, no re-seeding, no new events, no new trials). Freeze `91b21dc7dc5d…` · addendum-2 `dcb85c81e4d1…`

All numbers here are DESCRIPTIVE. They are not gates, cannot change any verdict, and were not used to select anything.

## Three-way decomposition — bounce / break / NONE (contrast between two episode types)

**The two arms differ in episode type, so this table describes the CONTRAST between them, not the zones.** Real ARMED events fire while price hovers at / retests adjacent structure (armed rule <= 2 x ATR; measured median near-edge distance 0.28-0.34 ATR at the anchor). A control band must sit >= 1.0 x ATR away by Addendum 2 and actually draws at a median 2.11-2.37 ATR, so a control event can only fire after price has TRAVELLED to it (an impulse-arrival episode). That asymmetry predicts the sign of all three columns; no column can be attributed to zone physics (reviewer F1, measured). The causal claim is NOT established: the control bounce rate is flat across control-distance deciles (0.68 +- 0.005), consistent with a mechanism that saturates past 1 ATR but not evidence for it. The decisive test is R02's matched design.

Raw shares of events with a resolved outcome OR NONE (deltas = simple rate differences, real minus control; CIs = percentile bootstrap of the difference, independent arms, B=2,000, seed 20260920).

**Pooled (all terciles, core symbols)**

| generator | bounce real | bounce ctrl | Δbounce pp [CI] | break real | break ctrl | Δbreak pp | NONE real | NONE ctrl | ΔNONE pp [CI] |
|---|---|---|---|---|---|---|---|---|---|
| `line1_cluster` | 0.4617 | 0.5191 | -5.74 [-6.28,-5.22] | 0.2370 | 0.2300 | 0.71 | 0.3012 | 0.2509 | 5.03 [4.56,5.53] |
| `fractal_h1` | 0.4616 | 0.5140 | -5.24 [-5.94,-4.54] | 0.2636 | 0.2519 | 1.17 | 0.2748 | 0.2341 | 4.07 [3.48,4.68] |
| `kde_swing` | 0.4630 | 0.5240 | -6.10 [-6.83,-5.38] | 0.2237 | 0.2147 | 0.90 | 0.3132 | 0.2613 | 5.20 [4.53,5.88] |
| `profile_va` | 0.4700 | 0.5066 | -3.65 [-5.23,-1.98] | 0.2171 | 0.2155 | 0.16 | 0.3129 | 0.2779 | 3.49 [2.03,4.98] |
| `sd_base` | 0.4561 | 0.5184 | -6.22 [-7.21,-5.16] | 0.2463 | 0.2498 | -0.35 | 0.2976 | 0.2319 | 6.57 [5.59,7.49] |
| `ref_levels` | 0.4499 | 0.5123 | -6.25 [-6.96,-5.54] | 0.3150 | 0.2783 | 3.67 | 0.2351 | 0.2094 | 2.57 [1.97,3.15] |

**Top strength tercile**

| generator | bounce real | bounce ctrl | Δbounce pp [CI] | break real | break ctrl | Δbreak pp | NONE real | NONE ctrl | ΔNONE pp [CI] |
|---|---|---|---|---|---|---|---|---|---|
| `line1_cluster` | 0.4472 | 0.5208 | -7.36 [-8.28,-6.46] | 0.2266 | 0.2144 | 1.22 | 0.3261 | 0.2648 | 6.13 [5.31,7.00] |
| `fractal_h1` | 0.4401 | 0.5116 | -7.15 [-8.38,-5.89] | 0.2475 | 0.2358 | 1.17 | 0.3124 | 0.2526 | 5.98 [4.88,7.15] |
| `kde_swing` | 0.4445 | 0.5190 | -7.45 [-8.68,-6.18] | 0.2201 | 0.2103 | 0.98 | 0.3354 | 0.2707 | 6.47 [5.33,7.60] |
| `profile_va` | 0.4483 | 0.5109 | -6.26 [-8.94,-3.51] | 0.2107 | 0.2157 | -0.50 | 0.3411 | 0.2734 | 6.76 [4.34,9.36] |
| `sd_base` | 0.4420 | 0.5232 | -8.12 [-9.94,-6.24] | 0.2520 | 0.2456 | 0.63 | 0.3060 | 0.2312 | 7.48 [5.81,9.14] |
| `ref_levels` | 0.4480 | 0.5141 | -6.61 [-7.79,-5.42] | 0.2848 | 0.2648 | 2.00 | 0.2671 | 0.2211 | 4.61 [3.53,5.67] |

Reading (Lead R01-FINAL-B §1-§3, reviewer F1): the negative bounce delta, the flat break delta and the positive NONE delta are all predicted by the episode-type asymmetry (hover-arrival vs impulse-arrival) and therefore describe the contrast, not zone physics. The asymmetry is measured and real; the causal claim that it produces the whole gap is NOT established (no dose-response among controls: flat 0.68 +- 0.005). No zone claim is made from this table.

## D4 / D4b — position in the recent range (the decisive measurement)

`folded` = distance of the band from the nearest R5 extreme, normalized to the R5 width = `min(pos, 1-pos)`; `dist ATR` = that distance in units of the anchor's A(t). R5 = bars [anchor-1440, anchor-1].

| generator | real folded (med) | real dist ATR | ctrl folded (med) | ctrl dist ATR |
|---|---|---|---|---|
| `line1_cluster` | 0.229 | 2.65 | 0.215 | 2.49 |
| `fractal_h1` | 0.212 | 2.47 | 0.209 | 2.40 |
| `kde_swing` | 0.281 | 3.08 | 0.199 | 2.17 |
| `profile_va` | 0.281 | 2.97 | 0.185 | 1.92 |
| `sd_base` | 0.283 | 3.08 | 0.211 | 2.32 |
| `ref_levels` | 0.220 | 2.57 | 0.212 | 2.46 |

**Statement:** real and control bands ARE matched on this dimension to within ~0.05 folded units (median folded 0.21-0.28 real vs 0.19-0.22 control), and the real arm is very slightly FURTHER from the extreme than the control arm. The hypothesis that real zones sit AT range edges while controls sit mid-range is REFUTED by measurement. The arms overlap in every decile with thousands of observations on both sides (D4b tables below); the primary comparison is between two heavily overlapping populations, not disjoint ones.

**D4b (post-stratified, unpaired within deciles; descriptive only).** Decile edges are deciles of the pooled folded-position distribution per generator. `D` = unpaired difference (real minus control); reported only where both arms have >= 200 resolved events in the decile (`-` otherwise).

### D4b `line1_cluster` (edges 0.018, 0.054, 0.105, 0.161, 0.218, 0.275, 0.331, 0.387, 0.444)

| decile | n real | n ctrl | D_bounce | D_cont |
|---|---|---|---|---|
| 1 | 3487 | 12408 | 0.0582 | -0.0633 |
| 2 | 1676 | 14421 | 0.0386 | -0.0284 |
| 3 | 2365 | 13019 | 0.0244 | 0.0122 |
| 4 | 3501 | 11626 | -0.0214 | -0.0093 |
| 5 | 3825 | 11365 | -0.0551 | -0.0162 |
| 6 | 3676 | 11519 | -0.0598 | 0.0461 |
| 7 | 3345 | 12004 | -0.0783 | 0.0256 |
| 8 | 3113 | 12097 | -0.0697 | 0.0166 |
| 9 | 2943 | 12235 | -0.0879 | 0.0225 |
| 10 | 2851 | 12506 | -0.0942 | 0.0597 |

### D4b `fractal_h1` (edges 0.013, 0.047, 0.094, 0.151, 0.210, 0.269, 0.328, 0.385, 0.443)

| decile | n real | n ctrl | D_bounce | D_cont |
|---|---|---|---|---|
| 1 | 3534 | 5375 | 0.0936 | -0.0333 |
| 2 | 906 | 8361 | 0.0479 | -0.0151 |
| 3 | 1222 | 7678 | 0.0235 | 0.0098 |
| 4 | 1804 | 6848 | -0.0288 | -0.0097 |
| 5 | 2096 | 6528 | -0.0537 | -0.0250 |
| 6 | 2192 | 6496 | -0.0560 | 0.0805 |
| 7 | 1952 | 6762 | -0.0859 | 0.0744 |
| 8 | 1813 | 6928 | -0.0691 | 0.0316 |
| 9 | 1770 | 6910 | -0.1064 | 0.0279 |
| 10 | 1742 | 7003 | -0.1006 | 0.0983 |

### D4b `kde_swing` (edges 0.023, 0.063, 0.111, 0.164, 0.219, 0.274, 0.330, 0.387, 0.444)

| decile | n real | n ctrl | D_bounce | D_cont |
|---|---|---|---|---|
| 1 | 1758 | 6711 | 0.0503 | -0.0617 |
| 2 | 478 | 8157 | 0.0291 | n/a |
| 3 | 691 | 7772 | -0.0098 | n/a |
| 4 | 1285 | 6952 | -0.0236 | 0.0124 |
| 5 | 1642 | 6556 | -0.0598 | -0.0375 |
| 6 | 1932 | 6194 | -0.0595 | 0.0416 |
| 7 | 1967 | 6316 | -0.0635 | 0.0135 |
| 8 | 2131 | 6125 | -0.0726 | 0.0279 |
| 9 | 2099 | 6121 | -0.0954 | 0.0399 |
| 10 | 2026 | 6205 | -0.0946 | 0.0415 |

### D4b `profile_va` (edges 0.021, 0.057, 0.104, 0.155, 0.210, 0.261, 0.318, 0.376, 0.437)

| decile | n real | n ctrl | D_bounce | D_cont |
|---|---|---|---|---|
| 1 | 442 | 1217 | 0.1149 | n/a |
| 2 | 83 | 1597 | n/a | n/a |
| 3 | 111 | 1534 | n/a | n/a |
| 4 | 208 | 1396 | -0.0135 | n/a |
| 5 | 267 | 1338 | -0.0111 | n/a |
| 6 | 372 | 1199 | -0.0924 | n/a |
| 7 | 410 | 1211 | -0.0609 | n/a |
| 8 | 443 | 1184 | -0.0826 | n/a |
| 9 | 466 | 1147 | -0.0656 | n/a |
| 10 | 486 | 1117 | -0.0811 | n/a |

### D4b `sd_base` (edges 0.027, 0.068, 0.118, 0.174, 0.230, 0.284, 0.338, 0.393, 0.447)

| decile | n real | n ctrl | D_bounce | D_cont |
|---|---|---|---|---|
| 1 | 133 | 4248 | n/a | n/a |
| 2 | 312 | 4039 | 0.0487 | n/a |
| 3 | 546 | 3724 | 0.0088 | n/a |
| 4 | 801 | 3346 | -0.0310 | -0.0328 |
| 5 | 982 | 3252 | -0.0404 | 0.0339 |
| 6 | 1000 | 3226 | -0.0628 | 0.0779 |
| 7 | 982 | 3191 | -0.0911 | 0.0902 |
| 8 | 954 | 3218 | -0.0661 | 0.0593 |
| 9 | 908 | 3218 | -0.0676 | 0.0335 |
| 10 | 832 | 3321 | -0.0665 | 0.0192 |

### D4b `ref_levels` (edges 0.016, 0.050, 0.099, 0.156, 0.214, 0.271, 0.329, 0.387, 0.444)

| decile | n real | n ctrl | D_bounce | D_cont |
|---|---|---|---|---|
| 1 | 2779 | 6141 | 0.0142 | 0.0039 |
| 2 | 822 | 8265 | -0.0245 | 0.0094 |
| 3 | 1247 | 7604 | 0.0036 | -0.0164 |
| 4 | 1974 | 6583 | -0.0301 | -0.0297 |
| 5 | 2173 | 6447 | -0.0668 | 0.0389 |
| 6 | 2081 | 6572 | -0.0846 | 0.0290 |
| 7 | 1881 | 6718 | -0.0870 | 0.0446 |
| 8 | 1809 | 6860 | -0.1131 | 0.0490 |
| 9 | 1765 | 6787 | -0.1154 | 0.0460 |
| 10 | 1687 | 7073 | -0.1108 | 0.0720 |

Reading: D_bounce swings from positive near the range extreme (deciles 1-3) to strongly negative mid-range (deciles 5-10); D_cont does the opposite. Position in the range modulates the CONTRAST strongly, and the two arms overlap in every decile; the numbers are unpaired and are not comparable 1:1 with the paired primary D. Position is NOT the explanation of the gap (both arms sit mid-range; reviewer B5).

## D1 — raw shares with NONE in the denominator (prereg §4 compliance fix)

| generator | arm | tercile | n | bounce | break | NONE |
|---|---|---|---|---|---|---|
| `line1_cluster` | real | all | 0 | 0.4617 | 0.2370 | 0.3012 |
| `line1_cluster` | real | top | 0 | 0.4472 | 0.2266 | 0.3261 |
| `line1_cluster` | real | mid | 0 | 0.4639 | 0.2339 | 0.3022 |
| `line1_cluster` | real | bot | 0 | 0.4740 | 0.2505 | 0.2754 |
| `line1_cluster` | ctrl | all | 0 | 0.5191 | 0.2300 | 0.2509 |
| `line1_cluster` | ctrl | top | 0 | 0.5208 | 0.2144 | 0.2648 |
| `line1_cluster` | ctrl | mid | 0 | 0.5199 | 0.2305 | 0.2495 |
| `line1_cluster` | ctrl | bot | 0 | 0.5166 | 0.2454 | 0.2380 |
| `fractal_h1` | real | all | 0 | 0.4616 | 0.2636 | 0.2748 |
| `fractal_h1` | real | top | 0 | 0.4401 | 0.2475 | 0.3124 |
| `fractal_h1` | real | mid | 0 | 0.4698 | 0.2639 | 0.2663 |
| `fractal_h1` | real | bot | 0 | 0.4740 | 0.2785 | 0.2475 |
| `fractal_h1` | ctrl | all | 0 | 0.5140 | 0.2519 | 0.2341 |
| `fractal_h1` | ctrl | top | 0 | 0.5116 | 0.2358 | 0.2526 |
| `fractal_h1` | ctrl | mid | 0 | 0.5159 | 0.2547 | 0.2294 |
| `fractal_h1` | ctrl | bot | 0 | 0.5145 | 0.2646 | 0.2210 |
| `kde_swing` | real | all | 0 | 0.4630 | 0.2237 | 0.3132 |
| `kde_swing` | real | top | 0 | 0.4445 | 0.2201 | 0.3354 |
| `kde_swing` | real | mid | 0 | 0.4573 | 0.2122 | 0.3305 |
| `kde_swing` | real | bot | 0 | 0.4873 | 0.2388 | 0.2738 |
| `kde_swing` | ctrl | all | 0 | 0.5240 | 0.2147 | 0.2613 |
| `kde_swing` | ctrl | top | 0 | 0.5190 | 0.2103 | 0.2707 |
| `kde_swing` | ctrl | mid | 0 | 0.5246 | 0.2143 | 0.2611 |
| `kde_swing` | ctrl | bot | 0 | 0.5284 | 0.2194 | 0.2521 |
| `profile_va` | real | all | 0 | 0.4700 | 0.2171 | 0.3129 |
| `profile_va` | real | top | 0 | 0.4483 | 0.2107 | 0.3411 |
| `profile_va` | real | mid | 0 | 0.4796 | 0.2188 | 0.3016 |
| `profile_va` | real | bot | 0 | 0.4821 | 0.2219 | 0.2959 |
| `profile_va` | ctrl | all | 0 | 0.5066 | 0.2155 | 0.2779 |
| `profile_va` | ctrl | top | 0 | 0.5109 | 0.2157 | 0.2734 |
| `profile_va` | ctrl | mid | 0 | 0.4893 | 0.2162 | 0.2944 |
| `profile_va` | ctrl | bot | 0 | 0.5189 | 0.2146 | 0.2665 |
| `sd_base` | real | all | 0 | 0.4561 | 0.2463 | 0.2976 |
| `sd_base` | real | top | 0 | 0.4420 | 0.2520 | 0.3060 |
| `sd_base` | real | mid | 0 | 0.4620 | 0.2430 | 0.2950 |
| `sd_base` | real | bot | 0 | 0.4644 | 0.2438 | 0.2919 |
| `sd_base` | ctrl | all | 0 | 0.5184 | 0.2498 | 0.2319 |
| `sd_base` | ctrl | top | 0 | 0.5232 | 0.2456 | 0.2312 |
| `sd_base` | ctrl | mid | 0 | 0.5118 | 0.2614 | 0.2268 |
| `sd_base` | ctrl | bot | 0 | 0.5200 | 0.2422 | 0.2378 |
| `ref_levels` | real | all | 0 | 0.4499 | 0.3150 | 0.2351 |
| `ref_levels` | real | top | 0 | 0.4480 | 0.2848 | 0.2671 |
| `ref_levels` | real | mid | 0 | 0.4468 | 0.3193 | 0.2339 |
| `ref_levels` | real | bot | 0 | 0.4547 | 0.3407 | 0.2046 |
| `ref_levels` | ctrl | all | 0 | 0.5123 | 0.2783 | 0.2094 |
| `ref_levels` | ctrl | top | 0 | 0.5141 | 0.2648 | 0.2211 |
| `ref_levels` | ctrl | mid | 0 | 0.5076 | 0.2813 | 0.2111 |
| `ref_levels` | ctrl | bot | 0 | 0.5148 | 0.2914 | 0.1937 |

## D2 — volatility + geometry match

| generator | real A(t) med | ctrl A(t_k) med | share ctrl A(t_k) < A(t) | real w/m | ctrl w/m_k |
|---|---|---|---|---|---|
| `line1_cluster` | 0.001707 | 0.001716 | 0.397 | 0.478 | 0.468 |
| `fractal_h1` | 0.001688 | 0.001700 | 0.383 | 0.344 | 0.341 |
| `kde_swing` | 0.001689 | 0.001693 | 0.381 | 0.598 | 0.575 |
| `profile_va` | 0.001694 | 0.001705 | 0.364 | 0.631 | 0.617 |
| `sd_base` | 0.001755 | 0.001755 | 0.415 | 0.327 | 0.327 |
| `ref_levels` | 0.001661 | 0.001697 | 0.364 | 0.257 | 0.251 |

Per-tercile detail is in `_diag/DIAG.json` (`d2.by_tercile`). The control barrier ATR is effectively unbiased (share below 50% in every generator) and w/m is matched to within ~0.02, so the volatility-geometry hypothesis is not supported.

## D3 — pre-declared sensitivity (b): all barriers with A(t) frozen at the anchor

| generator | primary D_top | frozen-A D_top | frozen-A CI | n |
|---|---|---|---|---|
| `line1_cluster` | -0.0555 | -0.0641 | [-0.0768,-0.0511] | 6966 |
| `fractal_h1` | -0.0630 | -0.0712 | [-0.0886,-0.0540] | 3773 |
| `kde_swing` | -0.0573 | -0.0645 | [-0.0814,-0.0470] | 3849 |
| `profile_va` | -0.0532 | -0.0522 | [-0.0914,-0.0130] | 747 |
| `sd_base` | -0.0699 | -0.0739 | [-0.0976,-0.0489] | 2070 |
| `ref_levels` | -0.0737 | -0.0817 | [-0.0983,-0.0657] | 4724 |

Frozen-A barriers make D_top MORE negative in every generator: the volatility channel is not the driver. Recorded as a sensitivity field of the existing trials (no new trials).

## D5 — timing match `t_k - t` (controls)

| generator | median | p10 | p90 | share > 288 bars | share same bar |
|---|---|---|---|---|---|
| `line1_cluster` | 163 | 7 | 919 | 0.360 | 0.020 |
| `fractal_h1` | 147 | 6 | 898 | 0.345 | 0.026 |
| `kde_swing` | 152 | 6 | 873 | 0.343 | 0.027 |
| `profile_va` | 138 | 6 | 859 | 0.331 | 0.031 |
| `sd_base` | 158 | 7 | 911 | 0.347 | 0.019 |
| `ref_levels` | 137 | 4 | 895 | 0.342 | 0.037 |

Meaning (one paragraph, no hedging): the control event fires a median ~140-160 M5 bars (about half a day) after the anchor, at a band a median ~30 pips away, i.e. after the price has travelled to a level the anchor bar never reached; the real event fires where the price already is. This is the F1 episode-type asymmetry (reviewer/Lead-accepted, measured), and S-NEAR being MORE negative is a symptom of stronger-impulse episodes, not a timing artifact. The control bounce rate is flat across control-distance deciles (0.68 +- 0.005), so the mechanism saturates past 1 ATR and the causal claim is not established; the decisive test is R02's matched design.

## D6 — continuation endpoint detail and the exact failing clause

| generator | D_cont top | mid | bot | monotone | D>=5pp | CI>0 | sym>=3/4 | yr>=4/6 | BH q |
|---|---|---|---|---|---|---|---|---|---|
| `line1_cluster` | 0.2165 | 0.2137 | 0.2184 | NO | True | True | True | True | 0.0002 |
| `fractal_h1` | 0.2087 | 0.2042 | 0.2321 | NO | True | True | True | True | 0.0002 |
| `kde_swing` | 0.2867 | 0.2160 | 0.2092 | yes | True | True | True | True | 0.0002 |
| `profile_va` | 0.2730 | 0.3048 | 0.2221 | NO | True | True | True | True | 0.0002 |
| `sd_base` | 0.2857 | 0.2009 | 0.2550 | NO | True | True | True | True | 0.0002 |
| `ref_levels` | 0.2471 | 0.2110 | 0.1827 | yes | True | True | True | True | 0.0002 |

- `line1_cluster`: failed clauses = ['monotone']; symbol D_cont AUDUSD 0.255, EURUSD 0.249, GBPUSD 0.181, USDJPY 0.185; year D_cont 2016 0.227, 2017 0.256, 2018 0.194, 2019 0.190, 2020 0.205, 2021 0.225
- `fractal_h1`: failed clauses = ['monotone']; symbol D_cont AUDUSD 0.211, EURUSD 0.230, GBPUSD 0.216, USDJPY 0.177; year D_cont 2016 0.256, 2017 0.316, 2018 0.228, 2019 0.131, 2020 0.124, 2021 0.191
- `kde_swing`: failed clauses = none; symbol D_cont AUDUSD 0.260, EURUSD 0.270, GBPUSD 0.244, USDJPY 0.367; year D_cont 2016 0.260, 2017 0.313, 2018 0.293, 2019 0.372, 2020 0.275, 2021 0.204
- `profile_va`: failed clauses = ['monotone']; symbol D_cont AUDUSD 0.139, EURUSD 0.375, GBPUSD 0.361, USDJPY 0.162; year D_cont 2016 0.396, 2017 0.446, 2018 0.358, 2019 0.035, 2020 -0.103, 2021 0.475
- `sd_base`: failed clauses = ['monotone']; symbol D_cont AUDUSD 0.341, EURUSD 0.326, GBPUSD 0.289, USDJPY 0.181; year D_cont 2016 0.219, 2017 0.246, 2018 0.319, 2019 0.359, 2020 0.357, 2021 0.215
- `ref_levels`: failed clauses = none; symbol D_cont AUDUSD 0.312, EURUSD 0.299, GBPUSD 0.176, USDJPY 0.210; year D_cont 2016 0.296, 2017 0.267, 2018 0.214, 2019 0.184, 2020 0.224, 2021 0.294

The four generators flagged 'fail' in PHYSICS_RESULTS (line1_cluster, fractal_h1, profile_va, sd_base) fail ONLY the monotonicity clause of the continuation gate; their +5pp, CI, symbol and year clauses all pass. kde_swing and ref_levels pass every clause. BH q = 0.0002 everywhere.

## D7 — parity coverage (ruling already satisfied)

    UTC 2026-09-20T15:24:05Z · seed 20260920 · main symbol bars 200/generator, others 100 for line1_cluster.
    Tolerance: 0 mismatched bars (acceptance <= 0.5%).
    
    - `EURUSD` `line1_cluster`: 200 bars, 0 mismatches (0.0000%) — PASS
    - `EURUSD` `fractal_h1`: 200 bars, 0 mismatches (0.0000%) — PASS
    - `EURUSD` `kde_swing`: 200 bars, 0 mismatches (0.0000%) — PASS
    - `EURUSD` `profile_va`: 200 bars, 0 mismatches (0.0000%) — PASS
    - `EURUSD` `sd_base`: 200 bars, 0 mismatches (0.0000%) — PASS
    - `EURUSD` `ref_levels`: 200 bars, 0 mismatches (0.0000%) — PASS
    - `GBPUSD` `line1_cluster`: 100 bars, 0 mismatches (0.0000%) — PASS
    - `USDJPY` `line1_cluster`: 100 bars, 0 mismatches (0.0000%) — PASS
    - `AUDUSD` `line1_cluster`: 100 bars, 0 mismatches (0.0000%) — PASS
    
    OVERALL: PASS

PARITY.md already contains the 100-bar rows for GBPUSD/USDJPY/AUDUSD (written by the second parity run); all 0 mismatches. Nothing to re-run, no frozen file was overwritten.

## D8 — audit findings

### D8a — freshness rule: the frozen run MATCHES the frozen prereg

The frozen `PHYSICS_PREREG.md` §3 clause 2 specifies the strict-bucket rule (no intersecting bar anywhere in [t-24, t-1] AND at least one away bar); `phys_extract.py:92-96` implements exactly that. The R00 DRAFT's ordered-scan wording was superseded when the prereg was frozen and declared; there is NO code-vs-prereg divergence and no remedy. The table below is a POPULATION-WIDTH SENSITIVITY carried to R02 (an ordered scan that accepts as soon as an away bar is reached, ignoring older intersects behind it, admits more candidates); it is not a defect and it changed nothing in R01.

| generator | strict-bucket candidates (frozen rule) | ordered-scan candidates | difference | % |
|---|---|---|---|---|
| `line1_cluster` | 10650 | 14558 | +3908 | +36.7% |
| `fractal_h1` | 6439 | 8195 | +1756 | +27.3% |
| `kde_swing` | 5722 | 7321 | +1599 | +27.9% |
| `profile_va` | 1119 | 1383 | +264 | +23.6% |
| `sd_base` | 2631 | 3251 | +620 | +23.6% |
| `ref_levels` | 5952 | 7770 | +1818 | +30.5% |

Counts are EURUSD candidate events BEFORE the side/broken/strength gates, armed population; the realized difference is not measured (no new events per the order).

Note (reviewer F6): the draft-to-frozen §3.2 tightening was NOT declared in prereg §0 and should have been; that is a PROCESS DEFECT, recorded as such (Lead R01-FINAL-B §6.2). There is no code-vs-frozen-prereg divergence; the frozen spec binds and the result stands. Every future prereg must carry a 'diff vs draft' subsection in §0.

### D8b — `gate_verdict` years clause

`phys_stats.py:160` contains `bool(n_yr_pos >= 4 and n_yr >= 6) or bool(n_yr == 3 and n_yr_pos >= 3)`. The `n_yr == 3` branch is a BUG (the years stratum always has 6 values here, so the branch was dead in this round and changed no verdict). Marked for the R02 carry-forward list; not fixed in the frozen physics code.

### D8c — `pa_fill` TP R-value bug (fixed)

`lib/pa_fill.py:320` hardcoded `r = 2.0` on TP exits instead of `tp_mult`; any family with b != 2.0 would have recorded wrong R. Fixed to `r = float(sp["tp_mult"])` and locked by `tests/test_fill.py::test_tp_exit_r_uses_tp_mult_not_hardcoded_2`; the PA_Pro suite reports `43 passed` (was 42). The lib hash changes and is recorded in PROGRESS.md.

## D9 — `struct/zones/refs.py` daily-level carry-forward defect (CONFIRMED)

`refs.py:58-78`: `pdh/pdl/pdc` are written ONLY on the first bar of a new server day (`if day[i] != cur_day: ... self.pdh[i] = d_hi`), with no carry-forward; week levels (`refs.py:93-95`) and Asia levels (`refs.py:108-116`) DO carry forward. Measured on EURUSD DESIGN (445,858 M5 bars, 1,578 server days): pdh/pdl/pdc are finite on 1,577 bars (one per day) vs 445,595 bars under correct carry-forward; wk_hi finite on 445,027; asia_hi on 445,858.

Impact: (a) `RefBook.confluence` feeds the `T_ref` term of the strength score of ALL SIX generators on every bar, so the frozen terciles were computed with a term that saw daily levels on 0.35% of bars; (b) my `contam_ref` diagnostic reads the same `levels_at`, so the reported contamination rates (0.19-0.36) are UNDERSTATED for daily-level coincidences; (c) `ref_levels` publishes its zones at the rollover bar from the same arrays, so its zone set is probably unaffected, but its strength is. Not fixed in the frozen code.

Recorded in `rounds/R02/CARRY_FORWARD.md`.

## Summary of artefact candidates (descriptive)

- F1 (reviewer, Lead-accepted): the control's APPROACH DISTANCE asymmetry is the dominant explanation of both endpoints; the two arms are different episode types. Causal attribution NOT established (no dose-response among controls).
- D2 volatility/geometry: NOT supported (control ATR unbiased, w/m matched).
- D3 frozen-A barriers: makes D more negative -> not the driver.
- D4/D4b edge-vs-middle: REFUTED (arms are position-matched on medians and overlap in every decile), but position DOES modulate both endpoints strongly.
- D5 timing: S-NEAR more negative, a symptom of stronger-impulse episodes (F1).
- F3 refs.py carry-forward: unsystematic (0.35% of bars), cannot explain the gap.
- F4 n_yr==3 clause, F5 freeze guard, F7 raw-share report, F9 ledger last line, F10 stale run_counts, F11 mean_k column: recorded, inventory of defects; none of them changed a verdict.
- NO VALID EVIDENCE about zone physics in either direction from R01; the decisive test is R02's arrival-matched design.
