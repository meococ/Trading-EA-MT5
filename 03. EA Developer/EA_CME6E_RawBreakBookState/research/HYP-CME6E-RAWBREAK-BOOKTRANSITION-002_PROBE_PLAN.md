# HYP-CME6E-RAWBREAK-BOOKTRANSITION-002 — frozen DESIGN probe plan

Status: **FROZEN PRE-OUTCOME / RESEARCH-ONLY / NO HOLDOUT AUTHORIZED**  
Frozen: `2026-07-27`  
EA package: `EA_CME6E_RawBreakBookState` (no `.mq5`, compile, Model 0,
paper/live or deployment authority)

This V1 plan becomes immutable when its SHA256 is appended to the canonical
candidate registry. Any post-outcome threshold, score, quality, session,
direction, year, cost or geometry change requires a fresh hypothesis ID.

## 1. Identity and falsifiable mechanism

- Hypothesis ID: `HYP-CME6E-RAWBREAK-BOOKTRANSITION-002`.
- Parent price object: the valid raw first-close BREAK control inside
  `HYP-SCC-MT5-REPLICATION-EURUSD-M5-004`, economically killed over 2019-2022
  (`N=1112`, PF `0.69809649`, mean realized R `-0.21561826`).
- Adjacent killed object: `HYP-CME6E-RAWBREAK-BOOKSTATE-001` tested a stale
  two-minute CME book window ending at the M5 break-bar **open** and was validly
  killed. Its chart-forensics clock correction showed that the real decision
  and next-bar entry occur about five minutes later. HYP-001 remains killed;
  this is not a threshold rescue or rerun of that feature.
- Decision symbol/timeframe: EURUSD / closed M5 raw first-close BREAK.
- External source: CME Globex 6E continuous front-volume contract,
  `GLBX.MDP3 / mbp-10 / 6E.v.0`.
- Feature family:
  `raw-first-close-break-causal-cme6e-full-breakbar-book-transition`.
- Distinct mechanism: continuation should be associated with a direction-
  aligned improvement in displayed primary-futures depth from the first minute
  to the last minute of the completed break bar, plus aligned late-bar state
  and full-bar persistence. The feature ends strictly before the actual
  next-bar decision/entry. Entry, stop, target, timeout, sizing and management
  remain unchanged.
- Empirical prior: Cont, Kukanov and Stoikov report that short-interval price
  changes relate more robustly to order-flow imbalance than trade volume alone:
  <https://arxiv.org/abs/1011.6402>. Databento documents MBP-10 as aggregated
  depth/events across the top ten price levels:
  <https://databento.com/microstructure/mbp>.
- Adverse prior: displayed CME depth can cancel, the broker executes spot FX
  rather than 6E, the parent is strongly negative, and the earlier stale-book
  score failed. Default verdict is KILL unless every gate passes.

## 2. Hash-bound source and DESIGN boundary

### Source plane opened outcome-blind

- Owner-approved source plan ID:
  `C57B0AF9CAAB52095629C4D6F3BE449EA23629E02F9FA30C4F54C5CC164A1D1C`.
- Source plan SHA256:
  `BF478C4FF9B181E0BC7C38E55C9613D69B44DBF348CBC351EC0909583E25D7F6`.
- Execution ID:
  `A233093174009674C66D696F6FA8860B4CFF6C7035DC9C67F02916BC956B4EE1`.
- Execution authorization SHA256:
  `EF2E69FF1BF557EDA44E1503922B9487958186270E7813EA63A3C3DB54A6628A`.
- Download manifest SHA256:
  `5E2DFCB42E451104C9C9A941610BE514839C85129BB3E457EAA9BA4B7FC1BC52`.
- Raw validation receipt SHA256:
  `4771964FFA829A152C8F45D91C8F058FC48CCAF63536428B4E52C78B8D4382FB`.
- Acquisition wrapper SHA256:
  `3814D025278F2F7FEE0DB42F4E5CF8FEFBB94D9136C396D0F3832E0C74BB2F4C`.
- Raw result: 565 frozen DESIGN identities; 561 paid, complete and nonempty
  DBN responses; four planned metadata-empty windows; 2,185,882 decoded
  records; 59,883,285 raw bytes. Journal-estimated cost was
  `USD 0.696219488984`, below the Owner ceiling of `USD 1.40`.
- Source-only feature CSV:
  `02. AlphaFactory/data/databento/cme_6e_breakbar_transition_design/book_transition_features_source_only.csv`
  SHA256
  `E8CEA705489AEB3BF684CE0949924BB5FB1D9EAA030779B5E58911F6A7EE2B49`.
- Source-only feature receipt SHA256:
  `6C4E48E1DEE15DE22DD92989DFCB871CF70B110C87C6545C616FE2202C3C389C`.
- Feature extractor SHA256:
  `E1DA8963A05FFFCDF3745E02EB1051B5E54DADCCD998145B3B6DEE6A3DA1402B`.
- Immutable fixed-point book foundation SHA256:
  `34A668CF89FEB9ED5A0D74E41E35B6C6B19E810E5BF6CC02AA6F36EE4FDBC4BB`.
- Frozen parent outcome ledger, not read by the source plane:
  `03. EA Developer/EA_SweepCascadeContinuation/research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/control_trades.csv`
  SHA256
  `07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9`.

### DESIGN boundary

- DESIGN: UTC years 2021-2022, 565 frozen raw BREAK decisions.
- These years were sealed for the materially different HYP-001 stale pre-break
  feature and were never opened under HYP-001. Owner authorization of the fresh
  full-break-bar source plan opens them only as DESIGN for HYP-002. It does not
  amend or rescue HYP-001.
- No holdout, alternate years, symbol, timeframe, source schema or additional
  paid data is authorized. A survivor would require a new preregistration and
  fresh validation data.
- DESIGN elapsed denominator:
  `(2022-12-31 - 2021-01-01) / 7 = 104.14285714285714` weeks.

## 3. Frozen causal feature transform

For each full break-bar window `[break_bar_open, actual_decision)` (564 windows
of 300 seconds and one clock-corrected window of 330 seconds):

1. Keep only valid MBP-10 states with both `ts_event` and `ts_recv` greater
   than or equal to `break_bar_open` and strictly less than
   `actual_decision`. No record at or after the decision is usable.
2. At every retained event, sum bid and ask size over levels 0..4 and compute
   `I5=(bid_size-ask_size)/(bid_size+ask_size)`.
3. Align by raw BREAK direction: BUY sign `+1`, SELL sign `-1`.
4. Compute the aligned median I5 over the first 60 seconds and over the final
   60 seconds. Transition is `late60_median - early60_median`.
5. Compute full-bar persistence as the fraction of aligned I5 observations
   greater than zero. Final-30-second persistence is retained as a diagnostic
   only and is not part of the score.
6. Fixed score:
   `0.50*clip(transition,-1,1) + 0.25*late60_median +
   0.25*(2*full_bar_positive_persistence-1)`.

No feature weight, lookback, level count, clock boundary or sign may change
after outcome access.

## 4. Frozen quality and acceptance surface

A row is quality-eligible only when all hold:

- source is nonempty;
- full-window causal records `>=30`;
- first-60-second records `>=5`;
- final-60-second records `>=5`;
- final-30-second records `>=3`;
- last spread `<=2.0` CME ticks;
- last valid book staleness `<=10,000ms`;
- finite score.

Source-only result before outcome: 516 quality-eligible rows, exactly 258 per
year and 246 BUY / 270 SELL. Exclusive exclusion reasons are fixed: four
metadata-empty, 11 insufficient causal records, one insufficient first-minute
record count, one insufficient final-30-second record count, 11 stale books
and 21 wide/invalid spreads.

The outcome-blind median score is frozen at
`-0.012342488801680875`:

- `CONTROL_QUALITY_ELIGIBLE`: all 516 rows; cadence
  `516/104.14285714285714 = 4.95473251028807/week`.
- `CHALLENGER_TOP50_TRANSITION_SCORE`: score `>=` frozen median, exactly 258
  rows; 2021=133, 2022=125, BUY=133, SELL=125; cadence
  `258/104.14285714285714 = 2.47736625514403/week`.
- `NEGATIVE_CONTROL_BOTTOM50_TRANSITION_SCORE`: score below the median,
  exactly 258 rows; 2021=125, 2022=133, BUY=113, SELL=145.

Ties stay on the challenger side. No weekday, hour, session, year, direction,
news, volatility or outcome-derived veto is allowed.

## 5. Outcome join and cost contract

- The probe may read only the frozen 2021-2022 position IDs in the source plan
  from the frozen control trade ledger.
- Join key is `position_id`; `decision_time`, `open_time` and `direction` must
  match the frozen `break_bar_open`, `actual_decision` and direction contract.
  Any missing, duplicate or mismatched identity PARKS the probe as
  engineering-invalid before economics.
- Native `net` and `realized_r` remain report-bound HYP-004 diagnostics.
- Additional round-trip cost remains `UNVERIFIED_PROXY`, never cost truth:
  for each trade and declared pips `c`,
  `stressed_net = native_net - c*volume*10.0`.
- Required stress readouts: `0.5`, `1.5`, `2.25`, `3.0` pips. Cost tiers are
  not additional trials.
- No exit, stop, target, risk, sizing or management change is simulated.

## 6. Trial accounting and deflation

- Executed trial universe: exactly three arms listed in section 4.
- Primary candidate series: challenger native realized R.
- Per-trade SR = mean(realized R)/sample standard deviation.
- DSR uses `02. AlphaFactory/tools/research/dsr.py` SHA256
  `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`,
  non-excess kurtosis, `V[SR]` across all three arms, `N_trials=3`, floor
  `0.95`.
- Trial rows must use canonical `02. AlphaFactory/tools/research/trial_log.py`
  SHA256
  `DECFBE0A9613A3145075D6EBF247813C0E72679D6314636535D341A0C1934AD3`.
- Year and direction buckets plus cost tiers are diagnostics/gates, not new
  trials. No grid or alternate percentile is authorized.

## 7. Kill gates — all required for DESIGN FLAG

1. Hash, identity, row-count, clock and no-outcome-before-prereg checks PASS.
2. Challenger remains exactly N=258 with cadence `2.00..5.00/week`.
3. Native challenger PF `>=1.30`.
4. Native challenger mean realized R `>=+0.08`.
5. Fixed 1.5-pip stress PF `>=1.25`.
6. Fixed 2.25-pip stress PF `>=1.00`.
7. Both 2021 and 2022 separately have PF `>1.00` and mean R `>0`.
8. BUY and SELL separately have PF `>1.00` and mean R `>0`.
9. Versus quality-eligible control: PF lift `>=0.15` **and** mean-R lift
   `>=0.10`.
10. Versus bottom-score negative control: PF lift `>=0.20` **and** mean-R
    lift `>=0.15`.
11. Challenger DSR `>=0.95` across the exact three-arm universe.

Any valid economic failure is
`KILL_DESIGN_BREAKBAR_BOOK_TRANSITION_NO_POSITIVE_EXPECTANCY`. Any source,
identity, implementation or reconciliation failure is
`PARK_INVALID_BREAKBAR_BOOK_FEATURE_OR_JOIN` and carries no market verdict.

Passing every gate yields only
`FLAG_DESIGN_BREAKBAR_TRANSITION_SURVIVOR_NEEDS_FRESH_VALIDATION`. It does not
authorize MQL5/Model 0, promotion, paper or live trading.

## 8. Mandatory artifacts

- Hash-bound probe script and red-first tests.
- Joined DESIGN trade ledger containing source features plus declared outcome
  fields only after this plan is registry-bound.
- Three-arm metrics, 2021/2022 and BUY/SELL buckets, four cost stresses, DSR,
  gate table and reconciliation receipt.
- Canonical `trials/trial_log.jsonl` rows carrying this hypothesis ID and
  prereg SHA.
- Readout and one terminal/FLAG registry transition.

## 9. Hard exclusions

- No alternate score, weight, level count, clock, percentile or threshold.
- No exclusion beyond the frozen source-quality rules.
- No HOLD/retest, session, weekday, hour, year, direction or chart-pattern
  rescue.
- No reinterpretation of HYP-001; its stale pre-break object remains killed.
- No claim that CME 6E displayed depth is the EURUSD broker's executable book.
- No positive-expectancy, EA-ready or deploy-ready claim from source validity
  alone.
