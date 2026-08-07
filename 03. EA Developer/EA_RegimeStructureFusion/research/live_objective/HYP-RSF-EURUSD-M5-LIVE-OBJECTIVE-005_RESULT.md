# HYP-RSF-EURUSD-M5-LIVE-OBJECTIVE-005 — terminal result

## Verdict

`KILL_ZERO_TRADES_CAUSAL_TARGET_UNAVAILABLE`

The single frozen EURUSD M5 Model-0 development run completed on 105,949,201 ticks with 100% history quality and produced zero trades. This is an economic kill under the preregistered minimum of 100 trades. No threshold, session, route, year, or parameter rescue is allowed under this hypothesis ID.

## Engineering evidence

- Run: `20260807_093015`
- Source SHA-256: `C2ACC82167746612C9EEE1DD91C9FE7C2E0E56CA64799E1A80C690BB131B1831`
- EX5 SHA-256: `9B7EE8FFEF5CE9F3327B6FCFC8B668DE30068DB7606E786D86A22BCD6E5860C7`
- Report SHA-256: `68158F988EAFA8EB34FC2A6F0E88A02C410EF9C7035CD30360A690AE8A81A88E`
- RunMeta SHA-256: `C1DF6C2143546C715BEA66EFE11BB27B131C16FF31C6B1B8396B37D8053FB46C`
- EntryContext SHA-256: `213847DF0BF73BC3E5949DC1CC11523601985FEA7343BB0B43D2F3CAB2C0EDD6` (0 rows)
- Lifecycle SHA-256: `9D0CC6A7F1986CD3230CE2BA275B0116C7CD2F12AF9D25D7B10C922420CA6EC7` (0 rows)

Required sidecars were present and internally consistent. AlphaFactory's enhanced trade analyzer exited with `No trades found in report`; this is expected for a zero-trade economic result and does not invalidate the run artifacts.

## Causal failure radius

RunMeta recorded:

- structural context rejects: 602
- structural no-objective rejects: 5,598
- structural armed/retested/confirmed: 0 / 0 / 0
- entries/final closes: 0 / 0

The gate did fail closed exactly as coded. The failure is the objective data contract: TB consumes the nearest same-direction swing on the BOS/MSS bar, while its current buffers expose only that nearest swing. Requiring a still-live swing high above a bullish break (or swing low below a bearish break) is therefore structurally unavailable at arm time, not merely an overly high numeric threshold.

## Next hypothesis boundary

Any continuation must use a new mechanism and ID. The allowed next idea is a bounded pool of causally confirmed, unconsumed swing-liquidity levels. The nearest still-unconsumed level ahead of price may become the objective; the consumed break level is forbidden. This is a new indicator/EA data contract, not a parameter rescue.
