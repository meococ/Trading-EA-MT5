# Prereg — HYP-FVG-SCALP-CONFL-M5-EUR-001

## Identity

- Hypothesis ID: `HYP-FVG-SCALP-CONFL-M5-EUR-001`
- Parent candidate: Owner council brief “FVG Scalping + Confluence” (Path-C override)
- Author/session: impl (Owner-authorized BUILD) / 2026-07-15
- Date: 2026-07-15
- State on creation: `idea` (scaffold under Owner Path-C override)
- **Owner Path-C override noted:** prior council/red-team PARK and Structural V3 FVG-cont kill history are **not** waived as research truth; Owner explicitly ordered BUILD anyway. This prereg does **not** claim a de-dup pass.

## Thesis

- Trader/market thesis: M5 FVG (3-candle impulse gap) with multi-factor confluence (HTF BOS/bias, OB, premium/discount, liquidity sweep, London/NY) can produce positive expectancy scalps on EURUSD when entries require score ≥ 3 and risk is capped.
- Source provenance: Owner council brief + mechanical closed-bar mapping (local implementation)
- Feature family: FVG + SMC confluence (related to killed FVG-cont class — override risk accepted by Owner)
- Lane/setup: M5 FVG reclaim/continuation with confluence gate
- Symbol/timeframe: EURUSD M5 (HTF H1 default; H4 optional)
- Market regime expected: directional session liquidity (London/NY); avoid news (stub only)
- Independence claim: **none asserted** — override build; may densify prior FVG-cont failure mode

## Locked Design (frozen for first meaningful run)

### Exact feature definition

- FVG: closed bars only; newest of trio `shift >= 1`; impulse = middle (`shift+1`) with body ≥ `InpMinBodyATR * ATR` **or** body/range ≥ `InpMinBodyRange`.
- Bullish gap: `High[shift+2] < Low[shift]`; bearish inverse; min gap from symbol pack (EURUSD default 10 pips) unless override.
- Mitigation: reject fully filled; allow fill ≤ `InpMaxFillPct` (default 0.50).
- Confluence score (integer count, default min 3): HTF aligned, nearby OB, PD aligned, prior sweep, session (if counted).
- Entry: rejection candle on shift=1 **or** mid-gap depth in [`InpEntryDepthMin`, `InpEntryDepthMax`] (defaults 0.40–0.60).
- SL: outside FVG edge + pack buffer (EURUSD default 4 pips); hard SL required.
- TP: ≥ `InpMinRR` (default 2.0); optional structure TP only if RR ≥ min.
- Manage: partial 50% @ 1R; BE @ 1R; trail remainder (inputs).

### Closed-bar contract

- Signal decisions use `shift >= 1` only (new-bar gate on `iTime(..., 1)`).
- Management (BE/partial/trail) may run on tick after a position exists.
- First executable entry is the next market quote **after** the closed-bar signal bar — never the signal bar’s historical close as a fill.

### Frozen parameters (Challenge preset)

| Param | Value |
|---|---|
| Magic | 26071501 |
| Risk % | 0.25 |
| Min confluence | 3 |
| Min RR | 2.0 |
| Max trades/day | 3 |
| Daily loss % | 2.0 |
| Max concurrent | 1 |
| Entry mode | EITHER |
| Depth | 40–60% |
| Session hard filter | true |
| News filter | false (stub) |
| Symbol pack | AUTO → EURUSD |

### Banned post-result edits

- No post-hoc hour/day/year veto from readout of this hyp.
- No tightening confluence thresholds or fill% from the same failed run’s equity curve.
- Fail → kill/park + new hyp id; no rescue tune.

## Kill gates (from council / GOAL — research plane)

Treat as **fail-closed** targets for any future Model 0 (not claimed met):

- Profit factor after **verified full cost**: council band PF ≥ 1.55–1.60 (GOAL floor PF > 1.30 still applies as workspace minimum).
- Cadence: 2–5 trades per elapsed calendar week (not active-week denominator).
- Drawdown: council DD &lt; 10–12% band; workspace hard invalidation per sonic gates if used.
- Expectancy preferred over chasing WR; do not claim council WR 70%+.

## Test plan (not executed by this impl packet)

- Offline OHLC probe recommended before ceremony (Owner may still order Model 0 later).
- Model 1 screen only for kill/park; serious control/challenger → Model 0 via AlphaFactory.
- Cost field 0 ≠ cost 0; QFSI STOP may block honest PF.
- Train/holdout and cost stress x1/x1.5/x2: TBD by coordinator before first ceremony run.

## Preflight

- Canonical source: `03. EA Developer/EA_FVGConfluence/EA_FVGConfluence.mq5`
- Archive compile paths: **invalid evidence**
- Preset: `Presets/EURUSD_M5_Challenge.set`

## Expected failure modes

- Same FVG-cont densify failure as Structural V3 (`HYP-H1-DISPLACE-FVG-CONT-001`).
- Session/confluence stacking without edge after cost.
- News stub leaves event risk unfiltered.

## Explicit non-claims

- No de-dup pass.
- No promotion-ready status.
- No live / funded entitlement from compile success alone.
