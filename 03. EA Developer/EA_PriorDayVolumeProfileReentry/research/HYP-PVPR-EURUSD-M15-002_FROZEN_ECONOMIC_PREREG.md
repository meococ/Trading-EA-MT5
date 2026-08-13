# HYP-PVPR-EURUSD-M15-002 — frozen untuned economic baseline

Frozen after the independently reviewed HYP002 source PASS and before MQL5
compilation, tester prices, trades or outcomes are opened.

## Bound source evidence

- Native FivePercent EURUSD M1 SHA256
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- HYP002 source report SHA256
  `1C8303BDEA00787BCFC092A81DB1C10C1047E28E34019351264113CDA72E8097`.
- HYP002 source ledger SHA256
  `629CFEF00E0254D1EFE47F8FA39B531E794D21DFBABD88DA1A5ED0A435216EB2`.
- Source population: 945 events, LONG/SHORT `457/488`, exact-next `100%`,
  cadence `2.5900548/week`, valid-profile coverage `98.7671%`.
- HYP001 is not evidence: its float-boundary PASS was invalidated. HYP002 uses
  only integer five-digit broker points and exact equality never emits.

## Signal and execution

- EA runs on native EURUSD M15. At each new M15 open it consumes only the just
  completed M15 bar; all signal/profile prices are converted with
  `floor(price/0.00001+0.5)`.
- Prior UTC calendar-day profile uses native closed M1 bars, typical price
  `(H+L+C)/3`, one-pip bins, tick volume, deterministic POC tie-breaking and
  adjacent 70% value-area expansion exactly as HYP002 source.
- Only Tuesday–Friday source bars in `[07:00,16:00 UTC)` are eligible. The first
  bar per UTC date that opens strictly outside value and closes inside emits;
  entry is attempted on its exact next M15 open. One signal maximum per date.
- LONG stop is one profile bin below the completed source-bar low. SHORT stop is
  one profile bin above its high. Target is fixed `1.50R` from actual requested
  entry to the outward-normalized stop. Invalid broker geometry rejects once.
- Risk is `0.10%` of current equity, rounded down to broker volume step. One
  position maximum; no pyramiding, trailing, break-even, pending orders or
  re-entry.
- Time exit after 16 completed M15 bars. Always flatten by `20:00 UTC` or UTC
  date rollover; Friday positions cannot be held over the weekend.
- Daily equity lock `3.5%`; peak-equity drawdown lock `8.0%`. Locked signals are
  consumed and counted, never queued. These locks are safety gates, not signal
  filters.

## Sole baseline contract

- One untuned AlphaFactory Model-0 run: EURUSD M15, preload from `2015.01.01`,
  scoring/trading only `2016.01.04` through `2022.12.31`, deposit USD 100,000,
  leverage 1:100, current tester spread, broker commission and swap.
- Engineering gates precede economics: compile `0E/0W`, non-repaint PASS,
  runtime failure false, untruncated journal, source/runtime raw direction
  counts reconcile, and no orphan exposure.
- Economic gates: PF strictly greater than `1.30` after report costs;
  expectancy strictly positive; executed cadence `2–5/week`; max equity
  drawdown `<=8%`; both directions `>=30%`; max calendar-year share `<=30%`.
- Only a full baseline pass may open cost stress, validation/OOS, Monte Carlo or
  paper-forward work. A PF, expectancy, cadence or engineering failure kills
  this exact mapping.

No parameter, session, direction, weekday, stop/target, risk or hold change may
be made after reading the baseline under this hypothesis. No paid data is used.
