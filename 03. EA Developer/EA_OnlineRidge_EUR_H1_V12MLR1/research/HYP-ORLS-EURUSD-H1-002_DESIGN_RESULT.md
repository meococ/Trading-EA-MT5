# DESIGN result - HYP-ORLS-EURUSD-H1-002

Verdict: `KILL_DESIGN_NEGATIVE_EDGE_OVERTRADING_NO_VALIDATION`.

AlphaFactory run `20260812_032000`, EURUSD H1 Model 0, current broker spread, HQ100, full DESIGN `[2018-01-01, 2022-01-01)`. Fresh compile passed with `0 errors, 0 warnings`; ten static/causality tests passed; `runtime_failed=false`; all 24,857 generated H1 decision bars produced valid feature observations; zero feature/missing/nonfinite skips; no covariance reset.

The delayed learner reconciled 23,883 exact four-contiguous-H1-open RLS updates and 858 intentional label gaps across weekend/non-contiguous intervals. After 120 warm-up observations it made 24,737 predictions. It produced 3,185 long and 3,149 short threshold crossings, 17,844 hurdle rejects, 1,656 schedule rejects, 559 spread rejects, 2,881 exposure skips, 93 entry rejects, and 1,704 accepted entries. Maximum observed entry margin use was only `1.2373%`.

Economics fail clearly: 1,704 trades, PF `0.924678`, net `-$7,041.14`, WR `48.5%`, expectancy `-$4.13/trade`, max DD `9.6378%`. Cadence is about `8.17 trades/week`, far above the frozen validation design range equivalent. The learner is negative before the report-level cost gap: unique journal exits sum to `-$2,625.34` price PnL; final report is another `-$4,415.80` lower, about `-$2.59/trade`.

Exit forensics: 1,035 exact four-bar exits produced `+$30,632.12`; 492 other expert closes produced `+$9,472.73`; 177 catastrophe SLs produced `-$42,730.19`. Catastrophe-stop rate is `10.39%`, within its safety gate, but their loss mass exceeds the combined positive fixed/expert exits. This is not a cost-only failure: the raw price path is already negative.

The equity chart peaks briefly in mid-2018, falls below starting equity by late 2018, and then follows a persistent lower-high/lower-low path through 2019-2021. Recoveries in early 2020 and early 2021 never approach the prior peak; the run ends near its maximum drawdown. There is no stable DESIGN edge worth exposing the untouched 2022-2023 validation set.

Kill this exact six-feature EURUSD H1 EW-standardized online RLS with four-open target, symmetric cost hurdle, catastrophe stop and fixed horizon. Do not rescue it by excluding New York/Friday/hours, changing score/cost/forgetting thresholds, editing features, changing the catastrophe stop/hold, or transferring symbol/timeframe from this outcome.

Evidence hashes: source `E91F6A90388050099C603780F99C1EA8F8227216FEA22C2F047BC20320829A56`; EX5 `02470E81790A088F7869327D611DE40226B4ACD0B25A919043E3F7B7D62BAB04`; report `61076595D017BAE814A7DD0711D3AA541C191C0F9AF28373ADE47651E4FD6EF9`; journal `1AC089510C8BE20A34286B5BD31863C5EBB6209F730C1BD8F323C2BAA2720874`; chart `9930090564F89C7912565289BEF3EFCCE8E39A9882D21638D45D2CC9181D708A`.
