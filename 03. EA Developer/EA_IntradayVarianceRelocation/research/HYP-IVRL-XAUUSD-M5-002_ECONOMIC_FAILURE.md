# HYP-IVRL-XAUUSD-M5-002 — Economic failure

Date: 2026-08-11

Verdict: `KILL_BASE_PF_EXPECTANCY_AND_YEAR_CONCENTRATION_FAIL_CADENCE_DD_PASS`

## Frozen mechanism

- XAUUSD M5, FivePercent MT5 native data, 2018-01-01 through 2023-01-01.
- Compare early-session versus late-session mean squared log return on the
  complete 00:00–15:55 session.
- Emit only when late variance exceeds early variance; continue the signed
  07:55→15:55 displacement at exact next 16:00.
- Frozen execution: structural 12-bar extreme plus 0.20 ATR14 stop, 1.50R
  target, 0.10% risk, 20:00 flatten, 3.5% daily and 8% account loss locks.

## Engineering evidence

- Source gate: 1,196 executable events, LONG/SHORT 607/589,
  `4.5848849945/week`.
- AlphaFactory run: `20260811_143033`.
- History quality: 99%; 351,303 bars; 135,208,676 ticks.
- Journal: 5,035,086 raw bytes from three deltas, not truncated; two identical
  summaries; `runtime_failed=false`.
- Runtime reconciliation: raw 1,196 = entries 670 + rejects 5 + risk-lock skips
  521; closes 221 + close rejects 0 = close attempts 221.
- Compile: 0 errors, 0 warnings; non-repaint audit PASS.

## Economic result after tester costs

- Trades: 670; wins/losses 259/411.
- Profit factor: `0.7648116391`.
- Net profit: `-$7,824.07`.
- Expectancy: `-$11.6777/trade`.
- Gross profit/loss: `$25,443.18 / -$33,267.25`.
- Commission/swap: `-$971.60 / -$298.48`.
- Cadence: `2.5684556407/week` — PASS.
- Maximum drawdown: `7.9897069296%` — PASS, narrowly.
- Direction split: both LONG and SHORT books lost.
- Calendar concentration: 2018/2019/2020 had 230/234/206 trades; 2021–2022
  had none after the frozen 8% loss latch. Maximum-year share was
  `34.9254%`, above the 30% gate.

## Decision boundary

This is an economic failure of the exact variance-relocation continuation
mapping, not a data or implementation failure. Do not rescue it by removing or
loosening the drawdown latch, inverting direction, selecting years/weekdays,
changing the session split, or tuning stop/target/hold/risk. Cost stress,
optimization, validation and holdout remain unopened. The overall EA goal
continues with a materially different information mechanism.

## Bound artifacts

- Source SHA256: `2BAC58D5BC2FE061CE4593E084E899338CE0615F0B48BC3D3CC8BF53F000E484`
- EX5 SHA256: `C322CCA309AEF670390F13203C917DEA39D0A185B5DB212C61745234FF32418B`
- Prereg SHA256: `3B10BC51C60B16FBC2BFBE8DE55463D26F7806FE738C705BA4BE45A95139CA57`
- Task SHA256: `9DB124D369F58419214F65EAA70F37F27994F2080AD124B73FAA34C965EE5CFC`
- Receipt SHA256: `00F7719A9FD032F099DBB65D486AF3EAD68E8482DDD3360CB2D8CAC931AA336E`
- Run manifest SHA256: `141DB64AB844F102FDFE7CBD3DE6B06A3BF96EA0E27AE1B82575909F82D379A4`
- Report SHA256: `F85768DCB6CBBD384139830411D594410621768B5126C58C42086CA2056FF36F`
- Journal SHA256: `46938E898A41DA25A2BF15B9E9B1F4446B0C8199BAA1789A3E0C3120BFEEE6C6`
- Non-repaint audit SHA256: `9CF0B27A16CA4931418D81302572E816AFA5883E14799160BCC3B661DE52EA23`
