# HYP-RSF-MULTI9-M5-001 Frozen Preregistration

Frozen before the first Strategy Tester launch or performance-outcome read.

## Hypothesis

A mode-routed combination of probabilistic/deterministic regime state, MBB
setup events, TB SMC structural confirmation and QQE timing can produce a more
stable decision surface than the killed universal AIRQMB default. Symbol and
session customization is permitted only through the predeclared search family
and must survive per-symbol walk-forward evidence.

This is materially distinct from AIRQMB SCREEN-006 because VRC and TB SMC add
new state variables and price geometry, the context timeframe is M15, the
decision policy has three mode-specific routes, high volatility becomes a risk
state rather than a veto, and market sessions are historically DST-aware.

## Frozen source identity

- EA source SHA-256: `AD9E575C66A9F66D9F2DF3BFF350AC1CDE0AD5C0397C203CF01C9E5C0A6B2DB0`
- EA EX5 SHA-256: `B3833F10B6845484E5242B8AEA0295818E838122A506E42EC7A65ECE02BCE5F3`
- EA contract SHA-256: `7F8768962F36830DA4537C3B81B17ABD4F808289CF28D28F14C621D185E1B1D0`
- AIRD source: `C432AEF3BF7EC93EC8A64BD2806C115E71F822B2DCB438DAC22590FB978EB475`
- VRC source: `EB81B1426CBDAF3143F553388A213E2BB5A3E33E05433991918CC5977273A087`
- MBB source: `AC5DB6E1DDA825F6A3535E9AB1E4C9956086C7AF590E2672C71CF03D8F4E54FE`
- TB SMC source: `4658F3CD2C439C2655EF1534A18D29BC52EB6D91B494F2C17CC337755F1F1F33`
- QQE source: `22456C83C73D2070F52D83BBCE7D5DC1982CD987F8BE807E10482703982CAF9A`
- Compile: MetaEditor `0 errors / 0 warnings`, EX5 93,404 bytes; AIRD, VRC,
  MBB and TB SMC also compile with `0 errors / 0 warnings`.

Any pre-outcome engineering correction requires a prereg amendment with new
hashes. Any decision-rule change requires a new hypothesis ID.

### Pre-outcome engineering amendment A1 — 2026-08-06

Run `20260806_155504` produced a 100%-quality report with zero orders and no
readable trade outcome. Its lifecycle funnel recorded `indicator_ready=0` and
`indicator_not_ready=6262`; the tester journal showed AIRD, VRC, MBB and TB SMC
rejecting the partial `iCustom` signature on every attempted update. QQE alone
initialized. This is an integration failure, not a market result.

A1 declares mirror enum types and passes the complete input signature for all
five custom indicators. Every calculation input and default numeric value is
unchanged. Trailing display and alert inputs are fixed to a headless tester
profile; they do not participate in the public calculation buffers. No entry,
exit, session, risk or sizing rule changed. Compile remains MetaEditor
`0 errors / 0 warnings`; the new source and EX5 hashes above supersede the
original engineering hashes solely for this smoke.

### Pre-outcome engineering amendment A2 — 2026-08-06

Run `20260806_160734` proved that A1's complete `iCustom` varargs still failed
runtime type marshaling: all five indicators rejected their inputs,
`indicator_ready` remained zero, and no order or economic outcome existed.

A2 replaces only custom-indicator handle construction with the official
`IndicatorCreate(IND_CUSTOM)` interface and an explicitly typed `MqlParam`
array for every input (`TYPE_INT`, `TYPE_DOUBLE`, `TYPE_BOOL`, `TYPE_COLOR`,
`TYPE_DATETIME`, and `TYPE_STRING`). The complete numeric calculation values,
buffer contracts, router, entries, exits, sessions, sizing and risk rules remain
unchanged. Headless display and alert values also remain identical to A1.
Compile is MetaEditor `0 errors / 0 warnings`; the A2 source and EX5 hashes above
supersede A1 for the same integration smoke.

### Pre-outcome engineering amendment A3 — 2026-08-06

Run `20260806_161527` showed that manually reconstructing `MqlParam.type` was
still not byte-for-byte equivalent to the compiled indicator ABI. Again all
five indicators rejected initialization, with no orders or economic outcome.

A3 stops reconstructing the ABI. It creates a parameterless default probe for
each compiled EX5, reads the authoritative parameter count, order and types via
`IndicatorParameters`, preserves those returned types, overrides only the
known values, releases the probe, then creates the controlled handle. It fails
immediately if the compiled parameter count or indicator kind drifts. All
calculation values and every strategy/risk rule remain unchanged. Compile is
MetaEditor `0 errors / 0 warnings`; the A3 hashes above supersede A2.

### Pre-outcome engineering amendment A4 — 2026-08-06

Run `20260806_162528` proved that `IndicatorParameters` is unavailable inside
this Strategy Tester context (`error 4014`). The parameterless probes did load
all five compiled indicators, but the EA deliberately failed before telemetry,
orders or any readable economic outcome.

A4 keeps `IndicatorCreate(IND_CUSTOM)` and explicit `MqlParam` types, but passes
only each indicator's leading calculation contract. MetaTrader supplies the
trailing visual/alert inputs from the compiled defaults. Every parameter read by
the EA remains independently controlled; no calculation value, buffer mapping,
router, entry, exit, session, sizing or risk rule changed. This also removes the
unsupported runtime introspection call. Compile is MetaEditor `0 errors / 0
warnings`; the A4 hashes above supersede A3 for the same integration smoke.

### Pre-outcome engineering amendment A5 — 2026-08-06

Run `20260806_163304` completed the full 7,322,711-tick window and wrote the
required sidecars, but the journal proved AIRD, VRC, MBB and TB SMC were still
rejected while QQE initialized. `indicator_ready` therefore remained zero and
there was no order or readable economic outcome.

A5 declares the indicator custom-enum types with the exact source ABI names and
uses `iCustom` with the shortest valid engine prefix. AIRD/MBB/TB now receive
their native enum types; VRC is passed through its validated band multiplier
and native dashboard enums; QQE retains its already working calculation prefix.
All numerical engine values and every strategy/risk rule remain unchanged.
Compile is MetaEditor `0 errors / 0 warnings`; the A5 hashes above supersede A4.

### Pre-outcome engineering amendment A6 — 2026-08-06

Run `20260806_164139` showed that separately compiled custom-enum identities
remain incompatible even when their source names match. AIRD/VRC/MBB/TB again
rejected initialization, QQE remained valid, and no economic outcome existed.

A6 adds a versioned primitive string as the first, optional EA-contract input
of AIRD, VRC, MBB and TB SMC. Empty strings preserve all chart-facing inputs and
visual behaviour. The EA packs the independently exposed engine parameters into
that stable transport; each indicator parses, validates and resolves them before
calculation. QQE retains its working primitive prefix. Calculation values,
buffers and all strategy/risk decisions remain unchanged. This explicitly
separates the human UI ABI from the EA engine ABI without adding an include file.
The A6 hashes above supersede A5 for the same integration smoke.

### Pre-outcome engineering amendment A7 — 2026-08-06

Run `20260806_165446` proved that the versioned indicator contracts work:
`indicator_ready=309`, `indicator_not_ready=0`, the range/trend funnels became
active and one market order opened. However, the account's unusually high
tester stop-out threshold terminated the simulation at 3% of the authorized
interval, five minutes after that first order. Lifecycle telemetry consequently
contained an OPEN without a reconciled final close. This is an incomplete
execution test, not a valid economic outcome or cadence observation.

A7 adds a sizing-only projected post-trade margin-level guard. Before sending
an order, volume is stepped down until projected margin level is at least the
configured floor and at least 1.25 times the broker's percent stop-out level;
money-mode stop-out also fails closed when equity headroom is insufficient.
Signal features, mode routing, sessions, entries, stop geometry, reward/risk
and exits are unchanged. The new source/EX5 hashes above supersede A6 for the
same integration smoke.

### Pre-outcome engineering amendment A8 — 2026-08-06

Run `20260806_170213` completed all 7,322,711 ticks and 18,402 bars with
`indicator_ready=6262` and `indicator_not_ready=0`, but rejected all 145 setup
attempts in sizing and opened no orders. The cause was A7's generic 15,000%
margin-level floor. It was deliberately conservative but incompatible with the
symbol's minimum lot, so the run contained no readable trade outcome.

A8 models the broker contract according to its declared stop-out mode. Percent
mode uses a 150% generic floor or 1.25 times the broker threshold, whichever is
higher. Money mode additionally requires projected free margin—not equity—to
remain above the broker's currency stop-out amount plus the greater of 5% of
equity or two planned losses. Volume is still reduced stepwise and never raised
above risk sizing. The exact stop-out mode/levels and safety inputs are emitted
in RunMeta. Signals, sessions, entry/exit conditions, stops and targets remain
unchanged. The source/EX5 hashes above supersede A7 for the same integration
smoke.

### Pre-outcome execution-contract amendment A9 — 2026-08-06

Run `20260806_170644` again completed the full Q1 interval with all indicators
ready and 145 setup attempts, but no lot could satisfy the broker contract.
New RunMeta evidence identified `ACCOUNT_MARGIN_SO_MODE=money`, margin-call
`92,000 USD` and stop-out `90,000 USD`, while the original smoke packet had
forced a `10,000 USD` deposit. That tester account is structurally incapable of
holding any position: the broker's stop-out amount alone exceeds equity.

A9 changes only the execution packet deposit to `100,000 USD`, matching the
broker's prop-account geometry. Risk remains percentage based at 0.20%; all
strategy, sizing, session and signal parameters stay frozen. This is an
environment-contract correction before any completed trade outcome, not a
performance parameter search. Economic and optimization authority remain
locked.

## Universe and evidence windows

Ordered independent cells:

1. EURUSD
2. USDJPY
3. GBPUSD
4. USDCHF
5. USDCAD
6. AUDUSD
7. NZDUSD
8. XAUUSD
9. BTCUSD

- Entry/context: M5/M15.
- Discovery and optimization family: 2018.01.01-2022.12.31, subject to verified
  per-symbol MT5 coverage.
- Rolling validation: 2023.01.01-2024.12.31.
- Family-sealed final holdout: 2025.01.01-2026.07.31. It is opened once, only
  after source and per-symbol selections are frozen.
- Final reporting also includes the entire available MT5 history and the
  workspace 84-month/14-half-year/7-year fitness surface when coverage permits.

## Outcome-blind symbol/session priors

| Symbol | Candidate session mask | Candidate modes |
|---|---|---|
| EURUSD | London, overlap | range, trend, breakout |
| GBPUSD | London, overlap, New York | range, trend, breakout |
| USDJPY | Asia, London, New York | range, trend, breakout |
| USDCHF | London, overlap | range, trend, breakout |
| USDCAD | overlap, New York | range, trend, breakout |
| AUDUSD | Asia, London | range, trend, breakout |
| NZDUSD | Asia, London | range, trend, breakout |
| XAUUSD | London, overlap, New York | trend, breakout |
| BTCUSD | Asia, London, overlap, New York, off-hours, weekend | range, trend, breakout |

Sessions are defined in local Tokyo/London/New York time and converted to UTC
with historical DST. Broker server offset is a separate frozen clock profile.

## Ordered search blocks and trial budget

The blocks are sequential. A later block is not opened unless the selected
surface from the earlier block remains positive after cost and temporal checks.
The full family count includes failed and discarded trials.

1. **Mode/session/ablation, maximum 18 trials per symbol.** Compare MBB setup
   control, context router, TB structure and QQE timing in the frozen order.
   Session masks are limited to the declared base session, adjacent session and
   their union; no arbitrary hour/weekday mining.
2. **Structure block, maximum 27 trials per surviving symbol.** TB swing length
   `{3,5,8}`, displacement/ATR `{0.35,0.55,0.75}` and event age `{1,2,3}`.
3. **Regime/timing block, maximum 27 trials per survivor.** AIRD confidence
   `{0.40,0.50,0.60}`, VRC ADX trend `{20,25,30}` and QQE threshold `{2,3,4}`.
4. **Exit block, maximum 9 trials per survivor.** Reward/risk
   `{1.25,1.50,1.75}` and stop half-width `{0.75,1.00,1.25}`. This block cannot
   rescue a signal family with non-positive selected OOS expectancy.

Maximum theoretical exposure is 81 trials per symbol and 729 across nine
symbols, plus prior AIRQMB family exposure disclosed separately in DSR/PBO.
Necessary-condition routing may skip later blocks but does not erase skipped or
executed family counts.

## Frozen selection rule

1. Reject cells outside 2-5 executed trades per elapsed calendar week on any
   required train/validation/OOS split.
2. Reject non-positive net expectancy or PF below the applicable stage gate.
3. Rank remaining parameter surfaces by median OOS net R across expanding WFA
   folds, not by in-sample PF or net profit.
4. Require the selected cell to have adjacent parameter neighbors at least 90%
   of its median OOS score. Isolated peaks fail.
5. A symbol-specific profile replaces the shared/default profile only when it
   improves median OOS net R by at least 0.05R, wins at least 60% of folds and
   does not worsen cost stress or tail DD. Otherwise shrink to the shared
   profile.
6. Ties use lower OOS dispersion, then lower drawdown, then lowest MT5 pass ID.

## Validation and promotion gates

- Real MT5 optimization passes and full `alphafactory_optimization_receipt.v1`.
- DSR counts every campaign simulation; required DSR floor 0.95.
- Event-level purged/embargoed CPCV and aligned CSCV/PBO; preferred PBO <0.20.
- Expansion WFA OOS profitable ratio >=0.60.
- Confirmed per-symbol PF >1.30; cadence 2-5/week; x1.5 PF >=1.25; x2 PF >=1.0.
- Positive years >=4/7, positive half-years >=9/14 and positive months >=0.50,
  subject to canonical validation-gate definitions.
- Monte Carlo P95 drawdown <=8%, no equity-spike dependency, no overnight/weekend
  exposure outside the frozen BTC contract.
- Each symbol stands alone. Pooled performance cannot rescue a losing symbol.

## Authority boundary

The first authorized run after engineering gates is an EURUSD M5 2023.01.02-
2023.03.31 Model-0 integration smoke using the frozen baseline. It can validate
indicator initialization, order path, telemetry and signal cadence. It cannot
promote, unlock optimization or spend validation/holdout data. If engineering
fails before an order outcome is readable, a semantics-preserving amendment is
allowed; otherwise all observed performance counts as an economic trial.
