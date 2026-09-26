> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**

# M5 — Trend lines (DESIGN 2016–2021)

Prereg `abc8b5ba…` — post-review revision: placebo = 2 price-shifted copies of each real line (same anchors/slope, +/-delta*ABR, delta~U[1.5,4]) scanned by the same machinery (exchangeable).  Strata side x dow x 4h x ABR-tercile x approach-decile x slope-class x symbol (per-symbol edges).

## Context

| sym | touches | plac touches | P(bounce x1) real | plac | breaks | plac breaks | share first |
|---|---|---|---|---|---|---|---|---|
| EURUSD | 19771 | 27496 | 0.632 | 0.614 | 32218 | 44655 | 0.913 |
| GBPUSD | 19653 | 26507 | 0.629 | 0.614 | 33236 | 45132 | 0.920 |
| USDJPY | 19222 | 25563 | 0.631 | 0.591 | 30482 | 41817 | 0.908 |
| AUDUSD | 19152 | 25190 | 0.629 | 0.602 | 29225 | 40816 | 0.911 |

## F-TL — D = P(bounce|real line) - P(bounce|placebo line) at the third touch

| test | D | CI | p | q | stable |
|---|---|---|---|---|---|
| x1_t3 | 0.0716 | 0.0647–0.0786 | 0.0005 | 0.0010 | YES |
| x2_t3 | 0.0839 | 0.0777–0.0899 | 0.0005 | 0.0010 | YES |
| x1_all_desc | 0.0631 | nan–nan | nan | nan | — |
| x2_all_desc | 0.0754 | nan–nan | nan | nan | — |

## F-SLOPE — cont24 after break: rising vs (flat|falling), real-vs-real

| test | D | CI | p | q | stable |
|---|---|---|---|---|---|
| rising_vs_rest_up | -0.0099 | -0.0220–0.0007 | 0.0770 | 0.1027 | YES |
| rising_vs_rest_down | 0.0021 | -0.0067–0.0141 | 0.4640 | 0.4640 | no |

descriptive — per-class real vs placebo lines (D, no q):

| class | cont24 | fwd_48 (ABR) |
|---|---|---|
| rising | 0.0008 | -0.0201 |
| flat | 0.0027 | -0.0641 |
| falling | 0.0018 | -0.0239 |
