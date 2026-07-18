# READOUT — HYP-MR-REGIME-EURUSD-H1-001

Date: 2026-07-17 · Verdict: **KILL_AT_OFFLINE_PROBE** · No `.mq5`, no compile,
no Model 0, no holdout access. Cost tier: UNVERIFIED_PROXY (KILL-decision-grade
only). `promotion_eligible=false`.

## Object

Owner MR v3 spec (`05. Playbook/Strategy/MR/`, commit 2b9dbc1) Variant A:
regime-gated mean reversion on EURUSD H1. Entry object: z = (Close −
SMA(100))/σ_D, fade at |z| ≥ 2.0, fill next-bar open. Challenger gates:
ADX(14,H1) < 23, ADX(14,H4) < 28, ATR-percentile(250) ∈ [25,75], rolling
half-life(D) ∈ [4,48]. Exits (both arms): SL 2×ATR14, TP nearer-of(μ_e−0.2σ_e,
1.5R), trailing +0.8R→1.2×ATR, time-stop min(⌈2·HL_e⌉, 5-night cap), re-entry
cooldown. Cost x1 = 1.5 pips RT + 0.8 pip/weighted rollover (Wed ×3).
Frozen pre-outcome in `HYP-MR-REGIME-EURUSD-H1-001_PROBE_PLAN_V2.md`
(SHA `75917FDA78031E75A9CCA9EC7B66BD3A208AC7E1258B553669E33E28793600CA`).

## Data

FivePercentOnline-Real demo bars (installed C terminal, read-only, no orders),
D-portable parquet, SHA-bound in `evidence/EURUSD_PULL_AUDIT.json`. H1 71,785 /
H4 17,965 / M1 4,293,916 rows, 2015-01-02 → 2026-07-17. Probe loaded ONLY
bars < 2023-01-01 (parquet read filter); holdout_bars_loaded = 0.
Server→UTC offset verified empirically on every week (Friday-17:00-NY close
anchor, 99.17% match, residuals = holiday early closes): UTC+2/+3 with EU DST
calendar ≤ 2023, US DST calendar ≥ 2024 (broker changed convention in 2024).
Historical spread column is unusable (2023+ ~99% zero-filled; 2015–2019
resembles a 0.7–1.0 pip standard feed) → per-bar spread gate OFF in both arms,
frozen cost proxy used instead.

## Engine

`mr_probe_engine.v1` + `mr_indicators.py` (math copied from the reviewed
mr_system skeleton; detrend/half-life/ATR-percentile leakage-clean). Contract
tests 16/16 PASS (`tests/test_mr_probe_contract.py`): next-open fill, SL-first
worst case, session half-open boundary at hour 16, H4 availability (no forming
bar), frozen-at-entry TP, time-stop, night-cap events ≤5, Wednesday ×3 swap
weight, cooldown, challenger-gate isolation. ADX/ATR ↔ MT5 iADX/iATR parity
remains UNVERIFIED — a precondition for trusting a SURVIVE only; this KILL is
robust to small indicator misalignment (margins below are catastrophic, and
the control arm carries no indicator gates at all).

## Results (run `20260717_075658`, artifact SHA `113A2B31FC426B7B1929C6892911E982E7200BACBF4D7AA71E8EA9CF9B20F062`)

| Arm / split | N | tpw | gross PF | PF@x1 | PF@x1.5 | PF@x2 | exp@x1 (R) | net R@x1 |
|---|---|---|---|---|---|---|---|---|
| Control train 2015–2020 | 503 | 1.61 | 0.981 | 0.860 | 0.805 | 0.753 | −0.074 | −37.3 |
| Control validation 2021–2022 | 154 | 1.48 | 0.923 | 0.806 | 0.754 | 0.704 | −0.098 | −15.2 |
| Challenger train | 59 | 0.19 | 0.802 | 0.685 | 0.633 | 0.586 | −0.175 | −10.3 |
| Challenger validation | 23 | 0.22 | 0.289 | 0.247 | 0.229 | 0.213 | −0.543 | −12.5 |

Gate table: 6/7 FAIL (sample 82 < 300; economics; stress; year concentration
1.0 — only 2018 positive; incremental value vs control INVERTED in both
splits; cadence floor 0.196 < 0.7). Only the cadence ceiling passed.

## Interpretation

1. The un-gated detrended-z fade object is dead on EURUSD H1 (gross PF < 1
   before any cost) — consistent with the graveyard (S540/S541 MeanRevGold
   breakeven, S114/S115 Nocturne fail, EMAStretchFade PF 0.84).
2. The regime ensemble (the spec's core rescue thesis) does NOT rescue it: the
   challenger is WORSE than the always-on control in both splits while
   deleting 87.5% of cadence (657 → 82 trades) — repeating the
   "ChopMeanRevert S652/S653 dead" and "ATR filter deletes ~90% cadence"
   precedents. The burden-inverted pass condition failed in the strongest
   possible way (margin gate inverted, not merely missed).
3. Per the frozen plan, this collapses the spec's Variant A into the killed
   regime-gated-MR family: terminal at offline probe. XAUUSD (worse costs,
   swap-negative, every prior XAU MR variant dead) is NOT authorized as a
   follow-up under this family.

## Do-not-revive scope

Do not re-run this ID or rescue by: changing Z_entry/W/K_sl/TP/k_ts/session,
tuning or removing individual regime gates (ADX/ATR-band/HL), swapping the
trendiness index (CI/Hurst/other), moving to M15 or XAUUSD, post-hoc
hour/day/year vetoes, or re-costing with an optimistic spread. A future MR
lane requires a materially different information set (e.g. verified order-flow
/ options-implied state) plus fresh preregistration — not another OHLC
recombination of deviation-from-mean fade with regime gates.

## Artifacts

- Probe JSON: `evidence/20260717_075658_HYP_MR_REGIME_EURUSD_H1_001_PROBE.json`
  (SHA `113A2B31FC426B7B1929C6892911E982E7200BACBF4D7AA71E8EA9CF9B20F062`)
- Trade ledger: `evidence/20260717_075658_HYP_MR_REGIME_EURUSD_H1_001_TRADES.csv`
  (SHA `047B9427E05FFF5A360DA1DE05CF20E7BF371EFC2363DD3AC4B3CFAB9E12CAEB`)
- Data audit: `evidence/EURUSD_PULL_AUDIT.json`; trial log `trials/trial_log.jsonl`
  (2 evaluations of the single frozen config; tuning budget 0 respected)
- Storage: C Common IDENTICAL 137 files / 20,008,308 bytes; two Tester roots
  shrank via MT5's own startup pruning (documented in
  `evidence/20260717_MR_C_STORAGE_DELTA_NOTE.md`); EURUSD `2026.hcc` +124,038 B
  live-bar append, protected per precedent. All run evidence on D.
