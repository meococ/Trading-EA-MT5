# 03. EA Developer — Active Shelf

Updated: 2026-07-18 (MR family closed, B-R + Kalshi kills recorded)

Active compilable shelf = 6 lane. Mọi package khác đã archive THẬT sang
`00. Old File/EA_Archive/` (2026-07-15) — **không** compile từ đó làm evidence.

| Active package | Path | Notes |
|---|---|---|
| `EA_FVGConfluence` | `03. EA Developer/EA_FVGConfluence/` | Path-C scaffold compile 0/0 and closed-bar audit PASS, but `HYP-FVG-SCALP-CONFL-M5-EUR-001` terminal at de-dup as illegal densify of killed FVG-cont; no Model 0/rerun/live authority |
| `EA_HybridICT_Sonic` | `03. EA Developer/EA_HybridICT_Sonic/` | Path-C stub (KILL@Model0, 0 trades); lane riêng |
| `EA_KLR_Scalper` | `03. EA Developer/EA_KLR_Scalper/` | Native Model-0 replication terminal KILL: core N=4/0.02555 per week, USD N=1/0.00639 per week; source retained for audit, no live/rerun authority |
| `EA_UnicornPrecisionScalper` | `03. EA Developer/EA_UnicornPrecisionScalper/` | Event-anchored Model-0 `HYP-UPS-XAU-M5-006` remains terminal KILL; canonical v1.24 is tester-only/alert-only hardening with source-bound zero-trade V1.3 casebook awaiting independent labels, not live/economic-rerun eligible |
| `EA_UnicornPrecisionScalperControl` | `03. EA Developer/EA_UnicornPrecisionScalperControl/` | Storage-safe four-closed-bar Model-0 control; compiled/non-repaint PASS, `HYP-UPSC-XAU-M5-002` terminal KILL, not live/run eligible |
| `EA_UnicornPrecisionScalperRR15` | `03. EA Developer/EA_UnicornPrecisionScalperRR15/` | Exact RR1.5 replay `20260716_144508` terminal `KILL_DIAGNOSTIC`: WR 35.606%, PF 0.697, net -$4,904.75, full-cost PF 0.475; no rerun/promotion/live authority |

Research-only terminal records (no `.mq5`, not returned by `alpha list`):

| Record | Verdict |
|---|---|
| `EA_PO3_AMD_Scalper/` | HYP-001/002/003 `KILLED_AT_OFFLINE_PROBE`; no code/compile/backtest |
| `EA_DRAT_ONNX_ICT_Hybrid/` | `KILLED_AT_OFFLINE_PROBE`; no code/Model 0 |
| `EA_GoldMacroPulse/` | HYP-GMP real-yield challenger `KILLED_AT_OFFLINE_PROBE`; no code/holdout/Model 0 |
| `EA_GLDFlowPulse/` | Official SPDR primary-flow HYP-001 schema kill then frozen HYP-002 `KILLED_AT_OFFLINE_PROBE_NO_EDGE`; cadence passed but gross/x1 economics failed; no `.mq5`, holdout or Model 0 |
| `EA_CFTCOptionsPulse/` | CFTC TFF economic probe terminal KILL plus DTCC/CME public-SDR source-feasibility records; no `.mq5` or Model 0 |
| `EA_CMEParticipationPulse/` | Official CME daily futures-OI HYP-001 `KILLED_AT_OFFLINE_PROBE`; cadence passed but post-cost economics failed in train and validation; holdout unopened, no `.mq5`/compile/Model 0 |
| `EA_SGEFixingPulse/` | Official SGE SHAU fixing source `KILLED_AT_SOURCE_GATE_NO_POINT_IN_TIME_PUBLICATION_PROOF`; density passed but exact public release/version lineage failed before hypothesis/outcomes; no `.mq5`/compile/Model 0 |
| `EA_HybridRegimeMR/` | Owner MR spec: `HYP-MR-REGIME-EURUSD-H1-001` `KILL_AT_OFFLINE_PROBE`, then exhaustive grid `HYP-MR-GRID-EURUSD-H1-002` `KILL_FAMILY_EXHAUSTIVE` (8100 sims, 0 arms gross PF≥1.25, best DSR 0.0129) — family CLOSED_EXHAUSTIVE; no `.mq5`/compile/Model 0. Reusable EURUSD 2015–2026 parquets: `02. AlphaFactory/data/fivepercent/EURUSD/` (hash-bound manifest); clock model: `tools/research/fivepercent_server_clock.py`; acquisition audit stays in `research/evidence/` |
| `EA_EURSessionDrift/` | Breedon-Ranaldo unconditional session drift `HYP-BR-SESSDRIFT-EURUSD-H1-001` `KILL_AT_OFFLINE_PROBE` (2026-07-18): N=4146, gross PF 1.036, 2/8 positive years, anomaly decayed post-2017 — closes the last untested MR v3 branch; no `.mq5`/compile/Model 0 |
| `EA_KalshiMacroPrint/` | `HYP-KALSHI-MACRO-PRINT-H1-XAU-001` `KILL_AT_OFFLINE_PROBE` (2026-07-18, cron lane): gross PF 0.941/0.947 dead before cost, 0/4 positive years, challenger worse than momentum control; no `.mq5`/Model 0 |

| Archived (2026-07-15) | Archive path | Ghi chú |
|---|---|---|
| `EA_SonicR` | `00. Old File/EA_Archive/EA_SonicR/` | full research ledger; bản duy nhất (vẫn còn trong `origin/main` history) |
| `EA_SilverBullet` | `00. Old File/EA_Archive/EA_SilverBullet/` | **binary-only** (`.ex5`); không còn source `.mq5` |
| 78 stub `.ex5` | `00. Old File/EA_Archive/` | binary compile không-nguồn (không tracked); manifest trong cleanup_receipts |

Manifest: `00. Old File/project_control_archive_20260716/cleanup_receipts/20260715_docs_disk_sync_archive.json`.
Live scope / blockers / next moves: `04. Memory/hot.md`.
Workspace map: `INDEX.md`. Do not compile from `00. Old File/` as valid evidence (`AGENTS.md`).
