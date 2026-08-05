# HYP-AIRQMB Multi-9 M5 SCREEN-002 — Frozen Preregistration

Frozen on 2026-08-05 UTC before any SCREEN-002 tester launch and before any performance outcome from the aborted BASE-001 smoke was available.

## Purpose and authority

SCREEN-002 is a computationally bounded screening lane for the new AIRD + MBB + QQE ensemble. Model 4 open-prices is authorized only to verify runtime contracts, measure approximate cadence, reject clearly negative cells and rank the already-preregistered small grid. It cannot establish `economic-valid`, cost resilience or promotion readiness.

The BASE-001 Model-0 launch produced no report and no outcome. Its only findings were engine runtime and nondeterministic EX5 bytes. All nine BASE-001 identities are superseded so the universe remains on one source and protocol.

## Ordered independent cells

`EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`, `NZDUSD`, `XAUUSD`, `BTCUSD`, all M5. IDs use `HYP-AIRQMB-<SYMBOL>-M5-SCREEN-002`; magics remain `5686101` through `5686109` in that order.

## Bound implementation

- Source SHA-256: `07D94050A8142353E6E0DD491334CED5631E3B0EF12011B8119AD92A28208B52`
- Contract SHA-256: `1FDC453718A1D306AB67D686AAD4B96B892A9B45400CF267136A4071211C81E5`
- Compile: `0 errors, 0 warnings`
- Static non-repaint: `PASS`
- Exact logic and indicator runtime hashes: `HYP-AIRQMB-MULTI9-M5-SCREEN-002_LOGIC_MATRIX.md`

## Population and split locks

| Stage | Dates | Model | Access |
|---|---|---:|---|
| Screening baseline and grid | `2023.01.02–2024.12.31` | 4 | open, ordered cells only |
| Model-0 confirmation | same training dates | 0 | locked until one parameter pair is frozen from Model 4 |
| Validation | `2025.01.01–2025.12.31` | 0 | locked until training Model 0 passes |
| Holdout | `2026.01.01–2026.07.31` | 0 | locked until validation passes unchanged |

History Quality must be strictly above `97%`. Missing or shortened history is data-invalid, never a pass or economic failure.

## Baseline screen

Exact identity overrides:

```text
InpExpectedSymbol=<SYMBOL>;InpHypothesisId=HYP-AIRQMB-<SYMBOL>-M5-SCREEN-002;InpMagic=<MAGIC>;InpResearchAutoMode=true;InpVariantTag=SCREEN002_MODEL4
```

All strategy inputs remain the compiled defaults. A symbol authorizes grid work only if:

1. compile, receipt, indicator load, non-repaint and lifecycle reconciliation pass;
2. at least 100 completed trades, both directions each at least 20%, and approximate cadence between `1.5` and `6.0` trades per elapsed week;
3. Model-4 PF `>=1.10`, expectancy positive and maximum equity drawdown `<=8%`.

Failure stops that symbol. Model-4 success only authorizes its nine-point training grid.

## Preregistered grid for screen survivors

- AIRD confidence `{0.35, 0.45, 0.55}`
- target `{1.25R, 1.50R, 1.75R}`
- stop fixed `1.00` MBB half-width
- all other EA and indicator inputs frozen
- exactly nine Model-4 trials per surviving symbol

Selection requires a positive-expectancy candidate with at least two positive adjacent neighbors. Rank by median neighbor-group expectancy, not isolated PF. A tie chooses higher confidence then lower R target. The selected pair is frozen before one Model-0 training confirmation.

No session, weekday, year, direction, signal-lane, indicator or stop-multiplier search is authorized. Model-0 failure kills the selected mechanism for that symbol; no same-family rescue grid follows.

