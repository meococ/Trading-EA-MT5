# HYP-EURFXREV-EURUSD-M1-001 - TRAIN readout

## Verdict

`KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`

The post-ECB-fix pressure-reversal proxy is engineering-valid and economically
invalid. All 5 structural gates passed; only 1 of 8 economic gates passed. No
MQL5, Model 0, validation, holdout, optimization, promotion, paper or live
authority is granted.

## Fresh object tested

Krohn, Mueller and Whelan document USD appreciation before institutional fixes
and depreciation after them, with dealers later trading away inventory built
around client imbalances. This probe opened a new post-fix target that had not
been read by the earlier pre-fix/VIX family:

- EURUSD completed-Bid M1, DESIGN/TRAIN 2016-2020 only
- Europe/Berlin pre-fix pressure: completed `07:59` to `14:14` closes
- strict-lag eligibility: absolute pressure at or above the median of the prior
  60 complete weekdays, excluding current, minimum 40 observations
- entry at completed `14:14` close; exit at completed `15:59` close
- direction opposite the pre-fix pressure; matched continuation control
- costs 1.50 / 2.25 / 3.00 pips; 12 x1 DSR arms

The rule and gates were frozen before any post-14:15 target return was read.
Validation 2021-2024 and every 2025+ payload remained sealed.

## Engineering and economics

| Check | Result |
|---|---:|
| Selected trades | 612 |
| Cadence per elapsed calendar week | 2.344828 |
| LONG / SHORT share | 53.43% / 46.57% |
| Largest year share | 22.06% |
| Structural gates | 5 / 5 |

| Metric | Gross | x1 | x1.5 | x2 |
|---|---:|---:|---:|---:|
| Primary PF | 1.110752 | 0.845237 | 0.737469 | 0.643462 |
| Expectancy, pips/trade | +0.577288 | -0.922712 | -1.672712 | -2.422712 |

- Total: `+353.3` gross pips, `-564.7` x1 net pips.
- Matched continuation-control x1 PF: `0.686501`.
- Positive x1 years: `1/5`.
- Random-sign p-value: `0.180382`.
- Twelve-arm DSR: `0.000121`.
- Economic gates: `1/8`; only the matched-control comparison passed.

Annual x1 PF was `0.7955, 0.6208, 1.1020, 0.7692, 0.9262` for 2016-2020.
The chart shows a positive but unstable gross path that becomes persistent decay
after the frozen 1.5-pip cost. Absolute pre-fix pressure has only `0.0549`
Spearman correlation with the post-fix reversal outcome, so the contemporaneous
pressure magnitude does not provide useful ranking power on this contract.

Direction anatomy is also contradictory rather than actionable: pressure-
reversal SHORT trades had x1 PF `1.1350`, while LONG trades had x1 PF `0.6597`.
Choosing only the favorable direction now would be an outcome-derived rescue
and is forbidden; it also conflicts with the source's unconditional post-fix
USD-depreciation interpretation.

## Failure radius and next decision

Killed exactly: EURUSD completed-Bid M1 2016-2020, post-ECB-fix `14:14` to
`15:59` target, reverse of pre-fix `07:59` to `14:14` pressure, selected by the
strict-lag prior-60 median absolute-pressure rule with minimum 40, fixed costs
and matched continuation control.

Forbidden rescue: direction-only selection, another pressure threshold or
lookback, magnitude/weekday/month/year bucket, clock shift, cost reduction,
stop/target, validation/holdout access or same-ID rerun.

This kill closes only this post-fix pressure-reversal translation. It does not
complete the Owner goal. The combined evidence now says price-only clock and
lagged-VIX proxies can show small gross drift but do not supply enough
discrimination or gross opportunity to survive retail execution costs. The
next candidate must use a materially different alpha source, preferably
contemporaneous dealer/order-book imbalance or a mechanism with a much larger
gross move per paid round trip.

## Bound evidence

- Plan SHA256: `8F62C3A5FB9C944EFF96C68904C7CFB57F84752C2455805538D84F352DAE8833`
- Armed evaluator SHA256: `FBEA4DA174E9943069470D5C96DAA5086F72EC028D644E19C701FB00374F74C6`
- Test SHA256: `D87601BAF397E3B8FDC6A30383F2E776F5E89F6619CEB5732D836BF96B4F2741`
- Authority row SHA256: `BB5B8C2198B7892A857D67AF8D28E42BDB7C77154C851A74F17AC2AA78541404`
- Attempt-start SHA256: `1348DC636DD6205CEEE1F01B4724F0C81ECECBC497B936C43457C2C552C4F470`
- Trade ledger SHA256: `952E193FFC65D91B43E7F55EE970A65E904B2E9DD50A5E6469B9659EDFC28E45`
- Terminal SHA256: `8393300AEED35F0B58E4135581B7F1E8E16A03FBEF3B864C68B7BA0F689FB945`
- Chart SHA256: `F18933024C7959EDDC02FD61787178387009492B773D7C5CEF36D5B6F5151651`
