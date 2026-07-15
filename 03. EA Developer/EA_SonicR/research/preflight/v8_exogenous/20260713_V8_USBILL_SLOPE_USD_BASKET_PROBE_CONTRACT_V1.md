# V8 US Bill-Slope → USD Basket Probe Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner GOAL + skip-GPT self-research (2026-07-13 23:40). Uses on-disk
Treasury bill archives only. Authorizes one cheap offline probe. No registry,
prereg, EA, compile, or Model 0.

## De-dup intake (pre-result)

| Closed family | Why this is independent |
|---|---|
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | That idea uses **contemporaneous FX return** median factor + strongest-pair pullback-break. This probe uses **lagged US Treasury bill slope** only; no FX-return factor, no pullback-break, no strongest-pair routing. |
| V8 carry weekly/daily/event | Those use G3 short-rate differentials / rank. This uses US bill curve shape alone. |
| COT TFF / Carry×Vol | Different causal surfaces (positioning / vol-gated carry). |

If intake fails later, kill as duplicate — do not run.

## Probe identity

- Working ID: `HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001` (mint only if registered)
- Probe tag: `V8_USBILL_SLOPE_USD_BASKET_V1`

## Data

- `preflight/v8_exogenous/raw/us_treasury_bill_rates_{2018..2026}.csv`
- Prefer 26-week minus 4-week bill rates (fallback: 13W − 4W if columns differ).
- `available_at_utc = observation_date + 1 calendar day 00:00Z`
- Fail closed on missing observation (no silent fill > 3 calendar days).

## Signal (frozen)

1. `slope_t = bill_long_t - bill_short_t` (percentage points).
2. `z_t = (slope_t - mean(slope_{t-60..t-1})) / stdev(...)` (need ≥40 prior obs).
3. If `z_t >= +0.75` → USD strength regime (`D=+1`); if `z_t <= -0.75` → USD weakness (`D=-1`); else flat.
4. On each completed D1 Mon–Thu with non-zero D, hold equal-weight basket:
   - `D=+1`: short EURUSD, short GBPUSD, long USDJPY
   - `D=-1`: long EURUSD, long GBPUSD, short USDJPY
5. Friday flatten. Stop per-leg 1.5×ATR14_D1; time-stop 5 D1 bars.

## Control

Same calendar + |z| threshold machinery, but `D = sign(mean 20d USD proxy)` where
USD proxy = `(-ret_EURUSD - ret_GBPUSD + ret_USDJPY) / 3` from spot (bills unused).

## Cost / splits / kills

- Stress A 1.5 / B 3.0 pip RT per leg (aggregated at basket trade level as mean of legs).
- Train `[2019-01-01, 2023-01-01)`; holdout `[2023-01-01, 2026-01-01)` gated.
- Kill if train trades < 80, tpw < 0.5, PF-A < 1.05, fail beat control PF-A and
  expectancy-A, or year concentration of positive net-A > 0.55.

## Non-rescues

No post-hoc z-threshold, bill tenor, or session mining from the readout.
