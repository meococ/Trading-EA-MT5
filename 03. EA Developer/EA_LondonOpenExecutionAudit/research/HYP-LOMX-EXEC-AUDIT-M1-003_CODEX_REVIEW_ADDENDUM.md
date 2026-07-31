# HYP-LOMX-EXEC-AUDIT-M1-003 — Codex review correction addendum

## Status

`CORRECTIVE_AUDIT_V2_PASS__TERMINAL_PARK_AND_PARENT_KILL_UNCHANGED`

This is an append-only correction to the immutable original readout. It does not
modify the EA, preregistration, task packets, receipts, Model-0 runs, or the
economic verdict. A fresh-context Codex code reviewer inspected the complete
session and returned `CHANGES_REQUIRED`; the findings below were then verified
against the source, Grok packet, run manifests, receipts, telemetry, lifecycle
rows, and MT5 reports.

## Corrected review statement

The original readout statement that the independent Grok forensic review
"PASSed after pre-outcome fixes" is incorrect. The cited Grok packet has verdict
`BLOCKED_BY_FINDINGS` and reviewed source SHA256
`651413...`, not the final source SHA256
`C99D18C7912384D529CF651214EBF636211536957D7F4241831CB2418D28EEC1`.
The engineering gate truthfully records the narrower fact: seven Grok findings
were addressed before the valid Model-0 runs. It does not record a Grok PASS on
the final source. The Grok packet remains useful as an advisory pre-run review,
not as final independent approval.

## Codex findings and disposition

| Priority | Finding | Why it matters | Disposition |
|---|---|---|---|
| Must fix | V1 accepted count/timing reconciliation without binding the exact authorized run, Model 0, 2016-2020 window, final source, receipt, report, or individual deal identities. | A substituted artifact or same-count corruption could falsely pass. | Fixed by `validate_execution_audit_v2.py`. |
| Must fix | V1 dashboard derived PASS from percentages and counts rather than a provenance/identity validator. | A descriptive chart must not be the acceptance authority. | Fixed by `render_execution_audit_dashboard_v2.py`; it reruns V2 live before writing PASS. |
| Must fix | Original readout overstated the Grok verdict. | Review provenance must be exact. | Corrected by this immutable addendum and current workspace pointers; the terminal registry row remains immutable. |
| Must fix | First V2 draft reconciled DEAL rows but only counted `ENTRY_SUBMIT`/`EXIT_SUBMIT`. | Same-count corruption in submission identity, price, volume, or position could pass. | Fixed by exact REQUEST->SUBMIT->DEAL joins and entry/exit submission corruption tests. |
| Should fix | Canonical AlphaFactory TCA/datalog summaries do not understand `DecisionTelemetry` + `LifecycleTrades` lifecycle-v3 and can emit misleading zeros. | Zero from an unsupported adapter is not observed zero execution cost. | V2 declares `UNSUPPORTED_NA_FOR_DECISIONTELEMETRY_LIFECYCLEV3` and removes those economics from the audit dashboard. A shared adapter remains backlog work. |
| Should fix | The terminal EA was not built to prove restart recovery, partial-fill residual handling, or arbitrary position-history traversal. | Those are production-safety surfaces, not required to verify these completed single-fill tester paths. | Do not mutate this terminal ID. Any production-oriented successor needs a fresh mechanism/ID and preregistered fault tests. |
| Optional | A generic entry-latency label would be misleading for the 15:30 LATE_FIX branch because the signal is observed at 08:31. | Formation-to-entry delay and gate-to-fill delay are different quantities. | A future successor should expose both fields explicitly. |

## V2 acceptance evidence

- Validator: `research/validate_execution_audit_v2.py`, SHA256
  `56D2BCD947D7A848408D50E8446DC2374AF0DBA8AABF1E54B9C5C5E75120F3D4`.
- V2 result: `research/evidence/HYP-LOMX-EXEC-AUDIT-M1-003_MODEL0_AUDIT_READOUT_V2.json`,
  SHA256 `67A91D4C1B5A90E4705AB1368CD368145387BA8485F5EA3E214638F16F2B1813`.
- Dashboard data: `research/evidence/HYP-LOMX-EXEC-AUDIT-M1-003_EXECUTION_DASHBOARD_V2.json`,
  SHA256 `F3736280CAAA8F3BAC2C20B36B14F1D2FF7D3F07E924B37D99A70046E89440BE`.
- Dashboard image: `research/evidence/HYP-LOMX-EXEC-AUDIT-M1-003_EXECUTION_DASHBOARD_V2.png`,
  SHA256 `5B14171652A2178AE6FF1C9B4BDB163EB7AC32D3344B5691AF10D016FFA3D67B`.
- Focused suite: `31 passed` (`11` original contract tests plus `20` V2
  provenance, REQUEST->SUBMIT->DEAL identity, corruption, rejection, DST, and
  dashboard-gate tests).

V2 revalidated the four immutable authorized runs and 5,171 completed
lifecycles. It binds the exact run IDs, manifests, Model 0, M1, 2016-2020
window, overrides, final source, source/EX5/config/report snapshots, receipts,
task packets, sidecar hashes and row counts. It then reconciles each frozen
REQUEST->SUBMIT->DEAL path plus every entry/exit deal ID, order ID, position ID,
side, time, price, and volume across DecisionTelemetry, lifecycle-v3, and the
parsed MT5 report. It also rejects
execution rejection rows, duplicate/substituted IDs, same-count price changes,
clock/DST mismatches, non-final close paths, and diagnostic-counter drift.

The four runs still pass the implemented trade narrative. This is now a
stronger engineering statement, not a profitability claim. "First eligible
tick" is not claimed beyond the event timestamp plus the EA's `OnTick` gate;
performance/economics, validation, holdout, optimization, promotion, paper, and
live authority remain false. Parent `HYP-LOMX-MULTI-M1-002` remains killed.

## Development backlog by owner surface

1. `02. AlphaFactory/analysis/`: add an explicitly selected lifecycle-v3
   adapter for canonical TCA/datalog analysis, or return `UNSUPPORTED_NA` rather
   than zero-valued summaries. This is shared-harness work and was not changed
   inside the terminal EA correction.
2. Fresh audit successor only: preregister partial fills, residual close,
   restart/state recovery, history traversal, and ownership-conflict fault
   injection before any production-readiness claim.
3. Fresh telemetry schema only: split `formation_to_entry_minutes` from
   `eligible_gate_to_request_ms` and `request_to_deal_ms`.
4. Keep the current source and four Model-0 runs immutable. A materially new
   execution or economic question requires a fresh hypothesis ID; no same-ID
   rerun or post-hoc rescue is authorized.
