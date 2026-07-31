# HYP-SCC-EURUSD-M5-001 — Stage-0 readout

Verdict:
`PARK_STAGE0_REQUIRED_GATE_FAIL_NO_OUTCOME_READ`

The first and only frozen SCC Stage-0 attempt completed on the sealed
FivePercent EURUSD 2019–2022 design window. The scanner loaded zero 2023+
holdout bars and computed no trade outcome, future excursion, exit, PnL, PF,
win rate, expectancy, balance, equity or drawdown.

## What was tested

SCC is a continuation object, not an ASRS fade:

1. latest N=2 pivot known before the BREAK bar opened;
2. first close-break arm attempt of the UTC date consumes the pivot and date;
3. immediate contiguous HOLD outside the frozen level;
4. first-passage retest acceptance before a close back inside, gap, day change
   or 12-bar expiry;
5. future entry reference is only the next contiguous M5 open;
6. decision-time stop geometry is the BREAK/HOLD/RETEST complex extreme plus
   `0.25 * ATR14_MT5`.

No session, weekday, ADX, volume, HTF, news, FVG, score or direction filter was
used.

## Integrity

- Frozen plan SHA256:
  `6541239D88FFF99D9C8D1E2B3C78645ECE0BE01A69FFCF32BA1620ED6557FA3B`
- Scanner SHA256:
  `2E491B95795F3681AF7FCDD5BDF0A2DFF7C59707F26E137E858E9E5C1C6A7C4F`
- Tests SHA256:
  `C518E1CE02CB9D1A66AFF805DD63A5A3F0ACAFD2D6353E5100E3C8855A74F896`
- Red-first receipt SHA256:
  `FF8A7216A926086FCA00818A42F0C82FED4CCF30F8C0E9EC6D9C869E1E82DD91`
- Result SHA256:
  `B15465AF7B99BC1807550B03D0FA67B057159B0D0143CCA646803FCB2D5AB7CD`
- M1 SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- M1 rows: `1,491,312`
- Complete/incomplete M5 bins: `297,801 / 682`
- Deterministic internal replay: PASS
- Pivot reuse / ambiguous labels: `0 / 0`
- Treatment is a strict subset of the identical raw-BREAK control: PASS
- Accepted entry-reference integrity: `100%`
- Synthetic tests: `7/7 PASS`

## Outcome-blind funnel

| Stage | Count |
|---|---:|
| Confirmed pivot highs / lows | 36,145 / 36,081 |
| Raw first BREAK attempts | 1,242 |
| LONG / SHORT BREAK attempts | 617 / 625 |
| HOLD pass / reject | 878 / 360 |
| RETEST accept | 286 |
| Close-inside reject | 334 |
| 12-bar expiry | 238 |
| Gap / day-boundary reject | 6 / 18 |
| Potential breaks blocked by frozen daily cap | 30,089 |

The large blocked count is not authority to remove the daily cap. That would
change the control population after observing the result.

## Required gates

Eight of twelve gates passed. Four independent necessary gates failed:

| Gate | Frozen threshold | Actual | Result |
|---|---:|---:|---|
| Accepted sample | `>=418` | `286` | FAIL |
| Pooled cadence | `2.00..5.00/week` | `1.3703/week` | FAIL |
| Per-year cadence | `2.00..5.00/week` each year | `1.2274..1.4575` | FAIL |
| Initial risk | median `>=7.50`, p25 `>=5.00` pips | median `3.1866`, p25 `2.1107` | FAIL |
| 1.5-pip cost-in-R | median `<=0.20R`, p75 `<=0.30R` | median `0.4707R`, p75 `0.7107R` | FAIL |

Passing diagnostics:

- LONG / SHORT accepted: `139 / 147`;
- year counts 2019–2022: `71 / 75 / 76 / 64`;
- maximum year share: `26.57% <=35%`;
- `54.90%` of accepts resolved at passage lag `>=2`;
- holdout seal, determinism, identity, outcome-blindness and entry reference
  integrity all passed.

## Interpretation

The categorical path is real and balanced, but it is neither dense enough nor
cost-feasible under the frozen scalp geometry. Its median `3.19`-pip risk means
the declared 1.5-pip round-trip proxy consumes `0.47R` before commission or
slippage. This is a geometry/cadence failure; it is not a market-edge or PnL
result.

Widening the stop, removing the one-attempt/day cap, shortening/lengthening the
12-bar contest, accepting a close inside, adding a session, selecting weekdays,
changing N, or transferring to another symbol after this readout would be
post-outcome rescue of this ID. HYP-SCC-EURUSD-M5-001 is terminal PARK before
MQL5.

## Authority boundary

- `.mq5` source: **not authorized**
- compile / non-repaint audit: **not applicable**
- Strategy Tester / Model 0: **not authorized**
- economics / optimization / WFO / Monte Carlo: **not authorized**
- paper / live / promotion: **not authorized**
- cost: `UNVERIFIED_PROXY`

Any future continuation candidate needs a materially new information contract
or decision surface under a fresh ID; it cannot be a threshold/geometry sibling
of SCC V1.

