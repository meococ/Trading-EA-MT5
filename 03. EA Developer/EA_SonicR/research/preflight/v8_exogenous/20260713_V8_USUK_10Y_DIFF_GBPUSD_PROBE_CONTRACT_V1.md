# V8 US-UK 10Y Yield Differential -> GBPUSD Probe Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner autonomous data-state change after V8 self-research fail-closed.
Uses the newly frozen US-UK bond-yield panel only. Authorizes **one** cheap
offline probe. No registry, prereg, EA, compile, or Model 0 unless this probe
survives.

## De-dup intake (pre-result)

| Closed family | Why this is independent |
|---|---|
| `V8_USEU_10Y_DIFF_EURUSD_V1` (KILL PF-A 0.58) | Same *style* of sovereign 10Y differential z-gate, but **different currency leg** (GBPUSD not EURUSD) and **different non-US curve** (BoE UK GLC nominal spot 10Y, not ECB AAA gov). Not a retune of the killed USEU book. |
| Killed G3 carry weekly/daily/rate-event | Those use **short-rate / policy** differentials. This uses **sovereign 10Y bond yield** US-UK differential. |
| Killed COT TFF / CarryA-Vol | Positioning / vol-gated carry — different causal surface. |
| `V8_USBILL_SLOPE_USD_BASKET` | US bill **curve shape** -> multi-pair USD basket. This is **cross-market 10Y differential** -> GBPUSD only. |
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | Contemporaneous FX-return median + pullback-break. This uses lagged bond differential only. |
| S619 DXY-gold catch-up | Price-only leader/laggard. Causal variable here is lagged public bond yields. |
| S682-S685 equity-close hour drift | Equity session clock / close hour — not bond differential. |

If intake fails later, kill as duplicate — do not retune.

## Probe identity

- Working ID: `HYP-SR-FX-USUK-10Y-DIFF-GBPUSD-001` (mint only if registered)
- Probe tag: `V8_USUK_10Y_DIFF_GBPUSD_V1`

## Data

- Frozen panel:
  `preflight/v8_exogenous/panels/us_uk_bond_yield_diff_d1_v1.csv`
- Acquisition manifest:
  `preflight/v8_exogenous/manifests/20260713_V8_USUK_BOND_YIELD_PANEL_ACQUISITION_V1.json`
- Field: `diff_us_uk_10y` = US Treasury 10Y − BoE UK nominal spot 10Y (GLC)
- Lag: use `available_at_utc` column (observation_date + 1 calendar day 00:00Z)
- Fail closed if gap from last available observation > 3 calendar days
- FX: MetaQuotes-Demo GBPUSD D1 for falsification only

## Signal (frozen a priori — mirror USEU; do not mine)

1. Let `diff_t` be the lagged differential available on decision date `t`.
2. `z_t = (diff_t − mean(diff_{t−60..t−1})) / stdev(...)` (need ≥40 prior obs).
3. If `z_t >= +0.75` → short GBPUSD (`D=−1`); if `z_t <= −0.75` → long GBPUSD (`D=+1`); else flat.
4. Enter on completed D1 Mon–Thu when D ≠ 0; Friday flatten.
5. Stop 1.5×ATR14_D1; time-stop 5 D1 bars.

Thesis: unusually wide US−UK 10Y premium attracts capital toward USD → GBPUSD
weakens; unusually narrow/negative premium favors GBP.

## Control

Same calendar + |z| threshold machinery, but
`D = sign(20d GBPUSD return)` when |z| gate would fire on bond z
(momentum-follow with identical entry calendar density), else flat.
Bond series unused in control scores.

## Cost / splits / kills

- Stress A 1.5 / B 3.0 pip RT (not zero; research stress proxy, not QFSI Real).
- Train `[2019-01-01, 2023-01-01)`; holdout `[2023-01-01, 2026-01-01)` gated.
- Kill if train trades < 80, tpw < 0.5, PF-A < 1.05, fail beat control PF-A and
  expectancy-A, or year concentration of positive net-A > 0.55.

## Non-rescues

No post-hoc z-threshold, tenor swap (2Y/5Y), EUR/JPY sleeve mining, or
session filters from the readout. Do not retune from killed USEU evidence.
