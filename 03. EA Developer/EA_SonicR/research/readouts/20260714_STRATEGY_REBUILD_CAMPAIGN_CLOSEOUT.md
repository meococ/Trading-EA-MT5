# Strategy Rebuild Campaign Closeout — 2026-07-14 evening

Status: `PARTIAL_SURVIVOR_RESEARCH_BAR`  
Authority: Owner REBUILD_CAMPAIGN_ACTIVE; GPT waived  
Cost label for all runs: `UNVERIFIED_TESTER_DEFAULT` (Real login still absent)

## Option results

| ID | run_id | PF | tpw | Net | DD% | Verdict |
|---|---|---:|---:|---:|---:|---|
| HYP-SB-MAXKZ2-DENSITY-002 | `20260714_192304` | **1.334** | **2.094** | +8123 | 0.85 | **HIT_RESEARCH_BAR** (not confirmed) |
| HYP-SB-NYPM-KZ-001 | `20260714_192203` | 1.271 | **2.436** | +7654 | 1.05 | PARK (cadence OK, PF short) |
| HYP-SB-MAXHOLD-A2-001 | `20260714_191628` | 1.334 | 1.998 | +7541 | 0.85 | PARK (~null vs A1) |
| HYP-ITSM-NYONLY-STRICTALIGN-002 | `20260714_191955` | 1.22 | 2.07 | +2431 | 6.59 | PARK (best ITSM child) |
| HYP-ITSM-LONDON-ONLY-STRICTALIGN-002 | `20260714_192116` | 1.12 | 1.85 | +1641 | 6.96 | PARK (loses to NY) |
| HYP-SPARK-ASIAN-GBPUSD-001 | `20260714_191507` | 1.07 | 1.66 | +3503 | — | PARK (weak) |
| HYP-H1-LOWVOL-DONCHIAN-MR-001 | `20260714_191727` | 0.40 | 0.05 | −267 | — | **KILL** |

Parent baselines: SB A1 PF1.34/1.99wk; Spark USDJPY PF1.31/1.25wk; ITSM PF1.16/3.27wk.

## Rebuild delivered

- New EA: `EA_H1LowVolDonchianMR` (compiled; Model 0 killed)
- Override-only structural children on `EA_ITSM` / `EA_SilverBullet` / `EA_M15SparkAsian`
- No silent threshold rescue of killed books

## Distance to GOAL

| Gap | Status |
|---|---|
| Research PF>1.30 + 2–5/wk (tester) | **Cleared by SB MaxKZ2 only** |
| Verified Real cost / cost-stress | **Open** — `BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN` |
| Confirmed suite (WFA/MC/holdout) | Not started |
| Portfolio compose Phase 0 freeze | Still blocked (contamination) |

## Next moves (ranked)

1. **Owner:** login `FivePercentOnline-Real` → QFSI → reprice `HYP-SB-MAXKZ2-DENSITY-002` (`20260714_192304`) then SB A1 / SB+Spark pool  
2. Keep MaxKZ2 as research survivor; do not mine MaxTradesPerDay  
3. Optional: a-priori SB dual-book with Spark USDJPY only after cost contracts (not PF cherry-pick)  
4. ITSM NY child may spawn **new** independent thesis later — not T10 confluence

## Files

- Receipt: `preflight/20260714_STRATEGY_REBUILD_CAMPAIGN_RECEIPT.json`
- Coordinator: `readouts/20260714_STRATEGY_REBUILD_CAMPAIGN_COORDINATOR.md`
- Per-ID readouts under `readouts/20260714_HYP_*`
- Registry appends in `CANDIDATE_REGISTRY.jsonl`
