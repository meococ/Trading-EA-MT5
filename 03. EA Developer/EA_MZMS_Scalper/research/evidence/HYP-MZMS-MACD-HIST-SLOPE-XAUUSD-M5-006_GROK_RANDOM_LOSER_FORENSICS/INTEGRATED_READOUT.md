# HYP-006 random-loser chart forensics — integrated readout

## Executive verdict

Two independent Grok CLI workers completed pixel-level review of two disjoint,
pre-frozen random samples: 20 losing positions per worker, 40 positions total.
Both workers independently identified a dominant **late/mature impulse entry**
shape in 10 of their 20 cases. The second recurring anatomy is split between
rapid adverse movement and lack of follow-through: across all 40 selected
losers, 19 exited within 30 minutes and 11 exited at exactly the frozen
15-M5-bar / 75-minute timeout.

This is mechanism-discovery evidence only. The parent run remains
`INVALID_ENGINEERING_RUN` because tester history quality was 98%, below the
frozen 99% gate. The sample contains losers only, so no count below is a
population failure rate or evidence that the same visual shape does not also
occur among winners.

## Evidence integrity

- Hypothesis/run: `HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006` /
  `20260721_190051`.
- Lifecycle population: 5,078 exact OPEN+CLOSE positions; 3,030 positions with
  aggregate `deal_net < 0`.
- Frozen selection: sort losers by numeric position ID, deterministic Python
  `random.Random(5600721)` shuffle, indices `0:20` to Worker A and `20:40` to
  Worker B. The 40 positions are disjoint.
- Charts: 20 decision + 20 outcome PNGs per worker. All 80 renders have
  `chart_case_render.v2` manifests; every decision candle window enforces its
  entry cutoff.
- Bars: bounded XAUUSD M5 windows exported from the portable FivePercent
  terminal on D:. All 40 lifecycle entry/exit prices align with the M5 bid bar
  plus the frozen USD 0.35 spread ceiling.
- Bar limitation: this post-run bounded export is not tick-parity proof and
  does not repair the invalid 98% parent history.
- Blinding limitation: decision candle regions stop before entry, but their
  titles include the known loser net USD/R label. This is therefore a loser
  anatomy review, not a fully blinded entry-quality experiment.

Grok runner verification:

| Worker | Decision PNGs | Outcome PNGs | Cases | Schema | Turns | Cost |
|---|---:|---:|---:|---|---:|---:|
| A | 20 | 20 | 20 | PASS | 11 | $0.6860 |
| B | 20 | 20 | 20 | PASS | 12 | $0.7156 |

- Worker A response SHA256:
  `B52462AD96B1778F53D79A3B46AF4D5B2EBB0EA8452F6F0011085CB8D9A91C8B`
- Worker B response SHA256:
  `1DCC261D30CDAE8A6EA9BDCB36DC57D66C8D810463FE4E738AB6C5128818FDFA`
- Both runs used Grok CLI default model resolution, high reasoning, local-only
  evidence, nested subagents disabled, and web search disabled.

## Integrated observations

### 1. Entry after a mature impulse — convergent, high-confidence sample shape

Worker A classified 10/20 cases as late-extension/climax entries. Worker B,
reviewing a disjoint sample, independently classified 10/20 cases as
late/high-range long-extension failures. Both reviews repeatedly show the
entry close on the permitted EMA200 side after a large move is already visible
on M5/H1, followed by reversal or decay rather than fresh continuation.

The code linkage is plausible: `ClosedBarSignal()` confirms a local MACD
histogram extremum on shifts 1/2/3, normalized one-step histogram delta, EMA200
side, directional candle, RSI direction, and ADX. It has no impulse-age,
distance-from-recent-swing, or higher-timeframe range-location term
(`EA_MZMS_Scalper.mq5`, lines 337-400). This supports a testable mechanism, but
the loser-only charts cannot establish that the missing context causes losses.

### 2. Rapid adverse movement — observed path, stop-cause not established

Across the combined 40-case sample:

- 9 exits occurred within 15 minutes;
- 19 exits occurred within 30 minutes;
- 23 losses were at or below -0.8R;
- median hold was 41.09 minutes and median outcome was -0.865R.

Both workers called out one-to-few-bar stop paths. However, their stronger
claim that the structural stop is generally "too tight" is **not established**
by the code. The EA uses the farther of the five-bar structural stop plus
buffer and the 1.5-ATR stop (`TryOpenTrade()`, lines 413-427). A fast stop can
therefore reflect a genuinely large adverse move, spread/slippage, history
fidelity, or unsuitable entry timing. The two visible stop-then-go cases in
Worker A are hypothesis-level, not enough to diagnose stop geometry broadly.

### 3. No follow-through and forced timeout — observed, high confidence

Eleven of 40 selected losers closed at exactly 75 minutes, matching
`InpMaxHoldBars=15` in `ManageOwnedPosition()` (lines 581-595). Worker A found
3/20; Worker B found 8/20. Several are small losses after price oscillated
around entry, while others decayed materially before timeout.

This is a distinct failure path from immediate stops: the signal was not
quickly disproved, but it also did not generate enough directional expansion
to reach 1.6R. Break-even was frozen OFF, so these cases cannot answer whether
BE would help; any BE claim requires a separate preregistered arm.

### 4. Continuation entries into mean reversion — convergent sub-pattern

Worker A found five short losers after an extended decline/post-drop bounce;
Worker B found four. The EMA-side and MACD-local-extremum logic can still admit
a continuation entry when the larger move is mature. This is visually
consistent with the dominant late-entry mechanism, but it does not authorize a
short veto, session veto, or range-location cutoff.

## What the review can and cannot conclude

Observed within the 40 selected losers:

- many accepted signals appear after rather than before the visible impulse;
- almost half exit within 30 minutes;
- more than one quarter reach the exact 15-bar timeout;
- both immediate reversal and non-expansion are material loser anatomies.

Not established:

- prevalence among all 5,078 trades;
- whether late-looking entries lose more often than matched winner entries;
- whether stop geometry, signal timing, or invalid history is the primary
  causal driver;
- any profitable threshold, filter, symbol transfer, or parameter rescue.

## Legal next research

No EA edit or rerun is authorized from this readout. At most, the observations
support three fresh, pre-registered mechanism tests on valid history:

1. A matched winner/loser case-control analysis using continuous pre-entry
   impulse-age and range-location features, with charts fully outcome-blinded.
2. A frozen stop-geometry comparison on the identical signal stream to
   separate entry failure from stop placement; no threshold may be taken from
   these 40 outcomes.
3. A frozen timeout-path study using predeclared MFE/MAE and time-to-expansion,
   with BE ON/OFF only as separate arms.

## Artifact map

- `selection_manifest.json` — frozen sample, lifecycle identities, hashes.
- `bars_manifest.json` — bounded bar source and 40 price-alignment checks.
- `charts/worker_a/{decision,outcome}/cases_manifest.json`
- `charts/worker_b/{decision,outcome}/cases_manifest.json`
- `.context/mzms-xau-loser-forensics-a/{summary.json,grok-response.json}`
- `.context/mzms-xau-loser-forensics-b/{summary.json,grok-response.json}`

