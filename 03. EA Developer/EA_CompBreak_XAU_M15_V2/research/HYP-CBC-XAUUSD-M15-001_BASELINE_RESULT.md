# Baseline result — HYP-CBC-XAUUSD-M15-001

Verdict: `KILL_SPARSE_AND_CONCENTRATED_NO_OOS_NO_CONTROL`.

Authority: AlphaFactory run `EA_CompBreak_XAU_M15_V2/20260812_010304`, XAUUSD M15 Model 0, requested `[2018-01-01,2022-01-01)`, History Quality 99%, `FULL_2018_PLUS`, tester passed the complete window.

## Engineering and risk

- Compile proof: fresh EX5, `0 errors, 0 warnings`; static contract `15/15`; non-repaint audit `PASS`.
- Runtime: 93,887 decision bars; 39 compression boxes; 33 confirmed breaks; 28 entries; 28 exits; no entry rejects, close rejects, runtime failure or margin stop-out.
- Three-way sizing cap worked: maximum logged entry margin usage `11.9840%`, below the frozen `12%` cap.
- State/exit telemetry: 13 SL, 11 time-stop, 4 daily-flat; 12 BE moves, 6 trail arms and 11 trail moves.

## Economic readout

- Trades `28`; net `+$2,725.08`; PF `1.7463`; win rate `57.14%`; expectancy `+$97.32/trade`; maximum DD `0.7334%`.
- Year exit-net telemetry: 2018 `+$987.57` (5), 2019 `-$23.29` (9), 2020 `+$1,510.35` (7), 2021 `+$310.64` (7).
- The two largest exits were `+$1,474.17` and `+$1,300.19`; together they exceed 100% of report net after all trade costs. Equity therefore advances through rare jumps rather than a sufficiently sampled trading process.
- Cadence is only seven trades/year. Even a linear projection to 2018-latest is far below the frozen minimum 180 trades and cannot support a scalping/pro-trader replacement claim.

## Decision

The positive PF is acknowledged but is not promoted. The primary fails the preregistered cadence and concentration gate, so the matched control, OOS, holdout, cross-symbol transfer, validation and optimization remain forbidden. No session/hour subgroup may be selected from this readout.

Exact failure radius: the conjunction of a seven-bar box with every bar body `<=0.55`, total range `<=1.15 ATR`, buffered break and nine-bar frozen expiry produced only 39 boxes in four years. This exact signature is terminal. A new hypothesis must create materially more native M5/M15 decisions without loosening these observed thresholds post hoc.

Evidence: report SHA `4882015F986711F397FB24D03ADA72D4E05D09CC7849CC6B700217888BACACC4`; journal SHA `7DAD53F5FCF4713C2D5AE195D99B5C242087086AAA8D469C09DFFFA4942734FD`; source SHA `02E437B7BD015CEC4C2308BFC3E7C45646712B118E84461DADE4C9574FCE2656`; EX5 SHA `9C1988BF60293949A2BC155675C2295D722A70E35B32F5F3A68BC051E978E20C`.
