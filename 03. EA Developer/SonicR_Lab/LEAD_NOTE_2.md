# LEAD NOTE 2 - J-parity: the run window is unrecoverable; change the parity test (Lead, 23/09 16:20Z)

PREREG section 6 assumes the 16/08 run covered 2000-01-03..2026-08-14 and scales N to 270. The Lead searched for the
real window and it is gone: no row for run 20260816_205426 / HYP-SONICR-CLASSIC-EURUSD-M15-001 in
CANDIDATE_REGISTRY.jsonl or CANDIDATE_REGISTRY.era1.archive.jsonl; 02. AlphaFactory/runs.db was pruned (65 rows,
none from 16/08); STRATEGY_LOG.md, do_not_repeat_failures.md, hot.md and source_of_truth.md do not record it.
Your own smoke count (F0_J about 116 signals/year) also makes a 26-year window with N=307 implausible - the run was
probably a short window (possibly inside our sealed HOLDOUT). So an N-based parity cannot be judged honestly.

Apply this as an ERRATUM (record it in RESULTS.md "Errata" and in PARITY_J.md; do NOT edit PREREG.md or its hash):
1. F0_J stays exactly as coded in the 16/08 build (sr.blocked = telemetry, no W2 gate). Do NOT run the "w2='whq'
   alternative interpretation" to chase N: the build treated S/R as telemetry, and fitting the spec to hit a count
   would be the wrong kind of parity.
2. Parity criterion replaced by: (a) PF of F0_J on the J-PARITY window within 0.94 +/- 0.15 (0.79-1.09) at cost x1;
   (b) report trades/year and state which window lengths would give N=307 at that density; (c) spot-check 10 F0_J
   trades by hand against bars (entry, SL, TP, exit) - this is the real harness check in this round.
   If (a) fails, investigate spec/cost/data before the ladder, as the brief says.
3. Never load HOLDOUT to "find" the J window.
4. The decisive harness validation happens in round 3: MT5 Strategy Tester trade-by-trade parity with your Python
   trade list. Make the trade list export for F0_J and every advancing config exact enough for that (ticket-level
   fields: signal bar time, pending price, fill time/price, SL, TP, exit time/price/reason).
