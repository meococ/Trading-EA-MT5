# Readout — HYP-PO3-AMD-SCALP-M5-XAU-003

Verdict: **KILL_AT_OFFLINE_PROBE** on 2026-07-16. This closes the bounded
PO3-AMD report build lane before EA source.

## Frozen New York evidence

- XAUUSD M5/H4 train-only window: 2022-01-01 through 2024-12-31; 2025+ was not
  read by this probe.
- 212,339 M5 and 4,644 H4 bars; 729/774 ET dates passed the unchanged
  Asian-range/median-ATR gate.
- NY 07:00-10:00 ET funnel: 122 H4-bias-aligned sweeps -> 0
  displacement+MSS -> 0 FVG -> 0 retests.
- Sweep-only control: N=37, `0.2365` trades/elapsed week, cost-proxy PF
  `0.6739`, net `-5.4160R`, expectancy `-0.1464R`, max drawdown `2.2344%` at
  0.25% risk. 2022, 2023 and 2024 were all negative.
- Full PO3 challenger: N=0, 0 trades/week, PF unavailable, net/expectancy 0R.
- Cadence-minimum, PF, expectancy, positive-years, positive/control net and
  PF-separation gates failed. Only cadence-maximum and drawdown passed.

The report's New York branch does not change the diagnosis: the sweep family
is sparse and negative, while the frozen H4 + displacement + MSS chain
eliminates every challenger. London and New York both failed independently.
No code, compile or Model 0 backtest is justified. Relaxing signal gates or
mining another session after these outcomes would be post-hoc rescue.

## Hash-bound artifacts

- Prereg SHA256:
  `E2F5F05A4BAA10FDA7A7A47C38C3808A5FC74AB9677BCC5F33535FE9D3C641E0`.
- NY probe script SHA256:
  `F31327CE10B9E9110835562C53668026BE5F26D122D9B6242F864787C49743C2`.
- Result:
  `research/preflight/20260716_HYP_PO3_AMD_SCALP_M5_XAU_003_NY_PROBE.json`.
- Result SHA256:
  `D04C127C44E6EAD503067850548BEACFAF518063D0DF1B9055C3983611E0DA7C`.
- Frozen normalized dependency SHA256:
  `49EF8DEFA2B67F3BB60BE89D81D9635413706380D04380C6E8FB9E362FC927FD`.
- Frozen HYP-001 base dependency SHA256:
  `C0B2EA2F7B004762482178DF145329F52CA6B175BBCADD8B578C8397C4A85DCF`.

The Python bridge terminal was stopped after D-side evidence capture. No
Strategy Tester was started; see the C-drive hygiene receipt beside this
readout.

