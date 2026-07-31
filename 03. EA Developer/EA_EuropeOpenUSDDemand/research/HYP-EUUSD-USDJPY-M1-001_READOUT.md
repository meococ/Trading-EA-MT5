# HYP-EUUSD-USDJPY-M1-001 — TRAIN readout

## Verdict

`KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`

The one-shot DESIGN/TRAIN proxy is engineering-valid but economically invalid.
All 5 structural gates passed and only 1 of 8 economic survivor gates passed.
No MQL5, Model 0, optimization, validation, holdout, promotion, paper, or live
authority is opened.

## Frozen object

- USDJPY completed-Bid M1 close-only source, 2016-2020 DESIGN
- Europe/Berlin timezone with DST
- Fixed LONG USDJPY from completed `07:59` close (entry at `08:00`) to completed
  `14:14` close (exit at the `14:15` ECB-fix boundary)
- One trade per complete weekday
- Fixed round-trip cost proxies: 1.50 / 2.25 / 3.00 pips
- Matched exact-date reverse control
- Six x1 trial arms for DSR

This is the preregistered translation of the pre-ECB unconditional USD-demand
mechanism in Krohn, Mueller and Whelan, not a post-outcome clock search. The
working paper is available at
`https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf` and the
published DOI is `10.1111/jofi.13306`.

## Engineering and coverage

| Check | Result |
|---|---:|
| Complete trades | 1,296 |
| Weekday coverage | 99.3865% |
| Trades per elapsed calendar week | 4.965517 |
| Largest year share | 20.0617% |
| Exact fixed-long boundary contract | PASS |
| Structural gates | 5 / 5 |

The source manifest, parquet, preregistration, evaluator, test, prior ledgers,
helper, DSR module, authority row, attempt-start marker, trade ledger and
terminal result are SHA-bound. Validation 2021-2024 and every 2025+ payload
remain sealed.

## Economics

| Metric | Gross | x1 cost | x1.5 cost | x2 cost |
|---|---:|---:|---:|---:|
| Primary PF | 1.051219 | 0.887604 | 0.815747 | 0.749906 |
| Primary expectancy, pips/trade | +0.442747 | -1.057253 | -1.807253 | -2.557253 |

- Primary total: `+573.8` gross pips versus `-1,370.2` pips at x1 cost.
- Reverse control x1 PF: `0.803155`; primary beat the reverse control, but both
  lost after costs.
- Positive x1 years: `1/5`; only 2017 was positive.
- One-sided random-sign p-value: `0.282672`.
- Six-arm DSR: `0.000008`.
- Economic survivor gates: `1/8` (only the matched reverse comparison passed).

Annual x1 net pips were `-196.2`, `+302.2`, `-560.6`, `-343.8`, and `-571.8`
from 2016 through 2020. No weekday reached the PF `1.30` target after x1 cost;
Tuesday was merely near flat at PF `1.020552`, while Friday was weakest at PF
`0.681225`. These diagnostics are explanatory only and do not authorize a
weekday or month filter.

## Why it failed

The literature-shaped direction was better than its reverse, so the sign was
not arbitrary. The effect size was nevertheless too small and unstable:

1. Gross expectancy was only `+0.442747` pip per trade, while the frozen x1
   round-trip cost was `1.50` pips—about `3.39x` the mean gross drift.
2. Even at an impossible zero-cost assumption, gross PF was only `1.051219`,
   far below the Owner target `>1.30`.
3. Four of five years lost after x1 cost, the sign-flip test was not
   significant, and DSR was effectively zero after the six declared trials.
4. Tail contribution was roughly symmetric: the worst 1% contributed
   `-1,536.4` x1 pips while the best 1% contributed `+1,336.0`; there is no
   hidden stable core that warrants a same-ID rescue.

The correct diagnosis is not “all fix-related FX effects are false.” It is that
this single-pair USDJPY close-only implementation does not have enough gross
edge to survive the required retail-cost proxy.

## Failure radius and next legal work

Killed exactly: USDJPY, 2016-2020 FivePercent completed-Bid M1 close proxy,
Europe/Berlin `07:59` to `14:14`, always long, one complete weekday trade,
unfiltered, with fixed 1.50/2.25/3.00-pip costs and the matched reverse control.

Forbidden rescue under this ID: moving either clock, selecting 2017, Tuesday,
July/November or another post-outcome bucket, lowering costs, flipping the rule,
adding an indicator, stop, target, or accessing validation/holdout.

A legal next hypothesis must change a material mechanism or data/decision
surface. The primary paper reports a materially larger pre-ECB effect for EUR
than JPY; a fresh **short EURUSD** pre-ECB hypothesis is therefore a separate,
source-ranked symbol contract—not a tuned USDJPY rescue. It must receive its own
ID, preregistration, trial accounting, one-shot TRAIN probe and costs.

## Bound evidence

- Plan SHA256: `6C53F996D8DBDD7108AC2E9F08A2545F1036F463D612CF458CB54CEE61571797`
- Armed evaluator SHA256: `A8E8E61A8D75E9D95808A637E3E876A627DDBC8906EDF94743A79F1DCF691A63`
- Test SHA256: `FD14D6BF372ECC3621F49A06BD9101596D7DA5CEA7953DB61865EC3C8CAABD6F`
- Authority row SHA256: `C4F6E101A3CE3079F015582D7EF6B40266B78F48B467775C1FF08FDBB4DFA0CA`
- Attempt-start SHA256: `65E32D825CED28820F764E4AA9170A5783668DFBD94780AB553F18320ECFB88E`
- Trade ledger SHA256: `18D8C2333FE421DFA279325D30A29D759AAD4333A304BA1FC68E7B485009E10C`
- Terminal SHA256: `DBC820035700BA2C8AFC9175BAE4A3C63165A68FF77FA8C9BF2D9180FD2CD335`
- Diagnostic chart SHA256: `DBDC019929ED8CCC44ADB9F589255AB5CAAE67E56C76B293AD81D92578A90FF1`
