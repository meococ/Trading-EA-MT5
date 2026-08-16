# Sonic R system — invariant rules

Status: `FROZEN_ENGINEERING`  
Package: `EA_SonicR_PVSRA` v1.20  
Not an edge claim. Classic cell `HYP-SONICR-CLASSIC-EURUSD-M15-001` remains KILL hẹp (PF 0.94).

These rules are TAH/Kyaw public doctrine plus repo hard gates. They do **not** create expectancy. They keep the machine more disciplined than a person.

## Always on (DisciplineHost)

1. One position. One pending. Same symbol + magic.
2. Never add to a loser. No grid, martingale, DCA, scale-in.
3. Scout compile-off. PVSRA cannot open a trade.
4. No Asian session entries. London 08:00–16:00 only (signal-bar clock).
5. Flatten Friday 20:00 London and all weekend. No weekend hold.
6. At most 5 new entries per ISO week. At most 2 per calendar day.
7. SL beyond wave leg-1. Skip if SL > 120 pips on EURUSD. Do not shrink.
8. Pending several pips beyond the signal candle. TTL 4 M15 bars.
9. Daily lock 3.5%. Account DD lock 8%, persisted across restart.
10. Kill switch and spread gate fail-closed.

## Context (scanner / indicators only)

- Dragon EMA34 H/C/L, Trend EMA89, PVA rising/climax colors, WHQ runway.
- PVA colors help **read**. They are not long/short.
- Build vs run is **not** an order veto (not measurable on FX tick volume).

## Signal object

- Classic L–H–HL / H–L–LH, first close beyond Dragon, pending, WHQ TP.
- Economics of that object are already killed on train `20260816_205426`.
- This drop implements the **system shell**. It does not reopen 001.
