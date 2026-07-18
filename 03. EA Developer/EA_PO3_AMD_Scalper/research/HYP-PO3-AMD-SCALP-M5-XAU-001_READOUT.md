# Readout — HYP-PO3-AMD-SCALP-M5-XAU-001

## Bound identity

- Source report: `05. Playbook/Strategy/PO3_AMD_Scalper_Deep_Research_Report.html`
  (`SHA256 17D1D5B0AA742EB0448ADF73C8D911568BBFE764E111469B8147FD04E2727277`).
- Frozen probe spec:
  `research/HYP-PO3-AMD-SCALP-M5-XAU-001_PROBE_SPEC.md`
  (`SHA256 17A0DEB94485F4F70BB1AE26107FECD5B60B7F55382231F4D443B6C3BA55288B`).
- Probe script: `research/po3_amd_xau_offline_probe.py`
  (`SHA256 C0B2EA2F7B004762482178DF145329F52CA6B175BBCADD8B578C8397C4A85DCF`).
- Probe artifact:
  `research/preflight/20260716_HYP_PO3_AMD_SCALP_M5_XAU_001_PROBE.json`
  (`SHA256 2545DB390070A598F4130EFC1A3A13DAC61DB071E3BEA8C179B5A2CD0D1D5ABF`).
- Symbol/timeframe/window: `XAUUSD`, M5 signal + H4 bias,
  `2022-01-01` through `2024-12-31`; point size `0.01`.
- Evidence class: cheap closed-bar offline probe. Not Strategy Tester, not
  Model 0, not promotion eligible.

## De-dup result

The family is not novel. Historical XAU/EUR Asian-range sweep variants already
failed. This probe therefore required the a-priori composite
`H4 bias + sweep + 1.5xATR displacement + MSS + FVG retest` to beat the frozen
sweep-only control. No post-result threshold edit is allowed.

## Data and sequential gate counts

- M5 bars: `212,339`; H4 bars: `4,644`; ET trading dates: `774`.
- Asian range `80..300` broker points: `6` dates.
- Bias-aligned closed-back-inside sweeps: `1`.
- Displacements: `1`; valid FVGs: `1`; closed-bar retests: `0`.

The report's XAU point/range contract eliminated `768/774` observed ET dates
before signal confirmation. This is a direct implementation of the frozen
report parameter, not a missing-data inference.

## Results

| Metric | Sweep-only control | Full PO3 challenger |
|---|---:|---:|
| Trades | 1 | 0 |
| Trades / elapsed week | 0.0064 | 0.0000 |
| Net R after report-assumption cost proxy | +2.2154 | 0.0000 |
| Expectancy R | +2.2154 | 0.0000 |
| Positive years | 1/3 | 0/3 |

Control PF is mathematically undefined/infinite from one winning trade and has
no evidentiary value. Challenger PF is undefined because it has no trades.

## Frozen gate table

| Gate | Result |
|---|---|
| 2–5 trades per elapsed week | FAIL (minimum) |
| Cost-proxy PF >= 1.50 | FAIL |
| Expectancy >= 0.40R | FAIL |
| DD <= 5% at 0.25% risk | PASS but vacuous (zero trades) |
| Positive net R in at least 2/3 years | FAIL |
| Positive net and not below control | FAIL |
| PF margin >= control + 0.20 | FAIL |

## Verdict

`KILLED_AT_OFFLINE_PROBE`.

No EA entry code, compile, or MT5 backtest is legal for this hypothesis. The
workspace's independent verified-cost frontier is also still open; the fixed
`35`-point probe cost is explicitly an unverified report assumption.

## Next legal action

Do not widen `AsianMaxPoints`, reinterpret Gold points, remove H4 bias, extend
retest bars, or add NY/hour/year filters under this ID. Any normalized-range or
ATR-relative PO3 concept is a new hypothesis and needs an Owner scope decision,
new probe spec, and untouched evidence window.
