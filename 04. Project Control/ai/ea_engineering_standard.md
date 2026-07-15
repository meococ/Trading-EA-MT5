# EA Engineering Standard

## 1. Architecture
- Separate signal generation, risk policy, execution, state, and logging.
- Keep strategy logic replaceable without weakening risk or execution safety.
- Prefer explicit data contracts between modules over hidden globals.

## 2. Signal correctness
- Default to closed-bar logic (`shift=1`).
- Do not use bar zero for decisions unless the brief explicitly asks for live-bar behavior.
- Guard against insufficient bars, empty indicator buffers, and stale handles.
- Treat any MTF series as suspect until bar alignment is verified.

## 3. Execution safety
- Prefer `CTrade` unless a lower-level trade API is necessary.
- Check retcodes, order/deal tickets, and final broker response after every trade call.
- Respect symbol digits, point, spread, volume min/max/step, stop level, freeze level, fill mode, session, and trade mode.
- Use bounded retry with backoff for transient failures only.

## 4. Risk controls
- Provide risk-per-trade configuration.
- Require hard stop-loss by default.
- Include daily loss guard, max drawdown guard, max concurrent positions, spread filter, session filter, deviation/slippage control, and emergency kill switch.
- Make risk limits visible in logs or chart status.

## 5. Tester reproducibility
- Prefer deterministic AlphaFactory runs with explicit symbol, period, dates, model, and overrides.
- Save presets, repro notes, and `run_manifest.json` for every meaningful run.
- Avoid over-logging during optimization; keep detailed logs for baseline or forensic runs.
- Optional `OnTester()` metrics should target robustness, not only net profit.

## 6. Promotion checklist
An EA is not promotion-ready until all items below are satisfied:
- Architecture safety reviewed.
- No-lookahead/non-repaint audit completed.
- Execution and broker constraints reviewed.
- Risk controls implemented and tested.
- Tester settings and artifacts are reproducible.
- README, preset, and repro checklist updated.
- Known limitations stated plainly.
