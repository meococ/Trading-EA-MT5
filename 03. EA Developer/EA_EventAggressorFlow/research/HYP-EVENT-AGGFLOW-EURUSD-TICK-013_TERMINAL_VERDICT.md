# HYP013 TERMINAL DESIGN VERDICT

`KILL_FROZEN_MAPPING` on 2026-08-12. The exact same-direction CME 6E first-15s
aggressive-flow mapping is economically attractive but did not pass every
preregistered DESIGN gate, so 2021-2022 validation remains sealed.

## Engineering verdict

- MetaEditor: 0 errors, 0 warnings; fresh EX5.
- Static non-repaint/no-lookahead audit: PASS.
- PRIMARY and exact REVERSE each accounted for all 329 events: 325 closed,
  three zero/tie/no-source skips, one market-closed entry reject, no missed
  tick, no overlap, no exit reject, max concurrent one, runtime failure false.
- Every completed entry and exit respected the exact millisecond boundaries.
- Both runs used source SHA256
  `65AA6558629F6FF224E5DB6FD218B1DC9A4EC6A7B07DE886C3FE13E5922A106C`
  and table payload SHA256
  `620FEB6A51CFB69B9BFA9C47E2BC4C208B6C6E3D9645A1C61CE062AC1B09D8BA`.

AlphaFactory completed both MT5 tests, but sidecar collection did not finish
cleanly because `alpha.local.ps1` points `MT5CommonFilesRoot` to the portable
root while `FILE_COMMON` wrote to the actual global MetaQuotes Common folder.
The PRIMARY outer runner was additionally terminated by a 10-second shell
timeout after MT5 launch. Both native reports, journal identities and exact
sidecars were recovered without rerunning either role. These collector defects
are engineering evidence and do not alter the economic verdict.

## Economic verdict

Independent ledger recomputation:

| Role / arm | N | Net USD | PF | Expectancy | DD |
|---|---:|---:|---:|---:|---:|
| PRIMARY base | 325 | 5,112.50 | 1.7257 | 15.73 | 0.96% |
| PRIMARY 1.5x cost | 325 | 3,885.75 | 1.5126 | 11.96 | 1.05% |
| PRIMARY 2x cost | 325 | 2,659.00 | 1.3265 | 8.18 | 1.23% |
| REVERSE base | 325 | -10,019.50 | 0.3471 | -30.83 | 10.02% |

PRIMARY base net was USD 3,852.50 in 2019 and USD 1,260.00 in 2020. The
predeclared diagnostic exclusion of provider-degraded EVT0198 and EVT0270
remained strong (N323, base PF1.7108, 2x PF1.3155) but cannot rescue any gate.

The only failed gate was concentration: the top 17 events (ceil of 5% of 325)
contributed **32.4011%** of total positive base profit, above the frozen 30%
ceiling. Therefore `passed_all_gates=false`, validation is not opened, and no
threshold/filter/event subset/session/timing/SL/TP/sizing change or rerun is
authorized. This is a disciplined near-survivor, not a validated edge.

Authoritative analysis:
`HYP-EVENT-AGGFLOW-EURUSD-TICK-013_ECONOMIC_ANALYSIS.json`.

