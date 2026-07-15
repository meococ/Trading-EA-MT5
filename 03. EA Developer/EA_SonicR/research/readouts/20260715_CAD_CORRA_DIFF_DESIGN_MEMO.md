# Design memo — CAD CORRA vs USD differential expand (USDCAD)

Date: 2026-07-15
Data: BoC CORRA AVG.INTWO alt-source freeze + G3 USD; +1bd lag.

## Design
`HYP-USDCAD-CORRA-USD-DIFF-EXPAND-H4-001`
|Δ(CORRA−USD)|≥5.0bp available-at → trade USDCAD with CAD richness;
H4≥08; SL 1.5×ATR; RR=2.0; hold≤10.

## ≠ kill shelf
≠ FX3 Mon→Thu fundproxy; ≠ flush-MR; ≠ anticarry×vol;
≠ V8 weekly/daily/5bp/vol on G3; ≠ USBILL; ≠ WTI-USDCAD commodity.

Panel SHA: `26AF77CAFD3416F0F629CC5840C67B0B0C368CF745B1C3166628DE275CE07FD9`
