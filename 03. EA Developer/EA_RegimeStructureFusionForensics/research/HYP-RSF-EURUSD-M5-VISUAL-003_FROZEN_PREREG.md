# HYP-RSF-EURUSD-M5-VISUAL-003 — Frozen Native Replay

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Purpose

Repeat the terminal Cell-16 control in native MT5 Strategy Tester Visual Mode after the VISUAL-002 engineering run was invalidated by a stale concurrent Visual-001 job. VISUAL-002 stopped on 2018-01-11 with four lifecycle events and zero deal screenshots; no strategy outcome or parameter decision is taken from it.

This successor changes only forensic presentation and orchestration:

- calculation handles used by the parent EA remain hidden from automatic chart attachment;
- display-only MBB/TB/QQE handles reuse the same engine contracts;
- the MBB display uses clean mode, TB omits origin-cell shading, and indicator alerts are disabled;
- exactly one QQE pane is allowed;
- no decision buffer, entry, exit, stop, target, risk, session, or symbol rule changes.

## Frozen execution

- EA: `EA_RegimeStructureFusionForensics`
- symbol/timeframe: `EURUSD M5`
- window: `2018.01.01` through `2022.12.31`
- model/execution: Model 0 / no artificial delay
- deposit/leverage: `100000 USD`, `1:100`
- visual mode: required (`Visual=1`)
- parent Cell-16 settings: profile 1, manual mode mask 7, manual session mask 6, context/TB/QQE enabled
- case selector: `FROZEN_13_V1`; immutable 14 position IDs from the existing selection manifest

## Acceptance

Engineering acceptance requires all of the following:

1. one clean portable-terminal run with no concurrent AlphaFactory/visual tester job;
2. exact parent identity: 372,914 bars, 105,949,201 ticks, 670 trades, net `-5252.60`, PF approximately `0.7203706`;
3. 28 native PNG files: OPEN and CLOSE for all 14 frozen positions;
4. 28 matching rows in the VisualShots sidecar with `screenshot_ok=1` and `last_error=0`;
5. exactly one QQE pane and native MBB/TB overlays visibly legible around trade markers;
6. source, indicator bundle, report, sidecars, charts, and run manifest hash-bound.

Failure is diagnostic. This ID has no authority to rescue the killed Cell-16 strategy, tune parameters, inspect validation/holdout, or make an economic/promotion claim.
