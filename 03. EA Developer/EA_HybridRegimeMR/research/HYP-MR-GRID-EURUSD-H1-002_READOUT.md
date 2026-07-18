# READOUT — HYP-MR-GRID-EURUSD-H1-002 (exhaustive grid falsification)

Date: 2026-07-17 · Verdict: **KILL_FAMILY_EXHAUSTIVE_AT_OFFLINE_GRID** ·
Family `regime-gated-detrended-z-mean-reversion` is **CLOSED_EXHAUSTIVE**.
No `.mq5`, no compile, no Model 0, holdout 2023+ never loaded. Cost tier
UNVERIFIED_PROXY; `promotion_eligible=false`.

## What ran

Owner-directed (2026-07-17 scope change) closure instrument, frozen
pre-outcome in `HYP-MR-GRID-EURUSD-H1-002_GRID_PLAN.md`
(SHA `FC017E4FC4085A2673BF9158C2A8DE5CB827A48EA21213EA49C17CD1705176D0`)
after 2-critic adversarial review (legality + statistics, Opus max):

- Stage 1: full cross W{60,80,100,125,150} × Z{1.6,1.8,2.0,2.2,2.4} ×
  K_sl{1.5,2.0,2.5} × TP_cap{1.2,1.5,1.8} × k_ts{1.5,2.0,3.0} ×
  trailing{on,off} at session [7,16) = 1350 cells × 6 arms (control, gated
  ensemble, 4 single gates) = **8100 simulations**, ~110 s on 18 workers.
- Stage 2 (gate subsets/thresholds/session shifts): **skipped by the frozen
  routing rule** — zero cells had any arm with combined gross PF ≥ 1.25 and
  n ≥ 100.
- Every simulation logged to `trials/trial_log.jsonl` (trial_ids 1–8100);
  DSR computed with N = 8100, V[SR] across all arms.

## Results (artifact `20260717_102641_HYP_MR_GRID_002_SWEEP.json`, SHA `71523C90148A37911D677AB8B71BD13B0497B3DB3225CED2EDE9B8CFBCF92B31`)

| Fact | Value |
|---|---|
| Simulations | 8100 (Stage-1 complete; Stage-2 empty per rule) |
| Arms with gross PF ≥ 1.25 (necessary condition) | **0** |
| Max gross PF anywhere | 1.2476 (median 0.8902) |
| Arms with gross PF ≥ 1.0 | 891 / 8100 (11%) |
| Max net PF@x1 anywhere | 1.0991 (median 0.7741) |
| Best deflated arm | DSR 0.0129 (floor 0.95), exp −0.047R, fails 10/11 conjunction checks |
| Flag passers | 0 |

The single best deflated arm (`W100_Z2.4_SL2.5_TP1.8_TS3.0_TR0`, gated) has
n=48, gross PF 1.03, negative expectancy after costs, and LOO PF 0.84 — a
tail-of-8100 noise artifact, exactly what DSR exists to reject.

## Interpretation

1. The 001 kill generalizes: across the ENTIRE pre-declared variant space —
   every window, entry threshold, stop, target cap, time-stop, trailing
   setting, and every gate/single-gate combination — the detrended-z MR object
   on EURUSD H1 never reaches the pre-cost bar that the post-cost gate
   requires. The failure is the OBJECT, not the tuning.
2. Gate ablation adds nothing: no single gate, nor the ensemble, lifts any
   cell to the necessary condition. The regime-gating thesis is dead at family
   level with exhaustive coverage.
3. The Owner's "mọi biến thể và khả năng" question is answered with evidence:
   8100 counted trials, deflated verdict, default-KILL design that a survivor
   could still have escaped — none did.

## Do-not-revive scope (family closure)

`CLOSED_EXHAUSTIVE`: no further OHLC regime-gated mean-reversion variant on
majors/gold opens without a MATERIALLY DIFFERENT information set (e.g.
verified order-flow / options-implied state / paid PIT data) plus a fresh
Owner-scoped prereg. Forbidden as before: M15/lower TF, XAUUSD, CI/Hurst
gates, re-costing, post-hoc cells. The sealed 2023+ holdout was never opened
and stays sealed.

## Artifacts

- Sweep JSON: `evidence/20260717_102641_HYP_MR_GRID_002_SWEEP.json` (SHA above)
- Full results: `evidence/20260717_102352_HYP_MR_GRID_002_RESULTS.jsonl`
  (8100 rows; SHA in sweep JSON) — note: the run crashed at the final
  artifact dump on a numpy-bool serialization bug AFTER results+trial-log were
  written; the artifact was re-emitted by pure post-processing of the on-disk
  results (no re-simulation, no duplicate trial-log rows). Serializer fixed in
  `mr_grid_sweep.py`.
- Trial log: `trials/trial_log.jsonl` (2 rows for 001 + 8100 rows for 002)
- Engine: `mr_grid_engine.v1`, regression-verified vs frozen 001 outputs
- `grid_cache/` (reproducible feature caches) deleted post-run; bit-exact
  reproducible from the SHA-bound parquets + frozen code.
