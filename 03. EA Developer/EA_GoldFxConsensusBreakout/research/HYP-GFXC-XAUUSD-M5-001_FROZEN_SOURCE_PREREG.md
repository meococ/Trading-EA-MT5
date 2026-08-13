# Frozen Source Prereg — HYP-GFXC-XAUUSD-M5-001

Frozen before opening any DESIGN Parquet rows or computing a signal count.

## Thesis and scope

- EA family: `EA_GoldFxConsensusBreakout`.
- Target: `XAUUSD` / native M5 / FivePercent.
- DESIGN window: `2018-01-01T00:00:00` inclusive through
  `2023-01-01T00:00:00` exclusive. No 2023+ row or outcome may be opened.
- Mechanism: a gold range breakout is actionable only when three independent
  FX legs agree on broad USD weakness or strength. This is continuation, not
  XAU/USDJPY residual mean reversion, fixed-session momentum, triangular
  parity, real-yield shock or indicator voting.
- This stage is source/formula feasibility only. It may inspect current and
  prior completed OHLC but must not inspect any price after the decision bar,
  trade return, PF, expectancy, MFE, MAE or cost outcome.

## Frozen native inputs

All inputs are broker-native M5 Bid bars from
`DATA-FIVEPERCENT-5ASSET-MULTITF-004`:

| Symbol | SHA256 |
|---|---|
| XAUUSD | `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380` |
| EURUSD | `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8` |
| GBPUSD | `8EE2720261FC05A13A2E919C3EAA4FF50EEF75F9CB068519C61C48BB3D6B4F4B` |
| USDJPY | `FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD` |

Rows join one-to-one by `source_epoch`. For every joined row, all four
`time_server` values must agree and equal the source epoch mapping. Source
geometry, finite positive prices, positive tick volume, strict ordering and
unique timestamps are fail-closed. UTC is derived from the frozen FivePercent
server DST rule and is used only for the Friday rule.

## Exact causal formula

For symbol `s` and completed joined bar `t`:

1. `r_s(i) = ln(close_s(i) / close_s(i-1))`.
2. `sigma_s(t)` is the sample standard deviation of the 288 one-bar returns
   `r_s(t-288)..r_s(t-1)`. Current return `r_s(t)` is excluded.
3. `z12_s(t) = ln(close_s(t)/close_s(t-12)) / (sigma_s(t)*sqrt(12))`.
   Nonfinite or nonpositive sigma makes the row unusable.
4. XAU breakout uses only prior completed bars:
   - upper = strict maximum of XAU high `t-24..t-1`;
   - lower = strict minimum of XAU low `t-24..t-1`.
5. Long state at `t` is true iff all are strict:
   - XAU close(t) > upper;
   - XAU z12(t) >= `+0.50`;
   - EURUSD z12(t) >= `+0.50`;
   - GBPUSD z12(t) >= `+0.50`;
   - USDJPY z12(t) <= `-0.50`.
6. Short state is the exact inverse: XAU below lower; XAU/EURUSD/GBPUSD z12
   <= `-0.50`; USDJPY z12 >= `+0.50`.
7. A raw event exists only on a false-to-true transition of the same-side full
   state. Simultaneous long and short is a conflict and must be zero.
8. First usable decision index is `290`, the full dependency union needed for
   current and prior states. No partial warm-up is allowed.

The `0.50`, 12-bar return, 24-bar breakout, 288-bar scale and 12-bar lockout
are one frozen hypothesis, not a parameter grid.

## Population and decision contract

- Iterate completed joined bars in chronological order.
- A raw transition immediately consumes a 12 joined-bar lockout, before any
  eligibility rejection. A transition during lockout is ignored and not
  deferred.
- Decision availability is the next joined M5 row. It is executable only when
  its `source_epoch` is exactly decision epoch + 300 seconds.
- A raw transition whose availability time is Friday at or after 20:00 UTC is
  consumed but not executable.
- Calendar-year concentration and cadence use the availability-time UTC year.
- No daily quota, session filter, outcome-dependent overlap rule or direction
  selection exists.
- Ledger allowlist: hypothesis/attempt IDs, decision and availability clocks,
  direction, four current z12 values, breakout boundary, exact-next flag and
  Friday flag. No next-bar OHLC or outcome field is permitted.

## Source gates

All gates must pass in the single source attempt:

- joined DESIGN rows >= 300,000;
- usable feature coverage >= 99% of rows after the exact 290-row warm-up;
- exact-next coverage among raw consumed events >= 97%;
- executable events >= 500;
- pooled cadence 2.0–5.0 events per elapsed calendar week;
- LONG and SHORT each >= 30%;
- maximum single calendar-year share <= 30%;
- each decision-year cadence 1.25–6.5/week for 2018–2022;
- zero simultaneous-direction conflicts;
- deterministic byte-identical replay.

Any failed gate parks only this exact GFXC mapping as source-infeasible. It is
not an economic no-edge verdict. No threshold, window, cooldown, direction,
session or timeframe rescue is allowed under this ID.

## Authority boundary

- Exactly one durable source attempt: `GFXC-SOURCE-001`.
- Claim must be written exclusively and fsynced before any Parquet content
  read. Completion/failure terminal consumes the attempt; no overwrite/retry.
- A source PASS authorizes only direct MQL5 implementation, focused tests,
  compile and non-repaint/parity work for the unchanged mapping.
- It does not authorize MT5 economics, optimization, validation, holdout,
  paper, promotion or live deployment.
