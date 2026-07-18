# PROBE PLAN — HYP-MR-REGIME-EURUSD-H1-001 (frozen before any outcome read)

Status: FROZEN 2026-07-17, before any PnL/outcome of this object was computed.
Author: agent (Owner-directed MR v3 lane). This document is the anti-gate-shopping
instrument for the cheap offline probe; its SHA256 is bound into the registry
`idea` row. Any change after outcomes are read invalidates the probe.

## 1. Identity

- `hypothesis_id`: HYP-MR-REGIME-EURUSD-H1-001
- `ea_name`: EA_HybridRegimeMR (research-only package; no `.mq5` exists or is
  authorized at this stage)
- Symbol / TF: EURUSD H1 (single asset; XAUUSD is explicitly deferred behind
  EURUSD survival per spec §12 and the de-dup audit)
- Spec source: `05. Playbook/Strategy/MR/Hybrid_Regime_MR_XAUUSD_Forex_v3_EA_Ready_Spec.md`
  (commit 2b9dbc1) + reference skeleton `05. Playbook/Strategy/MR/mr_system/`
- Thesis: temporary, regime-conditional mean reversion of the detrended series
  D = Close − SMA(W) on H1, tradable only when a trend/vol/half-life gate
  ensemble says the market is range-like. Gold/EURUSD daily is near random walk
  (spec §0); the ensemble carries the entire edge burden.

## 2. De-dup status (PARTIAL — burden inverted)

The canonical registry has zero mean-reversion rows, but the workspace
graveyard contains the same entry object and the same gating thesis:

- `HYP-H1-LOWVOL-DONCHIAN-MR-001` — only prior H1 MR (channel fade, N=13,
  KILLED_AT_MODEL_0 PF 0.40)
- `HYP-EMA-STRETCH-FADE-M15-001` — normalized deviation-from-MA fade
  (KILLED_AT_MODEL_0 PF 0.84, N=1980)
- `HYP-AUDNZD-H1-RESIDUAL-ZMR-001`, `HYP-XS-USD-RESIDUAL-*` — residual z-MR
  (offline joint-screen kill; "densify XS z / AUDNZD z" forbidden)
- `HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001` — ATR-percentile state
  gate (cadence kill)
- Legacy S-log: S652/S653 ChopMeanRevert (trendiness-gated MR, dead on XAU+UJ),
  S634 HurstRegime (persistence gate, dead), S540/S541 MeanRevGold (XAU BB-2σ
  fade, breakeven), S114/S115 Nocturne + S109 Nighthawk (EUR/GBP band MR, dead),
  S680/S681 ADRExhaust, S613-615 VPReversion, S616 LBMAAMFix
- do_not_repeat B: "XAU ATR filter deletes ~90% cadence"

Consequence (frozen pass condition): the regime ensemble must prove
INCREMENTAL value — the gated challenger must beat a matched always-on control
on the identical entry object by the frozen margin below. If the un-gated
object is dead AND the gates do not rescue it, this collapses into the killed
regime-gated-MR family: terminal at probe, no MQL5, no Model 0.

## 3. Data (Stage B0 evidence, hash-bound)

- `evidence/EURUSD_H1_2015_now.parquet`, `_H4_`, `_M1_` — pulled 2026-07-17
  from FivePercentOnline-Real (installed C terminal, demo, read-only, no
  orders). SHAs + row counts in `evidence/EURUSD_PULL_AUDIT.json`.
- Server→UTC offset model (empirically verified on every week 2015–2026 via
  the Friday-17:00-NY close anchor; 99.17% match, residuals = holiday early
  closes): server = UTC+2 winter / UTC+3 summer with **EU DST calendar ≤2023
  and US DST calendar ≥2024** (broker changed convention in 2024).
- Historical spread column is NOT usable: 2023–2026 is ~99% zero-filled
  (zero/missing ≠ real zero), 2015–2019 resembles a ~0.7–1.0 pip standard
  feed. Therefore: no per-bar spread gate in either arm, and costs come from
  the frozen proxy below.

## 4. Frozen decision surface (ONE config; tuning budget = 0)

All parameters are the `mr_system/config/params.yml` defaults. No grid.
Every engine evaluation (control, challenger, and any reruns) is appended to
`trials/trial_log.jsonl`.

Entry object (both arms):
- Features on closed H1 bars only; decision at bar t close, fill at bar t+1 open.
- D = Close − SMA(100); σ = StdDev(D, 100, ddof=0); z = D/σ; σ=0 → no signal.
- LONG if z ≤ −2.0; SHORT if z ≥ +2.0. One position per symbol; no adds.
- Session (both arms): entry-bar OPEN time (UTC, converted per §3 model) hour
  in [7,16). Position management runs 24/5.
- Gap guard (both arms): |open(t+1) − close(t)| ≥ 4×ATR14(t) → no entry.
- News filter: OFF (v0; calendar not connected — grid deferred).

Regime gates (CHALLENGER ONLY — the object under test):
1. ADX(14, H1, Wilder) at t < 23
2. ADX(14, H4, Wilder) at last closed H4 ≤ t < 28
3. ATR(14, H1) percentile within prior 250 bars in [25, 75]
4. Rolling half-life of D (window 100, Δregression) in [4, 48] bars, λ<0

Exits (both arms, identical):
- SL = entry ∓ 2.0×ATR14(t) (frozen at entry); R = |entry − SL|.
- TP = nearer of {μ_e ∓ 0.2σ_e (frozen at entry, must be on favorable side and
  ≥ 2×spread_p50_proxy=0.2 pip from entry), entry ± 1.5R}. Server-side limits.
- Intrabar resolution worst-case: SL checked BEFORE TP within each bar.
- Time-stop: min(ceil(2.0 × HL_e), bars to 5-night cap) bars → close at next open.
  If HL_e is undefined at entry (λ ≥ 0 — possible in the control arm, which has
  no HL gate), the HL term is +∞ and the night-cap bound alone applies. The
  night-cap counts charged rollover EVENTS (Fri→Mon = 1 event, Wednesday = 1
  event charged ×3 swap); the position closes at the last bar close before a
  6th event would be charged. Trades still open at the end of loaded data
  (2022-12-31) force-close at the last bar and are flagged `DATA_END`.
  Trades are assigned to a split by ENTRY time; a Train entry may manage into
  2021-2022 bars but never into the sealed holdout.
- C-1 minimal core runs WITHOUT trailing and re-entry cooldown (both arms
  symmetric). If the directional read survives, C-2 adds trailing
  (+0.8R at close → SL = close ∓ 1.2×ATR14(t), monotonic, 1×/bar) and
  re-entry cooldown (z must close ≥1 bar inside ±2.0 after exit) to BOTH arms
  and the confirmatory run uses the full exit set. C-2 additions are frozen
  here, pre-outcome; they are not tunable afterwards.

Risk basis: RiskPct = 0.25% per trade (workspace probe convention), results
reported in R plus DD% at this risk. No portfolio overlays (single asset).

## 5. Frozen cost model

x1 (base) per-trade round-turn cost = **1.5 pips** (workspace precedent:
CME/CFTC EUR lanes CostPipsX1=EUR1.5). This covers raw-ECN 0.2 pip spread +
$7 RT (~0.7 pip) + p75-tier slippage, or a standard 0.7–1.0 pip feed +
slippage, with margin — chosen because the broker's historical spread column
is unusable (§3). Swap: −$8/lot/night ≈ 0.8 pip per charged rollover
(server-midnight crossing, computed on time_server), Wednesday rollover
charges ×3 (costs.yml triple_day=WED); positive-side swap treated as 0
(conservative). Stress axis: total per-trade cost ×1.5 and ×2.
Status: UNVERIFIED_PROXY — sufficient to KILL, never to promote.

## 6. Frozen windows

- Train: 2015-01-01 → 2020-12-31
- InternalValidation: 2021-01-01 → 2022-12-31
- Holdout: 2023-01-01 → now — **SEALED**; no bar of it is loaded by the probe.
- Cadence denominator: elapsed calendar weeks of each split.

## 7. Frozen kill gates (ALL must pass for SURVIVE)

| # | Gate | Threshold |
|---|---|---|
| 1 | Sample | ≥300 challenger trades over Train+Validation combined |
| 2 | Economics | challenger PF@x1 ≥ 1.25 AND expectancy ≥ +0.08R@x1, in Train AND Validation |
| 3 | Stress | challenger PF@x1.5 ≥ 1.25 AND PF@x2 ≥ 1.00 (Train AND Validation) |
| 4 | Concentration | no calendar year > 40% of total positive net PnL(R)@x1 |
| 5 | Incremental value | challenger PF@x1 ≥ control PF@x1 + 0.10 AND challenger net_R@x1 > control net_R@x1, in both splits |
| 6 | Cadence floor | challenger ≥ 0.7 trades/elapsed-week (single-asset honesty floor; EURUSD alone does NOT satisfy the 2–5/wk book GOAL — a SURVIVE is a component, not a sleeve) |
| 7 | Cadence ceiling sanity | ≤ 5 trades/week; above with weak PF ⇒ non-selective gates ⇒ KILL |

Relationship to the registry `acceptance_contract`: the registry schema pins
the contract to the workspace GOAL bar (min PF 1.30, 2–5 trades/week, max DD
8%, MC-P95 ≤ 8%) — that is the eventual PROMOTION bar for a Model-0 sleeve,
not the probe verdict instrument. This table is the probe verdict instrument.
An EURUSD-only survivor at ~0.7–2 trades/week does NOT yet meet the frozen
contract; meeting it requires later book-level construction under new
hypotheses. No narrative excuse may substitute for that arithmetic.

- KILL_AT_OFFLINE_PROBE: any gate fails.
- PARK: infrastructural ambiguity only (e.g. 200–299 trades with all economic
  gates passing, or unresolved indicator parity on a marginal pass). Parking
  reasons must be pre-listed here; "PF almost passed" is a KILL, not a PARK.
- SURVIVE: all gates pass → freeze full PREREG (template) → screened path.
  Model 0 additionally requires verified cost (currently BLOCKED for EURUSD).

## 8. Exclusions (hard, from de-dup)

- No M15 or lower timeframe, now or as rescue.
- Choppiness Index / Hurst / any new trendiness index must NOT enter the entry
  gate (S652/S653/S634 are dead); weekly diagnostics only, and none in v0.
- No post-hoc hour/day/year/session veto; no threshold change from this
  probe's readout — any such change is a NEW hypothesis_id.
- Entry object stays std-normalized detrended-z; no drift to ADR%/channel/
  band-extreme geometries (ADRExhaust/Donchian are dead).
- XAUUSD only after EURUSD survival, as a separate hypothesis.
- The always-on control is a falsification instrument, not a deliverable.

## 9. Engine contract (what Stage C must honor)

Next-open fill with cost applied per trade; SL-first worst-case intrabar;
μ_e/σ_e/R/HL_e frozen at entry; features end at bar t; session by entry-bar
UTC open hour; H4 gate consumes the last H4 bar whose close time ≤ t (merge
backward on availability, no forming H4 bar); warm-up ≥ 350 H1 bars skipped;
no demo/synthetic data anywhere; trade ledger with feature_time (t close),
decision_time (t close), execution_time (t+1 open). Contract tests must cover:
next-open fill, SL-first, session boundary at hour 16, H4 availability, and
frozen-at-entry exits.

## 10. Artifacts the probe must emit

- `evidence/<ts>_HYP_MR_REGIME_EURUSD_H1_001_PROBE.json`
  (`schema_version=mr_regime_gated_offline_probe.v1`, `promotion_eligible=false`,
  `cost_status=UNVERIFIED_PROXY`, control+challenger metrics per split, gate
  table, verdict) — hash-bound into the registry transition.
- `evidence/<ts>_HYP_MR_REGIME_EURUSD_H1_001_TRADES.csv` (both arms, 3 timestamps).
- `trials/trial_log.jsonl` — every evaluation, appended at run time.
- `HYP-MR-REGIME-EURUSD-H1-001_READOUT.md` at verdict.
