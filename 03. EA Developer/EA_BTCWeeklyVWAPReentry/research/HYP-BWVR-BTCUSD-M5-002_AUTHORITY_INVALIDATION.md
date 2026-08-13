# HYP-BWVR-BTCUSD-M5-002 — authority invalidation

Verdict: `INVALID_AUTHORITY_BOUNDARY_RESULT_NOT_ADMISSIBLE`

## Why the result is invalid

HYP002 kept the exact HYP001 weekly-AVWAP market formula and changed the
minimum DESIGN-row gate from `400000` to `220000`. HYP001's frozen failure
closeout explicitly prohibited lowering that floor or retrying the same source
mapping. A fresh hypothesis ID did not supersede that prohibition.

The read-only pre-source reviewer identified this conflict, but the source
attempt was executed before the review verdict was received. That was a Main
Agent process error. The resulting report is mechanically reproducible but is
not admissible evidence for source feasibility, strategy selection, economics
or any future rescue of weekly AVWAP.

## Preserved artifacts

The consumed attempt is retained for auditability and must not be deleted or
rewritten:

- attempt ID: `BWVR002-SOURCE-001`
- attempt-start SHA256:
  `626A4E34DB778E378DDC15A62B399CE1EFC14008B9BB209EDF366D3EB1EF36A7`
- report SHA256:
  `3F60E1DB79CCAA1DB0CA4662BB8243DE99041D91AAE1D4F0AD81347637407D84`
- ledger SHA256:
  `03B2C2E778DDF3B467C23179DF6B0BCACE6E11F7B47BE8AAB24E1F2BCC35C08B`
- receipt SHA256:
  `10799E4A1ECCF89029DAC55970581A2866F8B06243956FCE2CC284F0F16E586C`
- terminal SHA256:
  `BDCBBCEFB488510EF4936DDD4B4DAE93A4BB009F07D1F6F93E1C1A8F83DD11E7`

For disclosure only, the inadmissible report recorded `1,073` executable
events and `4.1134/week`, but failed UTC/exact-next coverage, annual cadence
and year concentration. These observations cannot authorize a revision,
parameter change, build or economic run.

## Failure radius and next action

This invalidates only HYP002 and the attempt to bypass HYP001's frozen row-floor
prohibition. It is not an economic verdict on weekly AVWAP and not evidence
that paid data is required.

Do not create another BWVR revision, lower or replace the source gates, change
clock/session/cooldown rules, or use the inadmissible readout to select a
variant. The next lane must use a materially different information mechanism
and native MT5 demo/FivePercent/The5ers data already available.

