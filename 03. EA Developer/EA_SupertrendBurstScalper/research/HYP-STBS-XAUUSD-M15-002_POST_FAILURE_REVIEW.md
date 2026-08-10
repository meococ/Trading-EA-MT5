# HYP-STBS-XAUUSD-M15-002 — Independent post-failure review

- Status: `PASS_KILL_HYP2`
- Exact verdict: `KILL_PRE_ALPHA_GIT_STATUS_PATHSET_DRIFT_NO_COMPILE_NO_MT5`
- Scope: immutable HYP002 authority, packet, MT5-claim and Alpha preflight evidence only. No source data or outcomes were opened.

The screened authority raw SHA `513BAFDF946FFB2EFA9651EE7F7D7D35DEA36EF642B175B07299371E787C30F0` legitimately consumed the sole `STBS002-MT5-AUDIT-001`. The attempt start `CF3A13807364159E2A1B136ED86E4043A25C6540CAD342402D042EB475D3B7DB` and failed terminal `8A5860E3F97FE6D35B7BAFDE577010C9C32DDC7EB9BD5ECBB7A7C636E9426C67` prove the attempt is not retryable. Alpha stdout `06BB013D1A8543DCBB096E78372239700247B5F551B37A007F75BEDF8BD568AA` contains only the launcher banner; stderr `299B2530FCC0BC5DD8D23194C5120FE8F5B8191A22D40F801E6D6375E3C60E92` proves the failure occurred at the live Git identity gate.

The sealed path set contained 311 entries with SHA `2BB28EB2243D021F6DC05B3CBE54DB6E4D05C1ACC989806F68BFE71457E93060`. At the failed launch it contained 312 entries with SHA `E598B0EDC8290B55640118282B44EC19A9333E2831F40DC60D6C2E0B14DFA7B3`; the sole added path was the required HYP002 post-packet review. The later HYP002 failure documents were created after that observation and are not represented as causes.

No Alpha run directory, run compile, MT5 process, source-data access, order, outcome, performance trial or economic evaluation exists. The failure radius is only pre-Alpha path-set provenance. HYP002 must be terminally killed with packet attempts consumed `1`, MT5 attempts consumed `1`, run-compile attempts consumed `0`, every performance/execution count zero and every authority false.

A legal fresh HYP003 governance revision must use fresh packet/MT5 IDs and bind the exact terminal HYP002 raw row plus failure artifacts. Its exact post-packet review path must exist as a non-authoritative reserved placeholder before packet sealing; the sealed status list must contain that path exactly once, while immutable receipt evidence must exclude the placeholder bytes. After packet completion only those bytes may change. The screened row must bind the final review hash, and the runner must validate the final non-placeholder PASS review after its durable MT5 claim. Any added, deleted or renamed path still fails closed.
