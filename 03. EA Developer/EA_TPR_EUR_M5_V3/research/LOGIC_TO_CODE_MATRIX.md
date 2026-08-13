# Logic-to-code matrix — HYP-TPR-EURUSD-M5-001

| Frozen rule | Code authority |
|---|---|
| Completed M5 only | `CopyRates(... PERIOD_M5, 1, ...)`; all indicator buffers start at 1 |
| Trend expansion | `DetectTrend`: EMA order, body/ATR and five-bar highest-lowest range |
| Forward-only pullback/resumption | `g_state`, `g_trend_time`, `g_trend_age`, stored pullback bar |
| Next-bar entry | exact five-minute availability assertion before `SubmitEntry` |
| Structural stop | stored pullback extreme vs resumption EMA21, 0.25 ATR buffer, 1.10..2.40 ATR clamp |
| Runner exit | no TP; tick-triggered BE+, closed-bar ATR trail, 24-bar time stop |
| Capital protection | minimum of risk/notional/margin volume with post-normalization checks |
| Evidence compatibility | canonical M5/M1 D0 series proof and complete state/entry/exit telemetry |
