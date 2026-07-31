# HYP-LOMX-EXEC-AUDIT-M1-003 — Frozen Pre-Outcome Audit Amendment V2

Status: **FROZEN BEFORE REVISED SOURCE, VALIDATOR, OR ANY MODEL-0 OUTPUT**  
Freeze date: 2026-07-30  
Base prereg:
`03. EA Developer/EA_LondonOpenExecutionAudit/research/HYP-LOMX-EXEC-AUDIT-M1-003_PREREG.md`,
SHA-256 `039178106824BD8F2610B55F6AA54DED0CCAB3CE688A77B12142A9C897AC209B`.

This V2 is a pre-outcome engineering amendment. No MT5 backtest has run. It
preserves every scenario, symbol, polarity, formation, entry, exit, split,
volume, attempt budget, authority boundary, and prohibition in the base
prereg. It only closes evidence false-PASS/false-FAIL gaps found during the
independent read-only MQL5 review.

Review artifact:
`.context/lomx_execution_audit_mql5_review_20260730/run3/grok-response.json`,
SHA-256 `9EABCD90113DF131DB92F4CCFD973C57F498770559E9762FF4149B735B33485F`.
The review ended normally with schema validation PASS and
`BLOCKED_BY_FINDINGS`; its economic-authority field remained false.

## V2 evidence amendments

1. Every `SIGNAL_READY` row must occur in the exact London 08:31 minute.
2. `MIDDAY` and `FULL_SESSION` entry requests must occur in the exact London
   08:31 minute. `LATE_FIX` entry requests must occur at or after 15:30 and
   strictly before 16:00.
3. A run cannot pass vacuously. Each of the four full-window scenario runs must
   have at least **1,000** `SIGNAL_READY`, entry request, actual entry deal,
   lifecycle OPEN, actual exit deal, and final lifecycle CLOSE rows. This is an
   engineering coverage floor below the parent arm population of roughly
   1,274–1,290 trades; it is not an economic selection threshold.
4. The canonical MT5 report Deals table must be parsed with the existing
   AlphaFactory report parser. Report entry and exit deal counts for the tested
   symbol must equal decision entry/exit deals and lifecycle OPEN/final CLOSE
   counts exactly.
5. Deal telemetry must derive actual deal side and London date from immutable
   deal history fields. Close rows must retain the stored entry direction and
   signal context by position identifier rather than reading mutable daily
   globals.
6. Final-close classification must use cumulative deal-history volume for the
   position through the current deal. It must not depend on whether the live
   Positions table has already removed the position at callback time.
7. Synthetic validator tests must prove fail-closed behavior for wrong signal
   minute, late MIDDAY/FULL entry, zero population, and report/sidecar count
   mismatch before Model 0 is authorized.

All base terminal verdicts remain unchanged. A V2 engineering PASS only proves
execution-fidelity coverage; HYP-LOMX-MULTI-M1-002 remains economically killed,
and validation/holdout, optimization, promotion, paper, and live remain closed.
