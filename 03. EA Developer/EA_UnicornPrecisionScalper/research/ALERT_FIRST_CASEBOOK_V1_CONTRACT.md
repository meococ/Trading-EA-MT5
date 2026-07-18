# ALERT_FIRST_CASEBOOK_V1 contract

## Status and authority

`DATA_ACQUISITION_ONLY / NO_TRADING_HYPOTHESIS / NO_MODEL0_AUTHORITY`

This contract adds bounded, pre-outcome alert instrumentation to the canonical
post-kill kernel. It does not reopen HYP-006/007/008, change a signal threshold,
authorize an economic backtest, or permit live/paper order mutation.

## Research conclusion before implementation

There is no legally fresh OHLC-only Unicorn candidate in the current evidence
surface. The control, event-state, passive CE entry and RR 1.50 replay are
terminal. Real-yield and broad-USD additions are also terminal locally.

Primary-source mechanism checks support a data-acquisition step rather than a
new trading rule:

- New York Fed research documents clustered stop-loss orders and price
  cascades, but it relies on actual order information; a bar-pattern sweep is
  not equivalent evidence:
  <https://www.newyorkfed.org/research/staff_reports/sr150.html>.
- Cont, Kukanov and Stoikov find short-horizon price impact is more robustly
  related to order-flow imbalance and displayed depth than raw trade volume:
  <https://arxiv.org/abs/1011.6402>.
- CFTC COT data are Tuesday aggregates normally released Friday, so they are a
  weekly positioning input, not an M5 microstructure label:
  <https://www.cftc.gov/MarketReports/CommitmentsofTraders/AbouttheCOTReports/index.htm>.
- CME states DataMine market-depth files reconstruct the order book with
  millisecond timestamps and COMEX futures depth. This is the relevant external
  frontier, but it may not be assumed without an Owner-approved data contract:
  <https://www.cmegroup.com/market-data/files/cme-group-market-depth-faq.pdf>.
- Repeated variants on one historical surface increase false-discovery risk;
  this contract therefore freezes labels before outcomes rather than opening
  another threshold sweep:
  <https://www.nber.org/papers/w20592>.

The Grok 4.5 read-only council independently returned `NO_LEGAL_CANDIDATE` and
ranked the same alert-first casebook as the only useful next action. Its runner
artifacts are under
`.context/unicorn_fresh_causal_research_20260716/`.

## Frozen implementation boundary

- Existing H4/D1, sweep, displacement, FVG, breaker-proxy, score, session and
  management parameters remain unchanged.
- Source contract `UPS_ALERT_FIRST_CASEBOOK_V1_3` retains the v1.22 event-sweep
  invalidation coverage so every completed bar through the decision is checked.
  The 2024-2025 no-outcome identity audit removed zero candidates. V1.3 changes
  engineering safety and casebook lineage only, not the detector identity.
- Casebook is opt-in and can run only while trade mutation is disabled.
- Terminal data path must be on `D:`. `FILE_COMMON` is forbidden.
- Lifecycle telemetry defaults off in the safe alert preset, preventing empty
  trade-log files when no trade mutation is allowed.
- Maximum rows per attachment are bounded by input, default `200`.
- A row is written only at a completed-bar valid-alert decision and before any
  order path.
- The EA writes no PnL, future return, MFE, MAE or outcome label.

## Event schema

Each generated CSV contains:

- identity: schema version, contract id, exact source SHA256, deterministic
  event id, decision UTC, symbol and direction;
- detector context: score, sweep extreme/age, displacement ATR, FVG bounds and
  midpoint, overlap ratio, H4/D1 bias, premium-discount check and spread points;
- blank human-label columns: true sweep, true displacement, MSS/BOS close, true
  breaker validity, fresh unfilled FVG, micro-confirmation, accept/reject,
  reject reason, reviewer id and label time.

## Collection and kill gates

- Do not join any forward outcome before at least `100` independently labeled
  alerts and a separately sealed analysis plan.
- Prefer two reviewers; require predeclared Cohen kappa `>=0.70` on the final
  accept/reject label before using the labels to propose a new hypothesis.
- If accepted density is below `25%`, record a detector-to-memo gap and stop;
  do not lower score or other thresholds.
- Later research gets at most one frozen feature family, one no-outcome density
  probe and one matched Model-0 challenger under a new hypothesis id.
- Any threshold/session/RR/entry change from this collection without a new
  preregistration is invalid.

## Engineering clarification v1.21

The first v1.20 instrumentation build was audited before collection and then
corrected without reading any outcome:

- `sweep_age_bars` now matches the frozen Python definition (`j-left`), so a
  sweep on the FVG left bar has age zero rather than two;
- every casebook has a separate metadata CSV with source-contract id, run id,
  broker/server, terminal build/data path, UTC offset and exact detector inputs;
- rows also record server decision time and the configured UTC offset;
- the new-bar gate rejects missing, repeated and backward timestamps;
- trade-history query failure blocks new risk instead of returning zero state;
- close/modify paths require an accepted broker retcode; same-symbol pending
  orders and a second pre-send spread check block mutation; normalized sizing
  may exceed the declared risk budget by at most one cent, not five percent.

These are engineering and data-lineage corrections only. They do not alter the
frozen detector, authorize a performance run or reopen a killed hypothesis.

## Engineering clarification v1.23

The completed V1.2 collection exposed a provenance gap before human labeling:
the manifest knew the source hash, but the casebook rows and metadata did not
bind it, and the review schema omitted the true-breaker validity label required
by the report-to-code fidelity audit. V1.3 therefore:

- requires a 64-hex expected source SHA256 before casebook initialization and
  writes it into metadata and every row;
- adds a blank `label_true_breaker_valid` column without adding an outcome;
- permits order mutation only inside Strategy Tester and only with both retired
  execution switches enabled;
- fails closed when position, order or history enumeration is incomplete;
- binds broker deviation to declared slippage and reconciles stop-loss money
  risk to actual fill price/volume, immediately closing any overshoot.

V1.2 evidence remains preserved as diagnostic acquisition evidence but is not
valid input to the labeling gate. V1.3 does not change H4/D1 bias, sweep,
displacement, FVG, overlap, score, session, entry, stop, target or management
thresholds and creates no authority for an economic rerun.
