# EA_NativeSessionStatsProbe

Source-only MT5 capability probe for native broker session aggregates across
XAUUSD and seven major FX pairs. It never opens orders, reads OHLC/settlement
prices, or authorizes economics.

Current terminal record: `HYP-NATIVE-SESSION-STATS-XAUFX-H1-004` is
`PARK_DATA_QUALITY_HISTORY_49_BELOW_97_SOURCE_UNREAD`.

- static contract tests: 5/5 PASS;
- fresh compile: 0 errors, 0 warnings; EX5 15,816 bytes;
- final bound run: `20260813_225528`;
- report produced, but AlphaFactory rejected History Quality 49 because the
  frozen data gate requires greater than 97;
- no `NSSP_*` source values and no performance metrics were read;
- no economic, promotion, paper or live authority exists;
- do not rerun, lower the quality gate, or start another `SYMBOL_SESSION_*`
  probe as a rescue.

The exact closeout is
`research/HYP-NATIVE-SESSION-STATS-XAUFX-H1-004_SOURCE_UNREAD_PARK_RECEIPT.json`.
