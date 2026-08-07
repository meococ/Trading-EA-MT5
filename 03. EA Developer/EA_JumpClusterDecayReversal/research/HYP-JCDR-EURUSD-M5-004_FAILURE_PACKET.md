# HYP-JCDR-EURUSD-M5-004 failure packet

Status: `KILLED_SOURCE_FEASIBILITY_NO_ECONOMICS_OPENED`

Run: `20260807_164858`

## Decision

HYP004 is terminal. The single authorized fixed-window Model-0 source probe was
consumed. It produced valid outcome-blind evidence but failed five simultaneous
frozen source gates. No threshold, date, route, indicator parameter or geometry
rescue is authorized under HYP004.

This is not a market no-edge verdict. It kills only the exact frozen HYP004
composition and its end-date coverage contract.

## Engineering and data identity

- Exact source SHA256:
  `4C3ED94B29329299DE57FE8C8ABDA247CF30FCAC029533C6B41BBFD03ADE06BE`.
- Compile, focused tests, regression tests, non-repaint audit and independent
  Grok finding-closure review passed before execution.
- Strategy Tester reported `100%` analyzed history quality.
- The original run stopped in AlphaFactory's post-run validator because the
  validator incorrectly required the symbol-wide history envelope first date
  to equal the timeframe-specific M5 first date.
- Bounded journal evidence proves that the symbol envelope is
  `1971.01.04` to `2026.07.30`, while M5 server, M5 terminal, M1 server,
  M1 terminal and exact one-bar CopyTime all agree on epoch `1420189200`
  (`2015.01.02 09:00` in the recorded broker series).
- AlphaFactory was fixed so the broad symbol envelope must cover, rather than
  equal, the exact M5 first date. Regression suite: `56 passed`.
- Artifact-only revalidation of the existing run passed. There was no second
  MT5 launch.

Revalidation receipt:
`02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_164858/analysis/data_quality_revalidation.json`
SHA256:
`02A6BE1628816694F60F915412AC75897A786A6D3908FFEB1332B4698CE6EE11`.

## Frozen source gates

| Gate | Frozen requirement | Observed | Verdict |
|---|---:|---:|---|
| History quality | `>97%` plus journal and series proof | `100%`, proof PASS | PASS |
| No trading | zero trading deals/orders/positions | zero; one initial balance operation | PASS |
| Exact observed window | first `2016.01.04`, last `2020.12.31` | first `2016.01.04`, last `2020.12.30` | FAIL |
| Raw JCDR events | `>=500` | `933` | PASS |
| Routed events | `>=180` | `53` | FAIL |
| Routed cadence | `[0.70,2.00]` per week | `0.20351` | FAIL |
| Long/short balance | `>=80` each | `28 / 25` | FAIL |
| Reversal/continuation balance | `>=80` each | `53 / 0` | FAIL |
| Maximum year share | `<=0.30` | `0.26415` | PASS |
| Matched arms | exactly two adjacent opposite arms | `106` rows / `53` pairs, zero errors | PASS |
| Median stop | `>=6.0` pips | `9.30` | PASS |
| Median 1.5-pip cost/stop | `<=0.25` | `0.16129` | PASS |
| Outcome boundary | no forbidden outcome fields/reads/economics | none | PASS |

The date failure is a frozen tester-end semantics defect: `To=2020.12.31`
stopped at the prior bar (`2020.12.30 23:59:59`). It cannot be repaired by a
same-ID rerun. A successor must preregister an explicit inclusive analysis
window and a wider tester envelope.

## Composition failure

Only `53 / 933 = 5.68%` raw events survived. Outcome-blind dispositions were:

- regime conflict: `404` (`43.30%`);
- unreleased squeeze: `270` (`28.94%`);
- TB stop/corridor geometry: `186` (`19.94%`);
- indicator invalidity: `20` (`2.14%`);
- routed: `53` (`5.68%`).

Within the 53 routed pairs:

- continuation-energy true: `36`;
- AIRD-follow true: `30`;
- QQE-follow true: `19`;
- AIRD and QQE jointly follow: `2`;
- AIRD+QQE joint with continuation energy: `0`;
- energy without AIRD+QQE joint: `36`;
- AIRD+QQE joint without energy: `2`.

The HYP004 hard conjunction therefore joins nearly disjoint indicator states.
It suppresses the entire continuation branch even though energy and individual
momentum signals occur separately. This confirms that indicator roles cannot be
implemented as a single exact Boolean AND without first measuring their causal
stage and temporal alignment.

## Failure radius and successor constraints

The following are reusable:

- JCDR event clock and closed-bar implementation;
- no-trade exporter, paired-arm integrity and no-outcome boundary;
- AlphaFactory fixed-window and artifact-only data revalidation tooling;
- TB protected-stop/corridor geometry and its observed healthy median values;
- native MT5 visual casebook findings about stale episodes, structural
  obstruction and momentum/structure conflict.

The following exact mechanism must not be repeated:

- `AIRD_follow && QQE_follow && energy` as one same-bar continuation gate;
- unconditional unreleased-squeeze abstention without measuring release age;
- a routed-only CSV that hides the pre-route stage of the other 880 events;
- an MT5 `To` date assumed to include the full named calendar day.

A fresh diagnostic hypothesis must remain outcome blind and export every raw
event with: individual predicates, confidence/magnitude, indicator age/change,
pre-geometry route candidate, post-geometry disposition, TB level age, squeeze
age/release age and the exact inclusive analysis membership. Only after that
source passes may a separately preregistered economic EA read outcomes.

## Bound evidence

- Run manifest SHA256:
  `190B1C49EB0AF3A68F2247C01F45ADA3B80083F4D77E7311E472FB9148542342`.
- Report SHA256:
  `8D64977B83B15325210EF7E5E6E06BCBA75D1CCCBD5880D8C89410C34614EBD2`.
- Journal delta SHA256:
  `AA9BA3C3ECDB7F2DB22694111C80DFF2F28FA1BCFD11DEF342505307EB0C1BF7`.
- RunMeta SHA256:
  `2C132AA1CB0E3FBF28326868D9E0FAE139D6C6424F59B211080B6F17F6319103`.
- Role-router CSV SHA256:
  `25E6A2D758DFFC9C4C86B0D82015D5F57F28EA573C322890EB1D43296BAC46E7`.
- Role-router analysis SHA256:
  `204AE3F37E1B0F7257B888F9BA63749F70CB54A45448803CFE5C286C680F463D`.
- Bounded journal search SHA256:
  `C168A7AF0154C94FD31961C82BEA98FEF7F9733FDB4A11754BFCAA3B48D70411`.
- Bounded telemetry index SHA256:
  `9C310BE218AD1D1B6FA381B358896743C89E80899064F0F9FED50C23BA1EF9B4`.

No PF, win rate, PnL, expectancy, optimization, validation, holdout, paper or
live claim was computed or authorized.
