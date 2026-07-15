# Acquisition readout — XLK/XLF + Cu/Gold

Manifest: `v8_exogenous/manifests/20260715_SECTOR_CUGOLD_ACQUISITION_V1.json`  
Contract: `v8_exogenous/contracts/20260715_SECTOR_CUGOLD_AVAILABLE_AT_UTC_CONTRACT_V1.json`

## OK

- Yahoo XLK/XLF daily → ratio panel lag +1d  
  SHA `47911C4420655A8A6A808F82830EEDF40156CD807F2D47DCD50D45DED8B9D15E`
- Yahoo HG=F / GC=F → copper-gold ratio panel lag +1d  
  SHA `E424ABE51B82E5F50DF421024BB4A672C601E5D36A7CB6DA7157220AECC88DF5`

## Unavailable this pass

- EVZCLS / FX vol index (FRED timeout; DBnomics 404; Yahoo EVZ unusable) —
  documented in contract `unavailable_this_pass`; pick-next = sector+cugold.

## Explicit non-use

- Not VIXCLS risk-off twin.
- Not SPX−DGS10 equity-bond twin.
- Not WTI/Brent oil ToT densify.
- Not MOVE/HY/DTWEX shopping.
