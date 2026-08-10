# HYP-KVO-EURUSD-H1-001 Source Failure

Verdict: `KILL_SOURCE_CONTRACT_CM_ZERO_AT_INDEX_1_NO_ECONOMIC_VERDICT`

The sole source attempt fail-stopped before indicator/event analysis. The frozen literal Klinger initialization requires `CM_1=DM_0+DM_1` and forbids substitution, deletion, interpolation or reset. The first two broker-history H1 rows both have zero range, so `CM_1=0` and `VF_1` is undefined.

Evidence:

- attempt-start SHA256: `A88F9CCFD8BCB9EFB1646CB3B45617326243E931729BD57C0EB8F19A5BDC6CC8`
- failed-terminal SHA256: `D0A6D9E6A5AAEF4DC5D07108F54775DBEEF2376741ACE7BAEDF228C707CADE3E`

No ledger, report, events, returns, trades, PF, MQL5, MT5, validation or holdout were created. The failure rejects only this exact full-prehistory/literal Klinger initialization contract. Same-ID reseeding is forbidden.
