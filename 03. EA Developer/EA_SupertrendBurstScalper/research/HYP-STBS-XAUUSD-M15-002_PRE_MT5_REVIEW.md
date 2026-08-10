# HYP-STBS-XAUUSD-M15-002 — Conditional independent pre-MT5 review

- Review time: `2026-08-09T02:50:00Z`
- Status: `PASS_CONDITIONAL_AFTER_HYP001_TERMINAL`
- Scope: static package review only; no HYP002 packet, AlphaFactory, MT5, source data, outcome or economic access.

Frozen package reviewed:

- Prereg: `35B142CB446A187FDFB042A5374C9D5C1018CE1FB98C1879AB4E43523D7461E8`
- Packet builder: `02E876C2C59878ED9B0D119728C2F362B301E1B629209C8AFA3794489DF26EEE`
- Outer MT5 runner: `B1124D9F4BC70CAD65C03F348F25BFA7459141704EABB7EC5DA414AC06762687`
- Governance tests: `0470A2E9EEED7BD96BD4F46619F7DDEA2488AB8D9F2EB3F37E4B7B1AA4BB4AA2` (`12/12 PASS`)
- Frozen inner runner dependency: `C4F2976F919EF9345CFC15891A9A8066F1FB5D474635C88BB29D047456645C14`
- Frozen inner MQL5 source: `B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D`

The outer HYP002/inner journal-HYP001 adapter is coherent: AlphaFactory, task packet, receipt and run manifest use HYP002; the unchanged already-reviewed source emits its HYP001 implementation identity, which is scoped only while validating the journal and restored afterward. The builder and runner pin the inner runner literal, require latest HYP001 `killed` with the exact chronology verdict, and bind its raw terminal-row SHA. Post-claim chronology is frozen as:

`probe authority <= packet start <= receipt generated <= packet terminal <= screened authority <= MT5 start`.

All Model0 performance, Model4, trade, outcome, economic, optimization, validation, holdout, promotion, paper and live permissions remain false. This conditional PASS becomes actionable only after actual UTC exceeds `2026-08-09T04:46:00Z` and a validator-valid HYP001 killed terminal row exists. It authorizes only a fresh HYP002 probe row and one packet-build attempt; a second reviewed screened row is still required before MT5.

The final hardening adds executable mutation coverage for packet-consumed/MT5-zero/run-compile-zero terminal metrics, every forbidden terminal permission, all five possible order inversions in the six-timestamp chain, and byte tampering of each canonical HYP001 failure/receipt/terminal artifact. Builder and runner independently rehash those actual files against literal constants.
