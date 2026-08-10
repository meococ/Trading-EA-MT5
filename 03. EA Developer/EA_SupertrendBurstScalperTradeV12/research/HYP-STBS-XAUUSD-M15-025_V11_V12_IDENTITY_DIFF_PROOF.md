# HYP025 V11-to-V12 identity-only diff proof

V12 is the narrow source clone required to make the outer Alpha run-manifest identity and inner MQL5 RunMeta/lifecycle identity both equal `HYP-STBS-XAUUSD-M15-025` without changing the generic cost builder.

The exact source diff is limited to:

1. property version `11.00` to `12.00`;
2. property description text;
3. default and OnInit-guarded hypothesis `HYP024` to `HYP025`;
4. default and OnInit-guarded variant to `STBS_H1_FLIP_M15_BURST_TRADE_V12_IDENTITY_CLONE`;
5. default and OnInit-guarded magic `5604124` to `5604125`;
6. constant EA name V11 to V12.

No signal, indicator, timeframe, bar timing, ATR, price geometry, margin loop, volume choice, request, SL, TP, hold, exit, lifecycle, risk lock, telemetry event, cost or acceptance logic changed.

- V11 source SHA-256: `7CC7A9D7C30216A1669D84AEEA867E32EA15F2E9E8C195D171BD574A4D2EB0BC`
- V12 source SHA-256: `D96F55A26F277CFC3FDC4E23A11A84C74598C111639E629CEC1877AC3F7704C5`
- V12 static EX5 SHA-256: `229E76BA503471AC86C947463FF1DD340FF1B182E9A5D8A193DFD16AFEEFD27F`
- V12 compile log SHA-256: `B2D9AA542737168BEC8A9A2A4135D407A3CE2546577B398076E5328B4AD7BEF9`, exactly `0 errors, 0 warnings`.
