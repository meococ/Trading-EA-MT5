# V8 Exogenous Data Acquisition Inventory — 2026-07-13

Status: `INVENTORY_SUPERSEDED_IN_PART / SEE_RATES_AND_BOND_YIELD_READINESS / NO EA / NO BACKTEST`

Supersession (2026-07-13 night): lawful G3 **rates** archives are now present
under `preflight/v8_exogenous/raw/` and `research/data/exogenous/`. Treat
`readouts/20260713_V8_G3_RATES_PANEL_READINESS.md` as the live rates inventory.

Supersession (2026-07-13 late night, post fail-closed): lawful **US–EU bond
yield differential** panel is now frozen under
`preflight/v8_exogenous/raw/bond_yields/` +
`preflight/v8_exogenous/panels/us_eu_bond_yield_diff_d1_v1.csv`
(SHA256 `27D4BE9BAEBDE5062813D98869C886DC2E0E0CDA5E8B6967D723085308E7D18D`;
2098 joined days). Lag contract:
`contracts/20260713_V8_BOND_YIELD_AVAILABLE_AT_UTC_CONTRACT_V1.json`.
Readiness: `readouts/20260713_V8_BOND_YIELD_PANEL_READINESS.md`. Probe
`V8_USEU_10Y_DIFF_EURUSD_V1` → `KILL_AT_OFFLINE_PROBE` (cadence OK; PF-A 0.579;
lost to momentum control). Do not retune.

This file remains historical for QFSI/GVBCI/SCFIS blockers. COT TFF extracted
TXT 2022–2025 is on disk; older zip-binary claims may still be incomplete and
are **not** required after the COT probe kill.

Authority: Owner autonomous mandate to acquire lawful public exogenous
surfaces so V8 can reopen after the V7 price-only stop. This readout does not
authorize a hypothesis, registry row, prereg, probe, compile, or Strategy
Tester run. It answers what agents can acquire **today without Owner broker
re-login**.

## 1. Local evidence already on disk

### `preflight/v4_data/*`

| Artifact | Verdict |
|---|---|
| `20260713_MT5_READONLY_PROBE_V1.json` | `BROKER_SERVER_MISMATCH`: expected `FivePercentOnline-Real`, observed `MetaQuotes-Demo`. Read-only; 0 orders. Symbols probed: EURUSD, GBPUSD, XAUUSD (not USDJPY). History sample marked `UNPROVEN_HISTORY_SAMPLE`. |
| `20260713_EXECUTION_DATA_INVENTORY_V1.json` | QFSI `STOP_DATA_FRONTIER` (server mismatch + 0 eligible hash-bound bundles). GVBCI `data_present_locally: false`. SCFIS excluded. 69 tester slippage summaries ≠ broker evidence. |
| `20260713_V4_DATA_FOUNDATION_RECEIPT_V1.json` | Foundation tools/schemas ready; live data not ready. Strategy authority: none. |
| `20260713_GVBCI_DATABENTO_QUOTE_REQUEST_V1.json` | Frozen cost-quote-only request; no purchase/download authorized. |

### Related contracts

- `20260713_GVBCI_DATA_ACQUISITION_FEASIBILITY.md`: `GO_FOR_COST_QUOTE_ONLY`. Paid CME/Databento route; Owner license/cost approval required. **Not Owner-login-independent in the free sense.**
- `04. Project Control/ai/data_contracts/20260713_EXECUTION_DATA_ACQUISITION_CONTRACT_V1.md`: QFSI capture gate still requires target-server identity. **Blocked until Owner broker re-login to `FivePercentOnline-Real`.**
- `20260713_NEW_STRATEGY_DEEP_RESEARCH_DATA_CONTRACT_V8.md`: explicitly expands lawful public carry/funding/positioning, COT-with-lag, and equity/bond differentials as V8 reopen surfaces.

### Workspace search for COT / FRED / yield / carry series

**Historical note (inventory original):** claimed absent. **Now superseded.**

Present on disk (hash-bound under `preflight/v8_exogenous/`):

- G3 short rates + US Treasury bills (see G3 rates readiness).
- CFTC TFF extracted TXT 2022–2025 (`raw/cot_tff_extracted/`).
- US Treasury par yield curve 2018–2026 + ECB AAA gov 2Y/10Y + frozen
  US−EU 10Y differential panel (see bond-yield readiness).

Still missing / not frozen: true FX forwards/OIS, UK gilt / JGB official
CSV panel, license-clean equity-index archive, ALFRED vintages, QFSI Real.

## 2. What is blocked vs available without broker re-login

| Lane | Owner broker re-login needed? | Available today? |
|---|---|---|
| QFSI broker ticks / commission / side-referenced slippage | **Yes** (`FivePercentOnline-Real`) | No — probe proves Demo mismatch |
| GVBCI COMEX GC L1/trades | No login, but **paid + license** | Cost quote only; no local data |
| SCFIS segmented customer flow | N/A | Excluded — not possessed |
| Public policy rates / T-bills / yields | No | Yes — free official archives |
| CFTC COT | No | Yes — free public bulk files |
| Public equity index closes (risk proxy) | No | Yes with license/caveats |

## 3. Candidate surfaces (V8 expansion)

### A. G3 policy rates (ECB / BoE / BoJ + Fed)

| Dimension | Assessment |
|---|---|
| Free / lawful? | Yes. Official central-bank open data / public statistical releases. Research reuse with attribution is standard; do not redistribute as a paid product. |
| Reconstructable timestamps? | Yes if stored as **effective-date change events** plus a daily step series built only from known changes (fail closed on missing change dates). |
| Publication lag? | Policy changes are announced with a stated effective date. Use announcement clock + effective date; never backfill a future effective rate into prior bars. |
| Join to EURUSD / GBPUSD / USDJPY without lookahead? | Join on `max(decision_bar_close_utc) >= effective_utc` for the rate in force. Prefer H4/D1 cadence; policy steps are sparse and will not alone hit 2–5 trades/week without a second signal. |
| Next acquisition command / URL | ECB DFR (no key): `https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV?format=csvdata` — also daily level `FM/D.U2.EUR.4F.KR.DFR.LEV`. BoE Bank Rate history: `https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp` (CSV export). BoJ: Bank of Japan “Basic Discount Rate and Basic Loan Rate” / Policy Interest Rate pages under `https://www.boj.or.jp/en/` (store effective dates manually or from official CSV/HTML tables). Fed: NY Fed EFFR / target range pages or FRED `DFEDTARU`/`DFEDTARL`/`EFFR` (see B). |
| Blocker | Sparse step series ≠ complete carry surface. True short-rate differentials still need money-market / T-bill / OIS proxies (surface B). BoJ English table scrape needs a frozen parser + hash receipt. |

### B. FRED / official short-rate and T-bill / OIS proxies (USD leg + mirrors)

| Dimension | Assessment |
|---|---|
| Free / lawful? | Yes for research. FRED Terms of Use allow non-commercial research; free API key is now the reliable programmatic path (unauthenticated `fredgraph.csv` has been returning HTTP 403 for some series). Treasury.gov daily bill/par-yield CSVs need **no** key. |
| Reconstructable timestamps? | Observation date ≠ availability date. Prefer ALFRED vintages for revised series; for market rates (EFFR, DTB3, DGS*) use observation date + documented release lag (often next business day for EFFR/SOFR). |
| Publication lag? | EFFR/SOFR: typically next-business-day publication by NY Fed. T-bill / constant-maturity yields: same-day market observation, published end-of-day / next open depending on series. Freeze: first usable FX bar **after** official publish time in UTC. |
| Join without lookahead? | Build `available_at_utc` column; join FX closed bars with `bar_close_utc >= available_at_utc`. Never use same-calendar-day rate for an earlier London/Tokyo bar unless the publish clock proves availability. |
| Next acquisition command / URL | 1) Register free key once: `https://fredaccount.stlouisfed.org/apikeys`. 2) Pull: `https://api.stlouisfed.org/fred/series/observations?series_id=EFFR&api_key=$FRED_API_KEY&file_type=json` (also `SOFR`, `DTB3`, `DGS2`, `DGS10`, `IRLTLT01GBM156N`, `IRLTLT01JPM156N` as needed). 3) Key-free US bills/yields: `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives` (`bill-rates-*.csv`, `par-yield-curve-rates-*.csv`). |
| Blocker | Soft: free FRED API key creation (not broker login). Hard for “true OIS”: liquid EUR/GBP/JPY OIS histories are often vendor-only; public proxies (policy + T-bill + government yields) are the lawful substitute, not a full OIS book. |

### C. CFTC Commitments of Traders (COT)

| Dimension | Assessment |
|---|---|
| Free / lawful? | Yes. Public U.S. government report; no API key; bulk historical zips on CFTC.gov. |
| Reconstructable timestamps? | Report **as-of Tuesday**; files are labeled by that as-of date. Publication is Friday ~15:30 Eastern (holiday shifts exist). |
| Publication lag? | Standard ~3 business days (Tue snapshot → Fri release). Must honor lag: signal may use Friday release only after 15:30 ET; never treat Tuesday as-of as known on Wednesday. |
| Join without lookahead? | Map contracts: CME FX futures (EUR, GBP, JPY) and optionally rates. Store `as_of_date` and `release_datetime_utc`. Join FX bars with `bar_close_utc >= release_datetime_utc`. Prefer Traders in Financial Futures (TFF) for FX/rates; Legacy as fallback. Cadence is weekly → naturally H4/D1, not M15 scalp. |
| Next acquisition command / URL | Index: `https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm`. Historical compressed: `https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm`. Example TFF futures-only year file: `https://www.cftc.gov/files/dea/history/fut_fin_txt_2023.zip` (repeat year pattern; unzip → `FinFutYY.txt`). PRE/API: `https://publicreporting.cftc.gov/`. |
| Blocker | Weekly lag may starve North-Star 2–5 trades/week if used as sole trigger; better as regime/positioning overlay. Contract-code mapping to spot EURUSD/GBPUSD/USDJPY must be frozen in a later data contract (not done here). |

### D. Public equity-index / bond-yield differentials (capital-flow / risk-on proxy)

| Dimension | Assessment |
|---|---|
| Free / lawful? | Bond yields: yes via Treasury.gov / ECB `YC` / national DMOs. Equity closes: FRED `SP500` is limited history; Stooq/Yahoo are commonly used but ToS/redistribution must be checked before archiving. Prefer official index providers’ free delayed closes when possible. |
| Reconstructable timestamps? | Daily official closes with exchange calendars. Intraday equity L1 is **not** claimed here. |
| Publication lag? | Equity cash close known after local cash close; US equity close ~20:00 UTC (EDT) / 21:00 UTC (EST). Bond yields end-of-day. |
| Join without lookahead? | For Tokyo/London morning FX decisions, use **prior** US/EU cash close only. Freeze session alignment: e.g. D1 FX bar may use T−1 equity/bond close; H4 bars before US close may not see same-day US close. |
| Next acquisition command / URL | US yields: Treasury archives above. Euro-area yield curve: ECB SDMX `YC` dataflow via `https://data-api.ecb.europa.eu/`. Equity: FRED `SP500` / `VIXCLS` with API key, or Stooq daily CSV (license check before commit to evidence tree). |
| Blocker | Easy to collapse into killed “risk-on = risk FX” proxies if the rule is just correlate SPX with EURUSD. Needs an independent mechanism + de-dup vs V2–V7. Equity feed license is the soft compliance risk. |

### E. Explicitly not Owner-independent free acquisitions

- Broker QFSI tick/commission/slippage bundles → need `FivePercentOnline-Real`.
- Databento/CME GC for GVBCI → cost + Category C-2 license confirmation.
- Signed dealer/customer flow / SCFIS → not possessed; still excluded.
- True broker swap/funding history from Demo → wrong server fingerprint; not admissible for the QFSI lane.

## 4. Top 3 Owner-independent acquisition moves (ranked)

These are the cheapest lawful steps that can reopen a **V8 data surface** without Owner broker re-login. They do not waive cost provenance for later Model 0 runs.

1. **CFTC COT TFF bulk pull (FX + financial futures)**  
   Zero registration. Clear Tuesday/Friday lag contract. Directly addresses V7’s “positioning” gap. Store yearly zips under a new hash-bound evidence folder with `as_of_date` + frozen `release_datetime_utc` rules before any probe.

2. **G3 policy + USD short-rate / T-bill archive (ECB SDMX + BoE Bank Rate + BoJ effective dates + Treasury bill/par-yield CSVs; FRED EFFR/SOFR/DTB3 with free API key)**  
   Builds the minimum reconstructable interest-differential surface V7 said price OHLC cannot invent. Prefer Treasury.gov + ECB (no key) first; add FRED key only for EFFR/SOFR convenience.

3. **Public bond-yield differential panel (US Treasury + ECB YC; optional VIX/equity close after license check)**  
   Supplies the “external capital-market” surface named in the V7 reopen list. Join strictly on prior official closes; fail closed on missing days.

## 5. Recommended storage contract (when acquisition is executed)

Suggested root (not created by this inventory):

`03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/`

Per series: raw file + SHA-256 manifest + `available_at_utc` derivation note + license URL. No silent forward-fill across missing observations. No join into an offline probe until a coordinator freezes the join keys.

## 6. Verdict

- Local exogenous carry/COT/yield archives: **absent**.
- Broker-dependent QFSI: **still blocked** (Demo ≠ Real).
- Owner-independent lawful public surfaces: **available today**, with CFTC COT and official rate/yield CSVs as the fastest path to satisfy the V8 data-contract expansion text.
- This inventory grants **acquisition design authority only**, not download execution, not Deep Research submission, and not EA build authority.
