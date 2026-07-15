# Readout — HYP-ITSM-NYONLY-STRICTALIGN-002

Date: 2026-07-14  
State: `PARKED_AT_MODEL_0` (GOAL unmet)  
Cost: tester `current` research-proxy only — **not confirmed**

## Identity

- Hypothesis: `HYP-ITSM-NYONLY-STRICTALIGN-002`
- Parent: `HYP-ITSM-PULLBACK-M15-001` (PF 1.16 / ~3.27/wk)
- EA: `EA_ITSM`
- Run: **`20260714_191845`**

## Overrides

```
InpKZ1_StartH=15;InpKZ1_EndH=18;InpUseKZ2=0;InpStrictAlign=1;InpRiskPct=0.5;InpRR_Ratio=2.0;InpMaxTradesDay=2;InpTradeFri=0
```

USDJPY M15 | 2021.01.01–2025.12.31 | Model 0 | Deposit 10000

## Metrics (VN report)

| Metric | Parent `003920` | NY-only Strict `191845` |
|---|---|---|
| Trades | 852 | **540** |
| PF | 1.16 | **1.22** |
| Net | +3960 | **+2431.47** |
| tpw | ~3.27 | **2.0712** |
| Equity DD max | ~8.93% | **~7.13%** |

## Verdict

`PARKED_AT_MODEL_0` — PF lifts 1.16→1.22 but still **<1.30**; cadence remains in band.
Structural NY-only + StrictAlign helps but does not clear research bar. Do **not** enable
T10 ADX/H4/skip-Tue or remine hours from this readout.

## Cost honesty

Research-proxy only. Not Real QFSI.
