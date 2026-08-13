# Baseline result - HYP-VRE-EURUSD-M15-001

Verdict: `KILL_NEGATIVE_EDGE_OVERTRADING_STOP_OUT_NO_OOS`.

AlphaFactory run `20260812_021633`, EURUSD M15 Model 0, current broker spread, HQ100, requested 2018-2021 window. Engineering passed: fresh compile `0 errors, 0 warnings`, static contract `15/15`, `runtime_failed=false`, 51,501 completed decision bars, no entry rejection, no close rejection, and maximum observed margin usage `2.8123%`.

The run stopped out on `2020.04.01 13:30` after only 56% of the requested interval. It produced 662 trades; net `-$10,009.71`; PF `0.8433`; WR `46.4%`; expectancy `-$15.12/trade`; max DD `10.8502%`. Cadence also exceeded the frozen 200-520 design band before the full period could finish.

Runtime observed 1,412 expansion bars, 680 immediate confirmations, 732 confirmation failures, 680 signals, and 662 entries. The immediate-confirmation gate therefore rejected 51.8% of expansions but did not isolate profitable continuation. Logged exits comprise 349 SL exits (`-$17,636.51`), 286 time stops (`+$12,394.68`), 22 Friday flats (`-$572.38`), and 4 daily flats (`+$239.46`), plus the final unlogged stop-out close. The 661 logged exits sum to `-$5,574.75` before the report-level cost/final-close gap; the final report is another `-$4,434.96` lower. The price path was already negative before that gap, so transaction cost is an amplifier rather than the root cause.

The equity chart shows brief recoveries in 2018 and late 2019 inside a persistent lower-high/lower-low path, followed by a fresh collapse into the April 2020 stop-out. There is no durable recovery regime to promote.

Kill this exact EURUSD M15 ATR(8)/ATR(40) >= 1.55 expansion plus immediate same-direction confirmation object. Do not rescue it by selecting Tuesday/Thursday, removing Europe/Asia hours, changing the confirmation threshold, or tuning stop/trail/time exit from this readout. No matched control, OOS, holdout, or optimization.

Evidence hashes: source `93608598C5CB1ABD2535D5563474A725ACDB8BD3348ECEC71694768DFBD0BDC5`; EX5 `064E20D78349AC5A697DC2FAF56DF7C5D7665ABFE8F805A035B5DB82E638688F`; report `CC279FA04B9BC5C4554D54AD3578BEA1AC59B7ABB7B18E1AF84494B9777E8C67`; journal `0D184BCB8E3001D800D9DE47C455A4981EE537454A152AC5AA74CF6B57369CA3`; chart `32DA8F00B7A1203FE30F43A0024FC15BA8B0C52BEFAFBD2BD42C32C19E1926CC`.

