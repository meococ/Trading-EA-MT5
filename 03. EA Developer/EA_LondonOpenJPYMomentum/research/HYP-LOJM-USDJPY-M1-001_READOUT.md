# HYP-LOJM-USDJPY-M1-001 — TRAIN Proxy Readout

- Attempt: `LOJM001-TRAIN-ECON-001`
- Verdict: `KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`
- Evidence class: engineering-valid offline close-only TRAIN proxy
- Promotion status: not eligible
- MQL5 / Model 0 / validation / holdout: not opened

## Plain result

The exact London-open remainder-of-session translation has enough natural
cadence, but it has no economic survivor on the frozen 2016–2020 FivePercent
USDJPY broker data. All five source/cadence gates passed; all seven economic
gates failed.

This result closes only the exact 08:00–08:30 London formation / 08:30 entry /
16:30 exit / same-direction / no-filter object. It does not claim that every
London-open strategy, every JPY mechanism, or the paper's unretrieved exact
implementation has no edge.

## Frozen population and source validity

- Trades: `1,283` complete London-local weekdays.
- Coverage: `98.3896%` of weekdays between first and last eligible date.
- Elapsed weeks: `260.999998`; cadence: `4.915709/week`.
- Direction: `611 LONG / 672 SHORT`.
- Maximum year share: `20.2650%`.
- Source/cadence gates: `5/5 PASS`.
- Dataset parquet SHA-256:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`.
- Validation 2021–2024 and every 2025+ payload remained sealed.

## Economic result

| Measure | Primary | Matched reverse |
|---|---:|---:|
| Gross PF before proxy costs | 0.907704 | 1.101681 |
| PF @ 1.50 pips | 0.793002 | 0.962553 |
| PF @ 2.25 pips | 0.741205 | 0.899813 |
| PF @ 3.00 pips | 0.692888 | 0.841224 |
| Expectancy @ 1.50 pips | -2.575682 pips | -0.424318 pips |

- Annual primary x1 net pips: 2016 `-1282.9`, 2017 `-407.6`, 2018 `+55.0`,
  2019 `-629.9`, 2020 `-1039.2`.
- Positive years: `1/5` versus frozen minimum `4/5`.
- One-sided 10,000-permutation p-value: `0.861814` versus maximum `0.05`.
- Economic gates: `0/7 PASS`.

The primary loses even before the 1.50-pip proxy cost, and the reverse control
is less bad but still loses after cost. Direct reversal is therefore not a
survivor and is not authorized as a rescue.

## Chart and forensic interpretation

The frozen diagnostic chart shows the primary equity falling across most of
the full window, not a single isolated failure year. Only 2018 is slightly
positive. PF deteriorates monotonically as the predeclared cost increases.
This supports a terminal kill without chart-mined filters or a second run.

- Chart:
  `research/evidence/HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001/lojm_001_train_kill_diagnostics.png`
- Chart SHA-256:
  `784630AFA78B4DBF70DFA20F618E2DB809279A182B0329239CC850F6FB98D999`.

## Failure radius and next authority

Forbidden under this ID: clock changes, last-half-hour reinterpretation,
direction flip, BOJ/year/news deletion, volatility or trend filters, cost
changes, stop/target invention, validation access, MQL5, Model 0, optimization,
promotion, paper or live execution.

A future London-related candidate must be independently anchored and materially
different before any outcome access—for example a genuinely different
decision surface or external point-in-time state—not a filter mined from this
readout. The workspace book goal remains unmet.

## Bound evidence

- Plan SHA-256:
  `83C1D47893170789C936F1539889A46A596BEEDC19B45BED465C5CDB7EB9B66C`.
- Attempt-start SHA-256:
  `74BB01E7DD0987D63ACBDD690CA5BD8B7B4CA439FC57FEB7DF0DF228DA364D53`.
- Trade ledger SHA-256:
  `6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98`.
- Terminal SHA-256:
  `FCBCC6B5C54796B0D96F81B71BAD825A809DB605EDFDD88374F84AE1129A86FB`.
