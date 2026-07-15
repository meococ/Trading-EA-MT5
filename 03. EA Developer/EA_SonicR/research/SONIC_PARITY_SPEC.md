# Sonic R Parity Spec

## Core model
- Timeframe: M15 closed bars only.
- Dragon: 34 EMA band using high / close / low, with the close EMA as the midpoint.
- Trend: 89 EMA close, used as the bull/bear divider and PA confirmation line.
- Classic Trend: PA wave pulls into Dragon, then breaks Dragon and recent swing in the direction of Dragon angle.
- Re-entry: only after a live Classic narrative exists, and only after a retrace breaks again in the same direction.
- Scout Probe: disabled by default; allowed only as a same-bias support layer after Classic is seeded.
- Classic Reversal: disabled by default; requires strong PVSRA, whole/half/quarter level interaction, and Dragon reclaim/rejection.

## PVSRA parity
- `pvsra_grade` is a 0-5 score from relative tick volume, candle body, range/ATR, and level interaction.
- `pvsra_event` is `CLIMAX`, `RISING_ACTIVITY`, `WIDE_BODY`, or `NONE`.
- `pvsra_bias` is `BULLISH`, `BEARISH`, or `NEUTRAL` from recent accumulation/distribution around Dragon.
- PVSRA is a qualifier and router input. It does not fire a trade by itself.

## Level grid
- `InpLevelGridMode=0`: whole and half levels.
- `InpLevelGridMode=1`: whole, quarter, half, and three-quarter levels.
- Level radius remains symbol-aware through pip scaling.

## HTF bias
- Hard HTF mode requires H1/H4 alignment with the trade.
- Soft HTF mode blocks only when both H1 and H4 are against the setup.
- Soft HTF is the default parity setting because Sonic R uses HTF context, not a mechanical veto on every M15 setup.

## Lifecycle
- `OBSERVE`: context and setup are recorded, but no trigger exists.
- `ARM`: a valid Classic setup is held for a limited number of bars.
- `TRIGGER`: a Classic, Re-entry, Scout, or Reversal setup enters.
- `MANAGE`: live narrative management, break-even, force-flat, and exits.
- `INVALIDATE`: setup is blocked by session, news, weak context, daily cap, or stale arm.
