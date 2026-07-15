# New Strategy Deep Research Failure Packet V3 — 2026-07-13

Status: `FAILURE-FEEDBACK RESEARCH / NO PREREG / NO EA CODE AUTHORIZED`

## Required ChatGPT UI contract

- Model `GPT-5.6 Sol`.
- Intelligence mode `Pro`.
- Tool selected through `+ -> Nghiên cứu sâu` after the prompt is present.
- Read back all three states before submission.

## Why V3 exists

Deep Research V2 proposed `EURUSD Europe benchmark-fix dealer-hedging reversal`
and called it a Phase-A survivor. Coordinator de-duplication proved that this
was a direct duplicate of an already falsified local family. V3 must treat that
miss as evidence and search outside the entire fix/session-timing field.

## Newly locked falsification controls

Do not propose, rename, threshold-filter, or condition any of these families:

- `S532 / EA_FixFade`: EURUSD M15 London WMR post-fix reversal fade,
  2018-2026, 965 trades, PF 0.870869, net -2553.65, DD 32.61%.
- `S214-S217 / EA_LondonFix`: pre-fix/fix momentum on USDJPY, EURUSD and
  GBPUSD. PF 0.193689, 0.635137 and 1.018369 respectively.
- `S564 / EA_PostFixRevert`: XAUUSD M15 post-fix mean reversion, 1905 trades,
  PF 0.851529, net -3577.23, DD 36.91%.
- TokyoFix/TokyoFixV2, LBMAAMFix, GoldAMFix, ShanghaiFixScalp, EODRevert,
  TimeFade, HourBias, SessionDrift, London/Asian sweep/reclaim, opening drift,
  and any fixed-time benchmark/session reversal or momentum family.
- A pre-fix condition such as `preE < 0`, volatility, day, symbol, ATR, trend,
  displacement, or spread threshold does not create a new mechanism. It is a
  filter/rescue of the closed fix family unless independent causal evidence and
  a non-overlapping decision surface are proven.

The academic fix mechanism is not disputed. Bank of Canada research documents
pre/post-fix reversals and dealer hedging, but it also finds that most profits
disappear under transaction costs. Economic plausibility does not override the
local direct falsification.

## Full closed-family boundary inherited from V2

Also keep closed: Sonic Classic/PVSRA/Dragon/Trend and context-rescue fields;
Asian manipulation; generic range/mean reversion; compression/breakout/retest;
ATR/HTF/sweep/velocity/SR-runway filters; gap fill; S555 lead-lag; S618 fixed
consensus; S670 laggard catch-up; common-USD strongest-pair routing;
management-only MFE/BE/TP/trailing/max-hold rescue; ITSM, ChopRegime, Gotobi,
Spark, H4Ribbon, TrendBook, SilverBullet tuning, and sparse LondonNY transfer.

## Current data and cost boundary

- Canonical unsuffixed universe: EURUSD, GBPUSD, XAUUSD; USDJPY only under a
  new frozen contract.
- Preferred M5/M15 execution; closed higher-timeframe context only.
- Same-broker cost provenance is still incomplete: roughly 4% non-zero M15
  spread coverage in 2024-2025, two EURUSD commission lifecycles, no GBPUSD or
  USDJPY commission evidence, and zero independent slippage samples.
- Missing cost/data is never zero. A candidate may return `BLOCKED_BY_DATA`,
  but it must first survive hard mechanism de-duplication.
- Reject order-book, options-strike/OI, dealer-flow, proprietary consensus,
  discretionary labels, or unreconstructable event-timestamp dependencies.

## V3 task

1. Perform a frontier audit before ideation. State whether any mechanism space
   remains that is causally independent from every closed family above and can
   be observed using synchronized OHLC/ticks plus official public data.
2. Propose at most two mechanisms. `NO LEGAL CANDIDATE` is preferred over a
   cosmetic variant.
3. For each proposal, provide a line-by-line de-dup matrix against S214-S217,
   S532, S564 and the inherited closed-family boundary. Reject anything that
   differs only by time, symbol, side, threshold, filter, target, stop or hold.
4. Require a primary source for the mechanism, but explicitly separate
   mechanism evidence from evidence that a retail rule is profitable.
5. Apply data availability and cost tolerance before writing exact rules.
6. If one candidate truly survives, provide one fixed closed-bar rule set and
   one cheap train-first/one-time-holdout offline falsification probe. Do not
   provide MQL5 code.
7. If nothing survives, return `NO LEGAL CANDIDATE`, identify the exhausted
   frontier, and specify what genuinely new external data or market access
   would be required to reopen research.

## Non-negotiable outcome contract

The answer cannot authorize a hypothesis ID, registry row, preregistration,
analyzer, EA source change, compile, backtest or promotion. Coordinator source
audit and local de-dup remain authoritative.

