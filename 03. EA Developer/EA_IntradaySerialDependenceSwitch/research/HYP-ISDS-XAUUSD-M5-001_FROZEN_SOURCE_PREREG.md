# Frozen source prereg — HYP-ISDS-XAUUSD-M5-001

Frozen before reading DESIGN rows or computing serial-dependence events.

## Thesis and novelty

- EA: `EA_IntradaySerialDependenceSwitch`; FivePercent `XAUUSD`, native M5.
- DESIGN: 2018-01-01 inclusive through 2023-01-01 exclusive; outcomes and
  2023+ remain sealed.
- At the completed 15:55 UTC bar, classify the day's intraday path as
  persistent or anti-persistent using the ordinary lag-1 correlation of its
  M5 log returns. Persistent paths continue the final 30-minute move;
  anti-persistent paths fade it.
- This is one path-dependence state switch. It is not indicator voting and has
  no fitted correlation threshold.
- De-dup: DPMO used total tick activity above a prior-session median plus the
  full-session return. ISVA used semivariance and close-location absorption.
  ISDS uses neither volume, full-session direction nor semivariance; its
  information object is return serial dependence plus the terminal 30-minute
  impulse. No matching object exists in the shelf, registry or failure catalog.

## Data and exact daily measurement

- Reuse the exact FivePercent XAUUSD M5 source and validator used by DPMO; no paid data.
- Frozen DPMO dependency SHA256:
  `4DDC3056D2C35B88198A9C1C0734F4746CC3E5BCC37037F8715978AFD443D670`.
- For each UTC Monday–Friday date require exactly the 192 native M5 opens
  `00:00,00:05,...,15:55`, contiguous in UTC and source epoch. Incomplete days
  emit nothing.
- Let `r_i=log(close_i/close_(i-1))` for the 191 intraday intervals.
- Let `x=(r_0,...,r_189)` and `y=(r_1,...,r_190)`. Compute the ordinary
  mean-centered Pearson correlation
  `rho=sum((x-xbar)*(y-ybar))/sqrt(sum((x-xbar)^2)*sum((y-ybar)^2))`.
  A nonpositive/nonfinite denominator fails the day closed.
- `recent_return=log(close_15:55/close_15:25)`, exactly six M5 intervals.

## Exact event

- If `rho>0`, LONG when recent return is positive and SHORT when negative.
- If `rho<0`, reverse that direction: SHORT for positive recent return and LONG
  for negative.
- Exact zero correlation or zero recent return emits nothing. There is no
  magnitude threshold, rolling lookback, alternate impulse window, volume,
  session subset, weekday filter, cooldown or direction deletion.
- Decision is completed 15:55; availability must be the exact 16:00 source row
  at `+300` seconds. Inspect only its timestamp, never price.

## Gates and authority

- DESIGN rows >=300,000; exact-session coverage >=95%; valid-measurement
  coverage >=95% of complete sessions; exact-next >=97%;
- executable N>=500; cadence 2–5/week; each direction >=30%;
- maximum decision-year share <=30%; every year 1.25–6.5/week;
- zero conflicts and deterministic replay.

Sole attempt `ISDS001-SOURCE-001` must claim/fsync before source data access and
persist report, ledger, receipt and terminal. Ledger is limited to clocks,
direction, rho, recent return and completeness; no post-16:00 price, trade,
return, cost or PF.

Any failed gate parks this exact mapping. Do not rescue it with a rho threshold,
alternate recent window, daily subset, session/weekday/direction filter or
symbol/timeframe change. PASS authorizes only unchanged MQL5 build, parity,
compile/non-repaint and one separately frozen untuned baseline. Optimization,
validation, holdout, promotion, paper and live remain closed.
