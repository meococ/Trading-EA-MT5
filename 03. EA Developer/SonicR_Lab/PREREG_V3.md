# PREREG_V3.md - ROUND 2C: CROSS-SYMBOL REPLICATION (frozen before any
# basket P/L)

Lead brief 23/09 20:20Z. Frozen with sha256 BEFORE the first basket P/L
file; hash recorded in LAB_LOG.md. Original text never edited after
freeze; any amendment goes in a separate section with its own hash.

Question: do the frozen rules replicate on symbols they were not fitted
on?

Configs: F0_J (reference), F2_NH_b, F5_S2, F5_S3 - exact round-2B/A1
definitions and exits, no changes.

Harnesses: H0 and H1 exactly as A1 (E1b, E2, E3 on both; E1 on H1 only).
Secondary column: daily flat 23:50.

Replication criteria (all on DESIGN, basket = the 10 symbols, both
harnesses unless stated):

  R1 essence: per-symbol Spearman(S, trade R) on F0_J trades; combined
     by Stouffer's z weighted by sqrt(n); replicates if one-sided
     p < 0.05 on H1 AND on H0, AND rho > 0 on >= 6 of the symbols with
     >= 100 trades.

  R2 config: pooled basket PF_R = sum(R>0) / sum(|R<0|) over all basket
     trades. A config replicates if pooled PF_R x1 >= 1.10 on H0 and H1,
     pooled PF_R x1.5 >= 1.00 on H1, and PF_R > 1.00 on >= 6 of 10
     symbols (H1).

  R3 luck check: for each config, the pooled basket PF_R must beat its
     random-entry null (per-symbol nulls, 20 seeds each, pooled the same
     way) at the 95th percentile on H1.

Reported, not judged: per-symbol tables, the EUR/XAU numbers next to the
basket, a portfolio view (below).

Portfolio view (reporting only): all basket symbols + EURUSD + XAUUSD,
1R risk per trade, account cap of 5 new trades per calendar week (TAH
doctrine, first-come by fill time) and max 3 open positions; report
trades/week per account, PF_R, positive years, MC DD P95 in R (200
reorderings), uncapped and capped.

Walls: VALIDATION and HOLDOUT of EVERY symbol stay unread this round;
the loader guard covers all 12 symbols (test_holdout_guard.py). A
symbol with < 90% DESIGN week coverage is dropped and named, never
replaced; "6 of N" criteria become ceil(0.6 x N). No parameter may
change vs A1/frozen 2B definitions. This round measures, it does not
promote.
