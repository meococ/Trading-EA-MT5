# Non-repaint audit — EA_M15VolExpansion / HYP-VOLEXP-M15-001

Date: 2026-07-14  
Auditor: Grok lane (Owner MT-open)  
Source: `03. EA Developer/EA_M15VolExpansion/EA_M15VolExpansion.mq5`

## Verdict: PASS (closed-bar decision path)

| Check | Result |
|---|---|
| New-bar gate | `OnTick` advances only when `iTime(..., 0)` changes; then evaluates once |
| Signal OHLC | `GetSignal` / `ComputeRV` use `shift >= 1` only (`iClose`/`iOpen` from 1+) |
| Indicators | `CopyBuffer(g_hTrend/g_hATR, 0, 1, 1, ...)` — closed bar only |
| Entry price | live Ask/Bid at bar open after signal on closed `[1]` (standard non-repaint fill) |
| Bar-zero decision | **none** on filters/direction/SL size |

## Notes

- Session/day gates use the new-bar timestamp (bar[0] open time) for clock filters only; that does not peek unfinished OHLC.
- No MTF misalignment (single timeframe PERIOD_CURRENT).
- This audit does **not** authorize promotion; it only clears the closed-bar gate for Model 0 screen.
