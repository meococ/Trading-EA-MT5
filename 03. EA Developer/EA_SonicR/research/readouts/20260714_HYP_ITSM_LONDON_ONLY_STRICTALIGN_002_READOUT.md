# Readout — HYP-ITSM-LONDON-ONLY-STRICTALIGN-002

Date: 2026-07-14  
State: `PARKED_AT_MODEL_0` (GOAL unmet)  
Cost: tester `current` research-proxy only — **not confirmed**

## Identity

- Hypothesis: `HYP-ITSM-LONDON-ONLY-STRICTALIGN-002`
- Parent: `HYP-ITSM-PULLBACK-M15-001`
- EA: `EA_ITSM`
- Authoritative run: **`20260714_192116`** (twins `192344` / `192606`)

## Overrides

```
InpMaxTradesDay=2;InpRiskPct=0.5;InpRR_Ratio=2.0;InpStrictAlign=1;InpTradeFri=0;InpUseKZ2=0
```

(London KZ1 defaults retained; KZ2 off; StrictAlign on)

USDJPY M15 | 2021.01.01–2025.12.31 | Model 0 | Deposit 10000

## Metrics (VN report `192116`)

| Metric | Value |
|---|---|
| Trades | **482** |
| PF | **1.12** |
| Net | **+1641.16** |
| tpw | **1.8488** |
| Equity DD max | **~7.45%** |

## Verdict

`PARKED_AT_MODEL_0` — worse than NY-only sibling on PF (1.12 vs 1.22) and loses parent
cadence headroom. Survives kill; fails GOAL. Do not flip back to dual-KZ densify from
this readout without a new child ID.

## Cost honesty

Research-proxy only. Not Real QFSI.
