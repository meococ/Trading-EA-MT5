# HYP-DATAACQ — Frozen preregistration: same-feed universe expansion

Authority: SOURCE_DATA_ACQUISITION_ONLY. No performance claim, no promotion,
no economics. Runs exist solely to make the isolate download M1 history for
symbols absent from the lab cache, so the falsification map can be tested on
a wider universe (JPY crosses, Scandies, EM exotics).

EA: EA_ExecutionKernelHarness (order mutation disabled — trades nothing).
Window: 2010.01.01 - 2026.09.18, M1, model 2 (open-price; fastest path that
still forces history sync). Spread: current. Deposit 10000, leverage 100.

Success criterion: history/{SYM}/ populated for the requested range. The
backtest's own result is void by design (EA trades nothing).
