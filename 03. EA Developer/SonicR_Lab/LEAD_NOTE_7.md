# LEAD NOTE 7 - A1G: G1r replaced (once) by G1b + AUDIT RULE A
(Lead, 24/09 03:46Z; verbatim spec for the A1G addendum. Frozen before
any code/power run of the addendum; HOLDOUT still sealed.)

## Why G1r is withdrawn (one redesign, logged as deviation)
G1r (drop every trade beyond +/-5R) was meant to catch PHANTOM winners
from bad prints, but it removes the strategy's real big winners (TP at
a far zone = right-skewed payoff): it tested payoff shape, not data
validity. Winsorize / median-R and a "single-bar winner" gate were
considered and rejected for the same reason.

## What replaces G1r (everywhere in the brief)
1. **G1b - not carried by one trade (gate):** pooled AM PF_R x1 on H1
   FR, after removing the single largest winner of EACH symbol (2
   trades total), >= 1.05.
2. **AUDIT RULE A - phantom-trade check (not a gate; downgrade-only):**
   a. Spike detector per winning TP-exit trade: neighbours = minute-
      aligned, non-E0'-voided M1 bars in [exit-5min, exit+5min], exit
      bar excluded. jump = TP - max(neighbour highs) [long] or
      min(neighbour lows) - TP [short], same price/spread convention
      the sim uses for TP fills. Flag if jump > 5 x median(high-low)
      of that server day's minute-aligned non-voided bars. <4
      neighbours (gap) -> flag "gap".
   b. AUDIT LIST = every spike/gap-flagged trade + every |R|>5 trade
      (any exit), both harnesses, both modes, de-duplicated. Columns:
      symbol, side, fill time+price, exit time, exit price, exit type,
      R, flag reason -> out/audit_list_2g.csv + pasted in RESULTS_v7.
   c. The LEAD checks each audit trade vs broker tick history (MT5,
      read-only): entry and exit price reached within +/-2 min,
      tolerance EURUSD 1.0 pip / XAUUSD 0.50 USD. Fail = "unconfirmed".
   d. Consequence (no-fix rule): removing unconfirmed WINNERS turning
      any gate pass->fail => INCONCLUSIVE; unconfirmed LOSERS deciding
      a FAIL => FAIL-DATA. Nothing moves upward. Printed verdict is
      "PASS pending Lead audit A" when all gates pass.
3. Reported, not gated: old G1r number; share of net R from top 1% and
   top 5% of trades; spike-detector flag counts and R for DESIGN,
   VALIDATION, HOLDOUT.

## STEP A code: one spike-detector function on raw M1, used by every
window. T14: pre-E0' VALIDATION bogus winner EURUSD 2022-10-19
13:47:44 (+57.7R) flagged (USDCAD +132.2R if reachable); report flag
rate among VALIDATION TP winners (EUR+XAU, H1 FR, E0' files), list all
- no threshold tuning.

## STEP B: power again with G1b; same method, same stop rule (<0.60).
## STEP C: re-freeze hashes -> out/freeze_2g_hashes_a1g.csv (list
changes vs the first freeze; freeze_2g_hashes.csv untouched).
## STEP D: PREREG_V7 with G1b + AUDIT RULE A verbatim; old G1r moved to
"reported"; history line: "G1r was replaced once, before any HOLDOUT
access, because the pre-read power check showed it tested payoff
shape, not data validity (LAB_LOG 03:32Z; addendum A1G sha ...)."
Then the read, deliverables, REVIEW_v7 (+check 8: A1G sha ordering).
Also: RESULTS_v7 states the 2F swap column was understated (n_rolls
bug) and shows the corrected VALIDATION swap column beside it.
