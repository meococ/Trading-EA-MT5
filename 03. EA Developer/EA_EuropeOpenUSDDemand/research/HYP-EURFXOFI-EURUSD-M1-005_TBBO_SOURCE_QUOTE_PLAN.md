# TBBO SOURCE QUOTE PLAN - HYP-EURFXOFI-EURUSD-M1-005

Frozen on `2026-07-30` before HYP005 vendor access. MBP-10 and MBP-1
full-history quotes exceeded the Owner's USD2.25 ceiling with zero paid calls.

HYP005 uses CME 6E `tbbo`: each trade event with contemporaneous best bid and
ask. The future feature is signed aggressive trade-flow imbalance in the final
15 seconds before 14:15 Europe/Berlin, with spread/quote context. It cannot be
called full-depth OFI or EBS dealer flow.

- Exact HYP002 date ledger SHA256:
  `EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF`
- 1,359 requests; TRAIN/VALIDATION/HOLDOUT = 630/526/203.
- `GLBX.MDP3` / `tbbo` / continuous `6E.v.0`.
- Each window: `[14:14:45,14:15:00) Europe/Berlin`, IANA DST.
- Free allowlist: metadata cost and billable-size only; full coverage required.
- Single shared Owner ceiling: USD2.25. No paid call is authorized here.

Forbidden: MBP fallback, window/date change, timeseries/batch/download, price
decode, outcome join, economics, MQL5, Model 0, promotion, paper or live.
