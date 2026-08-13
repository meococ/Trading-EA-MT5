# Baseline result - HYP-LAR-GBPUSD-M15-001

Verdict: `KILL_NEGATIVE_EDGE_FULL_SAMPLE_NO_CONTROL_NO_OOS`.

AlphaFactory run `20260812_013453`, GBPUSD M15 Model 0, current spread, HQ100, full requested design window from 2018-01-01 through 2021-12-31. Engineering passed: fresh compile `0 errors, 0 warnings`, static contract `9/9`, closed-bar non-repaint audit PASS, 369 entries on 369 unique broker days, no duplicate-day entry, no entry rejection, and maximum logged margin usage 2.8943%.

Performance: 369 trades; net `-$7,590.00`; PF `0.7861`; WR `46.3%`; expectancy `-$20.57/trade`; max DD `8.4369%`; maximum losing streak 6. The design fails both preregistered PF >= 1.15 and DD <= 6% gates.

Journal exit decomposition before report-level commission/cost: 208 `TIME_STOP` exits netted `+$11,936.31` (average `+$57.39`), while 161 `SL` exits lost `-$18,433.95` (average `-$114.50`). The report net is another `$1,092.36` lower, consistent with transaction costs. The structural loss is therefore not a telemetry, cadence, position-sizing, or incomplete-window defect.

Chart readback: equity temporarily recovered above its initial balance in late 2018 and early 2020, but formed a persistent lower-high/lower-low decline from mid-2020 through the end of 2021. Drawdown failed to recover and finished near its worst point around -8.4%. The path is not a few-winner concentration artifact; it is sustained negative expectancy.

Kill the exact overnight-balance London break, mandatory separate-bar retest/resumption, structural opposite-edge stop, BE/trail, and 16-bar time-stop object. Do not rescue it by weekday/hour/year exclusion or threshold/exit retuning. No matched control and no OOS/holdout are authorized.

Evidence hashes: source `4860673013511455C51C38B850E94F937C936FEC95DA54F5B12A78BC2944D8DA`; EX5 `6F15A32631720A1185DC059884001587297E38A22A09C1166B8CD3167B2CC1D9`; report `51582F211D72159F6A1A86E672622FB2E7CCEEC222BC14F862D04F69C4535A4C`; journal `B61129BACF408B09D2D74EEB639CF19C8061F85450C44C1F053B725945D20195`; chart `EF34A2DDA12B92776156343583664C8BD1BF890DDF02FFF3A48ABEDA54D96609`.
