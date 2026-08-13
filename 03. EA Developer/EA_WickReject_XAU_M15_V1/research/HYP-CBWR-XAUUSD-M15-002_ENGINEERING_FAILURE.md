# HYP-CBWR-XAUUSD-M15-002 — strict-input initialization failure

- The canonical D0 proof was implemented and compiled, but the MT5 tester stopped immediately with `OnInit reports incorrect input parameters`.
- Run folder: `20260812_003935`. The journal confirms zero closed bars, zero signals and zero trades. No economic outcome exists.
- The generated config explicitly carried only hypothesis, swing flag, auto mode and variant; all other frozen fields depended on EX5/tester defaults while the EA intentionally validates the full surface.
- HYP002 is closed as `INVALID_ENGINEERING_PARTIAL_OVERRIDE_SURFACE`.
- Successor HYP003 keeps the same trading source logic and D0 proof, changes identity/magic/log prefix, and binds every frozen research input explicitly in its task packet, receipt and CLI invocation.
