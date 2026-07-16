# EA_FVGConfluence

**Status:** Owner Path-C override build (2026-07-15). Registry state `probe`;
de-dup, lifecycle capability and verified cost are not cleared — **not
execution-eligible or promotion-ready**.

| | |
|---|---|
| Hypothesis | `HYP-FVG-SCALP-CONFL-M5-EUR-001` |
| Chart TF | M5 (intended) |
| HTF | H1 default (optional H4 input) |
| Magic default | `26071501` |
| Primary symbol | EURUSD (packs: EUR / GBP / XAU) |

## Strategy summary (EN)

Closed-bar M5 Fair Value Gap (3-candle) continuation/reclaim with a **confluence score** gate:

1. Detect FVG on closed bars (`shift >= 1`): middle candle = impulse (body vs ATR or body/range); bullish gap `High[s+2] < Low[s]`; bearish inverse; prefer unmitigated / partial fill (default max 50%).
2. Enter only when confluence ≥ `InpMinConfluence` (default **3**) among: HTF BOS/bias aligned, nearby Order Block, Premium/Discount aligned, prior liquidity sweep, London/NY session.
3. Entry mode: rejection (pin/engulf/strong close) **or** mid-gap depth 40–60% (`ENTRY_EITHER` default).
4. SL outside FVG edge + symbol-pack buffer; TP min RR 2.0; partial 50% @ 1R; BE @ 1R; optional trail.
5. Filters: London/NY (hard filter default), max 3 trades/day, daily loss 2%, risk 0.25% (challenge) / 0.15% live toggle, spread, one position/symbol, kill switch.
6. **News filter is a stub** (`InpUseNewsFilter=false`): no calendar feed; optional manual block windows only.

## Tóm tắt (VN)

EA scalp FVG M5 + điểm confluence. Quyết định **chỉ nến đóng** (không dùng bar 0). Owner đã override Path-C để **build** dù council/red-team từng PARK/KILL class FVG-cont — đây **không** phải tín hiệu promote / live.

## Symbol packs

| Pack | Min gap (pips) | SL buffer (pips) | Notes |
|---|---|---|---|
| EURUSD | 10 (8–12 band) | 4 (3–5) | default |
| GBPUSD | 12 | 5 | |
| XAUUSD | 25 + ATR floor | 15 | stricter; news stub still off |

`InpSymbolPack=PACK_AUTO` resolves from symbol name.

## Key inputs / defaults

- `InpMinConfluence=3`, `InpMinRR=2.0`, `InpRiskPct=0.25`, `InpRiskPctLive=0.15`
- `InpMaxTradesPerDay=3`, `InpDailyLossLimitPct=2.0`, `InpMaxConcurrent=1`
- `InpEntryDepthMin/Max=0.40/0.60`, `InpUseNewsFilter=false`
- Session broker offsets: `InpTimeHourOffset` / `InpTimeMinuteOffset`

Preset: `Presets/EURUSD_M5_Challenge.set`

## Limitations (plain)

- Owner Path-C override — prior PARK/kill history on FVG-cont family **not cleared** by this build.
- Not de-dup–clean vs Structural V3 FVG-cont kill; no Model 0 / cost-honest PF claim.
- News = stub only.
- QFSI / broker cost STOP may still block meaningful validation.
- Compile/backtest from `00. Old File/` remains invalid evidence.

## Modules

```
EA_FVGConfluence.mq5
Include/FVG_Types.mqh
Include/FVG_Detect.mqh
Include/FVG_HTF.mqh
Include/FVG_OrderBlock.mqh
Include/FVG_PremiumDiscount.mqh
Include/FVG_Session.mqh
Include/FVG_Risk.mqh
Include/FVG_Execution.mqh
research/HYP-FVG-SCALP-CONFL-M5-EUR-001_PREREG.md
```

## Compile

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory/alpha.ps1" compile "EA_FVGConfluence"
```

Use `02. AlphaFactory/tools/ea_research_loop.ps1` only after the generic
registry/prereg/capability/cost gates in `05. Playbook/ea_golden_path.md` clear.
