# PREREG_V7 — ROUND 2G (+A1G): THE ONE HOLDOUT READ (EURUSD + XAUUSD)

Frozen with sha256 in LAB_LOG BEFORE any HOLDOUT bar is loaded.
One read, once. After the unlock: NO-FIX RULE (below) applies.

## Question

Does the frozen candidate earn on EURUSD + XAUUSD over data nobody
has seen — HOLDOUT = (VALIDATION_END, COMMON_END]?

Exact constants (src/data.py):
  VALIDATION_END = 1684333392  (= 2023-05-17 14:23:12 server; the
    "~2023-05-25" comment in data.py is wrong - this number rules)
  COMMON_END     = 2026-09-18 23:59 server
  HOLDOUT        = (1684333392, COMMON_END]  ≈ 174 weeks

## History (honest)

The London-morning filter was found on DESIGN symbols (recomputed
with the corrected DST mapping), passed a confirm half (C: K1-K3) and
a VALIDATION read that FIRST failed on H0 because of malformed
(second-stamped) prints, then passed after the pre-declared E0' fix
(LEAD_NOTE_6; void bars with non-zero-second timestamps in every
harness). That VALIDATION pass is PROVISIONAL. This read is the
confirmation; there is no historical data left after it.

DEVIATION (one, pre-declared): G1r was replaced once, before any
HOLDOUT access, because the pre-read power check showed it tested
payoff shape, not data validity (LAB_LOG 03:32Z; addendum A1G sha
25212ea7d930751a4abb13323c760876b15fd24ba633d9e9e2c2d892c451ab42).
Old G1r is moved to "reported, not gated". No further redesign
without the Lead.

## The candidate (frozen; nothing may change this round)

F2_NH_b exactly as in round 2F: the generator with the DST fix and
reset_zones() in orders_for; entries only from signals whose M15 bar
opens in [07:00,12:00) London time; exits X0-HOLD (SL, zone TP,
Friday flatten); costs as coded (data.py COST: EURUSD 1.0 pip RT,
XAUUSD 5.5 pip RT; E1b roll stress, E2 floor); E0' (bars with
non-zero-second timestamps void in every harness); SL caps as coded
(EURUSD 120 pips; XAUUSD = runner.sl_cap, a fixed price amount from
DESIGN medians; SL > cap -> no trade). Harnesses H0 and H1 as since
A1. Mode FR = free-running AM-only (PM orders never placed; the EA's
own mode). Mode FL = fixed list (X0 run on all signals, then the AM
filter).

## Quoted definitions (verbatim from PREREG_V6 — they rule)

Label:
> AM iff London hour of the M15 signal bar open (sig_ctm) in [7,12);
> PM iff [12,16); else OUT (excluded from every statistic incl. base;
> none exist after the DST fix). Year = London calendar year of the
> signal bar. Holding is unchanged (SL/TP/Friday flatten). Entry, SL,
> TP, exits (X0-HOLD), costs, E1/E1b/E2/E3, H0/H1 unchanged.

Statistics:
> - sep = mean R(AM) - mean R(PM).
> - Bootstrap: calendar 4-week blocks resampled JOINTLY for all
>   symbols and all trades (same block draw for every subset), 2000
>   resamples, seed 20260924; one-sided p and 95% lower bound from it.
> - Primary harness H1 (suspect roll bars voided); H0 must agree in
>   sign.
> - Two modes: FIXED LIST (X0-HOLD trades from the _dstfix files, AM
>   kept) and FREE-RUNNING AM-ONLY (generator never places PM orders).

Confirm-stage (K1-K3, completed in round 2F — quoted for reference):
> - K1 sep: one-sided 95% lower bound > 0 on H1, and sep > 0 on H0.
> - K2 AM PF_R > PM PF_R on >= 4 of the 5 C symbols (H1).
> - K3 on H1: sep > 0 within longs and within shorts, and AM PF_R >
>   PM PF_R in >= 6 of the 10 full DESIGN years (2010-2019).

Validation (V1-V3, completed provisionally in round 2F — quoted for
reference):
> - V1 AM pooled PF_R x1 >= 1.10 and expectancy > 0 on H0 AND H1, and
>   AM pooled PF_R x1.5 >= 1.00 on H1 — required in BOTH modes (fixed
>   list and free-running AM-only).
> - V2 AM PF_R > 1.00 on >= 7 of 12 symbols (H1, fixed list).
> - V3 sep > 0 on H1 with one-sided 95% LB > 0 (fixed list).

FR position-coexistence rule (as implemented, src/sim.py):
> One pending + one position at a time per (symbol, config).
> busy_until_m1: a new order whose scan start is <= busy_until_m1 is
> skipped (not queued). An unfilled pending occupies the book until
> its expiry; a filled position occupies it until its exit bar.
> E2 admission floor applies first: orders with
> (entry - sl)*dir < max(3 x round-trip cost, 0.15 x ATR14) are
> skipped and counted in df.attrs["rejected"].

## Window rules

Indicators warm up on earlier prices; signals only inside HOLDOUT;
the book starts empty; positions open at COMMON_END close at the
last bar and are counted. Calendar years by fill time (server);
2023 and 2026 are part-years.

## Pre-freeze record (logged in LAB_LOG)

- T11 whitelist guard: raises for GBPUSD (+ basket symbol) with the
  unlock flag ON, and for EURUSD with it OFF. PASS.
- T12 dry-run to VALIDATION_END reproduces the 2F E0' trade files
  (both harnesses, both modes) row for row. PASS.
- T13 prefix truncation: orders before 2022-06-30 identical with a
  2022-06-30 vs VALIDATION_END context. PASS.
- Swap (post-processing): R_adj = R + swap_per_night * nights /
  |entry - SL|; Wednesday roll counts 3. Broker values (read 24/09,
  swap_mode=points): XAUUSD long -0.126, short -0.046 USD/oz;
  EURUSD long -0.0000070, short -0.0000100. Handcheck PASS
  (corrected n_rolls; the 2F copy never applied the Wednesday triple
  — the 2F swap column was understated and is shown corrected next
  to it in RESULTS_v7).
- XAU fixed cap = 21.22 price units (DESIGN medians). Relative-cap
  arm = same multiple (~1.001) of the trailing 250-trading-day
  median daily range, known at the signal bar (shifted).
- POWER (A1G, G1b): 4-week block bootstrap, 2000 resamples,
  seed 20260924, HOLDOUT-size 174 wk, from VALIDATION E0' FR H1 AM
  trades (n=588, base PF_R 1.390). P(all gates) as-is = 0.930;
  per-gate: G1 .98, G1b .98, G2 .99, G3 .97, G4 1.00, G5a .96,
  G5b .96; reporting-only G1r .49. Shifted-to-PF1.15 arm: 0.387.
  T14: detector flags both pre-E0' bogus winners; VALIDATION
  TP-winner flag rate 0/131.
- Code freeze: out/freeze_2g_hashes_a1g.csv (31 files); changed vs
  the first freeze: runs/holdout_2g.py, runs/prefreeze_2g.py;
  added: LEAD_NOTE_7.md, src/spike.py, tests/test_spike_2g.py.
  out/freeze_2g_hashes.csv untouched.

## GATES (all must pass; pooled = EURUSD + XAUUSD trades together)

  G1  pooled AM PF_R x1 >= 1.10 and expectancy > 0, on H0 AND H1,
      in FR AND FL.
  G1b not carried by one trade: pooled AM PF_R x1 on H1 FR, after
      removing the single largest winner of EACH symbol (2 trades
      in total), >= 1.05.
  G2  realism stress: pooled AM PF_R with costs x1.5 AND swap x2
      (broker values doubled) >= 1.00, on H1, FR and FL.
  G3  each symbol's AM PF_R x1 > 1.00 on H1 FR (the EA must earn on
      each symbol it trades; EURUSD cannot hide behind a gold trend).
  G4  mechanism: sep = mean R(AM) - mean R(PM) > 0 on H1 FL (all
      signals).
  G5  account viability, H1 FR pooled: MC DD P95 (200 reorderings,
      x1 cost) <= 50R AND at least 3 of the 4 calendar part-years
      (2023..2026) with net R > 0.
  "x1" means the PREREG_V6 costs with no swap (as on VALIDATION);
  swap enters only G2 and the reported swap column.

Sample floors: a symbol with fewer than 150 AM trades on H1 FR, or
under 90% of weeks with data, makes its G3 cell INCONCLUSIVE (it is
not dropped).

## AUDIT RULE A (verbatim; not a gate; downgrade-only)

  a. Spike detector: for every winning trade with a TP exit, take
     the neighbours = minute-aligned, non-E0'-voided M1 bars with
     timestamps in [exit_time - 5 min, exit_time + 5 min], exit bar
     excluded. jump = TP - max(neighbour highs) for a long,
     min(neighbour lows) - TP for a short, using the SAME
     price/spread convention the sim uses to decide a TP fill.
     Flag if jump > 5 x the median (high - low) of that server
     day's minute-aligned non-voided bars. Fewer than 4 neighbours
     (gap) -> flag "gap".
     (Implementation note: the checked price is the executed exit
     price, which equals the order TP for a normal fill and the bar
     open for a gap-through — the same convention the sim uses to
     decide and price a TP fill.)
  b. AUDIT LIST for HOLDOUT = every spike/gap-flagged trade + every
     trade with |R| > 5 (any exit type), both harnesses, both modes,
     de-duplicated. Columns: symbol, side, fill time (server) and
     price, exit time, exit price, exit type, R, flag reason ->
     out/audit_list_2g.csv, pasted in RESULTS_v7.
  c. The LEAD checks each audit trade against the broker's own tick
     history (MT5, read-only; the lane does NOT touch MT5): entry
     and exit price must be reached by the broker's bid/ask within
     +/-2 minutes of the sim's times (tolerance EURUSD 1.0 pip,
     XAUUSD 0.50 USD). A trade that fails is "unconfirmed".
  d. Consequence (pre-declared, no-fix rule): if removing the
     unconfirmed WINNERS turns any gate from pass to fail, the
     verdict is INCONCLUSIVE, not PASS. If unconfirmed LOSERS
     decided a FAIL, the verdict is FAIL-DATA. Nothing is ever
     moved upward. A printed PASS is "PASS pending Lead audit A".

## VERDICT STATES

PASS = every gate passes, no cell INCONCLUSIVE, reviewer confirms
(printed "PASS pending Lead audit A"). FAIL = any gate fails.
INCONCLUSIVE = no gate fails but a cell is INCONCLUSIVE, or the
audit consequence above applies. INCOMPLETE = timebox hit before
every gate cell exists (no partial verdict; the same frozen read
resumes next round). FAIL-DATA = a gate fails and the reviewer
confirms the failing trades were decided by a non-market print
(minute-aligned bar > 20% off the previous close): still not a PASS;
at most it sends the candidate to a forward test as the only
confirmation.

## NO-FIX RULE

After the unlock no rule, parameter, cost, cap or cleaning may
change. A data or code problem found after the unlock is diagnosed
and reported next to the verdict; it can only move PASS ->
INCONCLUSIVE or FAIL -> FAIL-DATA, never upward. A fix can only be
confirmed on new data (forward test).

## Reported, not gated

Per-year table; long/short per symbol; Friday split; swap x1 column
(corrected; the old understated 2F column shown beside it); cost x2;
trades/week per account; MC DD P95 and realized max DD; the H0-H1
difference and where it sits (rollover / session-open bars); the
XAUUSD cap binding rate per year (D, V, H); the relative-cap arm
with every gate computed (labelled "not gated - forward-test
candidate"); the census; the +/-5R list; old G1r (PF with |R|>5
removed); the share of net R from the top 1% and top 5% of trades;
spike-detector flag counts and R for DESIGN, VALIDATION, HOLDOUT.

## Read order (STEP 3c)

census -> H1 FR -> H1 FL -> H0 FR -> H0 FL -> relative-cap arm ->
reported items. Whatever is missing at the timebox makes the
verdict INCOMPLETE.
