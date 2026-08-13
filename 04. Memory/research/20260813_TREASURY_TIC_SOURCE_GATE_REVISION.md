# Treasury TIC source-gate revision

Date: 2026-08-13  
Scope: outcome-blind source and mechanism reconciliation only  
Lineage: revision of `REJECT_TIC_AS_STALE_FLOW_WITHOUT_FORWARD_SIGN_OR_SAMPLE`
in `20260813_MULTI_HORIZON_GOAL_RESET_AND_SOURCE_FRONTIER.md`  
Economic authority: none

## Why the old receipt was reopened

The old receipt correctly established point-in-time Treasury archives, the
public release clock, revision risk, the roughly six-week publication lag and
low monthly cadence. It overstated one boundary by saying that no forward sign
was available.

BIS 75th Annual Report, chapter V, Table V.2 supplies older primary evidence:

- sample January 2002 through April 2005;
- dependent variable: daily percentage change in the dollar/euro rate after
  news;
- TIC regressor: month-on-month change, in percent, in net foreign purchases
  of U.S. securities;
- text interpretation: an increase in total purchases was associated with USD
  appreciation, while an increase in official purchases had the opposite sign.

This narrows `no sign exists` to `no unique modern tradable sign/transform/
horizon has been established`. It does not authorize a price test. Source:
https://www.bis.org/publ/arpdf/ar2005e5.pdf, page 6, Table V.2.

## Official outcome-blind intake

Only official Treasury source files and headers were inspected. No FX/XAU
price, event return, EA result or target outcome was opened.

Official archive:
https://home.treasury.gov/archives-of-tic-monthly-data-releases

Official archive description:
https://treasury.gov/resource-center/data-chart-center/tic/Documents/arcdatadesc.pdf

Official release and revision rules:
https://home.treasury.gov/data/treasury-international-capital-tic-system/release-dates-of-tic-data

### Legacy Form S field lock

Both checked legacy ZIPs contain `npr_history.csv`. The first data row is the
newly released month, so reading only that row from the ZIP named for the actual
release date preserves first-vintage semantics.

- ZIP `ticrel_20140916.zip`
  - SHA256 `E7B2F72745286D68B287461BFDA39DD7A818418CE25A6DB327EAC795F33488D3`
  - header column `[3]`: domestic U.S. long-term securities, net purchases by
    foreigners (`gross foreign purchases - gross foreign sales`)
- ZIP `ticrel_20230315.zip`
  - SHA256 `B73248E68127285487090298A3AC358FF84D47DE2DC452AC8F4449E607347FC8`
  - same `npr_history.csv` column `[3]`; first row is January 2023

This is the direct legacy aggregate corresponding to the BIS total-purchases
concept. Country, official/private, line 21/30 and holdings fields are not
substitutes.

### Expanded Form SLT field map

ZIP `ticrel_20230417.zip`, SHA256
`A945D7B381A9EFC5B15035EC75F9C1E234D90AF11649BBE8F9817D4AE16A82EC`,
contains the first February 2023 expanded-SLT release.

- `npr_history.csv` column `[3]` becomes `Domestic L-T Securities, net U.S.
  sales`.
- `slt_table1.txt` exposes the detailed field `for_lt_total_net`, labelled
  `Total U.S. Securities / Net U.S. Sales`.
- Treasury documents a transaction-series break at February 2023 and explains
  that positive expanded-SLT net U.S. sales has the same capital-inflow sign as
  legacy net foreign purchases.

The field mapping is therefore `SOURCE_INTAKE_PASS`. Pooling legacy Form S and
expanded Form SLT in one economic sample remains forbidden.

## Counts-only calendar capability

The official archive page exposes 103 monthly release ZIPs from 2014-09-16
through 2023-03-15. Fifteen release dates were Fridays. Applying the already
authoritative no-weekend-hold rule before any price access leaves 88 calendar
events:

- 2014-2018: 44;
- 2019 through 2023-03-15: 44.

These are source-capability counts only. They do not select a strategy, sign or
horizon and do not establish economic sample adequacy.

## Unresolved mechanism gates

1. `TRANSFORM_UNRESOLVED`: BIS says month-on-month change "in percent" but does
   not give an algebra safe for a signed net-flow denominator. Division by a
   negative prior observation can reverse the meaning, and zero is undefined.
   Difference, absolute denominator, threshold or no-trade rules cannot be
   invented after intake.
2. `HORIZON_UNRESOLVED`: BIS uses a daily return in the old 09:00 Washington
   release regime. It does not define a post-16:00 closed-bar entry/exit window.
   A 24-hour hold can cross a weekend and is forbidden; no replacement horizon
   is manufactured.
3. `MODERN_CLOCK_EVIDENCE_UNRESOLVED`: no primary 2014-09-16+ study was found
   that isolates the 16:00 Eastern TIC announcement effect on EURUSD and binds
   the 2021 lag change plus 2023 methodology break.
4. The roughly six-week lag and about twelve observations per year remain
   supporting weaknesses, not proof that the overall EA goal is infeasible.

## Grok Build reconciliation

Grok first missed the existing local TIC receipt and proposed a weekend-crossing
24-hour rule. After receiving the authoritative lineage and project rule it
withdrew both claims and returned:

`REOPEN_SOURCE_ONLY_BUT_HOLD_MECHANISM`

Its corrected boundary agrees with the local evidence: field intake is
resolvable and now complete; a tradable object remains closed on transform,
horizon and modern announcement evidence.

## Verdict and authority

- Source field/revision clock: `PASS_OUTCOME_BLIND_SOURCE_INTAKE`.
- Tradable hypothesis: `HOLD_PRIMARY_MECHANISM_GAP`.
- Engineering-valid: not evaluated; no EA exists.
- Economic-valid: not evaluated.
- Promotion-ready: no.
- Spend/vendor contact: none.
- Backtest/price outcome: none.

This is a scoped TIC verdict, not a global feasibility verdict. The active goal
remains `ACTIVE / UNMET`, and research must continue in a materially independent
mechanism family rather than relabel this source or stop the goal.
