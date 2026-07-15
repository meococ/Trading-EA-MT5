# De-dup clearance — London ORB vs Spark / HourOpen / InsideBar

Date: 2026-07-14  
Verdict: `INTAKE_CLEARED / INDEPENDENT`  
Hypothesis: `HYP-LONDON-ORB-M15-001`

## Question

Is London first-hour opening-range breakout on USDJPY M15 a new family, or a
cosmetic twin of killed/parked books from tonight?

## Comparison

| Family | Mechanism | Verdict |
|---|---|---|
| Spark Asian (PARK) | Overnight Asian `[0,8)` range → LDN/NY break; Tue–Wed | **Different range clock + day set** |
| HourOpenBreak (KILL) | Per clock-hour micro-range on EURUSD; CI/EMA gated | **Different: single London auction ORB, not every hour** |
| InsideBar (KILL) | Mother/inside geometry + KZ | **Different: session ORB, not bar nesting** |
| VolExp / TickVol (KILL) | RV-ratio / tick spike continuation | **No vol impulse gate** |
| ChopTrend (FAIL_CLOSED) | CI + EMA cross trend | **No CI** |
| LondonSweep/Judas (dead) | Fakeout reclaim after sweep | **Opposite: continuation breakout, not fade** |
| ITSM (do-not-reopen / PARK) | EMA zone pullback | **Not pullback** |
| SB (PARK) | FVG SilverBullet | **Not FVG** |
| USBILL (KILL) | Exogenous bill-slope basket | **Price-only ORB** |

## Cadence path

Mon–Thu × ≤1 trade/day → structural upper bound ~4/week; expected ~2–3/week
if break frequency is moderate — inside GOAL 2–5 band, denser than Spark
Tue–Wed (~1.25/wk parked).

## Clearance

`INTAKE_CLEARED / INDEPENDENT`. Authorize prereg → Model 0 screen. Do not
retune from Spark/HourOpen losers.
