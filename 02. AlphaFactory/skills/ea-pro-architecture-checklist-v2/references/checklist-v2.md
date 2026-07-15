# EA Pro Architecture Checklist v2

Use this as the production-grade checklist for any serious EA. It is not a style guide; it is a promotion gate.

## 1) Edge thesis first
- State the market, timeframe, session, holding horizon, and structural edge.
- Name the regimes where the edge should work and where it should degrade.
- Define why the setup exists in market terms, not indicator folklore.

## 2) Architecture: modular, testable, replaceable
- Separate:
  - data/context
  - signal generation
  - risk model
  - execution
  - position management
  - logging/forensics
  - tester/research hooks
- Source/preset/docs must stay synchronized.
- Strategy logic must be swappable without weakening risk or execution safety.

## 3) Execution architecture: prefer FSM over monolithic `OnTick()`
Use `OnTick()` as a dispatcher, not a dumping ground.

Recommended state families:
- `IDLE`
- `BUILDING_CONTEXT`
- `SEARCHING_SETUP`
- `PLACING_ORDER`
- `WAITING_FILL`
- `MANAGING_POSITION`
- `RECOVERING_ERROR`
- `LOCKED_RISK`

Required behaviors:
- bounded retry with backoff
- no blind re-fire loops after requote/off-quotes
- explicit state transitions on success/failure/timeouts
- recovery paths for stale prices, disabled trading, freeze/stops violations

## 4) Asynchronous trade truth: `OnTradeTransaction()` first
- Use `OnTradeTransaction()` as the primary server-event bus.
- Never assume `CTrade` returning `true` means the trade lifecycle succeeded.
- Track:
  - request result/retcode
  - order/deal/position ids
  - partial fills
  - slippage
  - modify/close outcomes
- Keep handlers fast; queue capacity is finite.
- Use these events to drive FSM transitions and execution telemetry.

## 5) Data correctness and anti-lookahead
- Default to closed-bar signals only (`shift >= 1`).
- Treat bar `0` as unstable unless explicitly operating in tick mode.
- Guard every `Copy*`/`CopyBuffer` call for partial data and handle readiness.
- Audit MTF logic for timeframe alignment and shift consistency.
- Ban repainting dependencies unless explicitly isolated for visualization only.

## 6) Risk model: money-risk first, volatility aware
- Hard SL required by default.
- Position sizing must start from money risk, not vanity lot size.
- Prefer:
  - fixed-fraction base risk
  - stop distance derived from structure or ATR
  - optional light regime scaler
- If using volatility-adjusted sizing, avoid double-counting ATR when stop distance is already ATR-based.
- Enforce:
  - daily DD limit
  - overall equity DD limit
  - max concurrent positions
  - max trades/day
  - kill switch

## 7) Execution realism and broker constraints
- Check digits, point, tick size/value, min/max/step volume.
- Respect stops level, freeze level, fill mode, session tradability, trade mode.
- Detect spread/slippage drift and degrade or halt safely when conditions worsen.
- Record execution quality for TCA:
  - requested vs filled price
  - reject/retry rate
  - spread at entry/exit
  - latency proxies where possible

## 8) Position management must be data-backed
- Break-even, trailing, partials, pyramiding, and time exits need evidence.
- Measure:
  - close reason distribution
  - MAE/MFE
  - give-back after peak open profit
  - time-to-resolution
- Reject “good story” trade management if artifacts do not support it.

## 9) Live-safety / prop-firm controls
- Friday flatten or exposure reduction if weekend gap risk matters.
- News guard or shock-event policy must exist and be documented.
- Emergency kill switch must be obvious and tested.
- Support demo-forward / prop-safe presets separately from research presets.
- Assume live environments will be worse than tester assumptions.

## 10) Research architecture: MQL5 execution + optional Python intelligence
- MQL5 should own:
  - broker interaction
  - order lifecycle
  - local fail-safe logic
  - stop/position control
- Python may own:
  - large-scale data research
  - regime scoring
  - news/context scoring
  - Monte Carlo / correlation / matrix work
  - scenario mining
- If using a hybrid bridge, require:
  - heartbeat
  - timeout/stale-signal rejection
  - deterministic handoff format
  - local MQL5 fallback behavior

## 11) Evaluation: equity curve first, PF never alone
Minimum review set:
- equity curve chart
- underwater duration
- yearly/monthly returns
- worst month / worst rolling quarter
- trade count and trades/year
- profit factor
- expectancy
- avg win / avg loss
- max consecutive losses
- recovery factor
- SQN

SQN guidance:
- Compute SQN with enough sample size.
- Prefer using SQN as a supplemental promotion criterion or inside `OnTester()`.
- Do not let one or two outlier trades dominate the conclusion.

## 12) Anti-overfitting stack
- one meaningful change per run
- out-of-sample / walk-forward
- Monte Carlo
- sensitivity / heatmap / SSO-style stability surface review
- parameter-to-trade ratio awareness
- regime bucket analysis by year/month/session/hour
- reject isolated parameter islands

## 13) Tooling and research acceleration
- Build indicators when they accelerate scenario discovery or forensic review.
- Build analysis tools when a recurring question cannot be answered quickly from tester output.
- External repos/indicators are allowed only with audit:
  - source URL recorded
  - license checked
  - non-repaint/no-lookahead reviewed
  - bar-0 behavior reviewed
  - isolated first as research dependency before promotion into live core

## 14) Promotion gate: ask the money question
Before promoting a candidate, ask:
- Would I put my own money behind this?
- Would I trust it on a prop challenge with realistic spreads/slippage/news?
- If the answer is no, keep looping.

## 15) Operator doctrine
- Work proactively; do not wait for micro-instructions.
- Prefer the highest-value next step:
  - fix a real weakness
  - tighten live safety
  - improve evidence quality
  - reduce fragility
- Be hard-working but not chaotic:
  - long-horizon loops
  - minimal wasted runs
  - deterministic artifacts
  - decisions backed by evidence

## 16) Phoenix / AlphaFactory-specific reminders
- Use local AlphaFactory workflow as the primary lane.
- Use `alpha-orchestration-guard` first when chaining analysis skills.
- Reopen MT5 after backtests if the workflow disturbed the terminal.
