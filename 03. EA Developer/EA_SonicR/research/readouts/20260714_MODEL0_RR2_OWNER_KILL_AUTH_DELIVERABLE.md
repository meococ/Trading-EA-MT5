# Deliverable — Model 0 RR2 Owner kill-auth re-run

Date: 2026-07-14 ~23:20 ICT  
Authority: Owner 2026-07-14 23:15 — kill/close residual Real allowed unless backtest in-flight  
Hypothesis: `HYP-SB-MAXKZ2-RR2-FRICTION-001`  
Model: Grok 4.5 High Fast

## Backtest-in-flight check

| Check | Result |
|---|---|
| `terminal64` at prelaunch | **0** (then residual Real PID **61628** login **26451822** / `FivePercentOnline-Real` appeared ~23:16:50) |
| `metatester*` | **0** |
| AlphaFactory backtest lock / in_progress | **none** |
| Decision | **No Strategy Tester in-flight** → kill authorized |

## Kill / close actions

1. Prelaunch: slot clear (`terminal64=0`) — no kill needed initially.
2. Residual Real **PID 61628** (login 26451822) observed before contract-complete launch → **killed** under Owner auth; verified `terminal64=0`.
3. Post-run leftover **PID 57064** (started 23:18:49 after runner exit; no metatester) → **killed**; verified `terminal64=0`.
4. Did **not** re-login Real for this lane. After Model 0 closeout, parallel
   QFSI capture `20260714_QFSI_REAL_005_POSTAUTH` (python parent) re-opened
   Real — left alone (hygiene; not Model 0 blocker).

## Launch

- `alpha.ps1 backtest EA_SilverBullet` Model **0**, USDJPY M15, 2021.01.01–2025.12.31, deposit 100000
- Overrides frozen: `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;InpUseWeekendFlat=1`
- Contract receipt SHA `F48198039AC4C61517D0ED85A908E0B238581A681636092BE5DB505F3423316E`
- Compile OK (ex5 **88476** bytes). Runner MT5 PID **48032**.
- Ceremony flake: finalize threw `Required sidecar ''` (`required_sidecars: [null]` — same class as prior RR2 manifests). **Report + analyze kept** (not voided).

## run_id

**`20260714_231750`**

Report SHA256 `A6B071092829871C655BCC2A80E9DB13B53556EE3D1141FE65A099DF409F3618`

## Metrics vs baseline / GOAL

Elapsed weeks (calendar, prior freeze): **260.7143** → tpw **518/260.7143 ≈ 1.987**

| Metric | Baseline `194548`/`194221` | Fresh `231750` |
|---|---:|---:|
| N | 524 | **518** |
| PF | **1.378** | **1.156** |
| Net | +9828 | **+4425** |
| DD | ~0.96% | **1.58%** |
| tpw | ~2.01 | **~1.99** |
| ex5 size (snapshot) | 88826 | **88476** |

### Research gates (prereg)

| Gate | Result |
|---|---|
| KILL (PF&lt;1 or tpw∉[1,6] or N&lt;80) | **PASS** (survives) |
| Research HIT (PF&gt;1.30 ∧ tpw∈[2,5]) | **FAIL** (PF 1.156; tpw≈1.99) |
| Verdict | **`PARK_MISS_RESEARCH_BAR`** |

### Real partial P50 haircut (~$2.3088/trade, frozen; not full QFSI)

Artifact: `runs/EA_SilverBullet/20260714_231750/analysis/cost_stress_real_p50.json`

| Scenario | PF |
|---|---:|
| x1 (~$2.31) | **1.111** FAIL vs GOAL x1&gt;1.30 |
| x1.5 | **1.089** FAIL (≥1.25) |
| x2 | **1.068** |

Prior offline PASS on `194221` under same P50 is **superseded for current tester/build** by this fresh Model 0.

### GOAL proxy base+$12

Artifact: `analysis/cost_stress_base12.json` — x1.5 PF **0.855** FAIL; x2 PF **0.776** FAIL.

## Interpretation (no densify)

Fresh Model 0 under current compile/tester is a **material regression** vs shelf `194548` (same frozen RR2 overrides; ex5 hash/size drifted). Family stays **PARK**; do **not** retune RR/MaxKZ from this readout. Discovery lane continues with independent objects; Phase-0 compose still blocked / not opened by this miss.

## hot.md

Updated Active Truth with this run_id and verdict.
