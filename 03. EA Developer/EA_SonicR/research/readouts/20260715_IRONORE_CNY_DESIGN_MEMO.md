# Design memo — Iron ore ToT + CNY strength (W24 exo)

## Surface acquisition

1. **Tried CNH=X / USDCNH=X (offshore CNH)** — Yahoo n≈1 unusable →
   `PROVE_UNAVAILABLE_PICK_NEXT`.
2. **Selected:** Yahoo `TIO=F` SGX iron ore + `USDCNY=X` inverted to CNY strength.
   SHA-frozen panels lag `observation_date + 1 calendar day`.

## Mechanisms (a priori)

1. **Iron ore ToT:** Australia bulk-export terms-of-trade → AUDUSD follow H1
   displace (long if z≥+0.75; short if z≤−0.75).
2. **CNY strength:** China demand / CNY firm vs USD → same AUDUSD CONT displace.
3. **Nested book:** day-union prefer larger |z|.

## Explicit non-twins

Not XLK/XLF sector, not Cu/Gold, not WTI/Brent oil, not VIX-sibling, not killed
FRED boards (WALCL/ECB/MMF/G10 overnight), not OHLC HARD PIVOT densify.
