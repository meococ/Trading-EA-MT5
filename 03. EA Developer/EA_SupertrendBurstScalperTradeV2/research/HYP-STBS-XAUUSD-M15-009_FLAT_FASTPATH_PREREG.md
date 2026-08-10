# HYP-STBS-XAUUSD-M15-009 — flat-state lifecycle performance revision

Preregistered before implementation compile or any HYP009 source/run access.

## Informing result and legal scope

HYP008 consumed its sole Model0 attempt and timed out after 1,800 seconds. Its last logged simulated timestamp was the 2005 initialization record and no DESIGN event was observed; unlogged internal tester progress is unknown. It produced no signal, order, deal, report, return or economic metric. The audit-only parent completed the same 2005–2023 clock in about 71 seconds, while the trade source reconciled and rewrote a 24-field durable execution snapshot twice on every synthetic tick even when unchanged and flat.

HYP009 is a fresh engineering revision. It may change only execution-state persistence frequency and idle lifecycle scheduling. It must not change the frozen Supertrend calculation, flip timestamps, M15 ATR, entry/SL/TP geometry, sizing, trade permissions, risk locks, exit rules, session rules, DESIGN window or economic gates.

## Frozen code revision

- Fresh inner identity: `HYP-STBS-XAUUSD-M15-009`.
- Fresh variant: `STBS_H1_FLIP_M15_BURST_TRADE_FSM_V2`.
- Fresh non-economic persistence namespace/magic: `5604109`.
- The execution snapshot payload remains byte-semantically identical. `PersistExecutionIntent()` derives the complete generation-independent serialized payload and returns success without writing only when it exactly equals the last successfully loaded or committed payload; no hash-collision shortcut is used.
- Any changed payload still writes the complete alternate-slot snapshot, flushes it, writes and flushes the generation commit, and only then updates the in-memory exact payload cache. Partial or corrupt snapshots remain fail-closed.
- `OnTradeTransaction()` continues to reconcile immediately.
- `OnTick()` runs full lifecycle management on every tick whenever state is non-FLAT, an exit/reverse/entry expectation/request/order/deal is present, runtime is failed, or a new native M15 bar opens.
- While fully FLAT with no stateful intent, every tick still enumerates owned positions/orders. It skips full lifecycle reconciliation only after that inventory is proven empty. Any owned exposure or enumeration failure immediately enters the full management/fail-closed path. A new M15 bar always performs a full reconciliation as an additional health check.
- Risk-anchor update, H1 Supertrend advancement, frozen-window signal detection and event consumption remain on their original clocks.
- Audit mode is globally no-send: `SubmitEntry`, `SubmitClose` and `SubmitCancelOrder` each fail closed before their `OrderSend` gateway, independently of the normal signal branch.

## Static and runtime correctness gates

Before any economic run:

- focused tests must prove identity guards, generation-independent exact payload comparison, no rewrite on identical state, full write on changed state, exact active-state triggers, periodic new-M15 reconciliation, transaction reconciliation, restart recovery, pending/partial/reject handling, all three audit-mode send guards and DESIGN boundaries;
- MetaEditor compile must produce a fresh nonempty EX5 with 0 errors and 0 warnings;
- non-repaint audit must pass and signal/ATR/risk/exit logic must diff-identically outside the preregistered scheduling/persistence revision;
- independent review must approve the exact source/test/compile/audit hashes.

## Sole HYP009 engineering-throughput/parity run

After static/compile/review gates pass, HYP009 may run exactly one no-trade engineering audit using these exact source bytes:

- FivePercent `XAUUSD`, native `M15`;
- tester preload `2005.01.01` inclusive through `2023.01.01` exclusive;
- Model `0`, execution mode `0`, fixed delay `0`, current spread, USD 10,000, leverage 1:100, control role and telemetry off;
- the sole and exact override is `InpAuditOnly=true`;
- AlphaFactory timeout `300` seconds;
- exactly one attempt, with no optimization or same-ID retry.

It passes only if the tester completes within 300 seconds; data proof and initialization are valid; exact signal identity is `raw=690`, `executable=683`, `gaps=7`, `long=339`, `short=344`, `atr_ready=683`, `geometry_ready=683`; and request/order/deal/entry/close counts are all zero. PF, balance, expectancy and returns are forbidden evidence in this stage.

Only a pass may open a fresh economic child with the exact same source bytes, `InpAuditOnly=false`, the original 1,800-second budget and unchanged economic gates: at least 500 closed trades, 2–5 trades/week, each direction at least 30%, no year above 30% of trades, positive expectancy, PF strictly above 1.30 after tester costs, max equity DD at most 8%, no negative year, then later x1.5/x2 cost stress PF at least 1.25/1.00. Model0 remains TRAIN falsification only and cannot authorize OOS, holdout, paper, live or deployment.
