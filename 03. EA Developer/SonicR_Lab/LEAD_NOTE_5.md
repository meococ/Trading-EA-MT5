# LEAD NOTE 5 - E0: impossible prints are void in EVERY harness (Lead, 24/09 00:12Z)

Frozen by the Lead BEFORE any E0 rerun exists. Record this file's sha256 in LAB_LOG before the first E0 output.

## What happened
Round 2F's VALIDATION read (23:54Z) failed V1 on H0 only. The Lead traced it: one EURUSD AM trade (short, fill
2020-05-04 14:14 server, entry 1.09287, SL 1.094798) exited "sl" at 2.655360 on 2020-05-07 12:33:04, R = -810.4.
EURUSD never traded at 2.655. It is a bogus print in the M1 data (flagged suspect; bar time has seconds, like the
two bogus Sunday bars found in 2E at 0.42 / 2.65). H0 keeps suspect bars tradable, so the sim filled a stop at an
impossible price. The Lead's first quick look ("1.63 without that trade") was one-sided: a neutral reviewer found a
bogus WINNER in the same file too (2022-10-19 13:47:44, TP filled at 0.6808, 31% off-market, +57.7R). Removing
both gives EURUSD AM H0 PF_R about 1.34; replacing them by their H1 outcomes about 1.37 (H1: 1.42). Bogus prints cut
both ways; E0 must remove both kinds, and the report must show both.
H0 exists to bracket one open question: are the ROLLOVER-window spikes real, tradable quotes? It was never meant to
let an off-market print 143% away from the market execute. This is a data-validity bug in the harness, found after
the read, in the direction that hurt the hypothesis.

## E0 rule (applies to H0 and H1, every symbol, every window; thresholds fixed here, not tuned)
An M1 bar i is an IMPOSSIBLE PRINT if both hold:
  (a) max(|high_i / ref_i - 1|, |low_i / ref_i - 1|) > 3%, where ref_i = close of the last bar before i that is
      not itself an impossible print;
  (b) the close of the first bar at or after (bar i time + 15 minutes) is within 0.5% of ref_i (the price came back:
      not a real repricing).
Impossible prints are void for fills, SL, TP and flatten exactly as E1 voids suspect bars (skip; first clean bar
rules). Nothing else changes: suspect ROLLOVER bars stay tradable on H0 (they are far below 3%), so E0 does not
erase the H0/H1 distinction.
Why these numbers: a real 1-minute FX/gold move of more than 3% that fully reverts within 15 minutes does not
happen outside flash events; the print that caused the failure was 143% away. Real events that did NOT revert
(SNB 2015-01-15) are untouched by (b). Every flagged bar is listed so the reviewer can check none is a real event
(check explicitly: SNB 2015-01-15, GBP flash 2016-10-07, JPY flash 2019-01-03, gold 2013-04-15, gold March 2020,
gold flash 2021-08-09). Also report flagged bars inside vs outside the rollover windows.

## Status of the corrected verdict (stated BEFORE the rerun)
VALIDATION has been read and its outcome is now effectively known, so the E0-corrected V1-V3 are PROVISIONAL: they
can only say whether the failure was the data bug; they cannot confirm the idea. Promotion needs a pass on the
sealed HOLDOUT with E0 frozen (this note), V1-V3 unchanged, and no fix of any kind after HOLDOUT is opened.
E0 is a history-cleaning rule: it uses the price 15 minutes later, which a live EA cannot know; a real flash move
that reverts would hit live stops, so voiding it would be optimistic. Hence the event checklist and the listing.

## Sensitivity (required, reporting)
Re-apply V1-V3 for E0 thresholds {1%, 2%, 3%, 5%} x revert windows {5, 15, 60 minutes}, plus a variant that voids
only second-stamped bars. The provisional verdict is reported for every cell; if it changes anywhere, say so. List
every trade beyond +/-5R before and after E0, in DESIGN and VALIDATION, both harnesses.

## What must be reported
- Every flagged bar: symbol, time, OHLC, ref, deviation, the close 15 minutes later; count per symbol and window.
- Every trade whose outcome changes, in DESIGN and VALIDATION, H0 and H1: before/after R, and whether the change
  helps or hurts the tested idea (the fix must not be one-sided by construction).
- The frozen 2F rules (K1-K3, V1-V3) re-applied once on the E0-corrected data, side by side with the first
  computation. The first computation stays in RESULTS_v6 as it is; the corrected one is a new section.
