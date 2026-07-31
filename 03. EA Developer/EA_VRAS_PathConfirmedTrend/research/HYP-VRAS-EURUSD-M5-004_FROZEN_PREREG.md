# Frozen preregistration — HYP-VRAS-EURUSD-M5-004

Status: FROZEN PRE-OUTCOME on 2026-07-22.

## Hypothesis

The terminal HYP-003 chart census showed that winners and losers share the same
static TREND entry fingerprint, while realized outcome depends on immediate
post-setup directional continuity. HYP-004 tests one materially new causal
mechanism: delay only a valid TREND setup until exactly the next closed M5 bar
confirms continuation. This is a new hypothesis and package; HYP-003 remains
byte-identical, terminal KILL and may not be rerun or rescued.

## Frozen arms

Both arms use one canonical source, EURUSD M5, Model 0, `2023.01.03` through
`2026.06.30`, deposit USD 100,000, leverage 1:100, current tester spread,
tick-volume London-open VWAP, and identical signal/risk/execution settings.

- `CONTROL_IMMEDIATE_TREND`: `InpUsePathConfirmation=false`. It executes the
  inherited immediate RANGE and TREND logic under HYP-004 identity.
- `CHALLENGER_PATH_CONFIRM`: `InpUsePathConfirmation=true`. RANGE remains
  immediate and unchanged. TREND uses the frozen confirmation contract below.

The two runs are serial and matched. The only arm difference is
`InpUsePathConfirmation` plus the descriptive `InpVariantTag`.

## Frozen TREND confirmation contract

1. A raw TREND setup is the inherited HYP-003 closed-bar setup: regime TREND,
   session-VWAP pullback/rejection, confirmed five-bar AVWAP, and last fully
   closed M15 close/VWAP direction agreement.
2. The raw setup opens no order. It arms one pending candidate for exactly the
   next newly closed M5 bar. Pending candidates do not survive restart.
3. Long confirmation requires: regime still TREND; confirmation close strictly
   above the raw setup high; confirmation close above the current session VWAP
   and current AVWAP computed from the frozen setup anchor; current closed M15
   close strictly above current M15 session VWAP. Short is the exact mirror.
4. Any missing data, non-adjacent bar, regime mismatch, failed extreme break,
   failed VWAP/AVWAP/M15 direction, or exposure/guard failure rejects the
   pending candidate. No later bar can revive it.
5. The raw setup stop is frozen. Entry is the quote at the next bar after the
   confirmation close; TP remains 1.80R from actual entry to the frozen stop.
6. After resolving a pending candidate, the same newly closed bar may arm a
   fresh raw TREND setup for the following bar. At most one candidate is held.

## Matched constants

ADX14 enter/exit/dwell `25/19/6`; ATR14; RSI14; warmup `15`; SD floor
`0.30 ATR`; RANGE `2SD`, RSI `25/75`, stop `0.30 ATR or 2.50 SD`, target session
VWAP; TREND stop `0.40 ATR` beyond raw setup extreme and target `1.80R`; AVWAP
lookback `60`; M15 bias on; risk `0.25%`; spread cap `1.20 pip`; diagnostic
commission `0.70 pip`; diagnostic one-way slippage `0.40 pip`; cost-distance
`K=8`; max 3 trades/day; daily loss `1.50%`; account DD `6%`; max hold `20`
M5 bars; broker winter UTC+2 following US DST.

`InpRequireNewsGuard=false` is matched in both arms because the package-bound
calendar ends in 2022. This makes all economics diagnostic and
`promotion_eligible=false`; it is not a claim that news risk equals zero.

## Acceptance and stop rules

Engineering before either run: red-first tests green, compile `0/0`, exact
source/include hashes captured, closed-bar/non-repaint audit with zero findings,
and HYP-004 identity/variant fail-closed checks.

The challenger must pass all absolute workspace gates: at least 350 trades,
2–5 trades per elapsed calendar week, PF >=1.30, positive expectancy, max DD
<=6%, cost stress x1.5 PF >=1.25 and x2 PF >=1.00. It must also show a
predeclared mechanism lift over the matched control: PF improvement >=0.15,
mean realized-R improvement >=0.10R, and stop-exit share reduction >=10
percentage points. Failure at any necessary gate kills HYP-004. Improvement on
reused HYP-003 years is not tested and cannot count.

Exactly one control and one challenger Model-0 run are authorized. No optimizer,
threshold search, alternate confirmation delay, session/year/direction veto,
stop/target change, branch deletion, sensitivity rescue, live or paper attach.

## Why Model 0 follows directly

An offline replica would need to reproduce the stateful AVWAP anchor, MT5 ADX,
broker clock, next-bar quote, cost gate, account guards and lifecycle semantics.
For this one-bar mechanism, a matched fresh-window Model-0 pair is the cheapest
faithful falsification. This explicit exception avoids a parallel approximate
toolchain; it does not relax the preregistration or run limits.
