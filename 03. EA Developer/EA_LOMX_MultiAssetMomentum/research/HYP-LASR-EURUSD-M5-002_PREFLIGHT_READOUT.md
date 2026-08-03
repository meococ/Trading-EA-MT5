# HYP-LASR-EURUSD-M5-002 - Pre-EA Account Contract Readout

## Verdict

`PARK_PRE_EA_INVALID_ACCOUNT_DEPOSIT_STOPOUT_CONTRACT_NO_OUTCOME`

No Model-0 execution was launched and no performance outcome was read.

## Read-only FivePercent account probe

The probe initialized the same portable FivePercent terminal, selected EURUSD,
read account/symbol geometry and called `order_calc_margin` only. It sent zero
orders.

| Field | Observed |
|---|---:|
| Account leverage | `1:100` |
| `margin_so_mode` | `1` (`MONEY`) |
| Margin-call threshold | `$92,000` |
| Stop-out threshold | `$90,000` |
| Live account equity (identity context only) | `$98,390.92` |
| EURUSD one-lot margin at probe price `1.15400` | `$1,154` |
| Frozen tester deposit | `$10,000` |
| Orders sent | `0` |

The frozen `$10,000` tester deposit is already `$80,000` below the broker's
absolute stop-out threshold before any order exists. A correct fail-closed
margin cap therefore has zero legal capacity and would reject every signal.
Running Model 0 would consume a trial only to produce a deterministic zero-trade
infrastructure result, so execution is forbidden.

## Successor route

The next legal identity must:

1. use a `$100,000` tester deposit matching the FivePercent account class;
2. preserve free margin above the larger of margin call and stop-out, plus a
   reserve derived from remaining headroom rather than multiplying the absolute
   currency threshold;
3. keep signal, session, thresholds, direction, risk percent, stop and targets
   unchanged;
4. freeze a new source/prereg/task/registry identity before any outcome read;
5. retain `promotion_eligible=false` because commission and slippage remain
   research proxies.

Same-ID execution or repair is forbidden after this preregistered account
contract proved infeasible.
