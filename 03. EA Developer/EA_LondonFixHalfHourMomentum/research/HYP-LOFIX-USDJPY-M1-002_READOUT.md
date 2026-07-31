# HYP-LOFIX-USDJPY-M1-002 — TRAIN readout

Verdict: **KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED**

This is an engineering-valid, one-shot offline DESIGN/TRAIN result for the
frozen USDJPY London-local `08:00-08:30` sign predicting only the
`15:30-16:00` pre-fix half-hour. It is not an exact replication of any cited
paper and it is not a Strategy Tester result.

## Evidence integrity

- Frozen V2 plan SHA-256:
  `0E552F0BCAF792710EAA8E15C59640C3168F03B6160454DDB0F9862939BECC87`
- Authorized registry row SHA-256:
  `1D49E3AE947051DAE3CA0754B162F1E02E95AFF52DFE66CFDCE479144E82865B`
- Dataset parquet SHA-256:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`
- Attempt-started SHA-256:
  `48DA984AB10D704F6E8588E5FA5F642353D41FD5C61F4C7716F0B010407FAE04`
- Trade-ledger SHA-256:
  `04270A2E9772A884322753701D55B6101109B1BA1E49ABFF59F89B882815A6DB`
- Terminal SHA-256:
  `2472810502E2C468584EFA913CBC7926B362D5ADBDC3481A4E436002FE767B74`
- Diagnostic-chart SHA-256:
  `3E9BE9A7370217CF9BAFD4AAF8379EEFFBE043F118A0791910EC729EC68BD656`
- Focused tests: `11 passed` before and after the authority sentinel was armed.
- HYP001 predecessor consumed zero attempts and opened zero target outcomes; it
  was parked only to repair the armed-state sentinel test under this V2 ID.

The evaluator read 1,860,286 USDJPY DESIGN rows and created 1,283 complete
weekday trades. All five frozen source/cadence gates passed: 98.3896% eligible
weekday coverage, 4.915709 trades per elapsed calendar week, 611 LONG and 672
SHORT, and no year above 20.265% of the population. Validation 2021-2024 and
every 2025+ payload remained sealed. MT5, HCC, MQL5, Model 0/4, optimization,
network/paid requests, orders, paper and live counters remained zero/false.

## Frozen economic result

| Measure | Result | Gate |
|---|---:|---:|
| Gross PF | 0.960619 | diagnostic only |
| PF x1 / x1.5 / x2 | 0.594534 / 0.469438 / 0.372685 | >1.30 / >=1.25 / >=1.00 |
| Gross expectancy | -0.125721 pips/trade | diagnostic only |
| x1 expectancy | -1.625721 pips/trade | >0 |
| Positive x1 years | 0/5 | >=4/5 |
| One-sided permutation p | 0.645135 | <=0.05 |
| Four-arm DSR | 0.000000 | >=0.95 |
| Reverse-control PF x1 | 0.647909 | primary must beat |
| Economic gates | 0/8 | 8/8 |

Total primary gross result was `-161.3` pips. The fixed x1 cost added
`-1,924.5` pips, producing `-2,085.8` net pips. The signal is therefore already
slightly negative before cost, while the short holding horizon makes cost the
dominant net-loss component.

## Why it failed

1. **No opening-sign predictability in the target window.** Spearman correlation
   between signed opening formation and the raw pre-fix move was `-0.0135`;
   permutation p was `0.6451`. The signal is statistically indistinguishable
   from a shuffled sign.
2. **Cost overwhelms a near-flat gross distribution.** Gross PF was `0.9606`;
   subtracting 1.50 pips per trade reduced PF to `0.5945` and net win rate to
   40.37%.
3. **Failure is broad, not one isolated regime.** Every x1 year lost; annual x1
   PF ranged from `0.5047` to `0.8289`. No month passed PF 1.0 and every weekday
   was below PF 0.76.
4. **Opening-move magnitude is not a usable strength indicator.** All five
   predeclared diagnostic quintiles lost after x1 cost, with PF only
   `0.537-0.649`; absolute formation size versus gross return Spearman was
   `-0.0386`.
5. **Direction asymmetry is not a legal rescue.** LONG gross PF was `1.1424`
   but x1 PF only `0.7046`; SHORT gross PF was `0.8225` and x1 PF `0.5089`.
   A long-only rule would be outcome-mined and still fails economics.
6. **Tail removal cannot create the missing expectancy.** Bottom and top 1%
   x1 sums were `-567.9` and `+461.2` pips. The distribution and cumulative
   chart show persistent cost decay rather than one removable accident.

## Failure radius and next legal research direction

Killed object: completed-Bid USDJPY M1 DESIGN 2016-2020, Europe/London
`07:59→08:29` formation sign, same-direction `15:29→15:59` target, one complete
weekday trade, fixed 1.50/2.25/3.00-pip costs and the matched reverse control.

Forbidden under this ID: clock shift, direction flip, long-only, weekday/month/
year/BOJ/news/regime veto, formation-size threshold, RSI/EMA/ATR or another
indicator, cost reduction, stop/target retrofit, same-ID rerun, validation or
holdout access.

The broader workspace goal remains unmet. A legal successor must abandon the
seven-hour-old London-opening sign and use an independently anchored mechanism,
for example contemporaneous pre-fix inventory/flow pressure with a fresh
decision surface and preregistration. That idea is not authorized by this
readout and must be de-duplicated and frozen before any new target outcome is
read.
