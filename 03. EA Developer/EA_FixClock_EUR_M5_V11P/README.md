# EA_FixClock_EUR_M5_V11P

No-trade EURUSD M5 clock preflight for V11 WMR London-fix research. It classifies the FivePercent server as US-DST/NY-close or EU-DST from weekend-open bars during the frozen 2018 UK-US DST mismatch weeks.

Run `20260812_024540` passed as `US_DST_NY_CLOSE`: 3/3 mismatch-week opens were Monday 00:00 server, with zero copy failure. V11 fix time is therefore 18:00 normally and 19:00 during UK-US DST mismatch intervals.
