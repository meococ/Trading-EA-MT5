# HYP-TRENDSTACK-EURUSD-H1-007 — DESIGN Economics Readout

Date: 2026-07-28  
Status: `KILL_EXACT_HYP007_DESIGN_OBJECT`  
Evidence layer: engineering-valid DESIGN economics; not validation, holdout,
Model 0, promotion, paper, or live evidence.

## Decision

Kill the exact frozen HYP007 object. The STACK arm met cadence but failed every
economic, stability, multiple-testing, cost-stress, and relative-discrimination
gate. Validation and holdout remained sealed. No MQL5 implementation or Model 0
run is authorized for this hypothesis.

## Frozen object tested

- EURUSD BID H1 public DESIGN shards only, 2016-01-04 through 2020-12-31.
- One entry opportunity at 12:00 UTC on each eligible DESIGN date.
- Closed-bar M252 and M6 directions with four frozen arms: M252-only, M6-only,
  STACK, and DISAGREE.
- Entry at the 12:00 bar open, 1.0 ATR emergency stop, no take-profit, and exit
  at the same H1 bar close if the stop was not touched.
- Fixed round-trip cost stress at 1.50, 2.25, and 3.00 pips.

## Final metrics

| Metric | STACK result | Gate |
|---|---:|---:|
| Trades | 661 | descriptive |
| Elapsed-week cadence | 2.536732 | 2.0–5.0 PASS |
| PF at 1.50 pips | 0.733245 | >1.30 FAIL |
| PF at 2.25 pips | 0.621044 | >=1.25 FAIL |
| PF at 3.00 pips | 0.527567 | >=1.00 FAIL |
| Mean net R at 1.50 pips | -0.122447 | >=0.08 FAIL |
| Total net R at 1.50 pips | -80.937196 | >0 FAIL |
| Positive DESIGN years | 1/5 | >=4/5 FAIL |
| DSR at 1.50 pips | 0.000160 | >=0.95 FAIL |

Gate total: `1/12 PASS`. All four tested arms were negative after 1.50-pip
cost. M252-only had the best gross mean at about +0.043R, but its average cost
was about 0.132R per trade. STACK gross mean was only about +0.011R and it did
not beat the best standalone arm by either frozen PF or mean-R margin.

## Why it failed

The signal did not create enough directional discrimination for the one-bar
payoff geometry. Roughly 30–33% of observations touched the 1R stop, while
survivors closed with only about +0.45R to +0.49R on average. The small gross
edge of the best arm was overwhelmed by the frozen cost proxy. STACK was net
positive only in 2016 and negative in each of 2017–2020, so the failure was not
caused by one isolated year.

## Failure radius and prohibitions

This verdict kills only the exact M252/M6 direction set, single 12:00 UTC BID
H1 entry/stop/close proxy, 1.0 ATR emergency stop, no-TP geometry, four arms,
and frozen cost/gate contract. It does not prove that all trend, slow-information,
or external-state mechanisms lack edge.

Do not rescue HYP007 by selecting long-only, flipping polarity, changing the
hour or holding horizon, changing stop/target geometry, adding a regime,
session, weekday, or year filter, or choosing a subgroup from this opened
DESIGN readout. A successor requires a materially different point-in-time
information set, fresh hypothesis ID, source audit, preregistration, and gates.

## Engineering audit trail

Attempts 001–003 are preserved as null-market engineering-invalid evidence:
wrong Stage-0 scope, exact `WindowsPath` type rejection, and exact
`pandas.Timestamp` type rejection. No economic conclusion is drawn from them.
Attempt 004 is the only economic verdict. Its load/join contract was separately
preflighted with all economic functions hard-disabled: 1,297 DESIGN rows,
2016-01-04 through 2020-12-31, with validation/holdout access false.

- Final evaluator SHA256:
  `54F4045187751AC7B766845C4E66241448D2E97FE55A96D36DCE98E0218C5731`
- Final tests SHA256:
  `FC11A836BCF35B7E336D7AEB28E7C0F9806DFA4AAA053036E257AC36A6292BDA`
- Focused suite: `111 passed`.
- Input-contract preflight receipt SHA256:
  `C4C20DF8B9BE69B58173123B21CF492A4C24F39239CD423DCF4188181C003BDC`
- Final implementation review receipt SHA256:
  `BF2FF8395542E62E296E762F6C62B9657A18C5CFAE31F889CD362B3F8814C17D`
- Attempt-004 run packet SHA256:
  `FE1ADDD7DE615186013CB48CC503FE52BB881B750E74FADEE44CF953E952570E`
- Attempt terminal SHA256:
  `66E6EC66CFB5F944194F046E047E1D98332425AB0F7C6CBA76A926844A8315A4`
- Gate report SHA256:
  `8D3E9C04C0DE2FEFAFA9825F81F20F3C91C849B786F5F3F8D3A642B26CD3C54D`
- Trade ledger SHA256:
  `B522A53BD2554C1072EB7C9D1A1C1A11236F394C7969723BDF93125D6199D507`

Canonical evidence directory:
`03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-004/`.

## Next legal move

The Owner goal remains unmet. Start a fresh family only after de-duplication and
an outcome-blind source feasibility check. The nearest zero-purchase candidate
is scheduled macro impulse normalization using event timestamps plus the price
response observed after publication. The current local event calendar is
source-rank C and promotion-ineligible, so that route is kill/park-only unless
official point-in-time lineage is later obtained. Price-only fixing/session
variants are already inside a closed failure radius; options-state data would
require a new Owner-approved cost ceiling.
