# Stage-0 readout — HYP-ASRS-EURUSD-M5-001

**Verdict: `PARK_STAGE0_REQUIRED_GATE_FAIL_NO_OUTCOME_READ`**

The exact ASRS report object was reviewed, de-duplicated, frozen, implemented
as an outcome-blind scanner, and executed once on the sealed 2019-2022
FivePercent EURUSD M1 shelf. No MQL5 source, Strategy Tester report, future
excursion, PnL, PF, win rate, MFE/MAE, or 2023+ holdout bar exists.

## What the review changed

The 24-Jul-2026 report is a discovery memo, not evidence that ASRS has an edge.
The adjacent price-only M5 sweep-reversion object was already cost-dominated
(`HYP-ICTVIS-EURUSD-M5-001`). A fresh ID was therefore legal only as a narrow,
falsifiable geometry/information delta:

- mandatory immediate retest and directional rejection;
- sweep-extreme stop buffered by `0.30 * ATR(14)`;
- FivePercent tick-volume surge treated as a broker-specific proxy.

ADX/session filters and the Wyckoff/stop-hunt story were not accepted as
independent evidence. Primary currency-market research on clustered stop orders
supports price cascades, not the report's automatic reversal claim.

## Data and contract integrity

- Frozen plan SHA256:
  `0E6BC15E99E78ACF6D9B5FC88C267CFF685BDEF33855F525450592A0E5BF19D0`
- M1 data SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Development rows: `1,491,312`
- Complete M5 bins: `297,801`; incomplete bins discarded: `682`
- Elapsed calendar weeks: `208.7143`
- Holdout bars loaded: `0`
- Synthetic tests: `5/5 PASS` after an intentional red run (`5 failed`)
- Scanner SHA256:
  `625229B79F595823743704ADCBB4FAB8E7E91E6713DEC762AEB1B3AFACDA3C3D`

## Outcome-blind funnel

| Stage | Count |
|---|---:|
| Confirmed fractal highs / lows | 36,145 / 36,081 |
| ASRS ATR-depth sweeps | 137,199 |
| Same/next-bar reclaims | 39,101 |
| ADX-eligible, all hours | 16,920 |
| ADX + frozen session | 9,111 |
| Tick-volume eligible, all hours | 3,864 |
| Tick-volume eligible, frozen session | 1,770 |
| Mandatory retest/rejection entries | 280 |

Final cadence is `280 / 208.7143 = 1.3415` candidates per elapsed week.
The report's proposed sample floor is feasible at Stage-0, but the workspace
promotion cadence of `2-5/week` is still unmet.

## Geometry result

The new object is materially wider than the killed `4.5`-pip prior:

- initial risk p25 / median / p75: `5.2198 / 7.9482 / 11.5457` pips;
- median cost-in-R at 1.5-pip RT proxy: `0.1887R` (gate `<=0.20R`);
- p75 cost-in-R at 1.5-pip RT proxy: `0.2874R` (gate `<=0.30R`).

These are geometry diagnostics only. The historical spread column is unusable
as cost truth, commission/slippage remain unverified, and no economic result may
be inferred.

## Frozen gate that failed

The tick-volume gate removed `80.57%` of ADX/session candidates, but only
`45.81%` of all volume-qualified events occurred inside the frozen London-NY
session. The plan required at least `50%` so the supposed activity channel would
not be predominantly outside the session claimed by the report.

All other Stage-0 gates passed:

- candidates `280 >= 200`;
- cadence `1.3415 >= 1.0/week`;
- median risk `7.9482 >= 6.75` pips;
- median/p75 1.5-pip cost-in-R gates passed;
- maximum year concentration `29.29% <= 40%`;
- holdout seal passed.

Because every gate was mandatory, the result is PARK. Removing the volume gate,
moving the session wall, changing the volume baseline, or expanding to XAU/GBP
after seeing this funnel would be a new outcome-informed hypothesis, not a
repair of HYP-ASRS-EURUSD-M5-001.

## Known limitation that cannot rescue the verdict

The frozen V1 contract did not consume a pivot after its first sweep. Among 280
final rows there are 225 unique direction+pivot identities; 109 rows belong to
reused pivots (maximum reuse three). This can only make the observed cadence
optimistic. It does not repair the failed volume/session gate and is not amended
post-count.

## Authority boundary

- MQL5 build: **not authorized**
- Model 0 / optimization / WFO / Monte Carlo: **not authorized**
- Economic edge claim: **not available**
- Promotion / paper / live: **not authorized**
- News filter: **UNMET**
- Cost: **UNVERIFIED_PROXY**

The correct next action is stop. A later Owner decision may open a genuinely new
ID with a pre-outcome session/volume contract, but this ID cannot be tuned or
rerun.

