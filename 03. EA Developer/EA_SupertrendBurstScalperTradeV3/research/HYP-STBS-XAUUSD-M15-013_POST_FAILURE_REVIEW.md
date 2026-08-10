# HYP-STBS-XAUUSD-M15-013 post-failure review

Independent verdict: `PASS_KILL_ENGINEERING_PRE_COST`

The exact failure radius is the single HYP013 execution attempt. The manifest fingerprint mismatch independently blocks economic acceptance. The tester stop-out independently invalidates the report because it truncated 72% of the horizon, produced one OPEN-only lifecycle row, and left RunMeta `runtime_failed=false` despite an unreconciled execution state.

The displayed PF, trade count and return are inadmissible. There is no market no-edge claim and no strategy-parameter conclusion.

A fresh engineering child is permitted only if it:

- preserves signal timestamps, Supertrend-10x3 state, M15 ATR14, 1.00 ATR stop, 1.50R target, eight-bar hold and 0.25% maximum risk;
- descends volume by native step and verifies both `OrderCalcMargin` and `OrderCheck` projected margin, free margin and margin level against account stop-out mode/levels plus frozen headroom;
- rejects rather than enlarges risk when minimum volume is unsafe;
- performs an immediate post-fill actual margin-level check with emergency-close intent;
- classifies `DEAL_REASON_SO` as runtime failure, attributes the OUT deal through the owned position identifier, and reconciles any missing close at deinitialization;
- binds actual source-data identity `077437E0038B40FEDB8AC611CAFE410B2FF8D0A90A742F0C52336F728D8C0BF4` and fails closed on future drift;
- runs compile, source tests, non-repaint, audit/parity and one new Model-0 baseline before any economic claim.

Adding a session, direction, filter, alternate ATR, RR, stop, target or optimization cell based on this failed attempt is prohibited.
