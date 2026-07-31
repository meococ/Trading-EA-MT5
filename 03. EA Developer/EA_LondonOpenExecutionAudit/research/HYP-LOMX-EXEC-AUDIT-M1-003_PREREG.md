# HYP-LOMX-EXEC-AUDIT-M1-003 — Frozen MT5 Execution-Fidelity Audit

Status: **FROZEN BEFORE MQL5 SOURCE, COMPILE, OR MT5 OUTPUT**  
Freeze date: 2026-07-30  
Owner scope: create an audit-only MQL5 successor and backtest it.  
Economic parent: `HYP-LOMX-MULTI-M1-002` (terminal TRAIN kill; not reopened).

## 1. Audit question and authority boundary

Can a causal, closed-bar MQL5 implementation reproduce the four distinct
London-open trade scenarios with observable order requests, actual Model-0
fills, and exact time exits on FivePercent broker history?

This is an engineering/execution audit only. It does **not** test a new alpha
claim, rescue the killed HYP002 economics, open validation/holdout, authorize
optimization, or support promotion, paper, or live trading. Tester PF, net
profit, drawdown, win rate, and expectancy are diagnostic telemetry only.

Bound parent artifacts:

- HYP002 prereg SHA-256:
  `87671236C8481111992FAA20476A118AB1A7ABFEFBC3FC11B51E7CBAA1BF8D91`.
- HYP002 terminal TRAIN ledger SHA-256:
  `32EE3D1A642D2F5F46A6309358CD35B1B7DC8D23FC215A179C97EE52D77EC4D6`.
- HYP002 terminal metrics SHA-256:
  `6577299078F4ECB7009B2DD846C21118750D95DAABCEA2A66E5E702773C51261`.

The parent ledger contains 29,470 actual trade rows. The earlier registry
telemetry fields `returns_computed=29555`, `trades_simulated=29555`, and
`best_primary_gross_pf=1.000755` are known bookkeeping drift; they must not be
used as the audit population truth. This successor does not edit that terminal
row.

## 2. Frozen rule matrix

All runs use broker Model 0 real ticks, chart period M1, fixed 0.01 lot, one
owned position maximum, no stop-loss, no take-profit, no scaling, and a
same-day time exit. Signal direction remains:

`direction = primary_polarity * sign(log(open_0830 / open_0800))`

Exact-zero formations and days missing either exact M1 bar are skipped.

| Run cell | Symbol | Polarity | Signal observation | Earliest entry | Exit request |
|---|---|---:|---|---|---|
| `EURUSD_MIDDAY_CONT` | EURUSD | +1 | first tick of London 08:31, after the 08:30 M1 bar closes | same 08:31 tick | first tick at/after London 12:00 |
| `GBPUSD_MIDDAY_REV` | GBPUSD | -1 | first tick of London 08:31 | same 08:31 tick | first tick at/after London 12:00 |
| `GBPUSD_LATE_FIX_REV` | GBPUSD | -1 | first tick of London 08:31 | first tick at/after London 15:30 | first tick at/after London 16:00 |
| `GBPUSD_FULL_SESSION_REV` | GBPUSD | -1 | first tick of London 08:31 | same 08:31 tick | first tick at/after London 16:30 |

The one-minute MIDDAY/FULL_SESSION delay is deliberate and frozen. HYP002's
offline proxy assumed an entry at the 08:30 Bid open, the same boundary used
to finish formation. The successor waits until bar 08:30 is closed and enters
at 08:31 using the executable side: Ask for buys, Bid for sells. It therefore
tests realistic latency/fill divergence without pretending to be byte-equivalent
to the killed offline proxy.

`LATE_FIX` keeps the 15:30 entry because its signal has been immutable since
08:31. No bar-zero value participates in the decision. All exact London times
are mapped through UTC with UK DST and then to broker server time with winter
GMT+2 and European DST.

## 3. Frozen run window and attempt budget

- TRAIN only: `2016.01.01` through `2020.12.31`.
- Validation `2021.01.01` through `2024.12.31`: sealed.
- Holdout `2025.01.01` through current: sealed.
- Exactly four Model-0 run cells, one per row in the rule matrix.
- One compile/fix cycle is allowed until the source compiles 0 errors/0
  warnings and static non-repaint checks pass.
- No parameter optimization, alternate entry minute, spread filter, weekday,
  year, session, stop, target, symbol substitution, or rerun after outcome.
- An operational rerun is allowed only when a run is invalid because the
  harness, data, source identity, or required telemetry failed before a valid
  receipt; it must retain the exact frozen cell.

## 4. Required telemetry and scenario invariants

The package must emit `lifecycle-v3`, run meta, and decision telemetry without
`FILE_COMMON`. For every candidate/order/deal it must record enough data to
reconstruct:

- London date, London/UTC/server timestamps;
- exact source bar timestamps and 08:00/08:30 Bid opens;
- formation sign, frozen polarity, requested direction, set name;
- signal observation, entry eligibility, order request, broker result, and
  exit request events;
- Bid, Ask, spread, requested price, actual deal price, volume, order/deal/
  position identifiers, result retcode, and reason;
- missing-bar/zero-signal/exposure/order-check/order-send rejections;
- daily counters and final run counters in RunMeta.

Required population invariants per valid run:

1. Every entry has exactly one prior same-date `SIGNAL_READY` event.
2. Every entry direction equals frozen polarity times formation sign.
3. The 08:00 and 08:30 source bars are exact and closed (`shift >= 1`) at
   observation; no `iOpen(...,0)` or `CopyBuffer(...,0,...)` decision access.
4. No MIDDAY/FULL_SESSION entry request occurs before London 08:31; no
   LATE_FIX entry occurs before 15:30.
5. No exit request occurs before the set's frozen exit time.
6. Entry deals use Ask for buys / Bid for sells within broker fill mechanics;
   exit deals use the opposite executable side.
7. At most one owned position is open; no weekend or overnight position is
   allowed by the frozen same-day exits.
8. Lifecycle entry and final exit counts reconcile to the MT5 report and
   RunMeta. Missing sidecars or unreconciled IDs invalidate the run.

## 5. Acceptance and terminal decision

Engineering acceptance requires all four valid runs to pass:

- source/prereg/EX5/config/report hashes reconcile;
- compile `0 errors, 0 warnings`;
- exact-source non-repaint audit PASS;
- required sidecars exist and parse;
- all eight scenario invariants have zero mismatch;
- history quality is reported and any `<99%` result is labeled engineering
  invalid rather than economic evidence.

Economic gates remain the workspace defaults only so the registry schema and
runner contract stay complete: PF >1.30, 2–5 trades/elapsed week, max DD 8%,
x1.5 PF >=1.25, x2 PF >=1.00, Monte Carlo P95 DD <=8%. These gates are **not
authorized for evaluation** under this audit-only successor.

Terminal verdicts:

- `PASS_AUDIT_ONLY`: all four cells reconcile; parent HYP002 remains killed.
- `PARTIAL_AUDIT_ONLY`: some valid cells pass but one or more cells are blocked
  or invalid; no economic inference.
- `FAIL_EXECUTION_FIDELITY`: any valid run violates frozen scenario invariants;
  no economic inference and no post-hoc rule repair under this ID.

## 6. Explicit prohibitions

No validation/holdout read, optimization, economic rescue, promotion,
portfolio use, paper attach, live attach, cron, external order, or claim that
audit success establishes edge. The EA defaults disarmed and only runs when
the exact hypothesis ID, scenario tag, symbol, timeframe, magic, telemetry,
broker-time contract, and `InpAuditAutoMode=true` are supplied.
