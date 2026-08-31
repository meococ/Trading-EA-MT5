# SNB sight-deposit to USDCHF source reconciliation - 2026-08-13

## Scope and evidence boundary

- Source/mechanism-only, outcome-blind audit of one weekly USDCHF object:
  week-over-week change in total sight deposits at the Swiss National Bank.
- Frozen sign under audit: positive change BUY USDCHF, negative change SELL
  USDCHF, zero FLAT. No level, threshold, residual, regime classifier or
  alternate SNB series was permitted.
- No SNB payload, USDCHF price/return/PF, code, compile, MT5 run, backtest or
  purchase was opened.
- Grok Build independently checked official SNB material. Lead reconciled its
  answer against the official publication and implementation descriptions.

## Official object and corrected publication-clock record

- SNB glossary:
  https://www.snb.ch/en/services-events/digital-services/glossary
- SNB data-publication calendar:
  https://data.snb.ch/en/calendar
- The `Important monetary policy data` release is published on the first
  business day of the week and reports the preceding week's data. Current SNB
  calendar records display a 10:00 release time.
- This corrects the July blanket note that treated SNB sight-deposit releases
  as date-only. The inspected calendar does not explicitly label the timezone,
  and a complete historical 2018-latest first-print archive was not established,
  but neither issue is the first fatal gate for this object.
- Total sight deposits are a balance-sheet stock spanning domestic banks plus
  other sight liabilities; they are not labelled weekly FX-intervention flow.

## Mechanism, sign and horizon

- SNB monetary-policy implementation:
  https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/implementation
- SNB repo and monetary-policy operations FAQ:
  https://www.snb.ch/en/services-events/digital-services/faq-overview/qas_repos
- Liquidity-providing repos credit sight deposits. Foreign-currency purchases
  also create CHF sight deposits, but SNB Bills, reverse/liquidity-absorbing
  operations, swaps, standing facilities, government/payment flows and the
  tiered remuneration/minimum-reserve framework can change the same stock.
- Consequently, a positive weekly delta does not uniquely identify an SNB
  foreign-currency purchase or CHF sale. A negative delta likewise does not
  uniquely identify the opposite FX action. Making the proposed polarity work
  would require estimating and subtracting other flows or fitting regime
  filters, which would create a different, post-hoc composite object.
- The release describes the preceding week. Any FX transaction that contributed
  to the balance already occurred and affected the market before Monday's
  publication. No official SNB rule defines a new post-publication USDCHF H4
  or D1 direction ending Friday.
- Weekly cadence could provide ample nominal observations, but it cannot repair
  source-identity, mechanical-sign or causal-horizon failure. The object also
  remains inside the previously screened central-bank-liquidity family.

## Verdict

`NO_SNB_SIGHT_DEPOSIT_CANDIDATE`

First fatal gate: official operating mechanics show that week-over-week total
sight deposits do not uniquely identify FX purchases/CHF sales. Therefore the
frozen sign is not mechanical, and the prior-week publication has no
source-defined post-release USDCHF horizon.

Do not download the cube, substitute quarterly FX transactions or reserves,
or add residual, threshold and regime filters. The corrected 10:00 record must
not be cited as proof of edge. This is a scoped source rejection, not global
infeasibility. No hypothesis or registry row is created. Overall goal remains
`ACTIVE / UNMET`; no market mechanism is active.
