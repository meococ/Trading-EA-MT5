# HYP-ST-XAUUSD-H1-005 — terminal MT5 launcher failure

Verdict: `KILL_ENGINEERING_INVOCATION_ADAPTER_SPREAD_TOKEN_NO_MT5`

The sole outer attempt `ST005-MT5-001` was durably claimed, invoked
AlphaFactory, and failed in AlphaFactory scalar validation before compilation,
terminal launch, history access, or Strategy Tester execution. The launcher
passed the literal token `current` to `-Spread`; the frozen AlphaFactory CLI
requires an empty argument for a current-spread request and normalizes that
request to `current` only inside the run receipt and manifest.

Evidence SHA-256:

- `attempt_started.json`: `4627A3C97DAE5BE760DD3B72727FC728F39B0D2A2D76111290F093D1294A4B16`
- `alpha_stdout.log`: `FD8BCF14AB4701ABAC12BDBC16CA1781CFE4F2B5C82299CF54826D6E3195A319`
- `alpha_stderr.log`: `E1B3DBE80A54FF2276036188F8E23A86F92D2CC0FB6946528876111472D443B2`
- `attempt_terminal.json`: `383F0BD0B9BC947E5548220A06C1247A2880DCC61AAA52DA0279BA6F2CDDED78`

No `ALPHA_RUN_DIR` was emitted, no HYP005 AlphaFactory run directory exists,
and `ST003_MQL5_PARITY_001.csv` remained absent from `FILE_COMMON`. Therefore:

- MT5 launches / Model-4 runs / collection attempts / comparator attempts: `0`;
- orders, deals, outcomes, returns, PF, costs, optimization and validation: `0`;
- same-ID retry: forbidden.

The exact failure radius is only the HYP005 outer launcher mapping of semantic
spread `current` to the AlphaFactory CLI token. It does not invalidate the
HYP004 static compile, HYP003 oracle, Supertrend formula, or MT5 parity thesis.
A fresh child may change only the outer identity and pass `-Spread ''`, while
keeping the receipt/manifest semantic spread value frozen as `current`.

