# 2026-09-12 — HYP-AMA-XAU-M15-001 control screen: KILL; first fully-completed governed loop

## Verdict

`HYP-AMA-XAU-M15-001` (EA_AMA, XAUUSD M15, Kaufman adaptive-MA cross + ATR stop
+ time exit) → **killed** at Model 0, registry row updated (screened→killed,
validator green). First hypothesis to traverse the **entire** governed chain:
preflight → compile → isolate backtest → journal/data-quality → non-repaint
audit → report-bound cost artifact → unified validation → ledger.

Run `20260912_024554` (governed, portable isolate, MetaQuotes-Demo):

| Metric | Value |
|---|---|
| Window | all-available; history 2004.06.11 → 2026.09.10 |
| Trades | 22,245 (~7.5/week — **below** 10–40 cadence band) |
| Report PF | 0.914; Net -7,297.85 USD; Max DD 74.5%; WR 31.7% |
| History Quality | **98%** (gate >97 — XAUUSD clean, no stub years) |
| Cost-bound PF | **0.59** @x1.0 / **0.49** @x1.5 / **0.41** @x2.0 |
| Monte Carlo p95 DD | 79.1% (limit 20) |
| Robustness pass rate | 14.3% |
| Exposure | 42 overnight + 16 weekend-crossing (contract forbids) |
| Unified verdict | REVIEW — 10 FAIL / 2 BLOCKED / 2 PASS of 14 gates |

Disqualifying on economics under every stress tier. No post-hoc rescue.
Registry: `state=killed`, `verdict=KILLED_AT_MODEL_0`, run bound.

## Evidence chain that now works end-to-end

- Lifecycle telemetry v3 reconciled **44,490/44,490** report deals
  (position-side `order_type` on closes, real `risk_pts`/`initial_risk_account`,
  final-close via post-deal position existence).
- Cost evidence tier: `VERIFIED` spread (raw tick CSV) +
  `VERIFIED_RESEARCH_PROXY` slippage (quote-latency pairs) + commission
  (observed 0.00 → conservative $7/lot-RT bound; over-cost, never under).
- `verified_cost_artifact.json` bound to report SHA + run identity;
  `promotion_eligible=false` (research-proxy tier, as designed).

## Pipeline repairs landed this iteration

1. `post_run_cleanup.ps1` — no longer deletes the **current run's** staged EX5
   (engine needs it for post-run identity verify); held lock files are no
   longer misclassified as orphans (fail-open read on `FileShare.None`).
2. `alpha.ps1` journal delta — tester/agent log dirs are seeded pre-snapshot
   and roots re-derived at export (MT5 recreates them per run); recreated-file
   detection via head-region hash, not just length-vs-offset.
3. `audit_mql5_nonrepaint.py` — the `DATA_EPOCH_D0_SERIES_PROOF` `CopyTime`
   first-date probe is authorized by a valid `data_quality_contract` (not only
   collection-only authority); forbidden-API scan scoped to the probe's
   enclosing function so real EAs using `CTrade` pass.
4. `quant_analyzer.py` — skips report rows with empty time cells (initial
   balance deal); previously crashed on first XAU report.
5. `build_control_packet.py` — real fingerprint formulas (report-basis
   server/account/broker, data-drift pin `symbol|period|from|to|model|
   quality|bars|ticks|digits|point|pip`), transitive include-closure resolver,
   cost manifest regenerated from measured CSV evidence each build.
6. `research_loop_engine.ps1` — orphan sweep before factory-process assert
   (bare `terminal64.exe` left by post-run attach probes is swept when no live
   backtest lock is held); `Assert-EvidenceUnchanged` now passes the bound
   source into `Get-GitSnapshot` (was comparing GOAL-only provenance against a
   GOAL+source receipt — structurally unpassable).

## Process note for next cells

- Per-cell requirements: contract JSON + frozen prereg + registry screened row
  + `build_control_packet.py` args (`--magic --spread-points --pip --digits
  --point --history-quality --bars --ticks`) + cost CSVs in
  `research/evidence/` + EA wired with lifecycle-v3 AND `EmitD0SeriesProof`.
- `data_fingerprint` pin requires a prior measured run — chicken-and-egg is
  resolved by running once, reading manifest values, rebuilding packet, re-run.
- MetaQuotes-Demo charges 0.00 commission; validator's `positive()` means the
  conservative-bound proxy is mandatory on this broker.
- XAUUSD tick history on MQ-Demo is sparse pre-2016 — raw spread CSV sampled a
  recent window; semantics documented in manifest note.
