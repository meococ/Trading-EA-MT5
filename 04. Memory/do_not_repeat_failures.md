# Do Not Repeat — Failed Strategies / Approaches

Updated: 2026-07-16
Language: English (evidence plane). Purpose: stop re-running dead ends.

Authority: evidence pointers only. Do **not** invent kill reasons. If a row has
no pointer, treat as unknown and re-check artifacts before any revive.

Companion inventory: `00. Old File/EA_Archive/MANIFEST_20260715_workspace_cleanup.json`  
Portfolio audit: `00. Old File/EA_Archive/EA_SonicR/research/20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`  
Strategy diary (legacy S-numbers): `02. AlphaFactory/STRATEGY_LOG.md`

## How to use

1. Before a new hypothesis, search this file + registry + STRATEGY_LOG.
2. “Do not revive unless X” is a **hard gate**, not a suggestion.
3. Post-hoc threshold/hour/day veto from a just-read readout → new `idea` only,
   never a rescue of the killed hyp (`AGENTS.md`).

---

## A. EA families (shelf / killed) — code now under `00. Old File/EA_Archive/`

| Family / EA | Verdict (evidence) | Do not revive unless |
|---|---|---|
| **EA_SonicR** Classic XAU route | Best short seed PF~1.40 / ~1.23 tpw; longer route PF~1.15; equity REJECT; regime pocket 2024-25 — **not survivor**. Full package + research ledger archived 2026-07-15 under `EA_Archive/EA_SonicR/`. | New independent mechanism + cost provenance; not another Asian-range / CONTEXT / Dragon-Trend / ATR-delete-cadence patch on same fields. Audit `20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`. |
| **EA_SilverBullet** historical book | Near cadence seed PF~1.33 / ~1.99 tpw; The5ers transfer **KILL** (PF~1.02, x1.5~1.00); overnight vs scalp contract. Full package archived 2026-07-15 under `EA_Archive/EA_SilverBullet/` — no active code lane. | Fresh Model 0 only after Owner restores package to `03. EA Developer/` + updates `hot.md`; not tune from `131343` / The5ers kill. |
| **EA_LondonNY** | Strong PF/quality but ~0.3 tpw; cross-pair transfer killed; book ~0.42 tpw — sparse sleeve. | Cadence-capable universe redesign with prereg; not pair-add rescue. |
| **EA_ITSM** | Holdout PF~1.05 + 2024-25 decay → **KILL**. Portfolio expansions with ITSM offline **FAIL**. | Independent thesis; not Spark/SB+ITSM densify. |
| **EA_ChopRegime** | Untouched 2018-20 OOS PF~1.03 → **KILL_FAMILY**. | New family id + different mechanism. |
| **EA_Gotobi** | TZ fix did not rescue; treatment PF~0.91. | New evidence package. |
| **EA_Spark** / **EA_M15SparkAsian** | Configs ~PF 1.00 / 0.93; SB+Spark dual-runner Model 0 **KILL** (tester PF 1.219 < 1.30). | Independent Spark child with capital twin + a priori weights — not deposit-contaminated rerun. Readout `20260714_HYP_PORTFOLIO_SB_SPARK_RUNNER_001_READOUT.md`. |
| **EA_H4Ribbon** | Pooled PF ~0.36. | — |
| **TrendBook** / trend distance patches | Portfolio PF ~0.50; Dragon/Trend distance killed cadence-vs-impulse tradeoff. | — |
| **Gap-fill** | Stage-1 illusion; compiled probe PF~0.48. | — |
| **EA_Portfolio** (legacy multi-sleeve host) | Tear-down: contaminated toggles reintroduce killed sleeves. | Clean dual-instance compose only after survivors; do not compile legacy host. `20260714_EA_PORTFOLIO_TEARDOWN_FOR_SB_SPARK_BOOK.md`. |
| **EA_Cobra** | Historical E8 survivor class but sparse (~0.5 tpw in audit taxonomy); outside current SB Phase-0 universe. | Owner-scoped new prereg — not silent revive. |
| **EA_InsideBar** | Killed in portfolio teardown table. | — |
| Other flat `EA_*` under archive (ACF, Gold*, M15*, H1*, etc.) | Shelf after 20260710 frontier / later offline boards; many never cleared Model 0 with hypothesis_id. | Registry row + offline probe beat locked controls; no compile-from-archive as evidence. |

Duplicate / index stubs archived (do not use as fallback):
`EA_SilverBullet_Index` (full package),
`00. Old File/EA_Archive/EA_SilverBullet_dead_siblings/`
(`EA_SilverBullet_v2_Index.mq5`, `EA_SilverBullet_v1_backup.mq5`), and the
full former-active package
`00. Old File/EA_Archive/EA_SilverBullet/`. No active pin under
`03. EA Developer/` (shelf empty 2026-07-15).

---

## B. Research approaches / hypothesis classes already killed

### Sonic field / process illusions (closed frontier)

| Approach | Kill summary | Evidence | Do not revive unless |
|---|---|---|---|
| Generic sideway/range, compression breakout, retest, context-rescue | Failed on Sonic fields | Portfolio audit | Materially different feature set |
| EUR Asian manipulation | Cadence OK (~2.21 tpw) but cost PF~1.08 + year concentration fail | Portfolio audit | New cost-honest holdout |
| GBP value-drift EMA89 | Holdout cost PF~0.82 | Portfolio audit | — |
| XAU ATR filter “improve PF” | Deletes ~90% cadence | Portfolio audit | — |
| Same-bar consensus / lead-lag / laggard catch-up (S555/S618/S670 class) | Locked falsification controls for FX factor idea | Portfolio audit + XS prereg notes | Beat all three in train + one-time holdout |
| Matched-control-less Model 1 promotion | Model 1 kill/park only | `AGENTS.md` | — |
| Zero/missing cost treated as zero | Invalid | Doctrine / cost audit | Verified broker cost artifact |
| Active-week cadence denominator | Invalid | Portfolio audit | Elapsed calendar weeks only |
| Post-hoc hour/day/year veto | Forbidden rescue | `AGENTS.md` | New preregistered idea |

### Deep Research / data frontier (2026-07-13+)

| Item | Result | Pointer | Do not revive unless |
|---|---|---|---|
| V2–V7 Deep Research strategy candidates | No legal MT5 candidate / family locks | `readouts/20260713_DEEP_RESEARCH_V*_COORDINATOR_AUDIT.md`, failure packets V3/V6/V7 | Owner-new scope + de-dup clearance |
| V5 Impact-per-Pressure proxy | `KILL_AT_OFFLINE_PROBE` | `20260713_IMPACT_PRESSURE_PROXY_PROBE_READOUT.md` | Not rename/rescue; need independent hyp |
| V8 weekly carry / rates offline | `KILL_AT_OFFLINE_PROBE` (PF high, cadence dead) | `20260713_V8_CARRY_DIFF_OFFLINE_PROBE_READOUT.md` | Different timescale + cadence design |
| QFSI / GVBCI as strategy authority | Foundation only; QFSI STOP / quote-days gate | V4 foundation readout; hot QFSI 006 harvest | Research-grade multi-month quote+commission+slip |

### Offline monetization / greenfield boards (2026-07-15) — all `OFFLINE_ALL_KILL` / no Model 0

| Hypothesis / board | Why dead | Do not |
|---|---|---|
| RR2 BE@1R, MFE stall-cut | Path exits destroy edge | Densify arm/stall/giveback; revive BE@1R |
| Scale-out 1R50 / timebox 2h / vol-regime R-mult | Kill under joint PF+stress | Densify scale/timebox/R-mult |
| ATR-trail M1 path proxy | KILL (false early SL); envelope survivors ≠ deployable | Treat offline PF as Model 0; densify arm/k |
| LNY EUR fade / GBP coil / EUR lead catch-up | Cadence+PF+stress kills | Densify imbalance/coil/catch-up |
| Asia pctl-coil London break | Cadence kill (nearest miss) | Densify p40/lookback/hours |
| Greenfield XS USD residual/mom + AUDNZD zMR | Joint screen kill | Densify XS z / mom / AUDNZD z |
| FRED displace / ToT spam | Owner-rejected stall path | Revive FRED spam boards |
| Cost freeze invented from shallow capture | Diagnostic only (quote days << 90) | Invent cost freeze / densify Wave8 |

Best **shelf** reference run (not promotion): SilverBullet RR2 `20260714_194548` (a priori +$12 x1.5 still fail per closeouts). GOAL unmet.

---

## C. Process failures already paid for (do not reintroduce)

- Attractive PF hiding calendar cadence miss.
- Short favorable windows outranking longer falsification.
- Tester zero slippage / fixed $0.50 as live proof.
- Tool exit-code PASS as numeric validation.
- Duplicate reruns as independent confirmation.
- Globally keyed timestamp `run_id` cross-wiring EAs (ITSM/LondonNY collision).
- Compiling from `00. Old File` or other archive paths as evidence.

---

## D. What is still allowed (narrow)

- Active code lanes are only `EA_FVGConfluence` and `EA_HybridICT_Sonic` under
  `03. EA Developer/`; the former is probe-blocked and the latter is terminal
  killed. Do not infer execution eligibility from package presence.
- Canonical active ledger: `04. Memory/research/CANDIDATE_REGISTRY.jsonl`.
  Archived Sonic ledger remains de-dup history only; compile-from-archive invalid.
- New independent mechanisms follow de-dup → cheap offline probe → frozen prereg
  → capability/cost contract → sequential matched Model 0.
- Data acquisition toward research-grade bid/ask + commission + slip (QFSI frontier), without pretending gate is green.
