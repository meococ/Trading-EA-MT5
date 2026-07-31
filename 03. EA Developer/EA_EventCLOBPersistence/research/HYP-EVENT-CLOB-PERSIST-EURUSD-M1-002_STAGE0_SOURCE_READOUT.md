# Stage 0B-D source readout — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002

Verdict: `PARK_STAGE0B_DESIGN_SOURCE_OR_CADENCE`

## Acquisition reconciliation

- Canonical event pairs: 329/329.
- Canonical request identities: 658/658.
- Every identity was reconciled to the frozen manifest, local DBN size/hash, record count and exact PRE/LATE bounds.

## Source coverage and quality

- PRE nonempty: 326/329 (0.990881).
- LATE nonempty: 326/329 (0.990881).
- Paired nonempty: 326/329 (0.990881).
- Source-quality paired events: 1.
- Source-quality failures among paired nonempty events: 325.
- Sign/feature-eligible events: 1.
- Sign/feature-ineligible events after source quality: 0.
- Eligible cadence: 0.009576 events per elapsed week over 104.428571 weeks.

## Gate result

- request_identity_count: PASS.
- event_pair_count: PASS.
- pre_nonempty_coverage: PASS.
- late_nonempty_coverage: PASS.
- paired_nonempty_event_coverage: PASS.
- feature_eligible_count: FAIL.
- feature_eligible_cadence: FAIL.
- fatal_source_integrity_failures: FAIL.
- prohibited_reads: PASS.

This is an outcome-blind source and feature-supply verdict only. It is not a market edge verdict, and no EURUSD outcome was opened.
The source campaign remains bound to the Owner USD 3.50 ceiling and DEDDE7F2 authorization basis.
Validation source remains sealed. Stage 1 requires a separate pre-outcome task packet and Lead Quant authority after independent review of this evidence.
