# HYP-STBS-XAUUSD-M15-017 — completed audit, frozen evidence-contract mismatch

## Verdict

`KILL_FROZEN_DATA_FINGERPRINT_AND_TEARDOWN_REASON_CONTRACT_MISMATCH_AFTER_VALID_ZERO_TRADE_RUN_NO_ECONOMIC_VERDICT`

The sole HYP017 attempt compiled with zero errors/warnings, launched MT5, completed the requested tester horizon and produced a non-truncated journal. The runner then failed closed because the manifest data fingerprint did not equal the stale fingerprint inherited by the HYP016/HYP017 audit package. HYP017 cannot be retried.

## Exact frozen mismatch

- frozen expected data fingerprint: `077437E0038B40FEDB8AC611CAFE410B2FF8D0A90A742F0C52336F728D8C0BF4`
- actual complete-run fingerprint: `B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`

The actual value was already preregistered before outcomes as HYP013's expected packet fingerprint. The older `077437...` value came from the incomplete HYP013 execution and was carried into later audit revisions as if it described the complete window.

Two additional frozen assumptions were disproved by the complete artifact:

- AlphaFactory read three journal files, while only two contained the same exact EA range (`exact_match_count=2`, `distinct_range_count=1`); the journal itself contains exactly two copies of every signal and summary.
- both exact summaries contain `reason=1`, MT5 `REASON_REMOVE`, rather than `reason=0`. This is a platform teardown code, not runtime failure; `failed=false` and every forbidden send/deal marker is absent.

## Outcome-blind engineering observations

These observations do not establish profitability:

- history quality `98%`, full coverage and exact native series proof;
- journal `truncated=false`, SHA-256 `3284EA885A965123FB0BDA1B51F126524F014C1ABD95D43BDCF66E222A9361CE`;
- 690 unique signals, each duplicated exactly twice; raw/executable/gaps `690/683/7`;
- LONG/SHORT `339/344`;
- ATR-ready, geometry-ready and margin-ready all `683`;
- margin rejects, emergencies, forced stop-outs, entries, closes and lifecycle rows all zero;
- zero `STBS_FATAL`, order-request or deal markers;
- report Orders section exact-empty, one USD 100,000 funding-balance row and zero completed trades.

## Immutable evidence

- authorized row: `55F697D32A22F752ADC5DA4F2E98A0AE3A069E763F2BFEB90584660DF706B493`
- attempt start: `1A065A5E168095755300CF5D25D9526E9DB10B65525F542C6671A55C3B05D643`
- attempt terminal: `97228B36FA2E7A1511AC113DD43212C2382BB3B72724B2D1CDDE2D58D60416DD`
- run manifest: `8829191F4957ACF162F46B90EA1886AF26BB26B6271CC93638CE62E89319CFE7`
- report: `8AC7C0005D02BFF4E963049107ED1AA950BFFA3205E906EB1781D386866286DB`
- task packet: `52F75B8CA1A909DEFB6CDD3C339AF6023A1FE70D43EED33B170AFA44DEECBD1F`
- contract receipt: `96914D0FFD672876ED09D67A012CBA11E6FC02C46CA9CAB8130238CFE9456E8D`
- fresh run EX5/log: `832712C5A392400B46BB2B44F1273B05DDEDD25793DA7CB020B844EDD003E30B` / `886A9883DEDC54D2FC8236B8075A72FD1CDF61F8C407DE32E8402E95110300E6`

## Narrow continuation

No MT5 rerun is justified. A fresh comparator-only child may review the immutable HYP017 run if it freezes the actual pre-known `B326...` fingerprint, exact three-file/two-match journal provenance and `REASON_REMOVE=1`, while retaining every zero-order/source count and no-economic boundary. It must not read or claim PF/returns.
