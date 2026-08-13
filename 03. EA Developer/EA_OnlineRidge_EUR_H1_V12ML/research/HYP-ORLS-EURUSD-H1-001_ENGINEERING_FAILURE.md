# Engineering failure - HYP-ORLS-EURUSD-H1-001

Verdict: `INVALID_RUNTIME_ARRAY_BOUND_NO_ECONOMIC_READOUT`.

AlphaFactory run `20260812_031618` compiled with zero errors and launched EURUSD H1 Model 0 at HQ100, but stopped on `2018.01.02 00:00` before processing the requested window. The journal reports `array out of range` at source line 113. The ATR24 loop read `r[i+1]` through index 25 while `CopyRates` allocated only 25 elements, indices 0..24.

The report contains zero trades and AlphaFactory correctly rejected economic analysis. No PF, PnL, drawdown or market-edge conclusion is admitted. The exact fix is a runtime-only buffer bound change from `need=25` to `need=26`; the economic feature, model, label, hurdle, lifecycle and risk contracts remain byte-semantically unchanged under fresh package `EA_OnlineRidge_EUR_H1_V12MLR1` and hypothesis `HYP-ORLS-EURUSD-H1-002`.

Original source SHA256: `55507C9B300992165119E02BFAD7EC0FD8810369F268DFAD730A64C1FDE9E3AB`. Original run artifacts remain under `02. AlphaFactory/runs/EA_OnlineRidge_EUR_H1_V12ML/20260812_031618`.
