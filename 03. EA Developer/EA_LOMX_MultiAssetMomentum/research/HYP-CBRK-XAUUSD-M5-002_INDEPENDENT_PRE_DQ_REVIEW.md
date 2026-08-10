# HYP-CBRK-XAUUSD-M5-002 — independent pre-DQ review

Verdict: `PASS_PRE_DQ`.

The exact parent-to-current source diff is limited to the just-closed signal clock: full closed bars are loaded, `ServerToUtc(rates[0].time)` supplies weekday and `[07:00,16:00)` eligibility, and the same signal UTC resolves the 72-bar Asian date. `rates[0]` is the just-closed bar under `CopyRates(...,1,...)` plus series ordering. Decision-time `utc_now` remains the position/risk/flatten clock.

Boundary contract: 06:55 reject, 07:00 accept, 15:55 accept, 16:00 reject. No threshold, box/ATR/volume arithmetic, stop/target, risk, exit or lifecycle rule changed.

Evidence reviewed:

- source `A11ABD74BA6A4C051AF7C0EC726A69875CF4CC2B67847E810969460ABD068A6E`;
- prereg `BE1955A3C0847093EEB48D00BEEE951F28F82E0B2E345705E84371AE1AD43759`;
- historical snapshot contract test `D92FFE81152DE123A3038466C1309B28D856A0A64DEE00AD7C7BBFE428FA34CC`;
- clock-fix test `FBAE9695590B257872319FE511D07DC1DDF4B04709F58C98929DDA29EC0474ED`;
- Stage-0 test `B11D85666980CD6AE5A8A037C1AFAE38181662C27529DEF297E39D208D6B30F4`;
- combined focused tests: 15 passed;
- EX5 `F814C68D052B2742D76EDDB6C090D865C3A10E250A5BC9F7CB27EC45BB7CA19A`;
- compile log `A092284E3A1AAC24BE225E82013B9C222273F43AFEA62A5ED4B91380D9B98645`, exactly 0 errors / 0 warnings;
- non-repaint manifest `8CED62E59AA54830099158BB00DF63BD9B2C7EE93EA0A76738D1A87180B2628D`;
- non-repaint audit `DA705028142C8E440B298DE5C7CBFEB5E7E155AAA25A93C60A27D89788C4C235`, PASS with zero findings.

No XAU data, MT5 strategy run, outcome or economics has been opened for HYP002. The only next authority is the zero-trade DQ child requiring exactly 351303 report bars and HQ strictly greater than 97%.
