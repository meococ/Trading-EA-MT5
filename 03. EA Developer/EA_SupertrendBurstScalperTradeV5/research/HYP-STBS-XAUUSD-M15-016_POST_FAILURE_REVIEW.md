# HYP-STBS-XAUUSD-M15-016 — independent post-failure review

## Verdict

`PASS_KILL_ENGINEERING_CONTRACT_RECEIPT_OVERRIDE_NORMALIZATION`

The reviewer independently reconciled the attempt start, terminal, stdout and stderr. AlphaFactory's telemetry-profile `none` path parses the CLI override map and serializes it in sorted-key order, while the HYP016 receipt stored the original non-canonical CLI order. The resulting exact receipt mismatch occurred before compile or MT5.

The run-directory delta is `0 -> 0`. Static and post-attempt EX5/log captures are byte-identical. There is no report, data access, order, deal, outcome, PF or economics.

The reviewer ratifies killing only the HYP016 outer receipt mapping. The narrowest lawful continuation is a fresh outer HYP017 that:

- preserves the exact V5 source, EX5, inner HYP016 identity and magic `5604116`;
- uses a fresh preregistration, task/receipt paths and `STBS017-MODEL0-AUDIT-001` attempt;
- distinguishes the human CLI declaration from AlphaFactory's effective canonical override string;
- binds the exact sorted effective string used by receipt and run manifest;
- adds a regression test mirroring AlphaFactory normalization and rejecting order/value drift;
- preserves zero-order, no-outcome and no-economic authority.

HYP016 must be terminalized with audit consumed `1/1`, run compile `0/1`, all execution/economic counters zero, and same-ID retry forbidden before HYP017 authority is opened.
