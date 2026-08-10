# HYP-ST-XAUUSD-H1-003 — Oracle and compile result

Verdict: `PASS_ORACLE_AND_COMPILE_HANDOFF_TO_FRESH_MT5_PARITY_AUTHORITY`  
Epistemic scope: engineering correctness only; no Strategy Tester, trade, outcome or economic evidence

## Result

The sole `ST003-ORACLE-001` attempt completed. Its sealed full-bar oracle contains 29,460 comparable design rows and reconciles the frozen source-pass invariants: 690 raw flips, 683 exact-next executable flips, seven consumed gaps, 339 LONG and 344 SHORT. The report and receipt record zero outcome fields, returns and simulated trades.

AlphaFactory compiled the unchanged canonical MQL5 source with `0 errors, 0 warnings`.

## Bound artifacts

- Attempt start: `54ED6C2FF92C9B98C7AF447F2C44672723193E9182B59DEC3BC8A26FB2F4A01E`
- Oracle terminal: `7CCB8FE8C33F3369522C93E78B6B12CBAD79FEB408B399827041E6F2EF650396`
- Oracle receipt: `56DC6CBD39721002F892AE9981A47FF397455F57B744277C2C9A3F13EF0C621B`
- Full-bar oracle: `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096`
- Oracle report: `53D23C61A6CC2005B0587834A500F47860EF2104912BD7D61FDA05C52242CFC9`
- MQL5 source: `C4C2A0A700434A2C104551D9AD33ECB8893ACB887E25C6E2E045F4A94638A32E`
- Compiled EX5: `F446A86B86294B8E244173F545E989C664C4BCEB5F79885247B7D0EF8593A06A`
- Compile log: `F640411BAD680146289741EF839FFDBFAF8E68383ACEA519BA8A7EBC8C81837E`
- Immutable compile-archive receipt: `5537AD04B6945027B7552791ADBF3F3B133D6CAE6AFF582C870FC3E4DB2638C9`
- Compile-archive terminal: `AC0639C649A878CAB29F2B3BB16C18153A02CBFEDE938B3E1FDA4438B0E7F564`

The source, EX5 and log are preserved byte-for-byte under `ST003-COMPILE-001` before any later AlphaFactory rebuild. Because the compile completed before this archive hardening was requested, the receipt explicitly records `POST_COMPILE_IMMEDIATE_ARCHIVE_NO_PRESTART_CLAIM` and does not fabricate an attempt-start marker.

## Boundary

HYP003 is complete and must not be retried. It makes no parity or economic claim. A fresh HYP004 authority must freeze the exact AlphaFactory Model-4 audit invocation, contract receipt, canonical run-local journal and `FILE_COMMON` export provenance, current comparator/collector hashes and one unconsumed MT5 attempt before any Strategy Tester process is opened.
