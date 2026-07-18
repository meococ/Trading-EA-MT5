# GRID PLAN — HYP-MR-GRID-EURUSD-H1-002 (FROZEN pre-outcome, 2026-07-17)

Frozen after adversarial legality + statistics review (workflow
`wf_fda817d3-e99`, 2 Opus critics) and BEFORE any grid outcome was read.
SHA256 of this file is bound into the registry row. No cell, axis, arm or
threshold may be added after any grid outcome is read; an attractive uncovered
variant is a NEW hypothesis, never an amendment to this run.

## 1. Authority and role (closure, not rescue)

- Owner directive 2026-07-17: "cả đội ngũ cần triển khai và tinh chỉnh,
  research chạy lại loop mọi biến thể và khả năng" — an explicit scope change
  after the terminal `HYP-MR-REGIME-EURUSD-H1-001` kill.
- Doctrinal mechanism: Owner scope change + NEW hypothesis_id + fresh frozen
  prereg + declared trial family (AGENTS.md §3; research_doctrine multiple-
  testing budget). `-001` stays killed and untouched. The same tune list that
  is forbidden as a `-001` rescue is permitted here ONLY because every cell is
  declared pre-outcome, every simulation is counted into the deflation family,
  and the verdict DEFAULTS to `KILL_FAMILY_EXHAUSTIVE`. The moment this run is
  used to cherry-pick one passing cell for promotion, it is illegal.
- Honest prior: the 001 control had gross PF < 1.0 on 657 trades and net ≤
  gross per arm, so discovery probability is low. The value is decisive
  coverage of the Owner's "every variant and possibility" with multiple
  testing priced in.

## 2. Identity

- `hypothesis_id` HYP-MR-GRID-EURUSD-H1-002 · `ea_name` EA_HybridRegimeMR ·
  same `feature_family` regime-gated-detrended-z-mean-reversion (deliberately —
  this is the family being closed).
- EURUSD H1 only. Data: FivePercent parquet (SHA-bound in the sweep artifact),
  2015-2022 only; Holdout 2023+ SEALED — 0 bars loaded, parquet read-filter
  enforced and asserted.
- Engine `mr_grid_engine.v1` — regression-verified to reproduce the frozen 001
  numbers exactly (control 503/154 trades PF 0.8596/0.8062; gated 59/23 PF
  0.6849/0.2471). Cost model unchanged from 001: x1 = 1.5 pips RT + 0.8
  pip/weighted rollover (Wed ×3, Fri→Mon=1), stress ×1.5/×2,
  `UNVERIFIED_PROXY` — KILL/FLAG-decision-grade only.

## 3. Stage 1 (full cross; session fixed at [7,16))

| Axis | Values |
|---|---|
| W | 60, 80, 100, 125, 150 |
| Z_entry | 1.6, 1.8, 2.0, 2.2, 2.4 |
| K_sl (×ATR14) | 1.5, 2.0, 2.5 |
| TP_cap (R) | 1.2, 1.5, 1.8 |
| k_ts (×HL) | 1.5, 2.0, 3.0 |
| Trailing | on, off |

= 1350 cells × SIX arms = **8100 simulations**. Arms per cell: `control`
(gates off), `gated` (ADX H1<23 ∧ ADX H4<28 ∧ ATR-pctile[25,75] ∧ HL[4,48]),
and four single-gate arms `g_adx1|g_adx4|g_atr|g_hl` (full within-cell
gate-family coverage — no gate effect can hide outside a sampled subset).
Session was REMOVED from Stage 1 per statistics critique (three ±1h windows
overlap ~78% of hours → correlated near-duplicate trials that pad N and bias
deflation); session shifts are Stage-2 conditional axes instead.

Fixed (not axes): TP buffer 0.2σ + validity ≥0.2 pip, gap guard 4×ATR,
cooldown ON, night-cap 5 events, risk 0.25%, news OFF, spread gate OFF
(historical spread column unusable). Invariants (guards from legality review):
entry object stays std-normalized detrended-z — Z=1.6 must not be reframed as
band/BB/ADR-extreme geometry; exit family stays {SL, TP-cap/TP-mean,
time-stop, optional MONOTONIC trailing} — no BE@1R / scale-out / MFE
stall-cut / giveback (separately killed exit-path family); trailing-off is the
minimal core, not BE@1R; the session triple is closed (no post-hoc Asian /
overnight / breakout windows — separately killed lanes).

## 4. Stage 2 (conditional; runs ONLY under the frozen routing rule)

Routing rule: a cell enters Stage 2 iff ANY of its six Stage-1 arms has
combined (pooled 2015-2022) gross PF ≥ 1.25 with n ≥ 100. Rationale: net ≤
gross per arm (costs strictly subtractive, trade set identical across tiers),
so cells failing this cannot reach the economic bar; skipping them is legal
elimination and they STILL count as evaluated trials.

Per routed cell: the 10 remaining gate on/off subsets (2⁴ minus the 6 already
run), 8 single-axis threshold variants (ADX-H1 {20,26}, ADX-H4 {24,32}, ATR
band {[15,85],[35,65]}, HL {[4,24],[8,48]}), and 4 session-shift arms
(control+gated at [6,15) and [8,17)). All Stage-2 simulations are appended to
the same trial log and the same deflation family.

## 5. Forbidden (hard exclusions — unchanged from 001 §8)

M15/lower TF; XAUUSD or any other symbol; CI/Hurst/any new trendiness index as
entry gate; news filter without connected point-in-time calendar; entry-
geometry drift (ADR%/Donchian/BB/VP); optimistic re-cost or using the
zero-filled 2023+ spread column as cost; loading any 2023+ bar; post-hoc
cells/axes; promoting any survivor without verified same-broker cost + Model 0.

## 6. Verdict instrument (frozen)

Primary series = POOLED 2015-2022 per-trade net-R@x1 of an arm (statistics
critique: under a 1350-cell search the 2021-2022 split is optimized-against
and no longer OOS; the sealed 2023+ holdout is the only true OOS). Two-split
metrics are reported as diagnostics only.

**Survivor conjunction** (ALL required, single arm):
n ≥ 300 combined; train n ≥ 150 and validation n ≥ 50 (floors); gross PF ≥
1.25; net PF@x1 ≥ 1.25; expectancy ≥ +0.08R; PF@x1.5 ≥ 1.25; PF@x2 ≥ 1.00;
≥ 6 of 8 calendar years positive net R; no positive year > 40% of positive
net R; leave-one-out (drop single largest winner) PF@x1 ≥ 1.10 and expectancy
≥ 0; top-1 winner ≤ 20% of gross positive sum; **DSR ≥ 0.95**.

**DSR convention (frozen):** per-trade SR; PSR with skew and non-excess
kurtosis (radicand ≤ 0 ⇒ fail, not skip); SR* = E[max SR] over N trials with
V[SR] estimated across ALL evaluated arms' SRs; **N = every executed
simulation in the campaign (stages 1+2, controls and failures included; cost
tiers are NOT separate trials)**. Raw N is deliberately conservative under
correlated trials (higher bar → protects against the expensive error, a false
survivor); implementation `mr_dsr.py` (self-tested vs the paper's E[max]
value). If a passer emerges: PBO (CSCV) ≤ 0.5 co-primary and a lag-1
autocorrelation haircut on effective n if |ρ₁| > 0.2, computed at flag time
from deterministic re-simulation of the flagged cell (engine is seedless and
deterministic; per-trade arrays are reproducible bit-exactly on demand).

**Verdicts:** no passer → `KILL_FAMILY_EXHAUSTIVE_AT_OFFLINE_GRID`: family
CLOSED_EXHAUSTIVE; no further OHLC-MR variant without a materially different
information set + fresh prereg. Passer(s) → `FLAG_FOR_HOLDOUT_PREREG_REQUIRED`:
registry stays `probe` with the flag recorded; opening the sealed 2023+
holdout, `.mq5`, Model 0 or any promotion step requires a fresh Owner-approved
prereg + verified cost + MT5 indicator parity. PARK is not available (sample
ambiguity is priced by DSR). No mid-run peeking alters the grid: the sweep
runs to completion regardless of intermediate results.

## 7. Artifacts

Per-simulation trial-log rows (trial_id, cell_id, arm, session, n, gross/net
PFs, exp, SR, skew, kurt, LOO, top1-share) appended to `trials/trial_log.jsonl`;
full results JSONL + hash-bound sweep JSON (axes, routing, trial accounting,
best-deflated, verdict) under `research/evidence/`; readout + single registry
transition at verdict; hot.md + do_not_repeat updates. `grid_cache/` holds
reproducible feature caches (not evidence, deletable).
