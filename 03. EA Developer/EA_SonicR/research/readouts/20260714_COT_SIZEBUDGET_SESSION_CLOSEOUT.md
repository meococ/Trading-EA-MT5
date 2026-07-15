# Session closeout — COT size-budget + spread-table EV

Date: 2026-07-14 ~24:00 ICT  
Status: `BOTH_EV_KILL_OR_GAP / NO_MODEL0 / CONTINUE_STRUCTURAL_SEARCH`  
Lane: single checkout; no-Git; Real/QFSI hygiene parallel only

## Executed

### B — COT size-budget (a priori; not |z| retune)

| ID | Semantics | N | PF | tpw | x1.5 | Lift | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| Baseline RR2 `194548` | unscaled | 524 | 1.3794 | 2.0099 | 1.0134 | — | shelf |
| `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001` | keep-all; \|net_lev\| pctile size | 524 | 1.4134 | 2.0099 | 1.0421 | +0.0287 | **KILL** `stress_fail` |
| `HYP-RR2-CFTC-JPY-ASSETMGR-SIZEBUDGET-001` | keep-all; \|net_AM\| pctile size | 524 | 1.3756 | 2.0099 | 1.0118 | −0.0016 | **KILL** `stress_fail` + `no_stress_lift` |

Authoritative LevMoney receipt: `ED98F1FAD2A2E38E2726F9C636C913790EE79E362BD8FD514E3ED9DB477470B7`  
Authoritative AssetMgr receipt: `916636B3E4DE7FEA53FC28A5D3375A6A8D0FD6FB88B4DA71E5AF56865E19FFEE`  
Panel SHA: `93D69F957A503B38C729F41D2E6B6D714A25EB330147383867C65A5EFC19AE54`

**VOID (wrong semantics):** `preflight/20260714_COT_SIZEBUDGET_RR2_OFFLINE_PROBE.json` / matching readout claiming N=117 skip-gate. That is a gate clone, not size-budget. Do not cite.

### A — Broker session×symbol spread table

**GAP.** No multi-year reconstructable session×symbol spread/commission surface. QFSI ticks = single calendar day `2026-07-14`; commission incomplete. Diagnostic only: `preflight/20260714_QFSI_TICK_HOUR_SPREAD_DIAGNOSTIC.json` — **not** research cost surface; **no** RR2 gate-probe on it. See `readouts/20260714_BROKER_SESSION_SPREAD_TABLE_GAP.md`.

## Model 0

Withheld (no PROBE_SURVIVOR).

## Next autonomous EV

1. Stop COT size-budget / |z| / AssetMgr size family on RR2 shelf — exhausted for this panel.
2. Do not invent spreads; accumulate multi-day Real quote+commission before cost-surface freeze.
3. Next object must be **outside** Wave1–8 / dichotomy / COT gate+size families — new structural or independent exo join.

Best shelf unchanged: RR2 `20260714_194548`. Phase-0 still BLOCKED. GOAL unmet.
