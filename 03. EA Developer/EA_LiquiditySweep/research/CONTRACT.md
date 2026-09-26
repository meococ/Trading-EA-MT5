# CONTRACT — Liquidity Sweep Reversion (LSW)

**Status:** FROZEN 2026-08-31, before any backtest was run on this package.
**Authority chain:** Owner request → `01. GOAL/GOAL.md` (as amended 2026-08-31) →
this contract → verified artifacts. Written per `05. Playbook/WORKFLOW.md` §2.

Nothing in this file was written after reading an outcome. The package had never
been run when this was frozen; the isolate has no price history loaded for it yet.

---

## 1. Hypothesis

**IDs**

| ID | Symbol | Timeframe |
|---|---|---|
| `HYP-LSWEEP-XAU-M5-001` | `XAUUSD` | `M5` |
| `HYP-LSWEEP-EUR-M5-001` | `EURUSD` | `M5` |

Each sleeve passes or fails on its own. No pooled P&L.

**Statement.** Resting stop-loss orders cluster just beyond salient intraday
reference levels. When price sweeps through such a level and immediately fails to
hold beyond it, the excursion was liquidity-driven — a stop cascade absorbed by
dealers — rather than information-driven. Dealers left holding unwanted inventory
push price back inside the level. The reversion is the payoff.

**Documented basis.**

- Osler, C. L. (2003). "Currency Orders and Exchange Rate Dynamics: An Explanation
  for the Predictive Success of Technical Analysis." *Journal of Finance*, 58(5),
  1791–1819. Actual Citibank order-book records show stop-loss orders clustering
  *just past* round numbers while take-profit orders cluster *at* them. That
  placement asymmetry is what produces the breach-then-reverse dynamic this EA
  trades: the stop cluster beyond the level supplies the fuel for the excursion,
  and the absence of continuation flow behind it supplies the reversion.
- Andersen, T. G., & Bollerslev, T. (1997, 1998). Intraday FX volatility
  seasonality — the deterministic activity pattern around London and New York
  hours. This is why the EA only trades inside the London and New York windows:
  the mechanism needs a populated order book and dealer inventory to work against.

**Why this is regime-invariant ("bất biến với thị trường").** The edge is not a
statistical artifact of a trend regime, a volatility level, or a central-bank era.
It rests on two structural facts about how the FX/metals market is organised:

1. **Order-placement convention.** Humans and institutions place protective stops
   at round numbers and at the previous day's / session's extremes. This is a
   convention of *where risk is written down*, not a forecast. It persists across
   regimes because the alternative (placing stops at random prices) has no
   constituency.
2. **Dealer inventory management.** A dealer who absorbs a one-directional stop
   cascade is left with inventory they did not want and must offload. Their
   offloading is the reversion. This is a microstructure necessity, not a
   behavioural bias that can be arbitraged away by more participants — more
   participants make the stop cluster *bigger*, not smaller.

The mechanism therefore does not require a directional forecast, a trend filter,
or a volatility regime classifier, and its failure mode is honest: if the level was
breached by *information* rather than by a stop cascade, the bar does not close
back inside, and no trade is taken.

**Failure condition (what would falsify it).** If, on closed M5 bars, price that
penetrates a reference level by a bounded amount and closes back inside shows no
positive mean reversion over the next 24 M5 bars gross of cost, the thesis is dead
for that symbol. That is a gross-edge test and is read before any cost discussion.

---

## 2. Instrument, clock and data

| Item | Value |
|---|---|
| Symbols | `XAUUSD`, `EURUSD` (separate sleeves, separate configs) |
| Decision timeframe | `M5`, closed bar only |
| Terminal | portable isolate `02. AlphaFactory/runtime/mt5-portable-mqdemo` |
| Compile path | `.\alpha.ps1 compile "EA_LiquiditySweep"` only |
| Data range target | 2016-01-01 → cutoff, or `broker-limited` if the isolate has less |
| Model | Model 0 (every tick) for baseline |
| History quality | must be **> 97 %** or the run is void |

### Server clock — explicit, no assumption that server time equals GMT

The EA reads bar times from `iTime(...)`, which are **broker server times**. It
converts them to a GMT-equivalent decision clock with an explicit input:

```
gmt = server_time - (InpServerGmtOffsetHours + (US_DST_active ? 1 : 0)) * 3600
```

- `InpServerGmtOffsetHours` is the **standard-time** (winter) offset. Default `+2`.
- `InpServerDstUsRule` (default `true`) adds one hour between the second Sunday of
  March and the first Sunday of November, which is the convention almost every
  retail MT5 FX server follows (GMT+2 winter / GMT+3 summer).
- `TimeGMT()` is **never** used for a decision. At `OnInit` the EA prints the
  measured `TimeGMT() - TimeTradeServer()` delta as a **diagnostic only**, so the
  correct offset can be read off the first journal and pinned. It does not feed
  any branch, so tester and live take the identical code path (WORKFLOW §3).

**Open item for the run agent:** confirm from the first journal line
`LSW_CLOCK_DIAG` that `InpServerGmtOffsetHours=2` is right for
`mt5-portable-mqdemo`. If it is not, the correct value is an *engineering fix*, not
a market revision, and does not consume revision budget.

### Two clocks, deliberately

- **Session windows** are evaluated on the derived **GMT** clock (the mechanism is
  tied to London/NY liquidity, which is a GMT phenomenon).
- **Flatten hours and the rollover exclusion** are evaluated on raw **server**
  time, because `02. AlphaFactory/analysis/unified_validation.py` classifies a
  trade as overnight with `t.exit_time.date() > t.entry_time.date()` on
  **report/server** timestamps. Binding the flatten to server time is the only way
  to make the `HoldingContract=scalp` gate structurally satisfiable.

---

## 3. Decision semantics — closed bar, no exceptions

- One decision per completed `M5` bar, taken on the first tick after the bar closes.
- The confirmation bar is shift `1`; when `InpRequireNextBarHold` is on, the sweep
  bar is shift `2` and shift `1` is the hold bar.
- `iHigh/iLow/iClose(...,0)` and any incomplete-bar data are **never** read for a
  decision. Bar `0` is used only for new-bar edge detection (its open time).
- Every reference level is a function of bars that had already closed at decision
  time. The Asia range and the opening range are recomputed as pure functions of a
  **fixed, already-elapsed time window**, so they are frozen by construction rather
  than by mutable state — a restart mid-day reproduces the identical level.
- `ArraySetAsSeries` is never relied on implicitly. Every `CopyRates`/`CopyBuffer`
  either uses `count = 1` at an explicit shift (unambiguous) or sets the series
  flag explicitly at the call site with a comment stating the index direction.
- Indicator handles and every `CopyBuffer`/`CopyRates` return value are checked;
  a failure is a **fail-closed** `data_fail`, never a silently-passed filter.

---

## 4. Reference levels (`Include/LSW_Levels.mqh`)

All computed from closed bars only. Each level carries a family tag so telemetry
can attribute realised performance per family.

| Family | Definition | Availability |
|---|---|---|
| `PREV_DAY` | prior completed `D1` high / low (shift 1) | always, once ≥ 2 D1 bars |
| `ASIA` | high / low of `[00:00, 07:00)` GMT of the current GMT day | only from 07:00 GMT; frozen for the rest of the day |
| `OPEN_RANGE` | high / low of the first `InpOrBars` M5 bars after the active session open (London 07:00 GMT, NY 12:00 GMT) | only after the OR window has fully elapsed |
| `ROUND` | nearest multiple of `InpRoundStep` above and below the confirmation close | always, if `InpRoundStep > 0` |

`InpRoundStep` is symbol-appropriate: `5.0` for XAUUSD, `0.0050` for EURUSD,
`0.50` for JPY pairs.

---

## 5. Entry

**Sweep geometry**, on the sweep bar `S` (shift 1, or shift 2 when a hold bar is
required), with `atr = ATR(M5,14)` read at the same shift:

For a level `L` swept from below (a **high** sweep ⇒ **short**):

1. `S.high - L >= InpSweepMinAtr * atr` — a real penetration, not noise.
2. `S.high - L <= InpSweepMaxAtr * atr` — deeper than this is a genuine breakout,
   not a stop run, and is rejected.
3. `S.close < L` — the bar closes back on the origin side.
4. `prev(S).close <= L` — the level was approached *from* the origin side; this
   excludes "price was already above L" cases that are not sweeps at all.
5. If `InpRequireNextBarHold`: the following closed bar must satisfy
   `high <= L` (no re-penetration).

A **low** sweep (⇒ **long**) is the exact mirror.

If both a high sweep and a low sweep qualify on the same bar (outside bar), the
signal is **rejected as ambiguous** — it is not resolved by preference. If several
levels qualify in the same direction, the one with the **largest penetration** is
taken, deterministically.

**Direction:** against the sweep. Swept a high ⇒ **short**. Swept a low ⇒ **long**.

**Order:** market order at the confirmation bar's close tick, submitted through
`CAFExecutionKernel::SubmitMarket` (`03. EA Developer/_Shared/Execution/AF_ExecutionKernel.mqh`)
with SL and TP attached to the entry request, so broker-side protection exists from
the first tick. The kernel is compiled with `AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 1`.

---

## 6. Exit

| Exit | Rule |
|---|---|
| Stop loss | sweep extreme ± `InpSlBufferAtr * atr`, then floored so the risk distance is at least `InpMinSlSpreadMult × current spread`; broker-side |
| Take profit | `InpTpR × risk_distance` from entry; broker-side |
| Time stop | close at market after `InpMaxHoldBars` completed M5 bars |
| Break-even | when open profit reaches `InpBeAtR × risk_distance`, move SL to entry (`InpBeAtR = 0` disables) |
| Daily flat | hard close at server hour ≥ `InpFlattenHourServer` |
| Friday flat | hard close at server hour ≥ `InpFridayFlattenHourServer` on Friday |

No trailing stop, no pyramiding, no averaging, no re-entry on the same level in the
same bar. One position per symbol at any time.

Entries are also blocked inside the flatten windows and inside the rollover
exclusion (server hour `23` or `0`), so no position can be opened that cannot be
closed on the same server calendar day.

---

## 7. Position sizing

Risk-per-trade is `InpRiskPercent` % of **account equity**, converted to volume
from the actual stop distance:

```
money_per_lot = (risk_distance / SYMBOL_TRADE_TICK_SIZE) * SYMBOL_TRADE_TICK_VALUE_LOSS
```

`SYMBOL_TRADE_TICK_VALUE_LOSS` is already expressed in the **deposit currency**, so
account-currency conversion is handled by the terminal rather than by a hand-rolled
FX cross. The result is cross-checked against
`OrderCalcProfit(type, symbol, 1.0, entry, sl, …)` and the **more conservative
(larger) of the two** money-risk figures is used. If both paths fail, the trade is
rejected (`entry_reject_sizing`) — it is never sized on a guess.

Volume is then clamped to `SYMBOL_VOLUME_MIN` / `SYMBOL_VOLUME_MAX` and rounded
**down** to `SYMBOL_VOLUME_STEP`. `OrderCalcMargin` must come back at ≤ 50 % of
free margin or the trade is rejected. `SYMBOL_TRADE_STOPS_LEVEL` and
`SYMBOL_TRADE_FREEZE_LEVEL` are enforced on both SL and TP before submission.

---

## 8. Filters, exposure and safety locks

| Lock | Input | Default (XAU) |
|---|---|---|
| Session window | `InpSessionMode` | `BOTH` (London 07:00–16:00 GMT, NY 12:00–20:00 GMT) |
| Rollover exclusion | hard-coded | server hour 23 and 0 blocked |
| Adaptive spread guard | `InpMaxSpreadAtr` | `0.20` (`spread <= 0.20 × atr`) |
| Volatility floor | `InpMinAtrPoints` | `60` points |
| News blackout | `InpNewsBlackoutMin` | `20` minutes either side of a high-impact event in either leg currency |
| Max trades/day | `InpMaxTradesPerDay` | `6` |
| Max consecutive losses | `InpMaxConsecutiveLosses` | `4` (locks for the rest of the day) |
| Daily loss lock | `InpMaxDailyLossPct` | `2.0` % of the day's opening equity |
| Account DD lock | `InpMaxAccountDdPct` | `10.0` % from peak equity (locks until restart) |
| Concurrency | hard-coded | exactly one open position per symbol |

**News-filter honesty.** `CalendarValueHistory` returns nothing in a tester whose
calendar database is empty, and the time zone its records use is a documented
uncertainty (see §12). The filter therefore **fails open** and increments a
`news_query_empty` counter, so a silently-inactive news filter shows up in the
`OnDeinit` summary instead of hiding.

---

## 9. Cost, slippage and swap assumptions

| Item | Baseline (x1) | Stress x1.5 | Stress x2 |
|---|---|---|---|
| Spread | tester `current` (broker-modelled, variable) | ×1.5 | ×2 |
| Commission | XAUUSD `$7` / lot round turn; EURUSD `$7` / lot round turn | ×1.5 | ×2 |
| Slippage | execution mode with a fixed delay (`-ExecutionMode` per `alpha.ps1`) | ×1.5 | ×2 |
| Swap | broker default; expected to be **irrelevant** — no position may survive to rollover |

### Preregistered statement about the cost hurdle

This is the part that is most likely to kill the mechanism, and it is written down
*before* the first run rather than discovered afterwards.

At 10–40 trades/week on M5, **cost per trade is a large fraction of the expected
edge per trade.** Concretely: with an M5 ATR of roughly `$0.80` on XAUUSD and a
stop distance near `0.5 × ATR`, the risk unit is around `$0.40–0.90`, while a
typical XAUUSD round-trip cost (spread + commission + slippage) is around
`$0.30–0.50`. That is **on the order of 40–60 % of one R** consumed by cost at
`x1`. On EURUSD the ratio is no better once a raw-spread commission is included.

Consequences that are accepted in advance:

- A gross edge that looks convincing can still produce a net PF below 1.30.
- **The `x2` cost-stress gate (`PF ≥ 1.00`) is the single likeliest failure mode
  of this mechanism.** It is preregistered as such. Failing it is a KILL, not an
  invitation to renegotiate the gate.
- The one *designed* defence is `InpMinSlSpreadMult` (default `4.0`), which floors
  the risk distance at four times the live spread so that cost cannot exceed
  ~25 % of R from the spread leg. This trades hit-rate for cost robustness on
  purpose. It is a parameter, not a post-hoc rescue.
- Widening the stop to dilute cost also lengthens the time to target, which
  collides with `InpMaxHoldBars` and with the no-overnight requirement. This
  tension is real and is not resolved by this contract; it is what the baseline is
  supposed to measure.

---

## 10. Data split

Sealed until the config is frozen. The OOS and final holdout are not to be looked
at, summarised, or used to choose anything.

| Split | Range | Use |
|---|---|---|
| TRAIN / DESIGN | 2016-01-01 → 2021-12-31 | baseline, all research |
| VALIDATION | 2022-01-01 → 2023-12-31 | robustness, sensitivity |
| OOS | 2024-01-01 → 2025-06-30 | **sealed** until freeze |
| FINAL HOLDOUT | 2025-07-01 → cutoff | **sealed**, one read only |

If the isolate's history starts later than 2016-01-01, the run is recorded as
`broker-limited` with the actual first bar, and the split boundaries shift
proportionally — recorded before the run, not after.

---

## 11. Researchable parameters and trial budget

Only the parameters below may be researched. Everything else is fixed at its
declared default for the life of this hypothesis.

| Parameter | Range | Step |
|---|---|---|
| `InpSweepMinAtr` | 0.10 – 0.40 | 0.05 |
| `InpSweepMaxAtr` | 0.60 – 1.60 | 0.20 |
| `InpSlBufferAtr` | 0.25 – 0.75 | 0.10 |
| `InpTpR` | 1.00 – 2.00 | 0.10 |
| `InpMaxHoldBars` | 12 – 48 | 6 |
| `InpOrBars` | 3 – 12 | 3 |
| `InpMinSlSpreadMult` | 2.0 – 6.0 | 1.0 |

Not researchable: risk %, all safety locks, session windows, flatten hours,
`InpRequireNextBarHold`, `InpBeAtR`, `InpRoundStep` (pinned per symbol),
`InpMaxSpreadAtr`, `InpMinAtrPoints`, `InpNewsBlackoutMin`.

**Total trial budget: 60 trials** (30 per symbol), in one optimization pass,
opened only after a Model-0 baseline shows a gross edge. No second pass without a
new hypothesis ID. Trial debt is carried into DSR/PBO at validation.

Revision budget: baseline + at most **two** market-logic revisions, then KILL
(WORKFLOW §6).

---

## 12. Known uncertainties, declared up front

1. **Economic-calendar time zone.** `MqlCalendarValue.time` is queried with
   **server-time** bounds. If the terminal actually returns those records in GMT,
   the blackout window is displaced by the server offset. Not verifiable without a
   populated calendar; declared here rather than discovered later.
2. **Server offset default.** `InpServerGmtOffsetHours = 2` is the retail-MT5
   convention, not a measured fact for this isolate. See §2.
3. **DST switch edges.** The US-DST rule is evaluated to the day with a fixed hour
   boundary, so the two switch days each year can be off by up to a few hours.
4. **Calendar-in-tester.** If the isolate's calendar DB is empty, the news filter
   is inert. Visible via `news_query_empty` in the summary, never silent.

---

## 13. PASS / KILL

Bound to `01. GOAL/GOAL.md` as amended by the Owner on 2026-08-31. **Per symbol.
No pooling.**

### PASS (all must hold, on the same frozen config)

| # | Condition |
|---|---|
| 1 | `PF > 1.30` after cost `x1` |
| 2 | cadence **10–40 trades per week** on that symbol |
| 3 | cost stress `x1.5` ⇒ `PF ≥ 1.25` |
| 4 | cost stress `x2` ⇒ `PF ≥ 1.00` |
| 5 | tester history quality **> 97 %** |
| 6 | `overnight_trades == 0` **and** `weekend_crossing_trades == 0` — the exact `HoldingContract=scalp` gate in `02. AlphaFactory/analysis/unified_validation.py` |
| 7 | positive expectancy, and Monte-Carlo P95 drawdown inside the preregistered budget |
| 8 | OOS and final holdout consistent with train, read only after freeze |

### KILL

- No gross edge before cost on the design split → KILL immediately. Do not
  optimize a mapping with no gross information.
- `x2` cost stress `PF < 1.00` after the permitted revisions → KILL.
- Cadence below 10/week that can only be reached by going outside the ranges in
  §11 → KILL (widening the ranges after seeing the count is overfitting).
- Cadence above 40/week that can only be fixed by a filter invented after the run
  → KILL.
- Any overnight or weekend-crossing trade that is not traceable to an engineering
  defect → KILL.
- Two market-logic revisions exhausted → KILL.

### Not a KILL

- A compile or wiring defect. That is an `ENGINEERING_FIX` under the same
  hypothesis ID (WORKFLOW §6) and does not consume revision budget.
- A wrong `InpServerGmtOffsetHours` for the isolate. Same category.

---

## 14. Freeze record

| Field | Value |
|---|---|
| Frozen at | 2026-08-31 |
| Package | `03. EA Developer/EA_LiquiditySweep/` |
| Entry point | `EA_LiquiditySweep.mq5` |
| Shared dependency | `03. EA Developer/_Shared/Execution/AF_ExecutionKernel.mqh` (reused, not modified) |
| Backtests run before freeze | **none** |
| External data | none — MT5 native only, so no source-governance child is opened (WORKFLOW §2) |
