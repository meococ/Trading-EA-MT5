# HYP-EUVIX-EURUSD-M1-002 — TRAIN readout

## Verdict

`KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`

The corrected V2 is engineering-valid and economically invalid. All 5
structural gates passed; only 1 of 8 economic gates passed. The lagged-VIX state
does not authorize MQL5, Model 0, validation, holdout, optimization, promotion,
paper, or live.

## V1 engineering boundary

`HYP-EUVIX-EURUSD-M1-001` stopped before VIX was joined to PnL because V1
confused `1,328` raw FRED rows with `1,281` valid numeric closes. V1 produced
only an attempt marker and engineering-abort receipt: zero selected conditional
trades, zero conditional outcomes and no metric. V2 bound the same CSV bytes,
corrected the contract to raw=`1,328`, valid=`1,281`, missing=`47`, and changed
no feature or trading rule.

## Frozen V2 object

- Parent: fixed SHORT EURUSD, Europe/Berlin completed `07:59` to `14:14`
- State: last valid VIX close strictly before trade date is at or above the
  median of the prior 252 valid closes, excluding itself, minimum 60
- Costs: 1.50 / 2.25 / 3.00 pips
- Controls: matched reverse and unfiltered-parent benchmark
- Ten x1 DSR arms; 10,000 random-sign permutations

FRED describes VIXCLS as the CBOE VIX daily close. The primary mechanism paper,
Krohn, Mueller and Whelan (DOI `10.1111/jofi.13306`), links higher fix reversal
returns to higher lagged VIX/intermediary constraints.

## Engineering and economics

| Check | Result |
|---|---:|
| Selected trades | 592 |
| VIX mapping coverage | 100% |
| Cadence per elapsed calendar week | 2.268199 |
| Minimum trades in a year | 34 |
| Largest year share | 37.8378% |
| Structural gates | 5 / 5 |

| Metric | Gross | x1 | x1.5 | x2 |
|---|---:|---:|---:|---:|
| Primary PF | 1.127809 | 0.976592 | 0.908987 | 0.846174 |
| Expectancy, pips/trade | +1.252703 | -0.247297 | -0.997297 | -1.747297 |

- Total: `+741.6` gross pips, `-146.4` x1 net pips.
- Reverse x1 PF: `0.767323`.
- Positive x1 years: `2/5`.
- Random-sign p-value: `0.145385`.
- Ten-arm DSR: `0.009159`.
- Economic gates: `1/8`; only the combined reverse/unfiltered-parent comparison
  passed.

The filter improved parent x1 PF only from `0.968723` to `0.976592`, and x1
expectancy only from `-0.298688` to `-0.247297` pips. That is a small lift, not
a route to the Owner target `>1.30`.

Annual selected trade counts were `34, 34, 224, 102, 198`; x1 PF was `1.2755,
0.6076, 0.9883, 0.9091, 1.0026`. Thus the effect was concentrated and unstable.
VIX excess over its trailing median had only `0.0552` Spearman correlation with
daily gross PnL. The best/worst 1% contributed `+711.5/-525.4` x1 pips, but this
tail anatomy is not a license to add a stop or winsorization.

## Failure radius and decision

Killed exactly: the fixed parent EURUSD trade selected by the strict-lag
adaptive high-VIX state above, 2016-2020, VIX snapshot/manifest V2 hashes,
unfiltered costs 1.50/2.25/3.00 pips, matched reverse and parent control.

Forbidden rescue: another VIX threshold/lookback/operator, VIX-excess sizing,
weekday/month/year filtering, clock shifts, cost reduction, stop/target,
validation/holdout access, or same-ID rerun.

This closes the **unconditional/lagged-VIX Europe-open-to-ECB-fix seasonal
family on this retail close-only contract**, not the full FX research goal.
Further progress toward PF 1.30 needs a materially new alpha source that changes
the information set—not another calendar or VIX threshold. Candidate directions
include contemporaneous dealer-flow/order-book data or a different intraday
mechanism with larger gross opportunity per paid round trip.

## Bound evidence

- Plan SHA256: `26CB850427719016E61AA73C1AC673A602E34FF7AE7510387A4398E5C087FAE6`
- Armed evaluator SHA256: `D5FAD38CD39D47158DA4FECEA86E5167E3590D7516F3A53A1CDFC216CABC5493`
- Test SHA256: `EBBB83375117F30A43164D1AB6A2DB3868C0C0C8B977CA9FD3E5069DD0D6B822`
- Authority row SHA256: `1A88694B96C67AD9FB472EF204F295C8C5B342B83754A9EEB535291D2C839368`
- Attempt-start SHA256: `9569C38FC415E20C3551A5F5CAC673E21ACF174EBEB5F4293F45E04805E1F341`
- Trade ledger SHA256: `B2C9CA21F80F307BDBCB9B8DFE34D4477D3B7CFF78B164823D6810563EA66F1E`
- Terminal SHA256: `BE7D3985DC11A0FD472B3676A5F4DD790B51EA83E6D7CF997B9341656747144C`
- Chart SHA256: `F164612271170A2EF8151FB38FB9BA8E16231EBBEBF3A1B47F3C4B9D72346D46`
