# ALERT_FIRST_CASEBOOK_V1.3 collection readout

Date: 2026-07-16  
Verdict: `DATA_COLLECTION_PASS / LABEL_GATE_PENDING / GOAL_UNMET`  
Collection id: `DATA-ACQ-UNICORN-CASEBOOK-V1-002`  
Authority: no trading hypothesis, no Model-0 performance claim, no outcome join

## Bound change

Canonical v1.23 retains the exact v1.22 detector, score, thresholds, session,
entry, stop, target and management settings. The engineering-only delta binds
the source SHA256 into every casebook row and metadata file, adds a blank true
breaker validity label, restricts trade mutation to Strategy Tester, fails
closed on incomplete position/order/history enumeration, binds broker deviation
to the declared slippage budget, and reconciles money risk to the actual fill.

Exact source SHA256:
`10E278435644E63FD6418047AC775537CECEE8BBA4A9E5D89842E0F15312CB18`.
The V1.2 collection and label-calibration artifacts remain preserved, but they
are diagnostic-only for the labeling gate because their row/meta schema did
not bind source SHA256 and omitted the true-breaker label.

## Runtime result

Authoritative AlphaFactory run `20260716_155111` used XAUUSD M5,
2024-01-01 through 2025-12-25 and Model 0 strictly as a zero-trade data
collector. Both trade-mutation switches were false. The report and enhanced
summary prove exactly zero trades and explicitly set
`performance_metrics_authorized=false`.

- Detector rows: 200/200.
- Unique event IDs: 200.
- Nonblank human-label/outcome cells: 0.
- Strategy Tester trades: 0.
- Casebook SHA256:
  `F7CA7B9EB7E231CB3898F7B8AF852481663BA0A87E808C312E1DB96512BEDAC1`.
- Metadata SHA256:
  `CCBAC922FDD92694219FF179F05E81472AAE8D38FCA0E9D45B5ADBF34AD7D71D`.
- Run manifest SHA256:
  `D6F960296F901DC6475C8D6341ED01BDBE3DA8F9504E6B6BC7E22F803ACC8F26`.
- Report SHA256:
  `41716B84F015CF4935F07C5673004BCD18FC7629340EDB88E54DBC91AF2FD05A`.
- Collection validation SHA256:
  `3867A96EE23FF67C1E939C219C430EB94220201A4448173DD9BAC1314B0B5A3A`.

The validator checks the manifest collection id, exact source hash across the
manifest/meta/rows, V1.3 contract id, blank breaker and other human labels,
unique event ids, D-drive terminal path and zero-trade summary.

## Harness failure and repair

Run `20260716_154857` is an invalid pre-collection attempt. AlphaFactory wrote
the numeric optimization tuple to a string input, so MT5 passed the literal
`<sha>||<sha>||0||<sha>||N`; the EA correctly rejected `OnInit`, no casebook was
created, and required-sidecar validation stopped the run.

The harness now identifies declared MQL5 `input string` names and emits plain
key/value syntax for them while retaining the optimization tuple for numeric
and boolean inputs. A red-then-green regression locks this behavior. The exact
harness is receipt-bound:

- AlphaFactory SHA256:
  `AAB40CE246D3309000D0963545E9DE9F7AFE1A1C77D45645F5D079AB901BD633`.
- Contract receipt SHA256:
  `C9925045E6635142D47270539F80C03F0D4430EC43262EA62C766756F49FF332`.

## Verification and storage

- Package regression: 58/58 PASS.
- MetaEditor: 0 errors / 0 warnings.
- Exact-source non-repaint: PASS, zero findings.
- Static audit manifest SHA256:
  `B9D3C88AABE084A8FE1134FFCC18D40F3CFCEF61876C5BAF6CFB030D2B3E600C`.
- Static audit SHA256:
  `60171A0EA3CE0F4BD1A6B6C2F5A74776A349C0ABCBE95F1A4C42C00FDA5C3658`.
- Portable install/data/tester roots: `D:`.
- `FILE_COMMON`: disabled.
- MT5 terminal after the run: stopped.

All four protected C-drive roots were identical before and after by path,
existence, file count, bytes, latest file time and metadata SHA256. The before
and after snapshot files differ only in their generation timestamp.

## Strategy interpretation

This closes engineering and data-lineage defects; it does not improve the
killed detector's expectancy. The implemented setup remains a weak proxy for
the report because explicit MSS/BOS close, true breaker taxonomy, FVG freshness,
M15 structure and micro-confirmation are not executable hard gates. Adding
those now and reading PnL would be post-hoc rescue.

The next legal Unicorn gate is independent outcome-blind human review of the
V1.3 rows, preferably by two reviewers, followed by a separately frozen label
agreement and outcome-analysis plan. No win-rate, PF, cadence, Monte Carlo,
promotion or live claim is authorized from this collection.

The V1.3 label extractor now rejects V1.2, missing-breaker and source-hash
mismatch inputs before opening MT5. Actual-corpus preflight passed for 200 rows.
Frozen review rubric SHA256:
`BAAC8C2A4DD8BB8638C945D568DBD98BE6F4F1029023B61676DD380B937E87B1`;
extractor SHA256:
`546D0E14BA7A8F844299DEA132818F545A3E810C7F2129DABA805FEA31243590`.
