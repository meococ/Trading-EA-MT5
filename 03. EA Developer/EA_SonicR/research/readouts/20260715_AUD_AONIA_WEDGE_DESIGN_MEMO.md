# Design memo — AUD AONIA vs Cash Target wedge expand (AUDUSD)

Date: 2026-07-15
Data: DBnomics RBA F1 FIRMMCRID/FIRMMCRTD freeze + G3 USD; +1bd lag.

## Design
`HYP-AUDUSD-AONIA-TARGET-WEDGE-EXPAND-H4-001`
|Δ(AONIA−Target)|≥5.0bp available-at → AUDUSD with MM stress;
H4≥08; SL 1.5×ATR; RR=2.0; hold≤10.

## ≠ kill shelf
≠ CORRA−USD Δdiff expand densify (different series + wedge object);
≠ Mon→Thu fundproxy / flush-MR / anticarry×vol / V8 / USBILL.

Panel SHA: `98E8204CACE0CC38042AEB80309813FBE36377591137D443E2F3C7094212D9FE`
AONIA SHA: `76C464CE0FA2E5C2EE6C8231AFA70F04E4582345D2DAC3D4B0E8B0D50FF72460`
