# Design memo — Natgas LNG + Wheat ag ToT (W25 exo)

## Surface acquisition

1. **Selected:** Yahoo `NG=F` NYMEX Henry Hub natgas + `ZW=F` CBOT wheat.
   SHA-frozen panels lag `observation_date + 1 calendar day`.
2. Outside killboard: ironore-cny · sector-cugold · oil · VIX-sibling ·
   killed FRED/COT boards · W1–W24 OHLC densify.

## Mechanisms (a priori)

1. **Natgas LNG ToT:** Australia LNG/energy-export terms-of-trade → AUDUSD
   follow H1 displace (long if z≥+0.75; short if z≤−0.75). NG ≠ crude oil.
2. **Wheat ag ToT:** Australia softs/ag export channel → same AUDUSD CONT displace.
3. **Nested book:** day-union prefer larger |z|.

## Explicit non-twins

Not TIO iron ore, not USDCNY/CNY, not XLK/XLF sector, not Cu/Gold, not
WTI/Brent oil, not VIX-sibling, not killed FRED/COT boards, not OHLC HARD PIVOT densify.
