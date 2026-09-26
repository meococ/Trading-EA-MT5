# PREREG_V4 — ROUND 2D: EXIT MANAGEMENT FOR F2_NH_b

Frozen 2026-09-23 (before any exit-variant P/L file exists).
This text is verbatim-frozen; amendments go in new sections, never edits.
Scope/walls unchanged: no MQL5/MT5/alpha.ps1/git write; heavy runs only
via heavy_run.py --lane sonic-lab, never parallel; read-only outside
SonicR_Lab; HOLDOUT of every symbol sealed; VALIDATION read at most
once and only if the confirm stage passes (logged unlock).

## Question

Does one pre-registered exit rule improve NH_b's exits trade-by-trade
on symbols it was not designed on, and does the improved system then
clear the PF_R gate 1.10 on unread data (VALIDATION)?

## Split (fixed by the Lead before any exit-variant P/L; verified)

Snippet (rerun and verified 2026-09-23 ~21:26Z):

```python
import random
rng = random.Random(20260924)
pairs = [("AUDUSD","NZDUSD"),("USDCAD","USDCHF"),("EURJPY","GBPJPY"),
         ("AUDJPY","USDJPY"),("GBPUSD","EURGBP")]
D, C = [], []
for a, b in pairs:
    (D, C) if rng.random() < 0.5 else (C, D)  # first -> D iff < 0.5
# actual code: D.append(a) if r<0.5 else C.append(a); other -> other set
```

Printed output:

    D basket: ['AUDUSD', 'USDCHF', 'GBPJPY', 'USDJPY', 'GBPUSD']
    C: ['NZDUSD', 'USDCAD', 'EURJPY', 'AUDJPY', 'EURGBP']
    D total = ['AUDUSD', 'USDCHF', 'GBPJPY', 'USDJPY', 'GBPUSD',
               'EURUSD', 'XAUUSD']

DESIGN set D = AUDUSD, USDCHF, GBPJPY, USDJPY, GBPUSD + EURUSD + XAUUSD
(EUR/XAU were used to pick NH_b, so they belong on the design side)
-> 7 symbols.
CONFIRM set C = NZDUSD, USDCAD, EURJPY, AUDJPY, EURGBP -> 5 symbols.

Honest limit (written down before any C computation): C is the same
time window, and the Lead has already seen X0 (baseline) per-symbol
results on C from 2C. So C can test the EXIT EFFECT (paired dR), not
the entry edge; the level test (PF_R gate 1.10) is done on VALIDATION.
Until the design-stage decision is logged, no exit-variant result on a
C symbol may be run, printed or opened.

X0's pooled and per-symbol PF_R on C from the 2C trade files
(already known to the Lead), written in for reference:

    H0: NZDUSD 1.0778 (n=1297), USDCAD 0.8172 (n=1406),
        EURJPY 1.1568 (n=1289), AUDJPY 1.0136 (n=1224),
        EURGBP 1.0879 (n=1240); pooled 1.0124 (n=6456)
    H1: NZDUSD 1.0305 (n=1189), USDCAD 1.0026 (n=1249),
        EURJPY 1.0804 (n=1185), AUDJPY 1.0494 (n=1141),
        EURGBP 1.0087 (n=1118); pooled 1.0337 (n=5882)

## Configurations (exits only; entries/SL/TP/session/costs/E1-E3/H0-H1
unchanged; F2_NH_b orders are the frozen 2C files)

X0-HOLD (reference) and 9 candidates: X0-DF, X1-HOLD, X1-DF, X2-HOLD,
X2-DF, X3-HOLD, X3-DF, X4-HOLD, X4-DF. HOLD = today's behaviour
(Friday flatten only). DF = HOLD + daily flat: any open position is
closed at the open of the first clean M1 bar at/after 23:50 server
every day (same mechanics as daily_flat_mod=1430; E1/E1b as today).
Verified 2026-09-23: no X0 fill occurs in [23:50, roll window end) on
any D symbol/harness, so DF never changes an entry.

    X0  baseline exit = F2_NH_b as in 2C (no management).
    X0-DF = baseline exit + daily flat.
    X1  BE1: at the trigger, SL -> BE level. TP unchanged.
    X2  PART: two half-size positions at the fill: leg A TP = +1R,
        leg B the original TP; both carry the original SL. When leg A's
        TP fills on bar i, leg B's SL -> BE from bar i+1. Leg A's TP
        fills like any TP (no gap bonus, E1/E1b as today). If a bar
        reaches both +1R and leg B's TP, both legs fill at their own TP
        prices. If a bar hits the SL first, both legs stop.
        Trade R = [dir*0.5*(partA_px - fill) + dir*0.5*(partB_px - fill)
        - m*cost_x1] / R0, m = 1/1.5/2 (one round-trip cost for the
        whole size). Export part_ctm, part_px and leg B's exit fields.
    X3  DRAGON: X1, plus a Dragon exit. For every M15 bar that CLOSES
        after the trigger bar's time: long and M15 close < EMA34(Low)
        of that bar (short: close > EMA34(High)) -> exit at the open of
        the first clean M1 bar of the next M15 bar. That exit happens
        at the bar's open, so it takes priority over the same M1 bar's
        SL/TP (if that open is already beyond the stop, the exit price
        is still the open). E1b if in the roll window. Reason "dragon".
        TP unchanged. Same Dragon arrays the signal generator uses
        (context), values of CLOSED bars only. Under H1: if the M15
        bar's last M1 bar is suspect, skip that bar's check (wait for
        the next M15 close); under H0 no skip.
    X4  RUN: same as X3 but with NO take-profit: exits are original SL,
        BE, dragon, Friday flatten (and daily flat in DF mode).

Trigger = the first CLEAN M1 bar i (fill bar included) whose favourable
extreme reaches fill + dir x 1.0 x R0, R0 = |fill - original SL|.
Fixed at 1.0R for every variant; no parameter search.

EA semantics the sim copies exactly: the EA acts on the trigger at the
OPEN of M1 bar i+1 (new-bar check). So a new stop level is live from
bar i+1; on bar i the original SL and TP stay in force; inside any one
M1 bar the order is SL first, then TP (as today).

Sensitivity column (reported, and used as a guard in the design rule):
"pessimistic same-bar" = if bar i's range contains both the +1R level
and the BE level, the trade exits at BE on bar i (unless SL hit first).

BE level = fill + dir x cost_x1 (round-trip cost in price), so a BE
exit nets about 0R at cost x1. A BE exit uses the SL fill logic (gap ->
bar open; E1 and E1b exactly as for SL). Reason code "be".

R is always measured against R0, costs included, at x1/x1.5/x2 as
today. E1 (skip suspect bars, first-clean-bar rules), E1b (roll
stress), Friday flatten and the optional daily flat 23:50 apply to
every new exit type exactly as they apply to SL/TP today.

## Modes

PRIMARY "fixed list": take X0's filled trades exactly as in the 2C
trade files (same fill bar, fill price, SL, TP, R0) and re-simulate
only the exit of each trade under each variant, from its fill bar.
Every selection statistic uses this mode, so each variant is paired
trade-by-trade with X0 on the same trades.

SECONDARY "free running": run_trades with the variant inside (a shorter
or longer hold changes which later signals get taken, because of the
one-position rule). Reported only.

Disclosure: 2C already wrote a free-running flat2350 column for the C
symbols into out/design_summary_2c*.csv; it was not reported and the
Lead has not read it; the confirm stage uses the fixed-list mode, which
is new computation.

## Power note

Trade counts: D pooled n = 9280 (H0) / 8444 (H1); C pooled n = 6456
(H0) / 5882 (H1); VALIDATION all-12 counts determined at read time.
Smallest mean dR detectable at 80% power, one-sided 5%:
MDE = (z_.95 + z_.80) * sd / sqrt(n) = 2.486 * sd / sqrt(n).
Using sd(X0 R) as the conservative bound: C pooled H1 sd = 1.69 ->
MDE ~ 0.055R; per-C-symbol n ~ 1120-1250 -> MDE ~ 0.12R. Paired dR sd
is expected far below sd(R); a pilot sd of dR on D will be logged after
the freeze (frozen text unchanged).

## Bootstrap

By calendar week, 2000 resamples, seed 20260924. One-sided 95% lower
bound for mean paired dR (K1); 90% CI for design-stage mean dR.

## DESIGN-STAGE RULE (on D pooled = all 7 symbols' trades together,
DESIGN window, fixed list)

Eligible if: pooled PF_R x1 >= 1.10 on H0 AND on H1; pooled PF_R x1.5
>= 1.00 on H1; mean paired dR = R(variant) - R(X0) > 0 on H0 and on H1;
and the pessimistic same-bar column also has mean dR > 0 on H1.
Rank eligible candidates by min(PF_R x1 H0, PF_R x1 H1). Exactly ONE
advances. Ties (equal to 3 decimals) -> fewer moving parts wins, in
this order: X0-DF, X1-HOLD, X1-DF, X2-HOLD, X2-DF, X3-HOLD, X3-DF,
X4-HOLD, X4-DF.
If none is eligible, the round stops after the design stage: C stays
unread for every candidate and no threshold is relaxed.

## CONFIRM-STAGE RULE (on C, only the advanced variant vs X0, fixed
list, DESIGN window) - tests the exit effect:

    K1 (primary) paired dR: one-sided 95% bootstrap lower bound > 0 on
       H1, and mean dR > 0 on H0.
    K2 mean dR > 0 on >= 4 of the 5 C symbols (H1).
    K3 sanity floor (not the gate): pooled PF_R x1 >= 1.05 on H0 and
       H1; pooled PF_R x1.5 >= 1.00 on H1.
    K4 pooled PF_R of the variant beats the pooled random-entry null
       that uses the SAME exit rule on H1: 100 seeds per symbol, pooled
       per seed; pct = share of the 100 pooled null values strictly
       below the variant; pass if pct >= 95.

All four pass -> step 6 (VALIDATION unlock). Any fail -> stop, report.

## VALIDATION RULE (read ONCE, only if confirm passed; all 12 symbols;
the advanced variant, with X0 for reference):

    pass = pooled PF_R x1 >= 1.10 and expectancy > 0 on H0 AND H1,
           pooled PF_R x1.5 >= 1.00 on H1, PF_R > 1.00 on >= 7 of 12
           symbols (H1), mean paired dR > 0 on H1.

## Multiple testing note

9 candidates x 2 harnesses on D, paired against the same X0 trades; one
hypothesis on C; one on VALIDATION.

## Mandatory tests status (all PASS before this freeze)

    T1 regression: X0 through the new exit layer reproduces the 2C
       trade files row for row (exit_ctm, exit px, reason, r_x1 to
       1e-9), all 12 symbols x H0/H1 x {fixed list, free running}:
       24/24 cells, zero fails.
    T2 synthetic paths: +1R then back to entry -> "be" ~0R; SL and
       trigger in one bar -> "sl" at -1R; X2 formula (bar reaching both
       +1R and TP; E1b on leg A); short mirrors; pessimistic same-bar.
       tests/test_exits.py: pass.
    T3 no look-ahead in the Dragon exit: post-exit M1 edits with M15
       and EMA34 RECOMPUTED -> same exit; altering the triggering M15
       bar's close moves the decision; H1 last-M1-suspect skips the
       check. tests/test_exits.py: pass.
    T4 X0 random-entry null through the new code equals the 2C null
       path (GBPUSD, seed 0): identical trades and R. pass.
    T5 X0-DF free-running reproduces the 2C pf_r_x1_flat2350 column on
       AUDUSD and EURUSD, H0 and H1, to 1e-9: pass.
