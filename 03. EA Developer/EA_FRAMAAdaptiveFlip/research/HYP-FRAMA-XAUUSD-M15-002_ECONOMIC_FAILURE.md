# HYP-FRAMA-XAUUSD-M15-002 — economic baseline failure

Verdict: `KILL_BASE_PF_EXPECTANCY_AND_YEAR_CONCENTRATION_FAIL`.

The sole frozen untuned XAUUSD M15 Model-0 TRAIN baseline completed engineering-valid with no runtime fatal. It generated 657 completed positions over 260.857 elapsed weeks.

## Frozen gates

- PF `0.6027644578` — FAIL versus strict `>1.30`.
- net `-$7,009.96`; expectancy `-$10.66965/trade` — FAIL.
- cadence `2.5186/week` — PASS versus `2–5/week`.
- equity DD `7.7987%` — PASS below 8%, but with negligible safety margin.
- direction split BUY 389 / SELL 268 — PASS both >=30%.
- calendar years 258 / 258 / 135 / 3 / 3; max share `39.27%` — FAIL versus <=30%.
- win rate `36.38%`; report commission `-$501.06`; swap `$0`.

This kills only the exact native FRAMA16 price-crossover + five-bar/0.20ATR stop + 1.50R/12-bar lifecycle. It is not evidence against all adaptive moving averages.

No day, hour, session, direction, stop/target, daily cap or FRAMA-period rescue is allowed. Cost stress, optimization, validation and holdout remain unopened because the report-cost baseline already fails decisively.

## Evidence

- run `20260810_220732`
- run manifest `B816D83AA2589B3D1CFCE2930C0FBDE83D08271194527870E6DD4F7A52EC48D1`
- report `7F937AABA29373D84318D3DD774FF6B3FE29AE85ECD44BAF29EB94B2F12E31EC`
- tester journal `F5845A03580B6B1496A803C8C6A5B98C54D4C489E21E82694244FF5574F24ECD`
- enhanced summary `95DA186D339A3BA5F682535CD0195B2BD1AA4BBE606EA91D56DE0DA16BA2FC77`
- executed source `6D2F21FCD53097DE82CA584A53CC507EBAC03A0056A4DA9137B46A12CFE2855F`
- executed EX5 `F5EFEB9ED33BE818D889FB918169A9FD1CCA85DAE6149AB99FD652998E5897D9`
