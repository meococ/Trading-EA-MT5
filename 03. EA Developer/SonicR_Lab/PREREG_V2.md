# PREREG_V2 - ROUND 2B frozen specification (frozen before ANY 2B P/L)

Frozen at write time 2026-09-23T19:1xZ (see LAB_LOG for exact hash line).
This file binds round 2B. It is written AFTER the 2B census (counts and
the W4d Q constant only - no P/L of any 2B config exists yet) and BEFORE
`runs/run_design_2b.py` produces `out/trades_2b_*`.

## Provenance
- LEAD_NOTE_4.md sha256 =
  b15654a19e0b9a9ff3171bbe35b11fad11a65adca45bda3b92457d2c0f9f8906
  (verified 2026-09-23T19:03Z; the Lead froze it at 17:40:34Z, before any
  per-element DESIGN P/L existed).
- PREREG.md (round 2) sha256 =
  94214bbfa768665e7741d2f79dd2e6ba54ddad3eee848ed1ae9a080df473abb1
  remains in force; nothing here changes round-2 numbers.

## Harness errata in force for ALL configs (round-2 rerun AND round 2B)
Lead errata E1-E3 (brief 19:02Z), applied to every config uniformly:

- E1 (fabricated bars skip): **NOT APPLIED** - decided by the registered
  diagnostic in DATA.md: roll-window median M1 range / M15 ATR14
  suspect/clean ratio = 0.86 (EURUSD) and 1.19 (XAUUSD), both < 2.0.
  Only E1b applies. sim.py keeps the skip machinery behind
  `skip_suspect=False`.
- E1b (rollover spread stress, Lead assumption): transaction price
  worsens by S_roll on the ask side when the resolving M1 bar is inside
  the roll window - EURUSD 23:55-00:15 server, +2.0 pips;
  XAUUSD 00:55-01:20 server, +20 pips ($2.00).
- E2 (executability floor): skip any order with
  (pending_px - SL) * dir < max(3 x round_trip_cost, 0.15 x ATR14[t]).
  Removal counts reported per config in the census. The wrong-side-stop
  admission guard is kept as a second line; `sl_big_swing` itself was
  fixed to only return confirmed extremes strictly beyond the pending
  price on the stop side (None otherwise).
- E3 (metric): primary = PF_R = sum(+R)/sum(|negative R|) at cost x1 and
  x1.5. A config must clear the PREREG thresholds on BOTH PF_R and the
  registered PF in pips. Random-entry control percentile uses PF_R.
  Secondary column (NOT selection): same config with a daily flat at
  23:50 server.

## Round 2B configs (verbatim from LEAD_NOTE_4)
Base = F0_J signal generator (same wave, trigger, entry, session, costs,
sim). All inputs are bars <= t.

1. F1_W4c: dir * (mid[t] - mid[t-20]) > 0.
2. F1_W4d: dir * angle20[t] >= Q, angle20 = (mid[t]-mid[t-20])/(20*ATR14[t]).
   Q = median of dir*angle20 over F0_J DESIGN signals of the same symbol,
   computed in the 2B census (outcome-blind, orders only):
   **Q_EURUSD = -0.0063401056, Q_XAUUSD = -0.0053644141**
   (runs/q_w4d.json; also in out/census_2b.csv printout).
3. F1_PV2a: any bar in [leg2-1, leg2+1] has PVA class rising or climax
   (TAH thresholds). leg2 confirmed at or before t.
4. F1_PV2b: trigger bar t has PVA class rising or climax.
5-8. F5 confluence S = W2any + W3 + W4c + PV2a (0..4), W2any = WHQ zone
   OR swing zone at the leg-0 origin price. Exits = R1b + R2a.
   F5_S2 (S>=2), F5_S3 (S>=3), F5_S2_EXT / F5_S3_EXT (london_ext).

2B census counts (outcome-blind) live in out/census_2b.csv.

## Essence test (pre-registered, LEAD_NOTE_4 verbatim)
On F0_J DESIGN trades (J exits, both symbols, all signals, no gates):
S per trade; report expectancy R, PF x1, PF x1.5 per S bucket (buckets
<30 trades merge upward), 1000-sample bootstrap 90% CI. One-sided
Spearman S vs trade R, p<0.05, per symbol and pooled. Same with/without
split per single element. Evidence only - selection uses the PREREG rule.

## Selection and validation
- Selection rule, costs, windows, heavy lock, walls: unchanged from
  PREREG.md; thresholds applied to BOTH PF_R and PF in pips (E3).
- Trials for deflated Sharpe / best-of-N: N = 25 configs x 2 symbols.
  Best-of-N null computed twice: all configs as registered, and configs
  with >= 1 trade/week/symbol only.
- At most 3 configs advance. VALIDATION read once, only for those;
  pass = PF_R x1 >= 1.15 and expectancy > 0. HOLDOUT stays sealed.
- If nothing passes: no tuning; honest verdict per family + 2-3 next
  approaches.


---

# AMENDMENT A1 (Lead addendum, 23/09 19:17Z) - appended, frozen text above untouched

The Lead's 19:06Z diagnostic rule (median M1 range ratio < 2 -> skip E1)
was applied correctly, then corrected by the Lead: the median is the
wrong statistic. Corrected diagnostic (DATA.md): exits per 1000
trade-minutes inside the roll window run 19x-450x the outside rate
across all 25 configs; per-day max M1 range inside the roll window is a
median 31x/38x (EUR/XAU) the adjacent quiet windows; jump-and-revert on
25.7%/18.1% of days. The standing repo rule already voids trades priced
inside suspect bars. E1 is therefore APPLIED.

## Two harness versions, both reported for every config (25 x 2 x 2)
- H0 = E1b + E2 + E3 (suspect bars tradable) - already run.
- H1 = H0 + E1 (sim.py skip_suspect=True; SL/TP/pending checks skip
  suspect bars; first clean bar after a suspect run: SL beyond open ->
  fill at open, TP beyond open -> fill at TP, pending beyond open ->
  fill at open; Friday flatten on a suspect bar -> first clean bar open).
- Controls: 100 seeds for configs with PF_R >= 1.05 on H0 or H1, else 20.
- Daily-flat-23:50 secondary column kept on both harnesses.

## Selection (replaces the selection paragraph above)
A config advances only if it passes the PREREG selection rule on BOTH
harnesses AND on BOTH PF_R and PF in pips (thresholds unchanged).
Rationale: the two versions bracket the data problem (H0 keeps suspect
bars, H1 voids them); requiring both removes any incentive to pick the
harness that flatters a config. Best-of-N over 25 x 2 x 2 = 100 cells
(also reported on the >= 1 trade/week subset). At most 3 advance.
VALIDATION read ONCE, on both H0 and H1, for those only; pass = PF_R
x1 >= 1.15 and expectancy > 0 on both. HOLDOUT stays sealed.
Essence test reported on both H0 and H1.

This amendment was written before any H1 control/selection result
existed (H1 design P/L existed - 19:31Z - but controls, selection and
validation did not).
