# HYP-STBS-XAUUSD-M15-002 — Pre-compile Git-status failure

Verdict: `KILL_PRE_COMPILE_GIT_STATUS_DRIFT_NO_MT5`.

The sole `STBS002-MT5-AUDIT-001` attempt was durably claimed at `2026-08-09T04:58:14.842382Z` under screened raw registry row `513BAFDF946FFB2EFA9651EE7F7D7D35DEA36EF642B175B07299371E787C30F0`. AlphaFactory returned code 1 at its receipt identity gate at `04:58:17Z`, before compile, tester launch, source-data opening, orders, outcomes or economics.

Exact evidence:

- attempt start: `CF3A13807364159E2A1B136ED86E4043A25C6540CAD342402D042EB475D3B7DB`;
- failed terminal: `8A5860E3F97FE6D35B7BAFDE577010C9C32DDC7EB9BD5ECBB7A7C636E9426C67`;
- Alpha stdout: `06BB013D1A8543DCBB096E78372239700247B5F551B37A007F75BEDF8BD568AA`;
- Alpha stderr: `299B2530FCC0BC5DD8D23194C5120FE8F5B8191A22D40F801E6D6375E3C60E92`;
- packet receipt: `23145DA32179E68EE5601E4D99380D6B76626F77C899787EAE94ECAF7E6F6294`.

The receipt sealed 311 Git-status paths with SHA `2BB28EB2243D021F6DC05B3CBE54DB6E4D05C1ACC989806F68BFE71457E93060`. At launch the live list contained 312 paths with SHA `E598B0EDC8290B55640118282B44EC19A9333E2831F40DC60D6C2E0B14DFA7B3`. The exact set difference was only:

`03. EA Developer/EA_SupertrendBurstScalper/research/HYP-STBS-XAUUSD-M15-002_POST_PACKET_REVIEW.md`

The HYP002 packet receipt had been sealed before that required new independent-review artifact was created. Registry content changes did not alter the path-level status list because the registry path was already modified; the new review path did.

Failure radius is only the HYP002 post-packet-review path reservation and Git-status chronology. The causal signal/ATR/geometry mapping, compile result, MT5 runtime, source-data coverage, trade behavior and economic edge were not tested. Same-ID retry is forbidden.

A fresh governance revision must reserve its dedicated post-packet review path before packet sealing, declare that mutable-in-phase path in preregistration, preserve its status-list presence, and bind the final reviewed bytes only in the later screened authority row. It must use fresh packet and MT5 attempt IDs.
