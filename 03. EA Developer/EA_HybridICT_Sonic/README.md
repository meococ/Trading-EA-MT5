# EA_HybridICT_Sonic

Owner Path-C override (2026-07-15): mechanical Hybrid ICT-Sonic from council
brief. Latest executable child `HYP-HIS-SL-SIGATR-M15-EUR-001` is registry
state **`killed`** (N=76, PF=0.98, net -$210.25, ~0.22 trades/elapsed week).
Do not rescue or rerun that hypothesis.

| Field | Value |
|---|---|
| Terminal hypothesis | `HYP-HIS-SL-SIGATR-M15-EUR-001` |
| Symbols (first) | EURUSD, GBPUSD |
| Timeframe | M15 |
| Risk | 0.25%/trade, daily loss 2%, max 5 trades/day |

## Mechanical mapping

- Dragon Band: EMA34 High / Close / Low
- HTF bias: H4 closed-bar BOS of swing pivots
- ICT levels: unmitigated H4 FVG + swing liquidity + simple OB (last opposite bar before BOS)
- Wave: M15 swing sequence L-H-HL (long) / H-L-LH (short)
- PVSRA: tick-volume climax proxy (not true exchange volume)
- Entry: pending stop 4 pips beyond signal candle extreme
- Exit: RR 2.5; optional BE at +50 pips; SL beyond level or Dragon±40 pips
- Filters: London∪NY, spread ≤2.5 pips, ATR regime vs ATR MA

## Limits

- Terminal killed lane; package presence is not execution authority. A new run
  requires an independent mechanism and new hypothesis ID.
- Not promotion-ready. No live claim.
- News calendar filter is OFF unless Owner wires a calendar later.
- Compile/backtest via AlphaFactory only — not from archive.
