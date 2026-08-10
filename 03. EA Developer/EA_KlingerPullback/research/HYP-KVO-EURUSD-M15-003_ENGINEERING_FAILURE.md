# HYP-KVO-EURUSD-M15-003 — Engineering failure

- Verdict: `KILL_ENGINEERING_ENTRY_TRANSPORT_CLASSIFICATION_AND_JOURNAL_TRUNCATION_NO_ECONOMIC_VERDICT`
- Run: `EA_KlingerPullback/20260810_210309`
- Manifest SHA256: `56EE4DAC32061ECBEF42C95F34C3DD7130078136007161A73C78099F60A55C4F`
- Report SHA256: `5A1E302A7929153E9E57F5F17D2108C8DDF6984955833A67478348DC7789A3A3`
- Truncated journal SHA256: `2954F705E2B0A25FDDEA6296D31573710A0420A59904CA1068CA866343EC0B96`
- Source SHA256: `5D7E989E674C7D85E008FC58A44FB9335AB15C5B7A920EBBED60EF7FD0D66F73`
- Run EX5 SHA256: `04BE7EF277A70C167D91DBFAFE61E06109D2A32E016713A0B27B1F625339D06C`
- Config SHA256: `C281BE5173C897A550A69327E30C7F51C19A6CAD62E645F0642CA9ED30372F33`

MT5 completed and wrote the report. AlphaFactory correctly stopped before economic analysis because the raw two-file journal delta hit exactly 1,048,576 bytes and `truncated=true`.

The full agent journal independently shows a second engineering failure before any admissible economics: at 2010-02-16 00:00, `OrderSend=false` returned exact `TRADE_RETCODE_MARKET_CLOSED`, `order=0`, `deal=0`. The overly conservative HYP003 transport branch marked this definitive no-fill response fatal. Terminal summary: 197,804 closed bars; raw 9,524; LONG 4,798; SHORT 4,726; accepted entries 31; rejects 9,482; closes 1; clock rejects 11; invalid 0; `runtime_failed=true`.

The 9,524 routine signal rows also dominated the journal. The exact agent segment was 5,189,374 UTF-16 bytes; deleting only routine signal rows projects 78,574 bytes for the observed 31-entry prefix. No PF, PnL, expectancy or outcome is admissible. Same-ID retry is forbidden.

A fresh child may preserve all market and risk logic while: (1) recognizing only exact MARKET_CLOSED + zero result IDs + verified zero inventory as definitive no-fill even when OrderSend returns false; (2) removing routine per-signal/per-entry/nonfatal-reject prints; and (3) binding a larger explicit journal cap justified before the next run.
