# HYP-STBS-XAUUSD-M15-024 — Independent post-failure review

## Verdict

`PASS_KILL_PRE_MT5_AND_OPEN_OUTER_HYP025`

The independent review confirms that HYP024 must be terminalized before any MT5 attempt. Screened authority row `20B7285DFF78E85019B73E626C5850D637FBABDC947F377CC383B9D14D02DC4D` already contains `one_shot_economic_harness_version` but omits `pre_execution_harness_addendum_path` and `pre_execution_harness_addendum_sha256`. The hash-bound runner requires those fields before launch.

The generic Model0 `screened -> screened` hardening transition applies only when the prior row lacks the one-shot harness version. The engineering-receipt correction transition permits only its exact correction path/SHA pair. Therefore an in-place edit, same-ID successor, post-authority runner patch or validator exception is not lawful.

The exact failure note is `HYP-STBS-XAUUSD-M15-024_PRE_MT5_AUTHORITY_FAILURE.md`, SHA-256 `D58707EF9ADCCEE78FEFBCAFBB35B06342D3DDB5A641421097EA77EBD674ADEA`. Packet build consumed one attempt, but the Model0 attempt root is absent and MT5/run-compile/model0/launch/order/trade/return/performance counters remain zero. No economic verdict exists.

The narrow continuation is a fresh outer-only HYP025 governance child over the unchanged V11/HYP024 inner implementation. HYP025 must use a packet-only probe followed by an ordinary packet-bound screened row. Its addendum path/SHA must be frozen before the probe and carried through packet and screened authority. Outer registry/task/receipt/attempt/manifest identity is HYP025; inner MQL override, RunMeta and lifecycle identity remains HYP024. Source `7CC7A9D7C30216A1669D84AEEA867E32EA15F2E9E8C195D171BD574A4D2EB0BC`, static EX5/log, non-repaint evidence, magic, parameters, data, cost and gates remain unchanged.

No V12 source clone or new standalone compile is justified. The eventual AlphaFactory backtest may perform its normal run-scoped compile only after HYP025 authority, and its source/EX5/log/manifest chain must be captured and reconciled.
