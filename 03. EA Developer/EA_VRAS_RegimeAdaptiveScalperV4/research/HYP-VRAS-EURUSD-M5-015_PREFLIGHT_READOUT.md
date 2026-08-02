# HYP-VRAS-EURUSD-M5-015 P0 Preflight Readout

Date: 2026-08-02

Verdict:
`PARK_PRE_EA_INVALID_PLAN_EVIDENCE_OR_CAPABILITY_NO_OUTCOME_READ`

## Decision

Do not create the proposed V4 EA, compile it, or launch MetaTrader. The supplied
plan fails all six frozen pre-EA gates before any trade outcome or economic
surface is opened. Building the three-engine EA now would convert mislabeled
and incomplete evidence into code without establishing a causal edge.

This is an evidence/capability failure, not a claim that every future regime or
order-flow strategy lacks edge.

## What the deterministic replay established

The source called `design_m1_close.parquet` contains 5,580,755 combined DESIGN
rows, not 5.5 million EURJPY rows:

| Symbol | Rows | Coverage | Legacy tail H | VR(5) | OU half-life |
|---|---:|---|---:|---:|---:|
| EURJPY | 1,860,530 | 2016-01-04 to 2020-12-31 | 0.443191 | 0.939514 | 1252.69 M1 bars |
| EURUSD | 1,859,939 | 2016-01-04 to 2020-12-31 | 0.486425 | 0.990089 | invalid, AR(1) b > 1 |
| USDJPY | 1,860,286 | 2016-01-04 to 2020-12-31 | 0.461182 | 0.865403 | 89.43 M1 bars |

The original unfiltered `tail(10,000)` and `tail(1,440)` contain only USDJPY.
Those rows reproduce the plan's headline Hurst 0.4612, VR(5) 0.8654 and OU
half-life 89.43. They are therefore not EURJPY evidence and cannot be
transferred to the proposed EURUSD EA.

The canonical manifest declares 2016-2020 as DESIGN and 2021-2024 as sealed
validation. The preflight loaded zero sealed rows.

## Gate results

| Gate | Result | Evidence |
|---|---|---|
| Source identity | FAIL | Headline tail is USDJPY, while the plan labels it EURJPY. |
| History coverage | FAIL | Source is three-symbol 2016-2020 DESIGN, not EURJPY 2016-2024. |
| Target-symbol evidence | FAIL | Proposed target is EURUSD; its own legacy statistics differ and OU is invalid. |
| True-flow contract | FAIL | EURUSD source has OHLC, tick volume, real volume and spread, but no aggressor side/trade volume or bid/ask queue sizes for true CVD, VPIN and LOB OFI. |
| Estimator/arbitration contract | FAIL | No estimator window, confidence interval, null/power, rolling stability rule or deterministic engine arbitration is frozen. |
| Production async execution | FAIL | Shared kernel is mutation-disabled and lacks durable-intent restart, late/partial-fill and callback-correlation fixture proof. The supplied timeout fallback can return to IDLE after an ambiguous late fill. |

Non-stitched daily session diagnostics also fail to justify the proposed fixed
regime thresholds. The frozen runner accepted same-day, gap-free segments with
at least 300 M1 rows; it did not require every one of the nominal 360 minutes,
so these are descriptive eligible segments rather than full-session proof. On
1,152 Asian segments, the plan's range-master gate appears on 52.60% while its
trend-master gate appears on 0.087%. On 1,271 London segments, those shares are
34.46% and 0.00%. Point estimates without calibrated uncertainty and a frozen
decision policy do not authorize a regime switcher.

## Outcome-blind attestation

- No PnL, PF, MFE/MAE, trade return or post-entry outcome was computed.
- No 2021-2024 validation or 2025+ holdout row was loaded.
- No `.mq5` or EX5 was created.
- No MetaTrader process, Model 0/4 backtest, order or position was opened.
- Economic trials consumed: 0. Promotion eligibility: false.

## Registry reconciliation

A candidate-registry open row was attempted before the probe and rejected by
the canonical validator because every candidate row must bind a real canonical
EA source. The just-appended invalid row was removed under the explicit
latest-row repair rule. The registry then passed at 461 rows / 163 hypotheses.
No fake `.mq5` sentinel or terminal candidate row was created. This packet is a
pre-candidate P0 failure record; the active T2 build/MT5 authority is unchanged.

## Legal successor boundary

A successor must use a fresh identity and freeze one atomic engine before
outcomes. It must bind correct EURUSD data; define estimator, window, null,
uncertainty, power, session clock, costs and matched control; and either acquire
genuine decision-time flow under Model 4/forward/external data or explicitly
name and validate a different proxy thesis. Use synchronous execution for the
MVP unless the async kernel first passes deterministic callback, restart,
partial-fill, late-fill and ownership fixtures.
