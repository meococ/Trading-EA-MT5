# V8 VIXCLS Risk-Off → USDJPY Probe Contract V1 — 2026-07-14

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner MT autonomy + GPT waived. Price-M15 dual-filter shelf EMPTY.
Authorizes **one** cheap offline probe on hash-bound `fred_vixcls.csv`.
No registry/prereg/EA/Model 0 unless probe survives.

De-dup: `readouts/20260714_VIX_RISKOFF_USDJPY_DEDUP_CLEARANCE.md`
(`INTAKE_CLEARED / INDEPENDENT`).

## Probe identity

- Working ID: `HYP-SR-FX-VIX-RISKOFF-USDJPY-001` (mint only if registered)
- Probe tag: `V8_VIX_RISKOFF_USDJPY_V1`

## Data

- Series: `preflight/v8_exogenous/raw/equity_bond/fred_vixcls.csv` (VIXCLS)
- Acquisition provenance: equity_bond panel manifest
  `manifests/20260713_V8_EQUITY_BOND_PANEL_ACQUISITION_V1.json`
- Lag: observation date `t` → `available_at = t + 1 calendar day` (cash close → next UTC day)
- Fail closed if as-of gap > 3 calendar days
- FX: MetaQuotes-Demo USDJPY D1 falsification only

## Signal (frozen a priori — mirror OIS z constants; do not mine)

1. Let `vix_t` be VIXCLS level on observation `t`.
2. After lag, on decision date `d`, take latest available `vix`.
3. `z_d = (vix − mean(prior 60 available obs)) / stdev(...)` needing ≥40 prior obs.
4. If `z >= +0.75` → risk-off → **short USDJPY** (`D=−1`).
5. If `z <= −0.75` → risk-on → **long USDJPY** (`D=+1`).
6. Else flat.
7. Enter completed D1 Mon–Thu when D ≠ 0; Friday flatten.
8. Stop 1.5×ATR14_D1; time-stop 5 D1 bars.

Thesis: elevated VIX marks risk-off / JPY strength → USDJPY falls; depressed VIX
marks risk-on → USDJPY rises.

## Control

Same calendar + `|z|` gate density; direction = sign(20d USDJPY return)
(momentum-follow). VIX unused in control scores.

## Cost / splits / kills

- Stress A 1.5 / B 3.0 pip RT (research proxy ≠ Real QFSI).
- Train `[2019-01-01, 2023-01-01)`; holdout `[2023-01-01, 2026-01-01)` gated.
- Kill if train trades < 80, tpw < 0.5, PF-A < 1.05, fail beat control PF-A and
  expectancy-A, or year concentration of positive net-A > 0.55.

## Non-rescues

No post-hoc z-threshold, VIX-return transform, hour/day mining, equity−bond
overlay, or SOFR−SONIA twin from this readout.
