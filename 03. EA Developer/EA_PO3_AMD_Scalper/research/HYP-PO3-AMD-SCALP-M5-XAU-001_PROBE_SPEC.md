# Offline Probe Spec — HYP-PO3-AMD-SCALP-M5-XAU-001

Status: frozen before first probe run on 2026-07-16. This is not an MT5
Strategy Tester result and cannot promote an EA.

## Purpose and de-dup control

The PO3-AMD report overlaps failed Asian-range sweep/reversal families. The
locked control enters the next M5 open after a London sweep closes back inside
the completed Asian range. The challenger adds the only a-priori mechanism
that can make this family materially different:

`H4 structure + premium/discount -> sweep -> displacement -> MSS -> FVG retest`

If the challenger does not separate from the sweep-only control, the
hypothesis is killed before EA entry code.

## Frozen data and time contract

- Symbol: `XAUUSD`; M5 signal data plus H4 bias data from the current MT5
  broker history, read-only through the MetaTrader5 Python bridge.
- Window: `2022-01-01 00:00:00 UTC` through `2024-12-31 23:59:59 UTC`.
- Canonical session timezone: `America/New_York`, including US DST.
- Asian range: `20:00 <= ET < 03:00`; range belongs to the following ET date.
- Manipulation window: `03:00 <= ET < 05:00`. The report's 02:00 start is not
  used because its Asian box remains open until 03:00 and would look ahead.
- Entry window: London `03:00-04:30 ET` only. NY continuation is deferred to a
  separate hypothesis so this first probe spends only one session degree of
  freedom.
- All signal predicates use completed bars. Simulated entry is the next M5
  bar open after the confirmation close.

## Frozen predicates

- Asian range: `80..300` broker points.
- H4 swing strength: `2`; bias requires the last two confirmed swing highs and
  lows to form HH+HL for long or LH+LL for short. Long also requires price at
  or below the confirmed dealing-range midpoint; short is symmetric.
- Sweep: at least `1` point beyond the Asian boundary and close back inside.
- ATR: Wilder-style `ATR(14)` on M5, minimum `15` points.
- Displacement deadline: next `3` completed M5 bars; body `>=1.5*ATR(14)`.
- MSS: displacement close beyond the last confirmed pre-sweep M5 pivot,
  strength `2`.
- FVG: standard three-candle gap on the displacement bar; no OB fallback.
- Retest deadline: next `6` completed M5 bars; bar overlaps the FVG and closes
  in the intended direction. Entry occurs at the next bar open.
- Maximum one control and one challenger trade per ET trading date.

## Frozen management and cost proxy

- Structural SL: sweep extreme plus `40` points.
- BE after `1R`; close `50%` at `2R`; final target `3R`.
- If `1R` is not reached in `30` minutes, close at that bar's close.
- Maximum hold `90` minutes and hard flat by `16:00 ET`.
- Intrabar ambiguity is conservative: stop is evaluated before favorable
  milestones on the same bar.
- Research cost proxy: `20` spread points + `8` round-turn slippage points +
  `7` commission-equivalent points = `35` points per completed trade. This is
  an assumption from the report, **not verified broker cost provenance**.

## Frozen pass/kill gates

The challenger passes the cheap probe only if all are true:

- `2.0 <= trades / elapsed calendar week <= 5.0`;
- cost-proxy PF `>=1.50`;
- mean net expectancy `>=0.40R`;
- max drawdown at `0.25%` risk per trade `<=5%`;
- positive net R in at least `2/3` calendar years;
- challenger net R is positive and not below the sweep-only control;
- challenger PF exceeds control PF by at least `0.20`.

No threshold, session, direction, year, SL/TP, or filter may be changed after
reading the result under this hypothesis ID.
