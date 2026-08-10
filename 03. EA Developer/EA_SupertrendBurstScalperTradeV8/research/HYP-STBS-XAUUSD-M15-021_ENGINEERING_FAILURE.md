# HYP-STBS-XAUUSD-M15-021 — Engineering Failure

## Verdict

`KILL_ENGINEERING_NR_PROVENANCE_PROPAGATION_AND_ACTUAL_MONEY_MARGIN_HALT_NO_ECONOMIC_VERDICT`

The sole authorized Model-0 TRAIN attempt is consumed. MT5 produced a report and complete lifecycle sidecars, but two independent engineering gates failed before verified cost and unified economic acceptance. The displayed PF, return and session breakdown are inadmissible and must not be used to accept, reject, tune or filter the strategy.

## Frozen attempt

- Attempt: `STBS021-MODEL0-TRAIN-001`
- Alpha run: `20260810_023506`
- Source SHA-256: `11E44FF9B51DA50F6DF25C54858BFF492C89A58EED04684C828A70740B37FED9`
- Attempt start SHA-256: `40DCC8C2B38A0082ED9C21E85DF5A3E7F5D836AA39D6104AB999B88523C1DFB7`
- Attempt terminal SHA-256: `18B9EB6C323FCCC1B3BF39D43061EF83687E6D422A16C87FA8AC75EFB29D9DCF`
- Run manifest SHA-256: `91E9C25BF9888846944A42CAF3F21CC4D76BF3C638B583187931B91D3A918EE6`
- Tester report SHA-256: `EE65AD34F85A82F9084C78D820A71478EE5541D51ECAAEC5D0F9F293D671A66D`
- Exported journal SHA-256: `AF7561346F81685B5DD2EAD2AFECD308FE0A2A57A080DB79E40037630E43D381`
- Lifecycle CSV SHA-256: `FF7F79C44123AD87075CB036A4780C45A33AF8A34494416D3B06BD45028DB612`
- RunMeta SHA-256: `392295B680039E7AF19E63E416B041D7EE0C982E1B506CE477BCFE33788BA48A`
- Run-local non-repaint audit SHA-256: `100A7A483166AD8520766F83E17DD0CBF0EBE35ED924B8088FFA6E00F56A4BB8`
- Run EX5 SHA-256: `9852C654B2281C713A1014ED7778EF30BF3BEA47CC7A8DC3E91A1E1FFFFF7C00`
- Run config SHA-256: `B68FEAA9278D348688A696C2C0E7B0FB37AE77E79717DB0160623DB6EF8C7CDF`

## Exact failure evidence

1. Static non-repaint review explicitly authorized the sole data-quality provenance read with `nondecision_provenance_copytime_authorized=true`. The run manifest did not propagate that narrow permission. The run-local auditor therefore marked the same `CopyTime` call at source line 672 as `unproven_closed_bar_shift`, emitted `collection_authority_verified=false`, and failed.
2. This must not be repaired by asserting generic collection authority. The lawful repair is to carry the exact nondecision provenance permission through packet, receipt and run manifest to the post-run auditor.
3. Independently, position `358` breached the frozen MONEY-mode actual-margin invariant on `2019-03-21`. The journal records `STBS_MARGIN_ACTUAL_UNSAFE` with threshold `93217.43000000`, followed by `STBS_FATAL|actual_margin_contract_failed|result=0`.
4. This was not a broker stop-out. RunMeta records `forced_stopouts=0`, `margin_emergencies=1` and `runtime_failed=true`.
5. Lifecycle transport is repaired: the journal is not truncated, and the sidecar reconciles `179` OPEN rows with `179` FINAL_CLOSE rows across `179` completed positions.
6. RunMeta stops at raw/executable/gaps `185/184/1`, LONG/SHORT `91/93`, entries/closes `179/179`. The strategy did not process the complete 2018–2022 scoring window.
7. The report contains one funding row plus `358` trade-deal rows forming `179` completed trades. Its displayed PF is approximately `0.8546`, but it is inadmissible because runtime failed, the window is incomplete, and verified cost/unified gates never ran.

## Failure radius

This kills only the exact HYP021 V8 execution/evidence contract in which:

- the narrow DQ-only `CopyTime` permission is present in the static manifest but absent from the run-manifest authority supplied to the post-run auditor; and
- entry admission can pass at the requested price while the same MONEY-mode headroom invariant later becomes fatal before the frozen SL is reached.

It does not establish a valid economic verdict for the Supertrend signal. It does not authorize session, direction, stop, target, hold, indicator or acceptance-threshold changes.

## Lawful next revision

Fresh HYP022/V9 may change only two bounded contracts:

1. propagate the exact nondecision provenance `CopyTime` permission into the post-run audit contract; and
2. stress every candidate volume at its already-frozen SL with `OrderCalcProfit`, recompute the same MONEY/percent margin headroom at stressed equity/free margin, and search downward by broker volume step until the stressed candidate passes or min lot is rejected.

The runtime actual-margin check remains a fail-closed backstop. HYP022 must preserve signal, ATR14, entry/exit geometry, 1R stop, 1.5R target, eight-bar hold, session rules, cost model and economic gates. Same-ID retry of HYP021 is forbidden.
