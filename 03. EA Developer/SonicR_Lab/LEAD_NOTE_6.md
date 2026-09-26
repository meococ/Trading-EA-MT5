# LEAD NOTE 6 - E0 narrowed to malformed records (Lead, 24/09 00:40Z)

Frozen by the Lead BEFORE any rerun with it. Record this file's sha256 in LAB_LOG before the first E0' output.

## Why LEAD_NOTE_5's E0 is withdrawn
The price-based E0 (>3% and back within 0.5% in 15 minutes) was mis-calibrated by the Lead. Devin's scan (00:25Z)
correctly stopped on both safety conditions: 238 flagged bars, XAUUSD 50 and AUDJPY 33 in DESIGN, and real events
flagged (SNB 2015-01-15, GBP flash 2016-10-07, JPY flash 2019-01-03, gold 2021-08-09, NZD 2015-08-24, and other
session-open bars). A rule that voids real flash crashes is optimistic and is not used. It stays in the record as a
reported sensitivity cell only, labelled "voids real events - not valid".

## E0' (applies to H0 and H1, every symbol, every window)
An M1 bar whose timestamp is not aligned to a whole minute (non-zero seconds) is a malformed record, not an M1 bar
of the normal aggregation. Such bars are void for fills, SL, TP and flatten exactly as E1 voids suspect bars.
This rule is format-based: it uses no price and no future information, and it cannot touch a real market event
recorded as a normal M1 bar. It was already listed in LEAD_NOTE_5 as a pre-declared sensitivity variant.
Population it covers (Devin's inventory, E0_BARS.md): the 14 second-stamped bars on garbage price ladders
(0.42656 / 0.68080 / 2.65536 ...), including both prints that decided V1 (2020-05-07 12:33:04 -810R and
2022-10-19 13:47:44 +57.7R) and the near-miss 2019-12-01 18:01:36 that the price rule missed.
Everything else (the ~216 session-open / rollover wicks) stays tradable on H0: whether those are real quotes is the
open round-3 question, and H0 exists to bracket it.

## Status
Unchanged from LEAD_NOTE_5: the corrected V1-V3 are PROVISIONAL (VALIDATION has been read); promotion only via the
sealed HOLDOUT with E0' frozen and no later fix.
