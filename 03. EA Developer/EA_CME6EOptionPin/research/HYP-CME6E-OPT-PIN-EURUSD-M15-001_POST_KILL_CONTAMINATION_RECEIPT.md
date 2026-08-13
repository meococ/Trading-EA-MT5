# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - post-kill contamination receipt

Status: `TERMINAL_NO_USE`

## Authority

- The authoritative terminal decision is
  `HYP-CME6E-OPT-PIN-EURUSD-M15-001_SOURCE_CONTRACT_KILL.md`, created at
  `2026-08-12T14:40:46.5935715Z`, SHA-256
  `0134aba109d3b17b9c89605c4463f1342c6961853bcac0d60e4e3b697b3f3f44`.
- Its verdict is `KILL_SOURCE_CONTRACT_INVALID`. HYP001 therefore ended before
  statistics, futures direction, broker target, economics, EA implementation,
  or promotion.

## Contaminated artifacts

The following material was created or completed after that terminal decision
and is retained only as forensic evidence. It must not be used for a target
readout, economic claim, child-hypothesis direction, EA logic, or promotion:

- HYP001 phase-02 normalized option-statistics payloads, manifests, analysis,
  and receipts;
- `HYP-CME6E-OPT-PIN-EURUSD-M15-001_FUTURES_REFERENCE_ADDENDUM.md` and the
  associated futures quote, authority, raw payloads, directions, analysis, and
  receipts;
- `HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_ECONOMIC_PREREG.md`;
- `capture_cme6e_option_pin_design_eurusd_ticks.py` and its unit test.

The retired capture script now fails closed on direct invocation. No EURUSD
target tick, return, PnL, Strategy Tester report, EA, or indicator was opened or
created from HYP001.

## Permitted inheritance

HYP002 may reuse only the 60 immutable parent definition payloads explicitly
named and hash-bound by
`HYP-CME6E-OPT-PIN-EURUSD-M15-002_SOURCE_PREREG.md`. HYP001 statistics,
futures, target, and economic artifacts carry no authority into HYP002.

This receipt does not assert an edge. It restores the outcome-blind boundary
and prevents a terminal source-contract failure from being laundered into a
later result.
