# Strategy Rebuild Campaign Coordinator — 2026-07-14

Status line: **`GOAL_NEAR_MISS`** (one research-bar hit under tester cost; GOAL unmet)  
Campaign: Owner multi-option refine + tear-down/rebuild (~19:09 ICT)  
Process: `GPT_DEEP_RESEARCH_WAIVED`; nested workers `cursor-grok-4.5-high-fast`; no-Git

## Matrix (a priori; frozen before Model 0)

| ID | Family | Structural change | Run | PF | tpw | Verdict |
|---|---|---|---|---|---|---|
| `HYP-ITSM-NYONLY-STRICTALIGN-002` | ITSM | NY-only KZ + StrictAlign | `20260714_191955` | 1.22 | ~2.07 | PARK |
| `HYP-ITSM-LONDON-ONLY-STRICTALIGN-002` | ITSM | London-only + StrictAlign | `20260714_192116` | 1.12 | ~1.85 | PARK |
| `HYP-SB-NYPM-KZ-001` | SB | Enable NYPM KZ + A1 flat | `20260714_192203` | 1.27 | ~2.44 | PARK (cadence↑ PF↓) |
| `HYP-SB-MAXKZ2-DENSITY-002` | SB | MaxTradesPerKZ=2 + A1 flat | `20260714_192304` | **1.33** | **~2.09** | **HIT_RESEARCH_BAR_COST_UNCONFIRMED** |

Optional concurrent arms (same Owner auth): Spark-GBPUSD PARK PF 1.07
(`20260714_191507`); H1 Donchian MR KILL PF 0.40 (`20260714_191727`);
SB MaxHold A2 PARK PF 1.33 / ~1.998/wk (`20260714_191628`).

3-critic merge: `readouts/20260714_TEAM_REFINE_REBUILD_3CRITIC_MERGE_MEMO.md`  
Owner brief: `readouts/20260714_OWNER_TEAM_REFINE_REBUILD_SESSION_DELIVERABLE.md`

## Anti-overfit attestation

- No day/hour threshold mining from failed readouts.
- No T10 confluence enable; no Friday cutoff retune.
- Each arm = new child ID with frozen prereg + ContractReceipt.
- Portfolio compose Phase-0 still blocked — no outcome-mined book from tonight PF list.
- Family stop tonight: no further SB densify / ITSM session spam.

## Cost honesty

All Model 0s: tester `current` / `UNVERIFIED_TESTER_DEFAULT`. Missing cost ≠ 0.  
**No confirmed / no GOAL claim.** MaxKZ2 research HIT ≠ GOAL.

## Survived

- **Primary survivor:** `HYP-SB-MAXKZ2-DENSITY-002` — research joint PF>1.30 ∧ 2–5/wk under Demo tester cost only.
- Secondary parks: ITSM NY (PF lift insufficient), SB NYPM (cadence only), MaxHold (null cadence), Spark GBP (weak).

## Next moves

| Who | Action |
|---|---|
| **Owner-physical (highest EV)** | `FivePercentOnline-Real` + QFSI → reprice MaxKZ2 `20260714_192304` (and A1 `002505`) |
| Agent | Stop further SB densify / ITSM session spam tonight; optional structural rebuild only with new a-priori child |
| Portfolio | Still Phase-0 contamination blocked — do not compile compose EA from PF ranking |

## Paths

- Receipt: `preflight/20260714_STRATEGY_REBUILD_CAMPAIGN_RECEIPT.json`
- Metrics: `preflight/rebuild_campaign/20260714_STRATEGY_REBUILD_METRICS.json`
- Readouts: `readouts/20260714_HYP_*_{NYONLY,LONDON,NYPM,MAXKZ2,MAXHOLD,SPARK_ASIAN_GBPUSD,H1_LOWVOL}_*_READOUT.md`
- Contracts: `preflight/rebuild_campaign/{itsm_nyonly,itsm_london,sb_nypm,sb_maxkz2,spark_gbpusd}/`
