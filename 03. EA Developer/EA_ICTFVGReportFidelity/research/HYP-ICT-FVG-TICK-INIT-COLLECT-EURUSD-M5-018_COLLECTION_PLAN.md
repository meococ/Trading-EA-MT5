# HYP-018 — frozen real-tick initiation collection

## Identity and research boundary

- Hypothesis: `HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018`.
- Parent scaffold: terminal HYP-012 three-bar context state, as retained in
  canonical HYP-017 source SHA-256
  `FF02340C65CBB0E36B1794CB8263023FDD9B7F9218492E749F1F8875C826A5C6`.
- This is a **zero-trade, outcome-blind data-acquisition and de-dup gate**. It
  may establish that a real-tick path field is available, material and dense;
  it cannot establish profitability.
- HYP-012, HYP-014 and HYP-017 remain terminal. This plan cannot change their
  body threshold, timeout, close-location threshold, stop, target, management,
  session, direction or year policy.

## Mechanism under test

The known gap is initiation: sweep/reclaim and available room do not show that
directional price discovery has begun. Primary research reports that FX order
flow is tightly associated with high-frequency returns, while stop-loss order
clusters can generate rapid price cascades. The proposed field is deliberately
weaker than true order flow: it is a broker quote-mid tick-rule path statistic,
not signed trade volume or a limit-order-book measure.

For every existing HYP-012 confirmation, use only ticks belonging to the just
closed confirmation M5 bar:

1. `mid=(bid+ask)/2` when bid and ask are finite, positive and `ask>=bid`.
2. For consecutive valid mids, count `up`, `down`, and `flat`; flats do not
   enter the imbalance denominator.
3. `imbalance=(up-down)/(up+down)` when `up+down>0`; otherwise it is undefined.
4. `sign_agree=true` only for long with imbalance `>0` or short with imbalance
   `<0`. Zero/undefined never agree.
5. Also record valid/invalid tick count, first/last mid, net mid change, total
   absolute mid path, first/last/max spread, exact bar interval, and event ID.

The bar interval is `[bar_open, next_bar_open)`. The first tick of the new bar
must never enter the prior profile. A profile is usable only when its bar-open
identity exactly equals the closed confirmation bar time.

Research motivation:

- C. L. Osler, *Stop-Loss Orders and Price Cascades in Currency Markets*,
  Federal Reserve Bank of New York Staff Report 150 (2002/2005).
- Berger et al., *Order Flow and Exchange Rate Dynamics in Electronic
  Brokerage System Data*, Federal Reserve Board IFDP 830 (2005/2006).
- MetaQuotes MQL5 tester documentation: Model-0 real-tick execution contract
  and tick history are bound by AlphaFactory evidence; the statistic is
  accumulated from `OnTick`, not reconstructed from future bars.

These sources motivate the measurement contract only; they do not prove the
strategy has edge.

## Frozen scaffold and source delta

- Add only signal mode `4`, named `SIGNAL_TICK_INITIATION_COLLECTION`.
- Reuse HYP-012 exactly: latest closed-M5 pivot sweep/reclaim, one setup per
  direction/date/session, maximum three later closed M5 bars, invalidation on
  close acceptance beyond the swept extreme, directional body at least the
  prior-20 mean body, close beyond the opposite sweep-bar extreme, and close
  in the outer directional 25%.
- At confirmation, write HumanContext observation plus one TickInitiation row,
  increment funnel counters, clear the setup, and **do not call any order
  function**.
- `InpResearchAutoMode=false`, telemetry on, news off. Lifecycle data rows and
  entries attempted/opened must remain zero.
- Stop/2R/BE/trailing inputs are retained only so the context snapshot and
  future child geometry stay comparable; they have no economic effect here.

## One authorized collection run

- AlphaFactory portable FivePercent runtime on `D:` only.
- EURUSD M5, Model `0`, `2018.01.01` through `2026.07.19`.
- Exactly one tester collection run after tests, compile, exact-source
  non-repaint audit and a fresh source→EX5→receipt binding.
- Preset:
  `presets/EURUSD_M5_HYP018_TICK_INIT_COLLECT.set`.
- Required sidecars: one LifecycleTrades CSV, one HumanContext CSV, one
  TickInitiation CSV, and one RunMeta JSON, all identity-bound.
- Parser allowlist: identity, model/history/tick counts, lifecycle row count,
  TickInitiation fields and funnel counters. It must not read report PnL, PF,
  WR, DD, commissions, exits, MFE, MAE or any future price label.

## Frozen pre-economic gates

All gates are required:

1. tests pass; compile `0/0`; exact-source non-repaint PASS;
2. Model `0`, one symbol, history quality at least `99%`, and pre-run EURUSD
   `.tkc` coverage spans every requested calendar month available through the
   run end;
3. entries attempted/opened `0`, lifecycle OPEN/final rows `0`;
4. unique event IDs and exact confirmation-bar/profile-bar identity;
5. at least `99%` of confirmation rows have a defined imbalance;
6. sign-agree rows occur at least `2.0` per elapsed calendar week and cover
   both directions, both London/New-York sessions, and every calendar year;
7. materiality: among defined rows, both sign-agree and sign-oppose-or-zero
   shares must each be at least `20%`, pooled and separately for
   `2018-2022` and `2023-YTD`;
8. deterministic parser replay with the same input and seed reproduces the
   same result hash;
9. no outcome field is present in the collection result or parser input
   allowlist.

If any gate fails, terminal verdict is
`KILL_AT_HYP018_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`. No imbalance magnitude,
tick-count, spread, session, year or direction threshold may be mined to rescue
the ID.

## Only legal successor if every gate passes

A separate pre-outcome HYP-019 may compare the unchanged HYP-012 scaffold with
and without the single sign-agreement gate. It must use the same stop, 2R,
management, sessions and risk controls and one frozen Model-0 pair. HYP-018
itself never authorizes economics, paper, live or promotion. Historical cost
provenance remains failed, so any HYP-019 result would remain diagnostic until
that independent blocker is resolved.

