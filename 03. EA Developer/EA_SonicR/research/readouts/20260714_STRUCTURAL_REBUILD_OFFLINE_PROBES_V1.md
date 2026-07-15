# Structural rebuild offline probes V1 (post-Wave5)

Generated: 2026-07-14T16:04:38.915775+00:00
Authority: Owner R&D continue; `DEMO_DISCOVERY_DIMINISHING_RETURNS=true`; GPT waived
Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`

## Panel merge (architecture shortlist ≤4)

| # | Thesis | Architecture | Offline verdict |
|---|---|---|---|
| T1 | Cost-aware arming on RR2 | Risk model | **KILLED_AT_OFFLINE_PROBE** |
| T2 | AUDJPY→USDJPY H1 lead | Cross-asset lag | **KILLED_AT_OFFLINE_PROBE** |
| T3 | D1 trend → H1 PB | Multi-TF confirmation | **KILLED_AT_OFFLINE_PROBE** |
| T4 | RR2+Spark equal-join | Portfolio sleeve rules | **DIAGNOSTIC_ONLY__CEREMONY_BLOCKED** |

## T1 — Cost-aware arming

- Baseline RR2 `20260714_194548`: PF 1.3794 / tpw 2.0099 / +$12 x1.5 PF 1.0134
- risk_usd P10/P50: 38.11 / 73.68
- `k2` min_risk=$24.0: N=524 PF=1.3794 tpw=2.0099 x1.5=1.0134 → **KILLED_AT_OFFLINE_PROBE**
- `k3` min_risk=$36.0: N=501 PF=1.3769 tpw=1.9216 x1.5=1.0199 → **KILLED_AT_OFFLINE_PROBE**

## T2 / T3 — MT5 bar probes

- MT5 status: `OK`
- T2: N=1785 PF=1.0578 tpw=6.8466 → **KILLED_AT_OFFLINE_PROBE** kills=['stress_fail', 'cadence_fail', 'pf_fail']
- T3: N=1259 PF=0.9999 tpw=4.829 → **KILLED_AT_OFFLINE_PROBE** kills=['stress_fail', 'pf_fail']

## T4 — Phase-0 compose

- Universe frozen: RR2 `20260714_194548` + Spark `20260714_193358`
- Pooled diagnostic: PF 1.3799 / tpw 3.2564 / x1.5 1.0669
- Ceremony: **BLOCKED** — `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`
- Goal-like proxy (diagnostic only): {'pf_gt_1_30': True, 'tpw_in_2_5': True, 'x1_5_ge_1_25': False}

## What NOT to test

- MaxKZ/RR/SB/Spark densify; ATR%ile; Asia/London/NY IB hours
- Wave1–5 killed/parked families; GBPJPY-lead retune; EMA-stack densify
- Phase-0 outcome compose until Owner clean freeze review
- Another random session-break Model 0 batch

## Model 0 authorization

**No offline survivors.** Model 0 withheld. Prefer next structural object redesign, not densify.

