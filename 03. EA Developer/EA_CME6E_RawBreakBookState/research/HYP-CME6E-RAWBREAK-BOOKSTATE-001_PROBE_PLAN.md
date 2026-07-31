# HYP-CME6E-RAWBREAK-BOOKSTATE-001 — frozen DESIGN probe plan

Status: **FROZEN PRE-OUTCOME / OOS SEALED / RESEARCH-ONLY**  
Frozen: `2026-07-27`  
EA package: `EA_CME6E_RawBreakBookState` (no `.mq5`, compile, Model 0,
paper/live or deployment authority)

This V1 plan becomes immutable when its SHA256 is appended to the canonical
candidate registry. Any post-outcome threshold, score, quality, session,
direction, year, cost or geometry change requires a fresh hypothesis ID.

## 1. Identity and falsifiable mechanism

- Hypothesis ID: `HYP-CME6E-RAWBREAK-BOOKSTATE-001`.
- Parent: the valid price-only raw first-close BREAK control inside
  `HYP-SCC-MT5-REPLICATION-EURUSD-M5-004`, which was economically killed over
  2019-2022 (`N=1112`, PF `0.69809649`, mean realized R `-0.21561826`).
- Decision symbol/timeframe: EURUSD / closed M5 raw first-close BREAK.
- External source: CME Globex 6E continuous front-volume contract,
  `GLBX.MDP3 / mbp-10 / 6E.v.0`.
- Feature family:
  `raw-first-close-break-causal-cme6e-mbp10-five-level-book-alignment`.
- Distinct mechanism: the parent uses price-only BREAK timing. This object asks
  whether persistent, direction-aligned primary futures depth immediately
  before that same frozen decision separates continuation from false breaks.
  It is not a HOLD/retest amendment and does not change entry, SL, TP, timeout
  or trade management.
- Empirical prior: Cont, Kukanov and Stoikov report that short-interval price
  changes relate more robustly to order-flow imbalance than trade volume alone:
  <https://arxiv.org/abs/1011.6402>. Databento documents MBP-10 as aggregated
  depth and events across the top ten price levels:
  <https://databento.com/microstructure/mbp>.
- Adverse prior: the cited study is equities, not EURUSD/6E; displayed futures
  depth can cancel, the spot execution venue is different, and the parent edge
  is strongly negative. Default verdict is KILL unless every gate passes.

## 2. Hash-bound source and sealed split

### DESIGN source, opened outcome-blind

- Source plan ID:
  `1825DC77A35F2794051BD83E5A35ED87C8952049FB08B47BEA1AF34E1802D98F`.
- Source plan SHA256:
  `B780B7A4AD0F0C8B7CDF6A109DE41754C5F9CD88856D464085EE69513A1E24D5`.
- Download manifest SHA256:
  `7C83A964551B7A1F82E483173879A4468A076DA1D2D823E8C8F99A8A3034D38F`.
- Raw validation receipt SHA256:
  `DC383862412E22652FBAA48365CB64D2453200C2727EF1B23AEFFEDD3D57FFFC`.
- Acquisition stderr/source-quality SHA256:
  `7ECFE1DAFA60E287985341177EB4AA1BC998F178870C91C14302ECAB5D8515B1`.
- Raw result: 547 DESIGN decisions; 541 paid responses, 529 nonempty,
  12 complete source-empty responses, six metadata-empty windows, 353,598
  decoded records. Outcome fields used=false.
- Degraded Databento dates, frozen exclusion:
  `2019-01-15`, `2019-02-22`, `2020-02-27`, `2020-06-30`, `2020-07-01`.
- Source-only feature CSV:
  `02. AlphaFactory/data/databento/cme_6e_raw_break_design/book_features_source_only.csv`
  SHA256
  `7BE51A64CB282DD5F11719B97206173F3A0D9D37A212A043B1AC5D45ACFC8BAD`.
- Source-only feature receipt SHA256:
  `801BA6B1D6627367280C614E9B64D3F2D4CAAC4F096858632487CB1F85DEE9BB`.
- Feature extractor SHA256:
  `34A668CF89FEB9ED5A0D74E41E35B6C6B19E810E5BF6CC02AA6F36EE4FDBC4BB`.
- Frozen outcome ledger, not read by the feature plane:
  `03. EA Developer/EA_SweepCascadeContinuation/research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/control_trades.csv`
  SHA256
  `07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9`.

### Split

- DESIGN: UTC years 2019-2020, 547 frozen raw BREAK decisions.
- Sealed OOS: UTC years 2021-2022, 565 decisions. No CME quote, download,
  decode, feature extraction or outcome access is authorized by this plan.
- DESIGN elapsed denominator follows the parent convention:
  `(2020-12-31 - 2019-01-01) / 7 = 104.28571428571429` weeks.

## 3. Frozen causal feature transform

For each nonempty two-minute window `[decision_utc-120s, decision_utc)`:

1. Keep only valid MBP-10 states with both `ts_event < decision_utc` and
   `ts_recv < decision_utc`. No record at or after the decision is usable.
2. At every retained event, sum bid and ask size over levels 0..4 and compute
   `I5=(bid_size-ask_size)/(bid_size+ask_size)`.
3. Align by raw BREAK direction: BUY sign `+1`, SELL sign `-1`.
4. Over the final 30 seconds compute aligned median I5 and the fraction of
   aligned I5 observations greater than zero.
5. Compute the aligned median-I5 change from seconds `[-60,-30)` to
   `[-30,0)`; if the prior interval is empty, change is zero.
6. Fixed score:
   `0.50*aligned_median_I5_last30 + 0.25*(2*persistence_last30-1) +
   0.25*clip(aligned_median_I5_last30-minus-prior30,-1,1)`.

No feature weight, lookback, level count or sign may change after outcome.

## 4. Frozen quality and acceptance surface

A row is quality-eligible only when all hold:

- source is nonempty and not on a frozen degraded date;
- causal records `>=10` and final-30-second records `>=5`;
- last spread `<=2.0` CME ticks;
- last valid book staleness `<=10,000ms`;
- finite score.

Source-only result before outcome: 459 quality-eligible rows (2019=216,
2020=243; BUY=240, SELL=219). Reasons for exclusion are fixed: 12
source-empty, six metadata-empty, six degraded-date rows, 25 insufficient
causal records, nine insufficient final-30-second records, 15 stale books and
15 wide/invalid spreads.

The outcome-blind median score is frozen at
`-0.005025602742083225`:

- `CONTROL_QUALITY_ELIGIBLE`: all 459 rows.
- `CHALLENGER_TOP50_SCORE`: score `>=` frozen median, exactly 230 rows;
  2019=114, 2020=116, BUY=118, SELL=112; cadence
  `230/104.28571428571429 = 2.2054794520547945/week`.
- `NEGATIVE_CONTROL_BOTTOM50_SCORE`: score below the median, 229 rows.

Ties stay on the challenger side. No weekday, hour, session, year, direction,
news, volatility or outcome-derived veto is allowed.

## 5. Outcome join and cost contract

- The probe may read only DESIGN rows from the frozen control trade ledger.
- Join key is `position_id`; `decision_time` and `direction` must also match the
  frozen source plan. Any missing, duplicate or mismatched identity PARKS the
  probe as engineering-invalid before economics.
- Native `net` and `realized_r` remain report-bound HYP004 diagnostics.
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
- DSR uses `02. AlphaFactory/tools/research/dsr.py`, non-excess kurtosis,
  `V[SR]` across all three arms, `N_trials=3`, floor `0.95`.
- Year and direction buckets plus cost tiers are diagnostics/gates, not new
  trials. No grid or alternate percentile is authorized.

## 7. Kill gates — all required for DESIGN FLAG

1. Hash, identity, row-count and no-OOS/no-outcome-before-join checks PASS.
2. Challenger remains exactly N=230 with cadence `2.00..5.00/week`.
3. Native challenger PF `>=1.30`.
4. Native challenger mean realized R `>=+0.08`.
5. Fixed 1.5-pip stress PF `>=1.25`.
6. Fixed 2.25-pip stress PF `>=1.00`.
7. Both 2019 and 2020 separately have PF `>1.00` and mean R `>0`.
8. BUY and SELL separately have PF `>1.00` and mean R `>0`.
9. Versus quality-eligible control: PF lift `>=0.15` **and** mean-R lift
   `>=0.10`.
10. Versus bottom-score negative control: PF lift `>=0.20` **and** mean-R
    lift `>=0.15`.
11. Challenger DSR `>=0.95` across the exact three-arm universe.

Any valid economic failure is
`KILL_DESIGN_BOOK_ALIGNMENT_NO_POSITIVE_EXPECTANCY`. Any source, identity,
implementation or reconciliation failure is
`PARK_INVALID_BOOK_FEATURE_OR_JOIN` and carries no market verdict.

Passing every gate yields only
`FLAG_DESIGN_SURVIVOR_OOS_STILL_SEALED`. It does not authorize OOS access,
MQL5/Model 0, promotion, paper or live trading; the next step would require a
separate frozen OOS/implementation preregistration.

## 8. Mandatory artifacts

- Hash-bound probe script and tests.
- Joined DESIGN trade ledger containing source features plus declared outcome
  fields only after this plan is registry-bound.
- Three-arm metrics, 2019/2020 and BUY/SELL buckets, four cost stresses, DSR,
  gate table and reconciliation receipt.
- `trials/trial_log.jsonl` rows carrying this hypothesis ID and prereg SHA.
- Readout and one terminal/FLAG registry transition.

## 9. Hard exclusions

- No alternate score, weight, level count, lookback, percentile or threshold.
- No exclusion beyond the frozen source-quality rules.
- No HOLD/retest, session, weekday, hour, year, direction or chart-pattern
  rescue.
- No OOS touch in this probe and no claim that CME 6E displayed depth is the
  EURUSD broker's executable book.
- No positive-expectancy, EA-ready or deploy-ready claim from source validity
  alone.
