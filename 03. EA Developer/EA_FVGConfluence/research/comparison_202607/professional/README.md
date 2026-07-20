# Professional benchmark plane

The broad professional comparator is the Barclay Currency Traders Index. A
named CTA requires identity/status verification in NFA BASIC and an admissible
performance presentation. FX DARWINs with at least 36 months may be used only
as a secondary risk-normalized cohort. None of these sources establishes ICT
style attribution.

`compare_monthly.py` implements the frozen comparison mechanics:

- common calendar overlap only;
- 12-month trailing volatility, lagged one month;
- 10% annual volatility target;
- leverage cap 2x;
- paired circular month-block bootstrap with fixed seed;
- non-inferiority margin of -0.25 Sharpe;
- maximum-drawdown tolerance of three percentage points.

The script refuses to compare fewer than five peer series or a series with
fewer than 36 raw monthly observations. No current EA monthly-return file is
provided because the terminal FVG hypothesis remains killed without Model 0.

Current verdict is `INSUFFICIENT_VERIFIED_DATA`. Pass 2 recorded nine
36-month-plus DARWINs with Forex exposure as secondary context, but no common
monthly series was ingested and the subset is often multi-asset, gross-return,
not ICT-attributed, and not exact-EA-attributed. See
`PROFESSIONAL_BENCHMARK_STATUS.json` and `PROFESSIONAL_BENCHMARK_READOUT.md`.

Primary definitions:

- Barclay Currency Traders Index:
  https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Currency-Traders-Index
- NFA BASIC: https://www.nfa.futures.org/basicnet/
- CFTC performance presentation:
  https://www.cftc.gov/foia/fedreg03/foi030313a.htm
- Darwinex Return/Risk:
  https://help.darwinex.com/return-risk-ratio
