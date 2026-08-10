# HYP-APC-XAUUSD-M15-001 — engineering failure, no economic verdict

The sole frozen TRAIN invocation compiled and reached MT5, but AlphaFactory rejected the run before economic acceptance.

- Run: `20260810_194807`
- Source snapshot SHA256: `ED33D6D4E41144BA423D3039C9C12FB6166A0B6C2583918F0B8655971B5FECF6`
- EX5 snapshot SHA256: `DEF473FDDF0A602627339FCB86F5B5322306B1D1312FEF32503A6DC35B521F17`
- Run manifest SHA256: `2262AAD21D30611FD41800BF98058E20FE6D965DBBDE4D470AC41ED0246528F8`
- Report SHA256: `79A8658CD9B4586FDBBCEDA38C644106284D2C8ABE4D0A5FFE717891597AC3A6`
- Journal SHA256: `DF0593ACF4223D267AC632FB898F4050DB27C5DDC7FA86224153502BB94AC72A`

Two pre-economic engineering failures are conclusive:

1. The journal contained zero `DATA_EPOCH_D0_SERIES_PROOF` records, so the mandatory fixed-window D0 provenance gate failed.
2. Three valid broker-native flat impulse bars were classified as `TRUE_RANGE_INVALID`, and the terminal summary reported `runtime_failed=true`.

Raw report outcomes are inadmissible and were not used to modify signal thresholds, stop, target, holding time, direction, risk, session or split. Exact APC001 is terminal. A fresh APC002 engineering child may add the D0 proof and treat a zero-range impulse as a consumed non-signal while preserving the frozen market mechanism.
