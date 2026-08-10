# Independent review — HYP-STBS-XAUUSD-M15-008 Model0 timeout

Reviewer verdict: `PARK_ENGINEERING_INVALID_MODEL0_TIMEOUT_PRE_REPORT_NO_ECONOMIC_READOUT`

## Evidence reconciliation

The independent reviewer reconciled the sole attempt start `B095C136…F3BE0`, failure terminal `1E897BAD…D3F80`, exact source `2E0501CC…77E32`, run EX5 `7FF08B11…11848` and config `77700AD8…B0A25`.

The exact tester segment contains successful initialization but zero `STBS_SIGNAL`, request result, deal, summary or fatal records. No report or manifest exists. AlphaFactory stopped the tester process at its frozen 1,800-second timeout; `thread finished` is not evidence of a completed backtest.

Therefore no PF, expectancy, drawdown, cadence, cost, balance or market-edge inference is legal. HYP008 is terminal and cannot retry.

## Root cause and revision boundary

The throughput defect is high-confidence. The audit-only source processed the same 2005–2023 tester clock in about 71.9 seconds, while the trade source performs two execution reconciliations per tick. An unchanged FLAT reconciliation still writes 24 terminal Global Variables and performs two synchronous flushes per persistence call.

Raising timeout alone leaves a production hot-path defect. A legal fresh child must preserve the strategy mapping but use new source bytes/package so historical HYP007/HYP008 path/hash bindings remain intact.

Approved revision constraints:

- state-change-idempotent execution persistence: initial snapshot once, then no durable write for an identical payload;
- every actual persisted state mutation still commits the full alternate-slot snapshot and generation marker exactly once;
- a FLAT/no-intent fast path may skip full reconciliation only after per-tick owned position/order enumeration proves inventory empty;
- per-tick lightweight inventory checks, transaction reconciliation, Friday/risk/time management and all pending/partial/reverse/runtime-fault paths remain intact;
- pre-send intent durability, post-result IDs, dual-slot corruption detection and risk anchors remain fail-closed;
- first run must be no-trade engineering throughput/parity evidence; economics requires a later fresh child with the exact passed bytes.

Required gates include stable FLAT/OPEN no-rewrite tests, every mutation commits once, partial/cancel/close/reverse/restart tests, exact `690/683/7` signal identity with `339/344` directions, fresh 0E/0W compile, non-repaint PASS, and a full no-trade Model0 performance run before any economic baseline.
