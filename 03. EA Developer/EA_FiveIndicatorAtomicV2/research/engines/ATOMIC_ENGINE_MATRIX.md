# Atomic Engine Logic Matrix — FIV2

Frozen pre-outcome. Engines are separate hypothesis families.
**Do not pool results across engines.**

| Role | ENGINE_R Range/MR | ENGINE_T Trend Pullback | ENGINE_B Squeeze Breakout |
|---|---|---|---|
| **Primary event clock** | MBB S1 or price reclaim of robust band (rising-edge) | MBB S2 / pullback-to-basis event (rising-edge) | MBB S3 release (rising-edge) |
| **Structure (TB SMC)** | Sweep/reclaim at range boundary; protected swing intact | BOS/MSS same direction; pullback does not break protected swing | Displacement and/or structure break same direction |
| **Regime context (AIRD)** | Held regime = Ranging; confidence ≥ prereg floor | Held regime = Bull (long) or Bear (short); confidence ≥ floor | Regime transition or confidence rising with direction; not pure HighVol shock without structure |
| **Vol context (VRC)** | Range / mean-reversion regimes; not strong trend extremes | Trend-compatible regimes; block compression + high-cost shock | Compression → expansion path; block extreme spread/ATR |
| **Timing (QQE)** | Loss of extreme momentum or causal cross-back toward neutral/zero | Re-acceleration same direction (composite/state; **no** double-count primary+secondary RSI) | Impulse same direction on release bar+confirm |
| **Invalid if** | AIRD trend strong; VRC strong trend; TB opposite BOS/MSS | AIRD ranging/high-vol without trend; VRC compression-only; structure broken | Gap/open shock; spread/ATR gate fail; no displacement |
| **Exit** | Basis or opposite band; structural invalidation | Structural stop; vol target; causal trail | Opposite failure of release; structural stop; time stop |
| **Hypothesis prefix** | `HYP-FIV2-R-` | `HYP-FIV2-T-` | `HYP-FIV2-B-` |

## Indicator retention rule

An indicator may remain in an engine only if nested-training ablation shows:

- higher expectancy or stability, **or**
- lower DD/tail risk without destroying expectancy,

and the improvement holds on a **majority of outer folds**, not only pooled.

## Explicitly forbidden

- Five-way buy/sell vote
- Treating QQE primary RSI and secondary RSI as independent sources
- Mixing engine trade lists into one PF for discovery survival
- Opening validation after any hard discovery gate fail
