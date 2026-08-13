# Prospective XAU/Forex DOM collection preregistration - revision 1.1

Date frozen: 2026-08-13

Status: `FROZEN_AFTER_V1_0_RUNTIME_IO_FAILURE_BEFORE_V1_1_BUILD`

## Why this is a new revision

The v1.0 smoke established that the current broker exposes nonempty DOM for all
four frozen symbols, but it failed the engineering gate. The stopped session
reported 4,183 snapshots, 33 duplicate payloads, zero empty books, zero book API
errors and five I/O errors. Its JSONL lacked the required `INIT`/`SUBSCRIBE`
receipts and the CSV contained snapshot keys absent from the JSONL. Those facts
freeze v1.0 as failed; its output must not be repaired or promoted.

## Unchanged source boundary

- Platform/server: MT5/MQL5 on the current `FivePercentOnline-Real` terminal.
- Symbols: exactly `XAUUSD`, `EURUSD`, `GBPUSD`, `USDJPY`.
- Source APIs: `MarketBookAdd`, `OnBookEvent`, `MarketBookGet` only.
- No chart/tick/bar/indicator/Calendar/WebRequest/trade/order/position/outcome
  access. Tester and optimization modes fail initialization.
- This is source collection only. It cannot open an imbalance sign, prediction,
  EA entry rule, economic verdict, paper trade or live trade.

## Frozen v1.1 engineering changes

- New immutable filenames: `dom_tape_v1_1.jsonl`, `dom_levels_v1_1.csv`,
  `dom_state_v1_1.txt`; v1.0 artifacts remain untouched.
- One persistent exclusive writer owns JSONL and CSV for the session. Read
  sharing is allowed; write sharing is forbidden. A second collector fails
  before subscriptions.
- Every receipt includes a session ID and the existing safety fields. Startup
  must produce one writer receipt, four ordered subscription receipts and one
  initialization receipt.
- Output is flushed after every record. A partial JSON/CSV pair caused by a
  crash remains detectable and is a gate failure; no transactional claim is
  made.
- Per-snapshot state replacement is forbidden. The collector must atomically
  reserve high-water ID blocks before using global snapshot IDs and per-symbol
  event IDs. Restart may create gaps but may never reuse or move IDs backward.
- `GetTickCount64` monotonicity is session-local. Its value is not restored or
  compared across a terminal restart.
- Fatal JSON, CSV or state I/O is counted once, handled without recursive error
  logging, and removes the collector after releasing resources.
- A checked 30-second timer emits heartbeat and persists counters without
  lowering reserved floors. Deinitialization emits shutdown before closing
  output handles and releases every successful subscription.

## Revision 1.1 smoke gate

After static tests and a fresh AlphaFactory compile with zero errors and zero
warnings, run one clean bounded live smoke. Pass only when an independent
auditor proves:

1. exclusive writer, four subscriptions and initialization receipts exist;
2. all four symbols have at least one nonempty full-book snapshot;
3. session clocks and event/snapshot IDs are monotonic;
4. every JSON snapshot has exactly its declared CSV level rows and no CSV-only
   snapshot key exists;
5. state schema, reserved floors and symbol rows are readable and consistent;
6. at least one heartbeat reports all four subscriptions active;
7. no empty-book, book-API, tick-regression or I/O failure occurred; and
8. source and runtime receipts retain the zero-trade/outcome-blind flags.

Passing this gate means `SOURCE_CAPABILITY_PASS` only. It is not an EA backtest,
not economic validity and not promotion readiness.
