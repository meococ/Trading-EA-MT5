# HYP-VRAS-EURUSD-M5-007 — Invalid Full-Horizon Diagnostic

Verdict: **INVALID — broker/tester stop-out at 44% of the requested interval.**

The account-DD entry halt bypass worked as designed: RunMeta reports `account_dd_entry_halt_enabled=false`, the 6% threshold was crossed, and `account_halt=false`. MT5 nevertheless invoked its account-level position stop-out on 2020-10-12 after 132,413 bars / 26,884,260 ticks, versus 298,483 bars in the requested full window.

The partial control produced 2,148 report trades, PF 0.7866, net USD -10,014.12 and max DD 10.45%, but these are not full-horizon economics. The forced final deal was not delivered to lifecycle telemetry before deinitialization: 2,148 OPEN versus 2,147 final CLOSE and a USD -6.88 reconciliation gap. The challenger was correctly not executed.

HYP007 cannot be rerun or rescued. A separate engineering successor may change only tester-survival scaling while preserving the same initial cash risk budget, signal, stop, target and management rules. It remains diagnostic-only and cannot revive HYP006.
