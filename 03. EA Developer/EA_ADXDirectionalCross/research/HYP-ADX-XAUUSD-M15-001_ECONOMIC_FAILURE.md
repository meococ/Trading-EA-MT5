# HYP-ADX-XAUUSD-M15-001 — economic baseline failure

Verdict: `KILL_BASE_PF_EXPECTANCY_AND_CADENCE_FAIL`.

The sole untuned run `20260810_230823` is engineering-valid: source SHA `CEA49A1F897727451E16C8C18B1ABAFD273B3FAB4CCD7191F4723D49F87DB2EF`, manifest `48D95A4E1F28E97B42A7A10A46A49481848D41D9FDC32D077AE10C97D4434545`, report `A71454CEA9E2D2622D4B54C4066A47A8DAD2E1D2D7F66A51B43CA59C63E7356C`, journal `36B5D5685FE1CBA917B62CD3D9FCE3FC83E1BC1FDE34AAAA56F8790B40198786`. HQ99/full coverage, journal nontruncated, two identical summaries, no fatal marker and `runtime_failed=false`.

- Raw closed-bar events `71`; accepted positions `61`; `27W/34L`.
- PF `0.9302921538`, net `-347.64`, expectancy `-5.6990163934`; commission `-146.18`, swap `-552.42`.
- Cadence `0.2338444688/week` over the full five-year window — far below `2/week`.
- BUY `31`, SELL `30`; years `10/9/16/12/14`, max-year share `26.2295%`; DD `1.6868%`.

Kill the exact native ADX14 DI polarity cross with current ADX>=25 and rising, one accepted entry/day, five-bar plus 0.20ATR stop, 1.50R target and 12-bar exit. Do not rescue by changing ADX period/threshold, removing the rising condition, changing timeframe/session/direction, or changing exits/risk. Validation and holdout remain unopened.
