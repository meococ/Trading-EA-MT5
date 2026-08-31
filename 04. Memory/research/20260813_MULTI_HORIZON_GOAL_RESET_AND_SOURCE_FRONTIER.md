# Multi-horizon goal reset and source frontier closeout

Date: 2026-08-13 (Asia/Saigon)

Authority: Owner goal reset plus locally verified artifacts. Grok Build is
advisory only. This receipt records scope, source capability and pre-outcome
rejections. It does not authorize an EA, a backtest, optimization, validation,
paper trading or live capital.

## Goal reset

The active deliverable is an economically valid XAU/Forex EA, not necessarily
a scalper. A new mechanism may freeze its decision clock on M5, M15, H1, H4 or
D1 when the clock follows the source and causal mechanism. A slower clock does
not erase prior trials or revive a terminal price-only, carry, session or trend
family. Weekend holding remains forbidden; any overnight sleeve needs a frozen
swap, cost and risk contract.

`01. GOAL/GOAL.md` and `05. Playbook/WORKFLOW.md` carry the normative reset.
Historical checkpoint text remains historical.

## Directional-change / intrinsic-time draft

Verdict: `REJECT_DC_AS_RENAMED_BREAKOUT` before source access, hypothesis ID,
code or outcome.

Fixed-percentage directional-change and overshoot events on completed M5 bars
duplicate the existing swing/ZigZag, momentum and breakout neighborhoods. M5
OHLC cannot reconstruct tick-mid extrema or same-bar event order without a
path assumption. The literature's overshoot statement is not a unique trading
sign. Changing the name or timeframe would not create a new information
object.

## CFTC TFF source-only intake

Official yearly compressed TFF files were downloaded without reading prices,
returns, signals, trades or economic outcomes. Directory:

`02. AlphaFactory/data/cftc_tff/official_yearly_zips/`

| File | Bytes | SHA256 |
|---|---:|---|
| `fut_fin_txt_2018.zip` | 458570 | `6843D130A25A17C6248DF67463810F02077EF4EEAFDD629299D21C18F5125E40` |
| `fut_fin_txt_2019.zip` | 454803 | `631B31880D513072AA50D63117C896184DD35DB3CC8FCDD6DEBD80197EE7A661` |
| `fut_fin_txt_2020.zip` | 430721 | `C90D98D94DB708772D669F263FB8061C75F8A7F681BA231FB21247E5C9798E6B` |
| `fut_fin_txt_2021.zip` | 466549 | `5C929991038C70AE2501661B6D442B9E784D3C29D3166CEAC2E21B45AC93D56A` |
| `fut_fin_txt_2022.zip` | 494559 | `94C9C1FDEE9DFBE377A09923DDFE26B88D3460605DD076081F221AD367D88601` |
| `fut_fin_txt_2023.zip` | 506931 | `43C3DBDD4D01FCEEFAD5E457003751CDC0974C7CF46097B322E26E9E2FE44D7A` |
| `fut_fin_txt_2024.zip` | 563591 | `3F00585741A7CF76C207DF640951D644DD91FF22A1106B38CA37A2469C765637` |
| `fut_fin_txt_2025.zip` | 627068 | `2EA0CDA6395F7DD6501C27422BE3763E1F2F5B41B768CFD36B871F092A07D438` |
| `fut_fin_txt_2026.zip` | 431870 | `A4FFCF3BB82606D167B3492C826F2B03CED9DF2A88E292BB9213FA78C464ECEA` |

Each archive contains one `FinFutYY.txt` with 87 columns. The intended FX
contracts found were CAD `090741`, CHF `092741`, GBP `096742`, JPY `097741`,
EUR `099741` and AUD `232741`; NZD is absent. Target-row counts for 2018
through 2026 were respectively `318, 312, 312, 312, 312, 312, 318, 312, 186`
through report date 2026-08-04, with zero duplicate `(contract code, report
date)` keys.

Official references:

- Release schedule: https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm
- Historical compressed files: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
- COT notes and FAQ: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
- TFF field definitions: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/cotvariablestfm.html

Verdict: `CLOSE_CFTC_TFF_AS_NO_HISTORICAL_CLOCK_OR_MECHANICAL_SIGN`.

First fatal contract failure is historical first-public timing. The rows carry
Tuesday report dates, while the ordinary release is Friday 15:30 ET and holiday
weeks may move by one or two days. CFTC does not provide a complete historical
release-datetime list for 2018 onward. Assigning every row Friday 15:30 ET or
`report_date + N` would invent PIT timestamps. Category choice and follow/fade
sign, classification churn, and futures-to-FivePercent spot/CFD identity remain
additional unresolved boundaries. The ZIPs are reusable only as capability
evidence, not as a hypothesis/source archive or live serve contract.

## Official-rate carry and broker financing

The single-pair USDJPY draft used final official EFFR minus the BOJ
uncollateralized overnight call rate, with a Monday entry and Friday exit.
Verdict: `REJECT_CARRY_AS_UNCONDITIONAL_WEEKLY_DRIFT_OR_SERVE_MISMATCH`.

The sign is a persistent policy rank rather than a weekly information event,
so the rule collapses to a Monday-Friday USDJPY direction/calendar sleeve.
The initial 15:00 UTC clock was also earlier than the New York Fed's 14:30 ET
same-day revision close during standard time.

The existing FivePercent zero-order swap-schedule receipt was then re-read:

`03. EA Developer/EA_MultiAssetTSMOMSwapScheduleProbeV1/research/HYP-MULTI-TSMOM-D1-004-SWAP-SCHEDULE-PROBE-001_RESULT.json`

It proves the current mode-1 broker contract only: Monday-Thursday coefficient
1, Friday coefficient 3, weekend zero, and both long and short swap values are
negative on every active FX major. Examples include EURUSD `-9.9/-9.8`, USDJPY
`-13.8/-13.65` and USDCHF `-11.3/-12.8`. It is not historical PIT financing
proof, but it does show that positive official-rate carry cannot be assumed to
arrive as a positive broker credit.

Cross-sectional official-rate ranking is not a fresh escape. The old V8 carry
family already opened weekly, daily and rate-event G3 rank books on EURUSD,
GBPUSD and USDJPY, plus carry-volatility descendants. The weekly terminal
readout had a high diagnostic PF but failed its frozen contract; its outcomes
and all sibling lineage are trial-contaminated. The 2026-08-13 cadence reset
cannot re-score or retime them. Verdict:
`CLOSE_CROSS_SECTIONAL_CARRY_AS_DUPLICATE_AND_SERVE_MISMATCH`.

Grok Build independently returned
`REJECT_CROSS_SECTIONAL_CARRY_AS_DUPLICATE_AND_SERVE_MISMATCH`: the object is
already V8, the goal reset does not clear trial debt, and the broker swap probe
shows an adverse serve contract rather than official-rate carry credit. This
is advisory agreement; the local lineage and swap artifacts are authoritative.

No additional official-rate download is justified without a materially new
information object outside rate rank, rate changes and carry-volatility, plus
a documented historical/live broker financing identity. None is currently
identified.

## U.S. Treasury TIC monthly-flow capability

Official Treasury documentation was checked without downloading a TIC payload
or opening market outcomes. The monthly archive provides a dated ZIP for each
release from 2018 onward, the release calendar identifies the public clock, and
the revision policy covers the prior three months plus annual revisions in the
quarterly release months. The historical/live PIT plumbing is therefore
stronger than the rejected retrospective macro sources.

That capability does not supply a trading sign. TIC is normally released about
one and a half months after the measured month, and the raw signed level in net
foreign acquisition of long-term securities or monthly net TIC flows describes
capital movement that has already occurred. `sign(flow)` is not a new
post-release directional shock, while differencing, thresholding, country
selection or follow/fade choice would manufacture a sign after source intake.
Only about twelve observations per year further weakens any independent OOS
claim. Verdict: `REJECT_TIC_AS_STALE_FLOW_WITHOUT_FORWARD_SIGN_OR_SAMPLE`.

Grok Build independently returned the same verdict and identified stale-flow
semantics as the first fatal boundary. No ZIP download, hypothesis, outcome or
spend was authorized.

Official references:

- Archives: https://home.treasury.gov/archives-of-tic-monthly-data-releases
- Release dates: https://home.treasury.gov/data/treasury-international-capital-tic-system/release-dates-of-tic-data
- Press-release field examples: https://home.treasury.gov/data/treasury-international-capital-tic-system/tic-press-releases-by-topic

## EIA WPSR-only successor audit

The old paired WPSR/WNGSR source attempt was re-read under the new
mechanism-specific cadence rule. WPSR alone has a viable official archive: 417
weekly archive tokens were previously enumerated for 2017-2024, releases are
normally after 10:30 ET Wednesday with published holiday exceptions, and the
weekly tables expose crude-oil stock changes. Removing the obsolete universal
two-events-per-week floor cures cadence administration only; it does not cure
the information contract.

EIA's own market research defines the relevant information as *unexpected*
inventory, typically actual inventory minus the Bloomberg survey expectation.
A raw build/draw can therefore carry the opposite sign from the release
surprise. No free, complete, point-in-time historical expectation archive with
a matching live serve was identified, and substituting raw stock change plus a
next-business-day USDCAD trade would be a stale physical-change proxy with an
additional cross-asset mapping. Verdict:
`REJECT_WPSR_RAW_CHANGE_AS_EXPECTATION_MISSING_OR_POSTHOC_PAIR_RESCUE`.

Grok Build independently returned the same first-fatal boundary. The WPSR
archive remains capability evidence only. No source child, payload, outcome,
MQL5, MT5 run or spend was opened.

Official references:

- Release schedule: https://www.eia.gov/petroleum/supply/weekly/schedule.php
- Weekly report/archive: https://www.eia.gov/petroleum/supply/weekly/index.php
- Inventory/price relationship: https://www.eia.gov/finance/markets/crudeoil/balance.php
- EIA research using actual-minus-expected inventory: https://www.eia.gov/finance/markets/reports_presentations/2017/linn.pdf

## H1 native-indicator frontier after the reset

Six terminal source-only XAUUSD H1 mappings were reconciled from the registry;
none had opened post-event OHLC, an economic trial or MQL5:

| Exact mapping | Raw / executable | Exact-next | Cadence/week | First binding boundary |
|---|---:|---:|---:|---|
| CRSI(3,2,100) extreme re-entry | 1,137 / 1,092 | 96.0422% | 4.1862 | Frozen 97% coverage failed |
| TD9 perfected setup | 555 / 528 | 95.1351% | 2.0241 | Frozen 97% coverage failed |
| Ichimoku full alignment | 453 / 435 | 96.0265% | 1.6676 | Coverage failed; old N/cadence also failed |
| PSAR(0.02,0.20) flip | 2,531 / 2,498 | 98.6962% | 9.5761 | Old upper cadence only |
| Vortex(14) polarity | 2,981 / 2,907 | 97.5176% | 11.1440 | Old upper cadence only |
| WPR(14) extreme re-entry | 3,899 / 3,798 | 97.4096% | 14.5597 | Old upper cadence only |

The reset does not authorize lowering a seen coverage gate for CRSI/TD9/
Ichimoku or opening economics for PSAR/Vortex/WPR merely because the universal
upper cadence cap was removed after their counts were known. A child would
still use the same XAUUSD H1 OHLC-to-indicator transition/extreme information
set; changing period, threshold, timeframe, session, cooldown, exit or risk is
parameter rescue, not an independent source cure. Verdict:
`NO_H1_INDICATOR_CANDIDATE_AFTER_RESET`.

Grok Build independently returned the same compact audit. No seventh native
oscillator/transition is authorized; the lawful frontier remains a materially
different non-price PIT object with a fixed sign, not another OHLC transform.

## SOFR interquartile-dispersion draft

The already-local official New York Fed response contains 1,687 SOFR rows from
2018-04-02 through 2024-12-31 with p1/p25/p75/p99, volume and a revision
indicator. A proposed source-only object would have used the daily change in
`p75-p25` as USD funding fragmentation, selling EURUSD on widening and buying
on narrowing. It was rejected before computing that feature or opening a price.

First fatal boundary is proxy/sign identity. SOFR IQR is dispersion inside the
domestic Treasury-repo market; the cited global-dollar-funding literature does
not prove it is a sufficient EUR-versus-USD funding shock. Distinct columns do
not turn `delta IQR > 0 -> SELL EURUSD` into a mechanical sign. The current API
snapshot and revision flag also do not reconstruct every 08:00 ET original
print. Verdict: `REJECT_SOFR_IQR_BEFORE_SOURCE`; the local response remains
capability-only. Grok Build independently returned the same proxy/sign-first
verdict. No IQR/delta count, 2023+ gate read, hypothesis or outcome opened.

## Grok SonicR QUALITY v10 H1 reset re-audit

The previously downloaded package is locally bound as:

- ZIP SHA256 `77709C82212FACD6DF4F74C31A6EBD1581DEB033DECF60C03EC5C3494EA921DA`;
- MQL5 SHA256 `421E7C58CE8279E1D135459AFE5B9AC777F38D38EF64C4F048A438192B72EA30`.

The multi-horizon reset removes the old M5/M15-only mismatch, but it does not
make the package reproducible. The ZIP omits the claimed Python engine, exact
data/cache, fold assignments and trade ledgers. Its XAU research used a GC
futures/yfinance proxy rather than FivePercent XAUUSD. Static review also found
bar-zero/fail-open HTF use, an out-of-range slope read, double cooldown decay,
bar-zero ATR management, unscoped trade transactions and an unbound UTC-versus-
server session clock. Correcting those defects and adding the mandatory Friday
flat would create a new EA rather than reproduce the claimed object.

The claimed 2023/2024-2026 outcomes and roughly 225 historical trials are fully
seen, so a 2018-2022 backward transfer is neither DESIGN nor an untouched
holdout. Verdict: `REJECT_EXTERNAL_SONICR_REPLICATION_BEFORE_COUNTS`. No local
price, source count, hypothesis, MQL5 child or MT5 run was opened. Grok Build
was then tasked only with recovering the exact omitted frozen bytes and must
return `ORIGINAL_V10_NOT_REPRODUCIBLE_FROM_WORKSPACE` rather than reconstruct
missing evidence.

Grok Build completed that bounded recovery with verdict
`ORIGINAL_V10_NOT_REPRODUCIBLE_FROM_WORKSPACE`. It found current copies of the
four Python modules, summary/comparison JSON, the current quality-pack manifest,
an XAU yfinance cache, full-sample trade JSON and aggregate walk-forward JSON.
It did not find the per-trade OOS ledgers, saved fold windows/embargo assignments,
the original pack/freeze-doc bytes, a standalone timezone/session plus same-bar
SL/TP precedence contract, or proof binding the XAU ticker/cache to the claimed
run. The first fatal gap is therefore unchanged: the claimed PF and sample sizes
cannot be bound to an exact OOS tape. Grok reported an 8,803-byte
`MISSING_EVIDENCE.md` with SHA256
`A95E28F0037BD89D8124E48E52B3D5B24EC8ED6E3262ADE96100C6A9679D6466`;
its chat attachment failed, so the hash/inventory is a remote receipt rather
than a locally possessed artifact. No code, parameter, data, backtest or PF was
created during recovery.

## State after closeout

- Goal: `ACTIVE / UNMET`.
- Active mechanism: none.
- MQL5/compile/backtest opened by this pass: none.
- Outcome or holdout accessed by this pass: none.
- Paid source/service authorization: none.
- Next admissible action: a new zero-outcome source/design object that passes
  novelty, PIT/revision, historical/live identity, mechanical sign, sample and
  cost/serve gates at its mechanism-frozen horizon.

## Revision note - Treasury TIC primary evidence and field intake

Later on 2026-08-13, BIS 75th Annual Report Table V.2 was found to provide an
old-regime total-purchases/USD sign that this receipt had not considered. That
evidence narrows, but does not remove, the TIC mechanism blocker. Official
first-vintage ZIP/header intake then resolved legacy `npr_history.csv` column
`[3]` and the expanded-SLT field map without opening prices. The current scoped
verdict is `REOPEN_SOURCE_ONLY_BUT_HOLD_MECHANISM`; transform, weekend-legal
horizon and modern 16:00-ET announcement evidence remain unresolved. Canonical
revision receipt:
`04. Memory/research/20260813_TREASURY_TIC_SOURCE_GATE_REVISION.md`.
