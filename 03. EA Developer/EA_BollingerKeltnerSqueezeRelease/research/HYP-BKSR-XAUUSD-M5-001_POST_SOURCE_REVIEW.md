# HYP-BKSR-XAUUSD-M5-001 — Independent post-source review

Verdict: `PASS_PARK`

Scope: read-only reconciliation of the frozen source-feasibility evidence. The source Parquet files were not reopened or rehashed.

## Integrity

- Attempt start SHA256: `2FBA09ADE2C09DA3188FEC9262A1BC35C765356E78ABF9DF5A1951D7B7C6FC0E`
- Report SHA256: `973D45AA2CE6F6B0319D622547A55EF89BB14FA42471AFC27B5CD6DD16853F50`
- Ledger SHA256: `B05D14A8E38D27B83C4E21969D4D3F6DF295CECAF901D1EE456175C875538C53`
- Receipt SHA256: `7D66F89CE9108B4F7EDAA4E067DEEE59468B38C543B10E48F74B39B091283A72`
- Attempt terminal SHA256: `C593C7B0667A4D3D7DC98495FD6C77969B6AB93B5390A756081B0DB7D86793D6`
- Source result SHA256: `98C9601DEC657D63BFF854DC84888A91CDCCB02DB36EF769504238C941DE7D76`
- Failure packet SHA256: `C270103837B0EEDC13974B56FC8982E5BD6E14E81FD89A4B8E83D75B3180FEE6`

All five attempt artifacts rehash and link exactly. The result and failure packet preserve the source-only, no-outcome, no-economics boundary.

## Independent reconciliation

- Ledger rows are unique, strictly ordered, and use the exact frozen allowlist.
- Raw events: `757`; executable events: `731`; exact-clock rejects: `26`.
- Direction: `363 LONG`, `368 SHORT`.
- Exact H1-release to native-M5 decision coverage: `731 / 757 = 0.9656538969616909`.
- Pooled cadence: `731 / 260.857142857 = 2.8023001095290256` executable events/week.
- Calendar-year counts: `139 / 130 / 169 / 157 / 136`; all annual cadence and concentration gates pass.
- Zero clock, squeeze-cluster, strict-release, band, or direction violations were found.

## Terminal interpretation

The sole failed frozen gate is `raw_event_exact_m5_decision_coverage >= 0.97`. The exact H1 Bollinger-inside-Keltner squeeze-release mapping is therefore parked for source feasibility. This is not an economic no-edge result, and it does not authorize lowering the coverage gate, weakening the dual UTC/source-epoch mapping, retrying the same ID, or opening MQL5/economic stages.
