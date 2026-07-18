# Readout — HYP-UPS-XAU-M5-001

## Bound identity

- Prereg SHA256: `C3B57121FA7EB67DC2A4283A560E2CFF2E0D90A100E49F3341D6D3C8798B881D`
- Probe source SHA256: `FC98AA57830A9B6B2147CF00E787FC15B403DE91F92FDCDB2083B6E2C22F77A6`
- Probe artifact SHA256: `55AFEF4F13268901C24A182CD30061303D91280EE31943974E9F25C83E7036EA`
- Window: XAUUSD M5, 2024-01-01 through 2026-07-15; closed-bar only.

## Evidence quality

- Opportunity-density probe only; no fill, P&L or profitability simulation.
- MT5 raw bars were read in place and were not copied into the workspace.
- Terminal reported `trade_allowed=false`; no order or account mutation path
  exists in the probe.

## Results

- Eligible candidates: `65` (`55` long, `10` short).
- Active months: `23`; median `3` candidates per active month.
- Frozen probe gates: candidate count FAIL, short count FAIL, active months
  FAIL, monthly median FAIL; long count PASS.

## Gate table and verdict

| Gate | Required | Actual | Result |
|---|---:|---:|---|
| candidates | >=120 | 65 | FAIL |
| long / short | each >=20 | 55 / 10 | FAIL |
| active months | >=24 | 23 | FAIL |
| median per active month | >=4 | 3 | FAIL |

Final verdict: `PARKED_BEFORE_BUILD`. No EA entry code or Model 0 run is legal
for this hypothesis ID.

## Next legal action

The exact-adjacency interpretation is not mandated by the report. A new
hypothesis may model sweep as a state persisting for a fixed number of closed
bars. Thresholds or post-result time/direction vetoes may not be changed under
this ID.
