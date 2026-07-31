# HYP-VRAS-EURUSD-M5-012 feed-smoke readout

## Verdict

`PARK_FORWARD_SMOKE_TICK_CLOCK_MISLABELED_NO_OUTCOME`

The collection-only source passed 57 independent tests, MetaEditor compile
0 errors / 0 warnings, exact-source non-repaint audit and zero forbidden trade
API matches. The one authorized 120-second read-only broker-feed smoke connected
to the exact `FivePercentOnline-Real` server and wrote 239 heartbeats plus 49
EURUSD quote rows with `orders_sent=0`, `positions_opened=0` and
`live_trading_authorized=false`.

The chronology contract is nevertheless invalid. `session_start.json` was
created at `2026-07-23T02:25:36.339590Z`, while the first quote's raw
`time_msc=1784784337089` was rendered as
`2026-07-23T05:25:37.089000Z`. The approximately +10,800-second difference is
the broker server clock offset, not UTC. The producer converted server-clock
epoch milliseconds with `datetime.fromtimestamp(..., UTC)` without first
subtracting the observed server-to-UTC offset. The MQL5 EA used the same raw
tick-clock assumption in its telemetry formatter.

The generic bundle validator returned `STOP_DATA_FRONTIER` but did not detect
the future-of-manifest timestamp because it checked only row-internal
`time_msc`/`time_utc` consistency. Therefore that validator also needs an
absolute capture-clock coherence gate.

## Evidence

- Capture ID: `20260723_VRAS012_FEED_SMOKE_001`.
- Session-start SHA256:
  `77A8E52A65E5EB1453177C0788CBBBB64EC7106D656BF9899383A3D78796F437`.
- Session-end SHA256:
  `C3A213ADF5583C510856CDF3E6C8A059485A91F8417B871CAEC2756F94C3580A`.
- Manifest SHA256:
  `450FADAF07FEBAD5B745A949C78B5E662B585E2C3BF99335D253960E246AB582`.
- Quote CSV SHA256:
  `104531AC8FD3651D1BFA0E97A9F055AD0E7FDB063ABB16E7C940145F91649381`.
- Generic validation SHA256:
  `BA54BDFE2AC70D8B18F4E10874D7EB1675EA41EE27D2196CA91AE835E349FC08`.
- Engineering receipt SHA256:
  `F6A447D8E2815F339BD239A29BBCC434848D8B4F54E65FA84A46E85495C2BB02`.

## Epistemic boundary and next move

No arm, acceptance event, trade, PnL, return, SL/TP, economic metric or outcome
was opened. The 49 quote rows are invalid as UTC HYP-012 research data and may
not be appended to a forward corpus. HYP-012 receives no repair or rerun.

A fresh administrative successor may preserve every frozen signal/acceptance
threshold while changing only the clock/data contract:

1. keep raw broker tick time for provenance;
2. infer/freeze the broker UTC offset from capture receipt time versus the first
   fresh quote, rounded to 15-minute timezone increments and fail closed if the
   residual is excessive;
3. write normalized UTC `time_msc` and ISO-8601 `time_utc`;
4. reject any quote timestamp materially future to the capture manifest;
5. keep account-history reads disabled and all order surfaces absent.

