# HYP-XAU-SIGNED-QUOTE-ABSORB-002 — Frozen source gate

Status: frozen before any signal count or economic readout.

Authority: source/capability only. This run sends zero orders and authorizes no performance claim.

## Mechanism

The candidate measures signed quote revisions, not trade aggressor flow. For each strictly ordered valid `MqlTick`, `BidUp/BidDown` are the sign of the Bid revision and `AskUp/AskDown` are the sign of the Ask revision. `NetSignedPressure = (BidUp-BidDown) - (AskDown-AskUp)`. A fade is eligible only when this pressure does not move the mid-price proportionally during the same closed 30-second window.

## Frozen source cell

- Symbol: `AFD_XAUUSD_DUKA_V3`.
- MT5 model: 4, Every tick based on real ticks.
- Period: M1.
- Window: 2018-01-01 through 2022-01-01 exclusive.
- Decision window: `(M1 close - 30,000 ms, M1 close)`; a quote exactly at the left edge establishes the starting mid but contributes no event.
- Duplicate millisecond timestamps: process in tester arrival order.
- Invalid quote: reject if Bid or Ask is non-finite/non-positive or `Ask <= Bid`.
- Simultaneous two-sided revisions: count each changed side once.
- Signal threshold: `abs(NetSignedPressure) >= 8`.
- Absorption: long when pressure `<= -8` and 30-second MidMove `>= -0.12 * ATR(14)`; short when pressure `>= +8` and MidMove `<= +0.12 * ATR(14)`.
- Entry-cost gate evaluated at the first tick of the next M1: spread `<= 0.30 USD`.
- Warmup: 500 completed valid M1 bars.
- Entry clock: Monday-Friday 01:00-21:00 custom-symbol time; Friday entries stop at 18:00.

## Source gates before economics

All must pass:

1. imported custom-symbol receipt remains daily-count/readback PASS for 3,134 days and 457,065,926 ticks;
2. MT5 report History Quality is greater than 97 and journal identifies real-tick execution;
3. valid quote ratio and observed M1/bar ratio are each at least 98%;
4. at least 350 design signals, with at least 40 in every calendar year 2018-2021;
5. median absolute signed pressure among signals is at least 9;
6. no reverse timestamp and no quote-queue overflow.

If any source gate fails, do not inspect economics. A passing source gate authorizes one separately packaged baseline with the already frozen economic constants: SL `clamp(1.7*ATR14, 0.35, 1.60 USD)`, TP `1.25R`, seven-bar time stop, 0.20% equity risk, one position, no Friday entry after 18:00, flat before weekend. Spread is native Bid/Ask; stress adds 0.05 and 0.10 USD round-turn. Design economics are 2018-2021 only; 2022-2023 validation and 2024-2026-07-31 holdout stay sealed.

## De-dup signature

This is signed quote-revision absorption. It is not unsigned tick intensity, trade-side CVD, spread dislocation, immediate quote continuation, candle geometry, or range breakout.

## Source identity

- source contract SHA256: `C24BB36FF90B45286D7F6E1CB5E28AD7D2820CAFEE82893E97D426A6D40BD330`;
- range manifest SHA256: `E3D03C085191BD2DE4BC3098ED808C5B0207E71655EAA59D93647E813D9C7A26`;
- import plan SHA256: `79497691E00F9A62DAE541C8EC41D1289B717F43E17EADF1B7A004A6C7C9CE16`;
- active MQL receipt SHA256 at audit: `D44B092B44A1DD6D7FB0D447D44E79EA22A6F9577E13A42B8D2C02336198CB24`.

The Dukascopy custom symbol can establish research economics only. FivePercent forward/demo tick and execution parity remain mandatory before promotion.
