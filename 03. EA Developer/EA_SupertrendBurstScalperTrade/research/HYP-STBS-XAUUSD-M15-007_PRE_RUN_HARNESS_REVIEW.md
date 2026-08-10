# Independent pre-run review — HYP-STBS-XAUUSD-M15-007

Verdict: `FAIL_PRE_RUN_HARNESS`.

The reviewer confirmed that the intended AlphaFactory CLI contract was otherwise exact (`XAUUSD/M15`, 2005–2023 preload, Model 0, current spread, execution/fixed delay zero, control, telemetry none/off, empty overrides, no optimization), but found four fatal evidence-chain defects before any packet or MT5 execution:

1. packet build was neither claim-first nor one-shot;
2. the runner opened the AlphaFactory executable before its durable claim;
3. builder and runner bytes were not bound;
4. the authority surface omitted full attempt/retry/mutation and run-scoped compile gates.

The recommended closure is governance-only: terminalize HYP007 with zero attempts/outcomes, then use a fresh outer ID with a packet-only probe and a separately reviewed screened run authority. The frozen HYP007 MQL remains the inner implementation.
