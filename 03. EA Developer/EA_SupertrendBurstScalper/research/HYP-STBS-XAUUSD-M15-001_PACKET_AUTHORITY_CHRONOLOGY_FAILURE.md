# HYP-STBS-XAUUSD-M15-001 — Packet authority chronology failure

- Actual detection time: `2026-08-09T02:35:31Z`
- Verdict: `KILL_PACKET_AUTHORITY_TIMESTAMP_AFTER_ATTEMPT_NO_MT5`

The packet evidence chain is byte-consistent, but it is not legally usable. Registry row 811 declares its probe authority at `2026-08-09T04:46:00Z`; the sole packet attempt started at `02:31:55Z`, sealed its receipt at `02:31:57Z`, and completed at `02:31:58Z`. The packet also froze availability-as-of `03:30:00Z`. Both authority and availability therefore postdate the attempt under the actual system clock.

`STBS001-PACKET-BUILD-001` is consumed and must never be retried. No AlphaFactory backtest, MT5 launch, run-scoped compile, order, deal, outcome, return, PF or economic metric occurred. The exact failure radius is temporal authority provenance; the causal MQL5 source, static compile, non-repaint audit, parent signal parity and market thesis remain untested by this failure.

The next legal action is a fresh hypothesis and fresh attempt identities, with all temporal fields captured directly from system UTC before any claim. HYP001 must not receive a screened MT5 authority row.
