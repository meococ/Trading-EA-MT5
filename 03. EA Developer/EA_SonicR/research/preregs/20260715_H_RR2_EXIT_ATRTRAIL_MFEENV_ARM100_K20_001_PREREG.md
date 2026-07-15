# Prereg — HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001

Date: 2026-07-15  
State on freeze: `preregistered` / `PROBE_SURVIVOR`  
Parent board: same as ARM075/K15; alternate a priori formula

## Locked overrides (exact)

```
InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;InpUseWeekendFlat=1;InpUseTrail=1;InpTrailActivateR=1.0;InpTrailATR_Mul=2.0;InpTrailBE=0;InpPartialClose=0
```

Still ≠ BE@1R: trail = price − k×ATR with BE clamp off (arm@1.0R does not
move SL to entry). Run only after primary ARM075/K15 Model 0, or in parallel
if terminal allows — do not densify from primary readout.
