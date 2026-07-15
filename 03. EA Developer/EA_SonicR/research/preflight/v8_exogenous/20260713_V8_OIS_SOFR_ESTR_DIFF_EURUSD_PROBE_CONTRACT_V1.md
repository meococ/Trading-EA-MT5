# V8 OIS/RFR SOFR−€STR Differential → EURUSD Probe Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner self-research (GPT waived; no Real login). Uses newly frozen overnight
RFR panel only. Authorizes **one** cheap offline probe. No registry, prereg,
EA, compile, or Model 0 unless this probe survives.

De-dup: `readouts/20260713_OIS_SOFR_ESTR_VS_CARRY_DEDUP_CLEARANCE.md`
(`INTAKE_CLEARED / INDEPENDENT`).

## Probe identity

- Working ID: `HYP-SR-FX-OIS-SOFR-ESTR-DIFF-EURUSD-001` (mint only if registered)
- Probe tag: `V8_OIS_SOFR_ESTR_DIFF_EURUSD_V1`

## Data

- Frozen panel:
  `preflight/v8_exogenous/panels/us_eu_ois_rfr_diff_d1_v1.csv`
- Acquisition manifest:
  `preflight/v8_exogenous/manifests/20260713_V8_OIS_RFR_PANEL_ACQUISITION_V1.json`
- Lag contract:
  `preflight/v8_exogenous/contracts/20260713_V8_OIS_RFR_AVAILABLE_AT_UTC_CONTRACT_V1.json`
- Field: `diff_sofr_minus_estr` = SOFR − €STR
- Lag: use `available_at_utc` (observation_date + 1 calendar day 00:00Z)
- Fail closed if gap from last available observation > 3 calendar days
- FX: MetaQuotes-Demo EURUSD D1 for falsification only

## Signal (frozen a priori — mirror bond-diff constants; do not mine)

1. Let `diff_t` be the lagged differential available on decision date `t`.
2. `z_t = (diff_t − mean(diff_{t−60..t−1})) / stdev(...)` (need ≥40 prior obs).
3. If `z_t >= +0.75` → short EURUSD (`D=−1`); if `z_t <= −0.75` → long EURUSD (`D=+1`); else flat.
4. Enter on completed D1 Mon–Thu when D ≠ 0; Friday flatten.
5. Stop 1.5×ATR14_D1; time-stop 5 D1 bars.

Thesis: unusually wide USD overnight RFR premium vs €STR attracts USD funding /
capital toward USD → EURUSD weakens; unusually narrow/negative premium favors EUR.

## Control

Same calendar + |z| threshold machinery, but
`D = sign(20d EURUSD return)` when |z| gate would fire on OIS z
(momentum-follow with identical entry calendar density), else flat.
OIS series unused in control scores.

## Cost / splits / kills

- Stress A 1.5 / B 3.0 pip RT (research stress proxy, not QFSI Real).
- Train `[2019-01-01, 2023-01-01)`; holdout `[2023-01-01, 2026-01-01)` gated.
- Kill if train trades < 80, tpw < 0.5, PF-A < 1.05, fail beat control PF-A and
  expectancy-A, or year concentration of positive net-A > 0.55.

## Non-rescues

No post-hoc z-threshold, tenor swap, SOFR−SONIA overlay after seeing this
readout, session filters, or carry-rank revival. Companion US−UK OIS panel may
only be probed under a **separate** frozen ID after this book closes.
