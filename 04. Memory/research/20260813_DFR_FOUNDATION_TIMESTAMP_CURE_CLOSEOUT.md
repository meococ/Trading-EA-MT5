# DFR Foundation timestamp cure closeout — 2026-08-13

## Question and authority boundary

This outcome-blind audit asked only whether the local FiveAssetFoundation EURUSD
M5 timestamp plane cures the exact six-M15 horizon-coverage failure of terminal
`HYP-DFR-IC-EURUSD-M15-001`. It did not authorize a same-ID rerun, a child
hypothesis, prices, returns, trades, economics, MQL5, MT5, validation, holdout,
paper or live use.

## Bound evidence

- Frozen audit plan SHA256:
  `E3B715C25B87ECA88C4E0F98613534A2D1F9B20B526DBD2BDC69395649F27FD0`.
- Frozen parent classifications SHA256:
  `E5AF87FE704DBA1114C89D1422DD016DBFB25F41DA442B8786CF26216CAAE8AC`.
- FiveAssetFoundation EURUSD M5 parquet SHA256:
  `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8`.
- Auditor SHA256:
  `29E3E1907FF9930C41474C683CD4ECE96E1758B48A9A6230318FB776474A9A63`.
- Report SHA256:
  `F591C8264EC413982D4032DE40C8C373AC50EF0151D2D5F74D2CEED583BD0576`.
- Receipt SHA256:
  `682B196DC2D49889BE737B90B22F963D1DC108D8B121ADF742CED1326BD6A4CA`.

The first attempted execution failed before any parquet row was read because the
classification SHA had been transcribed incorrectly in the audit bindings. The
binding was corrected before source access, the plan was re-hashed, four focused
tests passed, and the single bound metadata audit then executed.

## Capability result

`PASS_INDEPENDENT_TIMESTAMP_CURE_EVIDENCE_ONLY`

- Exact frozen signal population: `1,235`.
- Foundation six-M15 horizon complete: `1,233`; incomplete: `2`.
- Coverage: `99.8380566802%`, above the frozen `99%` capability threshold.
- Old source-executable signals retained: `1,220 / 1,220 = 100%`.
- Old incomplete signals recovered: `13 / 15`; still incomplete: `2`.
- Parquet access was limited to `symbol`, `timeframe`, `time_utc` and
  `utc_ambiguous`.
- Post-entry OHLC rows, price columns, returns, trades, PnL, PF, validation,
  holdout, MQL5 and MT5 counters were all exactly zero.

This proves an independent timestamp-data cure. It is not evidence of edge.

## Causal and de-dup decision

`REJECT_DFR_CURE_SUCCESSOR__CAPABILITY_PASS_BUT_INFORMATION_SET_DUPLICATE`

The exact DFR object uses only the completed-bar return sign and magnitude,
ATR14, a same-UTC-slot absolute-return scale, hours `01..20 UTC` and a
first-hit-per-day clock. Its trade thesis is therefore a session-windowed,
volatility-standardized large-bar continuation with a matched fade control.
The new timestamp plane changes none of those fields, the decision clock or the
direction map. It cures the parent data boundary but does not create a distinct
market mechanism outside the already closed raw/session momentum, large-bar
jump continuation/fade and diurnal/session-clock neighborhoods.

Grok Build independently returned `B) REJECT_DFR_CURE_SUCCESSOR` on the same
information-set/decision-clock grounds. That response is advisory; the Lead
verdict above is based on the frozen local mechanism and evidence hashes.

## Failure radius and next action

Do not open a DFR child, run outcomes or build an EA from this cure. The terminal
parent remains terminal, while the Foundation timestamp capability remains a
reusable source fact for a materially different future mechanism. The overall
XAU/Forex EA goal remains `ACTIVE / UNMET`; continue at the local database
frontier and require a genuinely new information set before a hypothesis ID.
