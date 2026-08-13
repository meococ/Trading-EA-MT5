# HYP-CBWR-XAUUSD-M15-001 — engineering failure before accepted economics

- AlphaFactory request reached MT5 and produced an unparsed report at run folder `20260812_003324`.
- The runner then failed the mandatory journal data-quality gate because the EA emitted `m15_*` fields while `Get-DataQualitySeriesProof` requires the canonical M5/M1 D0 field set.
- No P&L, PF, trade count or chart from this run was opened for strategy selection.
- The complete source, EX5, config, report, journal and manifest snapshots remain in the run folder.
- V1 is closed as `INVALID_ENGINEERING_EVIDENCE_ADAPTER`; it has no economic verdict.
- Successor `HYP-CBWR-XAUUSD-M15-002` changes only the evidence proof line and identity/magic/log prefix. Signal, management, risk, cost and date-window rules are unchanged.
