# RSF Cell 16 — Five-indicator losing-trade forensics

## Verdict

Cell 16 is empirically invalid on the full population. The forensic evidence
identifies its **same-bar confirmation stack** — rather than a temporal
decision process — as a plausible design mechanism, not the proven sole cause.
The stack can describe a regime, setup, structure and momentum consistently,
yet it does not establish that the entry location still has positive forward
expectancy. Stronger agreement did not reliably separate winners from losers
in the frozen matched pairs.

This is a terminal explanation of the already-killed
`HYP-RSF-EURUSD-M5-BLOCK1-001`; it is not a parameter rescue. The EA remains:

- engineering-valid: **yes**;
- economic-valid: **no**;
- promotion-ready: **no**.

## Evidence boundary and replay fidelity

- Parent Cell 16: run `20260806_210021`, EURUSD M5, 2018–2022, Model 0.
- Parent source SHA-256:
  `E40F29431E8ADA440302F7DEDB7ACD8EBCB48C1308EB6B43936849C128E959D0`.
- Forensic replay: run `20260806_231942`.
- Replay source SHA-256:
  `F08F6FB01456738536EB72E68D9CAB184ABC92D37345168DB2F5A8E403CF5839`.
- Fidelity: exactly 670 trades, net `-5,252.60`, PF
  `0.7203706316229374`, DD `5.528080118%`, 372,914 bars and 105,949,201
  ticks — identical to the parent result.
- Five-indicator replay sidecar SHA-256:
  `B94E3A856AE6AE6DE0E3047D3215E3AF9AC1C929827645D051AD285F26E8F655`.
- Fourteen cases were selected before any chart or indicator inspection: one
  negative-median loser and one matched winner for each engine/direction, plus
  the global R extremes.
- Every selected entry timestamp maps to exactly one replay snapshot. The
  wrapper's `entry_fired` convenience flag is not used because MT5 transaction
  callbacks update position state asynchronously; the authoritative join is
  lifecycle position ID plus exact server entry time.

Each case has two separate images:

- `casebook/asof/Axx.png`: only closed bars before entry, outcome hidden;
- `casebook/anatomy/<case-id>.png`: exit and outcome disclosed.

The charts plot actual MT5 indicator buffers. Python renders pixels but does
not recompute AIRD, VRC, MBB, TB SMC or QQE.

## Full-population result: the rule has no edge

| Metric | Result |
|---|---:|
| Trades | 670 |
| Wins / win rate | 273 / 40.75% |
| Net / PF | -5,252.60 USD / 0.720 |
| Mean net R | -0.0816R |
| Average win / loss | +1.265R / -1.008R |
| R-payoff breakeven win rate | 44.33% |
| Actual shortfall | -3.59 percentage points |

The failure is not just dollar-risk scaling. Normalized expectancy is also
negative. The frozen 1.5R target becomes about +1.27R after costs and expert
exits, so a 40.75% hit rate is insufficient.

### Engine decomposition

| Engine | N | WR | Net USD | PF | Mean net R | Reading |
|---|---:|---:|---:|---:|---:|---|
| TREND_LONG | 194 | 35.1% | -4,309.90 | 0.379 | -0.238R | primary failure driver |
| TREND_SHORT | 221 | 45.7% | -253.90 | 0.962 | +0.025R | near-flat R, still money-negative |
| BREAKOUT_LONG | 95 | 46.3% | -787.85 | 0.695 | +0.083R | positive mean R but adverse risk chronology |
| BREAKOUT_SHORT | 118 | 38.1% | -91.54 | 0.950 | -0.122R | below its 42.96% breakeven WR |
| RANGE_LONG | 10 | 20.0% | -100.72 | 0.017 | -0.598R | tiny and clearly failed |
| RANGE_SHORT | 32 | 40.6% | +291.31 | 1.488 | -0.046R | small post-hoc pocket; not a survivor |

The opposing signs between USD and normalized R in some branches are caused
by chronology, not a hidden robust edge. The money-mode stop-out reserve makes
the risk budget collapse after early losses: median initial risk fell from
`191.06 USD` in 2018 to `25.90` in 2019, `5.60` in 2020 and `1.21` in 2021.
Capital preservation worked, but later wins became too small to recover early
losses. No branch may be selected after seeing this decomposition.

### Path decomposition

Of 397 losing trades:

- 172 (43.3%) never reached even conservative +0.25R before exit;
- 152 (38.3%) reached at least +0.50R and still closed as losses;
- 44 reached at least +1.00R and still closed as losses;
- median loser MFE was +0.337R and median MAE was 1.00R.

MFE/MAE uses only fully completed M5 bars before the exit plus entry/exit
prices, so these counts are conservative. The first group raises an
entry-location/selection question. The second raises a separate
path-management question in the fixed SL/TP/max-hold geometry. Neither count
proves causality, and neither proves that break-even or trailing rules improve
expectancy.

## What the code actually asks the indicators to do

`BuildDecision()` constructs every route from the same closed-bar snapshot:

- context gates: lines 744–756;
- breakout: lines 761–774;
- trend: lines 776–788;
- range: lines 790–802;
- stop/target geometry: lines 819–850;
- the route is evaluated once on each new bar: lines 1159–1180.

This design prevents repainting, but it also means there is no sequence such
as “regime established, setup armed, reclaim confirmed later, momentum
re-accelerated within an expiry.” The measured design permits correlated
indicators to confirm the same move; whether temporal sequencing repairs
expectancy remains an untested hypothesis.

Two route details matter:

1. Breakout checks `compression_origin && context_confident` but not
   bull/bear directional AIRD/VRC context (lines 755–768).
2. Range requires a sweep in the trade direction but ignores persistent TB
   bias (lines 790–800).

These are measured code properties, not proof that simply adding two filters
would create an edge.

## Frozen case analysis

### 1. Breakout long: perfect confirmation can still be late

**Loser `RSF-C16-BREAKOUT-LONG-L` (-1.09R):** AIRD BULL 99.4%, VRC BULL,
TB bias/cell/void bullish, MBB S3 long, QQE +23.83/+44.46. The entry was already
2.32 MBB half-widths above basis and stopped in under five minutes before price
resumed upward. The indicators described the move correctly but did not
provide a tolerant entry location.

**Matched winner (+1.40R):** AIRD was only RANGE 75.9%, VRC merely WEAK BULL,
and the entry was 1.30 half-widths above basis. Lower model confidence won;
greater agreement was not a quality ranker.

### 2. Breakout short: directional regime is not part of the route

**Loser `RSF-C16-BREAKOUT-SHORT-L` (-1.08R):** AIRD RANGE, VRC COMPRESSION
with bullish direction, while TB and QQE were bearish. The short passed because
the breakout route uses confidence/compression, not bear context.

**Matched winner (+1.47R):** AIRD and VRC were both bullish, yet the short also
won. This pair confirms the code behavior but rejects the easy post-hoc story
that directional context alone separates breakout outcomes.

### 3. Range long: the bounce fought persistent structure

**Loser `RSF-C16-RANGE-LONG-L` (-1.11R):** AIRD/VRC correctly said range,
MBB S1 long and a low sweep fired, but TB bias was -1 and price resumed its
broader decline after a shallow bounce.

**Matched winner (+1.43R):** the same range route had TB bias +1 and expanded
up immediately. This supports a *diagnostic* sequence/bias question, not a new
filter: there are only ten RANGE_LONG trades.

### 4. Range short: the second counter-bias loss

**Loser `RSF-C16-RANGE-SHORT-L` (-1.06R):** TB bias/cell/void were bullish;
the short stopped in about five minutes during upside expansion.

**Matched winner (+1.45R):** TB bias was bearish. Across the six frozen pairs,
all six winners were TB-bias aligned versus four of six losers. The difference
comes from these two range pairs. The global maximum-R RANGE_SHORT winner was
counter-bias, so “require bias alignment” is not established.

### 5. Trend long: the main loss engine has no stable visual separator

**Loser `RSF-C16-TREND-LONG-L` (-1.03R):** AIRD BULL 99.5%, VRC STRONG BULL,
TB bullish and QQE strongly positive; stop distance was 3.47 ATR. It still
rolled over after 152 minutes.

**Matched winner (+1.48R):** the same indicators and route were aligned with
similar extension and a 3.82 ATR stop. This is the core failure: the full stack
can validate both outcomes and therefore does not rank forward continuation.

### 6. Trend short: aligned trend episodes still reverse

**Loser `RSF-C16-TREND-SHORT-L` (-1.03R):** AIRD/VRC/TB/QQE all bearish,
MBB S2 short, 3.67 ATR stop. It entered near a local trough and reversed to SL.

**Matched winner (+0.92R):** almost the same state, then exited at the four-hour
max hold rather than TP. VRC volatility percentile was 100 versus 52 for the
loser, but one pair cannot authorize a volatility threshold.

### 7. Extreme loss: closed-bar logic cannot absorb every intrabar shock

`RSF-C16-EXTREME-LOSS` was a fully aligned BREAKOUT_SHORT and still lost
-1.22R in 42 seconds. Exit `1.04813` exceeded the `1.04796` stop by 1.7 pips.
This is direct evidence of intrabar jump/slippage risk. A static close-bar
state and current-spread backtest cannot promise exact stop execution.

## Cross-case indicator findings

- **AIRD confidence is not a ranker around these cases.** In the 2,691 frozen
  replay snapshots, 99.78% exceeded the configured 0.45 threshold. This is a
  window diagnostic, not a full-population frequency claim.
- **AIRD/VRC direction did not separate matched outcomes.** AIRD direction
  aligned in 3/6 losers and 2/6 winners; VRC aligned in 3/6 on both sides.
- **QQE state is non-discriminating in the captured windows.** All 2,691
  exported `qqe_state` values were zero. Price/RSI sign still gates trades, but
  the `>=0`/`<=0` state checks admit neutral for both directions. Cell 15→16
  deteriorated from PF 0.846 to 0.720, so QQE did not rescue this design. That
  is not a clean fixed-entry causal ablation because the trade sets differ.
- **MBB signals fire as specified but do not encode remaining runway.** The
  breakout-long loser is the clearest late-location example; extension is not
  consistent enough across all pairs to define a legal threshold.
- **TB is most useful as state/geometry, not proven alpha.** Bias alignment
  looks helpful only in the two range pairs and has an extreme counterexample.

## Independent Grok visual/logic review

Grok Build received the seven losing charts as actual image blocks plus the
report, code and machine-readable tables. The file-based runner completed with
exit code 0, `EndTurn`, seven images/3,202,070 decoded bytes and passed the
requested JSON schema.

- Verdict: `ACCEPT_WITH_CHANGES`.
- It independently confirmed all seven chart/CSV facts, the exact route
  predicates, engine arithmetic and terminal no-edge verdict.
- It found no chart-cutoff, MQL predicate or mathematical error that changes
  the kill decision.
- Its two medium changes are incorporated above: same-bar stacking is a
  candidate mechanism rather than proven sole cause; Cell 15→16 is evidence
  that QQE did not rescue the design, not clean causal harm proof.
- Structured review SHA-256:
  `4BB779980E72AD3B11CE219C0B76A25D61718A0FA2FFD98391675B621CB41C30`.
- Runner summary SHA-256:
  `133025D68DE9B88479B2D7D7413A673DE6AF19B58933F6FF02B622019EBB07B1`.
- Raw response SHA-256:
  `B14D72B0140AF428C37F0A81F7310E54EC814C03D6FAB4AA06C8D64417094517`.

## Legal next hypotheses — maximum two

### `HYP-RSF-EURUSD-M5-SEQUENCE-002` — temporal state machine

Fresh mechanism, not a parameter rescue:

1. AIRD/VRC establishes and ages a regime episode.
2. MBB arms one route-specific setup.
3. TB sweep/reclaim or displacement must occur on a later bar within a frozen
   expiry window.
4. QQE is route-specific confirmation or invalidation, not a universal gate.
5. Entry requires a separately frozen location/runway condition.

The preregistration must freeze state transitions, expiry, timezone/session,
trial family count, CPCV purge/embargo and DSR denominator before execution.

### `HYP-RSF-EURUSD-M5-PATH-003` — entry versus exit mechanism ablation

Test entry and path management separately using the same frozen entries:

- control: current fixed SL / 1.5R TP / 48-bar max hold;
- challenger mechanisms preregistered before outcome access, such as one
  conservative profit-protection rule versus one time-based invalidation rule;
- no threshold sweep selected from the +0.5R reversal statistic;
- dynamic slippage and stop-gap stress required.

No third hypothesis is justified by the 14 charts. In particular, weekday,
hour, direction, AIRD confidence, VRC volatility, MBB extension and TB-bias
thresholds remain forbidden post-hoc tuning surfaces.

## Artifact index

- `selection_manifest.json`: frozen case selection and capture windows.
- `position_truth_table.csv`: full 670-position lifecycle truth table.
- `casebook/casebook_manifest.json`: 28 chart hashes and cutoff assertions.
- `casebook/RSF_C16_LOSER_INDICATOR_CONTACT_SHEET.png`: seven frozen losses.
- `analysis/forensic_metrics.json`: machine-readable population/path metrics.
- `analysis/matched_pair_entry_states.csv`: actual five-indicator entry states.
- `analysis/population_by_engine.csv`: full-population engine decomposition.
- Replay run: `02. AlphaFactory/runs/EA_RegimeStructureFusionForensics/20260806_231942`.

## Evidence labels

- **Measured:** replay fidelity, lifecycle population, R/path metrics, exact
  indicator buffers, code predicates and hashes.
- **Interpreted:** “late entry,” “fought structure,” and visual price-action
  descriptions in the case notes.
- **Hypothesized:** temporal sequencing and path-management mechanisms. Neither
  has been tested or authorized.
