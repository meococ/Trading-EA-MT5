# Frozen preregistration - HYP-VRAS-EURUSD-M5-001

Status: FROZEN PRE-OUTCOME on 2026-07-22. Owner explicitly authorized a
build-first exception and removed the prior de-dup/pre-code veto. This file is
not a permission gate for source construction; it freezes the object before
any new VRAS outcome is read. Once its SHA is appended to the registry it is
immutable.

## Identity and sources

- EA: `EA_VRAS_RegimeAdaptiveScalper`
- Symbol/timeframe/model: `EURUSD / M5 / MT5 Model 0`
- Diagnostic design window: `2019.01.03-2022.12.31`; `2023+` stays sealed.
- Primary report SHA256:
  `AB57D7D3F8993784C9B0016E4347BB7D093122A539C0A741C0389648AD014F0C`.
- Technical-gap Google export SHA256:
  `DDBBCAD8F6DF1AD1DCD87855F3812B4DDC1F2DD775F9F74911B5686B3DFBD1B7`.
- Market data: FivePercent EURUSD M1/M5 history on D. The known historical
  spread field is not promotion-grade; `promotion_eligible=false`.

## Frozen primary decision surface

- Closed-bar decisions only. `iTime(...,0)` is only the new-bar gate. All rates
  and indicator reads start at shift 1. Market entry is first available quote
  after confirmation bar close.
- ADX(14) regime: RANGE -> TREND when ADX >= 25 and the current state has lived
  at least 6 closed M5 bars; TREND -> RANGE when ADX < 19 after the same dwell.
  The 19-25 gray zone retains state. Regime replay on restart is mandatory.
- Session VWAP/SD: typical price `(H+L+C)/3`, tick-volume weighted Welford
  population variance, reset at London 08:00 local. Warmup 15 positive-volume
  bars. Mean-reversion requires `SD >= 0.30*ATR(14)`.
- Trading window: London 08:00 local through New York 16:00 local. Clock uses
  explicit broker winter UTC+2 with US-DST-following offset and independent
  EU/US DST calendars. No hardcoded current offset.
- RANGE branch ignores directional bias. Long requires close <= VWAP-2SD,
  bullish rejection/engulfing and RSI(14)>25. Short is exact mirror at +2SD
  with RSI<75. Target is entry-time Session VWAP. Stop is the farther of
  rejection extremum plus 0.30 ATR or 2.5SD.
- TREND branch applies Session-VWAP bias. Long requires close above VWAP,
  a VWAP/-1SD pullback-reclaim, bullish rejection, latest confirmed five-bar
  swing-low AVWAP support and closed M15 price above its same-session VWAP.
  Short is exact mirror. Trend target is fixed 1.80R; stop is rejection
  extremum plus 0.40 ATR.
- Fractal center becomes available only after two newer bars close. Search is
  at most 60 M5 bars. No valid directional anchor means no trend entry.
- Rejection pinbar: body/range <=0.40 and directional wick/range >=0.50;
  engulfing is a closed-bar alternative. Equality is accepted at the limits.
- One position/order per symbol. Open-trade SL/TP/time-stop are not changed by
  a later regime flip. No partial, trailing, break-even, averaging or martingale.
- Risk 0.25% equity/trade; max spread 1.20 pip; max 3 trades/day; daily equity
  loss 1.50%; account peak DD 6%; max hold 20 M5 bars; flatten at NY 16:00.
- Cost filter uses `EstCost=max(current spread, 0)+0.70 commission +
  2*0.40 one-way slippage` pip and requires target distance >= 8*EstCost.
  It never stretches a target to manufacture eligibility.
- High-impact news guard is coded fail-closed and enabled for the primary run
  only when the hash-bound 2019-2022 calendar include is present. The source is
  diagnostic, not official or promotion-grade.

## Frozen sensitivity universe

Exactly four predeclared diagnostic arms; cost tiers are not separate trials:

1. Primary: tick-volume weighting + London-open anchor.
2. Volume sensitivity: equal-weight TWAP + London-open anchor.
3. Anchor sensitivity: tick-volume + 00:00 UTC anchor.
4. Anchor sensitivity: tick-volume + broker daily-open anchor.

Primary failure is not rescued by another arm. Sensitivity arms measure feed
and anchor dependence only. No optimizer, threshold grid, symbol change,
hour/day/year veto or 2023+ access is authorized under this ID.

## Acceptance and terminal rules

- Engineering: all unit/contract tests pass, compile 0 errors/0 warnings,
  exact-source non-repaint PASS, lifecycle-v3 reconciliation complete.
- Primary economic research gates (diagnostic because costs are unverified):
  at least 350 trades; 2-5 trades per elapsed calendar week; native/current
  cost PF >=1.30; max DD <=6%; no single year or direction supplies >55% of
  positive net result.
- Robustness red flags: TWAP signal-set collapse or materially different
  economics, excessive regime switching (>4/day), anchor dependence, or any
  overlapping-window replay mismatch.
- Missing verified cost provenance, missing official news provenance, or only
  one broker feed prevents promotion even if diagnostic metrics pass.
- Any post-result fix/tuning requires a new hypothesis ID. No rescue of 001.

## Prior and build-first exception

Historical VWAP/mean-reversion evidence is adverse and remains disclosed, but
the Owner's current build-first instruction supersedes the earlier
`KILL_AT_DEDUP_NO_BUILD` veto. The differentiating tested object is the complete
seven-gap implementation: hysteretic regime state, weighted Welford bands,
explicit branch FSM, DST/session clock, confirmed AVWAP, shadow TWAP and
cost-distance rejection. This is not a claim that the edge exists.
