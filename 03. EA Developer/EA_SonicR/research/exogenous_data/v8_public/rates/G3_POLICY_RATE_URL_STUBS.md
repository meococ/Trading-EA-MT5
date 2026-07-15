# G3 Policy / Short-Rate URL Index (documented)

This file records official URLs for G3 policy and short-rate surfaces.
Acquired files live beside this note; documented-but-not-acquired URLs are
retry targets. No FRED API key was used in this acquisition pass.

## Acquired (see sibling CSVs + acquisition receipt)

| Series | Source | Local file pattern |
|---|---|---|
| US Treasury bill rates | treasury.gov | `daily_treasury_bill_rates_YYYY.csv` |
| US Treasury par yield curve | treasury.gov | `daily_treasury_yield_curve_YYYY.csv` |
| ECB Deposit Facility Rate (change + daily) | data-api.ecb.europa.eu | `ecb_dfr_lev.csv`, `ecb_dfr_daily_lev.csv` |
| BoE Bank Rate (IUDBEDR) | bankofengland.co.uk IADB CSV | `boe_bank_rate_iadb.csv` |
| NY Fed EFFR | markets.newyorkfed.org | `nyfed_effr_search.csv` |
| NY Fed SOFR | markets.newyorkfed.org | `nyfed_sofr_search.csv` |

## Canonical URLs

### US Treasury (no API key)

- Archives index:
  `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives`
- Year CSV pattern (bill rates):
  `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{YEAR}/all?type=daily_treasury_bill_rates&field_tdr_date_value={YEAR}&page&_format=csv`
- Year CSV pattern (par yield curve):
  `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{YEAR}/all?type=daily_treasury_yield_curve&field_tdr_date_value={YEAR}&page&_format=csv`

Note: path segment order is `daily-treasury-rates.csv/{YEAR}/all` (not `.../all/{YEAR}`).

### ECB (no API key)

- DFR level (business / change series):
  `https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV?format=csvdata`
- DFR daily level:
  `https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata`

### BoE

- Bank Rate interactive page:
  `https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp`
- IADB CSV export used in this pass (`IUDBEDR`):
  `https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2020&Dateto=13/Jul/2026&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N`

### BoJ (document + HTML capture; structured CSV may still need frozen parser)

- EN statistics portal:
  `https://www.boj.or.jp/en/statistics/index.htm`
- Basic Discount Rate and Basic Loan Rate:
  `https://www.boj.or.jp/en/statistics/boj/other/discount/index.htm`
- Monetary Policy Meetings / decisions (EN):
  `https://www.boj.or.jp/en/mopo/mpmdeci/index.htm`
- Policy Interest Rate materials are published as HTML tables / PDFs; any
  future structured series must freeze a parser + SHA-256 receipt before probe.

### NY Fed (no API key; USD short-rate proxies)

- EFFR CSV search:
  `https://markets.newyorkfed.org/api/rates/unsecured/effr/search.csv?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`
- SOFR CSV search:
  `https://markets.newyorkfed.org/api/rates/secured/sofr/search.csv?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`

### FRED (not used this pass — free API key soft dependency)

- Register key: `https://fredaccount.stlouisfed.org/apikeys`
- Useful series later: `EFFR`, `SOFR`, `DTB3`, `DGS2`, `DGS10`

## Publication lag reminders

- Policy rates: announcement + effective date; never backfill future effective
  rates into prior FX bars.
- Treasury bill/yield CSVs: observation date ≠ availability; join only after
  documented `available_at_utc`.
- EFFR/SOFR: typically next-business-day publication by NY Fed.
