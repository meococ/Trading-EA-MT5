# V8 Equity–Bond Differential Join Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner GOAL + skip-GPT self-research after V8 campaign closeout
`NO_LEGAL_SURVIVOR`. Authorizes one cheap offline probe on the hash-bound
equity–bond panel. No registry, prereg, EA, compile, or Model 0 unless the
probe survives every frozen gate.

## De-dup intake (pre-result)

| Closed / blocked family | Why this is independent |
|---|---|
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | That idea uses **contemporaneous FX-return** median USD factor + strongest-pair pullback-break. This probe uses **lagged US equity–bond excess return** only; no FX cross-section rank, no pullback-break. |
| V8 carry weekly/daily/event / carry×vol | Those use G3 short-rate / policy differentials. This uses SPX vs UST10Y return differential. |
| COT TFF | Positioning surface; not used. |
| S619 DXY–gold catch-up | Price-only metal/DXY; not equity–bond exogenous. |
| S682–S685 equity-close hour drift | Intraday hour-of-day FX drift; this is D1 lagged cash-close differential regime. |
| VIX-only risk-off | VIX series is archived but **not** in the frozen signal. |

If intake fails later, kill as duplicate — do not retune.

## Probe identity

- Working ID: `HYP-SR-FX-EQUITY-BOND-DIFF-001` (mint only if registered after survivor)
- Probe tag: `V8_EQUITY_BOND_DIFF_V1`

## Data (hash-bound)

Root: `preflight/v8_exogenous/raw/equity_bond/`

| Series | File(s) | Role |
|---|---|---|
| S&P 500 daily close | `fred_sp500.csv` | Equity cash close |
| UST 10Y constant maturity | `mirror_us_dgs10_DGS10.csv` | Bond yield for return proxy |
| VIX | `fred_vixcls.csv` | Archived only; **unused in signal** |
| US Treasury par yield curve | `us_treasury_yield_curve_*.csv` | Provenance / alternate 10Y check |
| ECB AAA 2Y/10Y | `ecb_aaa_yc_sr_*.csv` | Archived; **unused in V1 signal** (US-only differential) |

Acquisition manifest:
`manifests/20260713_V8_EQUITY_BOND_PANEL_ACQUISITION_V1.json`

### Lag / availability

- Equity observation `t` (US cash close) → `available_at_utc = t + 1 calendar day 00:00Z`
- Bond yield observation `t` → same `+1d` rule
- FX D1 decision on calendar date `d` may use only series with `available_at <= d`
- Fail closed if as-of gap > 3 calendar days (no silent fill)

## Signal (frozen a priori)

1. `r_eq_t = SPX_t / SPX_{t-1} - 1` (skip missing)
2. `Δy_t = DGS10_t - DGS10_{t-1}` in decimal yield (e.g. 0.01 = 1 pp)
3. Bond return proxy: `r_bond_t = -7.0 * Δy_t` (modified duration **7.0** frozen)
4. `diff_t = r_eq_t - r_bond_t` (equity excess over bonds)
5. After lag, `z_d = (diff_avail_d - mean(prior 60)) / stdev(...)` needing ≥40 prior obs
6. If `z >= +0.75` → risk-on → **USD weakness** `D = -1`
7. If `z <= -0.75` → risk-off → **USD strength** `D = +1`
8. Else flat `D = 0`
9. Basket on completed D1 Mon–Thu; Friday flatten:
   - `D=+1`: short EURUSD, short GBPUSD, long USDJPY
   - `D=-1`: long EURUSD, long GBPUSD, short USDJPY
10. Per-leg stop 1.5×ATR14_D1; time-stop 5 D1 bars

## Controls (must beat equity-only)

Same calendar + `|z|>=0.75` cadence machinery:

1. **Equity-only control:** z built from `r_eq` alone; same risk-on/off → USD map
2. **Bond-only control:** z built from `-r_bond` alone (bond strength = risk-on proxy inverted consistently: high `-r_bond` = falling yields / bond rally → treat as risk-on → `D=-1`)

Candidate must beat **equity-only** on train PF stress-A **and** expectancy-A
(primary confound). Bond-only is diagnostic.

## Cost / splits / kills

- Stress A 1.5 / B 3.0 pip RT per leg; basket PnL = mean of legs after stress
- Train `[2019-01-01, 2023-01-01)`; holdout `[2023-01-01, 2026-01-01)` gated
- Kill if train trades < 80, tpw < 0.5, PF-A < 1.10, fail beat equity-only
  PF-A and expectancy-A, or year concentration of positive net-A > 0.55

## Non-rescues

No post-hoc z-threshold, duration, VIX gate, ECB overlay, or tenor mining from
the readout. Do not reopen killed carry/COT books.
