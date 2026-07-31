# HYP-VRAS-EURUSD-M5-008 - Grok Random-100 Forensic Plan

Frozen before random selection, chart rendering, image review, Grok output, or any successor source change.

## Authority and boundary

- Parent object: terminal diagnostic `HYP-VRAS-EURUSD-M5-008`.
- Exact run: challenger `20260722_233420`, EURUSD M5, Model 0, 2019-2022, 100% history quality.
- Purpose: explain entry context, winner/loser anatomy, stop/target/management behavior and code-fidelity constraints from an unbiased random trade sample.
- Grok role: read-only forensic reviewer. It may propose at most three mechanism-level hypotheses, but cannot edit the EA, tune thresholds, authorize a rerun, promote, or use the same outcomes to claim edge.
- This review cannot rescue or change the terminal HYP008 verdict.

## Bound evidence

- Run manifest SHA256: `FF9332450A14E1F0E8B190F735C5BC1B9834267265C16BB60154C4A4703D97F2`.
- Lifecycle SHA256: `2CB21056F69708D2FD735A2A06E725DC578FD9F56E39487C393CD3B3B340C556`.
- Decision telemetry SHA256: `C510692DB20D710D92FCDE52C8628B158D98AAFE00BD3211E5E36E74254EDF66`.
- Broker M1 bars SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Source SHA256: `720D45505282123D4C8B78428B9913F6ADD41176013E5B968A60C56CF446E53C`.
- MT5 report SHA256: `483E5D42D08EE9DFF538015F5A2305DEFA3A81CC702496A859B03DCBE92F7F68`.

## Pre-render evidence correction

The lifecycle `event_time` and decision `server_time` fields are broker-server time, not UTC. The case ledger must retain the exact server timestamps and derive UTC with the canonical `fivepercent_server_clock.py`; weekday/session context is calculated from that derived UTC value. The frozen sample and draw order do not change.

Exit classes must come from the report-bound closing-order comment joined by the lifecycle final-close `deal` ID. `sl <price>` is split into `INITIAL_SL` versus `MOVED_SL` by comparison with the frozen initial stop; it must not be called break-even activation because the source does not log the modification event. `tp <price>` and `VRAS HYP006 time exit` are authoritative `TARGET` and `TIME_EXIT`. Any unmatched or ambiguous row is `UNKNOWN`, never inferred from final price or M1 first passage.

## Frozen sampling rule

1. Reconcile the lifecycle ledger to exactly 3,611 unique positions with one OPEN and one final CLOSE.
2. Sort the population by numeric `position_id`.
3. Draw 100 unique positions without replacement using Python `random.Random(18416118573351363056).sample(population, 100)`. The seed is the unsigned integer represented by the first 16 hexadecimal characters of the already-bound challenger run-manifest SHA256.
4. Preserve draw order as case order. Do not rebalance winners/losers, replace inconvenient cases, or add visually interesting trades to the random sample.
5. Tail/median delivery cases may be read as separate known examples, but they do not enter the random-100 population statistics or coverage count.

## Chart contract

Each sampled position requires two independently hash-bound images:

1. `decision_asof`: ends at entry, hides result/net R/future bars, and displays the active closed-bar surface: M5 candles, rolling VWAP48, closed H1 EMA200 and H1 close context, ATR14, entry, proposed SL/TP, spread, direction and exact telemetry values.
2. `anatomy`: displays entry, initial SL, nominal TP1.5R, actual exit and post-entry M5/M15 path through the final close.

The entry manifest must reconcile exact case ID, position ID, server time, canonical UTC, direction, entry, stop, target, H1 close, H1 EMA, rolling VWAP48, ATR14 and spread to `ORDER_ACCEPTED` decision telemetry. The exit manifest must bind the exact closing report comment/class without claiming a break-even modification timestamp. Continuous recomputed indicator trajectories remain explicitly `NON_PARITY_DIAGNOSTIC` unless separately parity-proven.

Any missing image, missing telemetry match, duplicate case, hash mismatch, future leak, wrong server-time alignment or entry parity failure stops dispatch.

## Grok dispatch and QC

- 20 sequential jobs, five trades / ten images per job; no parallel Grok backend calls.
- Each job must open all ten images, reconcile exact five case IDs and report observation separately from inference.
- Final synthesis must reconcile all 100 case IDs exactly once and all 200 images opened.
- Required analysis: validity; population and sampled decomposition; matched/context contrasts; stop/payoff/BE/time-exit mechanics; weekend/overnight behavior; active-source choke points; what winners share; what disappears after matching; unknowns; at most three legal fresh hypotheses.
- Parent validates response schema, exact coverage, image hashes, artifact/run reconciliation and final claims. Grok process success alone is insufficient.

## Successor research boundary

A Grok idea can advance only as a fresh hypothesis ID with a mechanism-level delta, cheap falsification probe, frozen preregistration and no threshold selected from this outcome sample. Any meaningful successor Model-0 request window is `2018.01.01` through the current research date (`2026.07.22`) and must fail closed if broker history/history-quality cannot actually cover it. Current local evidence proves a 99%-quality tester precedent through the requested July 2026 range, but the hash-bound bar snapshot ends intraday `2026.07.17`; therefore the next preregistration must bind an exact `as_of_timestamp` and last closed bar after a no-outcome availability audit, and cannot claim July 22 coverage until refreshed/read back. Full-window observation uses tester-only DD-halt bypass with drawdown measurement and tester-survival sizing frozen before outcome; live/default DD protection remains enabled.

Workspace economic target remains the canonical acceptance contract: PF >= 1.30, 2-5 trades per elapsed calendar week, max DD <= 6%, positive expectancy, cost PF x1.5 >= 1.25, cost PF x2 >= 1.00, plus stability/execution/non-repaint/delivery gates. The loop stops on target PASS, an evidence-backed kill/frontier stop, or a real data/tool blocker; it does not tune indefinitely until a lucky backtest appears.
