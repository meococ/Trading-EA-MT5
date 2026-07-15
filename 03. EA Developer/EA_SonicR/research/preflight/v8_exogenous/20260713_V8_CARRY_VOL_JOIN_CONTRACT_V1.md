# V8 Carry×Vol Join Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner autonomous GOAL mandate (2026-07-13) plus V8 data-contract expansion
packet. ChatGPT Deep Research V8 submission is blocked by browser login; this
local contract uses point-in-time interest differentials and Menkhoff et al.
(2012) global FX volatility risk for carry.

This contract authorizes exactly one cheap offline probe. It does not
authorize registry append, prereg freeze, MQL5 EA code, MetaEditor compile, or
Strategy Tester.

## Hypothesis (probe identity)

- Working ID: HYP-SR-FX-CARRY-VOL-REGIME-001 (mint only if later registered)
- Probe tag: CARRY_VOL_REGIME_V1
- Mechanism: hold short-rate differential exposure only when innovations to
  global FX volatility are non-positive; flatten when innovations are positive.
- Independent of HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001 (no pullback-break,
  no strongest-pair routing, no M15 price-factor median).

## Availability rule

available_at_utc = observation_or_announcement_date + 1 calendar day, 00:00 UTC.
No silent forward-fill across gaps longer than 5 calendar days.

## FX surface

Symbols EURUSD, GBPUSD, USDJPY. Closed H4 via MT5 copy_rates_range.
MetaQuotes-Demo allowed for falsification only.

## Carry

carry_EURUSD = EUR_DFR - US_13W
carry_GBPUSD = BoE - US_13W
carry_USDJPY = US_13W - BoJ
dir = +1 if carry > 0.25 else -1 if carry < -0.25 else 0

## Vol gate

sigma_t = mean abs daily log returns of three pairs.
vol_innovation = AR(1) expanding residual (min 60 days). Positive => flat.

## Synthetic execution

Mon-Thu H4 decisions; Friday flatten. Stop 1.5*ATR14_H4; time-stop 6 bars.
Stress A 1.5 pip RT; Stress B 2.5 pip RT.

## Splits

Train [2021-01-01, 2024-01-01); Holdout [2024-01-01, 2026-01-01).

## Control

Momentum sign of prior 20 H4 returns; same stops/costs/weekend.

## Kill gates

Train stress-A PF < 1.10; holdout stress-B PF < 1.00; holdout exp<=0;
holdout tpw outside [0.5,8]; fail beat control holdout PF and exp;
year concentration > 0.55.
