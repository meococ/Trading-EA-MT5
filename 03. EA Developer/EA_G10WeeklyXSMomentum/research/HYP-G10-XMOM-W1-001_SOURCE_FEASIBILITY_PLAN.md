# HYP-G10-XMOM-W1-001 - Source-Feasibility Plan

Status: `FROZEN_PRE_OUTCOME_SOURCE_CONTRACT`

## 1. Identity and purpose

- Hypothesis: `HYP-G10-XMOM-W1-001`
- Package: `EA_G10WeeklyXSMomentum`
- Feature family: `g10-spot-cross-sectional-weekly-momentum`
- Portfolio decision timeframe: completed broker weekly bars (`W1`)
- DESIGN source years: `2018` through `2024` inclusive.
- Research holdout: every `2025+` HCC path and payload remains unopened.
- First task: exactly one outcome-blind, hash-only D-side source inventory.

The future economic thesis is a retail spot-return translation of weekly
cross-sectional currency momentum: rank non-USD G10 currencies by a single
completed one-week return, buy the top two and sell the bottom two through
their USD pairs, enter on Monday and flatten before the Friday broker close.
It is not a replication of academic spot-forward excess-return portfolios
because historical forward points and carry are absent.

This plan tests only whether the exact local broker-history source required for
that future question exists and can be frozen. It does not read or decode a
bar, timestamp, return, rank, signal, trade, cost or outcome.

## 2. Material delta and failure radius

- `EA_CurrStrength` S260/S261 tested a filtered ten-H1-bar currency-strength
  rule that traded only USDJPY. Those PF `0.74/0.84` results close that exact
  short-horizon, single-pair object; they do not close a one-week, four-leg
  cross-sectional portfolio.
- The killed Friday-D1 weekly carry surface used rate differentials. This cell
  uses completed spot-price ranking only and makes no carry claim.
- The earlier same-day cross-sectional proposal compressed a monthly mechanism
  into an intraday exit and was rejected before build. This cell freezes a
  literature-closer weekly formation and weekday multi-day hold.
- `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` survives only as an orphan
  independence comment in two tools. No registry row, contract, source,
  result or readout was found; it is context, not tested authority.

The new object is therefore legal to inspect at source level only. A valid
source PASS does not supersede any prior kill and does not authorize economics.

## 3. Exact source binding

Canonical broker-history root:

`D:/Trading EA MT5/02. AlphaFactory/runtime/mt5-portable-fivepercent/Bases/FivePercentOnline-Real/history`

Exact pair/orientation map, where `orientation` converts a future pair log
return into the non-USD currency return versus USD:

| Currency | Broker symbol | Orientation |
|---|---|---:|
| AUD | AUDUSD | `+1` |
| EUR | EURUSD | `+1` |
| GBP | GBPUSD | `+1` |
| NZD | NZDUSD | `+1` |
| CAD | USDCAD | `-1` |
| CHF | USDCHF | `-1` |
| JPY | USDJPY | `-1` |

For each exact symbol and each exact year `2018..2024`, the only allowed source
path is `<root>/<symbol>/<year>.hcc`. The source attempt may:

1. resolve the exact path without enumerating sibling years;
2. inspect path type, size, modification time and stable file identity;
3. stream the opaque bytes into SHA-256 without parsing, decoding or retaining
   any byte content;
4. confirm size, modification time and identity did not change across hashing.

The source attempt may also hash, without decoding, these exact broker cache
files:

- `.../Bases/FivePercentOnline-Real/symbols/symbols-26451822.dat`
- `.../Bases/FivePercentOnline-Real/symbols/selected-26451822.dat`

No other runtime path is allowed. In particular, `2025.hcc`, `2026.hcc`, ticks,
reports, tester artifacts and terminal logs are forbidden even for metadata.

## 4. Frozen future portfolio identity

This section prevents a source PASS from becoming a free design budget. It is
not executed in this stage.

- Information set: completed weekly spot bars only.
- Formation: exactly one completed week; no horizon grid.
- Currency universe: the seven non-USD currencies in Section 3; USD is the
  common numeraire and is not separately ranked.
- Selection: top two currency ranks and bottom two currency ranks; deterministic
  alphabetical tie-break.
- Instruments: exactly the four corresponding USD pairs, using the frozen
  orientation map. Equal ex-ante risk per leg is reserved for a later contract.
- Entry/exit: one Monday portfolio decision and Friday-flat before broker close.
- Exposure: weekday overnight exposure is explicit; weekend exposure is zero.
- Structural cadence: four intended entry legs per eligible elapsed week.
  Future evidence must count actual executed legs, never one rebalance event.
- Matched control: reverse the rank direction on the identical selected legs,
  dates, sizing and verified costs.
- Trial budget: one primary challenger plus one matched control. No dispersion,
  gap, volatility, session, weekday, news or trend filter.

## 5. One-shot source gates

All gates are fatal and outcome-blind:

1. Exactly `7 symbols x 7 years = 49` expected DESIGN HCC files are present,
   regular non-symlink files, non-empty and on the canonical D-side root.
2. Every HCC file is stable across its hash operation and has a valid SHA-256.
3. Every symbol has all seven exact years, establishing a file-year common
   intersection of `2018..2024`. This does not claim bar-level completeness.
4. Both exact broker symbol-cache files are present, regular, non-empty, stable
   and SHA-bound. Their presence does not prove historical cost provenance.
5. The orientation map is complete, unique and exactly balanced as four direct
   and three inverse USD quotes.
6. Structural portfolio identity emits exactly four intended entry legs per
   eligible week and explicitly counts legs rather than rebalance events.
7. Outcome-blind plane intact: zero HCC decode, bar/timestamp/price/return/rank/
   signal/trade/cost/outcome computation; zero MetaTrader5 import, MT5 launch,
   MQL5, network, paid request, validation or holdout access.

PASS: `PASS_SOURCE_INVENTORY_FUTURE_ECONOMICS_PREREG_ONLY`.

FAIL: `SOURCE_INVENTORY_FAIL_NO_ECONOMICS_AUTHORITY`.

Any path/hash/engineering failure is not a no-edge market verdict.

## 6. Attempt and evidence contract

- Attempt ID: `G10XMOM001-SOURCE-001`.
- Attempt limit: one.
- Evidence root:
  `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY/G10XMOM001-SOURCE-001`.
- Required chain: `attempt_started.json`, `source_inventory.json`,
  `source_feasibility_receipt.json`, `attempt_terminal.json`.
- Import must be inert. A production run requires an exact reviewed registry-row
  SHA sentinel plus an explicit CLI flag. The sentinel is disarmed immediately
  after the single attempt.
- Tests must use temporary synthetic opaque files only. Tests may not touch the
  real HCC source, MT5, network, registry or evidence root.

## 7. Forbidden claims and next authority

This plan and any valid source PASS grant no permission to decode HCC, load a
bar, inspect `2025+`, compute a return/rank/PnL/PF, build `.mq5`, run MT5,
optimize, promote, paper trade or trade live.

Only after a valid source PASS may a separate immutable economic preregistration
request a DESIGN bar export/loader. That later contract must bind the aggregate
source inventory SHA, define point-in-time weekly joins and broker-close clock,
include spread/commission/slippage plus weekday swap, preserve a sealed `2025+`
holdout, and freeze all economic/stability gates before any price is opened.

After any later result, same-ID rescue by changing formation/holding horizon,
universe, top/bottom count, tie-break, weekday, exit clock, sign, cost, filters
or subperiod is forbidden.
