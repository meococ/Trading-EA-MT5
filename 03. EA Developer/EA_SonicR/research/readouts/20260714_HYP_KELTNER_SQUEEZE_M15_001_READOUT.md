# Readout — HYP-KELTNER-SQUEEZE-M15-001 Model 0

Date: 2026-07-14  
Status: **KILLED** (cadence floor fail; PF thin)  
Authority: Owner MT autonomy ~00:46 ICT; GPT waived

## Run

| Field | Value |
|---|---|
| run_id | `20260714_005327` |
| EA | `EA_KeltnerSqueeze` |
| Seed | S654 Mon+Wed+Thu Europe PF~1.15 (not S655 skip-Wed) |
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model / Deposit | 0 / 10000 |
| Overrides | S654-aligned sorted binding (see contract receipt) |
| Cost | tester `current` research-proxy only — **not** Real QFSI |
| Closeout | Alpha required-sidecar `''` quirk after report ready (artifacts kept) |

## Metrics

| Metric | Value |
|---|---|
| Profit factor | **1.10** |
| Trades | **112** |
| Trades/week (elapsed) | **~0.43** |
| Net | **+$335.81** |
| Expectancy | **+$3.00** |
| Max DD | **~4.55%** |
| Win rate | 42.9% |

## Verdict

**KILLED** at Model 0: elapsed cadence **~0.43/wk** outside prereg floor
`[1.0, 6.0]`. PF 1.10 ≥ Owner fast-kill 1.05 but edge thin and sample sparse
vs GOAL. Do **not** rescue via S655 skip-Wed, hour-10 veto, or CI twin.
Independent of VolExp kill shelf remains closed for this ID.

## Paths

- Prereg: `preregs/20260714_H_KELTNER_SQUEEZE_M15_001_PREREG.md`
- De-dup: `readouts/20260714_KELTNER_SQUEEZE_VS_VOLEXP_DEDUP_CLEARANCE.md`
- Run: `02. AlphaFactory/runs/EA_KeltnerSqueeze/20260714_005327/`
