# Clock preflight result - HYP-FIXCLK-EURUSD-M5-001

Verdict: `PASS_US_DST_NY_CLOSE`.

AlphaFactory run `20260812_024540`, EURUSD M5 Model 0, HQ100, no trades. The probe observed 74,431 new bars, 54 weekend gaps, zero copy failures, and all three frozen UK-US DST mismatch-week opens at Monday 00:00 server. None opened Sunday 23:00. Outside mismatch weeks, 49 of 51 opens were Monday 00:00 and two holiday/week anomalies were retained as non-authoritative diagnostics.

The FivePercentOnline-Real history therefore follows the common NY-close/US-DST server convention. V11 must use WMR London 16:00 at 18:00 server normally and 19:00 server during the spring and autumn UK-US DST mismatch intervals. This receipt authorizes only the clock mapping, not trading economics.

