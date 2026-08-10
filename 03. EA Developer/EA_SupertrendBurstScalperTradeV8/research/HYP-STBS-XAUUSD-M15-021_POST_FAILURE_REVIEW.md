# HYP-STBS-XAUUSD-M15-021 — Independent Post-Failure Review

## Verdict

`PASS_KILL_ENGINEERING_NR_PROVENANCE_PROPAGATION_AND_ACTUAL_MONEY_MARGIN_HALT_NO_ECONOMIC_VERDICT`

The independent review reconciled the sole HYP021 attempt and agrees that it must be terminalized without an economic conclusion.

## Reconciled facts

- Attempt start: `40DCC8C2B38A0082ED9C21E85DF5A3E7F5D836AA39D6104AB999B88523C1DFB7`
- Attempt terminal: `18B9EB6C323FCCC1B3BF39D43061EF83687E6D422A16C87FA8AC75EFB29D9DCF`
- Run manifest: `91E9C25BF9888846944A42CAF3F21CC4D76BF3C638B583187931B91D3A918EE6`
- Report: `EE65AD34F85A82F9084C78D820A71478EE5541D51ECAAEC5D0F9F293D671A66D`
- Journal: `AF7561346F81685B5DD2EAD2AFECD308FE0A2A57A080DB79E40037630E43D381`
- Lifecycle CSV: `FF7F79C44123AD87075CB036A4780C45A33AF8A34494416D3B06BD45028DB612`
- RunMeta: `392295B680039E7AF19E63E416B041D7EE0C982E1B506CE477BCFE33788BA48A`
- Run-local non-repaint audit: `100A7A483166AD8520766F83E17DD0CBF0EBE35ED924B8088FFA6E00F56A4BB8`
- Source snapshot: `11E44FF9B51DA50F6DF25C54858BFF492C89A58EED04684C828A70740B37FED9`
- Run EX5: `9852C654B2281C713A1014ED7778EF30BF3BEA47CC7A8DC3E91A1E1FFFFF7C00`
- Run config: `B68FEAA9278D348688A696C2C0E7B0FB37AE77E79717DB0160623DB6EF8C7CDF`

The review verified two independent failures. First, the static manifest authorized the single DQ provenance `CopyTime` read, but the runtime manifest did not pass that exact permission to the non-repaint auditor. Second, an owned position crossed the frozen actual-money headroom threshold and caused the EA to fail closed. The latter was not a broker stop-out; all `179` positions were lifecycle-balanced before deinitialization.

## Economic boundary

The report-derived `179` trades and PF near `0.8546` are not admissible economic evidence. Signal processing stopped in March 2019, `runtime_failed=true`, non-repaint failed, and no verified cost or unified acceptance artifact was produced. The report cannot justify filtering Wednesday, Thursday, Asia, particular hours or any other post-hoc rescue.

## Approved next lane

Fresh HYP022/V9 may:

1. propagate only the exact nondecision provenance authority required for the DQ `CopyTime` proof; and
2. make entry admission consistent with the runtime invariant by stress-testing the proposed position at its frozen SL and reducing volume downward by broker step until the stressed state passes.

A recoverable margin-triggered exit followed by resumed trading is not approved: it would introduce a new exit rule after observing the failed run. Runtime margin failure remains a protective fail-closed backstop. All signal, ATR, stop, target, hold, session, cost and acceptance choices stay frozen. No optimization, OOS, holdout, promotion, paper or live authority is granted.
