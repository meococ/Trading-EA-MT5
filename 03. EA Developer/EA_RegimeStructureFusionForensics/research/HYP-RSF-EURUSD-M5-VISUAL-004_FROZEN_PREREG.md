# HYP-RSF-EURUSD-M5-VISUAL-004 — Frozen Native Replay

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Engineering delta

VISUAL-003 reached native Visual Mode but was invalidated before any selected trade: its display-only QQE handle used an extended iCustom argument list rejected by MT5, producing an empty pane and repeated `invalid input parameters` journal records. The captured 2018-01-03 chart is presentation evidence only.

VISUAL-004 makes two side-effect-only corrections:

1. display QQE uses the same proven 12-argument call as the parent decision handle;
2. TB SMC suppresses historical Alert/Print emission when `MQL_TESTER=true` while still rendering native objects in Visual Mode.

No indicator buffer, EA decision, order, stop, target, risk, session, or case selection changes.

## Frozen execution and acceptance

Execution is identical to VISUAL-003 except hypothesis/magic/variant identifiers: EURUSD M5, 2018.01.01–2022.12.31, Model 0, no artificial delay, 100000 USD, 1:100, Visual=1, parent Cell-16 masks, and `FROZEN_13_V1`.

Acceptance requires one isolated run; exact 670-trade parent identity; 28 successful native OPEN/CLOSE PNGs for the 14 frozen positions; one valid QQE pane; legible MBB/TB price overlay; no historical indicator alert storm; and hash-bound source/indicator/report/sidecars/charts/manifest.

This remains a diagnostic replay of an already killed strategy. It cannot authorize parameter rescue, economic re-evaluation, validation/holdout access, or promotion.
