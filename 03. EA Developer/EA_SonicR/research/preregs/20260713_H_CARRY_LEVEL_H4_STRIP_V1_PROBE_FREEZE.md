# Probe Design Freeze — Carry Level H4 Strip V1

Status: `FROZEN_PRE_RESULT / INDEPENDENT`  
Date: 2026-07-13  
Owner override: local self-research; no ChatGPT.

## Independence (de-dup)

| Family | Relation |
|---|---|
| Killed weekly D1 cross-sectional rank | Different: time-series **level sign**, daily H4 strip, not Friday single-winner rank |
| Killed/near-miss Δcarry event H4 V1b | Different: trigger is **scheduled daily strip** on carry *level sign*, not |Δcarry|≥5bps events |
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | Different: no common-USD impulse / pullback-break architecture |
| Spot momentum | Negative control uses prior-day return sign on same schedule |

Causal claim: lagged money-market interest differential level is a slow state;
a short H4 strip after each day’s rate availability tests whether that state
has short-horizon directional content beyond lagged spot returns (forward-
premium / carry channel at session scale).

## Frozen constants

| Constant | Value |
|---|---|
| Symbols | EURUSD, GBPUSD, USDJPY |
| Entry | First closed H4 bar of each UTC day (after rates asof that day exist) |
| Direction | sign(lagged carry level); skip if 0 |
| HOLD_BARS | 2 |
| Weekend flat | Friday H4 hour >= 16 UTC |
| Cost A/B | 1.5 / 3.0 pip RT |
| Train / holdout | 2018–2022 / 2023–2025 |
| Rate lags | USD +1d, EUR +1d, GBP +1d, JPY +2d (same series as V8 panel) |
| Control | same schedule; direction = sign(prior UTC day close-to-close return) |
| One position / symbol | yes |

## Train gates

1. 150 <= trades
2. 2.0 <= trades/elapsed_week <= 6.0
3. PF stress-A >= 1.10
4. PF stress-A > control
5. expectancy stress-A > 0

Holdout if train passes: trades >= 60, 1.5 <= tpw <= 7.0, PF_a >= 1.00, beats control.
