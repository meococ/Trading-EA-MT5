# De-dup clearance — HYP-PDH-BREAK-M15-001 vs shelf

Date: 2026-07-14  
Verdict: **PASS_INDEPENDENT** (written pre-Model-0; not a London-ORB / fade rescue)

## Claimed mechanism

Previous calendar-day high/low (`D1` shift ≥ 1) are auction reference levels. A closed M15 `bar[1]` close beyond PDH/PDL with body confirmation and D1 EMA50 alignment is treated as **continuation breakout**, invalidation = reclaim of the broken level.

## Explicitly not

| Shelf / ID | Why not a twin |
|---|---|
| London ORB `HYP-LONDON-ORB-M15-001` | Range is **same-day first-hour auction**, not prior-day extremes |
| Spark Asian / HourOpen | Overnight range or clock-hour micro-ORB — different range construction |
| InsideBar / ITSM / SB / USBILL / Keltner | Different signal families |
| LiqSweep S159–S161 | **Fade / stop-hunt** of PDH/PDL — opposite side; STRATEGY_LOG even notes breaks looked like genuine breakouts |
| PDLevel S249–S251 | **Fade / bounce** at PD levels — opposite side |

## Cadence path (a priori)

Max 1 trade/day, Mon–Thu → theoretical ≤4/elapsed wk. With filters, expected research band ~1.5–4/wk if edge exists — compatible with GOAL density screen, not a sparse swing book.

## Probe (cheap / offline)

No new price mine. Evidence used: STRATEGY_LOG S159 note that PDH/PDL *breaks* on USDJPY behaved as breakouts (fade dead). That observation is **not** a PF claim for this EA; it only justifies testing the opposite side as an independent Type, with frozen params before any Model 0 readout.

## Fail-closed bans after first readout

No day/hour veto, no buffer/body/EMA retune, no switch to fade, no NY-only window mine, no London-ORB parameter transplant.
