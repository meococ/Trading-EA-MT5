# HYP-JCDR-EURUSD-M5-005 — terminal diagnostic closeout

## Verdict

`PARKED_DIAGNOSTIC_COMPLETE_POSTRUN_IDENTITY_MISMATCH_NO_ECONOMICS`

The one authorized Model-0 launch was consumed. It completed the frozen
outcome-blind dataset and every EA runtime/data gate passed, but the research
loop correctly rejected the run because the task packet bound the stale server
fingerprint `7AFEBB7D...` while the report-bound identity was
`FivePercentOnline-Real (Build 6090)` / `30B25163...`. No second launch is
permitted. HYP005 cannot claim engineering-valid execution authority or any
economic result.

The exact StageTelemetry file remained usable as descriptive, outcome-blind
evidence: it contains no route, selected entry, future price, outcome, PnL or
trade. AlphaFactory initially omitted it only because the default sidecar list
did not include `*_StageTelemetry_*.csv`; it was recovered by artifact-only
hardlink with no MT5 relaunch, then parsed by the bounded reader and streaming
analyzer.

## Bound run evidence

- Run: `20260807_180115`, EURUSD M5, Model 0, 2016-01-04 through exclusive
  tester stop 2021-01-01.
- Source snapshot SHA256: `F337B9B7...F9D49AC1`.
- Task packet SHA256: `2981B4DD...46B63206`.
- Run manifest SHA256: `3F43893F...4259FCA`.
- Report SHA256: `4F7318B6...04E1ED24`.
- Journal SHA256: `3B8B2AFC...3D48F646`.
- RunMeta SHA256: `ECC9A787...F2AFB4`; `runtime_all_pass=true`.
- StageTelemetry SHA256: `04AB8F95...B3F83A0C`, 1,455,026 bytes,
  114 columns, 934 unique rows.
- Streaming analysis SHA256: `F8AB90F5...23D4A0D9`.
- History Quality: 100%; first/last analysis dates: 2016-01-04 / 2020-12-31.
- Orders/trading deals/positions: 0 / 0 / 0; only the initial balance operation.
- Outcomes observed/economics executed: false / false.

## Outcome-blind diagnosis

The dataset is balanced enough for source diagnosis: 934 raw events
(`3.5844/week`), 453 positive versus 481 negative clusters, maximum year share
20.34%, and only 20 invalid-core rows (2.14%). Both counterfactual TB geometries
were valid on 915 rows.

The failure is causal composition, not a threshold near-miss:

1. Only 77/934 events have a valid `>=6 pip` and `>=1R` corridor in the original
   cluster direction. The full same-bar continuation funnel falls from 934 raw
   events to 112 after AIRD/QQE/energy and then to zero after cluster-direction
   geometry.
2. Opposite-direction geometry exists on 447 rows, but the live context still
   points with the original cluster: TB bias aligns on 866 rows, VRC direction
   aligns on 827 and AIRD held regime aligns on 590. Treating opposite geometry
   as a reversal signal therefore fights structure rather than fixing timing.
3. QQE primary and secondary alignment are identical on this contract
   (742 positive for each), because both RSI streams share the same source,
   length and smoothing; counting them as two votes double-counts one momentum
   feature. QQE composite alignment is only 413/934 and must be treated as a
   timing state, not another independent regime vote.
4. TB structure event is zero on every JCDR decision row. The last structural
   event is usually old (516 rows are age 11–20); JCDR is not a fresh structural
   trigger. Native MT5 loser charts independently show the same failure mode:
   stale episode labels, obstructed corridors and momentum/structure conflict.

## Failure radius and legal successor

Terminal scope: the exact JCDR-centered, same-bar role composition and its
one-shot HYP005 authority. Do not rescue it by tuning AIRD confidence, QQE
thresholds, MBB squeeze windows, TB corridor thresholds, hour, direction, pair
or stop/target.

This is not a claim that JCDR, any individual indicator, structural trading or
the market lacks edge. A legal successor must change the event clock and
decision surface. The clean next hypothesis is an atomic TB-first structural
episode—such as a confirmed sweep/reclaim—where AIRD/VRC classify context,
MBB describes compression/expansion, QQE times confirmation, and TB supplies a
fresh protected swing plus entry-time live corridor. It must be preregistered
before outcomes, prove 2–5 source opportunities/week per symbol, and only then
open economic testing with pair/session adaptation confined to purged training
folds.
