# Acquisition readout — forwards / signed-flow

Manifest: `v8_exogenous/manifests/20260714_FORWARDS_SIGNEDFLOW_ACQUISITION_V1.json`

## OK

- NY Fed Primary Dealer all timeseries CSV (~26MB) → panel `PDPOSGST-TOT`
- FRED `WRMFSL` / `WIMFSL` retail+inst MMF
- FRED `DEXJPUS` + Yahoo chart `6J=F` → forward-basis panel
- BoC Valet FX daily (spot; not true forwards — raw only)
- FRED CP90 AA (basis raw; not probed this pass — VIX-sibling risk)

## FAIL

- Stooq `jf.f` / `ef.f`: JS bot challenge
- Yahoo v7 finance/download: empty/crumb
- BoC: no free FX-forward group found in Valet lists
