# Trading Economics NFP to XAU source and mechanism gate

Date: 2026-08-13

Source verdict: `PASS_SOURCE_METADATA_BUT_HOLD_CONTRACT`

Proposed EA verdict: `NO_TE_NFP_XAU_M5_60M_CANDIDATE`

## Frozen scope

- Exactly one commercial information object was screened: Trading Economics
  Economic Calendar historical/PIT plus live U.S. Non Farm Payrolls.
- Proposed sign was frozen before target outcomes: Actual above prerelease
  consensus sells XAUUSD; Actual below consensus buys XAUUSD; equal or missing
  is flat.
- Proposed execution was the first fully closed XAUUSD M5 bar after confirmed
  publication, then a fixed 60-minute hold.
- No API key, signup, trial, purchase, payload, target price, return, PF, code,
  registry row, MT5 run or backtest was opened.

## Official source capability

- Point-in-time documentation:
  https://docs.tradingeconomics.com/economic_calendar/point-in-time/
  explicitly says events can be retrieved as they appeared at the time,
  preserving original values before subsequent revisions, for backtesting
  without look-ahead. The dated country/indicator endpoint is documented.
- Response schema:
  https://docs.tradingeconomics.com/economic_calendar/schema/
  exposes `Date`, `Actual`, `Previous`, `Forecast`, `TEForecast`, `LastUpdate`,
  `Revised`, `Ticker` and numeric value fields. `Date` is release time in UTC;
  `Forecast` is survey consensus; `LastUpdate` is the most recent update or
  insertion timestamp.
- Streaming documentation:
  https://docs.tradingeconomics.com/economic_calendar/streaming/
  exposes the corresponding live fields, including actual, previous, revised,
  date and forecast.
- The NFP ticker is documented as `NFP TCH`, and official examples include NFP
  calendar rows with second-level `LastUpdate` values.

Grok Build first misread the PIT page as non-vintage and reported unsupported
pricing. Lead corrected it against the official pages. Grok's corrected verdict
is `PASS_SOURCE_METADATA_BUT_HOLD_CONTRACT`.

## Contract and live/history uncertainties

- Official current pricing:
  https://tradingeconomics.com/api/pricing.aspx
  lists Standard at USD 149/month billed yearly and Professional at USD
  299/month billed yearly. The lowest displayed commitment is therefore USD
  1,788/year, not a USD 17 probe. PIT is not itemized by plan on that page.
- Official terms:
  https://tradingeconomics.com/terms.aspx
  grant a limited, personal, nontransferable, revocable licence to analyse
  data. The API overview says historical rows may be downloaded and used in a
  custom application, but the public terms do not explicitly grant retention
  of the downloaded PIT tape after cancellation.
- Public documents do not bind a later historical PIT row to the exact first
  live streaming payload by `CalendarId`, publish an ingestion-latency SLA, or
  explicitly confirm uninterrupted `NFP TCH` coverage for every 2018-latest
  release under the Standard plan.
- Those are vendor-contract questions, not evidence that the PIT product does
  not exist. They keep source acquisition on HOLD and prohibit spending.

## Mechanism and horizon gate

The pre-outcome literature supports the proposed polarity but rejects the
proposed retail-M5 timing:

- Elder, Miao and Ramchander, *Impact of macroeconomic news on metal futures*:
  https://doi.org/10.1016/j.jbankfin.2011.06.007
  reports that NFP is among the largest metal-futures announcement impacts and
  an unexpected economic improvement tends to reduce gold and silver prices.
- *The importance of belief dispersion in the response of gold futures to
  macroeconomic announcements*:
  https://doi.org/10.1016/j.irfa.2015.01.017
  reports an almost immediate response that subsides within roughly 90 seconds.
- Earlier intraday work also reports that most futures price adjustment occurs
  within the first minute:
  https://doi.org/10.1016/S0148-6195(00)00029-1

Therefore `Actual > Forecast => SELL XAU` and the inverse sign have a defensible
economic story, but entry only after a fully closed M5 bar arrives after the
documented primary reaction window. Extending the position to 60 minutes is not
supported by the same evidence. Converting the object into pre-positioning,
sub-minute execution, reversal, threshold or regime logic would be a different
hypothesis and is not a repair of this frozen proposal.

## Sample and verdict

Monthly NFP from January 2018 through August 2026 has a theoretical ceiling of
about 104 releases before missing/equal/late-record exclusions. Any honest
DESIGN/validation/holdout split is thin, and it cannot compensate for a timing
mismatch.

The data vendor is not globally rejected: its documented PIT capability is a
real, materially new source class. However, the exact NFP-to-XAUUSD M5/60-minute
proposal fails the mechanism-horizon gate before spend. Contract questions do
not need to be escalated to the Owner for this killed proposal.

Final controls:

- `purchase_authorized=false`
- `hypothesis_authorized=false`
- `economics_authorized=false`
- `live_allowed=false`
- No API trial or vendor contact is required unless a future, materially new
  mechanism first passes an outcome-blind timing and execution gate.

The overall EA goal remains `ACTIVE / UNMET`. This is a scoped rejection of one
commercial source/hypothesis pairing, not a claim that no profitable EA is
possible.
