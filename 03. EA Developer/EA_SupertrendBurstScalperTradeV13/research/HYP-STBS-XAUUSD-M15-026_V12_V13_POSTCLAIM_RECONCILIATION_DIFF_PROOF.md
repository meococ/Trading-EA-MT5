# HYP026 V12-to-V13 bounded diff proof

Status: `PASS_IDENTITY_ONLY_SOURCE_PLUS_RUNNER_POSTCLAIM_RECONCILIATION`

## MQL5 source boundary

V13 differs from terminal V12 only in identity metadata:

- version `12.00` to `13.00`;
- description names the V13 post-claim reconciliation lane;
- hypothesis `HYP-STBS-XAUUSD-M15-025` to `HYP-STBS-XAUUSD-M15-026`;
- variant `STBS_H1_FLIP_M15_BURST_TRADE_V12_IDENTITY_CLONE` to `STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE`;
- magic `5604125` to `5604126`;
- EA name `EA_SupertrendBurstScalperTradeV12` to `EA_SupertrendBurstScalperTradeV13`;
- exact OnInit identity guard updated to those values.

No signal, Supertrend, ATR, exact-next mapping, data window, margin formula, volume search, entry, SL, TP, holding, exit, lifecycle, commission reserve, cost or acceptance byte was intentionally changed.

- terminal V12 source SHA256: `D96F55A26F277CFC3FDC4E23A11A84C74598C111639E629CEC1877AC3F7704C5`
- fresh V13 source SHA256: `F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4`
- fresh V13 EX5 SHA256: `032ACE29E30750585C34A39F6F74B6DA684C0BF4D1D6ACCFB04245BCBF5D92D4`
- fresh V13 compile-log SHA256: `FEC1E4F30F811E4BF5BD5B4CFD75E27705CBDE949EDA7E0D0F1FDEF72422710C`
- compile result: exactly `0 errors, 0 warnings`

## Harness boundary

The runner identity/path constants advance from HYP025/V12/STBS025 to HYP026/V13/STBS026. The sole functional harness change is inside the later Model0 launch-authority blocker.

For a fresh HYP026 `-Execute`, that blocker now accepts only the exact in-memory early claim created and fsynced by the same invocation when all of these reconcile:

- start path equals the canonical HYP026 one-shot start path;
- terminal path equals the canonical HYP026 terminal path and is still absent;
- current start bytes hash to the in-memory claim SHA;
- registry full hash and screened raw-row hash equal the post-claim contract;
- task-packet path and SHA equal the post-claim packet result.

Missing in-memory state, a pre-existing attempt root, any path/hash/registry/packet mismatch, or an existing terminal remains fail-closed. Dry-run behavior remains unchanged and never creates a claim.

This corrects only the exact HYP025 self-rejection failure. It is not a same-ID retry, strategy rescue, parameter change or outcome-informed modification.
