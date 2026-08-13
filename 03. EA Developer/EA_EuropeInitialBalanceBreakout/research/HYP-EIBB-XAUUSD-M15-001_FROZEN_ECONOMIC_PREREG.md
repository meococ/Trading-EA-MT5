# HYP-EIBB-XAUUSD-M15-001 — frozen untuned economic baseline

Frozen after source PASS and before MQL5 economic results.

## Signal and execution

- XAUUSD EA runs on native M5 and reconstructs M15 from exact M5 triplets.
- Signal is exactly the source preregistered first close outside the completed
  `07:00–07:45 UTC` four-bar initial balance, scanned `08:00–15:45 UTC`.
- Decision and market entry occur at the exact next M15 boundary; a missing
  constituent or clock step fails closed. Maximum one signal per UTC date.
- LONG stop is the completed initial-balance low; SHORT stop is its high.
- Target is fixed `1.50R` from actual requested entry to normalized stop.
- Position risk is 0.10% of current equity, rounded down to broker volume step.
- One owned position maximum; no pyramiding, trailing, break-even or re-entry.
- Time exit after 16 completed M15 bars (48 M5 bars). Always flatten by 20:00
  UTC and before a UTC-date rollover; no weekend hold.
- Daily equity lock 3.5%; peak-equity drawdown lock 8%; a locked signal is
  consumed and counted, never queued.

## Baseline contract

- One untuned Model-0 run through AlphaFactory, XAUUSD M5, preload from
  `2005.01.01`, economic scoring limited to `2018.01.01–2022.12.31`.
- Native tester spread plus commission/swap must be present in the report.
- Engineering gates precede economics: compile 0E/0W, non-repaint PASS,
  runtime failure false, source/runtime raw direction counts reconcile, no
  orphan exposure, and journal untruncated.
- Economic baseline gates: PF >1.30 after report costs; expectancy >0; executed
  cadence 2–5/week; max drawdown <=8%; both directions >=30%; max-year share
  <=30%.
- Only if baseline passes: cost x1.5 PF >=1.25 and x2 PF >=1.00, then freeze
  before validation/OOS. Otherwise kill this exact mapping.

No session, range-size, direction, weekday, stop/target, risk or hold change is
permitted after the baseline readout under this hypothesis.

