# HYP-IDOV-XAUUSD-M5-001 — source feasibility result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_INTRADAY_OBV_DIVERGENCE_FADE`

The sole outcome-blind attempt completed deterministically on FivePercent
XAUUSD M5 DESIGN 2018–2022. It found 304 exact-next price/OBV divergence
events, 167 LONG and 137 SHORT, or `1.165389/week`.

Design rows (351,303), complete-session coverage (97.7778%), measurement
coverage (100%), exact-next (100%), direction balance and year concentration
passed. Minimum 500 events, pooled cadence 2–5/week, and annual cadence failed;
2020–2022 produced only `0.9589–1.0740/week`.

This is source sparsity only. No post-decision price, outcome, cost, trade, PF
or economics was opened. Do not rescue through flow threshold/normalization,
sign inversion, agreement events, session/weekday, cooldown or timeframe.

Evidence SHA256:

- source report: `CDBD9BD3DEDB8AFCBD22DAB0B4A2D7F6C500898F26BCB83B8E52F4ACFB1461AA`
- source ledger: `86EF72F8AF6AA5C23EC05E5A7A8C837E7EE81173E9E22E4125C503556C521663`
- attempt receipt: `A48C8E7100E95D613A96FDF1BE5109ABDE4F932E5CCE42F54B26823BE3B00863`
- attempt terminal: `426CA22BD8BD50E64C3111706D6078DC7ADDF4C1A4F1E77821999A4B41E2D8FF`
