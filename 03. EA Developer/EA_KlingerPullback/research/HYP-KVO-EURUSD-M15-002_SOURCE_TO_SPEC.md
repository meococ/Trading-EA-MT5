# HYP-KVO-EURUSD-M15-002 — Source-to-spec matrix

| TradingView concept | Frozen implementation |
|---|---|
| Trend from current versus prior `H+L+C` | Completed M15 bars only; equality is `-1` |
| Volume Force | Broker `tick_volume * 2 * (DM/CM - 1) * trend * 100`, no absolute value |
| Klinger line | SMA-seeded EMA34(VF) minus SMA-seeded EMA55(VF) |
| Signal line | SMA-seeded EMA13(KO) |
| Long-trend context | Completed close above SMA-seeded EMA100(close); short inverse |
| Documented pullback/re-entry | Arm beyond zero against the price trend; emit only on signal-line recross before KO crosses zero |
| Flat source history | First positive two-bar range starts recursion; later zero-CM flat bars contribute VF=0 |
| MT5 volume | Native M15 tick volume only; explicitly not centralized money/aggressor flow |
| Causality | State advances only with completed bars; entry uses exact next M15 open timestamp |

Boundary fixtures must cover: equality trend `-1`; first positive seed after flat history; later zero-CM flat sequence; zero tick volume; EMA seed indices; prior equality/current strict cross; KO zero arm/trigger behavior; no same-bar rearm; exact `+900s` execution; UTC daily cap; stop rounding and 16-bar exit.
