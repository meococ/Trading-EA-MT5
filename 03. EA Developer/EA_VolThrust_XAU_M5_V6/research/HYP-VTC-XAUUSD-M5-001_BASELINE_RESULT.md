# Baseline result - HYP-VTC-XAUUSD-M5-001

Verdict: `KILL_NEGATIVE_EDGE_OVERTRADING_ACCOUNT_STOP_OUT_NO_OOS`.

AlphaFactory run `20260812_014617`, XAUUSD M5 Model 0, current broker spread, HQ100. Engineering passed: fresh compile `0 errors, 0 warnings`, static contract `14/14`, non-repaint audit PASS, no missing tick volume, no entry rejection, and maximum logged margin use 9.9997% within the frozen 10% cap. The account stop-out threshold ended execution on 2018-07-31 at 14% of the requested 2018-2021 interval.

Performance before stop-out: 264 trades; net `-$10,017.36`; PF `0.6364`; WR `41.7%`; expectancy `-$37.94/trade`; max DD `10.4393%`; maximum losing streak 11. Telemetry: 38,706 closed bars, 608 thrusts, 282 controlled pauses/signals, 264 entries, 2 spread rejects, 16 overlap skips, and no missing volume. There were 264 entries in 126 days, with as many as 6 in one day, already far above the intended four-year cadence trajectory.

For 263 telemetry-recorded exits, 239 `SL`-reason exits netted `-$11,419.94`, 22 time stops netted `+$2,029.78`, and 2 daily flats netted `+$65.16`; the last open trade was closed by account stop-out. Every major session was negative: Asia PF 0.81, Europe PF 0.50, and New York PF 0.62.

Chart readback: equity declined from January through March, temporarily recovered to a new high in early April, then entered a persistent near-monotonic collapse through July. Drawdown did not recover and terminated near its path worst at about -10.4%. This is a structural signal failure, not a missing-data, sizing-cap, compile, or sparse-sample defect.

Kill the exact broker tick-volume thrust, four-bar controlled-pause continuation, thrust-structure ATR stop, BE/ATR trail, and 24-bar time-stop object. No session/day/hour filter, cooldown insertion, matched control, OOS/holdout, or parameter/exit retuning is authorized.

Evidence hashes: source `F300E690BA65A1E696755611903755FB2CD83DDD4A70F47455155B5EAEECDC92`; EX5 `9F4D8409A02B7DC7C50AC18527745444FECADC725AFA5002DF1D69403E0A4200`; report `6A967DFBD94283DB769A4F816620B03848567C18E7327F516269CE9A0D11D4AC`; journal `8F91465A300041DB5D04336B01F1F37E5BADA3CBD9243096CB88DF9C723349BC`; chart `C7EE5412EFD9AEE33635C585A7E672B66E36EBB27E518E1380F1BCE3477D6EE1`.
