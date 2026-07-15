# Acquisition readout — ECBASSETSW + Brent

Manifest: `v8_exogenous/manifests/20260715_ECB_BRENT_ACQUISITION_V1.json`  
Contract: `v8_exogenous/contracts/20260715_ECB_BRENT_AVAILABLE_AT_UTC_CONTRACT_V1.json`

## OK

- FRED `ECBASSETSW` weekly Eurosystem assets → panel lag +5d + `wow_pct`
  SHA `FF4F0DF35797E9E9B0B6C5DFA0F70DF28DA62B75FACE6C0D1CB905E0816C0FC4`
- FRED `DCOILBRENTEU` daily Brent → panel lag +1d
  SHA `DA7C6417D263997DDE9D5F76F0A4239FF7E6354AEE7617F90D2815ABFBC45454`

## RAW_ONLY

- FRED `JPNASSETS` monthly BOJ assets — too coarse for this H1 campaign; not probed.

## Explicit non-use

- Not WALCL twin gate on RR2.
- Not WTI-USDCAD ToT clone.
- Not HY/MOVE/DTWEX VIX sibling.
- DTWEX not acquired this pass (VIX-sibling ban still binds for risk-off shopping).

Acquired_at: `2026-07-14T17:19:02.741407Z`
