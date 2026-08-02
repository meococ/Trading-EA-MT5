# HYP-VRAS-USDJPY-M5-001 — plan review and corrected implementation route

## Verdict on the supplied plan

`final_ea_build_plan.md` is not safe to implement literally.

1. Its headline Hurst, VR(5), and OU half-life values were attributed to
   EURUSD/EURJPY, but the independently parsed `design_m1_close.parquet` is a
   concatenation of EURJPY, EURUSD, and USDJPY. The quoted `H=0.4612`,
   `VR(5)=0.8654`, and `HL=89.43 M1 minutes` identify the USDJPY segment.
2. The plan's execution command still targets EURUSD, so the evidence symbol and
   deployment symbol are not aligned.
3. True CVD, VPIN, and order-book OFI are not identifiable from retail OHLCV
   bars. Relabeling candle/tick-volume transforms as those fields would create a
   false data contract.
4. The three-engine regime switch has no frozen estimator windows, uncertainty
   bounds, conflict arbitration, or independent outcome-blind evidence for the
   sweep and Volman branches.
5. The proposed asynchronous send/timeout-reset design can duplicate a late fill.

## Corrected route implemented

- Fresh hypothesis: `HYP-VRAS-USDJPY-M5-001`.
- Correct target: USDJPY M5, `[22:15,05:30) UTC` Asian sleeve.
- Correct source: FiveAssetFoundation USDJPY M5 parquet, SHA256
  `FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD`.
- Atomic engine: closed-bar OU mean reversion only.
- No true-flow or multi-engine claims under this ID.
- Synchronous `OrderCheck` + `OrderSend`, broker-side SL/TP, persistent risk
  latches, and lifecycle-v3 telemetry.
- Matched direction control remains frozen, but no economic run is legal until
  same-symbol cost provenance passes the AlphaFactory gate.

This is the full legal successor implementation of the evidenced mechanism. It
does not pretend that the invalid branches in the supplied plan became valid
because their names were replaced by proxies.
