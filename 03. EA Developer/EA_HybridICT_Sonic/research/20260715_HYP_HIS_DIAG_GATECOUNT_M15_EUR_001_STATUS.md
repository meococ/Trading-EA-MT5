# HYP-HIS-DIAG-GATECOUNT-M15-EUR-001 — Status readout

Date: 2026-07-15  
Owner: **B** authorized

## Done

| Item | Status |
|---|---|
| Prereg | `research/20260715_HYP_HIS_DIAG_GATECOUNT_M15_EUR_001_PREREG.md` |
| Code | `InpUseDragonSlFloor=false` default + OnDeinit gate counters |
| Compile | **OK** 58732 bytes (`EA_HybridICT_Sonic` v1.01) |
| Contract receipt | minted `…/20260715_HYP_HIS_DIAG_GATECOUNT_M15_EUR_001_CONTRACT_RECEIPT.json` |

## Blocked

Model 0 backtest **fail-closed**: unrelated `terminal64` PID **19064** running
(started ~17:00 ICT — treat as Owner Real / live session). AlphaFactory will
not stop it.

## Next

Owner closes Real (or confirms when free) → remint receipt (git dirty drift) →
rerun:

```powershell
# after Real closed; remint then:
.\02. AlphaFactory\alpha.ps1 backtest "EA_HybridICT_Sonic" `
  -Symbol EURUSD -Period M15 -From "2020.01.01" -To "2026.07.15" -Model 0 `
  -HypothesisId "HYP-HIS-DIAG-GATECOUNT-M15-EUR-001" -RunRole control `
  -Deposit 100000 -Overrides "<from receipt>" `
  -ContractReceipt "…DIAG…RECEIPT.json" -ContractReceiptSha256 "<fresh>"
```

DIAG success = N>0 and/or counters show `slOk`/`pendingOk` > 0 — **not** PF claim.
