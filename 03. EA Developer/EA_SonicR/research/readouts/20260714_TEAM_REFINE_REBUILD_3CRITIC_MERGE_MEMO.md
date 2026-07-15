# Team Refine / Rebuild — 3-Critic Merge Memo

Date: 2026-07-14 ~19:20 ICT  
Role: Coordinator merge (Sonic trader + Quant validation + MQL5/MT5 systems)  
Authority: Owner `REBUILD_CAMPAIGN_ACTIVE` (~19:09 ICT)  
Process: GPT waived; nested critics `cursor-grok-4.5-high-fast`; single-lane; no-Git  
Cost grade for all screens: `UNVERIFIED_TESTER_DEFAULT` — **not GOAL**

## Parks verified (do not trust memory)

| Park | Run | PF | N | tpw | Gap |
|---|---|---:|---:|---:|---|
| SB A1 | `20260714_002505` | 1.34 | 520 | **1.99** | cadence micro-short (~2 trades / 5y) |
| Spark Asian | `20260714_002821` | 1.31 | 325 | **1.25** | cadence structurally thin (Tue–Wed) |
| ITSM pullback | `20260714_003920` | **1.16** | 852 | 3.27 | PF short; cadence OK |

Offline SB+Spark compose PF 1.339 / ~3.24/wk remains research-proxy only; Phase-0 freeze blocked; cost×1.5 stress already red on compose diagnostics.

## Merge verdict

| Park | Rebuild vs tweak | Primary legal lever | Banned |
|---|---|---|---|
| SB | **Rebuild architecture / density contract** (weekend-flat already answered ~null) | MaxTradesPerKZ=2; a-priori NYPM `[20,22)`; optional MaxHold management | Friday hour mine; stacking axes after fail |
| Spark | **Mechanism / symbol rebuild**, not day densify | GBPUSD Wed–Thu transfer (S107); capacity MaxPerDay only if a-priori | Mon–Thu (S223); hour-11 mine |
| ITSM | **Quality / session isolation rebuild** | NY-only + StrictAlign; London-only sibling (frozen same night) | T10 confluence; skip-Tue; RR retune from T10 |

**None of the parks meet GOAL.** Ambition ≠ gates.

## Systems blockers (from MQL5 critic)

1. **ITSM `InpMaxTradesDay` is dead code** — hard 1 fill/day via `g_lastTradeDate`. Prereg `=2` is a **no-op** (parent `003920` same). Session/StrictAlign arms remain valid; density claims from MaxTradesDay are **systems-invalid** until wired. This campaign treats effective cap as **1/day** honestly.
2. SB Deposit must be **100000** to match A1 control (AF default 10000 breaks DD/lot compare).
3. `includes_sha256` closeout flake: keep reports; do not false-fail research.
4. Prefer same-EX5 override children; fork folder only for new entry anatomy.

## Multiplicity budget (Quant)

- Campaign Model 0 child cap ≈ **≤6** across SB+ITSM (+Spark symbol transfer).
- Per-family stop after **2 consecutive misses** of a-priori success screen.
- Spark: **no** USDJPY day densify children.
- Numeric threshold sweeps = mining; one structural axis per ID.

## Ranked execute order (this session)

| Rank | ID | Why | Control |
|---|---|---|---|
| 1 | `HYP-SB-MAXKZ2-DENSITY-002` | Smallest structural density fix for 1.99→≥2.0 | A1 `002505` |
| 2 | `HYP-SB-NYPM-KZ-001` | Sibling session expand (frozen hours) | A1 `002505` |
| 3 | `HYP-ITSM-NYONLY-STRICTALIGN-002` | PF lift via session quality | `003920` |
| 4 | `HYP-ITSM-LONDON-ONLY-STRICTALIGN-002` | A-priori opposite arm | `003920` |
| 5 | `HYP-SPARK-ASIAN-GBPUSD-001` | Symbol sleeve cadence without USDJPY densify | parent Spark park |
| 6 | `HYP-SB-MAXHOLD-A2-001` | Management only — unlikely to fix cadence | A1 `002505` |

Parallel Owner-physical (not agent-executable): Real QFSI reprice of SB A1 / Spark.

## Hard kill screens (every child)

- Model 0; new/child `hypothesis_id` + registry + frozen prereg **before** readout
- Elapsed tpw = N / 260.7143
- Kill: PF < 1.00 **or** N < 80 **or** tpw outside prereg band
- Research HIT (still not GOAL): PF > 1.30 **and** tpw ∈ [2.0, 5.0] under tester `current`
- Must not lose matched control on net + risk-adjusted behavior (density children: require tpw≥2.0 for cadence success)
- No post-result hour/day/threshold edits

## Explicit non-rescues

Mon/Fri densify SB; Spark Mon–Thu; ITSM T10 confluence; silent threshold retune of killed IDs; portfolio EA while Phase-0 contaminated; missing-cost-as-zero; claim GOAL from Demo PF.

## Critic inputs

- Sonic trader: agent `be0a476a-ea3a-454b-8458-cb924bd02720`
- Quant validation: agent `8c91fb34-b7db-455c-aa71-43ec439d75e5`
- MQL5/MT5 systems: agent `f11c7f0e-9397-4ddc-be8e-f85ab1114f7e`

Coordinator executes the ranked matrix; kill fast; update `hot.md` after each Model 0 batch.
