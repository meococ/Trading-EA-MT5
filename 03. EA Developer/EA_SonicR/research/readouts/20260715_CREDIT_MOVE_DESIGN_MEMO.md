# Design memo — Credit HYG/LQD + MOVE bond-vol (W26 exo)

## Surface acquisition

1. **Selected:** Yahoo `HYG`/`LQD` credit relative + `^MOVE` bond-vol.
   SHA-frozen panels lag `observation_date + 1 calendar day`.
2. Spare acquired (not probed): `UUP` TW-USD ETF.
3. Outside killboard: W23–W25 commodity/sector ToT · oil · OHLC densify.
4. Owner W26 explicitly authorizes credit/MOVE after prior VIX-sibling park.

## Mechanisms (a priori)

1. **Credit relative CONT:** HYG/LQD ratio↑ → risk-on → long AUDUSD H1 displace
   (z≥+0.75); ratio↓ → credit stress → short AUDUSD.
2. **MOVE bond-vol risk-off:** MOVE↑ → rates stress → short AUDUSD (invert);
   MOVE↓ calm → long AUDUSD.
3. **Nested book:** day-union prefer larger |z|.

## Explicit non-twins

Not NG/ZW/TIO/Cu/Gold/WTI/Brent commodity ToT, not XLK/XLF, not CNY, not
VIXCLS equity-vol densify, not killed FRED/COT boards, not OHLC HARD PIVOT densify.
