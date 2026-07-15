# V8 Public Exogenous Data Archive

Status: `ACQUISITION_SURFACE / NO_PROBE / NO_PREREG / NO_EA`

This folder holds Owner-independent, lawful public exogenous inputs for the
V8 data-contract expansion. Presence of files here does **not** authorize an
offline probe, registry row, prereg, EA build, compile, or Strategy Tester run.

## Layout

| Path | Contents |
|---|---|
| `cot/` | CFTC Traders in Financial Futures (TFF) historical bulk zips |
| `rates/` | Official G3 / USD short-rate and yield public CSVs (and URL stubs) |

## License / reuse

- **CFTC COT**: U.S. government public report. Free for research use. Do not
  redistribute as a paid product. Attribute CFTC.gov as source.
- **U.S. Treasury bill / par-yield CSVs**: U.S. government public data from
  treasury.gov. Research reuse with attribution is standard.
- **ECB SDMX**: European Central Bank open data. Follow ECB data-use terms;
  research reuse with attribution.
- **BoE Bank Rate**: Bank of England public statistical release. Research
  reuse with attribution; respect site ToS for scrape/export.
- **BoJ policy rates**: Bank of Japan public tables. Research reuse with
  attribution; freeze parser + hash when HTML tables are used.

Do not treat vendor mirrors (Yahoo, Stooq, etc.) as first-class evidence in
this tree without a separate license check.

## Publication lag (fail-closed)

### COT (TFF)

- Report **as-of**: Tuesday (holiday shifts exist).
- Typical **release**: Friday ~15:30 Eastern.
- Required fields for any future join: `as_of_date`, `release_datetime_utc`.
- Never treat the Tuesday as-of date as known on Wednesday/Thursday.
- Signal may use a report only after `bar_close_utc >= release_datetime_utc`.

### Policy / short rates / yields

- Policy rates: use announcement clock + **effective date**. Never backfill a
  future effective rate into prior bars.
- Market rates (T-bill, par yields, EFFR/SOFR when added): observation date ≠
  availability date. Prefer an explicit `available_at_utc` column.
- EFFR/SOFR (FRED/NY Fed, if later added with API key): typically next
  business day publication.
- No silent forward-fill across missing observations.

## Join rules (lookahead ban)

1. Join FX closed bars only with
   `bar_close_utc >= available_at_utc` (or `release_datetime_utc` for COT).
2. Prefer H4/D1 cadence; weekly COT and sparse policy steps are not M15 scalp
   triggers by themselves.
3. Map COT contracts to spot EURUSD / GBPUSD / USDJPY only after a frozen
   contract map (not defined in this README).
4. For equity/bond differentials (if added later): Tokyo/London morning FX
   decisions may use **prior** US/EU official closes only.
5. No join into an offline probe until a coordinator freezes join keys and
   Owner authorizes a probe.

## Authorization flags

| Action | Authorized by this archive? |
|---|---|
| Store / hash public files | Yes (acquisition only) |
| Offline probe | **No** |
| Registry append | **No** |
| Prereg | **No** |
| EA / compile / backtest | **No** |

## Hashing

Every acquired binary/CSV must have SHA-256 recorded in the acquisition
receipt under `research/preflight/`. Re-download if hash cannot be verified.

## Source index (canonical URLs)

- CFTC historical compressed index:
  `https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm`
- TFF year pattern:
  `https://www.cftc.gov/files/dea/history/fut_fin_txt_YYYY.zip`
- U.S. Treasury daily archives:
  `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives`
- ECB DFR CSV:
  `https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV?format=csvdata`
- BoE Bank Rate:
  `https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp`
- BoJ (EN portal):
  `https://www.boj.or.jp/en/`
