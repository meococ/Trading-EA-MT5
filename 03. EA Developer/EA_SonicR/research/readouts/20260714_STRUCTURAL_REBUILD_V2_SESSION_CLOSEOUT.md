# Session closeout — Structural rebuild offline V2 (2026-07-14)

Status: `COMPLETE`  
GPT: waived  
Model 0 launched this session: **0** (no offline survivors)

## Delivered

1. De-dup clearance for two **new** structural objects (not ASR/EQHL/ORB-accept/PDH densify).
2. Cheap offline probes A+B on USDJPY closed bars (MT5 history).
3. Registry kill rows appended.
4. Phase-0 compose **not** reopened (`BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`).
5. `hot.md` + option backlog updated.

## Evidence paths

| Artifact | Path |
|---|---|
| De-dup | `readouts/20260714_STOPRUN_ACCEPT_LNY_EVENT_DEDUP_CLEARANCE.md` |
| Probe JSON | `preflight/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V2.json` |
| Probe MD | `readouts/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V2.md` |
| Probe script | `preflight/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V2.py` |
| Result SHA256 | `10F0A23A85A2D8307C56F63DE080899FF340D9D57D1C5811DAC1514149B455D0` |

## Verdict board

| Thesis | Funnel / metrics | Verdict |
|---|---|---|
| A `HYP-H1-PDLIQ-STOPRUN-ACCEPT-001` | stoprun 1773 → accept 390 → **N=164** · PF **1.11** · tpw **0.63** · x1.5 PF **1.05** | **KILL** offline (cadence+pf+stress) |
| B `HYP-LNY-RANGE-ACCEPT-M15-001` | expansion days **13** → armed 11 → **N=4** · PF **0** | **KILL** offline (event starves) |
| Phase-0 compose | — | **Not reopened** / still BLOCKED |
| Best shelf | RR2 `194548` | **Unchanged** |

## Honest read (no retune)

- **A** has real sample and ~$33/trade zero-spread exp, but mean edge too thin for PF>1.20 and calendar cadence; +$12 stress does not clear. **Do not** mine accept-bars / hours / RR from this readout.
- **B** as a priori expansion≥1.0 ATR_D1 + outer-third + post-London accept-break is **too rare** (13 expansion days / 5y). Not a DualWin window densify — event definition itself fails capacity. **Do not** lower range_atr from this kill.

## Banned densify (extended)

Stop-run-accept H1 PDH family retune · LNY range-accept threshold mine · S530 Mon/day · DualWin third window · ASR/EQHL reclaim rescue · PDH-break/retest · Wave1–5 / T1–T3 / A–B retunes · Phase-0 compose without Owner clear.

## Next (no login dependency)

1. New structural object **outside** A/B kill families (fresh edge object + offline probe first).
2. Optional Owner: clear Phase-0 contamination for compose ceremony on frozen `194548`+`193358` (still expect +$12 stress fail unless cost provenance improves).
3. QFSI / Real cost = parallel hygiene only — never headline.

## Coordinator decision

- `DEMO_DISCOVERY_DIMINISHING_RETURNS=true` remains.
- **Zero Model 0** (kill-fast).
- Best shelf unchanged: RR2 `20260714_194548`.
