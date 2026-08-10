# HYP-STC-EURUSD-M15-003 source-to-spec matrix

Verdict: `PASS_BOUNDED_ENGINEERING_REVISION`.

Parent run source SHA256:
`F2ED1064789C9FDC8E7487107938608ECAAF5709656E95DFC8A1EFABC0C0D4ED`.
Current source SHA256:
`1E499F44F9B8CF56CD9350330A443373C2B8729D3D77466365E11FCD163E82A2`.

Allowed changes are limited to:

- package/source name, version `3.00`, hypothesis ID, magic and journal prefix;
- preload last closed bar `2015.12.31 20:00` -> `2015.12.31 19:45`;
- preload population `24,776` -> `24,775`.

The tester-visible boundary is bound by origin proof SHA256
`98D0707FD9C32E58021BCA6FB0DFA954FCDBC819675A3882F273BECC7006AC04`.

Unchanged invariants:

- completed M15 bars and exact +900-second availability only;
- EMA23/EMA50, stochastic10 twice, EMA3/EMA3, carry-50 zero range;
- 25/75 crossing with MACD-sign alignment;
- first eligible signal per server day, no session/HTF/ADX/news/volume filter;
- 0.25% equity risk, ATR14 x1.50 stop, 1.50R target, 16-bar hold;
- one position, Friday/weekend/design-end flatten, daily 3.5% and peak 8% locks;
- DESIGN/validation/holdout windows and all economic gates.

Compile proof: EX5 SHA256
`1BAE892827D5B64671BC53DA37FAAF866494C9124F367318114DC976EE9CA4AF`,
log SHA256 `8B48318494EAD69FF45927FEDEBB009B784A3FD012CC075AED16F78345C151EF`,
exactly one `Result: 0 errors, 0 warnings`.

Focused contract test SHA256:
`4F560A07DC1751EC828C0B703AEEE5DC6B157A2BC3DEBA16579375C74306CFA1`;
12/12 pass. Non-repaint audit SHA256:
`78EF8D9FBC9B03C25408DC9EAAD14F333FFFF57AC781E63EA6A9753FB69F4D3C`;
status PASS, zero findings.
