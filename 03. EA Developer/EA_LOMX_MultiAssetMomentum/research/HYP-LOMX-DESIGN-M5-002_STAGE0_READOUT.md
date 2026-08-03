# HYP-LOMX-DESIGN-M5-002 Stage-0 Readout

Verdict: `PARK_FULL_DUAL_ENGINE_CADENCE_OVERFLOW_ATOMIC_CELLS_SURVIVE_NO_OUTCOME`

## Trading authority

- MT5 launches: `0`
- trades simulated/executed: `0`
- performance outcomes read: `0`
- PnL/PF/MFE/MAE/validation/holdout: not computed and not authorized
- Model 0, optimization, promotion, paper and live: not authorized

This is an outcome-blind density and initial-geometry result only.

## Frozen P0 result

Window: EURUSD and XAUUSD native FivePercent M5, 2016-01-04 through
2024-12-31. All four atomic cells pass their preregistered density, direction,
year-concentration and positive-risk gates:

| Symbol | Atomic engine | Candidates | Candidates/week | Long/short | Max year share | Result |
|---|---|---:|---:|---:|---:|---|
| EURUSD | Asian-range sweep reclaim | 1,949 | 4.1531 | 952 / 997 | 12.67% | PASS |
| EURUSD | Bar-range compression breakout | 2,117 | 4.5111 | 1,052 / 1,065 | 13.79% | PASS |
| XAUUSD | Asian-range sweep reclaim | 2,085 | 4.4429 | 1,019 / 1,066 | 12.81% | PASS |
| XAUUSD | Bar-range compression breakout | 2,072 | 4.4152 | 1,117 / 955 | 13.03% | PASS |

The exact simultaneous dual-engine plan fails its own combined cadence gate:

| Symbol | Deconflicted candidates | Candidates/week | Asian coverage | Opposing same-bar collisions | Result |
|---|---:|---:|---:|---:|---|
| EURUSD | 4,022 | 8.5705 | 99.44% | 6 | FAIL |
| XAUUSD | 4,095 | 8.7260 | 99.66% | 12 | FAIL |

Both symbols exceed the frozen `2-5/week` combined band. Combining the engines
at this stage would create over-cadence and ambiguous conflict handling, so the
full dual-engine object is parked before any economic outcome.

## Failure radius and successor permission

Closed: the exact two-engine simultaneous stream with sweep priority and the
frozen thresholds/session/window. Do not reduce cadence by mining hours,
weekdays, years, direction or thresholds from this readout.

Not closed: each atomic symbol-engine cell. The frozen plan explicitly allowed
passing atomic cells to receive fresh symbol-specific identities. They must be
tested separately, one at a time, with their own source/prereg/task packet/cost
contract and no pooled PF/cadence claim. The generic compression arm remains
`BAR_RANGE_COMPRESSION_BREAKOUT`; it is not the T2 Volman grammar.

## Bound evidence

- Plan SHA256: `FB44311871144290B231DA3AFC083C89B4D950768D7FA1D5F4E61C695B8CD09E`
- Scanner SHA256: `A4A1EF5E2F289ABC94231953345B70070701C347D622A7DA4EB5A35E816B7D39`
- Synthetic tests: `5 passed`
- Result:
  `research/evidence/HYP-LOMX-DESIGN-M5-002/P0_DESIGN_001/stage0_result.json`
- Result SHA256: `8193E68D4EC240B696CDB91884C95976F3B47ECFFF740D5416BE2BEB4D2EF1DB`
- Candidate CSV SHA256:
  `4E836506FCB250B023DEE1B1DB1A2C0D141D7740DF893124941E971F7F438E0F`
