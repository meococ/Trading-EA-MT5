# CME SDR FX Options Source Feasibility Readout

Date: 2026-07-16

## Scope

This was an outcome-blind source/schema/density check. It did not open a
hypothesis, access MT5 price outcomes, create an EA, compile MQL5 or run Strategy
Tester. The 2024-2025 holdout corpus was not acquired.

## Source acquisition

- Official service: `ftp.cmegroup.com/sdr/fx/`
- Official description: `https://www.cmegroup.com/market-data/repository/data.html`
- Deterministic sample: three interior daily consolidated files per month,
  2017-2023; hourly fragments excluded.
- Acquired: 252 ZIPs / 2,592,226 bytes, directly to
  `02. AlphaFactory/external/cme_sdr_fx/` on `D:`.
- Every profiled file matches the source-manifest SHA256.

## Schema and density

- Legacy files expose dissemination time, contract type, option type,
  strike/premium and currencies. Standardized files expose equivalent UPI and
  option fields.
- Neither public schema exposes buyer/seller aggressor. The only admissible
  future thesis would be unsigned prior-day option activity conditioning a
  price-defined next-session breakout; call/put must not be treated as signed
  demand.
- With at most one setup per active day, 2017-2021 train estimates
  `4.361 trades/week`, inside the 2-5 target.
- 2022-2023 internal validation estimates only `1.944 trades/week`, below the
  target.
- The 2023 sample contains zero major-FX new-option days and zero major-FX
  new-option rows. This is temporal source discontinuity, not a threshold to
  tune around.
- Raw pair-event density (`9.250/week` train, `3.819/week` validation) is not a
  legal substitute: multiplying same-day pair trades would violate the frozen
  scalp/cadence objective and conceal the 2023 source failure.

## Verdict

`FAIL_TEMPORAL_CONTINUITY`

The source fails the 2-5/week requirement in internal validation and provides
no major-pair activity in sampled 2023. It cannot support a current seven-year
confirmed book. Do not rescue by truncating at 2022, increasing same-day pair
count, changing event types or treating call/put orientation as order-flow
direction. No hypothesis, `.mq5`, compile, Model 0 or live action is authorized.

## Verification and evidence identity

- Acquisition/profile contract tests: `8/8 PASS`; final pytest base temp was on
  `D:`.
- `02. AlphaFactory/external/cme_sdr_fx/source_manifest.json`
  - SHA256 `34FCCB9D3430405C97D8A1106EBEFFE684E3D624F434B442035D759AC97F2DD9`
- `02. AlphaFactory/external/cme_sdr_fx/schema_density_profile.json`
  - SHA256 `69BAAEEE51BD287C4AE184A740730C1582250B043554D62ADCA0D51FE0B8A44C`
- `02. AlphaFactory/tools/acquire_cme_sdr_fx.py`
  - SHA256 `6AFD5B2028234E84D6EFC43FCCEBF8F997483827EBC79428C13DFC3AADFC8E72`
- `02. AlphaFactory/tools/profile_cme_sdr_fx_options.py`
  - SHA256 `1FB97327CC0015DB978DFC373164F577489D08262C8AD5CA9C72E75948278BC9`
- Acquisition test SHA256
  `E6F468C44A19F33ACEBFD0D6DAD2A3BD285787551AA6C83110CE0FA5300F151F`
- Profile test SHA256
  `C549F7F590FB026B024F774D4F765B19A8EF2D3235F8BFF1AE93A261714FB08F`

Price outcomes accessed: `0`. Holdout files accessed by the acquisition/profile
campaign: `0`. MT5 initialized: `false`. Workspace GOAL: `UNMET`.
