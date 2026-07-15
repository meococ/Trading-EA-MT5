# Design memo — UUP TW-USD + DTWEXBGS dollar TWI (W27 exo)

## Surface acquisition

1. **Selected:** Yahoo `UUP` (W26 spare → W27 primary) + FRED `DTWEXBGS`
   (broad-goods dollar TWI). SHA-frozen panels lag `observation_date + 1d`.
2. DTWEX status: ACQUIRED.
3. Outside killboard: W26 credit-MOVE · W23–W25 commodity ToT · OHLC densify.

## Mechanisms (a priori)

1. **UUP USD-strength invert:** UUP↑ → USD strength → short AUDUSD H1 displace
   (z≥+0.75); UUP↓ → long AUDUSD.
2. **DTWEXBGS TWI invert:** same USD-strength → AUDUSD short on high z.
3. **Nested book:** day-union prefer larger |z| (when both present).

## Explicit non-twins

Not HYG/LQD / MOVE densify, not NG/ZW/TIO/Cu/Gold/oil ToT, not VIXCLS,
not killed FRED/COT boards, not OHLC HARD PIVOT densify.
