# Model-0 readout — HYP-UPS-XAU-M5-006

## Verdict

**KILL. Do not trade live and do not tune or rescue this mechanism.**

The exact pre-outcome event-anchored sweep mechanism failed its independent
FivePercent Model-0 research-control run. The first attempt
`20260716_141114` was rejected because the task packet omitted the terminal
include closure; no strategy rule or input changed. After the packet builder
was repaired and dry-run passed with seven bound includes, the deterministic
retry `20260716_141244` completed the research loop. Only the retry is strategy
evidence.

## Identity and operational validity

- Broker/server: `Five Percent Online Ltd` /
  `FivePercentOnline-Real (Build 6006)`.
- Model/window: real ticks Model 0, `2024.01.01–2025.12.25`.
- Source SHA256:
  `CB51EB2A72CBD1567452F6EA33983C5EAB4C32506A6E3A1CD1E47DBFF182A7B8`.
- Compile: zero errors/warnings; exact source plus seven terminal includes:
  non-repaint `PASS`.
- Telemetry: 130 OPEN / 130 final CLOSE, 130 unique positions, zero rows with
  non-positive initial risk.
- Cost evidence: `VERIFIED_RESEARCH_PROXY`, `fill_observed=false`,
  `promotion_eligible=false`.

## Frozen gates versus result

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Completed positions | evidence | 130 | usable |
| Elapsed cadence | 2.0–5.0/week | 1.2569/week | FAIL |
| Tester report PF | diagnostic | 0.7242 | losing |
| Full-cost PF x1.0 | >1.80 | 0.4982 | FAIL |
| Full-cost PF x1.5 | >=1.25 | 0.4129 | FAIL |
| Full-cost PF x2.0 | >=1.00 | 0.3433 | FAIL |
| Report max DD | <=5.50% | 5.4610% | PASS, marginal |
| Monte Carlo P95 DD | <=5.50% | 7.1176% | FAIL |
| Robustness pass rate | >=60% | 0% | FAIL |
| Equity audit | PASS | REJECT | FAIL |

Tester net was `-4,396.90 USD`, expectancy `-33.82 USD/trade`, win rate
`34.62%` and maximum loss streak `11`. After the frozen research cost proxy,
aggregate net was `-33.8428R`.

## Strategy analysis

The structural hypothesis was wrong. Keeping a sweep alive until price
invalidation/session end increased no usable edge. Relative to the separately
valid four-bar research control `HYP-UPSC-XAU-M5-002`, the event-state version
was diagnostically worse on every central measure:

| Measure | Four-bar control | Event-state HYP-006 |
|---|---:|---:|
| Trades/week | 1.3343 | 1.2569 |
| Tester PF | 0.9863 | 0.7242 |
| Tester net USD | -233.83 | -4,396.90 |
| Full-cost PF | 0.6884 | 0.4982 |
| Full-cost net R | -23.0358 | -33.8428 |
| Max DD % | 4.5240 | 5.4610 |
| Monte Carlo P95 DD % | 5.6541 | 7.1176 |

This is a diagnostic comparison, not a promotion-grade matched challenger,
because only research-proxy execution evidence exists. The absolute failures
alone are sufficient to kill HYP-006. Session, weekday, hour and year
breakdowns may not be used to remove weak slices post hoc.

The Unicorn fixed-expiry/event-expiry family is therefore closed. Any future
candidate must be a genuinely new causal hypothesis, preregistered before
outcome, rather than another sweep-age threshold, day/hour veto or score tune.

## Evidence

- Valid run: `02. AlphaFactory/runs/EA_UnicornPrecisionScalper/20260716_141244/`.
- Report SHA256:
  `AF2185806673218FE175E3CE770A3E65DD34D4375DBA211E23C887379042574D`.
- Manifest SHA256:
  `2F12ECC315DF456719C7F3EE792BD598CB2EA3696CE10F93B5655E15BBAA7301`.
- Unified validation SHA256:
  `9015C67BC2F672D4D05175904E69129DE5114C96F1387BAAE595E5C28C9DBF91`.
- Cost artifact SHA256:
  `7142114EC25A86A7F30460FD51FB7D032EBBD8669F902BC2C453DD2A62D3B38F`.
- Non-repaint artifact SHA256:
  `D795729677367BE3BD9E8DEF004C670B0B85FD9EC7ED6FF283B11471A1324CEA`.
- Storage closeout: `evidence/HYP-UPS-XAU-M5-006_STORAGE_CLOSEOUT.md`.
