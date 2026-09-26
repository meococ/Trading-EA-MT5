# Lead review of LINE-1 v0 snapshots (2026-09-20 19:03 VN) - input for PA-PRO perception v1

Reviewed by the Lead (visual, 4 snapshots): ab_case_025, ab_case_012, random_20201015_351031, random_20160205_6897.

## What works (keep)
- Session highs/lows are drawn and are often THE relevant ceiling/floor (case_012: SESS-H above the buildup).
- Swing-cluster levels with role flip are real pro lines (case_012: LEVEL 1.1375 was resistance, then support).
- Box (range) and triangle detection produce shapes a pro would draw (random 2020-10-15).
- Flag/pennant after an impulse (case_025) and a falling wedge (2016-02-05) are captured.

## What must be fixed in perception v1 (binding for R01)
1. MERGE near-duplicates: horizontal lines closer than 0.25 x ATR14(H1) become ONE zone (keep max score, zone = span of members, touches = union). Seen: two LEVEL lines 1.1873/1.1872 (case_025); LEVELs next to BOX-B (2020-10-15).
2. SESSION LEVELS: label current vs previous session explicitly (SESS-H today / SESS-H prev); never two unlabeled SESS-H lines (case_012).
3. RELEVANCE: only lines within +-2 x ATR14(H1) of the current close are ARMED; others stay in memory but are not drawn/armed. Round numbers: only the nearest 00/50 above and below price (2016-02-05 drew 1.1150 and 1.1100 far away and missed 1.1200 in the middle of the action).
4. TRENDLINES: >= 3 touches within tolerance, no candle BODY closing through between first and last touch, at most 2 per direction, drop lines that run away from price (2020-10-15 TREND 0.72) or cut through recent bodies (case_012 TREND 0.80).
5. SCORES: v0 scores sit in 0.55-0.80 for everything (no discrimination). Keep v0 weights frozen for the physics prereg; calibration happens only after the preregistered physics run, and every calibration is a ledger trial.
