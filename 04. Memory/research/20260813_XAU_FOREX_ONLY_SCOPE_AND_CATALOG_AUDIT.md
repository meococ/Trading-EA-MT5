# XAU/Forex-only scope and catalog audit — 2026-08-13

## Verdict

`NO_CANDIDATE / GOAL ACTIVE_UNMET`.

The active universe is `XAUUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`,
`USDCAD`, `AUDUSD` and `NZDUSD`. BTC/crypto is excluded from discovery,
source acquisition, hypotheses, MQL5, backtests, validation and promotion.
Historical BTC records remain audit history only.

No local run or registry lineage currently qualifies for a new Model-0 attempt,
and the bounded Grok Build source-frontier pass found no new information object
that clears all pre-outcome gates. Therefore this checkpoint authorizes no new
hypothesis ID, source spend, code, backtest, validation, paper or live trading.

## Local authority and catalog construction

- Source registry validation: `SOURCE_OF_TRUTH_OK`; the optional unavailable
  backup root does not alter local source status.
- AlphaFactory run catalog rebuilt at `02. AlphaFactory/runs.db`: 499 run
  folders indexed, 123 skipped and zero build errors after completing the
  missing-report audit described below. The catalog is only a locator/de-dup
  surface; original run manifests, reports and research verdicts remain the
  economic authority.
- Tight active-universe query `M5/M15`, at least 200 trades, `PF > 1.30`,
  `DD < 8%` and `TPY >= 104` returned nine rows. All nine are duplicate or
  sibling `EA_SilverBullet` shelf runs. The family is archived, binary-only,
  trial-contaminated and already failed The5ers transfer, so none survived.
- Because current GOAL does not impose a universal two-trades/week floor, a
  second cadence-neutral query removed the TPY condition. It returned 48 rows
  across eight families: `EA_Cobra`, `EA_ITSM`, `EA_Gotobi`,
  `EA_ChopRegime`, `EA_VolCluster`, `EA_ShanghaiFixScalp`,
  `EA_M15SparkAsian` and `EA_SilverBullet`. Every family has an existing
  terminal artifact/failure radius; slower cadence did not reveal an abandoned
  survivor.
- Candidate registry validator exits `1` with 1,473 historical transition,
  serialization and hash-consistency error lines. The registry was not used as a
  broad PASS authority; relevant latest rows and their bound artifacts were
  inspected individually. This checkpoint does not repair or reinterpret
  those historical records.

## Catalog completeness restoration and skipped-report audit

The previous 434/188 catalog count was not a complete locator surface. The
current `runs_db.py` had regressed in four ways: UTF-8 BOM summaries were not
accepted, `run_id` alone was unique across all EA names, runtime path overrides
were absent, and replacing `sys.stdout`/`sys.stderr` broke captured execution.
The catalog tool was repaired without changing any EA or economic artifact:

- summary JSON is read with `utf-8-sig`;
- identity is the composite `EA_NAME/run_id`, while an ambiguous bare timestamp
  fails closed;
- `ALPHAFACTORY_RUNS_DIR` and `ALPHAFACTORY_RUNS_DB` overrides are supported;
- console encoding is reconfigured in place rather than replacing streams; and
- `02. AlphaFactory/tests/test_runs_db.py` covers BOM loading, duplicate
  timestamp preservation, ambiguous-reference rejection and qualified lookup.

Verification is `py_compile` PASS plus `4 passed` under pytest. The real catalog
also preserves timestamp `20260621_170259` for both `EA_ITSM` and
`EA_LondonNY`; no row is silently overwritten.

The complete folder audit then found:

- 622 run folders total;
- 456 pre-existing summaries, including 22 UTF-8 BOM summaries that the old
  loader hid; all 22 were zero-trade source/data/contract probes;
- 166 folders without a summary, of which 140 had a non-empty native report;
- 113 missing-summary reports were inside the active XAU/Forex M5/M15 universe;
- bounded `alpha.ps1 analyze` recovery created 43 valid summaries; and
- the remaining 70 active reports all state `Total trades = 0` in the native
  MT5 report, so no positive-trade EA was lost behind a parser failure.

The final catalog contains 499 indexed runs, 477 positive-trade runs across
126 EA families, 123 skipped folders and zero build errors. This was analysis
of existing reports only: no new MT5 test, price-outcome scan, optimization or
holdout was opened.

Among the 43 newly recovered summaries, the only rows crossing the strict
locator thresholds are additional SilverBullet siblings. The closest distinct
rows still fail before validation: `EA_M15SparkAsian` has 325 trades and
PF 1.3053 but only about 65 trades/year; `EA_UnicornPrecisionScalper` has
157 trades, PF 1.2164 and about 79 trades/year; every other substantive new row
has PF at or below 1.0759. Tiny one- to ten-trade rows are diagnostics, not
economic candidates.

The `TPY >= 104` query above is therefore a locator view, not a new universal
cadence gate. The cadence-neutral audit is authoritative for catalog coverage:

- Cobra is source/trial contaminated, equity-concentrated, weekend-heavy and
  overlaps terminal session/previous-day breakout families;
- ITSM is `KILL_NO_REVIVAL` after independent baselines, WFA and concentration
  review;
- Gotobi failed its timezone-corrected treatment;
- ChopRegime failed untouched OOS;
- VolCluster and ShanghaiFixScalp lack auditable source/cost identity and have
  terminal latest-OOS/WFA evidence;
- M15SparkAsian belongs to the terminal Spark family whose independent runner
  did not clear the PF gate; and
- SilverBullet remains archived/binary-only and failed broker transfer.

No family may be revived by relaxing cadence or selecting a sibling timestamp.

## False-survivor audit

| Local hit | Why it is not a candidate |
|---|---|
| SilverBullet `20260714_194548`, USDJPY M15 | 524 trades, PF 1.378 and about 105/year is only an old shelf seed. Source is no longer active (binary-only), the family has heavy trial debt, and The5ers transfer fell to about PF 1.00. No revival. |
| SonicR `20260701_134204`, XAUUSD M5 | 127 trades, PF 1.398 and about 64/year misses the requested cadence and fails robustness/equity quality: bootstrap PF 95% lower 0.719, negative median, 182-day flat period and extreme winner concentration. Archived, not promotion evidence. |
| EventAggressorFlow `20260812_184117` | Headline PF about 1.73–1.75 on 325 trades, but the frozen exact mapping is terminal: tick decisions at +15/+75 seconds violate the active closed-M5/M15 contract and top-5% gross-profit share 32.4011% exceeded the frozen 30% cap. |
| RegimeStructure `20260807_073820` | Catalog annualization comes from only 12 trades in a short visual-forensics window. The artifact explicitly has no economic authority. |
| MultiAssetTSMOMD1V6 `20260812_110939` | Apparent PF 1.403 was engineering-invalid custom-symbol accounting: FX PnL/spread telemetry was zero because symbol currencies were parsed incorrectly. |
| MultiAssetTSMOMD1V6 `20260812_113422` | Corrected native run is terminal: PF 0.4853467684, net -USD 7,708.23, expectancy -USD 18.01/trade, 0/4 positive years. |
| RoundCascade EURUSD HYP008/HYP010 | These are consumed source/execution parents, not active economic candidates. Descendants HYP009 and HYP011 are respectively parked engineering-invalid and killed economic-no-edge; HYP011 had PF 0.6762 at 1.5-pip cost, mean -0.12339R, total -150.28R, zero positive years, DSR about 1.55e-7 and failed 10/11 gates. |
| SBSparkBook catalog rows | Cadence is adequate but PF is only about 1.22–1.24, below the current minimum. |

Original run evidence is under:

- `02. AlphaFactory/runs/EA_SilverBullet/20260714_194548/`
- `02. AlphaFactory/runs/EA_SonicR/20260701_134204/`
- `02. AlphaFactory/runs/EA_EventAggressorFlow/20260812_184117/`
- `02. AlphaFactory/runs/EA_RegimeStructureFusionForensics/20260807_073820/`
- `02. AlphaFactory/runs/EA_MultiAssetTSMOMD1V6/20260812_110939/`
- `02. AlphaFactory/runs/EA_MultiAssetTSMOMD1V6/20260812_113422/`
- `03. EA Developer/EA_RoundNumberCascade/research/`

## Grok Build bounded source-frontier review

Conversation: `https://grok.com/c/04527241-cd90-4e7f-a3e2-ea182ddbe4c8`

Grok was constrained to pre-source advisory work only: XAU/Forex, zero spend,
no code, no target-price outcomes and no backtest. It returned
`B) NO_CANDIDATE` after considering five materially different objects:

| Object | First fatal gate |
|---|---|
| Official USD/EUR release clock after first closed M5 | Evidence supports a contemporaneous seconds-scale jump, not a same-sign move beginning after the bar and persisting 5–30 minutes; also overlaps the killed event-clock/first-wave radius. |
| CFTC COT/TFF | Weekly positioning, not a 5–30 minute closed-bar object and insufficient cadence. |
| Fed H.4.1 / FiscalData TGA | Daily/weekly policy-liquidity object, not an M5/M15 5–30 minute source. |
| CME ZT/6E post-print mid change | Forbidden cross-asset momentum/lead-lag; sign is not mechanically unique and live CME service is not MT5-only. |
| TBBO same-price size-up versus trades | L1 refill/HYP013 transform; aggregate TBBO lacks MBO identity and the fade-versus-iceberg sign requires empirical outcome selection. |

The Grok conclusion is advisory and was accepted only because it agrees with
the local source/de-dup audit. It is not economic evidence.

## Lawful reopen condition

A new research cell may open only when a materially new information source has
all of the following before outcomes:

1. explicit point-in-time, timezone, revision and cancellation semantics;
2. historical/live identity accessible to an individual user;
3. a deterministic formula and mechanically fixed direction;
4. two inspectable primary or independent sources supporting the same sign
   beginning after a fully closed M5/M15 bar and persisting 5–30 minutes;
5. expected cadence/sample sufficient for train and untouched validation;
6. no overlap with the frozen failure radius; and
7. zero spend, unless the Owner separately authorizes a precise historical and
   live data contract.

An MBO dataset with customer/dealer and open/close identity plus literature at
the exact post-bar horizon could reopen capability review; plain TBBO, another
retime of killed flow, Sonic, option-pin or event-clock logic cannot.

## Authority matrix at close

| Action | Authorized |
|---|---:|
| New hypothesis ID | No |
| New/changed MQL5 | No |
| New MT5 backtest | No |
| Optimization, validation or holdout | No |
| Paid source acquisition | No |
| Paper/live/promotion | No |
| Continue zero-outcome XAU/Forex source-capability discovery | Yes |

No Git command was used for this checkpoint, per Owner instruction. No profit
or edge claim is made.

## Second source-class frontier (structured news, public swaps, gold auction)

A second bounded Grok Build pass was required because the first five-row table
did not prove that these three source classes had been considered. It also
returned `NO_CANDIDATE`. Local review of primary documentation agrees with the
first-fatal-gate verdicts:

| Source class | Local pre-outcome verdict |
|---|---|
| GDELT 2.x Events/GKG | `SIGN_NOT_IDENTIFIABLE`. GDELT 2.0 runs at 15-minute resolution and supplies event/CAMEO, Goldstein and tone fields, but those fields describe reported events and article tone, not a mechanically determined XAU/FX trade side. `DATEADDED` supplies dataset timing; it does not remove news/event-time latency or establish two studies of a same-sign post-closed-bar 5–30 minute move. Any mapping would require a fitted NLP/threshold/direction rule. |
| CFTC Part 43 / DTCC public swap dissemination | `SIGN_NOT_IDENTIFIABLE`. The public regime disseminates transaction/price data while protecting counterparty identities and permits delays for block/large-notional swaps. Current CFTC technical specifications mark buyer/seller and payer/receiver identifiers as not publicly disseminated. An FX swap also contains two currency legs; pay/receive is not initiator/aggressor pressure. No stable closed-M5 directional identity is available. |
| LBMA Gold Price auction | `FORBIDDEN_AND_NOT_ZERO_SPEND`. LBMA confirms two daily auctions, aggregate anonymous bids/offers and a possible terminal imbalance up to 10,000 oz. The object is the already-frozen fixing-clock family; residual imbalance is shared among direct participants, not unique demand. Real-time/historical benchmark use requires IBA licensing, so zero-spend historical/live parity is absent. |

Primary documentation checked:

- `https://www.gdeltproject.org/data.html`
- `https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf`
- `https://www.cftc.gov/LawRegulation/DoddFrankAct/Rulemakings/DF_18_RealTimeReporting/index.htm`
- `https://www.cftc.gov/media/9921/Part43_45TechnicalSpecification12132023CLEAN/download`
- `https://www.lbma.org.uk/prices-and-data/lbma-gold-price/lbma-gold-price`
- `https://www.lbma.org.uk/prices-and-data`

This pass also authorizes no ID, code, backtest, spend or outcome access.

## Third source-class frontier and correction audit

The remaining plausible source classes were audited without outcomes. Grok
initially returned `NO_CANDIDATE`; local primary-source review then found two
factual errors and required a correction pass. Grok accepted both corrections,
and the corrected verdict remains `NO_CANDIDATE`.

| Source class | Corrected local verdict |
|---|---|
| FX/XAU option IV risk reversal/skew | CME states CVOL is derived from option prices, while historical access is through DataMine licensing and live streaming requires enabled/licensed access. This is neither zero-spend historical/live parity nor a non-price object. Call-minus-put IV can reflect hedge premium as well as direction, so a post-bar trade side is not mechanically unique. |
| Official central-bank text | Fed statements/minutes have authentic archives, but there is no official NLP-free hawk/dove side. FOMC has eight scheduled meetings per year and minutes are released three weeks later, far below the required 2–5/week event cadence. Speeches add text but not a frozen mechanical sign. |
| OANDA retail order/position book | Correction: official Forex Labs v1 documentation exposes up to one year of order-book history and 20-minute snapshots for the one-hour period. It therefore has some history, but not the frozen 2018-current coverage. More importantly, crowd-long can be followed or faded only by empirical outcome choice; no mechanical sign exists. |
| Wikimedia pageview attention | Correction: public pageview files are hourly from 2015, not daily-only, and Wikimedia documents definition changes and data-loss periods. Attention increase still has no mechanical XAU/FX direction, any topic/page basket requires selection, and an hourly completed object does not prove a same-sign 5–30 minute move after a closed M5/M15. |
| Gold ETF creations/redemptions/holdings | GLD creates/redeems authorized-participant baskets against gold based on daily NAV determination. This is a daily fund-flow/NAV object, not a 5–30 minute post-bar signal, and is adjacent to the already-closed daily/weekly flow family. |

Primary documentation checked:

- `https://www.cmegroup.com/market-data/cme-group-benchmark-administration/cme-group-volatility-indexes.html`
- `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`
- `https://developer.oanda.com/docs/jp/v1/forex-labs/`
- `https://wikitech.wikimedia.org/wiki/Analytics/Data/Pageviews`
- `https://www.sec.gov/Archives/edgar/data/1222333/000143774925036305/gld20250930_10k.htm`

The correction audit matters: Grok is an advisory search worker, not authority.
Primary documentation and local artifact review control the verdict. No new
hypothesis, code, backtest, spend, outcome access or promotion is authorized.

## Fourth source-class frontier and Treasury correction audit

After catalog completion, Grok Build audited three additional official source
surfaces. The initial `NO_CANDIDATE` verdict was directionally correct, but its
first Treasury-auction reason was not: TreasuryDirect publishes competitive
results in real time as soon as available, and Treasury reports 444 public
auctions in 2025. A first fully closed M5 after release is clock-feasible and
raw cadence is not automatically deficient. Lead required a correction before
accepting the frontier verdict.

| Source class | Corrected local pre-outcome verdict |
|---|---|
| U.S. Treasury auction tail / bid-to-cover | `NO_CANDIDATE_SOURCE_IDENTITY_SIGN_AND_DEDUP`. A true auction tail is the auction high yield minus the pre-auction when-issued yield. TreasuryDirect/FiscalData expose auction results, history and fields such as high yield, bid-to-cover and bidder allocations, but not the PIT secondary-market WI benchmark or an identical live WI feed. Bid-to-cover or indirect-take alone requires an expected/normalization rule and does not mechanically fix an XAU/FX side. Available high-frequency work concerns Treasury yields/order flow, not two same-sign XAU/FX studies beginning only after the first closed M5/M15 and lasting 5–30 minutes. Without official WI this also collapses into the already-closed event-clock or cross-asset rates-to-FX families. |
| Japan official FX-intervention ledger | `NO_CANDIDATE_NOT_LIVE_PIT`. Japan MoF publishes total intervention amounts monthly and detailed date/amount/currency data quarterly. Those are after-the-fact releases, not a live intervention timestamp usable at a closed M5. Low event count is secondary evidence, not the fatal gate. |
| COMEX gold registered/eligible stocks and delivery notices | `NO_CANDIDATE_HORIZON_AND_SIGN`. CME labels the metal notices/stocks as daily and the depositories update registered/eligible inventory daily. This is not an intraday 5–30 minute post-bar object; stock or delivery changes also do not mechanically determine XAUUSD direction without an empirical mapping. |

Primary documentation checked:

- `https://www.treasurydirect.gov/auctions/announcements-data-results/announcement-results-press-releases/auction-results/`
- `https://www.treasurydirect.gov/auctions/`
- `https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/`
- `https://www.mof.go.jp/english/policy/international_policy/reference/feio/index.html`
- `https://www.mof.go.jp/policy/international_policy/reference/feio/index.html`
- `https://www.cmegroup.com/solutions/clearing/operations-and-deliveries/nymex-delivery-notices.html`

Grok accepted the Treasury clock/cadence correction and returned
`CORRECTED_NO_CANDIDATE` for the actual missing-WI, sign, exact-horizon and
de-dup failures. A second correction removed the obsolete universal
two-to-five-trades/week floor. Grok returned
`CADENCE_CORRECTED_NO_CANDIDATE`: Treasury still fails source/sign/de-dup,
Japan intervention still fails live PIT, and COMEX stocks still fail horizon
and sign. No candidate ID, source acquisition, outcome access, EA, backtest,
validation or spend is authorized from this pass.

## Fifth source-class frontier: scheduled institutional forced flow

The next cadence-neutral Grok Build pass inspected five scheduled-flow
surfaces. Primary documentation was checked locally before accepting the
bounded `NO_CANDIDATE`:

| Surface | Local pre-outcome verdict |
|---|---|
| Central-bank USD liquidity tenders / swap-line operations | `SIGN_NOT_IDENTIFIABLE`. Official allotment records can be timestamped and expose fixed-rate tender, total bid, bidders and allotted amount; an example is 100% allotment. High take-up can mean funding stress, policy backstop demand or both and does not mechanically determine EURUSD/XAUUSD side after a closed bar. |
| Japan MoF weekly International Transactions in Securities | `HORIZON_AND_AGGREGATION_FAIL`. The release is a weekly aggregate published at 08:50 JST on a later business day, and historical rows can be revised. It cannot identify a transaction-time 5–30 minute flow after a closed M5/M15. |
| Public equity/bond index review changes | `SIGN_NOT_IDENTIFIABLE`. Public effective dates exist, but the corresponding currency demand requires non-public or assumed AUM, investor base and hedge ratios. Effective-close execution also overlaps the fixing/event-clock radius. |
| WM/Reuters or peer benchmark order/rebalance data | `FIXING_DEDUP_AND_SOURCE_FAIL`. This is the already-closed fixing family, while the usable order/tape surface is licensed rather than a zero-spend individual 2018-current historical/live source. |
| CME FX quarterly roll/delivery | `SIGN_NOT_IDENTIFIABLE`. CME defines a calendar spread as simultaneous selling of one expiry and buying another in the same pair. Rolling preserves/relocates an existing exposure; without owner/hedge identity it creates no mechanically forced spot-FX side, and OI is end-of-day. |

Primary documentation checked:

- `https://www.bundesbank.de/en/tasks/monetary-policy/open-market-operations/outstanding-open-market-operations/fx-liquidity-providing-operation-allotment-987826`
- `https://www.mof.go.jp/english/policy/international_policy/reference/itn_transactions_in_securities/schedule.htm`
- `https://www.mof.go.jp/english/policy/international_policy/reference/itn_transactions_in_securities/index.htm`
- `https://www.msci.com/index-methodology`
- `https://www.cmegroup.com/articles/faqs/frequently-asked-questions-cme-fx-futures-calendar-spreads.html`

No universal cadence floor was used. Every row fails independently at source,
aggregation, sign, horizon or de-dup, so no counts run, hypothesis, MQL5,
backtest, validation, source spend or promotion is authorized.

## Current FivePercent DOM source-quality audit

The previously known live DOM-shaped capability was rechecked on all eight
active XAU/Forex symbols before deciding whether a prospective database was
worth building. The terminal was connected with `trade_allowed=false`; all
subscriptions succeeded and every one of 160 bounded polls contained both book
sides.

The decisive source failure is size identity: every level of every sampled book
used the exact same volume value, `100000000`. Across 267–300 sampled rows per
symbol there was only one unique size. Prices and row counts changed, but the
stream supplied no cross-level or time-varying quantity information.

Verdict:
`KILL_CURRENT_FIVEPERCENT_DOM_SIZE_INFORMATION / PRICE_LADDER_ONLY`.
No passive collector was built because it would persist a synthetic constant
size field, could not backfill the required history and would reduce to the
already-closed quote-path/price-geometry family. Detailed receipt:
`04. Memory/research/20260812_FIVEPERCENT_LIVE_DOM_CAPABILITY.md`.

This does not claim that every broker DOM is useless. Reopen only after a source
contract change and a fresh outcome-blind proof of non-constant size, stable
units, provenance and historical/live identity.

Grok Build independently agreed that `Delta size` is identically zero under the
observed placeholder field, multi-level price is only quote geometry and future
polls cannot manufacture 2018 history or historical/live size identity. Grok's
agreement is advisory; the local connected-terminal probe controls the verdict.

### Other local MT5 source surface

The only distinct local terminal is MetaQuotes-Demo. A controlled hidden probe
found variable book sizes on all seven FX majors and multiple cross-level XAU
sizes; terminal depth was 32, every poll was two-sided and trading was disabled.
This is technically better source telemetry than FivePercent's constant
placeholder field, but it remains `NO_CURRENT_DOM_CANDIDATE`:

- MetaQuotes-Demo has no historical DOM store or Strategy Tester replay;
- it cannot provide the frozen historical evidence window;
- it is not the intended deployment broker; and
- its variable size semantics do not exist on FivePercent, so train and serve
  identities diverge.

No prospective collector was built because it would be future research
infrastructure rather than movement toward the current promotion goal. The
local host has no third configured broker source. A DOM lane may reopen only
after the intended deploy venue supplies varying, documented sizes and a
replayable archive, or Owner explicitly changes both venue and evidence window.
