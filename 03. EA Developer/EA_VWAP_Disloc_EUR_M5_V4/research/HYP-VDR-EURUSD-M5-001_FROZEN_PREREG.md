# Frozen prereg — HYP-VDR-EURUSD-M5-001

Status: FROZEN before compile/outcome execution on 2026-08-12. Origin: Grok `/deep-research-trading-meta5` loop 4 after V3 negative-edge/overtrade kill.

EURUSD M5 Model 0 design `[2018-01-01,2022-01-01)`. Completed bars only; next-bar entry; one position; no weekend; maximum hold 24 bars. Rolling VWAP uses typical price and broker tick volume over terminal shifts 1..18; volume SMA uses the same shifts. Any missing/zero OHLC or tick volume fails closed (repo hard rule supersedes Grok's fallback-to-one suggestion).

Dislocation: `abs(Close[1]-VWAP18)>=1.35*ATR14[1]` and `TickVolume[1]>=1.45*VolumeSMA18`. Store sign, close extreme and time. During the next six completed bars, the first opposite-color bar whose close moves toward the stored extreme and whose body/range >=0.35 triggers next-bar reversion entry. Otherwise expire. Entry spread <=15 points.

Stop beyond stored dislocation close by 0.30 ATR, clamped to 1.00..2.30 ATR from entry. No TP/partial close; +0.90R moves stop to +0.12R, +1.50R arms a 0.70 ATR closed-bar trail; time stop 24 bars; daily/Friday flat 21:50/18:50. Risk locks 1.00% daily/2.50% weekly. Volume is the normalized-down minimum of 0.25%-stop-risk, 4.50x-equity notional and 12%-free-margin caps with post-normalization checks.

Primary `VWAP_STATE_PRIMARY`; locked control `VWAP_DISTANCE_CONTROL` ignores volume/reversion confirmation and immediately fades each 1.35 ATR distance event with identical downstream rules.

Kill for invalid runtime/data, incomplete design window/account stop-out, trades outside 160..600, PF <1.12, expectancy <=0, DD >6.5%, top-three exits >35% net or margin >12%. Only a full design pass may open matched control/OOS. No optimization or subgroup filtering.
