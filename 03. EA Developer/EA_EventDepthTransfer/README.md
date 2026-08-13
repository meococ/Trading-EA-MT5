# EA_EventDepthTransfer

Research package for an event-driven EURUSD scalp whose direction is determined by
post-release transfer of resting CME 6E liquidity below the top of book.

Current state: **HYP008/HYP009 terminal DESIGN kill**. HYP007 independently
reconciled the source-only artifacts. HYP008 PRIMARY was engineering-valid at
100% History Quality and already failed the frozen economics. HYP009 added only
read-only D0 proof after that outcome existed, so it cannot reset outcome
blindness; its PRIMARY/REVERSE pair is a same-mapping confirmation.

HYP003 remains parked at its free DESIGN metadata quote gate. HYP007 does not
retroactively pass it; it supplied the hash-reconciled source ledger used by the
now-terminal HYP008/HYP009 mapping.

HYP004/HYP005 incident and quarantine records are preserved. HYP009 consumed only
the HYP007 reconciled ledger, never a partial or direct incident artifact. See
`research/HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004_UNAUTHORIZED_ACQUISITION_INTERRUPTION_RECEIPT.md`.

HYP009 PRIMARY closed 317 trades. Frozen complete-cost results were base PF 0.9147,
net `-$415.50`; x1.5 PF 0.7101; x2 PF 0.5582. REVERSE base PF was 0.3846.
Although the primary sign produced `+$2,008` raw-mid information, `$2,423.50` of
complete execution cost erased it. Verdict is `KILL_FROZEN_MAPPING`; validation,
optimization, paper/live trading and promotion are forbidden. See
`research/HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009_MODEL0_RESULT.md`.

The current EA binary and both HYP009 task packets are fail-closed; rerun is
forbidden.

Do not revive this exact depth sign at T+60/T+120 through score, event/session/day,
direction, degraded-cell, timing, hold, SL/TP or sizing changes. The active research
loop must use a materially independent information mechanism. The live source now
contains `AF_MAPPING_TERMINAL=true` and fails `OnInit`; it remains compile-valid only
as an auditable terminal artifact.
