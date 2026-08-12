# Grok Deep Research loop review — 2026-08-11

Status: `RESEARCH_FRONTIER_OPEN`

This checkpoint records research triage only. It does not open a hypothesis,
authorize MQL5, or establish economic evidence.

## Owner objective applied

- Build a closed-bar M5/M15 MT5 EA with real post-cost edge, not an indicator
  showcase or a profitable-looking in-sample report.
- Validate each claimed sleeve independently from 2018 to the latest verified
  data across liquid FX, XAUUSD and BTCUSD before the goal can close.
- Scalping means short/same-day holding and no weekend exposure. It does not
  impose a universal 2–5 trades/week cap; cadence is mechanism-specific.

## Deep Research passes

### Pass 1 — broad microstructure survey

Grok returned `NO_CANDIDATE` but silently reduced native MT5 data to OHLC,
tick volume and time and made an unsupported universal negative. Verdict:
insufficient research packet; no lane opened.

### Pass 2 — native MT5 capability correction

The correction pass examined Economic Calendar values, real Bid/Ask quote paths
and quote-path efficiency. No lane passed all of point-in-time semantics,
closed-M5/M15 decision timing and post-cost evidence. In particular:

- MetaQuotes documents calendar actual/forecast/previous values and server-time
  delivery, but the reviewed documentation does not prove an immutable historical
  release-time consensus/revision tape suitable for a 2018-latest PIT claim.
- Strategy Tester calendar replay requires a frozen exporter/resource contract;
  direct live-calendar calls are not a lawful tester-history substitute.
- Official/academic evidence supports fast FX reaction to macro news, but this
  is not proof of an edge still available at the next closed M5/M15 bar.

Verdict: bounded `NO_CANDIDATE`; no price outcome, MQL5 or MT5 run authorized.

### Pass 3 — corrected scalping cadence

After removing the inherited 2–5/week cap, Grok selected `FX Daily Reopen Gap
Absorption` and claimed about 80% win rate, PF 4.69 after fixed spreads and no
losing years in 2019–2026. Adversarial source audit forced Grok to output
`RETRACT_CANDIDATE` because:

- no accessible primary or peer-reviewed source supported the numerical claims;
- the cited SSRN identity could not be inspected or independently verified;
- 5 pips, 00:05 server and 60–90 minutes were not shown to be preregistered;
- spot FX trades 24/5, so broker 00:00 is primarily a D1/rollover boundary, not
  a universal economic market reopen;
- no broker-independent UTC/DST mapping was frozen.

Local de-dup found no exact daily-gap package, but that does not rescue the
invalid mechanism. A related benchmark-flow detour was also rejected because
the repository already contains the London-fix family and explicit guidance
against relabeling a clock as WMR evidence.

### Pass 4 - source-first institutional constraints

Grok returned bounded `NO_CANDIDATE`. The four screened mechanisms failed
before outcome access:

- dealer inventory/liquidity elasticity required CLS/interdealer volume,
  funding or VaR fields absent from native MT5;
- temporary-impact decay required order imbalance/depth and operated below the
  closed-M5/M15 decision horizon;
- gold market-maker inventory relaxation required client trade/futures hedge
  data outside the allowed information set;
- BTC exchange-reserve pressure required on-chain exchange-reserve history.

Independent source review supported the institutional phenomena but not a
deterministic native-MT5 directional rule surviving at the next closed M5/M15.

### Focused audit - month-end equity-hedging demand

Melvin and Prins (2015) supplied a potentially material distinction from the
repository's clock-only/fixing families: month-to-date country equity returns,
known by the second-last business-day close, as an ex-ante hedge-adjustment
input. The FivePercent terminal exposes `DAX40`, `NAS100`, `UK100` and `ASXAUD`,
so capability was checked rather than dismissed from the old fixing failures.

The focused Grok audit returned `REJECT_PRE_HYPOTHESIS_CAPABILITY`, and local
review agrees, because:

- the accessible source did not expose the complete Eq. (12) alpha formula,
  weights, relative/world component or exact quote/sign convention;
- the available index set is therefore insufficient to claim a faithful paper
  replication rather than a guessed single-index sign rule;
- post-2015 evidence confirms benchmark-fix liquidity/rebalancing activity but
  not persistence of the paper's directional alpha;
- the visible result is gross/statistical, not verified net of executable
  spread, commission and slippage around the fix;
- about one event per month gives only about 100 observations per sleeve over
  2018-2026, inadequate for a strong single-sleeve PF/DSR/OOS claim.

No Stage-0 feature census, MQL5 or target-return backtest is authorized. The
repository also records `EA_Gotobi` as terminal after a time-zone correction
failed to rescue treatment PF, so Tokyo-fix seasonality is not a fresh fallback.

### Pass 5 - native Bid/Ask liquidity-shock decay

The narrow follow-up asked whether measured spread/liquidity withdrawal causes
price pressure that remains reversible only after a closed M5/M15 bar. Grok
returned `REJECT_PRE_HYPOTHESIS_CAPABILITY`; independent review agrees:

- the accessible FX response-function evidence conditions on inferred trade
  signs and documents an average impact path, not a spread-shock-only executable
  predictor;
- the documented temporary-impact and liquidity-replenishment horizons are
  mainly seconds to less than one or two minutes, inside the forbidden shock bar;
- Bitcoin liquidity-shock work predicts liquidity/volatility rather than the
  direction of next-bar return;
- precious-metals evidence describes five-minute liquidity periodicity but does
  not establish a post-shock directional reversal surviving costs;
- adding spread path would distinguish the field set from a return-only fade,
  but without predictive direction it is only a risk/avoidance filter and does
  not justify a new hypothesis.

No source-contract receipt can be completed for this class, so no analyzer,
MQL5 or price outcome is authorized.

### Pass 6 - asymmetric best-quote withdrawal

This pass tested whether one-sided Bid or Ask repricing supplies a directionally
useful information object distinct from quote-count OFI/CVD. Grok returned
`REJECT_PRE_HYPOTHESIS_CAPABILITY`; the receipt failed because:

- Chen and Gau (2014) report relative Bid-versus-Ask price-discovery importance
  on daily EBS EURUSD data, not a next-closed-M5/M15 trading direction;
- the FX response-function paper uses trade-sign response and does not test
  side-specific best-quote withdrawal as the predictor;
- no complete published formula/sign convention or post-2018 FX/XAU/BTC
  confirmation exists at the required decision horizon;
- FivePercent ticks could reconstruct which side of the quote moved, but data
  capability alone cannot replace missing predictive evidence;
- the 2022 FX LOB forecasting result explicitly loses economic gain after the
  bid-ask spread, contradicting a route to executable edge at a slower clock.

The field set is distinct from raw quote counts, but without a supported causal
direction it collapses toward already-terminal generic reversal/jump families.
No analyzer, MQL5 or price outcome is authorized.

### Pass 7 - de-anchored compulsory public information objects

The final pass in this checkpoint allowed free official/public external data at
capability level, while retaining the full source-contract. Grok returned
bounded `NO_CANDIDATE`. The most common fatal gaps were, in order:

1. no immutable historical first-public timestamp/vintage on the released value;
2. no primary evidence for a directional effect beginning after a closed M5/M15;
3. no continuous free revision-aware archive from 2018;
4. no defensible forced-flow mapping and sample size across FX, XAU and BTC.

Near-misses (Fed/ALFRED aggregates, COMEX files, provider-built BTC reserve
series, CFTC/central-bank/LBMA/SOFR disclosures) either repeated a locally sealed
frontier or lacked the clock, directional horizon or cross-universe contract.
No survivor completed the pre-hypothesis receipt, so this checkpoint ends with
no active market mechanism and no outcome access.

### Opportunity-cost audit - historical run catalog

Before opening another external-data lane, the local AlphaFactory run catalog
was used only as an artifact locator, not as economic authority. Across the
required liquid-FX/XAU/BTC universe, the only conspicuous full-window survivors
were `EA_Cobra` on XAUUSD and `EA_LondonNY` on USDJPY. No qualifying BTCUSD,
USDCHF or NZDUSD row existed, and the remaining full-window FX results did not
provide a PF >= 1.30 family that could satisfy the cross-universe goal.

Neither apparent survivor is authorized for revival:

- `EA_Cobra/20260621_173025` reported PF 1.598 over 2018-2025, but its equity
  audit failed: the top 5% of trades supplied 61% of profit, the longest flat
  spell was 725 days, and 30.5% of exits crossed a weekend. The source was
  recoverable only from history and labels several tested constants as
  `OPTIMAL`; its tester news filter silently disables when `news_events.csv` is
  absent. The run manifest does not hash-bind source, account, historical news,
  cost or DST. Grok's focused mechanism audit therefore returned
  `REJECT_REVIVAL_CAPABILITY`; the exact Asian-range/previous-day-level/session
  breakout information set is also not materially distinct from terminal local
  families.
- `EA_LondonNY/20260621_173121` reported PF 2.095 on USDJPY M15, but only 112
  trades over 2018-2025. Its equity audit is `WARN`: the top 5% supplied 52.6%
  of profit, the longest flat spell was 674 days and 16.1% of exits crossed a
  weekend. Thirty-one of 96 months were inactive and gross mean return was only
  0.0989% per month, about 1.1872% annualized. The failure catalog already
  records that cross-pair transfer was killed and that this is a sparse sleeve,
  not a universal or cadence-capable EA.

The catalog audit therefore closes with `NO_REVIVAL_CANDIDATE`. Historical PF
does not override missing source/PIT/cost binding, sample weakness, failed
transfer or the current cross-universe acceptance contract.

A second registry-lineage pass checked every latest non-killed row by
`hypothesis_id`. The apparent `PASS_SOURCE` parents do not represent unfinished
economic candidates: JCDR's pure-reversal child was killed at PF 0.764; G10
weekly cross-sectional momentum was killed at PF 0.814; Round Cascade's exact
execution child reached HYP011 and was killed at PF 0.676; the triangular lane
failed its design structure/cadence before economics. PTR remains data-epoch
collection only. Therefore no source-passed/economic-passed child was abandoned
and available for legal continuation.

### Pass 8 - de-anchored portfolio-host architecture

This pass explicitly removed the assumption that one signal rule must transfer
unchanged across G10 FX, XAU and BTC. Grok returned
`ARCHITECTURE_VERDICT: MULTI_SLEEVE_REQUIRED`, which local review accepts as an
engineering/product interpretation only: one deployable EA may host independent
asset-class sleeves behind shared execution and risk controls. It does not
create expectancy, authorize pooled rescue or weaken any sleeve-level gate.

The capability outcome remained negative in every asset class:

- G10 FX: no new compulsory disclosure or native-MT5 information object had a
  continuous immutable 2018-latest PIT tape plus two exact direction/horizon
  sources after excluding the sealed calendar, fixing, COT/OI/SDR, session and
  quote-flow families.
- XAU: COMEX/LBMA/warehouse objects still lacked the required free immutable
  archive/first-public clock or exact post-closed-bar directional evidence after
  costs; institutional inventory papers require fields unavailable to MT5.
- BTC: difficulty/halving data are public and timestamped but operate at
  multi-day/week horizons with insufficient event cadence, and do not support a
  short-horizon forced-flow direction after a closed M5/M15 decision.

Exact outcome: FX, XAU and BTC each returned
`REJECT_PRE_HYPOTHESIS_CAPABILITY`; final verdict `NO_CANDIDATE`. No analyzer,
MQL5 or MT5 outcome is authorized. The architecture clarification is recorded
in GOAL/WORKFLOW so later research can use genuinely independent sleeves
without manufacturing universal transfer.

### Pass 9 - BitMEX realized-funding BTC sleeve

Full-tree de-dup found no prior BitMEX/Binance funding-rate, perpetual-swap or
post-funding hypothesis, so this was a materially new BTC information object.
The first Grok response incorrectly treated the absence of a bulk immutable
file as fatal. Local verification corrected that failure radius:

- the official public `GET /api/v1/funding` endpoint returned XBTUSD rows at
  2018-01-01 04:00/12:00/20:00 UTC and current rows through 2026-08-11;
- the official schema supports `startTime`, `endTime`, pagination up to 500
  rows, and exposes `timestamp`, `symbol`, `fundingInterval`, `fundingRate` and
  `fundingRateDaily`; a first acquisition can hash responses and audit expected
  three-per-day continuity;
- historical funding rows contain realized funding only. The current instrument
  object exposes `indicativeFundingRate`, but no historical first-public vintage
  tape was proven, so a pre-settlement rule remains illegal.

The corrected focused audit still returned
`REJECT_REALIZED_POST_FUNDING_CAPABILITY`, for economic translation rather than
data availability. He, Manela, Ross and von Wachter analyze perpetual-versus-spot
arbitrage and funding-payment effects, not a pure directional BTC spot/CFD
return beginning after the first closed M5/M15 settlement bar. The older BitMEX
funding-correlation paper uses 8-hour observations and correlation/Granger
analysis, not an executable post-settlement directional rule after costs. No
second independent accessible source replicated the exact residual direction
at the required horizon. BitMEX-perpetual to MT5-CFD basis, settlement-bar
spread/slippage and weekend financing also remain unbound.

Exact failure radius: realized XBTUSD funding is free, dense and locally
source-capable from 2018-latest; it is not evidence that a one-leg MT5 BTCUSD CFD
has post-settlement M5/M15 expectancy. No analyzer, hypothesis, MQL5 or price
outcome is authorized.

### Pass 10 - stablecoin mint/burn liquidity shock

Local de-dup found no exact USDT/USDC mint, burn or treasury-release hypothesis;
the prior stablecoin CEX-premium screen is a different OHLC-residual object.
The on-chain candidate was nevertheless rejected before hypothesis:

- block events are immutable, but a deterministic 2018-latest liquidity-shock
  identity must span Omni, Ethereum and Tron while distinguishing mint to
  treasury, release into circulation, burn/redemption, internal movement and
  chain migration without future wallet labels or double counting;
- Griffin and Shams document concentrated next-hour Bitcoin purchases in the
  2017 Tether episode, while Wei finds grants did not Granger-cause Bitcoin
  returns and Lyons/Viswanath-Natraj attribute issuance mainly to peg arbitrage
  and demand. Ante et al. report positive abnormal returns in a 24-hour event
  window after prior market downturns, not a clean post-M5/M15 causal direction;
- Saggu's 2025 arXiv paper is the only located study claiming a 5-30 minute
  positive BTC response to USDT minting, but it is not an independent
  replication and its stronger effect depends on mutable third-party Whale
  Alert/public-sentiment conditioning;
- no two independent sources support the same pure on-chain event definition,
  direction and residual horizon after the first closed M5/M15 bar and costs.

Verdict: `REJECT_PRE_HYPOTHESIS_CAPABILITY`. The exact failure is causal/PIT
event identity plus conflicting evidence, not the existence of block timestamps.
No wallet threshold, chain selection, analyzer, MQL5 or BTC price scan is legal.

## Current verdict and next contract

- Active hypothesis: none.
- EA/indicator authorized: none.
- Backtest authorized: none.
- Economic verdict: not evaluated.
- Goal status: `ACTIVE / UNMET`.

The next loop must start from a materially different information set and require
direct, inspectable evidence before numerical claims enter a frozen packet. Grok
remains advisory; local source/PIT/de-dup checks decide whether a hypothesis may
open. A truthful `NO_CANDIDATE` remains preferable to coding a broker-clock
artifact and manufacturing a baseline.

## Sources checked

- MetaQuotes `CalendarValueHistory`:
  <https://www.mql5.com/en/docs/calendar/calendarvaluehistory>
- MetaQuotes Economic Calendar functions:
  <https://www.mql5.com/en/docs/calendar>
- MetaQuotes article on calendar replay architecture in Strategy Tester:
  <https://www.mql5.com/en/articles/22196>
- Federal Reserve, exchange-rate reaction to macro announcements:
  <https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm>
- Caporale and Plastun, daily price-gap anomaly study (older and not evidence
  for the retracted server-midnight M15 packet):
  <https://www.tandfonline.com/doi/abs/10.1080/10293523.2017.1333563>
- Huang, Ranaldo, Schrimpf and Somogyi, global FX liquidity/CLS evidence:
  <https://www.sciencedirect.com/science/article/pii/S0304405X22001891>
- Gargano, Ranaldo and Santucci de Magistris, FX volume and next-day reversal:
  <https://academic.oup.com/rfs/article-abstract/35/5/2386/6359835>
- Boudt et al., FX jumps/cojumps and the absence of a clean jump-reversal rule:
  <https://www.sciencedirect.com/science/article/pii/S0378426617302212>
- Henao Londono and Guhr, FX response functions requiring trade-sign response:
  <https://arxiv.org/abs/2104.09309>
- Chen and Gau, asymmetric Ask/Bid quote price discovery in EBS EURUSD:
  <https://www.sciencedirect.com/science/article/pii/S0378426613004056>
- Nakagawa et al., one-minute FX LOB forecast with no gain after spread:
  <https://doi.org/10.1016/j.frl.2021.102517>
- Brauneis et al., Bitcoin liquidity determinants rather than return direction:
  <https://www.sciencedirect.com/science/article/pii/S0927539822000822>
- Batten et al., five-minute precious-metals liquidity stylized facts:
  <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0174232>
- BIS Working Paper 1229, liquidity fragility and sub-M5 impact/replenishment:
  <https://www.bis.org/publ/work1229.pdf>
- Melvin and Prins, month-end equity hedging at the London fix:
  <https://www.sciencedirect.com/science/article/abs/pii/S1386418114000779>
- Goldbach, Nitschka and Ongena, global portfolio rebalancing and FX:
  <https://academic.oup.com/rfs/article/35/11/5228/6574924>
- GFXC/RBA 2020 evidence on benchmark-fix rebalancing flow:
  <https://www.bis.org/review/r201022c.htm>
- Benenchia, Galati and Lepone, post-2015 WM/R representativeness study:
  <https://research-management.mq.edu.au/ws/portalfiles/portal/330182102/325701168.pdf>
- BitMEX official funding-history API:
  <https://docs.bitmex.com/api-explorer/get-funding>
- BitMEX official perpetual-contract funding calculation and clock:
  <https://www.bitmex.com/app/perpetualContractsGuide>
- He, Manela, Ross and von Wachter, perpetual-futures pricing/arbitrage rather
  than a one-leg post-settlement CFD direction:
  <https://arxiv.org/abs/2212.06888>
- Nimmagadda and Ammanamanchi, 8-hour BitMEX funding correlation/Granger study:
  <https://arxiv.org/abs/1912.03270>
- Griffin and Shams, `Is Bitcoin Really Untethered?`:
  <https://onlinelibrary.wiley.com/doi/10.1111/jofi.12903>
- Wei, `The impact of Tether grants on Bitcoin`:
  <https://www.sciencedirect.com/science/article/pii/S0165176518302556>
- Ante, Fiedler and Strehle, stablecoin issuance event study:
  <https://www.sciencedirect.com/science/article/pii/S1544612320316810>
- Lyons and Viswanath-Natraj, stablecoin arbitrage/issuance evidence:
  <https://www.nber.org/papers/w27136>
- Saggu, intraday USDT mint/burn event study (single 2025 arXiv source):
  <https://arxiv.org/abs/2501.05232>
