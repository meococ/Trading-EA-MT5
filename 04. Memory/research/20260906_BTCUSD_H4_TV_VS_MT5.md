# BTCUSD H4 TV vs MT5 — 2026-09-06

Owner TV: LuxAlgo SMC Historical Colored, BTCUSD 4h OANDA, last ~79721.
MT5: TB SMC 2026 visual 2.49 / contract 2.3 on broker BTCUSD H4, last ~80074.

## Why they were not the same
1. Different product (LuxAlgo vs TBalgo IM2GxnOK).
2. No H4 chart was open; M15 had `InpDrawObjects=0` and all `InpShow*=0`.
3. MCP `chart_add_indicator` truncates `indicator_parameters` ~256 chars; leftover bools become 0 and become last-used.

## Deploy that actually paints
Short Name=Value string only:
`InpDrawObjects=1,InpShowStructure=1,InpShowCells=1,InpShowVoids=1,InpShowSweeps=1,InpShowTrail=1,InpShowHud=1,InpShowHtfInset=0,InpFocusMode=0,InpEnableAlerts=0,InpEnablePopupAlert=0,InpEaSweepsRequireLiveSwing=1`

Snapshot: `%APPDATA%\MetaQuotes\Terminal\9CA16B8382AE4CF692710FB36B9DA355\MQL5\Files\Temp\smc_btcusd_h4_v249.png`

## Code 2.49 (visual only)
- `IsHtfChildVisual` requires `CHART_IS_OBJECT` so a real H4 host is not treated as nested.
- CELL word skipped when that bar already has BOS/MSS.
- Engine 2.3 untouched. Compile log: 0 errors, 0 warnings.

## Zone check (MCP H4 tape, not PnL)
- ~62k Strong Low: held 4 times (62418/62235/62262/62483), never revisited after Aug 19.
- ~64-65.5k box: origin of Aug 19 16:00 displacement 64850→68428 (CELL slot).
- ~67k CHoCH line: Jul 21 high 66924 broken by that same close 68428.
- ~76.5-77.2k box: Sep 2 low 76206 swept then Sep 3 16:00 impulse 78612→80937.
- ~82.2k Weak High: Sep 4 00:00 82260, same-day dump to 79128.

Do not rename MSS→CHoCH or CELL→OB.
