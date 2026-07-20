# HYP-017 - frozen Human Context natural-policy Model 0

## Identity and epistemic boundary

- Hypothesis: `HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017`.
- Parent collection: HYP-016R1 run `20260719_213555`, manifest SHA-256
  `DDA8BF5BD2FAA026979EA5DE88D6CC72B0294992012C5447674141DC44ED969D`.
- Outcome-blind collection result SHA-256
  `BF1D930AEF0B01CAA6E939DD3B3762FFDF39F5585E678B14B626FA6BC35A5873`,
  canonical result SHA-256
  `7D06E9A6A75B2226226DDC44027FE39815A8A448F8875369DE10F8AFB309C284`.
- The parent collected 26,756 unique decisions over 445.479663 elapsed
  calendar weeks (`60.0611/week`) with 99% tester history quality, 100%
  complete context, zero entries and zero lifecycle data rows. The frozen
  natural policy contains 10,715 decisions (`24.0527/week`) and covers both
  directions, London/New-York, and every year 2018-2026.
- No parent report, trade outcome, PnL, commission, MFE or MAE was read before
  this plan was frozen. Older executions of the high-recall control are already
  known, so HYP-017 is diagnostic/design-after-family-history rather than a
  sealed independent holdout. It cannot establish promotion-grade edge.

## Fixed strategy object

The entry opportunity is the existing closed-M5 high-recall sweep/reclaim:

1. During London `07:00-11:00 UTC` or New York `13:00-17:00 UTC`, the just
   closed M5 bar sweeps the latest frozen M5 pivot and closes back through it.
2. Build the existing `human-context-v1` snapshot exactly once at decision
   time from closed M5/H1/H4 data and current executable entry quote.
3. Accept only when snapshot construction is valid and state is exactly
   `EXTERNAL_SWEEP_WITH_ROOM` or `INTERNAL_SWEEP_WITH_ROOM`.
4. Enter at market through the existing fail-closed execution path. Stop stays
   beyond the sweep extreme plus 1.5 pips; target stays 2R. Existing 1R-to-0.5R
   break-even, daily/session flatten, Friday cutoff, position ownership,
   sizing, retcode, stop-geometry and restart protections remain unchanged.
5. Rejected candidates open no order and remain in HumanContext telemetry.

No score, threshold search, weekday/year veto, external-sweep requirement,
trend filter, H1/H4 location cutoff, RR change, or parameter optimization is
permitted.

## Independent clock correction

The collection exposed 752 candidates outside canonical session labels because
the EA applies the European DST calendar in every year while the broker clock
audit independently establishes European DST through 2023 and US DST from
2024. HYP-017 must implement that fixed era-hybrid server-to-UTC convention:

- 2018-2023: EU last-Sunday March/October transitions;
- 2024 onward: US second-Sunday March / first-Sunday November UTC transitions;
- winter offset +2, summer offset +3.

This is a timestamp/session correctness fix bound to canonical
`fivepercent_server_clock.py` SHA-256
`A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`,
not a fitted performance filter. Tests must cover the March gap week in 2023
and 2024 plus summer/winter parity.

## Frozen native run

- Harness: AlphaFactory only; portable FivePercent runtime on D:.
- Exactly one run; role `control`, telemetry tier `trade-only` plus mandatory
  HumanContext sidecar.
- EURUSD M5, Model 0, `2018.01.01` through `2026.07.19`.
- Deposit `100000`, leverage `100`, tester spread `current`, timeout 3600s.
- Preset: `presets/EURUSD_M5_HYP017_HUMAN_CONTEXT_POLICY.set`.
- Key inputs: `InpResearchAutoMode=true`, `InpSignalMode=3`, risk `0.01%`,
  account-DD threshold `100%`, news guard off, max two entries/day, magic
  `5600727`. Every other value equals HYP-016R1.
- Source/version, policy branch, rejection telemetry and clock correction are
  the only permitted source changes. Closed-bar/non-repaint audit is mandatory.

## Economic analysis and terminal rules

- Reconcile every OPEN/final CLOSE lifecycle and entries-opened counter.
- Cadence denominator is elapsed calendar weeks, not active weeks.
- Primary diagnostic cost is lifecycle net minus an additional 1.5 pips
  round-trip per trade; stress uses 2.25 and 3.0 pips. For USD-quoted EURUSD,
  incremental cost is `pips * 10 USD * lots`. This is deliberately conservative
  because tester spread is already embedded and historical spread separation is
  unverified.
- Required economic gates: at least 200 closed trades; 2-5 trades per elapsed
  week; primary cost PF >=1.30; 2.25-pip PF >=1.25; 3.0-pip PF >=1.00;
  primary expectancy >0; max account DD <=8%; at least 6 positive calendar
  years and no single year above 40% of positive profit.
- Also report base tester PF, WR, R/trade, Sharpe/Sortino/Calmar, max DD, CVaR,
  holding time, yearly/session/direction/context-state attribution and paired
  week-block bootstrap CI for mean R/trade. These are diagnostics, not tuning
  inputs.
- Any required gate failure gives terminal
  `KILL_AT_HYP017_MODEL0_NO_STABLE_EDGE`; no threshold/session/RR/year rescue or
  second run. Passing gives only `PASS_DIAGNOSTIC_REQUIRES_FRESH_VALIDATION`.
- Historical broker cost provenance remains failed, therefore
  `promotion_eligible=false` regardless of result. No paper/live attach.

