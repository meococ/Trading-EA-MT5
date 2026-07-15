# Design memo — Sector relative + copper-gold (W23 exo)

## Surface acquisition

1. **Tried EVZCLS (CBOE euro FX vol)** — FRED timeout; DBnomics 404; Yahoo EVZ unusable →
   `PROVE_UNAVAILABLE_PICK_NEXT`.
2. **Selected:** Yahoo `XLK`/`XLF` sector relative + `HG=F`/`GC=F` copper-gold ratio.
   SHA-frozen panels lag `observation_date + 1 calendar day`.

## Mechanisms (a priori)

1. **XLK/XLF growth-lead:** tech vs financials leadership = growth risk-on → AUDUSD
   follow H1 displace (long if z≥+0.75; short if z≤−0.75).
2. **Cu/Gold ratio:** industrial copper vs haven gold = real-activity/growth factor
   beyond oil curve → same AUDUSD CONT displace contract.
3. **Nested book:** day-union prefer larger |z|.

## Explicit non-twins

Not VIX level risk-off, not SPX−bond, not WTI/Brent oil ToT, not OHLC HARD PIVOT densify.
